# Infrastructure

La configuration L08 et les imports sont dans [`terraform/`](terraform/).
Le [compte rendu](../docs/infra.md) donne les ressources, leur raison d'être,
les plans réels et le test de dérive. [ADR-0008](../docs/adr/0008-remote-state.md)
documente le backend GCS versionné, ses lecteurs et la récupération de l'état.

Depuis `terraform/`, utiliser Terraform 1.13.5 et son lock :

```sh
terraform init -lockfile=readonly
terraform fmt -check -recursive
terraform validate
terraform plan
```

Authentification locale par `gcloud auth application-default login`. La CI
utilise `terraform init -backend=false` et ne reçoit aucun identifiant cloud.
Le backend existe déjà : ne pas le recréer et ne pas déplacer l'état partagé.
Les données sont protégées par `prevent_destroy` ; toujours relire le plan.

Le compte technique non adoptable est documenté, sans ressource fictive.
Les API et accès projet restent administrés par l'équipe enseignante.
L09 ajoute les [labels et coûts mesurés](../docs/costs.md#l09--attribution-et-optimisation-mesurée).
Le budget reste désactivé par défaut : son API n'est pas activée et le compte
étudiant ne peut pas l'activer. Voir `terraform/budget.tf` avant de demander
son activation à l'administrateur. L10 précise le moindre privilège.
