"""Export the configured catalog of the local Airbyte connection, without any connector configuration."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request

API = "http://localhost:8000/api/v1"
PUBLIC_API = "http://localhost:8000/api/public/v1"


def credentials():
    # abctl prints the application credentials; they stay in this process.
    run = subprocess.run(["abctl", "local", "credentials"], capture_output=True, text=True)
    text = re.sub(r"\x1b\[[0-9;]*m", "", run.stdout + run.stderr)
    client_id = re.search(r"Client-Id:\s*(\S+)", text)
    secret = re.search(r"Client-Secret:\s*(\S+)", text)
    if not client_id or not secret:
        raise RuntimeError("abctl did not print Client-Id and Client-Secret.")
    return client_id.group(1), secret.group(1)


def call(url, body=None, token=None):
    request = urllib.request.Request(
        url, data=None if body is None else json.dumps(body).encode(),
        method="GET" if body is None else "POST",
        headers={"Content-Type": "application/json", "Accept": "application/json",
                 **({"Authorization": f"Bearer {token}"} if token else {})})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Airbyte refused {url.split('/api/')[1]}: HTTP {error.code}") from None


def export(source_name):
    client_id, secret = credentials()
    token = call(f"{API}/applications/token", {
        "client_id": client_id, "client_secret": secret, "grant-type": "client_credentials",
    })["access_token"]
    connections = [
        item for item in call(f"{PUBLIC_API}/connections?limit=100", token=token)["data"]
        if call(f"{PUBLIC_API}/sources/{item['sourceId']}", token=token)["name"] == source_name
    ]
    if len(connections) != 1:
        raise RuntimeError(f"Expected one connection from '{source_name}', found {len(connections)}.")
    connection = call(f"{API}/web_backend/connections/get", {
        "connectionId": connections[0]["connectionId"], "withRefreshedCatalog": False,
    }, token)
    source = call(f"{API}/sources/get", {"sourceId": connection["source"]["sourceId"]}, token)
    jobs = call(f"{API}/jobs/list", {
        "configTypes": ["sync"], "configId": connection["connectionId"], "pagination": {"pageSize": 5},
    }, token)["jobs"]
    # Only the catalog and job outcomes: source and destination settings may hold secrets.
    return {
        **{key: connection.get(key) for key in (
            "connectionId", "name", "status", "scheduleType", "scheduleData", "syncCatalog")},
        "replicationMethod": source["connectionConfiguration"].get("replication_method", {}).get("method"),
        "jobs": [{"id": job["job"]["id"], "status": job["job"]["status"],
                  "attempts": [{"status": attempt.get("status"), "recordsSynced": attempt.get("recordsSynced")}
                               for attempt in job.get("attempts", [])]}
                 for job in jobs],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="An untracked file, e.g. data/airbyte-export.local.json")
    parser.add_argument("--source-name", default="Marketplace Postgres (group6)")
    args = parser.parse_args()
    try:
        document = export(args.source_name)
    except (RuntimeError, OSError, KeyError) as error:
        parser.exit(1, f"Airbyte export failed: {error}\n")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=1) + "\n")
    print("replication method:", document["replicationMethod"], "| schedule:", document["scheduleType"])
    for entry in document["syncCatalog"]["streams"]:
        if entry["config"].get("selected"):
            print(f"  {entry['stream']['name']:18} {entry['config']['syncMode']} | {entry['config']['destinationSyncMode']}")
    for job in document["jobs"]:
        print(f"  job {job['id']}: {job['status']}, attempts {[a['status'] for a in job['attempts']]}")
    print("catalog saved to", args.output)


if __name__ == "__main__":
    main()
