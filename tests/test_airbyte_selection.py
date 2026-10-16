import copy
import unittest

from ingestion.check_airbyte_export import SELECTION, check_export


def exported_connection():
    streams = []
    for name, columns in SELECTION["required_streams"].items():
        streams.append({
            "stream": {"name": name, "jsonSchema": {"properties": dict.fromkeys(columns, {})}, "sourceDefinedCursor": True},
            "config": {"selected": True, "syncMode": "incremental", "destinationSyncMode": "append"},
        })
    return {"connectionId": "synthetic-connection", "status": "active", "scheduleType": "basic",
            "syncCatalog": {"streams": streams}, "credentials": "PRIVATE_FIXTURE_VALUE"}


class AirbyteSelectionTests(unittest.TestCase):
    def test_all_seven_streams_and_only_whitelisted_evidence(self):
        result = check_export(exported_connection())
        self.assertEqual(set(result["streams"]), set(SELECTION["required_streams"]))
        self.assertNotIn("credentials", result)
        self.assertNotIn("PRIVATE_FIXTURE_VALUE", str(result))

    def test_missing_stream_and_manual_connection_are_rejected(self):
        connection = exported_connection()
        connection["syncCatalog"]["streams"].pop()
        with self.assertRaises(ValueError):
            check_export(connection)
        connection = exported_connection()
        connection["scheduleType"] = "manual"
        with self.assertRaises(ValueError):
            check_export(connection)

    def test_secret_columns_must_be_deselected_before_writing(self):
        connection = exported_connection()
        sensitive = {
            "stream": {"name": "customer", "jsonSchema": {"properties": {"c_id": {}, "pwd": {}}}},
            "config": {"selected": True, "syncMode": "incremental", "destinationSyncMode": "append"},
        }
        connection["syncCatalog"]["streams"].append(sensitive)
        with self.assertRaises(ValueError):
            check_export(connection)
        sensitive["config"].update({"fieldSelectionEnabled": True, "selectedFields": [{"fieldPath": ["c_id"]}]})
        self.assertEqual(check_export(connection)["streams"]["customer"]["columns"], ["c_id"])
        broken = copy.deepcopy(connection)
        broken["syncCatalog"]["streams"][-1]["config"]["selectedFields"].append({"fieldPath": ["pwd"]})
        with self.assertRaises(ValueError):
            check_export(broken)


if __name__ == "__main__":
    unittest.main()
