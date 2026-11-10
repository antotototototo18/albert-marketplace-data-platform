# L06 — Reproduction réelle des images

Exécuté le 3 novembre 2026 sur Docker Desktop, hôte macOS ARM64, images jobs
`linux/amd64`. Registre privé :
`europe-west1-docker.pkg.dev/data-engineering-i1/dataeng`.

L'ingestion SQL et le consumer Kafka partagent l'image `group6-ingestion` ;
le runner dbt utilise `group6-transform`. La reproduction vérifie le véritable
extracteur SQL contre une base PostgreSQL jetable contenant trois lignes
figées. Aucun générateur de charge ni service de production n'intervient.
Deux volumes vierges empêchent le checkpoint du premier run de fausser le
second. Les noms de fichiers et dates d'ingestion varient ; toutes les colonnes
métier sont comparées exactement après tri par `order_id`, puis hachées.

La machine hôte est la même avant et après ; l'image locale est effectivement
supprimée, son absence est constatée par `docker images` et `docker image
inspect`, puis elle est récupérée du registre par tag. Il ne s'agit pas d'une
seconde machine physique. Le transcript ci-dessous est la sortie réelle de
[scripts/reproduce-images.sh](../scripts/reproduce-images.sh), erreurs comprises.

| Image, tag `20261103T-step6-01` | Digest du push | Digest du pull |
|---|---|---|
| ingestion | `sha256:45174dffd123b9a406624c736dfc6ac0b137ce26584b98d9271faa1b3003bfd7` | `sha256:45174dffd123b9a406624c736dfc6ac0b137ce26584b98d9271faa1b3003bfd7` |
| transform | `sha256:ea2d809cc22761514c0dcf3b440919cb1fbc2e4e788e3ed0bb41683b680ba7af` | Pas de cycle suppression/pull revendiqué pour dbt |

## Publication

Journaux conservés (couleurs ANSI et espaces finaux retirés pour lecture) dans [evidence/l06/](evidence/l06/).
Les deux commandes de push et leurs sorties réelles :

```text
$ docker push europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-ingestion:20261103T-step6-01
The push refers to repository [europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-ingestion]
84a2afebaf4d: Waiting
2e8ff2a71e95: Waiting
06e4a9c2b2a0: Waiting
44136fa355b3: Waiting
2e8ff2a71e95: Waiting
06e4a9c2b2a0: Waiting
44136fa355b3: Waiting
84a2afebaf4d: Waiting
2e8ff2a71e95: Waiting
06e4a9c2b2a0: Waiting
44136fa355b3: Waiting
84a2afebaf4d: Waiting
06e4a9c2b2a0: Waiting
44136fa355b3: Waiting
84a2afebaf4d: Waiting
2e8ff2a71e95: Waiting
06e4a9c2b2a0: Waiting
44136fa355b3: Waiting
84a2afebaf4d: Waiting
2e8ff2a71e95: Waiting
2e8ff2a71e95: Waiting
06e4a9c2b2a0: Waiting
44136fa355b3: Waiting
84a2afebaf4d: Waiting
44136fa355b3: Waiting
84a2afebaf4d: Waiting
2e8ff2a71e95: Waiting
06e4a9c2b2a0: Waiting
44136fa355b3: Waiting
84a2afebaf4d: Waiting
2e8ff2a71e95: Waiting
06e4a9c2b2a0: Waiting
06e4a9c2b2a0: Waiting
44136fa355b3: Waiting
06e4a9c2b2a0: Waiting
44136fa355b3: Waiting
f9f25941dc13: Waiting
f9f25941dc13: Waiting
dbeb2af0e7bd: Waiting
572ad4ee692b: Waiting
06e4a9c2b2a0: Pushed
44136fa355b3: Pushed
dbeb2af0e7bd: Waiting
572ad4ee692b: Waiting
572ad4ee692b: Pushed
ffa1dade770a: Waiting
2e8ff2a71e95: Pushed
79a701b02134: Waiting
3fb54130dc59: Waiting
dbeb2af0e7bd: Pushed
ffa1dade770a: Waiting
3fb54130dc59: Waiting
ffa1dade770a: Pushed
79a701b02134: Pushed
f9f25941dc13: Pushed
84a2afebaf4d: Pushed
3fb54130dc59: Pushed
20261103T-step6-01: digest: sha256:45174dffd123b9a406624c736dfc6ac0b137ce26584b98d9271faa1b3003bfd7 size: 856
```

