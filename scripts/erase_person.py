"""Erase one buyer from the group's bronze bucket and native tables (L10, docs/runbooks/erasure.md).

    python scripts/erase_person.py find   --buyer-id ... --workdir /private/tmp/erasure
    python scripts/erase_person.py erase  --workdir /private/tmp/erasure [--dry-run]
    python scripts/erase_person.py verify --workdir /private/tmp/erasure

`find` writes the linked identifiers and a bucket scan to the workdir; `erase` rewrites the
Parquet objects without the person's rows and DELETEs from the native tables; `verify` scans
the bucket again and counts rows in every dataset of the group. Silver and gold are rebuilt
with `dbt build` between `erase` and `verify`.

The workdir holds the clear identifiers and, while running, copies of bronze: keep it outside
the repository and delete it when done. Credentials: Application Default Credentials.
"""

import argparse
import hashlib
import json
import os
import shutil
import time

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from google.cloud import bigquery, storage

PROJECT = "data-engineering-i1"
LOCATION = "europe-west1"
BUCKET = "data-engineering-i1-group6"
PREFIX = "bronze/"
LABELS = {"team": "group6", "pipeline": "l10-erasure"}
MAX_BYTES = 1 << 30  # ADR-0004

# Column name -> which identifier set it holds. c_id is the same value as buyer_id.
KEYS = {
    "buyer_id": "buyer_id", "c_id": "buyer_id", "address_id": "address_id",
    "payment_id": "payment_id", "order_id": "order_id", "review_id": "review_id",
    "session_id": "session_id",
}
# Native tables the group owns. External tables follow the bucket; silver views and gold
# tables follow dbt.
NATIVE = [
    "group6_bronze.orders_raw", "group6_bronze.order_items_raw",
    "group6_warehouse.orders", "group6_warehouse.orders_untuned",
    "group6_warehouse.order_items", "group6_warehouse.order_items_untuned",
    "group6_warehouse.order_items_day", "group6_warehouse.review",
    "group6_warehouse.review_untuned", "group6_warehouse.product_reviews",
    "group6_warehouse.product_reviews_untuned", "group6_warehouse.customer_shipping",
    "group6_warehouse.shipping_details",
]
GROUP_DATASETS = ["group6_bronze", "group6_warehouse", "group6_silver", "group6_gold"]


def bq_client():
    return bigquery.Client(project=PROJECT, location=LOCATION)


def job_config(params=None):
    return bigquery.QueryJobConfig(
        maximum_bytes_billed=MAX_BYTES, labels=LABELS, query_parameters=params or [])


def condition(columns, ids):
    # An empty identifier list matches nothing (an empty array literal has no type in SQL).
    parts = [f"CAST({c} AS STRING) IN UNNEST({json.dumps(ids[KEYS[c]])})"
             for c in columns if ids[KEYS[c]]]
    return " OR ".join(parts) or "FALSE"


def person_mask(table, ids):
    """True for every row that holds one of the person's identifiers."""
    buyer = ids["buyer_id"][0]
    mask = pa.array([False] * table.num_rows, type=pa.bool_())
    for name in table.column_names:
        col = table[name]
        if not (pa.types.is_string(col.type) or pa.types.is_large_string(col.type)
                or pa.types.is_integer(col.type)):
            continue
        values = pc.cast(col, pa.string())
        if name in KEYS:
            hit = pc.is_in(values, value_set=pa.array(ids[KEYS[name]], type=pa.string()))
        else:  # free text and raw JSON (clickstream raw_event) can carry the id
            hit = pc.match_substring(values, buyer)
        mask = pc.or_(mask, pc.fill_null(hit, False))
    return mask


