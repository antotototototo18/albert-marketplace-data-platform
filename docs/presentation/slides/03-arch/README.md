# Slide 3 — Architecture

**Qui parle :** Colin · **Durée :** 1 min 15

## Message clé

Deux étages sur GCP en `europe-west1` : un bronze dans Cloud Storage qu'on peut
rejouer, puis BigQuery pour silver et gold.

## À dire

- De gauche à droite : les sources (PostgreSQL, clickstream Kafka, archive CSV
  legacy), le bronze, BigQuery, puis ce qui fait tourner l'ensemble.
- Le bronze garde les données brutes autorisées, pour pouvoir tout reconstruire.
- BigQuery contient les tables natives, les vues silver et les tables gold
  construites par dbt.
- Airflow lance la pipeline chaque jour ; Docker et Terraform la rendent
  reproductible.
- Les mots de passe et les données de carte (`pwd`, `card_no`, `cvv`)
  n'arrivent jamais dans le bronze.

## Si on nous demande

- Schéma complet, ce qui est construit et ce qui reste cible : [architecture.md](../../../architecture.md).
- Pourquoi deux étages : [ADR-0001](../../../adr/0001-target-architecture.md).
