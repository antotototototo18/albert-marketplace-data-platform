import csv
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from scripts.profile_source_archive import profile


TABLES = {
    "orders.csv": [
        ["order_id", "buyer_id", "order_date"],
        ["1", "c1", "2026-10-01"],
        ["2", "c2", "2026-10-02"],
    ],
    "order_items.csv": [
        ["order_id", "p_id", "qty", "price_at_purchase"],
        ["1", "p1", "2", "7"],
        ["1", "p1", "3", "7"],
        ["99", "missing", "-1", "7"],
    ],
    "product.csv": [["p_id"], ["p1"]],
    "customer_shipping.csv": [
        ["c_id", "address_id", "is_default"],
        ["c1", "a1", "1"],
        ["c1", "a2", "1"],
    ],
    "shipping_details.csv": [
        ["address_id", "country", "street_address"],
        ["a1", "Germany", "PRIVATE_FIXTURE_VALUE"],
        ["a2", "France", "PRIVATE_FIXTURE_VALUE"],
    ],
}


def write_archive(path, entries):
    with tarfile.open(path, "w:gz") as archive:
        for name, rows in entries:
            buffer = io.StringIO(newline="")
            csv.writer(buffer).writerows(rows)
            content = buffer.getvalue().encode()
            member = tarfile.TarInfo(name)
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))


class SourceProfileTests(unittest.TestCase):
    def test_defects_are_counted_without_cleaning_or_disclosing_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.tar.gz"
            write_archive(path, TABLES.items())
            result = profile(path)
        self.assertEqual(result["tables"]["order_items.csv"]["row_count"], 3)
        self.assertEqual(result["units_ordered"], 4)
        for check in (
            "duplicate_order_product_rows",
            "order_item_rows_without_order",
            "order_item_rows_without_product",
            "customers_with_multiple_default_addresses",
            "orders_without_default_address",
            "order_item_rows_with_nonpositive_qty",
        ):
            self.assertEqual(result["checks"][check], 1, check)
        self.assertNotIn("PRIVATE_FIXTURE_VALUE", json.dumps(result))
        self.assertEqual(len(result["archive_sha256"]), 64)

    def test_missing_tables_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.tar.gz"
            write_archive(path, [("orders.csv", TABLES["orders.csv"])])
            with self.assertRaisesRegex(ValueError, "five required tables"):
                profile(path)

    def test_ambiguous_table_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.tar.gz"
            write_archive(path, [
                ("one/orders.csv", TABLES["orders.csv"]),
                ("two/orders.csv", TABLES["orders.csv"]),
            ])
            with self.assertRaisesRegex(ValueError, "Duplicate archive member"):
                profile(path)


if __name__ == "__main__":
    unittest.main()
