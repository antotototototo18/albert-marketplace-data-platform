"""Check a real Airbyte configured catalog and retain only non-secret evidence."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path


SELECTION = json.loads((Path(__file__).parent / "airbyte" / "selection.json").read_text())


def check_export(document):
    connection = document.get("connection", document)
    if connection.get("status") != "active":
        raise ValueError("The exported connection must be active.")
    if connection.get("scheduleType") not in {"basic", "cron"}:
        raise ValueError("The connection must have an automatic schedule.")
    streams = connection["syncCatalog"]["streams"]
    selected = {}
    for entry in streams:
        config = entry["config"]
        if config.get("selected") is not True:
            continue
        name = entry["stream"]["name"]
        if name in selected:
            raise ValueError(f"Ambiguous stream name: {name}")
        if config.get("fieldSelectionEnabled") is True:
            paths = [field["fieldPath"] for field in config["selectedFields"]]
            if any(len(path) != 1 for path in paths):
                raise ValueError(f"Expected explicit top-level columns for {name}")
            columns = {path[0] for path in paths}
        else:
            columns = set(entry["stream"]["jsonSchema"]["properties"])
        forbidden = columns.intersection(SELECTION["forbidden_columns"])
        if forbidden:
            raise ValueError(f"Forbidden columns selected in {name}: {sorted(forbidden)}")
        selected[name] = {
            "columns": sorted(columns), "sync_mode": config.get("syncMode"),
            "destination_sync_mode": config.get("destinationSyncMode"),
            "cursor_field": config.get("cursorField", []),
            "source_defined_cursor": entry["stream"].get("sourceDefinedCursor", False),
        }
    for name, required in SELECTION["required_streams"].items():
        if name not in selected:
            raise ValueError(f"Required stream missing: {name}")
        if selected[name]["sync_mode"] != "incremental":
            raise ValueError(f"Required stream is not incremental: {name}")
        if selected[name]["destination_sync_mode"] != "append":
            raise ValueError(f"Expected append destination mode for GCS: {name}")
        if not set(required).issubset(selected[name]["columns"]):
            raise ValueError(f"Required columns missing: {name}")
    return {
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "connection_id": connection["connectionId"],
        "schedule_type": connection["scheduleType"], "streams": selected,
        "secret_exclusions_verified": True,
        "scope": "Configured catalog only; source replication method, destination and sync results require separate verification.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = check_export(json.loads(args.export.read_text()))
    except (ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Airbyte selection check failed: {error}\n")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print("Selected streams and secret exclusions verified; evidence saved.")


if __name__ == "__main__":
    main()
