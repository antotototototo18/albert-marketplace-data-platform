"""Land the legacy CSV archive as bronze Parquet; publishes a manifest without rows or PII."""

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import tarfile

import pandas as pd
import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq


SOURCE = "legacy"
CODEC = "zstd"
# ADR-0001: secrets never cross the ingestion boundary. Everything else lands unchanged.
EXCLUDED_COLUMNS = {
    "customer": ["pwd"],
    "payment_details": ["card_no", "cvv"],
}
UNNAMED_COLUMN = "unnamed_0"


def header(raw):
    first = raw.split(b"\n", 1)[0].decode("utf-8-sig").rstrip("\r")
    return [name or UNNAMED_COLUMN for name in first.split(",")]


def read_as_text(raw, names):
    """Every column as a string, empty cells kept as empty strings: no type inference."""
    return pacsv.read_csv(
        io.BytesIO(raw),
        read_options=pacsv.ReadOptions(column_names=names, skip_rows=1),
        parse_options=pacsv.ParseOptions(newlines_in_values=True),
        convert_options=pacsv.ConvertOptions(
            column_types={name: pa.string() for name in names},
            strings_can_be_null=False,
            quoted_strings_can_be_null=False,
        ),
    )


def leading_zero_counts(table):
    """Values that a numeric cast would silently change, per column (counts only)."""
    counts = {}
    for name in table.column_names:
        values = [v for v in table[name].to_pylist() if v]
        if values and all(v.isdigit() for v in values):
            changed = sum(len(v) > 1 and v.startswith("0") for v in values)
            if changed:
                counts[name] = changed
    return counts


def verify(raw, names, path, kept):
    """Re-read the Parquet file and compare it with an independent pandas parse of the CSV."""
    expected = pd.read_csv(
        io.BytesIO(raw), dtype=str, keep_default_na=False, header=0, names=names
    )[kept]
    landed = pq.read_table(path).to_pandas()
    if list(landed.columns) != kept or not expected.reset_index(drop=True).equals(landed):
        raise ValueError(f"{path} does not match its CSV source")
    return len(landed)


def land(archive_path, output, ingested_date, bucket):
    with archive_path.open("rb") as source:
        archive_sha256 = hashlib.file_digest(source, "sha256").hexdigest()
    ingested_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    tables = {}
    with tarfile.open(archive_path, "r:gz") as archive:
        members = [
            m for m in archive.getmembers() if m.isfile() and m.name.endswith(".csv")
        ]
        for member in sorted(members, key=lambda m: m.name):
            name = Path(member.name).stem
            raw = archive.extractfile(member).read()
            names = header(raw)
            excluded = EXCLUDED_COLUMNS.get(name, [])
            table = read_as_text(raw, names).drop_columns(excluded)
            table = table.replace_schema_metadata({
                "source_archive_sha256": archive_sha256,
                "source_member": member.name,
                "ingested_at": ingested_at,
                "excluded_columns": ",".join(excluded),
            })
            key = f"bronze/{SOURCE}/{name}/ingested_date={ingested_date}/part-0.parquet"
            path = output / key
            path.parent.mkdir(parents=True, exist_ok=True)
            pq.write_table(table, path, compression=CODEC)
            rows = verify(raw, names, path, table.column_names)
            tables[name] = {
                "object": f"gs://{bucket}/{key}",
                "csv_bytes": len(raw),
                "parquet_bytes": path.stat().st_size,
                "rows": rows,
                "columns": table.column_names,
                "excluded_columns": excluded,
                "values_with_leading_zero": leading_zero_counts(table),
            }
    return {
        "source_archive": archive_path.name,
        "archive_sha256": archive_sha256,
        "ingested_date": ingested_date,
        "ingested_at": ingested_at,
        "layout": f"gs://{bucket}/bronze/{SOURCE}/<table>/ingested_date=YYYY-MM-DD/part-0.parquet",
        "format": f"Parquet, {CODEC}, every column stored as string",
        "verification": "each file re-read and compared cell by cell with a pandas parse of its CSV",
        "totals": {
            "tables": len(tables),
            "rows": sum(t["rows"] for t in tables.values()),
            "csv_bytes": sum(t["csv_bytes"] for t in tables.values()),
            "parquet_bytes": sum(t["parquet_bytes"] for t in tables.values()),
        },
        "tables": tables,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="Path to legacy_csv.tar.gz")
    parser.add_argument("output", type=Path, help="Local directory to write bronze/ into")
    parser.add_argument("--bucket", default="data-engineering-i1-group6")
    parser.add_argument(
        "--ingested-date",
        default=datetime.now(timezone.utc).date().isoformat(),
        help="Partition value for this load (default: today, UTC)",
    )
    parser.add_argument("--manifest", type=Path, help="Write the manifest JSON here")
    args = parser.parse_args()
    manifest = json.dumps(
        land(args.archive, args.output, args.ingested_date, args.bucket), indent=2
    ) + "\n"
    if args.manifest:
        args.manifest.write_text(manifest, encoding="utf-8")
    else:
        print(manifest, end="")


if __name__ == "__main__":
    main()
