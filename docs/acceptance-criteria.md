# Critères d'acceptation, sous forme de tests (L05)

Version du 3 novembre 2026. Premier `dbt build` complet le même jour :
**93 tests passent, 1 avertissement attendu (C12, les 6 produits sans nom),
0 erreur.** Gold contient 204 280 lignes de commande, 693 320 unités et
19 599 950,31 € sur 111 322 commandes réelles, identiques dans les deux faits.

Les critères viennent du besoin de l'équipe ML et
des contrôles listés en fin de [modèle en étoile](model/star-daily-demand.md),
plus ceux du sujet L05. Chaque critère renvoie au test qui le vérifie à
chaque `dbt build`. Ceux qui ne peuvent pas devenir un test sont listés à la
fin, avec la raison.

Les tests génériques sont déclarés dans les YAML de
[`staging`](../transform/models/staging/_staging.yml),
[`intermediate`](../transform/models/intermediate/_intermediate.yml) et
[`marts`](../transform/models/marts/_marts.yml) ; les tests singuliers sont dans
[`transform/tests/`](../transform/tests/). La fraîcheur est dans
[`sources.yml`](../transform/models/sources.yml) et ne tourne qu'avec
`dbt source freshness`.

## Critères testés

| # | Critère | Test | Où |
|---|---|---|---|
| C1 | **Le chiffre d'affaires n'est pas compté deux fois.** L'export écrit chaque commande deux fois ; une seule de chaque paire est gardée. | `assert_each_kept_order_has_one_twin` : chaque groupe de commandes identiques (acheteur, paiement, lignes) compte exactement deux fois plus de lignes exportées que de commandes gardées | [tests/](../transform/tests/assert_each_kept_order_has_one_twin.sql) |
| C2 | **Une ligne de commande n'apparaît qu'une fois** dans le fait. | `unique_combination_of_columns [order_id, p_id]` sur `fct_order_items` | [_marts.yml](../transform/models/marts/_marts.yml) |
| C3 | **La demande quotidienne n'a qu'une ligne par produit, pays et jour.** | `unique_combination_of_columns [p_id, country_code, order_date]` sur `fct_daily_demand` | [_marts.yml](../transform/models/marts/_marts.yml) |
| C4 | **Aucune jointure n'ajoute ni ne perd d'unités** entre les lignes des commandes réelles et gold. | `assert_units_conserved_into_gold` : même nombre de lignes et même `SUM(qty)` dans `fct_order_items` et `fct_daily_demand` | [tests/](../transform/tests/assert_units_conserved_into_gold.sql) |
| C5 | **Une commande n'a qu'un pays** : la jointure commandes-adresses ne multiplie rien. | `unique` sur `c_id` où `is_default` dans `stg_customer_shipping` ; `unique` sur `order_id` dans `int_orders__country` | [_staging.yml](../transform/models/staging/_staging.yml), [_intermediate.yml](../transform/models/intermediate/_intermediate.yml) |
| C6 | **Les avis ne multiplient pas les ventes** : ils sont agrégés au produit avant toute jointure. | `unique` sur `p_id` dans `int_product__ratings` et `dim_product` | [_intermediate.yml](../transform/models/intermediate/_intermediate.yml), [_marts.yml](../transform/models/marts/_marts.yml) |
| C7 | **Chaque ligne de commande a un produit.** | `relationships` de `fct_order_items.p_id` et `fct_daily_demand.p_id` vers `dim_product` | [_marts.yml](../transform/models/marts/_marts.yml) |
| C8 | **Chaque ligne a une date et un pays connus du schéma en étoile.** | `relationships` vers `dim_date.date_day` et `dim_country.country_code`, sur les deux faits | [_marts.yml](../transform/models/marts/_marts.yml) |
| C9 | **Les pays non résolus restent visibles**, sans perdre d'unités. | `accepted_values [DE, FR, IT, ES, NL, BE]` en `warn` sur `fct_order_items.country_code` : `UNKNOWN` passe, mais se voit | [_marts.yml](../transform/models/marts/_marts.yml) |
| C10 | **Les notes vont de 1 à 5.** | `accepted_values [1..5]` sur `stg_review.rating` ; `accepted_range 1-5` sur `avg_rating` | [_staging.yml](../transform/models/staging/_staging.yml), [_marts.yml](../transform/models/marts/_marts.yml) |
| C11 | **Les quantités sont strictement positives** et les prix ne sont pas négatifs. | `accepted_range min 1` sur `qty` et `units_sold` ; `min 0` sur `price_at_purchase` et `line_amount` ; prix catalogue `> 0` | [_staging.yml](../transform/models/staging/_staging.yml), [_marts.yml](../transform/models/marts/_marts.yml) |
| C12 | **Chaque produit a un nom**, après nettoyage des noms vides. | `not_null` sur `stg_product.p_name`, en **warn jusqu'à 6, erreur au-delà** : les 6 produits sans nom de l'export sont connus et visibles, un septième casse le build | [_staging.yml](../transform/models/staging/_staging.yml) |
| C13 | **Aucune colonne personnelle n'arrive en gold**, que l'équipe ML lit directement. | `assert_no_personal_columns_in_gold` : lit les colonnes réellement construites dans `INFORMATION_SCHEMA` | [tests/](../transform/tests/assert_no_personal_columns_in_gold.sql) |
| C14 | **Chaque pays d'adresse est l'un des six connus.** | `not_null` et `accepted_values` sur `stg_shipping_details.country_code` | [_staging.yml](../transform/models/staging/_staging.yml) |
| C15 | **Un événement clickstream rejoué n'est compté qu'une fois.** | `unique` sur `stg_clickstream.event_id` | [_staging.yml](../transform/models/staging/_staging.yml) |
| C16 | **Les données sont assez fraîches pour l'entraînement du matin.** | `freshness` sur chaque source chargée ; seuils et raisons ci-dessous | [sources.yml](../transform/models/sources.yml) |

