"""Test PostgreSQL, Kafka and bronze storage with isolated synthetic records."""

import argparse
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import sys
from uuid import uuid4

from confluent_kafka import Consumer, Producer
from confluent_kafka.admin import AdminClient, NewTopic
import psycopg
from psycopg import sql
import pyarrow.parquet as pq

from ingestion.consume_clickstream import consume
from ingestion.extract_orders import extract
from ingestion.storage import BronzeStore


def objects(store, prefix):
    if store.bucket:
        return [(blob.name, blob.download_as_bytes(timeout=30))
                for blob in store.bucket.list_blobs(prefix=store._key(prefix), timeout=30)
                if blob.name.endswith(".parquet")]
    return [(str(path.relative_to(store.root)), path.read_bytes())
            for path in store.root.glob(f"{prefix}/**/*.parquet")]


def rows(files):
    return [row for _, content in files
            for row in pq.ParquetFile(io.BytesIO(content)).read().to_pylist()]


def verify(dsn, bootstrap, bronze_uri):
    run_id = uuid4().hex[:12]
    schema = f"l03_check_{run_id}"
    topic = f"l03-check-{run_id}"
    group = f"l03-check-{run_id}"
    root = BronzeStore(bronze_uri)
    sql_store = BronzeStore(f"{bronze_uri.rstrip('/')}/_validation/{run_id}/extractor")
    admin = AdminClient({"bootstrap.servers": bootstrap})
    report = {"run_id": run_id, "verified_at": datetime.now(timezone.utc).isoformat(),
              "bronze_uri": bronze_uri, "scope": "Synthetic isolated schema and topic; real storage uploads."}
    schema_created = topic_created = group_created = False
    try:
        with psycopg.connect(dsn) as connection:
            connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
            connection.execute(sql.SQL(
                "CREATE TABLE {}.orders (order_id integer PRIMARY KEY, buyer_id varchar, "
                "discount_id integer, payment_id integer, order_date date)"
            ).format(sql.Identifier(schema)))
            connection.execute(sql.SQL(
                "INSERT INTO {}.orders VALUES (1,'synthetic',NULL,NULL,'2026-09-15'),"
                "(2,'synthetic',NULL,NULL,'2026-09-15')"
            ).format(sql.Identifier(schema)))
        schema_created = True
        first = extract(dsn, sql_store, schema=schema, batch_size=2)
        with psycopg.connect(dsn) as connection:
            connection.execute(sql.SQL(
                "INSERT INTO {}.orders VALUES (3,'synthetic',NULL,NULL,'2026-09-15')"
            ).format(sql.Identifier(schema)))
        second = extract(dsn, sql_store, schema=schema, batch_size=2)
        with psycopg.connect(dsn) as connection:
            connection.execute(sql.SQL("UPDATE {}.orders SET buyer_id='changed' WHERE order_id=1").format(sql.Identifier(schema)))
            connection.execute(sql.SQL("DELETE FROM {}.orders WHERE order_id=2").format(sql.Identifier(schema)))
        third = extract(dsn, sql_store, schema=schema, batch_size=2)
        persisted = rows(objects(sql_store, "manual/orders"))
        assert first["rows_written"] == 2 and second["rows_written"] == 1
        assert second["last_order_id"] == 3 and third["rows_written"] == 0
        assert len(persisted) == 3
        assert any(row["order_id"] == 1 and row["buyer_id"] == "synthetic" for row in persisted)
        assert any(row["order_id"] == 2 for row in persisted)
        report["extractor"] = {
            "first_run_rows": 2, "same_day_insert_rows": 1, "cursor_after_restart": 3,
            "update_delete_run_rows": 0, "updates_captured": False, "deletes_captured": False,
            "persisted_rows": len(persisted), "storage": f"{bronze_uri}/_validation/{run_id}/extractor",
        }

        for future in admin.create_topics([NewTopic(topic, num_partitions=1, replication_factor=1)]).values():
            future.result(timeout=20)
        topic_created = True
        producer = Producer({"bootstrap.servers": bootstrap})
        now = datetime.now(timezone.utc).isoformat()
        def event(identifier):
            return json.dumps({
                "schema_version": 1, "event_id": f"{run_id}-{identifier}", "event_type": "product_viewed",
                "event_time": "2026-09-15T23:30:00-02:00", "emitted_at": now,
                "session_id": "synthetic", "buyer_id": None, "p_id": "synthetic", "price": 1.0,
            }).encode()
        broken = json.dumps({"schema_version": 999, "test_run_id": run_id}).encode()
        delivery_errors = []
        def delivered(error, message):
            if error:
                delivery_errors.append(str(error))
        for content in (event("before"), broken, event("after")):
            producer.produce(topic, value=content, on_delivery=delivered)
        assert producer.flush(20) == 0 and not delivery_errors
        consumer = Consumer({
            "bootstrap.servers": bootstrap, "group.id": group,
            "auto.offset.reset": "earliest", "enable.auto.commit": False,
            "enable.auto.offset.store": False,
        })
        prefix = f"_validation/{run_id}/clickstream"
        group_created = True
        result = consume(consumer, topic, root, batch_size=3, max_messages=3, output_prefix=prefix)
        accepted = rows(objects(root, prefix))
        quarantined_files = objects(root, "_dlq/clickstream")
        rejects = [(name, row) for name, content in quarantined_files
                   for row in pq.ParquetFile(io.BytesIO(content)).read().to_pylist()
                   if row["topic"] == topic]
        assert result == {"accepted": 2, "rejected": 1, "received": 3}
        assert len(accepted) == 2 and len(rejects) == 1
        assert rejects[0][1]["raw"] == broken
        assert {row["event_id"] for row in accepted} == {f"{run_id}-before", f"{run_id}-after"}
        assert "dt=2026-09-16" in objects(root, prefix)[0][0]
        report["clickstream"] = {
            **result, "continued_after_rejection": True, "raw_reject_preserved": True,
            "event_date_utc": "2026-09-16", "dlq_object": rejects[0][0],
            "accepted_prefix": prefix,
        }
    finally:
        if schema_created:
            with psycopg.connect(dsn) as connection:
                connection.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))
        # Only resources bearing this run's unique name are removed.
        if topic_created:
            for future in admin.delete_topics([topic]).values():
                future.result(timeout=20)
        if group_created:
            for future in admin.delete_consumer_groups([group]).values():
                future.result(timeout=20)
    report["cleanup"] = "Temporary PostgreSQL schema, Kafka topic and consumer group removed; proof objects retained."
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = verify(os.environ["DATABASE_URL"], os.environ["KAFKA_BOOTSTRAP"], os.environ["BRONZE_URI"])
    except Exception as error:
        print(f"Integration check failed: {type(error).__name__}", file=sys.stderr)
        return 1
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
