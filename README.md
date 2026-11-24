# Albert's Marketplace data platform: group repo

This repository is your group's data platform for **Albert's Marketplace**, the
fictional European beauty marketplace of the Data Engineering & Cloud
Infrastructure course (MSA-DAT09-02, Albert School).

It starts almost empty. Every lesson adds a layer on top of the previous one. By
the end of the course it holds the platform your group defends orally:
- ingestion
- a bronze, silver and gold warehouse
- containerised jobs and orchestration
- infrastructure as code
- cost controls and a security baseline

## Demo video

[Watch the project demo (step 11, 7 min 22, recorded on 23 November 2026)](https://thelio-my.sharepoint.com/:v:/r/personal/benjamin_caujolle_thelio_fr/_layouts/15/stream.aspx?id=%2Fpersonal%2Fbenjamin_caujolle_thelio_fr%2FDocuments%2FEnregistrements%2FPr%C3%A9sentation%20data%20engineering-20261123_175018-Enregistrement%20de%20la%20r%C3%A9union.mp4&nav=eyJyZWZlcnJhbEluZm8iOnsicmVmZXJyYWxBcHAiOiJTdHJlYW1XZWJBcHAiLCJyZWZlcnJhbFZpZXciOiJTaGFyZURpYWxvZy1MaW5rIiwicmVmZXJyYWxBcHBQbGF0Zm9ybSI6IldlYiIsInJlZmVycmFsTW9kZSI6InZpZXcifX0%3D&share=cQqxXf-hBFaWSqlYU5o3H7H1EgUDbnyoKRgFpzLjHJ8fyYqtNg)

The whole group backfills the missing day (16 September) with the Airflow DAG,
checks the new rows in BigQuery, then shows the daily report, the security
baseline and the Terraform plan.

| Time | Who | On screen |
|---|---|---|
| 0:00 | Antoine | The architecture diagram ([architecture.md](docs/architecture.md)) |
| 1:02 | Colin | 16 September before the run: 0 orders in bronze, 0 lines and 0 units in gold |
| 1:54 | Benjamin | The back-fill launched, then the DAG's five tasks and the dbt build log in Airflow |
| 3:07 | Colin | After the run: 208 orders in bronze, 364 lines and 1,201 units in gold; the raw files in the bronze bucket |
| 4:28 | Anthony | The daily report per country (1,201 units, €32,802.35) and the policy tags on `shipping_details` |
| 5:54 | Lenny | What we would do with one more month, then `terraform plan` |

## Team

| Name | GitHub | Role |
|---|---|---|
| Anthony Rascle | [@antotototototo18](https://github.com/antotototototo18) | Data Engineer |
| Antoine Rabeau | [@antorabo75](https://github.com/antorabo75) | Data Engineer |
| Colin Sibieude | [@csb123d](https://github.com/csb123d) | Data Engineer |
| Lenny Santus | [@lsantus-mines](https://github.com/lsantus-mines) | Data Analyst |
| Benjamin Caujolle | [@BenjaminAHS](https://github.com/BenjaminAHS) | Senior Data Engineer |

Technical responsibilities are agreed by the group as the course progresses.

### Review squads

Every pull request is reviewed inside its author's squad.

| Squad | Members | Reviews |
|---|---|---|
| A | Anthony ([@antotototototo18](https://github.com/antotototototo18)), Antoine ([@antorabo75](https://github.com/antorabo75)) | Anthony ↔ Antoine |
| B | Benjamin ([@BenjaminAHS](https://github.com/BenjaminAHS)), Lenny ([@lsantus-mines](https://github.com/lsantus-mines)) | Benjamin ↔ Lenny |
| Floating | Colin ([@csb123d](https://github.com/csb123d)) | Joins one squad per lesson, in turn |

| Lesson | L03 | L04 | L05 | L06 | L07 | L08 | L09 | L10 |
|---|---|---|---|---|---|---|---|---|
| Colin joins | A | B | A | B | A | B | A | B |

- A pull request is merged after **one approval** from the author's squad.
  Colin's review, when he is in the squad, is a second review, not a requirement.
- Colin's own pull requests are reviewed by the squad he joins that lesson.
- A pull request that changes the other squad's work (for example the
  architecture diagram or the data dictionary) also asks one member of that squad.
- Nobody merges their own pull request without an approval.

## Getting started

Accept the GitHub repository invitation, then follow [CONTRIBUTING.md](CONTRIBUTING.md)
to clone the project, create a branch and open your first pull request.

Pull requests to `main` and pushes to `main` or `antho` run the repository checks
in GitHub Actions, including the group-only contributor policy.
See [CI and deployment](docs/ci-cd.md) for the checks, local commands and the
deployment steps to add when the GCP platform is ready.

## Project progress

L01 deliverables: [data flows](docs/data-flows.md), [architecture decision](docs/adr/0001-target-architecture.md),
[target diagram](docs/architecture.md) and [daily-demand model](docs/model/star-daily-demand.md).
Proposed designs are distinguished from verified resources.

L03 ingestion writes into the group bucket `gs://data-engineering-i1-group6/bronze`:
see [ingestion/README.md](ingestion/README.md), the
[ingestion decision](docs/adr/0003-ingestion-modes.md) and the
[failure modes](docs/ingestion-failure-modes.md).

The L04 warehouse loads the working set into BigQuery (`group6_warehouse`):
see [warehouse/README.md](warehouse/README.md), the measured
[tuning and costs](docs/warehouse-tuning.md), the
[pricing decision](docs/adr/0004-warehouse-pricing.md) and the
[slow-query runbook](docs/runbooks/slow-query.md).

## L06 — Run the images on a new machine

You need Docker Desktop (running), a browser, a terminal with a POSIX shell,
and your own course GCP account with access to the private `dataeng` registry.
No host Python, dbt, Git or Google SDK is required. In GitHub, on branch
`main`, choose **Code → Download ZIP**, extract it and open a terminal in the
extracted repository. The course template remains restricted to course use.

On Windows, use Git Bash and run `export MSYS_NO_PATHCONV=1` first: otherwise
Git Bash rewrites container paths such as `/config` into `C:/Program Files/Git/config`.

Authenticate using the Google CLI inside a pinned container. These commands
store credentials in a Docker volume, outside the repository and images:

```sh
SDK=gcr.io/google.com/cloudsdktool/google-cloud-cli:546.0.0-stable@sha256:216b2307d4fafab08e259abe774ed7c29f3fef290418b2d0142d627c3184cff5
docker volume create group6-gcloud
docker run --rm --entrypoint sh -v group6-gcloud:/config "$SDK" \
  -c 'chown 10001:10001 /config'
docker run --rm -it --user 10001:10001 -e HOME=/tmp -e CLOUDSDK_CONFIG=/config \
  -v group6-gcloud:/config "$SDK" gcloud auth login --no-launch-browser
docker run --rm --user 10001:10001 -e HOME=/tmp -e CLOUDSDK_CONFIG=/config \
  -v group6-gcloud:/config "$SDK" gcloud auth print-access-token \
  | docker login -u oauth2accesstoken --password-stdin https://europe-west1-docker.pkg.dev
REGISTRY=europe-west1-docker.pkg.dev/data-engineering-i1/dataeng
TAG=20261103T-step6-01
docker pull --platform linux/amd64 "$REGISTRY/group6-ingestion:$TAG"
docker pull --platform linux/amd64 "$REGISTRY/group6-transform:$TAG"
```

To verify ingestion without production credentials or a live source:

```sh
sh scripts/reproduce-images.sh "$REGISTRY/group6-ingestion:$TAG"
```

Expected: `rows_written: 3`, then the same three rows and canonical content
hash twice, and `PASS`. This creates an isolated PostgreSQL fixture, deletes
the ingestion image locally, pulls it again and checks both outputs. Output
volumes are retained and named in the final line. No production table is used.
The actual transcript, push/pull digests and outstanding IAM limitation are
in [docs/reproduce.md](docs/reproduce.md).

For production GCS/BigQuery, create Application Default Credentials in the same
volume, using your own account:

```sh
docker run --rm -it --user 10001:10001 -e HOME=/tmp -e CLOUDSDK_CONFIG=/config \
  -v group6-gcloud:/config "$SDK" gcloud auth application-default login --no-launch-browser
```

Prepare an untracked `.env` from `.env.example` with `DATABASE_URL` and
`BRONZE_URI`. In containers, a database or Kafka broker running on the host
must use `host.docker.internal`, rather than `localhost`; use the actual host
port. Keep credentials out of shell history and Git. Run the SQL extractor:

```sh
docker run --rm --platform linux/amd64 --add-host host.docker.internal:host-gateway \
  --env-file .env -v group6-gcloud:/credentials:ro \
  -e GOOGLE_APPLICATION_CREDENTIALS=/credentials/application_default_credentials.json \
  "$REGISTRY/group6-ingestion:$TAG"
```

The ingestion entrypoint also runs the Kafka job: append
`ingestion.consume_clickstream --max-messages 200` to that command, after
configuring the Kafka variables described in [ingestion/README.md](ingestion/README.md).
Mount any `KAFKA_CLIENT_CONFIG` separately, read-only. Run dbt in your own datasets:

```sh
docker run --rm --platform linux/amd64 -v group6-gcloud:/credentials:ro \
  -e GOOGLE_APPLICATION_CREDENTIALS=/credentials/application_default_credentials.json \
  -e GCP_PROJECT_ID=data-engineering-i1 -e DBT_DATASET=group6_dev_lenny \
  "$REGISTRY/group6-transform:$TAG" build
```

Replace `group6_dev_lenny` with your own dataset prefix. The account needs
BigQuery job permission, bronze read access and permission to create/write the
development datasets. `dbt_utils` is already installed in the image. Docker
Desktop emulates `linux/amd64` on Apple Silicon. A failed pull with 401 means
the access token expired: repeat the token/login command; a 403 requires the
course administrator to grant registry read access.

To rebuild, run from the repository root, choose a new unused dated build tag,
and build both jobs with the root build context:

```sh
TAG=20261103T-step6-02
docker build --platform linux/amd64 -f ingestion/Dockerfile -t "$REGISTRY/group6-ingestion:$TAG" .
docker build --platform linux/amd64 -f transform/Dockerfile -t "$REGISTRY/group6-transform:$TAG" .
```

Publish only after verifying the tag is unused and recording both push digests.
See [ADR-0006](docs/adr/0006-image-tags.md) for rollback and retention.
The Docker-only instructions are prepared; a walkthrough by someone from another
group remains to be performed and recorded.

## How this repo grows

| Lesson | What your group adds | Where |
|---|---|---|
| L01 · Architecture decision frame | Data-flow matrix, first ADR, architecture diagram v1, star schema sketch | `docs/` |
| L02 · Object storage foundations | Bronze layer on Cloud Storage, data dictionary v1 | `docs/` |
| L03 · Batch, streaming, CDC | Ingestion pipelines | `ingestion/` |
| L04 · SQL warehouses | Warehouse tables, three costed queries | `docs/` |
| L05 · dbt and the medallion pattern | Silver and gold models, tests | `transform/` (planned) |
| L06 · Packaging data jobs | Two published images and ingestion reproduction; retention deletion blocked by IAM | `ingestion/`, `transform/`, [evidence](docs/reproduce.md) |
| L07 · Airflow | A daily DAG: extract a day, merge into bronze, dbt; alert, quality gate, back-fill | `orchestration/`, [docs](docs/orchestration.md) |
| L08 · Terraform | The platform as code, format and validation in CI, local plan | `infra/`, `.github/workflows/` |
| L09 · FinOps | Labels, a budget alert, one measured optimisation | `infra/`, `docs/` |
| L10 · Security and governance | Least-privilege access, PII redaction, data classification | `infra/`, `transform/`, `docs/` |

Starter files for later lessons arrive as **pull requests** opened by the
teaching team. Review and merge them like any other change.

## How we work

- **Every change goes through a pull request,** reviewed by another member
  before it reaches `main`.
- **One decision, one ADR** in `docs/adr/`. Every member writes at least one. At
  the oral defence, each of you defends a technical choice unprepared.
- **The commit history is graded.** Commit in small steps, with messages that
  say why.
- **Never commit secrets:** no `.env` files, no service-account keys.
  `.gitignore` blocks the usual names; it cannot catch everything.
- **Keep `docs/architecture.md` current.** It is the diagram you present at the
  defence.

## Layout

```
docs/
  architecture.md    target architecture and medallion layers
  data-flows.md      data-flow matrix
  adr/               architecture decision records (0001 to 0010)
  model/             dimensional model sketches
  runbooks/          failed run, slow query, erasure
  evidence/          logs and measurements, one folder per lesson
  presentation/      oral defence: deck (PPTX, PDF), script, demo video guide
ingestion/           from L03
warehouse/           from L04: BigQuery DDL and costed queries
transform/           from L05: the dbt project, as required by the project steps
dbt/                 template note pointing to transform/
orchestration/       from L07: the Airflow DAG
infra/               from L08: Terraform, IAM, lifecycle
scripts/             measurement, loading and governance scripts
tests/               unit tests run in CI
```

## Data

The source system is Albert's Marketplace's company repo (link on the course
site). Its data is synthetic or derived from public datasets; its licence and
attribution are stated there.

## Ownership

**No licence is granted for this repository.**
- **The template:** this README, the `docs/` templates and the folder structure
  remain the course author's intellectual property. Do not reuse them outside
  the course.
- **Your work:** what your group writes here belongs to your group.
