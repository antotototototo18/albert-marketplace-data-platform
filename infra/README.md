# Infrastructure

Arrives in **L08 · Terraform**: your group's cloud resources declared as code,
with remote state. The detailed L08 project step requires format checks and
validation in CI (`terraform init -backend=false`), without cloud credentials.
Run `terraform plan` locally using your own authenticated session.

- **Before L08,** the resources you create by hand in L02-L07 are listed in
  `docs/`.
- **From L08,** changes go through code, not the console.
- **L09** adds labels and budgets; **L10** tightens access.
