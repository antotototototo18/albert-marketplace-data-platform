# transform: dbt, silver et gold (L05)

Pour exécuter dbt sans Python sur l'hôte, utiliser l'image L06 et les commandes
du [README racine](../README.md#l06--run-the-images-on-a-new-machine).
Les dépendances Python transitives de l'image sont fixées dans `requirements.lock`.

Le projet dbt du groupe. Il lit bronze (`group6_bronze`, tables externes sur
GCS), construit silver en vues dans `group6_silver` et gold en tables dans
`group6_gold` ([ADR-0005](../docs/adr/0005-materialisations.md)).

## Construire depuis un clone propre

Prérequis : Python 3.12+, et un compte membre du projet `data-engineering-i1`
avec accès en lecture à `group6_bronze` et en écriture sur le projet.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r transform/requirements.txt
gcloud auth application-default login     # le profil lit ces identifiants (oauth)

cd transform
dbt deps  --profiles-dir .               # installe dbt_utils, version fixée par package-lock.yml
dbt build --profiles-dir .               # modèles et tests, dans l'ordre du graphe
dbt source freshness --profiles-dir .    # fraîcheur de bronze
```

`profiles.yml` est versionné : il ne contient aucun secret. Deux variables
d'environnement facultatives :

| Variable | Défaut | Rôle |
|---|---|---|
| `GCP_PROJECT_ID` | `data-engineering-i1` | Projet BigQuery |
| `DBT_DATASET` | `group6` | Préfixe des datasets : `<préfixe>_silver`, `<préfixe>_gold`. Mettre par exemple `group6_dev_antoine` pour construire sans écraser les tables du groupe. |

Chaque requête est plafonnée à 1 GiB facturé (`maximum_bytes_billed`,
[ADR-0004](../docs/adr/0004-warehouse-pricing.md)).

## Organisation

| Dossier | Couche | Règle |
|---|---|---|
| `models/sources.yml` | Bronze | Déclaré, jamais construit ; fraîcheur et raisons des seuils |
| `models/staging/` | Silver, vues | Une source par modèle, aucune jointure. Chaque en-tête nomme le défaut corrigé. |
| `models/intermediate/` | Silver, vues | Jointures et règles métier : jumeaux, pays, notes |
| `models/marts/` | Gold, tables | Faits et dimensions, grain déclaré en anglais dans `description` et testé |
| `tests/` | — | Tests singuliers des critères d'acceptation |

Critères d'acceptation : [docs/acceptance-criteria.md](../docs/acceptance-criteria.md).
Lignage : [docs/lineage.md](../docs/lineage.md).

## Où chaque défaut du dictionnaire est traité

Un défaut est corrigé à un seul endroit, ou laissé tel quel avec une raison.
Sources : [dictionnaire de données](../docs/data-dictionary.md) et profil de
l'export du 16/10/2026.

| Défaut | Traité dans | Comment |
|---|---|---|
| `unnamed_0`, index de l'export, sur toutes les tables sauf `order_items` | Chaque `stg_*` concerné | Non sélectionné |
| Toutes les colonnes en `STRING` en bronze | Chaque `stg_*` | Cast au type observé |
| `p_id`, `zip`, `phone` commencent parfois par `0` | `stg_product`, `stg_order_items` | `p_id` reste `STRING` ; `zip` et `phone` ne sont pas lus |
| `price` jusqu'à 20 décimales | `stg_product` | `BIGNUMERIC`, pas `NUMERIC` |
| `orders.discount_id` vide sur toutes les lignes | `stg_orders` | Supprimée |
| **Chaque commande exportée deux fois** (jumeau à 0-4 jours) | `int_orders__deduplicated` | Une seule de chaque paire gardée ; c'est une jointure avec les lignes, donc pas du staging |
| 6 `p_name` vides | `stg_product` | `NULL` après `TRIM` ; test `not_null` en warn jusqu'à 6 |
| `r_desc` : 14 vides, 110 espaces seuls, 6 non nettoyés | `stg_review` | `TRIM` puis `NULL` si vide |
| `title` : 10 avec espaces en bord | `stg_review` | `TRIM` |
| `seller_product_flag` toujours `S`, non documenté | `stg_review` | Supprimée |
| `is_default` en texte `0`/`1` | `stg_customer_shipping` | `BOOL` |
| Pays en toutes lettres | `stg_shipping_details` | Code ISO à deux lettres |
| Données personnelles directes (`street_address`, `phone`) | `stg_shipping_details` | Non sélectionnées ; `city` et `zip` non plus |
| Clickstream livré au moins une fois | `stg_clickstream` | Une ligne par `event_id`, première reçue |
| Horodatages clickstream en texte | `stg_clickstream` | `TIMESTAMP` |
| 30 lignes à `price_at_purchase = 0.00` | Laissé tel quel | Unités réellement commandées ; rien ne dit si c'est un cadeau ou une erreur |
| `qty` de 1 à 12, pas 1 à 9 comme dans le dictionnaire v1 | Laissé tel quel | Pas un défaut de la donnée ; dictionnaire corrigé |
| `p_desc` est du JSON sérialisé | Laissé tel quel | Gold ne le lit pas |
| Tables non lues par gold : `customer`, `buyer`, `seller`, `payment`, `payment_details`, `customer_payment`, `subscription`, `shipment`, `carrier`, `category`, `product_images`, `seller_products`, `seller_reviews`, `review_images`, `wishlist_item` ; tables vides : `cart`, `cart_items`, `returns`, `daily_deals`, `discount` | Hors périmètre | Pas déclarées en bronze BigQuery (L04) et pas nécessaires au modèle ; leurs défauts seront traités quand un modèle les lira. Les données personnelles de `customer` et `payment_details` relèvent de L10. |
| Flux Airbyte et extracteur (`bronze/airbyte/`, `bronze/manual/`) | Hors périmètre | Pas encore de table externe ; silver devra choisir un chemin par table (dictionnaire, Flux L03) |
