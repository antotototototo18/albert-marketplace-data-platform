"""Capture group 6 cost units and labels without exporting data or credentials."""

import argparse
from collections import Counter
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path

import google.auth
from google.auth.transport.requests import AuthorizedSession
from google.cloud import bigquery

from measure_finops import LABELS, ROOT


PROJECT = "data-engineering-i1"
DATASETS = ["group6_bronze", "group6_warehouse", "group6_silver", "group6_gold"]


def paged(session, url, key, params=None):
    params = dict(params or {})
    items = []
    while True:
        response = session.get(url, params=params, timeout=60)
        response.raise_for_status()
        page = response.json()
        items.extend(page.get(key, []))
        if not page.get("nextPageToken"):
            return items
        params["pageToken"] = page["nextPageToken"]


def query(client, sql, parameters=None):
    job = client.query(sql, job_config=bigquery.QueryJobConfig(
        use_query_cache=False, maximum_bytes_billed=1 << 30,
        labels=LABELS, query_parameters=parameters or [],
    ))
    return {"job_id": job.job_id, "rows": [dict(row) for row in job.result()]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--end-date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    start = args.end_date - timedelta(days=30)
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    session = AuthorizedSession(credentials)
    client = bigquery.Client(project=PROJECT, location="europe-west1", credentials=credentials)
    sql = (ROOT / "warehouse/queries/l09_jobs_daily.sql").read_text()
    daily = query(client, sql, [
        bigquery.ScalarQueryParameter("start_date", "DATE", start),
        bigquery.ScalarQueryParameter("end_date", "DATE", args.end_date),
    ])
    table_sql = " UNION ALL ".join(
        f"SELECT '{dataset}' AS dataset, table_id, row_count, size_bytes, type "
        f"FROM `{PROJECT}.{dataset}.__TABLES__`" for dataset in DATASETS
    ) + " ORDER BY dataset, table_id"
    tables = query(client, table_sql)
    datasets = []
    for name in DATASETS:
        ds = client.get_dataset(f"{PROJECT}.{name}")
        datasets.append({
            "dataset": name, "labels": ds.labels,
            "storage_billing_model": ds._properties.get("storageBillingModel", "LOGICAL"),
            "logical_bytes": sum(int(t["size_bytes"]) for t in tables["rows"] if t["dataset"] == name),
        })
    buckets = []
    for name in ["data-engineering-i1-group6", "data-engineering-i1-group6-tfstate"]:
        base = f"https://storage.googleapis.com/storage/v1/b/{name}"
        response = session.get(base, timeout=60)
        response.raise_for_status()
        meta = response.json()
        objects = paged(session, base + "/o", "items", {"versions": "true", "maxResults": 1000})
        soft = paged(session, base + "/o", "items", {"softDeleted": "true", "maxResults": 1000})
        by_class = Counter()
        for obj in objects + soft:
            by_class[obj["storageClass"]] += int(obj["size"])
        buckets.append({
            "bucket": name, "labels": meta.get("labels", {}), "location": meta["location"],
            "object_versions": len(objects), "soft_deleted_objects": len(soft),
            "bytes_by_class": dict(by_class),
        })
    images = paged(session,
        f"https://artifactregistry.googleapis.com/v1/projects/{PROJECT}/locations/europe-west1/repositories/dataeng/dockerImages",
        "dockerImages", {"pageSize": 1000})
    images = [{"image": x["uri"].split("/")[-1], "manifest_bytes": int(x.get("imageSizeBytes", 0))}
              for x in images if "/group6-" in x["uri"]]
    visible_datasets = sorted(ds.dataset_id for ds in client.list_datasets())
    report = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "project": PROJECT, "location": "europe-west1",
        "window": {"start_inclusive": str(start), "end_exclusive": str(args.end_date)},
        "source": "INFORMATION_SCHEMA.JOBS_BY_PROJECT; __TABLES__; resource metadata APIs",
        "billing_export_candidates_visible": [n for n in visible_datasets if any(
            word in n.lower() for word in ["billing", "cost", "export"])],
        "daily": daily, "datasets": datasets, "tables": tables,
        "buckets": buckets, "artifact_manifests": images,
        "artifact_note": "Manifest sizes can double-count shared layers; not invoice bytes.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(f"Capture enregistrée : {args.output}")


if __name__ == "__main__":
    main()
