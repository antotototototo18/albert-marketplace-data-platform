"""Compare L09 queries with cache off; publish metrics and hashes, never rows."""

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
from string import Template

from google.cloud import bigquery


ROOT = Path(__file__).resolve().parents[1]
LABELS = {
    "team": "group6", "environment": "course",
    "pipeline": "marketplace", "component": "finops",
}


def measure(client, filename, substitutions):
    sql = Template((ROOT / "warehouse/queries" / filename).read_text()).substitute(substitutions)
    job = client.query(sql, job_config=bigquery.QueryJobConfig(
        use_query_cache=False, maximum_bytes_billed=1 << 30, labels=LABELS,
    ))
    # ORDER BY in both queries makes the comparison deterministic. The iterator
    # follows every result page; no LIMIT or sample can hide a difference.
    rows = [dict(row) for row in job.result()]
    signature = hashlib.sha256(json.dumps(
        rows, sort_keys=True, default=str, separators=(",", ":"),
    ).encode()).hexdigest()
    return {
        "job_id": job.job_id,
        "query_sha256": hashlib.sha256(sql.encode()).hexdigest(),
        "bytes_processed": job.total_bytes_processed,
        "bytes_billed": job.total_bytes_billed,
        "cache_hit": job.cache_hit,
        "slot_ms": job.slot_millis,
        "rows": len(rows),
        "result_sha256": signature,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--month", default="2026-09", help="YYYY-MM")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    start = date.fromisoformat(args.month + "-01")
    end = date(start.year + (start.month == 12), start.month % 12 + 1, 1)
    substitutions = {"month": args.month, "month_start": str(start), "month_end": str(end)}
    client = bigquery.Client(project="data-engineering-i1", location="europe-west1")
    before = measure(client, "l09_monthly_demand_before.sql", substitutions)
    after = measure(client, "l09_monthly_demand.sql", substitutions)
    equal = before["result_sha256"] == after["result_sha256"] and before["rows"] == after["rows"]
    report = {
        "measured_at": datetime.now(timezone.utc).isoformat(), "month": args.month,
        "project": client.project, "location": "europe-west1", "labels": LABELS,
        "before": before, "after": after, "results_equal": equal,
        "processed_bytes_saved": before["bytes_processed"] - after["bytes_processed"],
        "billed_bytes_saved": before["bytes_billed"] - after["bytes_billed"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    if not equal:
        raise SystemExit("Résultats différents : optimisation refusée, voir le rapport.")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
