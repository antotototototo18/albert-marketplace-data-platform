# ADR-0001: Séparer le bronze GCS du warehouse analytique BigQuery

- **Status:** proposed — à relire et valider par le groupe
- **Date:** 2026-10-16
- **Author:** Anthony Rascle
- **Lesson:** L01

## Context

Le diagnostic de l'exercice L01 décrit une boutique et des analystes utilisant
le même PostgreSQL de 25 tables, des exports CSV nocturnes et des rapports qui
ne s'accordent pas sur le chiffre d'affaires. L'équipe ML demande une table
quotidienne par produit et pays. Le notebook propose un warehouse pour ce
besoin principalement SQL ; son SQL de démonstration utilise une base simulée.

Les consignes du projet précisent ensuite une contrainte matérielle : bronze
en Parquet dans un bucket GCS `europe-west1` en L02, puis chargement du jeu de
travail dans des tables natives BigQuery en L04 et modèles dbt en L05. La cible
doit donc conserver le stockage brut et le warehouse comme deux étages.
L03 ajoute un flux Kafka sans imposer une publication gold en temps réel.

L'[inspection reproductible](../evidence/l01-source-profile.json) de l'archive
legacy fournie compte 222 644 commandes et 408 560 lignes, avec 42 858 produits.
Ces volumes décrivent cet export, pas la production ni la base simulée du
notebook. Aucun besoin de moteur distribué supplémentaire n'est établi.

## Options considered

| Option | Pour | Contre dans ce projet |
|---|---|---|
| Warehouse seul | Accès SQL partagé, peu de composants, adapté aux rapports quotidiens | Une cible limitée aux tables natives ne fournit pas le bronze objet indépendant demandé en L02. |
| Lake seul | Conservation des fichiers bruts, rejeu et accueil des événements | Il manque la couche de tables natives et de modèles SQL attendue en L04-L05 ; les consommateurs devraient réimplémenter les transformations. |
| Two-tier : GCS puis BigQuery | Respecte L02-L05, conserve les sources autorisées et isole les lectures analytiques de l'OLTP | Deux stockages, chargements et droits à suivre ; risque de décalage entre fichiers et tables. |
| Lakehouse avec format de tables ouvert | Gestion transactionnelle et accès analytique autour des fichiers | Le besoin d'Iceberg, Delta ou d'un autre catalogue n'est pas démontré ; ces composants ne remplacent pas les tables natives demandées en L04. |

## Criteria

Appréciation de conception, pas un benchmark : 1 = peu adapté, 2 = compromis,
3 = adapté. Le coût réel devra être mesuré en L02 et L04.

| Critère | Warehouse seul | Lake seul | Two-tier | Lakehouse |
|---|---|---|---|---|
| Workload : reporting SQL et agrégat ML quotidien | 3 | 1 | 3 | 3 |
| Types : tables, exports et événements JSON à conserver | 2 | 3 | 3 | 3 |
| Fraîcheur : publication quotidienne, ingestion streaming distincte | 3 | 2 | 3 | 3 |
| Équipe : réutiliser SQL, limiter les nouveaux composants | 3 | 1 | 2 | 1 |
| Coût et exploitation : limiter les copies et systèmes à administrer | 3 | 2 | 2 | 1 |
| Gouvernance : contrats d'entrée et jeux de données autorisés | 3 | 1 | 2 | 2 |
| Conformité aux livrables GCS et tables natives BigQuery | 1 | 1 | 3 | 2 |

## Decision

Proposer une architecture **two-tier** : bronze dans Cloud Storage, puis un
warehouse BigQuery avec tables de chargement, silver et gold. Prévoir bucket
et datasets dans `europe-west1`. Les modèles dbt seront développés dans
`transform/`, conformément aux consignes L05-L06.

Les secrets sont exclus avant la première écriture analytique ; bronze conserve
ensuite les valeurs autorisées reçues, sans nettoyage ni déduplication métier.
Les analystes et le ML consommeront les modèles gold autorisés. La cadence
quotidienne est une proposition ; les seuils de fraîcheur seront justifiés en L05.

Il s'agit de deux étages physiques et de trois niveaux de qualité : bronze,
silver et gold ne désignent pas trois plateformes distinctes. Le chargement
sélectionné dans BigQuery n'est pas une quatrième couche métier.

## Consequences

- **Plus simple :** isoler les requêtes analytiques, rejouer les transformations
  depuis bronze et partager les définitions et grains dans dbt.
- **Plus difficile :** maintenir la correspondance fichiers/tables, limiter les
  droits sur les deux étages et suivre stockage, opérations et scans.
- **À surveiller :** petites partitions, doublons d'ingestion, curseurs qui
  ignorent les modifications, fraîcheur et jointures qui multiplient les unités.
- **Limite métier :** le schéma legacy ne prouve ni le paiement ni le pays à la
  date de commande ; le [modèle ML](../model/star-daily-demand.md) l'explicite.
- **Réexaminer :** si la publication quotidienne ne suffit plus, si les coûts de
  copie deviennent dominants ou si un usage exige des tables ouvertes partagées,
  écrire un nouvel ADR avec des mesures. Aucun seuil chiffré n'a encore été validé.

## References

- Consignes fournies : `Project Steps/L01.md`, `L02.md`, `L03.md`, `L04.md` et `L05.md`.
- Travail individuel : `Exercise/L01/EX1-diagnose/data_flow_mapping.ipynb`.
- [Architecture cible](../architecture.md) et [matrice des flux](../data-flows.md).
- [Chargement Parquet de GCS vers BigQuery](https://docs.cloud.google.com/bigquery/docs/loading-data-cloud-storage-parquet).
