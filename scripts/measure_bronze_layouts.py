"""Measure candidate bronze layouts for orders.csv; publishes sizes and timings only."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import statistics
import tarfile
import tempfile
import time

import duckdb
import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.dataset as ds
import pyarrow.parquet as pq


TABLE = "orders.csv"
QUERY_MONTH = "2026-08"
RUNS = 7
ROW_GROUP = 1 << 20


def read_orders(archive_path):
    with tarfile.open(archive_path, "r:gz") as archive:
        member = next(m for m in archive.getmembers() if Path(m.name).name == TABLE)
        raw = archive.extractfile(member).read()
    names = raw.split(b"\n", 1)[0].decode("utf-8-sig").strip().split(",")
    names = [name or "unnamed_0" for name in names]
    as_text = pacsv.read_csv(
        io.BytesIO(raw),
        read_options=pacsv.ReadOptions(column_names=names, skip_rows=1),
        convert_options=pacsv.ConvertOptions(
            column_types={name: pa.string() for name in names},
            strings_can_be_null=False,
        ),
    )
    inferred = pacsv.read_csv(
        io.BytesIO(raw),
        read_options=pacsv.ReadOptions(column_names=names, skip_rows=1),
    )
    return raw, as_text, inferred


def tree_stats(path):
    files = [p for p in Path(path).rglob("*.parquet")]
    return len(files), sum(p.stat().st_size for p in files)


def timed(fn):
    samples = []
    for _ in range(RUNS):
        start = time.perf_counter()
        result = fn()
        samples.append((time.perf_counter() - start) * 1000)
    return result, round(statistics.median(samples), 1)


def measure(archive_path):
    raw, table, inferred = read_orders(archive_path)
    work = Path(tempfile.mkdtemp(prefix="bronze-layouts-"))
    results = {"single_file": {}, "partitioned": {}, "query": {}}
    try:
        csv_path = work / "orders.csv"
        csv_path.write_bytes(raw)

        for codec in ("none", "snappy", "gzip", "zstd"):
            target = work / f"single_{codec}.parquet"
            pq.write_table(table, target, compression=codec, row_group_size=ROW_GROUP)
            results["single_file"][f"text_{codec}"] = target.stat().st_size
        for codec in ("snappy", "zstd"):
            target = work / f"inferred_{codec}.parquet"
            pq.write_table(inferred, target, compression=codec, row_group_size=ROW_GROUP)
            results["single_file"][f"inferred_types_{codec}"] = target.stat().st_size

        dates = table["order_date"]
        layouts = {
            "ingested_date": table.append_column(
                "ingested_date", pa.array(["2026-10-16"] * len(table))
            ),
            "order_month": table.append_column(
                "order_month", pa.compute.utf8_slice_codeunits(dates, 0, 7)
            ),
            "order_day": table.append_column("dt", dates),
        }
        keys = {"ingested_date": "ingested_date", "order_month": "order_month", "order_day": "dt"}
        for name, data in layouts.items():
            target = work / name
            start = time.perf_counter()
            ds.write_dataset(
                data,
                target,
                format="parquet",
                partitioning=[keys[name]],
                partitioning_flavor="hive",
                file_options=ds.ParquetFileFormat().make_write_options(compression="zstd"),
                basename_template="part-{i}.parquet",
                # Same row groups as a single-file write, so codecs compare fairly.
                min_rows_per_group=ROW_GROUP,
                max_rows_per_group=ROW_GROUP,
                max_partitions=2000,
                existing_data_behavior="overwrite_or_ignore",
            )
            write_ms = round((time.perf_counter() - start) * 1000, 1)
            objects, size = tree_stats(target)
            results["partitioned"][name] = {
                "partitions": len({p.parent for p in target.rglob("*.parquet")}),
                "objects": objects,
                "bytes": size,
                "write_ms": write_ms,
            }

        con = duckdb.connect()
        month_filter = f"order_date LIKE '{QUERY_MONTH}-%'"
        queries = {
            "csv_all_text": f"SELECT count(*) FROM read_csv('{csv_path}', all_varchar=true) WHERE {month_filter}",
            "single_zstd": f"SELECT count(*) FROM read_parquet('{work}/single_zstd.parquet') WHERE {month_filter}",
            "ingested_date": f"SELECT count(*) FROM read_parquet('{work}/ingested_date/**/*.parquet', hive_partitioning=true, hive_types_autocast=false) WHERE {month_filter}",
            "order_month": f"SELECT count(*) FROM read_parquet('{work}/order_month/**/*.parquet', hive_partitioning=true, hive_types_autocast=false) WHERE order_month = '{QUERY_MONTH}'",
            "order_day": f"SELECT count(*) FROM read_parquet('{work}/order_day/**/*.parquet', hive_partitioning=true, hive_types_autocast=false) WHERE dt LIKE '{QUERY_MONTH}-%'",
        }
        for name, sql in queries.items():
            rows, ms = timed(lambda sql=sql: con.execute(sql).fetchone()[0])
            results["query"][name] = {"rows": rows, "median_ms": ms}
    finally:
        shutil.rmtree(work)

    with Path(archive_path).open("rb") as source:
        archive_sha256 = hashlib.file_digest(source, "sha256").hexdigest()
    return {
        "source_archive": Path(archive_path).name,
        "archive_sha256": archive_sha256,
        "table": TABLE,
        "rows": table.num_rows,
        "csv_bytes": len(raw),
        "query": f"count of orders whose order_date is in {QUERY_MONTH}, median of {RUNS} local runs (DuckDB)",
        "environment": f"pyarrow {pa.__version__}, duckdb {duckdb.__version__}, local SSD; not a GCS or BigQuery timing",
        **results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="Path to legacy_csv.tar.gz")
    parser.add_argument("--output", type=Path, help="Write the JSON here instead of stdout")
    args = parser.parse_args()
    report = json.dumps(measure(args.archive), indent=2) + "\n"
    if args.output:
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report, end="")


if __name__ == "__main__":
    main()
