# L08 — La plateforme déclarée

Vérifié le 10 novembre 2026 depuis `Lenny`, avec le compte personnel de Lenny.
Le plan réel avant et après le test de dérive affiche **No changes. Your
infrastructure matches the configuration.** Aucun bucket ni dataset n'a été
recréé. La PR, sa CI et sa relecture restent à vérifier sur GitHub.

## Pourquoi chaque ressource existe

| Ressource | Pourquoi elle existe | Créée à la main ? |
|---|---|---|
| `google_storage_bucket.bronze` | Zone d'atterrissage et de rejeu L02-L03 ; lifecycle limité au legacy. | Oui en L02, déjà adoptée dans l'état distant ; pas recréée. |
| `google_bigquery_dataset.bronze` | Tables externes legacy et tables natives alimentées par Airflow. | Oui, adoptée. |
| `google_bigquery_dataset.warehouse` | Jeu natif typé et requêtes mesurées de L04. | Oui, adoptée. |
| `google_bigquery_dataset.silver` | Vues dbt de typage, déduplication et jointure. | Créée par dbt, adoptée. |
| `google_bigquery_dataset.gold` | Tables dbt des faits et dimensions pour l'analyse. | Créée par dbt, adoptée. |
| `google_bigquery_dataset_iam_member.writer["bronze_arabeau"]` | Antoine écrit les données bronze depuis les outils de la pipeline. | Oui, adoptée ; liaison conservée. |
| `google_bigquery_dataset_iam_member.writer["bronze_csibieude"]` | Colin écrit les données bronze. | Oui, adoptée ; liaison conservée. |
| `google_bigquery_dataset_iam_member.writer["warehouse_arabeau"]` | Antoine charge le warehouse. | Oui, adoptée ; liaison conservée. |
| `google_bigquery_dataset_iam_member.writer["warehouse_csibieude"]` | Colin charge le warehouse. | Oui, adoptée ; liaison conservée. |
| `google_bigquery_dataset_iam_member.bronze_reader_arabeau` | Lecture explicite du bronze pour Antoine ; redondante avec son rôle d'éditeur mais conservée pour préserver l'existant. | Oui, adoptée ; réduction à discuter en L10. |
| Bucket `data-engineering-i1-group6-tfstate` | État partagé, verrouillage GCS et historique de versions. | Oui, créé le 6 novembre hors de ce Terraform ; pas recréé. |
| Compte de service L02 | Identité technique souhaitée pour remplacer les identités humaines de la pipeline. | **Lacune : aucun compte adopté**, voir ci-dessous. |

## Adoption et limites

Le backend du groupe existait déjà, avec dix ressources dans son état.
Cette contribution conserve leurs adresses et leurs accès ; les blocs
`import` restent dans `infra/terraform/imports.tf` pour documenter l'adoption.
Ils sont sans effet sur les ressources déjà suivies. Aucun import initial
historique n'est attribué à cette contribution. Le plan nul vérifie ici leur
correspondance avec GCP. `prevent_destroy` protège le bucket et les datasets.

Le lifecycle réel lu le 10 novembre avait un seuil Nearline de **45 jours**
(modification du bucket datée du 6 novembre), contre 30 dans l'ancien JSON.
La configuration adopte 45, puis 90 jours pour Coldline et 365 pour Archive,
uniquement sous `bronze/legacy/`. Ce décalage préexistant n'est pas présenté
comme la dérive provoquée ci-dessous. Labels et descriptions ne sont pas
réinitialisés ; les descriptions bronze et warehouse reprennent celles de GCP.

Le compte `airbyte-bronze-writer@data-engineering-i1.iam.gserviceaccount.com`,
cité dans les anciennes notes, retourne `NOT_FOUND` lors du `describe`.
La liste des comptes est refusée avec `iam.serviceAccounts.list denied`.
La création était déjà interdite en L02 (`infra/iam.md`). Il est donc impossible
d'adopter honnêtement ce compte ou de conclure qu'aucun autre n'existe.
L'administrateur doit confirmer l'identité technique à utiliser avant d'ajouter
`google_service_account` et ses membres IAM au niveau des ressources.
Aucune clé de service n'est créée ni commise.

