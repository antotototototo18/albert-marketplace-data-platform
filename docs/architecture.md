# Architecture d'Albert's Marketplace

Version L03 du 16 octobre 2026. Le bucket bronze du groupe contient l'export
legacy (L02) et les écritures des trois chemins d'ingestion L03 ; le reste du
diagramme est la **cible proposée** en L01, à relire par le groupe.

## Context

La boutique et les analystes interrogent aujourd'hui la même base PostgreSQL,
tandis que des exports nocturnes alimentent des tableurs. Les rapports ne
partagent pas une définition unique du chiffre d'affaires, et l'équipe ML
demande les unités par produit, pays et jour. La plateforme doit isoler les
lectures analytiques, conserver les données autorisées pour permettre le rejeu
et publier des modèles dont le grain et les règles sont explicites. Les
consignes imposent un bronze GCS en `europe-west1`, un warehouse BigQuery et,
à partir de L03, une ingestion relationnelle et un clickstream Kafka. Le schéma
legacy disponible ne contient pas toutes les informations métier supposées
dans la démonstration L01 : ces limites doivent rester visibles dans les modèles.

## Architecture: built and target

La proposition [ADR-0001](adr/0001-target-architecture.md) retient deux étages :
stockage objet GCS puis tables natives BigQuery. Bronze, silver et gold sont
les niveaux de qualité successifs. Le layout de bronze est fixé par
l'[ADR-0002](adr/0002-bronze-layout.md). Les éléments en trait plein existent
et ont été vérifiés ; ceux en pointillés restent à construire.

```mermaid
flowchart LR
  shop["Clients et vendeurs / boutique"] --> pg[("PostgreSQL operationnel")]
  shop --> kafka["Kafka / topic clickstream, JSON"]
  archive["Archive legacy_csv.tar.gz / 27 tables CSV"] --> land["scripts/land_legacy_bronze.py / exclut pwd, card_no, cvv / L02"]
  pg -->|"1. Xmin, toutes les 24 h"| connector["Connecteur Airbyte local / sans pwd, card_no, cvv / L03"]
  pg -->|"2. order_id > curseur"| extract["ingestion/extract_orders.py / retries, curseur durable / L03"]
  kafka -->|"3. au moins une fois"| consumer["ingestion/consume_clickstream.py / JSON Schema v1 / L03"]

  subgraph gcp["Projet data-engineering-i1 / europe-west1"]
    subgraph bucket["gs://data-engineering-i1-group6 / Standard, acces uniforme, public bloque"]
      legacy[("bronze/legacy/table/ingested_date=2026-10-16 / 27 Parquet zstd, 62 Mo / L02")]
      airbyte[("bronze/airbyte/stream / 9 streams + colonnes _airbyte_* / L03, synchro partielle")]
      manual[("bronze/manual/orders/ingested_date= / L03")]
      click[("bronze/clickstream/v1/dt= / date UTC de event_time / L03")]
      dlq[("bronze/_dlq/clickstream / ligne, motif, heure / L03")]
      state[("bronze/_state / curseur de l'extracteur / L03")]
    end
    subgraph bq["BigQuery / L04-L05"]
      loaded[("Tables natives / jeu de travail bronze")]
      silver[("Silver / types, deduplication, jointures")]
      gold[("Gold / faits, dimensions, demande quotidienne")]
      loaded -.->|"dbt"| silver
      silver -.->|"dbt et tests"| gold
    end
    legacy -.->|"Chargement / L04"| loaded
    airbyte -.-> loaded
    manual -.-> loaded
    click -.-> loaded
  end

  land --> legacy
  connector --> airbyte
  extract --> manual
  extract --> state
  consumer -->|"Evenements valides"| click
  consumer -->|"Evenements invalides"| dlq
  readers["Lecteurs actuels du bucket : proprietaires, editeurs et lecteurs du projet (liaisons par defaut)"] --- bucket
  gold -.-> bi["Analystes et rapports / acces autorises"]
  gold -.-> ml["ML / produit, pays, jour"]
```

Le diagramme montre quatre producteurs du bronze, sans dépôt manuel :

- **L'archive legacy**, chargée une fois en L02 sous `legacy/`.
- **Le connecteur Airbyte**, sous `airbyte/`. Sa première synchro est
  incomplète, faute de mémoire dans Docker.
- **L'extracteur SQL**, sous `manual/orders/`, avec son curseur sous `_state/`.
- **Le consumer Kafka**, sous `clickstream/v1/`, et ses rejets sous `_dlq/`.

