#!/bin/sh
# Run from repository root. Only Docker and a POSIX shell are required.
set -eu
# Git Bash on Windows rewrites /output and /config into host paths; disable it.
export MSYS_NO_PATHCONV=1
IMAGE=${1:?Usage: sh scripts/reproduce-images.sh REGISTRY/ingestion:TAG}
case "$IMAGE" in *:20*) ;; *) echo 'Expected an explicitly dated image tag' >&2; exit 1;; esac
RUN_ID="l06-$(date -u +%Y%m%d%H%M%S)-$$"
# Remove this run's database and network even when a step fails.
trap 'docker rm -f "$RUN_ID-db" >/dev/null 2>&1 || true; docker network rm "$RUN_ID" >/dev/null 2>&1 || true' EXIT
PG=postgres:17.6-bookworm@sha256:f3bd19c606e442c3d7bdfa8002e03fe260a1023351e0ea4598032022b68dd6e3
set -x
docker network create "$RUN_ID"
docker run -d --name "$RUN_ID-db" --network "$RUN_ID" --network-alias fixture \
  -e POSTGRES_HOST_AUTH_METHOD=trust "$PG"
# Trust authentication is confined to this disposable network, with no host port.
ready=0
while [ "$ready" -lt 60 ]; do
  if docker exec "$RUN_ID-db" pg_isready -U postgres; then break; fi
  ready=$((ready + 1))
  sleep 1
done
docker exec -i "$RUN_ID-db" psql -v ON_ERROR_STOP=1 -U postgres <<'SQL'
CREATE TABLE orders (order_id integer PRIMARY KEY, buyer_id text, discount_id integer, payment_id integer, order_date date);
INSERT INTO orders VALUES (1, 'fixture-a', NULL, 101, '2026-10-01'), (2, 'fixture-b', 7, 102, '2026-10-02'), (3, 'fixture-a', NULL, 103, '2026-10-03');
SELECT count(*) AS frozen_input_rows FROM orders;
SQL
check_output() {
  docker run --rm --network none -v "$1:/output:ro" --entrypoint python "$IMAGE" -c '
import hashlib, json
from pathlib import Path
import pyarrow.parquet as pq
rows = []
for path in sorted(Path("/output/manual/orders").rglob("*.parquet")):
    rows.extend(pq.ParquetFile(path).read().to_pylist())
rows.sort(key=lambda row: row["order_id"])
payload = json.dumps(rows, sort_keys=True, default=str, separators=(",", ":"))
print(payload)
print("rows=", len(rows), "sha256=", hashlib.sha256(payload.encode()).hexdigest())
assert len(rows) == 3
assert [row["order_id"] for row in rows] == [1, 2, 3]
'
}
run_job() {
  docker volume create "$1"
  # A new volume is initialized from the image's /output, owned by UID 10001.
  docker run --rm --network "$RUN_ID" -v "$1:/output" \
    -e DATABASE_URL=postgresql://postgres@fixture/postgres -e BRONZE_URI=/output "$IMAGE"
}
docker image inspect "$IMAGE" --format 'user={{.Config.User}} id={{.Id}} digests={{json .RepoDigests}}'
run_job "$RUN_ID-before"
BEFORE=$(check_output "$RUN_ID-before")
printf '%s\n' "$BEFORE"
IMAGE_ID=$(docker image inspect "$IMAGE" --format '{{.Id}}')
docker rmi "$IMAGE"
docker images "$IMAGE"
# Check the image ID, not only the tag: with another local tag, rmi only untags.
if docker image inspect "$IMAGE" || docker image inspect "$IMAGE_ID"; then
  echo 'Image still present locally (remove its other tags first): reproduction aborted' >&2
  exit 1
fi
docker pull --platform linux/amd64 "$IMAGE"
docker image inspect "$IMAGE" --format 'user={{.Config.User}} id={{.Id}} digests={{json .RepoDigests}}'
run_job "$RUN_ID-after"
AFTER=$(check_output "$RUN_ID-after")
printf '%s\n' "$AFTER"
test "$BEFORE" = "$AFTER"
printf '%s\n' 'PASS: identical rows and canonical content hash after image deletion and pull.'
# The exit trap removes only this run's database and network; output volumes are retained.
printf 'Retained evidence volumes: %s-before %s-after\n' "$RUN_ID" "$RUN_ID"
