"""Profile the course's legacy CSV archive without extracting or publishing rows."""

import argparse
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import tarfile


REQUIRED_TABLES = {
    "orders.csv": {"order_id", "buyer_id", "order_date"},
    "order_items.csv": {"order_id", "p_id", "qty", "price_at_purchase"},
    "product.csv": {"p_id"},
    "customer_shipping.csv": {"c_id", "address_id", "is_default"},
    "shipping_details.csv": {"address_id", "country"},
}


def profile(path):
    tables = {}
    columns = {}
    with tarfile.open(path, "r:gz") as archive:
        for member in archive.getmembers():
            name = Path(member.name).name
            if not member.isfile() or name not in REQUIRED_TABLES:
                continue
            if name in tables:
                raise ValueError(f"Duplicate archive member for {name}")
            with archive.extractfile(member) as source:
                reader = csv.DictReader(io.TextIOWrapper(source, encoding="utf-8-sig"))
                columns[name] = reader.fieldnames or []
                if not REQUIRED_TABLES[name].issubset(columns[name]):
                    raise ValueError(f"Missing required columns in {name}")
                tables[name] = list(reader)
    if set(tables) != set(REQUIRED_TABLES):
        raise ValueError("The archive does not contain all five required tables.")

    orders = tables["orders.csv"]
    items = tables["order_items.csv"]
    shipping = tables["customer_shipping.csv"]
    addresses = tables["shipping_details.csv"]
    order_keys = Counter(row["order_id"] for row in orders)
    product_keys = Counter(row["p_id"] for row in tables["product.csv"])
    address_keys = Counter(row["address_id"] for row in addresses)
    line_keys = Counter((row["order_id"], row["p_id"]) for row in items)
    default_rows = [
        row for row in shipping
        if row["is_default"].strip().casefold() in {"1", "true", "t"}
    ]
    defaults = Counter(row["c_id"] for row in default_rows)
    dates = [row["order_date"] for row in orders]
    quantities = [int(row["qty"]) for row in items]
    with path.open("rb") as source:
        archive_sha256 = hashlib.file_digest(source, "sha256").hexdigest()

    # Only aggregates and column names leave this function; no identifiers or PII.
    return {
        "source_archive": path.name,
        "archive_sha256": archive_sha256,
        "scope": "Static legacy CSV snapshot; not the L01 demonstration database or live OLTP.",
        "tables": {
            name: {"row_count": len(tables[name]), "columns": columns[name]}
            for name in sorted(tables)
        },
        "checks": {
            "duplicate_order_id_rows": sum(n - 1 for n in order_keys.values()),
            "duplicate_product_id_rows": sum(n - 1 for n in product_keys.values()),
            "duplicate_address_id_rows": sum(n - 1 for n in address_keys.values()),
            "duplicate_order_product_rows": sum(n - 1 for n in line_keys.values()),
            "order_item_rows_without_order": sum(
                row["order_id"] not in order_keys for row in items
            ),
            "order_item_rows_without_product": sum(
                row["p_id"] not in product_keys for row in items
            ),
            "customers_with_multiple_default_addresses": sum(
                count > 1 for count in defaults.values()
            ),
            "orders_without_default_address": sum(
                defaults[row["buyer_id"]] == 0 for row in orders
            ),
            "default_address_rows_without_shipping_details": sum(
                row["address_id"] not in address_keys for row in default_rows
            ),
            "order_item_rows_with_nonpositive_qty": sum(q <= 0 for q in quantities),
        },
        "order_date_range": {"min": min(dates), "max": max(dates)},
        "units_ordered": sum(quantities),
        "shipping_address_country_counts": dict(
            sorted(Counter(row["country"] for row in addresses).items())
        ),
        "limitations": [
            "Orders have no payment status or historical shipping address/country.",
            "Current default address can only provide a proxy for country at order time.",
            "This profile does not validate any deployed cloud resource.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    print(json.dumps(profile(args.archive), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
