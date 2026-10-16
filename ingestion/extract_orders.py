"""Append new orders, at least once for visible increasing IDs; updates/deletes are not captured."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
import time
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row
import pyarrow as pa

from ingestion.storage import BronzeStore


LOGGER = logging.getLogger(__name__)
ORDER_SCHEMA = pa.schema([
    ("order_id", pa.int32()), ("buyer_id", pa.string()),
    ("discount_id", pa.int32()), ("payment_id", pa.int32()),
    ("order_date", pa.date32()),
])
CHECKPOINT = "_state/manual/orders.json"


def connect_with_retry(dsn, attempts=5, initial_delay=1, sleep=time.sleep):
    if attempts < 1 or initial_delay < 0:
        raise ValueError("Invalid retry configuration.")
    for attempt in range(attempts):
        try:
            return psycopg.connect(dsn, row_factory=dict_row, connect_timeout=5)
        except psycopg.OperationalError:
            if attempt + 1 == attempts:
                raise
            delay = min(initial_delay * 2 ** attempt, 30)
            LOGGER.warning("PostgreSQL connection failed; retry %s in %ss", attempt + 1, delay)
            sleep(delay)


def extract(dsn, store, schema="public", batch_size=5000, attempts=5, initial_delay=1):
    if not dsn or batch_size < 1:
        raise ValueError("DATABASE_URL and a positive batch size are required.")
    connection_info = conninfo_to_dict(dsn)
    identity = {key: connection_info.get(key, "") for key in ("host", "port", "dbname")}
    identity["schema"] = schema
    source_id = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    state, generation = store.read_checkpoint(CHECKPOINT)
    if state and state.get("source_id") != source_id:
        raise ValueError("The checkpoint belongs to a different database or schema.")
    cursor_id = state["last_order_id"] if state else 0
    if type(cursor_id) is not int or cursor_id < 0:
        raise ValueError("Invalid saved order cursor.")
    query = sql.SQL(
        "SELECT order_id, buyer_id, discount_id, payment_id, order_date "
        "FROM {}.orders WHERE order_id > %s ORDER BY order_id LIMIT %s"
    ).format(sql.Identifier(schema))
    total = 0
    with connect_with_retry(dsn, attempts, initial_delay) as connection:
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        while True:
            rows = connection.execute(query, (cursor_id, batch_size)).fetchall()
            if not rows:
                break
            batch_id = uuid4().hex
            day = datetime.now(timezone.utc).date().isoformat()
            store.put_parquet(
                f"manual/orders/ingested_date={day}/part-{batch_id}.parquet", rows, ORDER_SCHEMA
            )
            # All objects are durable before moving the cursor. A crash can replay a batch.
            cursor_id = rows[-1]["order_id"]
            generation = store.put_checkpoint(CHECKPOINT, {
                "source_id": source_id, "last_order_id": cursor_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }, generation)
            total += len(rows)
    return {"rows_written": total, "last_order_id": cursor_id}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=5000)
    parser.add_argument("--attempts", type=int, default=5)
    parser.add_argument("--interval-seconds", type=float)
    args = parser.parse_args()
    if args.interval_seconds is not None and args.interval_seconds <= 0:
        parser.error("--interval-seconds must be positive")
    logging.basicConfig(level=logging.INFO)
    try:
        store = BronzeStore(os.environ["BRONZE_URI"])
        while True:
            result = extract(
                os.environ["DATABASE_URL"], store,
                schema=os.environ.get("PG_SCHEMA", "public"),
                batch_size=args.batch_size, attempts=args.attempts,
            )
            print(json.dumps(result), flush=True)
            if args.interval_seconds is None:
                return 0
            time.sleep(args.interval_seconds)
    except KeyboardInterrupt:
        return 0
    except Exception as error:
        # Driver errors may contain connection details. Keep them out of logs.
        LOGGER.error("Extraction stopped (%s); checkpoint was not advanced for failed writes.", type(error).__name__)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