Les liaisons de pipeline existantes sur les datasets sont déclarées par membres
IAM, sans politique autoritaire. Les accès bronze GCS reposent encore sur les
liaisons legacy des rôles projet, observées à nouveau le 10 novembre ; aucun
nouvel accès n'est accordé par ce travail. Une fois le compte technique fourni,
déclarer ses droits avec `google_storage_bucket_iam_member` et
`google_bigquery_dataset_iam_member`. Aucun `google_project_iam_*` n'est utilisé.
Le lancement des jobs BigQuery et les API activées restent une dépendance
administrateur. Les datasets personnels sont hors périmètre ; tables et vues
restent gérées par les scripts SQL et dbt.

## État partagé et exécution

- Backend : `gs://data-engineering-i1-group6-tfstate/platform/default.tfstate`.
- Région : `europe-west1`, accès uniforme, accès public bloqué, versioning activé,
  suppression réversible de 7 jours.
- Terraform **1.13.5**, provider Google **8.10.0** exactement ; lock signé pour
  `darwin_arm64` et `linux_amd64`. Un provider 7.x ne peut pas lire le schéma
  d'identité de dataset déjà présent dans cet état ; ne pas le rétrograder.
- Politique et générations observées : [bucket](evidence/l08/05-backend-bucket.json),
  [IAM](evidence/l08/06-backend-iam.json), [versions](evidence/l08/07-state-versions.txt).
  Lecteurs et récupération sont détaillés dans [ADR-0008](adr/0008-remote-state.md).

```sh
gcloud auth login
gcloud auth application-default login
cd infra/terraform
terraform init -lockfile=readonly
terraform fmt -check -recursive
terraform validate
terraform plan -detailed-exitcode -no-color
```

Résultat du plan : code **0** avant le test et après restauration. Les sorties
intégrales sont [le plan initial](evidence/l08/01-baseline-plan.txt) et
[le plan final](evidence/l08/04-final-plan.txt). Aucun apply de création n'a été
nécessaire, puisque le backend et les ressources étaient déjà adoptés.

Pour reconstruire dans un projet neuf, amorcer un bucket d'état versionné avec
le compte autorisé, adapter le backend, le projet et les noms globalement uniques,
puis retirer les imports du projet actuel avant de revoir le plan de création.
La création du compte de service et les permissions projet nécessitent toujours
l'administration. Ce répertoire ne prétend donc pas reconstruire ces éléments
avec les droits étudiants actuels.

## Dérive provoquée, détectée et écrasée

Le 10 novembre, le plan initial était nul. Le test a changé uniquement l'âge
Nearline de **45 à 46 jours** hors Terraform, avec :

```sh
# Copie temporaire du lifecycle, seule la première condition passe à 46.
gcloud storage buckets update gs://data-engineering-i1-group6 \
  --lifecycle-file=/private/tmp/l08-drift-lifecycle.json
terraform plan -input=false -no-color -detailed-exitcode -out=drift.tfplan
```

