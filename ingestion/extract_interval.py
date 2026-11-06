"""Extract one scheduled interval of orders or order lines to one Parquet file.

The interval comes from the run (SINCE, UNTIL), never from the clock, so a
back-fill re-extracts exactly the days it names. The output key depends only on
the table and SINCE: running the same interval twice replaces the file instead
of adding a second one. Every column is written as STRING, like the rest of
bronze (ADR-0002); NULL stays NULL.
"""

from datetime import date
import json
import logging
import os

from psycopg import sql
import pyarrow as pa
import pyarrow.parquet as pq

from ingestion.extract_orders import connect_with_retry
from ingestion.storage import BronzeStore


LOGGER = logging.getLogger(__name__)

# order_items has no date of its own: a line belongs to the interval of its order.
QUERIES = {
    "orders": (
        ("order_id", "buyer_id", "discount_id", "payment_id", "order_date"),
        "SELECT order_id, buyer_id, discount_id, payment_id, order_date "
        "FROM {schema}.orders "
        "WHERE order_date >= %s AND order_date < %s ORDER BY order_id",
    ),
    "order_items": (
        ("order_id", "p_id", "qty", "price_at_purchase"),
        "SELECT i.order_id, i.p_id, i.qty, i.price_at_purchase "
        "FROM {schema}.order_items AS i JOIN {schema}.orders AS o ON o.order_id = i.order_id "
        "WHERE o.order_date >= %s AND o.order_date < %s ORDER BY i.order_id, i.p_id",
    ),
}


def parse_interval(since, until):
    try:
        start, end = date.fromisoformat(since), date.fromisoformat(until)
    except (TypeError, ValueError):
        raise ValueError("SINCE and UNTIL must be YYYY-MM-DD dates.") from None
    if end <= start:
        raise ValueError("UNTIL must be after SINCE.")
    return start, end


def as_text(value):
    if value is None:
        return None
    return value.isoformat() if isinstance(value, date) else str(value)


def to_parquet(columns, rows):
    schema = pa.schema([(column, pa.string()) for column in columns])
    table = pa.Table.from_pylist(
        [{column: as_text(row[column]) for column in columns} for row in rows], schema=schema
    )
    output = pa.BufferOutputStream()
    pq.write_table(table, output, compression="snappy")
    return output.getvalue().to_pybytes()


def extract(dsn, store, table, since, until, schema="public", attempts=5):
    if table not in QUERIES:
        raise ValueError(f"TABLE must be one of {sorted(QUERIES)}.")
    start, end = parse_interval(since, until)
    columns, template = QUERIES[table]
    query = sql.SQL(template).format(schema=sql.Identifier(schema))
    with connect_with_retry(dsn, attempts) as connection:
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        rows = connection.execute(query, (start, end)).fetchall()
    key = f"{table}/{start.isoformat()}.parquet"
    # generation=None replaces the object: the key is the interval, so a rerun
    # overwrites its own file and never sits next to it.
    store.put_bytes(key, to_parquet(columns, rows), "application/octet-stream", generation=None)
    return {"table": table, "since": start.isoformat(), "until": end.isoformat(),
            "rows_written": len(rows), "object": key}


def main():
    logging.basicConfig(level=logging.INFO)
    try:
        result = extract(
            os.environ["DATABASE_URL"], BronzeStore(os.environ["BRONZE_URI"]),
            os.environ["TABLE"], os.environ["SINCE"], os.environ["UNTIL"],
            schema=os.environ.get("PG_SCHEMA", "public"),
        )
    except (KeyError, ValueError) as error:
        # Configuration mistakes: the message names the variable, never a value.
        LOGGER.error("Bad configuration: %s", error)
        return 2
    except Exception as error:
        # Driver errors may contain connection details. Keep them out of logs.
        LOGGER.error("Extraction failed (%s); nothing was published.", type(error).__name__)
        return 1
    print(json.dumps(result), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
