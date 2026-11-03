# Lignage dbt (L05)

Graphe des modèles de [`transform/`](../transform/README.md), relevé dans
`transform/target/manifest.json` (`dbt parse`, dbt 1.11). Il se régénère avec :

```bash
cd transform
dbt docs generate --profiles-dir .
dbt docs serve --profiles-dir .   # onglet « Lineage graph »
```

```mermaid
flowchart LR
  classDef bronze fill:#cd7f32,color:#fff,stroke:#8a5520
  classDef silver fill:#c0c0c0,color:#000,stroke:#808080
  classDef gold fill:#d4af37,color:#000,stroke:#9c7c1c

  subgraph B["Bronze : sources.yml (group6_bronze)"]
    s_orders[(orders)]
    s_items[(order_items)]
    s_product[(product)]
    s_review[(review)]
    s_pr[(product_reviews)]
    s_cs[(customer_shipping)]
    s_sd[(shipping_details)]
    s_click[(clickstream)]
  end

  subgraph S["Silver : vues (group6_silver)"]
    stg_orders
    stg_order_items
    stg_product
    stg_review
    stg_product_reviews
    stg_customer_shipping
    stg_shipping_details
    stg_clickstream
    int_orders__deduplicated
    int_orders__country
    int_product__ratings
  end

  subgraph G["Gold : tables (group6_gold)"]
    fct_order_items
    fct_daily_demand
    dim_product
    dim_date
    dim_country
  end

  s_orders --> stg_orders
  s_items --> stg_order_items
  s_product --> stg_product
  s_review --> stg_review
  s_pr --> stg_product_reviews
  s_cs --> stg_customer_shipping
  s_sd --> stg_shipping_details
  s_click --> stg_clickstream

  stg_orders --> int_orders__deduplicated
  stg_order_items --> int_orders__deduplicated
  int_orders__deduplicated --> int_orders__country
  stg_customer_shipping --> int_orders__country
  stg_shipping_details --> int_orders__country
  stg_product_reviews --> int_product__ratings
  stg_review --> int_product__ratings

  stg_order_items --> fct_order_items
  int_orders__country --> fct_order_items
  fct_order_items --> fct_daily_demand
  stg_product --> dim_product
  int_product__ratings --> dim_product
  int_orders__deduplicated --> dim_date
  stg_shipping_details --> dim_country

  class s_orders,s_items,s_product,s_review,s_pr,s_cs,s_sd,s_click bronze
  class stg_orders,stg_order_items,stg_product,stg_review,stg_product_reviews,stg_customer_shipping,stg_shipping_details,stg_clickstream,int_orders__deduplicated,int_orders__country,int_product__ratings silver
  class fct_order_items,fct_daily_demand,dim_product,dim_date,dim_country gold
```

`stg_clickstream` n'alimente encore aucun modèle gold : il est déclaré pour sa
fraîcheur et son dédoublonnage, en attendant un besoin de consommation.

## Si la source la plus en amont changeait de forme demain

La source dont tout dépend est **`orders`** : elle alimente
`int_orders__deduplicated`, donc les deux faits, `dim_date` et la totalité de
la mesure de demande. Si sa forme changeait (le passage du legacy au flux
Airbyte typé est le cas prévu), il faudrait regarder, dans l'ordre :
`stg_orders`, seul endroit où ses colonnes sont nommées et typées ; la règle de
`int_orders__deduplicated`, qui suppose que l'export écrit chaque commande deux
fois, une hypothèse que le flux Airbyte ne vérifiera probablement pas, et que
le test `assert_each_kept_order_has_one_twin` signalera dès la première
commande non dédoublée ; puis `int_orders__country` et `fct_order_items`, dont
le grain `(order_id, p_id)` et le test de conservation des unités disent si la
nouvelle forme multiplie ou perd des lignes. `dbt ls --select stg_orders+`
donne la liste exacte des modèles et tests à relancer.