Chaque préfixe a un seul producteur identifié. `orders` arrive par trois
chemins, avec des types différents : le [dictionnaire](data-dictionary.md#flux-l03)
dit d'où vient chaque table. Modes, garanties et limites sont dans
l'[ADR-0003](adr/0003-ingestion-modes.md) et le
[suivi des pannes](ingestion-failure-modes.md).

## Layers

| Couche | Contenu | Garanties | Lecteurs |
|---|---|---|---|
| Bronze, GCS | **L02 :** `legacy/` (27 tables). **L03 :** `airbyte/`, `manual/orders/`, `clickstream/v1/`, rejets dans `_dlq/` | Legacy : valeurs **identiques au CSV**, stockées en texte, vérifiées cellule par cellule, un lot = une partition `ingested_date`. L03 : types de la source, provenance Kafka ou colonnes `_airbyte_*`, livraison au moins une fois (doublons possibles). Partout : ni nettoyage ni déduplication ; `pwd`, `card_no` et `cvv` exclus avant écriture | **Aujourd'hui :** tous les rôles du projet (voir [IAM](../infra/iam.md)). **Cible :** comptes d'ingestion et de chargement, membres du groupe |
| Chargement natif, BigQuery | Sous-ensemble de bronze nécessaire aux requêtes répétées | Représenter les lots chargés et rendre les doublons ou reprises observables ; garder GCS comme source de rejeu | Transformations dbt et ingénieurs autorisés |
| Silver, BigQuery | Tables typées et normalisées, règles de déduplication et de jointure explicites | Un défaut traité à un endroit identifié ; clés et relations testées ; `phone`, `zip` et `p_id` gardés en texte ; champs personnels limités selon l'usage | Modèles intermédiaires et modèles gold |
| Gold, BigQuery | `fct_order_items`, `fct_daily_demand` et dimensions | Grain déclaré et testé ; définition commune des mesures ; périmètre de données autorisé pour chaque consommateur | Analystes, rapports et compte ML |

`pwd`, `card_no` et `cvv` sont interdits à la frontière d'ingestion : absents
du bronze legacy, ils sont aussi exclus à la source en L03 (décochés dans le
connecteur ; l'extracteur ne lit que `orders`). Une extraction de démonstration fondée sur le schéma L01 devrait aussi
exclure leurs équivalents, notamment `password_hash` et `card_number`. Les
colonnes personnelles restantes sont recensées dans le
[dictionnaire de données](data-dictionary.md). La quarantaine n'est pas une
zone publique : un événement rejeté peut contenir des données personnelles.

## Ce qui est vérifié à ce stade

| Élément | État et preuve |
|---|---|
| Dépôt, équipe et CI | En place ; voir [CI](ci-cd.md). |
| Schéma et profil de l'export legacy | Inspection reproductible ; voir [le profil L01](evidence/l01-source-profile.json). |
| Bucket du groupe | `gs://data-engineering-i1-group6`, `europe-west1`, Standard, accès uniforme, accès public bloqué, suppression réversible de 7 jours ; lu avec `gcloud storage buckets describe`. |
| Bronze legacy | 27 tables, 2 928 485 lignes, 62 Mo de Parquet zstd, chacune comparée à son CSV ; voir [le manifeste](evidence/l02-bronze-legacy-manifest.json). |
| Lifecycle | Défini dans [infra/lifecycle.json](../infra/lifecycle.json), limité à `bronze/legacy/` : Nearline à 30 jours, Coldline à 90, Archive à 365. |
| IAM | Six liaisons par défaut, aucune ajoutée ; moindre privilège non atteint ; voir [infra/iam.md](../infra/iam.md). |
| Coûts | Moins de $0.002 par mois ; voir [costs.md](costs.md). |
| Extracteur `orders` (L03) | 228 028 commandes puis 2 à la reprise ; voir [le compte rendu](evidence/l03-live-run.json). |
| Consumer clickstream et DLQ (L03) | 69 335 événements acceptés, 2 rejets volontaires retrouvés en DLQ, flux poursuivi. |
| Connecteur Airbyte (L03) | Xmin, Incremental \| Append, 24 h ; `pwd`, `card_no` et `cvv` absents des fichiers. Synchro partielle : 6 streams complets sur 9 ; voir [la preuve](evidence/l03-airbyte-sync.json). Clé HMAC de compte utilisateur, à remplacer. |
| Warehouse et transformations | À réaliser en L04 et L05. |
| Docker, orchestration et Terraform | À réaliser de L06 à L08. |

## Decisions

| ADR | Décision | Statut |
|---|---|---|
| [0001](adr/0001-target-architecture.md) | Deux étages GCS et BigQuery, qualité bronze/silver/gold | Proposed |
| [0002](adr/0002-bronze-layout.md) | Bronze legacy en Parquet zstd, colonnes texte, partition `ingested_date` | Proposed |
| [0003](adr/0003-ingestion-modes.md) | Xmin pour le connecteur, curseur d'ID pour l'extracteur, Kafka au moins une fois | Proposed |

## Change log

| Date | Leçon | Changement |
|---|---|---|
| 2026-10-16 | L01 | Matrice des flux, comparaison des architectures, diagramme cible et limites du modèle quotidien. |
| 2026-10-16 | L02 | Bucket du groupe, bronze legacy chargé, layout mesuré, lifecycle, IAM et coûts ; diagramme distinguant le construit de la cible. |
| 2026-10-16 | L03 | Trois chemins d'ingestion vers bronze (connecteur, extracteur, consumer), DLQ et état de l'extracteur. |

Mettre cette page à jour à la fin de chaque étape, en remplaçant les intentions
par les ressources et garanties réellement vérifiées. Le [suivi du projet](project-plan.md)
recense les preuves attendues avant de déclarer une étape terminée.
