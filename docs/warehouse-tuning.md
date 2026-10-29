# Warehouse BigQuery : chargement, réglages et coûts (L04)

Version du 26 octobre 2026. Toutes les mesures viennent d'une seule exécution de
[`scripts/measure_warehouse.py`](../scripts/measure_warehouse.py), enregistrée
dans [l04-warehouse-measurements.json](evidence/l04-warehouse-measurements.json).
Le SQL est dans [`warehouse/`](../warehouse/README.md).

## Comment lire les chiffres

- **Octets traités, pas octets facturés.** BigQuery facture au moins 10 Mio
  **par table lue** : Q2 lit quatre tables et facture 41 943 040 octets avant
  comme après réglage. Le montant facturé ne bouge pas à notre volume ; les
  octets traités, si. Toutes les comparaisons ci-dessous portent sur
  `total_bytes_processed`.
- **Cache désactivé.** Chaque job est lancé avec `use_query_cache=False`, et le
  fichier de preuve enregistre `cache_hit: false` pour chacun. Une requête servie
  par le cache afficherait 0 octet et ferait croire qu'un réglage l'a rendue gratuite.
- **Estimation et réel concordent.** Le script fait un dry run avant chaque
  requête : l'estimation est égale aux octets traités sur les 30 jobs mesurés.
- **Coût** = octets traités / 2^40 × $7.50, tarif à la demande d'`europe-west1`.
  Presque tout arrondit à $0.000 : le **ratio** est ce qui reste vrai quand le
  volume change, pas le montant.
- **« Aujourd'hui » = 2026-09-14**, dernière date de commande de l'export, pour
  que chaque relecture donne la même fenêtre.

## 1. Ce qui est chargé, ce qui reste externe

Deux datasets en `europe-west1`, la région du bucket :

- `group6_bronze` : tables **externes** sur `gs://data-engineering-i1-group6/bronze`.
  Aucune ligne stockée ; chaque requête relit les fichiers.
- `group6_warehouse` : tables **natives**, copiées depuis `group6_bronze`.

| Table | Lignes | Où | Pourquoi |
|---|---|---|---|
| `orders` | 222 644 | Native, partitionnée | Filtrée par date dans Q2 et par toutes les questions de CA |
| `order_items` | 408 560 | Native, partitionnée et clusterisée | La table la plus lue : Q1, Q2, la demande ML. Reçoit `order_date` par jointure, faute de date propre |
| `product` | 42 858 | Native | Dimension de L05, jointe en entier |
| `review` | 111 322 | Native | Q3 et les avis de L05 |
| `product_reviews` | 111 322 | Native | Seul lien entre un avis et un produit |
| `customer_shipping` | 200 001 | Native | Pays de livraison de `fct_daily_demand` (Q2) |
| `shipping_details` | 200 001 | Native | Idem |
| `clickstream` | 69 404 | **Externe** | Événements en append, pas encore interrogés de façon répétée ; partition `dt` lue dans le chemin, filtre de partition obligatoire |
| 20 autres tables legacy | | **Externes non créées** | Aucune question du projet ne les lit pour l'instant (images, wishlist, abonnements...). Leur créer une table externe ne coûte rien le jour où L05 en a besoin |
| `bronze/airbyte/`, `bronze/manual/` | | **Non chargés** | Mêmes tables que `legacy/`, sous d'autres types et partiellement synchronisées (ADR-0003). Silver choisira une source par table en L05 ; les charger deux fois créerait les doublons que L05 doit justement résoudre |

