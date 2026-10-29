# Runbook : une requête qui prenait 2 secondes en prend 2 minutes

Pour un membre du groupe qui n'a pas construit le warehouse. Suivre les étapes
dans l'ordre : les premières sont les plus rapides et les plus probables.
S'arrêter dès qu'une étape trouve la cause.

Tout se passe dans la console BigQuery,
<https://console.cloud.google.com/bigquery>, projet `data-engineering-i1`.

## Avant de commencer (2 minutes)

1. En bas de l'éditeur, ouvrir **Job history**, puis **Personal history**
   (ou **Project history** si la requête a été lancée par quelqu'un d'autre).
2. Retrouver **deux jobs** de la même requête : le lent, et un rapide de
   référence. Noter leurs deux *Job ID*.
3. Pas de job de référence ? Utiliser les [valeurs de référence](#valeurs-de-référence)
   en bas de cette page.

## Étape 1 : le « avant » était-il réel ? (1 minute)

Ouvrir le job **rapide**, onglet **Job information**.

- **Bytes processed = 0 B**, ou la mention du cache : il a été servi par le
  cache. Il n'a jamais été rapide : il n'a rien calculé.
- Pour confirmer : *More → Query settings*, décocher **Use cached results**,
  **Save**, relancer la version « rapide ». Si elle est maintenant aussi lente,
  **rien n'est cassé. Arrêter ici** et le dire à la personne qui a signalé le problème.

Écarte : toute comparaison avec un résultat en cache. Si le job rapide a bien
traité des octets, passer à l'étape 2.

## Étape 2 : les octets traités ont-ils bondi ? (2 minutes)

Comparer **Bytes processed** (onglet **Job information**) du job lent et du job
de référence.

- **Multipliés** (par 3, 10, 30...) : la requête a **perdu son filtre de
  partition**. Lire la clause `WHERE` sur `order_date` :
  - le filtre a disparu ;
  - la date vient d'une sous-requête ou d'une jointure
    (`WHERE order_date IN (SELECT ...)`) : le moteur ne sait pas quelles
    partitions ouvrir avant d'exécuter ;
  - la colonne est enveloppée dans une fonction que le moteur ne sait pas
    inverser, comme `FORMAT_DATE('%Y', order_date) = '2026'`.
    (`EXTRACT`, `DATE_TRUNC` et une comparaison directe élaguent, eux.)
- **Vérifier la correction sans rien payer :** corriger le `WHERE` et lire
  l'estimation en haut à droite de l'éditeur (*This query will process...*)
  avant de cliquer sur **Run**. Elle doit revenir à la valeur de référence.

Écarte, si les octets n'ont pas bougé : un problème d'élagage. Le temps est
passé ailleurs : étape 3.

## Étape 3 : la table a-t-elle dépassé son grain ? (3 minutes)

Lancer :

```sql
SELECT table_name, COUNT(*) AS partitions,
       CAST(ROUND(AVG(total_logical_bytes)) AS INT64) AS avg_bytes,
       SUM(total_rows) AS total_rows
FROM `data-engineering-i1.group6_warehouse.INFORMATION_SCHEMA.PARTITIONS`
WHERE table_name IN ('orders', 'order_items')
GROUP BY table_name;
```

- **Nombre de partitions qui a sauté** (au-delà d'une par mois depuis
  septembre 2023), ou une partition `__NULL__` : un rechargement a écrit des
  dates fausses ou vides. Escalader (voir plus bas), ne pas recharger soi-même.
- **Taille moyenne multipliée** : la table a grossi et le grain mensuel ne
  convient plus. Ce n'est pas une panne mais une décision à reprendre, avec de
  nouvelles mesures et un nouvel ADR.

Écarte, si ces chiffres sont proches des valeurs de référence : la croissance
de la table. Passer à l'étape 4.

## Étape 4 : une étape du plan domine-t-elle ? (3 minutes)

Ouvrir le job lent, onglet **Execution details** (pas *Execution graph*).

- Chaque ligne est une étape (*S00: Input*, *S03: Join+*...). Trouver celle
  dont la barre de durée est **très au-dessus de ses voisines** (trois fois la
  suivante ou plus).
- Noter son type : *Join*, *Aggregate*, *Sort*... C'est elle que les étapes 5
  et 6 examinent.

Écarte, si toutes les étapes ont grandi dans les mêmes proportions : un
problème localisé dans le plan. Aller directement à l'étape 7.

## Étape 5 : du skew dans cette étape ? (2 minutes)

Toujours dans **Execution details**, déplier l'étape dominante et comparer le
temps de calcul **Max** au temps **Avg** des workers.

- **Max très au-dessus de Avg** (plus de trois fois) : du **skew**. Une clé
  porte beaucoup plus de lignes que les autres, et un seul worker travaille
  pendant que les autres attendent. Chez nous, les premiers suspects sont le
  best-seller `B0BM4GX6TT` (1 376 lignes de commande) et l'acheteur le plus
  actif (230 commandes, contre 2,2 en moyenne), ou une clé vide
  apparue après un rechargement (aucune au 26 octobre 2026).
- **Ne pas** chercher plus de puissance : plus de machines n'aident pas quand
  une seule a tout le travail. Ce qui aide : filtrer avant la jointure, agréger
  avant de joindre, isoler la clé chaude.

Écarte, si Max et Avg sont proches : le skew. Étape 6.

## Étape 6 : la donnée a-t-elle changé de forme ? (3 minutes)

Dans l'étape dominante, comparer **Records read** et **Records written** du job
lent et du job de référence.

- **Une jointure qui écrit beaucoup plus de lignes qu'elle n'en lit :** une
  table qui devait donner une ligne par clé en donne plusieurs (fan-out). Sur
  Q2, c'est le filtre `is_default = 1` sur `customer_shipping` qui l'empêche ;
  vérifier qu'il est toujours là, et qu'aucun client n'a deux adresses par défaut.
- **Les mêmes requêtes lisent beaucoup plus de lignes :** comparer l'onglet
  **Details** de chaque table aux comptes de référence. Une table qui a doublé
  sans raison a été rechargée en double.

Écarte, si les lignes lues et écrites sont stables : un changement des données.
Étape 7.

## Étape 7 : la requête attend-elle au lieu de travailler ? (1 minute)

Dans **Execution details**, si ce sont les barres **Wait** qui dominent et que
le temps de slot total (**Job information**, *Slot milliseconds*) est proche de
la référence, la requête attend des slots. Le projet est à la demande et
partagé avec les autres groupes du cours ([ADR-0004](../adr/0004-warehouse-pricing.md)) :
la requête n'a rien. Relancer plus tard.

## Quand arrêter et escalader

Arrêter et escalader, **sans** relever le plafond `maximum_bytes_billed` et
sans recréer de table la nuit, dès que :

- les sept étapes n'ont rien trouvé ;
- la correction demande de recharger ou de repartitionner une table (étapes 3 et 6) ;
- une requête légitime est refusée par le plafond de 1 GiB ;
- 30 minutes sont passées.

Escalader = ouvrir une issue GitHub avec le modèle **Task** contenant les deux
*Job ID*, l'étape atteinte et ce qu'elle a montré, puis prévenir le groupe.
Une donnée rechargée en double ou avec des dates fausses relève de l'ingestion
([ADR-0003](../adr/0003-ingestion-modes.md)) ; un grain ou un plafond à revoir
relève du warehouse ([warehouse-tuning.md](../warehouse-tuning.md)).

## Ce que chaque étape révèle

| Ce qui ne va vraiment pas | Ce qui le trahit | Étape |
|---|---|---|
| On compare à un résultat en cache | Le job « rapide » affiche 0 octet traité | 1 |
| La requête a perdu son filtre de partition | Les octets traités ont bondi ; le filtre a disparu ou passe par une fonction, une sous-requête ou une jointure | 2 |
| La table a dépassé son grain | Le nombre de partitions ou leur taille moyenne a changé | 3 |
| Une étape domine | Sa durée est très au-dessus de ses voisines | 4 |
| Skew | Dans cette étape, le worker le plus lent est très au-dessus de la moyenne | 5 |
| La donnée a changé de forme | Lignes lues et écrites ont changé pour la même requête | 6 |
| Rien, la requête attend des slots | Les barres *Wait* dominent, le temps de slot n'a pas changé | 7 |

## Valeurs de référence

Mesurées le 26 octobre 2026, cache désactivé
([preuve](../evidence/l04-warehouse-measurements.json)). Elles vieillissent :
après un rechargement, relancer `scripts/measure_warehouse.py` et mettre ce
tableau à jour.

| Requête, tables réglées | Octets traités | Durée | Slot ms |
|---|---:|---:|---:|
| [Q1](../../warehouse/queries/q1_monthly_revenue.sql) CA mensuel | 5 622 040 | 0,11 s | 213 |
| [Q2](../../warehouse/queries/q2_daily_demand_by_country.sql) Demande par pays, 28 jours | 13 377 983 | 0,15 s | 123 |
| [Q3](../../warehouse/queries/q3_product_ratings.sql) Notes produits | 4 007 592 | 0,12 s | 56 |

| Table | Lignes | Partitions | Taille moyenne d'une partition |
|---|---:|---:|---:|
| `orders` | 222 644 | 37 | 382 131 o |
| `order_items` | 408 560 | 37 | 574 192 o |
| `review` | 111 322 | | |
| `product_reviews` | 111 322 | | |
| `product` | 42 858 | | |
| `customer_shipping` | 200 001 | | |
| `shipping_details` | 200 001 | | |
