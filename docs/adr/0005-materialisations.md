# ADR-0005: Silver en vues, gold en tables

- **Status:** proposed - à relire par le groupe
- **Date:** 2026-11-03
- **Author:** Antoine Rabeau
- **Lesson:** L05

## Context

Le projet dbt de [`transform/`](../../transform/README.md) construit 16 modèles :
8 de staging et 3 intermédiaires (silver), 5 marts (gold). Dans le code, le choix
de matérialisation tient en quatre lignes de `dbt_project.yml`. Dans six mois, ce
sera la seule trace de la décision.

Les faits qui comptent :

| Grandeur | Valeur | Source |
|---|---|---|
| Lignes lues en bronze à chaque build | ~1,3 M sur 7 tables legacy ; 222 644 commandes, 408 560 lignes de commande | [Dictionnaire](../data-dictionary.md) |
| Taille du warehouse natif | 219,6 Mo, copies de mesure comprises | [warehouse-tuning.md](../warehouse-tuning.md) |
| Facturation | À la demande, $7.50 par Tio, **minimum de 10 Mio par table lue** ; plafond de 1 GiB par requête | [ADR-0004](0004-warehouse-pricing.md) |
| Rythme de la donnée | Synchro Airbyte toutes les 24 h ; l'équipe ML lit une fois par jour | [ADR-0003](0003-ingestion-modes.md), [flux](../data-flows.md) |
| Lecteurs de gold | L'équipe ML (`fct_daily_demand`), les analyses ad hoc du groupe | [Modèle en étoile](../model/star-daily-demand.md) |
| Bronze | Tables **externes** sur GCS : chaque lecture relit les Parquet | [02_bronze_external.sql](../../warehouse/02_bronze_external.sql) |

Le dernier point pèse : une vue silver sur bronze externe relit les fichiers
GCS à chaque requête. Le dédoublonnage des commandes (fenêtre sur 222 644
lignes et agrégation de chaînes sur 408 560) est le calcul le plus cher du
projet ; refait à chaque lecture de la demande, il serait payé par chaque
consommateur.

## Options considered

| Option | For | Against |
|---|---|---|
| **Tout en vues** | Toujours frais ; rien de stocké, rien à reconstruire | Chaque lecture de `fct_daily_demand` refait la chaîne entière : relecture GCS, dédoublonnage, jointures. Les tests aussi : ~80 requêtes qui recalculent chacune leur amont. Au minimum de 10 Mio par table lue, une requête gold touche 5 à 7 tables bronze. |
| **Tout en tables** | Lecture rapide et bon marché à chaque niveau | Silver périmé entre deux runs, comme gold, sans que personne ne lise silver en direct ; chaque couche stockée deux fois ; staging est une simple projection de bronze, la matérialiser ne fait que copier. |
| **Vues puis tables** (retenue) | Staging et intermédiaires restent une définition, sans copie ; gold est calculé une fois par build et lu au prix d'un scan de table, partitionné par mois et clusterisé par `p_id` comme en L04 | Il faut une étape de reconstruction ; gold n'est frais qu'à la date du dernier `dbt build` ; les tests qui lisent silver recalculent la vue |
| **Marts incrémentaux** | Reconstruction bon marché à grande échelle : seuls les jours nouveaux sont recalculés | Il faut définir « nouveau » et gérer les lignes tardives. Ici, c'est faux dès le départ : le jumeau d'une commande arrive jusqu'à 4 jours plus tard, et le dédoublonnage d'une commande dépend de ses voisines. Un filtre `order_date > max(order_date)` garderait des jumeaux. |

## Criteria

- **Coût de lecture pour le consommateur.** L'équipe ML lit gold chaque jour ;
  le scan d'une table partitionnée est le prix le plus bas. Vues seules : le
  plus cher. Tables : le moins cher.
- **Fraîcheur demandée.** Une fois par jour, pas à la minute. La
  limite des tables (frais au dernier run) ne coûte rien à ce rythme.
- **Coût de construction.** À notre volume, un build complet est dans le minimum
  de facturation : reconstruire gold en entier coûte moins de temps que
  d'écrire une logique incrémentale juste.
- **Justesse.** L'incrémental demande une définition de « nouveau » que nos
  jumeaux à 0-4 jours rendent fausse si on la fait simplement.
- **Stockage.** Ne dupliquer que ce qui est lu.

## Decision

Les modèles de `staging/` et `intermediate/` sont des **vues** dans
`group6_silver` ; les modèles de `marts/` sont des **tables** dans
`group6_gold`, reconstruites entièrement à chaque `dbt build`, les deux faits
partitionnés par mois sur `order_date` et clusterisés par `p_id`.

## Consequences

- Gold est aussi frais que le dernier build, pas que bronze. La fraîcheur de
  bronze est testée (`dbt source freshness`), celle de gold ne l'est pas :
  jusqu'à L07, un build oublié laisse gold périmé sans alerte.
- Les tests sur silver recalculent leurs vues depuis GCS ; c'est le poste de
  coût du build à surveiller s'il grandit.
- Lire silver en direct reste possible, mais coûte la relecture de bronze : ce
  n'est pas une interface de consommation.
- **Ce qui nous ferait changer d'avis :**
  - **si un build complet des marts dépassait une heure**, ou que ses octets
    traités approchaient le plafond de 1 GiB par requête, on passerait
    `fct_order_items` en **incrémental**, avec un `unique_key` `(order_id, p_id)`
    et une fenêtre de relecture d'au moins 4 jours pour rattraper les jumeaux
    tardifs. Le prix : une logique de fusion à tester, et un `--full-refresh`
    périodique pour corriger ce qu'elle aurait manqué ;
  - **si un consommateur avait besoin de données fraîches à la minute**, on
    sortirait ce besoin de dbt batch : une vue sur `stg_clickstream`, ou une vue
    matérialisée BigQuery comme `daily_demand` en L04, au prix de payer le calcul
    à chaque lecture ou de vivre avec les restrictions des vues matérialisées
    (pas de fonctions fenêtrées, donc pas de dédoublonnage dedans) ;
  - **si `int_orders__deduplicated` était lu par plusieurs marts** et que ses
    recalculs dominaient le coût du build, on le passerait en table, seule
    exception justifiée au silver en vues.