```text
$ docker push europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-transform:20261103T-step6-01
The push refers to repository [europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-transform]
84a2afebaf4d: Waiting
44136fa355b3: Waiting
2e8ff2a71e95: Waiting
c4d068f08bcd: Waiting
2e8ff2a71e95: Waiting
c4d068f08bcd: Waiting
84a2afebaf4d: Waiting
44136fa355b3: Waiting
44136fa355b3: Waiting
2e8ff2a71e95: Waiting
c4d068f08bcd: Waiting
84a2afebaf4d: Waiting
2e8ff2a71e95: Waiting
c4d068f08bcd: Waiting
84a2afebaf4d: Waiting
44136fa355b3: Waiting
2e8ff2a71e95: Waiting
c4d068f08bcd: Waiting
84a2afebaf4d: Waiting
44136fa355b3: Waiting
c4d068f08bcd: Waiting
84a2afebaf4d: Waiting
44136fa355b3: Already exists
f9f25941dc13: Waiting
dbeb2af0e7bd: Waiting
2e8ff2a71e95: Layer already exists
7e5ebc76c5ec: Waiting
f9f25941dc13: Layer already exists
dbeb2af0e7bd: Layer already exists
d4c7b1db0ae7: Waiting
e6fce87820e9: Waiting
84a2afebaf4d: Layer already exists
d4c7b1db0ae7: Waiting
e6fce87820e9: Waiting
7e5ebc76c5ec: Waiting
a80c6792ff22: Waiting
d4c7b1db0ae7: Waiting
c4d068f08bcd: Pushed
a80c6792ff22: Waiting
422c2c7136e6: Waiting
e6fce87820e9: Pushed
6afe3f2b0049: Waiting
7e5ebc76c5ec: Pushed
6afe3f2b0049: Waiting
6afe3f2b0049: Waiting
a80c6792ff22: Pushed
422c2c7136e6: Pushed
6afe3f2b0049: Pushed
d4c7b1db0ae7: Pushed
20261103T-step6-01: digest: sha256:ea2d809cc22761514c0dcf3b440919cb1fbc2e4e788e3ed0bb41683b680ba7af size: 856
```

## Exécution, suppression, téléchargement et comparaison

L'alias local de construction `group6-ingestion:20261103-candidate` a été retiré
avant ce test. Les conteneurs du job sont lancés avec `--rm` : aucun conteneur
arrêté ne conserve une référence à l'image lors de `docker rmi`.

