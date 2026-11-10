# Warehouse BigQuery (L04)

SQL du warehouse du groupe, projet `data-engineering-i1`, région `europe-west1`.
Les décisions et les mesures sont dans [docs/warehouse-tuning.md](../docs/warehouse-tuning.md),
le choix du compteur dans [ADR-0004](../docs/adr/0004-warehouse-pricing.md).

| Fichier | Rôle |
|---|---|
| [01_datasets.sql](01_datasets.sql) | Crée `group6_bronze` (tables externes) et `group6_warehouse` (tables natives) |
| [02_bronze_external.sql](02_bronze_external.sql) | Tables externes sur les sept tables legacy et sur le clickstream |
| [03_native_load.sql](03_native_load.sql) | Charge le jeu de travail en tables natives typées ; copies `*_untuned` de référence |
| [04_native_tuned.sql](04_native_tuned.sql) | Tables réglées, sous les noms lus par les consommateurs |
| [05_daily_demand.sql](05_daily_demand.sql) | Vue matérialisée de demande quotidienne par produit |
| [queries/](queries/) | Q1 à Q3, sondes de réglage et ratio de réduction ; `${table}` est remplacé par le script de mesure |
| [bigqueryrc.example](bigqueryrc.example) | Plafond de 1 GiB par défaut pour le CLI `bq`, à copier en `~/.bigqueryrc` |
| [requirements.txt](requirements.txt) | Client BigQuery des scripts |

Ordre d'exécution, depuis la racine du dépôt :

```sh
python scripts/run_sql.py warehouse/01_datasets.sql
python scripts/run_sql.py warehouse/02_bronze_external.sql
python scripts/run_sql.py warehouse/03_native_load.sql
python scripts/run_sql.py warehouse/04_native_tuned.sql
python scripts/measure_warehouse.py docs/evidence/l04-warehouse-measurements.json --create-view
```

Chaque fichier est idempotent (`CREATE OR REPLACE`, `IF NOT EXISTS`). Le dernier
script crée la vue matérialisée après les mesures de réglage.

`orders_untuned`, `order_items_untuned`, `review_untuned`, `product_reviews_untuned`
et `order_items_day` ne servent qu'aux mesures. Ils peuvent être supprimés une
fois les chiffres relus ; il faudra les recréer pour re-mesurer.
