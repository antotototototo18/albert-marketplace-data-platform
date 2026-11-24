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
in GitHub Actions, including the group-only contributor policy. Since
10 November the jobs no longer start because of a GitHub Actions billing block;
the same checks can be run locally.
See [CI and deployment](docs/ci-cd.md) for the checks, local commands and the
deployment steps.

## Oral defence

Everything for the defence is in [docs/presentation/](docs/presentation/README.md):
the deck ([PPTX](docs/presentation/group6-pitch.pptx), [PDF](docs/presentation/group6-pitch.pdf)),
the [speaker script](docs/presentation/SCRIPT.md) with who answers which question,
and the [demo video guide](docs/presentation/VIDEO.md).

## Project progress

Proposed designs are distinguished from verified resources. Each step links to
its decision record and its evidence.

| Lesson | Result | Read |
|---|---|---|
| L01 | Two-tier target: Cloud Storage for bronze, BigQuery for silver and gold | [data flows](docs/data-flows.md), [architecture](docs/architecture.md), [ADR-0001](docs/adr/0001-target-architecture.md), [daily-demand model](docs/model/star-daily-demand.md) |
| L02 | Legacy export landed in bronze as Parquet; secrets excluded at the source | [data dictionary](docs/data-dictionary.md), [ADR-0002](docs/adr/0002-bronze-layout.md) |
| L03 | Batch, incremental and Kafka ingestion into `gs://data-engineering-i1-group6/bronze`; full Airbyte sync still partial | [ingestion/](ingestion/README.md), [ADR-0003](docs/adr/0003-ingestion-modes.md), [failure modes](docs/ingestion-failure-modes.md) |
| L04 | BigQuery warehouse `group6_warehouse`, measured partitioning, 1 GiB cap per query | [warehouse/](warehouse/README.md), [tuning and costs](docs/warehouse-tuning.md), [ADR-0004](docs/adr/0004-warehouse-pricing.md), [slow-query runbook](docs/runbooks/slow-query.md) |
| L05 | dbt silver views and gold tables, tested | [transform/](transform/README.md), [ADR-0005](docs/adr/0005-materialisations.md), [lineage](docs/lineage.md), [acceptance criteria](docs/acceptance-criteria.md) |
| L06 | Two private images, reproduction checked after delete and pull | [reproduce](docs/reproduce.md), [ADR-0006](docs/adr/0006-image-tags.md) |
| L07 | Daily Airflow DAG, idempotent writes, quality gate, back-fill | [orchestration](docs/orchestration.md), [ADR-0007](docs/adr/0007-idempotency.md), [failed-run runbook](docs/runbooks/failed-run.md) |
| L08 | Platform as code with remote state; drift detected and recovered | [infra/](infra/README.md), [infra notes](docs/infra.md), [ADR-0008](docs/adr/0008-remote-state.md) |
| L09 | Cost labels and one measured optimisation; budget alert written but not active (billing budgets API disabled) | [costs](docs/costs.md), [ADR-0009](docs/adr/0009-cost-attribution.md) |
| L10 | Data classification, policy tags, tested erasure; narrower access written in Terraform, not yet applied | [governance](docs/governance.md), [ADR-0010](docs/adr/0010-data-classification.md), [erasure runbook](docs/runbooks/erasure.md) |

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
| L04 · SQL warehouses | Warehouse tables, three costed queries | `warehouse/`, `docs/` |
| L05 · dbt and the medallion pattern | Silver and gold models, tests | `transform/` |
| L06 · Packaging data jobs | Two published images and ingestion reproduction; retention deletion blocked by IAM | `ingestion/`, `transform/`, [evidence](docs/reproduce.md) |
| L07 · Airflow | A daily DAG: extract a day, merge into bronze, dbt; alert, quality gate, back-fill | `orchestration/`, [docs](docs/orchestration.md) |
| L08 · Terraform | The platform as code, format and validation in CI, local plan | `infra/`, `.github/workflows/` |
| L09 · FinOps | Labels and one measured optimisation; budget alert written, not active | `infra/`, `docs/` |
| L10 · Security and governance | PII redaction, data classification, erasure; least-privilege grant written, not yet applied | `infra/`, `transform/`, `docs/` |

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
.github/             CI workflows, pull request and issue templates
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
