"""Run one BigQuery SQL script file as a single multi-statement job."""

import argparse
from pathlib import Path

from google.cloud import bigquery


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sql_file", type=Path)
    parser.add_argument("--project", default="data-engineering-i1")
    args = parser.parse_args()
    client = bigquery.Client(project=args.project, location="europe-west1")
    job = client.query(args.sql_file.read_text(encoding="utf-8"))
    job.result()
    print(f"{args.sql_file}: job {job.job_id} done")


if __name__ == "__main__":
    main()
