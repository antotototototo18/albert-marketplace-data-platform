"""Attach the L10 policy tags to warehouse columns (docs/governance.md).

The taxonomy and its tags are declared in infra/terraform/governance.tf. The tables
are created by SQL, not by Terraform, so this script does the column half: it reads
the current schema, sets policyTags on the classified columns, and writes it back.
That is the demo guide's `bq show` / edit / `bq update --schema`, made repeatable.

Run it again after any reload: warehouse/03_native_load.sql recreates
shipping_details with CREATE OR REPLACE, and the new table carries no tags.

    terraform -chdir=infra/terraform output -json policy_tags > tags.json
    python scripts/apply_policy_tags.py tags.json            # show what would change
    python scripts/apply_policy_tags.py tags.json --apply    # change it

Credentials: Application Default Credentials, as every other script here.
"""

import argparse
import json
import sys

from google.cloud import bigquery

PROJECT = "data-engineering-i1"

# Column -> key of the Terraform output `policy_tags`. Columns not listed are left
# exactly as they are, including any tag somebody else put on them.
CLASSIFIED = {
    "group6_warehouse.shipping_details": {
        "street_address": "pii_contact",
        "phone": "pii_contact",
        "city": "pii_location_coarse",
        "zip": "pii_location_coarse",
    },
}


def tagged(field, tag):
    """Return a copy of a schema field carrying exactly one policy tag."""
    data = field.to_api_repr()
    data["policyTags"] = {"names": [tag]}
    return bigquery.SchemaField.from_api_repr(data)


def current_tag(field):
    names = list(field.policy_tags.names) if field.policy_tags else []
    return names[0] if names else None


def plan(table, columns, tags):
    """Return the new schema and the list of (column, before, after) changes."""
    known = {field.name for field in table.schema}
    missing = sorted(set(columns) - known)
    if missing:
        sys.exit(f"{table.full_table_id}: no column {missing}; is the table reloaded?")
    schema, changes = [], []
    for field in table.schema:
        if field.name in columns:
            tag = tags[columns[field.name]]
            if current_tag(field) != tag:
                changes.append((field.name, current_tag(field), tag))
            field = tagged(field, tag)
        schema.append(field)
    return schema, changes


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tags", help="JSON from `terraform output -json policy_tags`")
    parser.add_argument("--apply", action="store_true", help="write the schema back")
    args = parser.parse_args()

    with open(args.tags, encoding="utf-8-sig") as handle:
        tags = json.load(handle)

    client = bigquery.Client(project=PROJECT)
    for table_id, columns in CLASSIFIED.items():
        table = client.get_table(f"{PROJECT}.{table_id}")
        schema, changes = plan(table, columns, tags)
        if not changes:
            print(f"{table_id}: already tagged, nothing to do")
            continue
        for column, before, after in changes:
            print(f"{table_id}.{column}: {before or 'untagged'} -> {after}")
        if args.apply:
            table.schema = schema
            client.update_table(table, ["schema"])
            print(f"{table_id}: schema updated")
        else:
            print("dry run: add --apply to write the schema")


if __name__ == "__main__":
    main()
