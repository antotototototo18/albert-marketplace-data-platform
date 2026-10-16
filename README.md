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
| Anthony Rascle | [@anthonyrascle43-stack](https://github.com/anthonyrascle43-stack) | Data Engineer |
| Antoine Rabeau | [@antorabo75](https://github.com/antorabo75) | Data Engineer |
| Colin Sibieude | [@csb123d](https://github.com/csb123d) | Data Engineer |
| Lenny Santus | [@lsantus-mines](https://github.com/lsantus-mines) | Data Analyst |
| Benjamin Caujolle | [@BenjaminAHS](https://github.com/BenjaminAHS) | Senior Data Engineer |

Technical responsibilities are agreed by the group as the course progresses.

## Getting started

Accept the GitHub repository invitation, then follow [CONTRIBUTING.md](CONTRIBUTING.md)
to clone the project, create a branch and open your first pull request.

Pull requests to `main` and pushes to `main` or `antho` run the repository checks
in GitHub Actions, including the group-only contributor policy.
See [CI and deployment](docs/ci-cd.md) for the checks, local commands and the
deployment steps to add when the GCP platform is ready.

## Project progress

The first L01 deliverables are drafted for group review:
[data flows](docs/data-flows.md), [architecture decision](docs/adr/0001-target-architecture.md),
[target diagram](docs/architecture.md) and [daily-demand model](docs/model/star-daily-demand.md).
The [project plan](docs/project-plan.md) tracks the course requirements and the
evidence still needed. Proposed designs are distinguished from verified resources.

## How this repo grows

| Lesson | What your group adds | Where |
|---|---|---|
| L01 · Architecture decision frame | Data-flow matrix, first ADR, architecture diagram v1, star schema sketch | `docs/` |
| L02 · Object storage foundations | Bronze layer on Cloud Storage, data dictionary v1 | `docs/` |
| L03 · Batch, streaming, CDC | Ingestion pipelines | `ingestion/` |
| L04 · SQL warehouses | Warehouse tables, three costed queries | `docs/` |
| L05 · dbt and the medallion pattern | Silver and gold models, tests | `transform/` (planned) |
| L06 · Packaging data jobs | Dockerfiles for the ingestion job and dbt | `ingestion/`, `transform/` (planned) |
| L07 · Airflow | A scheduled DAG | `orchestration/` |
| L08 · Terraform | The platform as code, format and validation in CI, local plan | `infra/`, `.github/workflows/` |
| L09 · FinOps | Labels, a budget alert, one measured optimisation | `infra/`, `docs/` |
| L10 · Security and governance | Least-privilege access, PII redaction, data classification | `infra/`, `dbt/`, `docs/` |

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
  adr/               architecture decision records
  model/             dimensional model sketches
ingestion/           from L03
transform/           planned for L05, as required by the project steps
dbt/                 template note pointing to transform/
orchestration/       from L07
infra/               from L08
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