## Seuils de fraîcheur

| Source | Warn | Error | Ce qui casse, et pour qui |
|---|---|---|---|
| `orders`, `order_items` | 26 h | 48 h | L'équipe ML entraîne chaque matin ; la synchro Airbyte passe toutes les 24 h. Un passage manqué avertit. Deux passages manqués, et le jeu d'entraînement contient une journée entière à demande nulle qui n'est pas réelle. |
| `product` | 72 h | 7 j | Gold n'en lit que le nom et la catégorie. Un produit vendu avant d'être au catalogue casse déjà le test `relationships` ; la fraîcheur n'a qu'à repérer un chargement mort en silence. |
| `review`, `product_reviews` | 7 j | 14 j | Ils ne servent qu'à `avg_rating` et `review_count`. Environ 100 avis par jour sur 111 322 : une semaine de retard ne change aucune décision. |
| `customer_shipping`, `shipping_details` | 7 j | 30 j | Ils ne servent qu'au pays approximé. Un nouvel acheteur sans adresse tombe en `UNKNOWN`, déjà signalé par C9. |
| `clickstream` | 2 h | 24 h | Le consumer écrit toutes les 5 s : deux heures sans fichier, c'est une panne. Aucun modèle gold ne le lit encore ; le coût d'un trou est le rejeu, possible tant que Kafka garde les événements (7 jours par défaut, non mesuré sur notre cluster). |

**Résultat du 3 novembre 2026** (`dbt source freshness`, 18 jours après le
chargement legacy du 16 octobre) : `ERROR STALE` sur `orders`, `order_items`,
`product`, `review`, `product_reviews` et `clickstream` (aucun événement depuis
deux jours) ; `WARN` seulement sur `customer_shipping` et `shipping_details`,
dont le seuil d'erreur est à 30 jours. C'est vrai : bronze est un export figé,
pas un chargement planifié, et le consumer clickstream ne tourne pas en continu. Les seuils sont ceux du fonctionnement visé (synchro Airbyte
quotidienne, ADR-0003) ; ils passeront quand L07 planifiera l'ingestion. Ne pas
les relâcher pour faire passer le contrôle.

## Critères qui ne sont pas des tests

| Critère | Pourquoi il n'est pas testé |
|---|---|
| **Les unités sont des ventes payées, nettes des annulations et des retours.** | La source n'a ni statut de paiement exploitable (`payment.status` vaut toujours `completed` et `payment` n'est pas chargée en BigQuery), ni annulation, et `returns` a 0 ligne. `units_sold` mesure donc des unités commandées, ce que disent la description du modèle et le [modèle en étoile](model/star-daily-demand.md). Aucun test ne peut vérifier une donnée qui n'existe pas. |
| **Le pays est celui de la livraison au moment de la commande.** | Le legacy ne garde pas l'adresse de chaque commande, seulement l'adresse par défaut actuelle de l'acheteur. Le pays est un proxy ; on peut tester qu'il est unique (C5), pas qu'il est historiquement juste. |
| **Une absence de ligne dans `fct_daily_demand` veut dire « zéro vente ».** | La table est creuse par choix. Un jour sans ligne peut aussi venir d'une partition source manquante ; seule la fraîcheur (C16) couvre une partie de ce cas. Une grille dense avec des zéros serait un autre modèle, à valider avec l'équipe ML. |
| **Le chiffre d'affaires correspond aux paiements encaissés.** | Le profil L02 montre que `payment.amount` égale `SUM(qty × price_at_purchase)` pour chaque commande, mais `payment` n'est pas déclarée en bronze BigQuery. Le test de réconciliation devient possible dès qu'elle l'est. |
| **Les 30 lignes à 0,00 € sont légitimes.** | Rien dans la source ne dit si ce sont des cadeaux ou des erreurs. Elles sont gardées, et le test autorise un prix nul (C11) ; la question est à poser au métier, pas à un test. |
| **La règle des jumeaux reste vraie pour le flux Airbyte.** | C1 décrit l'export legacy. Le jour où le flux Airbyte remplace l'export, si ses commandes ne sont plus doublées, C1 échouera : c'est voulu. Il faudra alors revoir `int_orders__deduplicated` et ce test ensemble, pas supprimer le test seul. |

## Comment les lancer

```bash
cd transform
dbt build --profiles-dir .            # modèles et tous les tests ci-dessus sauf C16
dbt source freshness --profiles-dir . # C16
```
