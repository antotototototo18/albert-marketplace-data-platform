# Preuves du projet

## L01 : profil de la source

[l01-source-profile.json](l01-source-profile.json) contient des comptages et
contrôles recalculés le 16 octobre 2026 sur `Exercise/L02/legacy_csv.tar.gz`,
fourni avec les exercices. L'empreinte SHA-256 identifie exactement l'entrée.
Le fichier ne contient ni lignes de commande individuelles, ni identifiants
clients, ni coordonnées, ni secrets.

Le script lit cinq tables dans l'archive sans extraire les fichiers sur disque,
sans modifier les données et sans contacter PostgreSQL ou GCP. Il publie leurs
colonnes et leurs décomptes, des contrôles de clés et de références, la période
des commandes et les libellés de pays. Les colonnes de l'archive sont inspectées
comme du texte CSV : ce profil n'est pas un dictionnaire de types PostgreSQL.

### Reproduire

Depuis la racine du dépôt, avec Python 3.11 ou plus récent et l'archive locale :

```sh
python3 scripts/profile_source_archive.py ../Exercise/L02/legacy_csv.tar.gz
```

Si les dossiers sont organisés différemment, remplacer l'argument par le chemin
local de l'archive. La sortie JSON doit correspondre au fichier versionné si
l'empreinte de l'archive est identique. Ne pas ajouter l'archive ni ses CSV à Git.

### Portée de la preuve

Ces mesures décrivent un export statique. Elles ne prouvent ni le déploiement
d'un bucket, ni la fraîcheur des données, ni l'absence de futurs doublons.
Les résultats du notebook L01 et les expériences d'ingestion L03 utilisent
d'autres états de la base : leurs volumes ne sont pas interchangeables.

## L03 : ingestion dans le bucket du groupe

Ces fichiers portent sur `gs://data-engineering-i1-group6/bronze`, le
16 octobre 2026. Ils ne contiennent que des décomptes, des chemins d'objets et
des positions Kafka, sans ligne client.

- [l03-validation.json](l03-validation.json) : test isolé de
  `scripts.verify_ingestion` (schéma PostgreSQL, topic et groupe temporaires).
- [l03-live-run.json](l03-live-run.json) : chargement réel de `orders` en deux
  passages, rattrapage du topic `clickstream` et deux rejets volontaires
  envoyés dans le vrai topic, retrouvés en DLQ.
- [l03-airbyte-sync.json](l03-airbyte-sync.json) : lignes écrites par Airbyte
  par stream, comparées à la base, et issue des deux jobs. Le catalogue vérifié
  est dans [ingestion/airbyte/connection-evidence.json](../../ingestion/airbyte/connection-evidence.json).
