# ADR-0002: Bronze legacy en Parquet zstd, colonnes texte, partitionné par date d'ingestion

- **Status:** proposed — à relire et valider par le groupe
- **Date:** 2026-10-16
- **Author:** Antoine Rabeau
- **Lesson:** L02

## Context

L'export legacy (`legacy_csv.tar.gz`, SHA-256 `ac8132d9…f3d2ef`, la même archive
que le [profil L01](../evidence/l01-source-profile.json)) contient 27 tables CSV :
2 928 485 lignes et 206 Mo. Cinq tables sont vides. C'est un instantané
statique ; il sera chargé dans BigQuery en L04 puis transformé en L05
([ADR-0001](0001-target-architecture.md)).

Il doit atterrir dans le bucket du groupe, `gs://data-engineering-i1-group6`
(`europe-west1`), à côté de ce que l'extracteur L03 y écrit déjà :
`bronze/manual/orders/ingested_date=…/` (batch, partitionné par date de
chargement) et `bronze/clickstream/v1/dt=…/` (événements, partitionnés par date
d'événement).

Contraintes : bronze conserve ce qui est arrivé, sans nettoyage, sans
déduplication et sans colonne supprimée ; seule exception, les secrets `pwd`,
`card_no` et `cvv`, interdits à la frontière d'ingestion par l'ADR-0001.

Faits mesurés qui ont pesé :

- **Des valeurs ne survivent pas à un typage numérique.** 82 203 `customer.phone`
  et 125 861 `shipping_details.phone` commencent par `0`, comme certains
  `p_id`. Les lire comme nombres efface ce zéro ([manifeste](../evidence/l02-bronze-legacy-manifest.json)).
- **Les identifiants aléatoires compressent mal avec snappy.** Sur `orders.csv`,
  snappy ne gagne que 1,42×, alors que zstd gagne 2,58× ([mesures](../evidence/l02-layout-measurements.json)).
- **Partitionner par jour multiplie les petits fichiers.** C'est vrai dans
  l'exercice 1 comme sur `orders` (détail ci-dessous).

## Options considered

Mesures du groupe sur `orders.csv` (222 644 lignes, 13,3 Mo), avec
[`scripts/measure_bronze_layouts.py`](../../scripts/measure_bronze_layouts.py).
Requête : nombre de commandes d'août 2026, médiane de 7 exécutions DuckDB en
local. Ce sont des ordres de grandeur, pas des temps GCS ou BigQuery.

| Option | Objets | Octets | Requête août | Pour | Contre |
|---|---|---|---|---|---|
| **CSV brut, non partitionné** | 1 | 13 335 140 | 38,1 ms | Aucune conversion, lisible partout | 2,6× plus lourd que Parquet zstd ; relu en entier à chaque requête ; aucun schéma |
| **Parquet, partition `ingested_date`** (retenue) | 1 | 5 178 058 | 0,8 ms | Même convention que l'extracteur L03 ; une règle pour les 27 tables ; un rechargement crée une partition sans écraser l'historique | Aucun élagage par date métier dans bronze |
| **Parquet, partition mois de `order_date`** | 37 | 5 157 306 | 1,7 ms | Élagage par mois, taille identique | Seules 4 tables ont une date métier ; il faudrait dériver `order_items` par jointure, donc modifier bronze ; aucun gain mesurable à ce volume |
| **Parquet, partition jour de `order_date`** | 1 727 (1 096 partitions) | 9 787 060 | 52,4 ms | Élagage fin pour des lectures quotidiennes | 1,9× plus lourd ; 1 727 objets à écrire, lister et payer ; 65× plus lent ici |

Codecs, même fichier unique en colonnes texte : sans compression 13 387 562 o,
snappy 9 408 769 o, gzip 6 165 876 o, zstd 5 161 495 o. Typer les colonnes
au lieu de les garder en texte ne réduit pas la taille (zstd 5 478 615 o).

Ces mesures confirment celles d'Anthony à l'exercice 1 (`order_items`, bucket
individuel) :

- **CSV ou Parquet snappy :** le CSV de 10 373 925 o tombe à 3 546 873 o en
  Parquet snappy (2,92×).
- **Partition par jour :** 1 096 partitions donnent 1 967 fichiers et 25,6 Mo,
  soit 7× le fichier unique.
- **Sur le mois d'août :** le layout jour + produit produit 8 649 objets, contre
  31 pour le layout jour. Il prend 1 152 ms contre 318 ms dans BigQuery et
  consomme 168 111 slot-ms contre 463.

## Criteria

| Critère | CSV | `ingested_date` | Mois métier | Jour métier |
|---|---|---|---|---|
| Fidélité : bronze identique à la source | 3 | 3 | 2 | 2 |
| Coût de stockage et d'opérations | 1 | 3 | 3 | 1 |
| Lecture : élagage, schéma, vitesse | 1 | 2 | 3 | 1 |
| Cohérence avec le bucket existant (L03) | 1 | 3 | 2 | 2 |
| Simplicité : une règle pour 27 tables | 3 | 3 | 1 | 1 |

1 = mauvais, 2 = compromis, 3 = bon, d'après les mesures ci-dessus.

## Decision

Chaque table legacy est écrite en un fichier **Parquet compressé en zstd**, à
l'emplacement
`gs://data-engineering-i1-group6/bronze/legacy/<table>/ingested_date=YYYY-MM-DD/part-0.parquet`.
**Toutes les colonnes sont stockées en texte, telles que dans le CSV.**

Trois adaptations seulement, toutes documentées dans le
[dictionnaire](../data-dictionary.md) :

- **Colonne sans nom :** la colonne d'en-tête vide s'appelle `unnamed_0`.
- **Secrets :** `pwd`, `card_no` et `cvv` ne sont pas écrits.
- **Provenance :** elle est portée par les métadonnées du fichier (empreinte de
  l'archive, membre source, horodatage).

Le script [`scripts/land_legacy_bronze.py`](../../scripts/land_legacy_bronze.py)
relit chaque fichier écrit et le compare cellule par cellule au CSV. Le premier
chargement porte `ingested_date=2026-10-16`.

## Consequences

- **Plus simple :**
  - Un nouvel export arrive dans une nouvelle partition et ne réécrit rien.
  - Bronze reste la preuve exacte de ce qui a été reçu.
  - 27 objets et 62 Mo au lieu de 206 Mo de CSV.
  - BigQuery charge directement le Parquet zstd avec la partition Hive
    `ingested_date` en L04.
- **Plus difficile :**
  - Tout lecteur doit typer les colonnes. C'est le rôle de silver (L05), qui
    doit garder `phone`, `zip` et `p_id` en texte.
  - Une requête par date de commande lit toute la table dans bronze.
  - Les secrets exclus ne sont récupérables que depuis l'archive d'origine, hors
    de la plateforme.
- **À surveiller :**
  - Chaque nouvel instantané complet duplique la table. Un export quotidien
    multiplierait le stockage par 365 en un an.
  - Garder un seul producteur par préfixe : `legacy/` pour l'archive, `manual/`
    pour l'extracteur L03.
  - `unnamed_0` est un index technique de l'export, sans sens métier : ne pas
    l'utiliser comme clé.
- **Ce qui forcerait une réécriture :**
  - Une table au-delà d'environ 1 Go.
  - Des lectures régulières de bronze filtrées par date métier.
  - Des chargements complets fréquents ; il faudrait alors passer à
    l'incrémental ou au CDC de L03.

Dans chacun de ces cas, un nouvel ADR remplacera celui-ci, avec de nouvelles
mesures.

## References

- [Mesures des layouts](../evidence/l02-layout-measurements.json) et [manifeste du chargement](../evidence/l02-bronze-legacy-manifest.json).
- Exercice L02-EX1 individuel (mesures du bucket `data-engineering-i1-rascle-anthony`).
- [Chargement Parquet dans BigQuery](https://cloud.google.com/bigquery/docs/loading-data-cloud-storage-parquet) et [partitionnement Hive](https://cloud.google.com/bigquery/docs/hive-partitioned-loads-gcs).