Les sept tables natives sont celles de l'exercice 1 de L04, que L05 relit. Elles
sont **typées mais pas nettoyées** : dates en `DATE`, quantités et identifiants
numériques en `INT64`, `price_at_purchase` en `NUMERIC`, `product.price` en
`BIGNUMERIC` (jusqu'à 20 décimales dans la source). `p_id`, `zip` et `phone`
restent en texte (zéros initiaux, [dictionnaire](data-dictionary.md)). Aucune
ligne retirée, aucune déduplication, `unnamed_0` conservée : c'est le travail de
silver. Les `CAST` n'ont échoué sur aucune ligne.

## 2. Réglages, et ce que chacun a rapporté

Chaque réglage est mesuré contre une copie non réglée de la même table
(`*_untuned`), avec une requête qui correspond à un usage réel.

| Table | Changement | Requête | Octets avant | Octets après | Ratio |
|---|---|---|---:|---:|---:|
| `orders` | `PARTITION BY` mois | 28 derniers jours (la part de Q2) | 10 242 352 | 379 950 | **26,96×** |
| `order_items` | `PARTITION BY` mois | Q1, 12 mois | 16 342 400 | 5 622 040 | **2,91×** |
| `order_items` | `PARTITION BY` mois | Un seul jour | 11 439 680 | 145 740 | **78,49×** |
| `order_items` | Jour au lieu de mois | Q1, 12 mois | 5 622 040 | 5 427 280 | 1,04× |
| `order_items` | Jour au lieu de mois | Un seul jour | 145 740 | 20 440 | 7,13× |
| `order_items` | `CLUSTER BY p_id` | Historique d'un produit rare (`B0CHXWTSM6`, 4 lignes) | 11 439 680 | 532 308 | **21,49×** |
| `order_items` | `CLUSTER BY p_id` | Historique du best-seller (`B0BM4GX6TT`, 1 376 lignes) | 11 439 680 | 11 439 624 | 1,00× |
| `review` | `CLUSTER BY rating` | Avis à 1 ou 2 étoiles | 24 165 148 | 24 165 148 | 1,00× |
| `review` | `CLUSTER BY rating` | Q3 | 4 007 592 | 4 007 592 | 1,00× |
| `product_reviews` | `CLUSTER BY p_id` | Avis d'un produit rare | 2 226 440 | 2 226 440 | 1,00× |
| `product_reviews` | `CLUSTER BY p_id` | Avis du best-seller | 2 226 440 | 2 226 440 | 1,00× |

**`orders` et `order_items` au mois.** Le gain suit la part de partitions lues :
2 mois sur 37 pour la fenêtre de 28 jours de Q2, 13 sur 37 pour Q1. Le jour
isolé n'ouvre que septembre 2026, à moitié rempli : d'où 78×.

**Le grain journalier, rejeté.** Il ne gagne que 1,04× sur Q1 : il évite
seulement la première moitié de septembre 2025, que le mois oblige à lire. Il
gagne 7× sur une requête d'un seul jour, mais aucun consommateur ne lit un jour
isolé : le ML lit 28 jours, la finance des mois. Il construit 1 096 partitions
de 19 384 octets en moyenne, contre 37 partitions de 574 192 octets, et Q1 y a
consommé **5 754 ms de slot contre 137** pour le même résultat. Sur une
tarification à la capacité, ce temps se paierait. La table `order_items_day`
n'existe que pour cette mesure.

**`CLUSTER BY p_id` sur `order_items` : utile pour la longue traîne seulement.**
Le produit rare apparaît dans 2 mois sur 37, et le tri permet de sauter les
blocs qui ne peuvent pas le contenir. Le best-seller est dans chaque mois :
rien à sauter, 1,00×. Q1 et Q2 ne filtrent pas sur `p_id` : leur gain vient
uniquement de la partition. Conservé, car le clustering ne coûte ni stockage ni
écriture, et la plupart des produits sont rares.

**`review` et `product_reviews` : rien gagné.** Q3 lit toutes les notes et tous
les produits : un tri ne peut rien en éliminer, comme attendu. Les filtres qui
correspondent au clustering ne gagnent rien non plus. Les deux tables font
28,6 Mo et 3,0 Mo : notre hypothèse est qu'elles tiennent dans trop peu de blocs
de stockage pour qu'un bloc entier soit exclu. La console ne montre pas le
nombre de blocs, donc ce n'est pas vérifié. Conservés parce qu'ils ne coûtent
rien, à re-mesurer si ces tables dépassent quelques centaines de Mo (L09).

**Non réglées.** `product`, `customer_shipping` et `shipping_details` n'ont pas
de date, et Q2 les lit en entier dans ses jointures. `product.category_id` n'a
que deux valeurs. Aucun filtre répété ne justifie un réglage aujourd'hui.

État des partitions, lu dans `INFORMATION_SCHEMA.PARTITIONS` :

| Table | Partitions | Taille moyenne |
|---|---:|---:|
| `orders` | 37 | 382 131 o |
| `order_items` | 37 | 574 192 o |
| `order_items_day` (expérience) | 1 096 | 19 384 o |

## 3. Vue matérialisée `daily_demand`

[`warehouse/05_daily_demand.sql`](../warehouse/05_daily_demand.sql) : unités,
CA et nombre de lignes par produit et par jour, partitionnée et clusterisée
comme `order_items`. C'est la lecture quotidienne de l'équipe ML (flux A8).

**Ratio de réduction** (`order_lines / groupes distincts`, [requête](../warehouse/queries/collapse_ratio.sql)) :

| Grain | Lignes | Lignes de commande par ligne |
|---|---:|---:|
| Table de faits `order_items` | 408 560 | 1,00 |
| Produit × jour | 356 981 | **1,14** |
| Produit × semaine | 224 752 | 1,82 |
| Produit × mois | 165 141 | 2,47 |
| Produit | 41 323 | 9,89 |

La plupart des produits se vendent au plus une fois par jour : la vue stocke
356 981 lignes et 18,6 Mo, soit 87 % de `order_items`. La lecture des 28
derniers jours coûte **422 800 octets depuis la table et 422 800 depuis la
vue : 1,00×**. Elle ne fait économiser aucun octet, donc aucun dollar en
tarification à la demande. Elle épargne l'agrégation (33 ms de slot contre 41),
ce qui ne vaudrait quelque chose qu'en tarification à la capacité.

**Décision : gardée au grain jour, en le sachant.** Le grain demandé par le ML
est le jour ([modèle](model/star-daily-demand.md)) : la semaine (1,82) ou le
mois (2,47) réduiraient davantage, mais répondraient à une autre question. Ce
qu'elle coûte : 18,6 Mo de stockage, environ $0.0004 par mois, et un
rafraîchissement incrémental à chaque chargement de `order_items`. Ce qu'elle
apporte : un contrat de lecture stable pour le ML avant que L05 existe. Elle
sera supprimée quand `fct_daily_demand` (dbt, grain produit × pays × jour)
sera construite en L05 : garder les deux ferait deux définitions de la demande.

## 4. Trois requêtes du projet, chiffrées

| Requête | Besoin | Octets non réglé | Coût | Octets réglé | Coût | Ratio |
|---|---|---:|---:|---:|---:|---:|
| [Q1](../warehouse/queries/q1_monthly_revenue.sql) CA mensuel sur 12 mois | Finance (A7) | 16 342 400 | $0.000111 | 5 622 040 | $0.000038 | 2,91× |
| [Q2](../warehouse/queries/q2_daily_demand_by_country.sql) Unités par produit, pays et jour, 28 jours | ML (A8), grain de `fct_daily_demand` | 37 404 945 | $0.000255 | 13 377 983 | $0.000091 | 2,80× |
| [Q3](../warehouse/queries/q3_product_ratings.sql) Note moyenne des produits à plus de 50 avis | Catalogue, entrée des avis de L05 | 4 007 592 | $0.000027 | 4 007 592 | $0.000027 | 1,00× |

Facturé réellement, avant comme après : 10 485 760 octets pour Q1 ($0.000072),
41 943 040 pour Q2 ($0.000286), 20 971 520 pour Q3 ($0.000143), à cause du
minimum par table lue.

- **Q1** ne lit que `order_items`, qui porte la date : la partition fait tout le gain.
- **Q2** gagne sur `order_items` et `orders`, mais lit `customer_shipping` et
  `shipping_details` en entier : l'essentiel des 13,4 Mo restants vient de ces
  deux tables d'adresses. C'est la prochaine table à régler si Q2 devient
  fréquente, par exemple en préparant en L05 la correspondance acheteur → pays.
- **Q3** n'a pas de date et lit toutes les notes : aucun réglage de stockage ne
  peut l'aider. Une agrégation par produit en L05 le pourrait.

Les chiffres d'affaires sont **faux** à ce stade, et c'est attendu : les
commandes jumelles de l'export ne sont pas retirées (cours L04, démo §7). Ces
requêtes mesurent un coût, pas un résultat. La définition d'une commande est
le travail de silver en L05.

## 5. Le plafond `maximum_bytes_billed`

**Valeur : 1 GiB (1 073 741 824 octets).** La plus grosse requête légitime
mesurée traite 37,4 Mo et en facture 41,9 Mo (Q2 non réglée) : le plafond
laisse une marge d'environ 25×. Une erreur, par exemple un `SELECT *` sur une
table publique, coûte au plus $0.0073 avant d'être refusée. Le jour où une
requête légitime l'atteint, c'est un signal de croissance à examiner
([ADR-0004](adr/0004-warehouse-pricing.md)), pas une raison de le relever
sans réfléchir.

**Où il est posé :**

| Où | Comment | Portée |
|---|---|---|
| Chaque requête du script de mesure | `maximum_bytes_billed=CAP` sur chaque job, dans [`measure_warehouse.py`](../scripts/measure_warehouse.py) | Toutes les mesures de ce document |
| Configuration par défaut du CLI `bq` | [`warehouse/bigqueryrc.example`](../warehouse/bigqueryrc.example), à copier en `~/.bigqueryrc` par chaque membre | Toutes les requêtes `bq query` de cette machine |
| Console BigQuery | *More → Query settings → Advanced options → Maximum bytes billed* | Par personne et par onglet : non versionnable, à régler par chacun |
| dbt (L05) | `maximum_bytes_billed: 1073741824` dans `profiles.yml` | Tous les modèles et tests dbt |
| Projet entier | **Non posé** | Le quota personnalisé « Query usage per day » se règle sur le projet `data-engineering-i1`, partagé avec les autres groupes. Nos comptes n'ont pas ce droit : ils ne peuvent même pas lister les jobs du projet (`bigquery.jobs.listAll` refusé) |

La limite : rien n'oblige un membre à copier `bigqueryrc.example` ou à régler sa
console. Le plafond est donc une convention d'équipe sur ces deux chemins, et
une garantie seulement dans le script et dans dbt.

**Vu en échec,** sur nos tables avec un plafond de 1 000 000 octets :

```text
Query exceeded limit for bytes billed: 1000000. 10485760 or higher required.
```

Et avec le plafond retenu, sur `bigquery-public-data.samples.github_timeline`
(3,54 GiB estimés au dry run, soit $0.026 sans plafond) :

```text
Query exceeded limit for bytes billed: 1073741824. 3802136576 or higher required.
```

**Ce qu'ont coûté ces échecs : rien.** Les trois jobs refusés apparaissent dans
`INFORMATION_SCHEMA.JOBS_BY_USER` avec la raison `bytesBilledLimitExceeded` et
aucun octet facturé. BigQuery refuse avant d'exécuter. Le client Python remonte
ce refus comme une erreur HTTP 500 : c'est la raison, pas le code, qui
l'identifie.

## Reproduire

Depuis la racine du dépôt, avec les droits BigQuery sur `data-engineering-i1` :

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r warehouse/requirements.txt
gcloud auth application-default login
python scripts/run_sql.py warehouse/01_datasets.sql
python scripts/run_sql.py warehouse/02_bronze_external.sql
python scripts/run_sql.py warehouse/03_native_load.sql
python scripts/run_sql.py warehouse/04_native_tuned.sql
python scripts/measure_warehouse.py docs/evidence/l04-warehouse-measurements.json --create-view
```

Sous Windows, activer l'environnement avec `.venv\Scripts\Activate.ps1` dans
PowerShell. Le dernier script supprime puis recrée `daily_demand` après les mesures de
réglage : BigQuery peut réécrire une requête pour lire une vue matérialisée,
ce qui fausserait un « avant ». Chaque mesure enregistre si une vue a été
utilisée ; aucune ne l'a été.
