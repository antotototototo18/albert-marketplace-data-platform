"""Build the dated resource ledger from the L09 inventory, without cloud access."""

import argparse
import csv
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    inventory = json.loads(args.inventory.read_text())
    rows = []

    def add(resource, driver, units, price, unit, source, note=""):
        rows.append({
            "resource": resource, "driver": driver, "units": units,
            "unit_price_usd": price, "price_unit": unit, "price_read_at": "2026-11-10",
            "estimated_month_usd": f"{units * price:.10f}", "source": source, "note": note,
        })

    bq = "https://cloud.google.com/bigquery/pricing"
    gcs = "https://cloud.google.com/storage/pricing"
    artifacts = "https://cloud.google.com/artifact-registry/pricing"
    for bucket in inventory["buckets"]:
        # Current inventory is entirely Standard. Refuse to silently misprice
        # a later inventory once the legacy objects have changed class.
        if set(bucket["bytes_by_class"]) - {"STANDARD"}:
            raise ValueError("Mettre à jour les tarifs du ledger pour les classes non Standard.")
        add("gs://" + bucket["bucket"], "Stored object versions and soft-deleted objects",
            sum(bucket["bytes_by_class"].values()) / 2**30, 0.02, "GiB-month", gcs,
            "Snapshot held for a month; operations and transfers excluded.")
    for ds in inventory["datasets"]:
        if ds["storage_billing_model"] != "LOGICAL":
            raise ValueError("Le ledger attend une facturation BigQuery logique.")
        add("data-engineering-i1." + ds["dataset"], "Dataset container", 1, 0,
            "dataset-month", bq, "Storage counted once, in child table rows below.")
    for table in inventory["tables"]["rows"]:
        add("data-engineering-i1." + table["dataset"] + "." + table["table_id"],
            "Logical bytes (metadata __TABLES__)", int(table["size_bytes"]) / 2**30,
            0.02, "GiB-month", bq,
            "Conservative active-storage estimate before free tier; views/external metadata have zero bytes.")
    for address in ["bronze_arabeau", "bronze_csibieude", "warehouse_arabeau", "warehouse_csibieude"]:
        add('google_bigquery_dataset_iam_member.writer["' + address + '"]',
            "No direct usage charge", 1, 0, "binding-month", bq)
    add("google_bigquery_dataset_iam_member.bronze_reader_arabeau",
        "No direct usage charge", 1, 0, "binding-month", bq)
    image_sizes = {}
    for image in inventory["artifact_manifests"]:
        name = image["image"].split("@")[0]
        image_sizes[name] = image_sizes.get(name, 0) + image["manifest_bytes"]
    for name, size in sorted(image_sizes.items()):
        add("dataeng/" + name, "Sum of manifest sizes", size / 2**30, 0.10,
            "GiB-month", artifacts,
            "Estimate before shared free tier; shared layers may be counted several times.")
    for resource in ["google_monitoring_notification_channel.budget", "google_billing_budget.project"]:
        add(resource, "Disabled; no resource created", 0, 0, "resource-month",
            "https://cloud.google.com/billing/docs/how-to/budgets",
            "Budget API disabled; administrator action required.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} ressources : {args.output}")


if __name__ == "__main__":
    main()