Le plan a retourné **2** : zéro ajout, une modification sur place, zéro
suppression. Décision exécutée : **écraser la dérive**, car 46 est une valeur de
test sans justification métier. Le plan enregistré a été relu puis appliqué :
`terraform apply -input=false -no-color drift.tfplan`. Résultat : 0 ajout,
1 modification, 0 suppression ; [preuve](evidence/l08/03-drift-restore.txt).
Le plan final retourne **0** et `No changes`. Aucun fichier de données ni
aucune permission n'a été modifié. Une modification de lifecycle peut prendre
jusqu'à 24 heures à être prise en compte par GCS : ce test prouve la détection
de la configuration, pas une transition effective d'objets
([fonctionnement du lifecycle GCS](https://docs.cloud.google.com/storage/docs/lifecycle)).

En incident, ne pas annuler automatiquement une correction urgente : comprendre
sa raison, coordonner avec la personne qui l'a faite, puis adopter le changement
dans le HCL s'il est nécessaire. Faire relire et planifier la réconciliation
avant toute application. Une dérive de test ne justifie pas le retour aveugle
à une configuration devenue dangereuse en production.

Sortie intégrale du plan de dérive, également conservée dans
[`02-drift-plan.txt`](evidence/l08/02-drift-plan.txt) :

```text
google_bigquery_dataset.gold: Refreshing state... [id=projects/data-engineering-i1/datasets/group6_gold]
google_storage_bucket.bronze: Refreshing state... [id=data-engineering-i1-group6]
google_bigquery_dataset.warehouse: Refreshing state... [id=projects/data-engineering-i1/datasets/group6_warehouse]
google_bigquery_dataset.silver: Refreshing state... [id=projects/data-engineering-i1/datasets/group6_silver]
google_bigquery_dataset.bronze: Refreshing state... [id=projects/data-engineering-i1/datasets/group6_bronze]
google_bigquery_dataset_iam_member.bronze_reader_arabeau: Refreshing state... [id=projects/data-engineering-i1/datasets/group6_bronze/roles/bigquery.dataViewer/user:arabeau@albertschool.com]
google_bigquery_dataset_iam_member.writer["bronze_arabeau"]: Refreshing state... [id=projects/data-engineering-i1/datasets/group6_bronze/roles/bigquery.dataEditor/user:arabeau@albertschool.com]
google_bigquery_dataset_iam_member.writer["warehouse_csibieude"]: Refreshing state... [id=projects/data-engineering-i1/datasets/group6_warehouse/roles/bigquery.dataEditor/user:csibieude@albertschool.com]
google_bigquery_dataset_iam_member.writer["bronze_csibieude"]: Refreshing state... [id=projects/data-engineering-i1/datasets/group6_bronze/roles/bigquery.dataEditor/user:csibieude@albertschool.com]
google_bigquery_dataset_iam_member.writer["warehouse_arabeau"]: Refreshing state... [id=projects/data-engineering-i1/datasets/group6_warehouse/roles/bigquery.dataEditor/user:arabeau@albertschool.com]

Terraform used the selected providers to generate the following execution
plan. Resource actions are indicated with the following symbols:
  ~ update in-place

Terraform will perform the following actions:

  # google_storage_bucket.bronze will be updated in-place
  ~ resource "google_storage_bucket" "bronze" {
        id                          = "data-engineering-i1-group6"
        name                        = "data-engineering-i1-group6"
        # (18 unchanged attributes hidden)

      ~ lifecycle_rule {
          - condition {
              - age                                     = 46 -> null
              - days_since_custom_time                  = 0 -> null
              - days_since_noncurrent_time              = 0 -> null
              - matches_prefix                          = [
                  - "bronze/legacy/",
                ] -> null
              - matches_storage_class                   = [
                  - "STANDARD",
                ] -> null
              - matches_suffix                          = [] -> null
              - num_newer_versions                      = 0 -> null
              - send_age_if_zero                        = false -> null
              - send_days_since_custom_time_if_zero     = false -> null
              - send_days_since_noncurrent_time_if_zero = false -> null
              - send_num_newer_versions_if_zero         = false -> null
              - size_above_bytes                        = 0 -> null
              - size_below_bytes                        = 0 -> null
              - with_state                              = "ANY" -> null
                # (3 unchanged attributes hidden)
            }
          + condition {
              + age                    = 45
              + matches_prefix         = [
                  + "bronze/legacy/",
                ]
              + matches_storage_class  = [
                  + "STANDARD",
                ]
              + matches_suffix         = []
              + with_state             = (known after apply)
                # (3 unchanged attributes hidden)
            }

            # (1 unchanged block hidden)
        }

        # (4 unchanged blocks hidden)
    }

Plan: 0 to add, 1 to change, 0 to destroy.

─────────────────────────────────────────────────────────────────────────────

Saved the plan to: drift.tfplan

To perform exactly these actions, run the following command to apply:
    terraform apply "drift.tfplan"
```

## CI, historique et validation collective

Le workflow `.github/workflows/terraform.yml` s'exécute sur toute PR touchant
`infra/**` ou son propre fichier : `fmt -check -recursive`,
`init -backend=false -lockfile=readonly`, puis `validate`. Aucun secret cloud,
login ou plan en CI. Le contrôle existant des contributeurs reste inchangé.

Vérifications locales du 10 novembre : `terraform fmt -check -recursive`,
initialisation sans backend dans un `TF_DATA_DIR` vierge avec lock en lecture
seule, `terraform validate` et les huit contrôles `pre-commit` (dont actionlint)
réussis. Le dernier plan avec tous les blocs d'import retourne aussi zéro.

`.terraform/`, `*.tfstate`, `*.tfstate.*` et les plans binaires `*.tfplan` sont
ignorés. `git log --all -- infra/terraform/terraform.tfstate` ne retourne aucun
commit dans l'historique disponible. Aucun état ni identifiant n'est ajouté
à Git ; seuls des plans textuels sans données personnelles sont publiés.

La PR doit passer la CI et être relue par Benjamin (squad B) avant fusion.
Chaque membre doit pousser sa propre contribution : aucune signature ni aucun
commit n'est créé au nom d'un autre membre. Ces validations collectives et le
compte de service manquant restent des limites explicites à la clôture de L08.