```text
$ sh scripts/reproduce-images.sh europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-ingestion:20261103T-step6-01
+ docker network create l06-20261103175934-13741
39970c0656ce6b0b3f121432ea5cfedc54b9827dfe2293dceeb9c13d6fea2319
+ docker run -d --name l06-20261103175934-13741-db --network l06-20261103175934-13741 --network-alias fixture -e POSTGRES_HOST_AUTH_METHOD=trust postgres:17.6-bookworm@sha256:f3bd19c606e442c3d7bdfa8002e03fe260a1023351e0ea4598032022b68dd6e3
Unable to find image 'postgres:17.6-bookworm@sha256:f3bd19c606e442c3d7bdfa8002e03fe260a1023351e0ea4598032022b68dd6e3' locally
docker.io/library/postgres@sha256:f3bd19c606e442c3d7bdfa8002e03fe260a1023351e0ea4598032022b68dd6e3: Pulling from library/postgres
162e72af9357: Pulling fs layer
43297198b981: Pulling fs layer
359be260dcae: Pulling fs layer
f6184d0dc2fb: Pulling fs layer
a5d51e77f69f: Pulling fs layer
0f6c9876a1a2: Pulling fs layer
f6080d7cc0c1: Pulling fs layer
752fc1bcb5e0: Pulling fs layer
aa186232e6d4: Pulling fs layer
553e8b781e3b: Pulling fs layer
68ae6031e0df: Pulling fs layer
38723cf27dcc: Pulling fs layer
33049f381174: Pulling fs layer
9119c7c41821: Pulling fs layer
43297198b981: Download complete
9119c7c41821: Download complete
a5d51e77f69f: Download complete
752fc1bcb5e0: Download complete
f6080d7cc0c1: Download complete
f6184d0dc2fb: Download complete
aa186232e6d4: Download complete
68ae6031e0df: Download complete
38723cf27dcc: Download complete
359be260dcae: Download complete
0f6c9876a1a2: Download complete
33049f381174: Download complete
921639da2aa1: Download complete
1c4ddb9c7541: Download complete
162e72af9357: Download complete
359be260dcae: Pull complete
162e72af9357: Pull complete
a5d51e77f69f: Pull complete
f6184d0dc2fb: Pull complete
0f6c9876a1a2: Pull complete
752fc1bcb5e0: Pull complete
f6080d7cc0c1: Pull complete
aa186232e6d4: Pull complete
553e8b781e3b: Download complete
68ae6031e0df: Pull complete
38723cf27dcc: Pull complete
33049f381174: Pull complete
553e8b781e3b: Pull complete
43297198b981: Pull complete
9119c7c41821: Pull complete
Digest: sha256:f3bd19c606e442c3d7bdfa8002e03fe260a1023351e0ea4598032022b68dd6e3
Status: Downloaded newer image for postgres@sha256:f3bd19c606e442c3d7bdfa8002e03fe260a1023351e0ea4598032022b68dd6e3
7d0155032277ed093b13d8ec9d34f3b80973cf5a416ce962de120fa308f696a8
+ ready=0
+ '[' 0 -lt 60 ']'
+ docker exec l06-20261103175934-13741-db pg_isready -U postgres
/var/run/postgresql:5432 - no response
+ ready=1
+ sleep 1
+ '[' 1 -lt 60 ']'
+ docker exec l06-20261103175934-13741-db pg_isready -U postgres
/var/run/postgresql:5432 - no response
+ ready=2
+ sleep 1
+ '[' 2 -lt 60 ']'
+ docker exec l06-20261103175934-13741-db pg_isready -U postgres
/var/run/postgresql:5432 - accepting connections
+ break
+ docker exec -i l06-20261103175934-13741-db psql -v ON_ERROR_STOP=1 -U postgres
CREATE TABLE
INSERT 0 3
 frozen_input_rows
-------------------
                 3
(1 row)

+ docker image inspect europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-ingestion:20261103T-step6-01 --format 'user={{.Config.User}} id={{.Id}} digests={{json .RepoDigests}}'
user=10001:10001 id=sha256:45174dffd123b9a406624c736dfc6ac0b137ce26584b98d9271faa1b3003bfd7 digests=["europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-ingestion@sha256:45174dffd123b9a406624c736dfc6ac0b137ce26584b98d9271faa1b3003bfd7"]
+ run_job l06-20261103175934-13741-before
+ docker volume create l06-20261103175934-13741-before
l06-20261103175934-13741-before
+ docker run --rm --network l06-20261103175934-13741 -v l06-20261103175934-13741-before:/output -e DATABASE_URL=postgresql://postgres@fixture/postgres -e BRONZE_URI=/output europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-ingestion:20261103T-step6-01
WARNING: The requested image's platform (linux/amd64) does not match the detected host platform (linux/arm64/v8) and no specific platform was requested
{"rows_written": 3, "last_order_id": 3}
++ check_output l06-20261103175934-13741-before
++ docker run --rm --network none -v l06-20261103175934-13741-before:/output:ro --entrypoint python europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-ingestion:20261103T-step6-01 -c '
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
WARNING: The requested image's platform (linux/amd64) does not match the detected host platform (linux/arm64/v8) and no specific platform was requested
+ BEFORE='[{"buyer_id":"fixture-a","discount_id":null,"order_date":"2026-10-01","order_id":1,"payment_id":101},{"buyer_id":"fixture-b","discount_id":7,"order_date":"2026-10-02","order_id":2,"payment_id":102},{"buyer_id":"fixture-a","discount_id":null,"order_date":"2026-10-03","order_id":3,"payment_id":103}]
rows= 3 sha256= a08db0b2503b95e3fd39f918e7e2bbaf35b68de7c485f65936638a08b0928e89'
+ printf '%s\n' '[{"buyer_id":"fixture-a","discount_id":null,"order_date":"2026-10-01","order_id":1,"payment_id":101},{"buyer_id":"fixture-b","discount_id":7,"order_date":"2026-10-02","order_id":2,"payment_id":102},{"buyer_id":"fixture-a","discount_id":null,"order_date":"2026-10-03","order_id":3,"payment_id":103}]
rows= 3 sha256= a08db0b2503b95e3fd39f918e7e2bbaf35b68de7c485f65936638a08b0928e89'
[{"buyer_id":"fixture-a","discount_id":null,"order_date":"2026-10-01","order_id":1,"payment_id":101},{"buyer_id":"fixture-b","discount_id":7,"order_date":"2026-10-02","order_id":2,"payment_id":102},{"buyer_id":"fixture-a","discount_id":null,"order_date":"2026-10-03","order_id":3,"payment_id":103}]
rows= 3 sha256= a08db0b2503b95e3fd39f918e7e2bbaf35b68de7c485f65936638a08b0928e89
+ docker rmi europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-ingestion:20261103T-step6-01
Untagged: europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-ingestion:20261103T-step6-01
Deleted: sha256:45174dffd123b9a406624c736dfc6ac0b137ce26584b98d9271faa1b3003bfd7
+ docker images europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-ingestion:20261103T-step6-01
IMAGE   ID             DISK USAGE   CONTENT SIZE   EXTRA
+ docker image inspect europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-ingestion:20261103T-step6-01
[]
Error response from daemon: No such image: europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-ingestion:20261103T-step6-01
+ docker pull --platform linux/amd64 europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-ingestion:20261103T-step6-01
20261103T-step6-01: Pulling from data-engineering-i1/dataeng/group6-ingestion
ffa1dade770a: Pulling fs layer
f9f25941dc13: Pulling fs layer
dbeb2af0e7bd: Pulling fs layer
572ad4ee692b: Pulling fs layer
3fb54130dc59: Pulling fs layer
79a701b02134: Pulling fs layer
84a2afebaf4d: Pulling fs layer
2e8ff2a71e95: Pulling fs layer
572ad4ee692b: Already exists
3fb54130dc59: Already exists
79a701b02134: Already exists
ffa1dade770a: Already exists
2e8ff2a71e95: Already exists
f9f25941dc13: Already exists
44136fa355b3: Already exists
dbeb2af0e7bd: Already exists
84a2afebaf4d: Already exists
06e4a9c2b2a0: Download complete
84a2afebaf4d: Pull complete
2e8ff2a71e95: Pull complete
572ad4ee692b: Pull complete
79a701b02134: Pull complete
f9f25941dc13: Pull complete
dbeb2af0e7bd: Pull complete
3fb54130dc59: Pull complete
ffa1dade770a: Pull complete
Digest: sha256:45174dffd123b9a406624c736dfc6ac0b137ce26584b98d9271faa1b3003bfd7
Status: Downloaded newer image for europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-ingestion:20261103T-step6-01
europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-ingestion:20261103T-step6-01
+ docker image inspect europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-ingestion:20261103T-step6-01 --format 'user={{.Config.User}} id={{.Id}} digests={{json .RepoDigests}}'
user=10001:10001 id=sha256:45174dffd123b9a406624c736dfc6ac0b137ce26584b98d9271faa1b3003bfd7 digests=["europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-ingestion@sha256:45174dffd123b9a406624c736dfc6ac0b137ce26584b98d9271faa1b3003bfd7"]
+ run_job l06-20261103175934-13741-after
+ docker volume create l06-20261103175934-13741-after
l06-20261103175934-13741-after
+ docker run --rm --network l06-20261103175934-13741 -v l06-20261103175934-13741-after:/output -e DATABASE_URL=postgresql://postgres@fixture/postgres -e BRONZE_URI=/output europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-ingestion:20261103T-step6-01
WARNING: The requested image's platform (linux/amd64) does not match the detected host platform (linux/arm64/v8) and no specific platform was requested
{"rows_written": 3, "last_order_id": 3}
++ check_output l06-20261103175934-13741-after
++ docker run --rm --network none -v l06-20261103175934-13741-after:/output:ro --entrypoint python europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-ingestion:20261103T-step6-01 -c '
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
WARNING: The requested image's platform (linux/amd64) does not match the detected host platform (linux/arm64/v8) and no specific platform was requested
+ AFTER='[{"buyer_id":"fixture-a","discount_id":null,"order_date":"2026-10-01","order_id":1,"payment_id":101},{"buyer_id":"fixture-b","discount_id":7,"order_date":"2026-10-02","order_id":2,"payment_id":102},{"buyer_id":"fixture-a","discount_id":null,"order_date":"2026-10-03","order_id":3,"payment_id":103}]
rows= 3 sha256= a08db0b2503b95e3fd39f918e7e2bbaf35b68de7c485f65936638a08b0928e89'
+ printf '%s\n' '[{"buyer_id":"fixture-a","discount_id":null,"order_date":"2026-10-01","order_id":1,"payment_id":101},{"buyer_id":"fixture-b","discount_id":7,"order_date":"2026-10-02","order_id":2,"payment_id":102},{"buyer_id":"fixture-a","discount_id":null,"order_date":"2026-10-03","order_id":3,"payment_id":103}]
rows= 3 sha256= a08db0b2503b95e3fd39f918e7e2bbaf35b68de7c485f65936638a08b0928e89'
[{"buyer_id":"fixture-a","discount_id":null,"order_date":"2026-10-01","order_id":1,"payment_id":101},{"buyer_id":"fixture-b","discount_id":7,"order_date":"2026-10-02","order_id":2,"payment_id":102},{"buyer_id":"fixture-a","discount_id":null,"order_date":"2026-10-03","order_id":3,"payment_id":103}]
rows= 3 sha256= a08db0b2503b95e3fd39f918e7e2bbaf35b68de7c485f65936638a08b0928e89
+ test '[{"buyer_id":"fixture-a","discount_id":null,"order_date":"2026-10-01","order_id":1,"payment_id":101},{"buyer_id":"fixture-b","discount_id":7,"order_date":"2026-10-02","order_id":2,"payment_id":102},{"buyer_id":"fixture-a","discount_id":null,"order_date":"2026-10-03","order_id":3,"payment_id":103}]
rows= 3 sha256= a08db0b2503b95e3fd39f918e7e2bbaf35b68de7c485f65936638a08b0928e89' = '[{"buyer_id":"fixture-a","discount_id":null,"order_date":"2026-10-01","order_id":1,"payment_id":101},{"buyer_id":"fixture-b","discount_id":7,"order_date":"2026-10-02","order_id":2,"payment_id":102},{"buyer_id":"fixture-a","discount_id":null,"order_date":"2026-10-03","order_id":3,"payment_id":103}]
rows= 3 sha256= a08db0b2503b95e3fd39f918e7e2bbaf35b68de7c485f65936638a08b0928e89'
+ printf '%s\n' 'PASS: identical rows and canonical content hash after image deletion and pull.'
PASS: identical rows and canonical content hash after image deletion and pull.
+ docker stop l06-20261103175934-13741-db
l06-20261103175934-13741-db
+ docker rm l06-20261103175934-13741-db
l06-20261103175934-13741-db
+ docker network rm l06-20261103175934-13741
l06-20261103175934-13741
+ printf 'Retained evidence volumes: %s-before %s-after\n' l06-20261103175934-13741 l06-20261103175934-13741
Retained evidence volumes: l06-20261103175934-13741-before l06-20261103175934-13741-after
```

