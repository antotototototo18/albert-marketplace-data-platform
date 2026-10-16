"""Deliver Kafka events at least once by persisting valid rows and rejects before committing offsets."""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
import logging
import math
import os
from pathlib import Path
import re
import time
from uuid import uuid4

from confluent_kafka import Consumer, KafkaException, TopicPartition
from jsonschema import Draft202012Validator, FormatChecker
import pyarrow as pa

from ingestion.storage import BronzeStore


LOGGER = logging.getLogger(__name__)
SCHEMA = json.loads(Path(__file__).with_name("clickstream.schema.json").read_text())
Draft202012Validator.check_schema(SCHEMA)
FORMAT_CHECKER = FormatChecker()


@FORMAT_CHECKER.checks("date-time", raises=(ValueError, TypeError))
def is_timestamp(value):
    if not isinstance(value, str):
        return True  # JSON Schema handles the field's type separately.
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})", value):
        return False
    return datetime.fromisoformat(value.upper().replace("Z", "+00:00")).tzinfo is not None


VALIDATORS = {1: Draft202012Validator(SCHEMA, format_checker=FORMAT_CHECKER)}
EVENT_SCHEMA = pa.schema([
    ("schema_version", pa.int64()), ("event_id", pa.string()),
    ("event_type", pa.string()), ("event_time", pa.string()),
    ("emitted_at", pa.string()), ("session_id", pa.string()),
    ("buyer_id", pa.string()), ("p_id", pa.string()), ("price", pa.float64()),
    ("qty", pa.int64()), ("order_id", pa.int64()),
    ("payment_method", pa.string()), ("amount", pa.float64()),
    ("currency", pa.string()),
    ("items", pa.list_(pa.struct([
        ("p_id", pa.string()), ("qty", pa.int64()), ("price", pa.float64()),
    ]))),
    ("raw_event", pa.string()), ("_kafka_topic", pa.string()),
    ("_kafka_partition", pa.int32()), ("_kafka_offset", pa.int64()),
    ("_ingested_at", pa.string()),
])
DLQ_SCHEMA = pa.schema([
    ("raw", pa.binary()), ("reason", pa.string()), ("quarantined_at", pa.string()),
    ("topic", pa.string()), ("partition", pa.int32()), ("offset", pa.int64()),
])


def json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON property")
        result[key] = value
    return result


def reject_constant(_):
    raise ValueError("Non-finite JSON number")


def finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Non-finite JSON number")
    return number


def validate_event(raw):
    event = json.loads(
        raw.decode("utf-8"), object_pairs_hook=json_object,
        parse_constant=reject_constant, parse_float=finite_float,
    )
    if not isinstance(event, dict) or type(event.get("schema_version")) is not int:
        raise ValueError("Missing integer schema_version")
    validator = VALIDATORS.get(event["schema_version"])
    if not validator:
        raise ValueError("Unsupported schema_version")
    error = next(validator.iter_errors(event), None)
    if error:
        path = "/" + "/".join(str(p) for p in error.absolute_path)
        if error.validator == "required":
            # Field names only: validator messages would copy event values into the DLQ reason.
            missing = [name for name in error.validator_value if name not in error.instance]
            raise ValueError(f"{path}: missing required {', '.join(missing)}")
        raise ValueError(f"{path}: failed {error.validator}")
    return event