def scan_bucket(workdir, ids, label):
    """Download bronze, return {object: rows holding the person}, and the generations read."""
    gcs = storage.Client(project=PROJECT)
    found, generations, local = {}, {}, os.path.join(workdir, label)
    raw = [ids["buyer_id"][0].encode()] + [s.encode() for s in ids["session_id"]]
    for blob in gcs.list_blobs(gcs.bucket(BUCKET), prefix=PREFIX):
        path = os.path.join(local, blob.name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        blob.download_to_filename(path)
        if blob.name.endswith(".parquet"):
            n = pc.sum(person_mask(pq.read_table(path), ids)).as_py() or 0
        else:  # DLQ, state and validation files
            data = open(path, "rb").read()
            n = sum(data.count(r) for r in raw)
        if n:
            found[blob.name] = n
            generations[blob.name] = blob.generation
    return found, generations


def count_rows(ids, datasets):
    bq, counts = bq_client(), {}
    for dataset in datasets:
        for item in bq.list_tables(dataset):
            table = bq.get_table(item)
            columns = [f.name for f in table.schema if f.name in KEYS]
            if not columns:
                continue
            where = f"({condition(columns, ids)})"
            if item.table_id == "clickstream":  # require_partition_filter on dt
                where += " AND (dt >= '1970-01-01' OR dt IS NULL)"
            sql = f"SELECT COUNT(*) FROM `{PROJECT}.{dataset}.{item.table_id}` WHERE {where}"
            counts[f"{dataset}.{item.table_id}"] = list(bq.query(sql, job_config=job_config()))[0][0]
    return counts


def find(args):
    os.makedirs(args.workdir, exist_ok=True)
    bq, w = bq_client(), "data-engineering-i1.group6_warehouse"
    params = [bigquery.ScalarQueryParameter("b", "STRING", args.buyer_id)]

    def values(sql):
        return sorted({str(r[0]) for r in bq.query(sql, job_config=job_config(params))})

    ids = {
        "buyer_id": [args.buyer_id],
        "order_id": values(f"SELECT order_id FROM `{w}.orders` WHERE buyer_id = @b"),
        "payment_id": values(f"SELECT payment_id FROM `{w}.orders` WHERE buyer_id = @b"),
        "address_id": values(f"SELECT address_id FROM `{w}.customer_shipping` WHERE c_id = @b"),
        "review_id": values(f"SELECT review_id FROM `{w}.review` WHERE buyer_id = @b"),
        "session_id": values(
            "SELECT DISTINCT session_id FROM `data-engineering-i1.group6_bronze.clickstream` "
            "WHERE dt >= '1970-01-01' AND buyer_id = @b"),
    }
    json.dump(ids, open(os.path.join(args.workdir, "ids.json"), "w"))
    found, generations = scan_bucket(args.workdir, ids, "before")
    json.dump({"found": found, "generations": generations},
              open(os.path.join(args.workdir, "scan_before.json"), "w"), indent=1)
    counts = count_rows(ids, GROUP_DATASETS)
    json.dump(counts, open(os.path.join(args.workdir, "bq_before.json"), "w"), indent=1)
    print("sha256", hashlib.sha256(args.buyer_id.encode()).hexdigest())
    print("linked ids:", {k: len(v) for k, v in ids.items()})
    print("bucket objects holding the person:", len(found), "rows:", sum(found.values()))
    for table, n in counts.items():
        if n:
            print(f"  {table}: {n}")


def erase(args):
    ids = json.load(open(os.path.join(args.workdir, "ids.json")))
    scan = json.load(open(os.path.join(args.workdir, "scan_before.json")))
    bucket = storage.Client(project=PROJECT).bucket(BUCKET)
    log, start = {"objects": [], "tables": []}, time.time()
    for name, generation in sorted(scan["generations"].items()):
        source = os.path.join(args.workdir, "before", name)
        if not name.endswith(".parquet"):
            print("NOT PARQUET, handle by hand:", name)
            continue
        parquet = pq.ParquetFile(source)
        table = parquet.read()
        codec = parquet.metadata.row_group(0).column(0).compression.lower()
        kept = table.filter(pc.invert(person_mask(table, ids)))
        removed = table.num_rows - kept.num_rows
        log["objects"].append({"object": name, "rows_removed": removed})
        print(f"{name}: {removed} rows")
        if args.dry_run:
            continue
        target = os.path.join(args.workdir, "after", name)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        pq.write_table(kept, target, compression=codec)
        # Fails if someone rewrote the object since `find`: run `find` again.
        bucket.blob(name).upload_from_filename(target, if_generation_match=generation)
    bq = bq_client()
    for name in NATIVE:
        table = bq.get_table(f"{PROJECT}.{name}")
        columns = [f.name for f in table.schema if f.name in KEYS]
        verb = "SELECT COUNT(*) FROM" if args.dry_run else "DELETE FROM"
        job = bq.query(f"{verb} `{PROJECT}.{name}` WHERE {condition(columns, ids)}",
                       job_config=job_config())
        rows = job.result()
        n = list(rows)[0][0] if args.dry_run else job.num_dml_affected_rows
        log["tables"].append({"table": name, "rows": n, "job_id": job.job_id})
        print(f"{name}: {n} rows")
    log["seconds"] = round(time.time() - start)
    if not args.dry_run:
        json.dump(log, open(os.path.join(args.workdir, "erase_log.json"), "w"), indent=1)
    print("seconds", log["seconds"], "(dry run, nothing written)" if args.dry_run else "")


def verify(args):
    ids = json.load(open(os.path.join(args.workdir, "ids.json")))
    found, _ = scan_bucket(args.workdir, ids, "verify")
    counts = count_rows(ids, GROUP_DATASETS)
    json.dump({"bucket": found, "tables": counts},
              open(os.path.join(args.workdir, "verify.json"), "w"), indent=1)
    shutil.rmtree(os.path.join(args.workdir, "verify"), ignore_errors=True)
    left = {k: v for k, v in counts.items() if v}
    print("bucket objects still holding the person:", len(found))
    print("tables still holding the person:", left or "none")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("step", choices=["find", "erase", "verify"])
    parser.add_argument("--workdir", required=True, help="outside the repository")
    parser.add_argument("--buyer-id", help="required by find")
    parser.add_argument("--dry-run", action="store_true", help="erase: count, write nothing")
    args = parser.parse_args()
    if args.step == "find" and not args.buyer_id:
        parser.error("find needs --buyer-id")
    {"find": find, "erase": erase, "verify": verify}[args.step](args)


if __name__ == "__main__":
    main()