Le résultat des deux exécutions est `{"rows_written": 3, "last_order_id": 3}`.
Le contenu normalisé a le même hash :
`a08db0b2503b95e3fd39f918e7e2bbaf35b68de7c485f65936638a08b0928e89`.
Le digest d'image du pull correspond exactement à celui du push ci-dessus.
Les volumes de sortie sont conservés, avec leurs noms dans le transcript.

## Vérifications complémentaires

La base des deux Dockerfiles est
`python:3.12.12-slim-bookworm@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c`.
Les dépendances directes et transitives sont fixées dans les deux
`requirements.lock`. Le build amd64 a exécuté `pip check` dans chaque image.
La liste d'inclusion `.dockerignore` exclut structurellement les fichiers locaux,
ADC, `.env` et environnements virtuels du contexte.
Le [contrôle de l'image dbt](evidence/l06/transform-check.log) confirme aussi
l'UID 10001 et l'absence de dépendances incompatibles. Le chemin `.env` fourni
par `dbt_utils/integration_tests` est un répertoire d'exemples publics du paquet
amont : champs cloud vides et connexion PostgreSQL de test locale. Il ne contient
aucun identifiant du projet. Aucun fichier `.env` local n'a été envoyé au build.

```text
$ docker run --rm --platform linux/amd64 --network none --entrypoint sh europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-ingestion:20261103T-step6-01 -c 'id; python -m pip check; python -m ingestion.extract_orders --help; python -m ingestion.consume_clickstream --help; test ! -e /app/.env; test ! -e /app/.venv; find /app /home/job -type f'
uid=10001(job) gid=10001(job) groups=10001(job)
No broken requirements found.
usage: extract_orders.py [-h] [--batch-size BATCH_SIZE] [--attempts ATTEMPTS]
                         [--interval-seconds INTERVAL_SECONDS]

Append new orders, at least once for visible increasing IDs; updates/deletes
are not captured.

options:
  -h, --help            show this help message and exit
  --batch-size BATCH_SIZE
  --attempts ATTEMPTS
  --interval-seconds INTERVAL_SECONDS
usage: consume_clickstream.py [-h] [--max-messages MAX_MESSAGES]

Deliver Kafka events at least once by persisting valid rows and rejects before
committing offsets.

options:
  -h, --help            show this help message and exit
  --max-messages MAX_MESSAGES
/app/ingestion/export_airbyte_catalog.py
/app/ingestion/storage.py
/app/ingestion/check_airbyte_export.py
/app/ingestion/extract_orders.py
/app/ingestion/clickstream.schema.json
/app/ingestion/__init__.py
/app/ingestion/consume_clickstream.py
/home/job/.bashrc
/home/job/.bash_logout
/home/job/.profile
```

```text
$ docker run --rm --platform linux/amd64 --network none europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-transform:20261103T-step6-01 parse --no-partial-parse
18:03:52  Running with dbt=1.11.16
18:03:57  Registered adapter: bigquery=1.11.3
18:04:05  Performance info: /app/transform/target/perf_info.json
```

Les [35 tests existants](evidence/l06/unit-tests.log) ont été exécutés dans
un environnement Python 3.12 jetable avec les dépendances d'ingestion. Résultat :
`Ran 35 tests`, `OK`. Le build dbt complet est conservé dans
[transform-build.log](evidence/l06/transform-build.log). Aucun `dbt build` en
production ni validation de données BigQuery n'est revendiqué ici.
Les huit contrôles [pre-commit](evidence/l06/precommit.log), dont actionlint et
la détection de clés privées, ont également réussi.

## Rétention : tentative réelle refusée par IAM

La politique est définie dans [ADR-0006](adr/0006-image-tags.md).
Une image vide distincte, `group6-retention-probe`, a été créée et publiée pour
appliquer la clause de suppression immédiate des images jetables. Elle ne partage
pas le digest d'une release protégée. Publication, tentative de suppression et
inventaire après tentative :

```text
$ docker push europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-retention-probe:20261103-step6-01
The push refers to repository [europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-retention-probe]
20261103-step6-01: digest: sha256:6c7c0a1e426a85518e42cff23f724c8f457acfe73b61e03c35d3a490fcb48a1a size: 288
```

```text
$ gcloud artifacts docker images delete europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-retention-probe:20261103-step6-01 --delete-tags --quiet
Digests:
- europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-retention-probe@sha256:6c7c0a1e426a85518e42cff23f724c8f457acfe73b61e03c35d3a490fcb48a1a

Tags:
- europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-retention-probe:20261103-step6-01
ERROR: (gcloud.artifacts.docker.images.delete) PERMISSION_DENIED: Permission 'artifactregistry.tags.delete' denied on resource '//artifactregistry.googleapis.com/projects/data-engineering-i1/locations/europe-west1/repositories/dataeng/packages/group6-retention-probe/tags/20261103-step6-01' (or it may not exist). Remediate access with this Troubleshooter URL or share it with your administrator - https://console.cloud.google.com/iam-admin/troubleshooter/summary;errorId=CiQwMWExYTI5Mi04NDdlLTcxZTYtOGExYS01ZjIzOWVhOTEzMjQSf3Byb2plY3RzL2RhdGEtZW5naW5lZXJpbmctaTEvbG9jYXRpb25zL2V1cm9wZS13ZXN0MS9yZXBvc2l0b3JpZXMvZGF0YWVuZy9wYWNrYWdlcy9ncm91cDYtcmV0ZW50aW9uLXByb2JlL3RhZ3MvMjAyNjExMDMtc3RlcDYtMDE%3D . This command is authenticated as lsantus@albertschool.com which is the active account specified by the [core/account] property.
- '@type': type.googleapis.com/google.rpc.ErrorInfo
  domain: artifactregistry.googleapis.com
  metadata:
    error_info_id: CiQwMWExYTI5Mi04NDdlLTcxZTYtOGExYS01ZjIzOWVhOTEzMjQSf3Byb2plY3RzL2RhdGEtZW5naW5lZXJpbmctaTEvbG9jYXRpb25zL2V1cm9wZS13ZXN0MS9yZXBvc2l0b3JpZXMvZGF0YWVuZy9wYWNrYWdlcy9ncm91cDYtcmV0ZW50aW9uLXByb2JlL3RhZ3MvMjAyNjExMDMtc3RlcDYtMDE=
    permission: artifactregistry.tags.delete
    resource: projects/data-engineering-i1/locations/europe-west1/repositories/dataeng/packages/group6-retention-probe/tags/20261103-step6-01
    troubleshooter_url: https://console.cloud.google.com/iam-admin/troubleshooter/summary;errorId=CiQwMWExYTI5Mi04NDdlLTcxZTYtOGExYS01ZjIzOWVhOTEzMjQSf3Byb2plY3RzL2RhdGEtZW5naW5lZXJpbmctaTEvbG9jYXRpb25zL2V1cm9wZS13ZXN0MS9yZXBvc2l0b3JpZXMvZGF0YWVuZy9wYWNrYWdlcy9ncm91cDYtcmV0ZW50aW9uLXByb2JlL3RhZ3MvMjAyNjExMDMtc3RlcDYtMDE%3D
  reason: IAM_PERMISSION_DENIED
```

```text
$ gcloud artifacts docker images list europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-retention-probe --include-tags --format='table(version,tags)'
Listing items under project data-engineering-i1, location europe-west1, repository dataeng.

DIGEST                                                                   TAGS
sha256:6c7c0a1e426a85518e42cff23f724c8f457acfe73b61e03c35d3a490fcb48a1a  20261103-step6-01
```

**Le livrable 7 n'est pas validé** : l'image jetable reste dans le registre.
Un administrateur du cours doit exécuter la même suppression ou accorder les
permissions appropriées, puis conserver le nouveau transcript et l'inventaire
vide. Le compte ne peut pas non plus créer un dépôt à tags immuables ; le dépôt
partagé reste mutable et les déploiements doivent référencer les digests.
Aucun contrôle IAM n'a été modifié ou contourné.

## Essai par un autre groupe

Le README contient un parcours Docker seul, avec authentification via une image
CLI Google fixée par digest. Le test par une personne d'un autre groupe reste à
organiser ; aucun résultat d'un tel essai n'est inventé.

## L07 : images exécutées par le DAG

Reconstruites le 6 novembre 2026 sur Docker Desktop, hôte Windows x86-64, même
Dockerfiles, plateforme `linux/amd64`. Raison : l'image d'ingestion embarque
`ingestion/extract_interval.py` (extraction d'un intervalle fourni par le run) ;
l'image dbt embarque les sources repointées sur les tables bronze natives et le
test C1 limité à l'export legacy. Les tags existants ont été listés avant le push
(seul `20261103T-step6-01` existait) ; aucun tag n'a été réutilisé (ADR-0006).

| Image, tag `20261106T-step7-01` | Digest du push |
|---|---|
| ingestion | `sha256:d273c33b9e0e3d23914927f48e8630cd83afc68f4952b1ad10857cbe2e23b3b4` |
| transform | `sha256:e05e888f638b1dc0b9e1b435e6201bda792705b3b3b6d6587e183061439d38a2` |

Le DAG [`group6_marketplace_daily`](../orchestration/dags/group6_marketplace_daily.py)
référence les deux images par `tag@digest`. Les tâches sont lancées par le Docker
de l'hôte, qui doit déjà détenir les images : `docker pull` par digest avant le
premier run (le worker Airflow n'a pas les identifiants du registre).
