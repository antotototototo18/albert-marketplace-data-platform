"""Measure the L04 warehouse in BigQuery; publishes byte counts and timings only."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from string import Template

from google.api_core.exceptions import GoogleAPICallError
from google.cloud import bigquery


PROJECT = "data-engineering-i1"
DATASET = "group6_warehouse"
LOCATION = "europe-west1"
QUERIES = Path(__file__).resolve().parent.parent / "warehouse" / "queries"
CAP = 1 << 30
TRIP_CAP = 1_000_000
PUBLIC_TABLE = "bigquery-public-data.samples.github_timeline"
RARE_PRODUCT = "B0CHXWTSM6"
BEST_SELLER = "B0BM4GX6TT"
TIB_PRICE = 7.50

UNTUNED = {
    "orders": "orders_untuned",
    "order_items": "order_items_untuned",
    "review": "review_untuned",
    "product_reviews": "product_reviews_untuned",
}
TUNED = {name: name for name in UNTUNED}
DAY_GRAIN = {**TUNED, "order_items": "order_items_day"}

# (table, change, probe, extra substitutions, before layout, after layout)
TUNING = [
    ("orders", "PARTITION BY month", "t_orders_last_28_days", {}, UNTUNED, TUNED),
    ("order_items", "PARTITION BY month", "q1_monthly_revenue", {}, UNTUNED, TUNED),
    ("order_items", "PARTITION BY month", "t_one_day", {}, UNTUNED, TUNED),
    ("order_items", "PARTITION BY day instead of month", "q1_monthly_revenue", {}, TUNED, DAY_GRAIN),
    ("order_items", "PARTITION BY day instead of month", "t_one_day", {}, TUNED, DAY_GRAIN),
    ("order_items", "CLUSTER BY p_id", "t_product_history", {"p_id": RARE_PRODUCT}, UNTUNED, TUNED),
    ("order_items", "CLUSTER BY p_id", "t_product_history", {"p_id": BEST_SELLER}, UNTUNED, TUNED),
    ("review", "CLUSTER BY rating", "t_low_ratings", {}, UNTUNED, TUNED),
    ("review", "CLUSTER BY rating", "q3_product_ratings", {}, UNTUNED, TUNED),
    ("product_reviews", "CLUSTER BY p_id", "t_reviews_of_product", {"p_id": RARE_PRODUCT}, UNTUNED, TUNED),
    ("product_reviews", "CLUSTER BY p_id", "t_reviews_of_product", {"p_id": BEST_SELLER}, UNTUNED, TUNED),
]
ANALYTICAL = ["q1_monthly_revenue", "q2_daily_demand_by_country", "q3_product_ratings"]


def qualified(layout):
    names = {
        **layout,
        "customer_shipping": "customer_shipping",
        "shipping_details": "shipping_details",
        "daily_demand": "daily_demand",
    }
    return {key: f"{PROJECT}.{DATASET}.{table}" for key, table in names.items()}


def render(name, layout, **extra):
    sql = (QUERIES / f"{name}.sql").read_text(encoding="utf-8")
    return Template(sql).substitute(qualified(layout), **extra)


def cost(processed):
    return round(processed / 2**40 * TIB_PRICE, 8)


def run(client, sql):
    estimate = client.query(
        sql, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
    ).total_bytes_processed
    job = client.query(
        sql,
        job_config=bigquery.QueryJobConfig(use_query_cache=False, maximum_bytes_billed=CAP),
    )
    rows = job.result().total_rows
    stats = job._properties["statistics"]["query"]
    return {
        "job_id": job.job_id,
        "estimate_bytes": estimate,
        "bytes_processed": job.total_bytes_processed,
        "bytes_billed": job.total_bytes_billed,
        "cache_hit": job.cache_hit,
        "slot_ms": job.slot_millis,
        "elapsed_ms": int((job.ended - job.started).total_seconds() * 1000),
        "rows_returned": rows,
        "cost_usd": cost(job.total_bytes_processed),
        "materialized_view_used": any(
            mv.get("chosen") for mv in
            stats.get("materializedViewStatistics", {}).get("materializedView", [])
        ),
    }


def table_stats(client):
    tables = {}
    for table in client.list_tables(f"{PROJECT}.{DATASET}"):
        full = client.get_table(table.reference)
        tables[table.table_id] = {
            "type": full.table_type,
            "rows": full.num_rows,
            "logical_bytes": full.num_bytes,
            "partitioning": full.time_partitioning.type_ if full.time_partitioning else None,
            "clustering": full.clustering_fields,
        }
    partitions = client.query(
        f"""SELECT table_name, COUNT(*) AS partitions,
                   CAST(ROUND(AVG(total_logical_bytes)) AS INT64) AS avg_bytes
            FROM `{PROJECT}.{DATASET}.INFORMATION_SCHEMA.PARTITIONS`
            WHERE partition_id IS NOT NULL AND partition_id != '__NULL__'
            GROUP BY table_name""",
        job_config=bigquery.QueryJobConfig(use_query_cache=False, maximum_bytes_billed=CAP),
    ).result()
    for row in partitions:
        if row.table_name in tables and tables[row.table_name]["partitioning"]:
            tables[row.table_name]["partitions"] = row.partitions
            tables[row.table_name]["avg_partition_bytes"] = row.avg_bytes
    return tables


def trip(client, sql, cap):
    try:
        client.query(
            sql,
            job_config=bigquery.QueryJobConfig(use_query_cache=False, maximum_bytes_billed=cap),
        ).result()
    except GoogleAPICallError as error:
        # The client reports this refusal as HTTP 500; the reason is what identifies it.
        first = error.errors[0] if error.errors else {}
        return {
            "cap": cap,
            "tripped": first.get("reason") == "bytesBilledLimitExceeded",
            "reason": first.get("reason"),
            "error": first.get("message", str(error)),
        }
    return {"cap": cap, "tripped": False}


def measure(create_view):
    client = bigquery.Client(project=PROJECT, location=LOCATION)
    results = {
        "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "project": PROJECT,
        "dataset": DATASET,
        "location": LOCATION,
        "query_cache": "disabled on every job (use_query_cache=False)",
        "per_query_cap_bytes": CAP,
        "price_per_tib_usd": TIB_PRICE,
        "tuning": [],
        "analytical": [],
    }

    # Everything that reads order_items is measured before the view exists:
    # BigQuery may rewrite a query to read a materialised view instead.
    if create_view:
        client.delete_table(f"{PROJECT}.{DATASET}.daily_demand", not_found_ok=True)
    for table, change, probe, extra, before, after in TUNING:
        row = {
            "table": table,
            "change": change,
            "query": probe,
            **{f"parameter_{k}": v for k, v in extra.items()},
            "before": run(client, render(probe, before, **extra)),
            "after": run(client, render(probe, after, **extra)),
        }
        row["ratio"] = round(
            row["before"]["bytes_processed"] / max(row["after"]["bytes_processed"], 1), 2
        )
        results["tuning"].append(row)
        print(f"{table:16} {change:34} {probe:28} {row['ratio']}x")

    for name in ANALYTICAL:
        row = {
            "query": name,
            "untuned": run(client, render(name, UNTUNED)),
            "tuned": run(client, render(name, TUNED)),
        }
        row["ratio"] = round(
            row["untuned"]["bytes_processed"] / max(row["tuned"]["bytes_processed"], 1), 2
        )
        results["analytical"].append(row)
        print(f"{name:28} {row['ratio']}x")

    collapse = dict(next(iter(client.query(
        render("collapse_ratio", TUNED),
        job_config=bigquery.QueryJobConfig(use_query_cache=False, maximum_bytes_billed=CAP),
    ).result())))
    results["collapse"] = {
        **collapse,
        "lines_per_row": {
            grain: round(collapse["order_lines"] / collapse[grain], 2)
            for grain in ("product_day", "product_week", "product_month", "product")
        },
    }

    if create_view:
        sql_file = QUERIES.parent / "05_daily_demand.sql"
        client.query(sql_file.read_text(encoding="utf-8")).result()
    results["materialized_view"] = {
        "from_table": run(client, render("t_demand_28_days", TUNED)),
        "from_view": run(client, render("t_demand_28_days_mv", TUNED)),
    }

    results["cap"] = {
        "own_table": {
            "query": "q1_monthly_revenue on the tuned tables",
            **trip(client, render("q1_monthly_revenue", TUNED), TRIP_CAP),
        },
        "public_table": {
            "query": f"SELECT * FROM `{PUBLIC_TABLE}`",
            "estimate_bytes": bigquery.Client(project=PROJECT, location="US").query(
                f"SELECT * FROM `{PUBLIC_TABLE}`",
                job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False),
            ).total_bytes_processed,
            **trip(bigquery.Client(project=PROJECT, location="US"),
                   f"SELECT * FROM `{PUBLIC_TABLE}`", CAP),
        },
    }
    results["tables"] = table_stats(client)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--create-view", action="store_true",
                        help="(re)create daily_demand after the tuning measurements")
    args = parser.parse_args()
    results = measure(args.create_view)
    args.output.write_text(json.dumps(results, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"written: {args.output}")


if __name__ == "__main__":
    main()
