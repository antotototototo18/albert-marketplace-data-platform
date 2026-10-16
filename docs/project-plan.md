# Suivi des livrables du projet

Référence : les dix fichiers `Project Steps/L01.md` à `L10.md` fournis pour le
projet, avec les exercices individuels L01-L03. Ce suivi résume les consignes ;
les fichiers du cours restent la référence détaillée. État au 16 octobre 2026.

## Premier lot : L01

| Livrable demandé | Fichier | État |
|---|---|---|
| Équipe et comptes GitHub | [README](../README.md) | Renseignés ; rôles conservés depuis `main`. |
| Matrice des flux et trois questions | [data-flows.md](data-flows.md) | Rédigé pour relecture. |
| Choix parmi warehouse, lake, two-tier et lakehouse | [ADR-0001](adr/0001-target-architecture.md) | Proposed ; options, critères, décision et conséquences documentés. |
| Contexte, diagramme et garanties des couches | [architecture.md](architecture.md) | Cible L01 proposée, état vérifié séparé. |
| Processus, grain, dimensions et faits ML | [star-daily-demand.md](model/star-daily-demand.md) | Esquisse proposée ; limites du schéma source explicites. |

Le [profil reproductible](evidence/README.md) appuie le modèle sur l'archive
legacy réelle. Le notebook individuel L01 utilise une autre base de
démonstration ; ses colonnes ne sont pas supposées exister dans l'archive.

L01 ne sera terminé qu'après validation de ces choix, relecture d'une PR par
un autre membre et contribution effective de chaque membre. Chaque personne
pousse son propre travail sous son compte ; aucun commit n'est créé à sa place.

## Étapes suivantes

| Étape | Livrables et emplacements demandés | Preuves pour clôturer | État |
|---|---|---|---|
| L02 — Bronze | Bucket GCS en `europe-west1`, `docs/adr/0002-bronze-layout.md`, `docs/data-dictionary.md`, `infra/lifecycle.json`, `infra/iam.md`, `docs/costs.md`, diagramme actualisé | Parquet partitionné ; comparaison mesurée des layouts ; état lifecycle/IAM lu sur le bucket réel ; prix datés | Fait dans la PR #5 sur `gs://data-engineering-i1-group6`. |
| L03 — Ingestion | Connecteur et preuve de configuration dans `ingestion/`, extracteur incrémental, consumer, `clickstream.schema.json`, DLQ, `docs/ingestion-failure-modes.md`, ADR-0003, dictionnaire et diagramme | Sept streams requis ; exclusions des secrets à la source ; curseur durable, retries ; schéma validé ; événement invalide retrouvable et flux poursuivi ; limites testées | Fait dans la PR #6, à relire : extracteur, consumer, schéma, DLQ, connecteur et documents. Synchro Airbyte incomplète (mémoire Docker). |
| L04 — Warehouse | Tables natives BigQuery, SQL dans `warehouse/`, `docs/warehouse-tuning.md`, ADR-0004, `docs/runbooks/slow-query.md`, plafond de requête | Bytes processed avant/après, cache désactivé ; trois requêtes coûtées ; ratio de réduction de la vue ; plafond vu en échec | À réaliser. |
| L05 — dbt | Projet `transform/`, sources et fraîcheur, staging, marts, packages et lock, `docs/acceptance-criteria.md`, `docs/lineage.md`, ADR-0005 | `dbt build` depuis un clone propre ; grains et relations testés ; jointures sans fan-out ; seuils justifiés | À réaliser après L04. |
| L06 — Images | Dockerfiles `ingestion/` et `transform/`, `.dockerignore`, images versionnées, `docs/reproduce.md`, installation et ADR-0006 | Bases et dépendances fixées ; non-root ; aucun secret ; image supprimée puis récupérée ; digests concordants ; rétention exécutée | À réaliser après L05. |
| L07 — Orchestration | `orchestration/dags/`, `docs/orchestration.md`, `docs/runbooks/failed-run.md`, ADR-0007 | Mécanisme d'idempotence par tâche ; alerte reçue ; quality gate déclenché ; backfill avec prédiction et décompte | À réaliser après L06. |
| L08 — Terraform | `infra/terraform/`, backend GCS versionné, provider et lock, CI, `docs/infra.md`, ADR-0008 | Adoption des ressources existantes ; plan sans changement ; drift provoqué puis traité ; état absent de Git ; fmt/validate en CI | À réaliser après inventaire réel des ressources. |
| L09 — FinOps | Labels Terraform, budget, coûts par ressource/SKU, optimisation mesurée, `docs/costs.md`, ADR-0009 | Attribution expliquée ; alerte et destinataire ; limites du budget ; optimisation avant/après en unités | À réaliser après L08. |
| L10 — Gouvernance | `docs/governance.md`, classification et matrice, restrictions Terraform, `docs/runbooks/erasure.md`, ADR-0010 | Deux colonnes protégées avec refus vérifié ; droit réduit ; effacement testé, copies résiduelles et lacunes documentées | À réaliser après inventaire des données et des accès. |

## Reste à faire pour L03

1. Donner au moins 12 Go à Docker, relancer la stack, puis une synchro Airbyte
   complète ; mettre à jour `docs/evidence/l03-airbyte-sync.json`.
2. Remplacer la clé HMAC de compte utilisateur par celle d'un compte de service
   limité au bucket, si l'administrateur du projet en fournit un.
3. Faire relire la PR par un autre membre ; chaque membre doit avoir poussé au
   moins un commit.

## Conventions à conserver

- Travail de préparation sur `antho`, jamais de fusion directe dans `main`.
- Chaque lot passe par une PR relue par un autre membre ; attendre la CI verte.
- Un ADR par décision, sans réécriture rétroactive des décisions existantes.
- Les ressources appliquées, résultats mesurés et choix proposés sont distingués.
- Le modèle initial contient `dbt/`, mais les consignes L05-L06 demandent
  `transform/` : utiliser ce dernier pour le futur projet dbt, sans créer deux projets.
- Pour L08, la consigne détaillée demande `fmt`, `init -backend=false` et
  `validate` en CI, sans identifiants cloud. `terraform plan` reste local avec
  l'authentification du membre ; ne pas suivre l'ancienne mention du template
  qui plaçait `plan` en CI.
- Les archives, CSV, Parquet et sorties individuelles restent hors de Git.
  Seuls des éléments de preuve sans lignes personnelles sont publiés.