class EventBatch:
    def __init__(self, store, output_prefix="clickstream/v1"):
        self.store = store
        self.output_prefix = output_prefix
        self.good = defaultdict(list)
        self.bad = []
        self.offsets = {}
        self.size = 0
        self.accepted = 0
        self.rejected = 0

    def add(self, message):
        raw = message.value()
        now = datetime.now(timezone.utc).isoformat()
        position = {"topic": message.topic(), "partition": message.partition(), "offset": message.offset()}
        try:
            if raw is None:
                raise ValueError("Kafka tombstone without event payload")
            event = validate_event(raw)
        except (ValueError, UnicodeError, TypeError, RecursionError) as error:
            self.bad.append({"raw": raw, "reason": str(error), "quarantined_at": now, **position})
            self.rejected += 1
        else:
            day = datetime.fromisoformat(event["event_time"].upper().replace("Z", "+00:00")).astimezone(timezone.utc).date()
            self.good[str(day)].append({
                **event, "raw_event": raw.decode("utf-8"), "_ingested_at": now,
                **{f"_kafka_{key}": value for key, value in position.items()},
            })
            self.accepted += 1
        self.offsets[(message.topic(), message.partition())] = message.offset() + 1
        self.size += 1

    def flush(self, consumer):
        if not self.size:
            return
        batch_id = uuid4().hex
        for day, rows in self.good.items():
            self.store.put_parquet(f"{self.output_prefix}/dt={day}/part-{batch_id}.parquet", rows, EVENT_SCHEMA)
        if self.bad:
            day = self.bad[0]["quarantined_at"][:10]
            self.store.put_parquet(f"_dlq/clickstream/dt={day}/part-{batch_id}.parquet", self.bad, DLQ_SCHEMA)
        offsets = [TopicPartition(topic, partition, offset) for (topic, partition), offset in self.offsets.items()]
        committed = consumer.commit(offsets=offsets, asynchronous=False)
        if any(position.error for position in committed):
            raise RuntimeError("Kafka refused one or more offset commits.")
        self.good.clear()
        self.bad.clear()
        self.offsets.clear()
        self.size = 0


def consume(consumer, topic, store, batch_size=200, flush_seconds=5, max_messages=None,
            output_prefix="clickstream/v1"):
    if batch_size < 1 or flush_seconds <= 0 or (max_messages is not None and max_messages < 1):
        raise ValueError("Batch limits must be positive.")
    batch = EventBatch(store, output_prefix=output_prefix)
    consumer.subscribe([topic], on_revoke=lambda current, partitions: batch.flush(current))
    received = 0
    last_flush = time.monotonic()
    try:
        while max_messages is None or received < max_messages:
            message = consumer.poll(1.0)
            if message is not None:
                if message.error():
                    raise KafkaException(message.error())
                batch.add(message)
                received += 1
            if batch.size >= batch_size or time.monotonic() - last_flush >= flush_seconds:
                batch.flush(consumer)
                last_flush = time.monotonic()
        batch.flush(consumer)
    except KeyboardInterrupt:
        batch.flush(consumer)
    finally:
        consumer.close()
    return {"accepted": batch.accepted, "rejected": batch.rejected, "received": received}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-messages", type=int)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    try:
        config = {
            "bootstrap.servers": os.environ["KAFKA_BOOTSTRAP"],
            "group.id": os.environ["CONSUMER_GROUP"],
            "enable.auto.commit": False, "enable.auto.offset.store": False,
            "auto.offset.reset": "earliest", "allow.auto.create.topics": False,
        }
        # Optional TLS/SASL client settings live in an untracked local file.
        if os.environ.get("KAFKA_CLIENT_CONFIG"):
            extra = json.loads(Path(os.environ["KAFKA_CLIENT_CONFIG"]).read_text())
            reserved = {"group.id", "enable.auto.commit", "enable.auto.offset.store", "auto.offset.reset"}
            if reserved.intersection(extra):
                raise ValueError("Kafka auth configuration cannot override delivery settings.")
            config.update(extra)
        store = BronzeStore(os.environ["BRONZE_URI"])
        result = consume(
            Consumer(config), os.environ.get("KAFKA_TOPIC", "clickstream"), store,
            batch_size=int(os.environ.get("KAFKA_BATCH_SIZE", "200")),
            flush_seconds=float(os.environ.get("KAFKA_FLUSH_SECONDS", "5")),
            max_messages=args.max_messages,
        )
    except Exception as error:
        LOGGER.error("Consumer stopped (%s); failed batches remain uncommitted.", type(error).__name__)
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
