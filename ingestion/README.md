# Ingestion L03

Trois chemins écrivent dans le bucket du groupe,
`gs://data-engineering-i1-group6/bronze/` (`europe-west1`) :

| Chemin | Préfixe | État |
|---|---|---|
| Extracteur SQL `extract_orders.py` | `manual/orders/` | Exécuté le 16/10/2026 |
| Consumer Kafka `consume_clickstream.py` | `clickstream/v1/`, rejets dans `_dlq/clickstream/` | Exécuté le 16/10/2026 |
| Connecteur Airbyte local | `airbyte/` | Créé le 16/10/2026 ; synchro partielle, voir plus bas |

Les choix et leurs limites sont dans [l'ADR-0003](../docs/adr/0003-ingestion-modes.md).
Les résultats réels sont dans [le suivi des pannes](../docs/ingestion-failure-modes.md).

## Installation

Depuis la racine du dépôt, avec Python 3.11 ou plus récent :

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r ingestion/requirements.txt
cp .env.example .env
```

Renseigner `DATABASE_URL` dans `.env` avec l'accès fourni pour la stack locale.
Ne pas copier cette valeur dans le code ou la PR. Le bucket et le broker local
sont déjà indiqués dans l'exemple. Pour GCS, utiliser ses Application Default
Credentials existantes ; si nécessaire, les configurer avec
`gcloud auth application-default login` sur sa propre machine.

Charger les variables dans un shell compatible :

```sh
set -a
source .env
set +a
```

Sous PowerShell, activer `.venv\Scripts\Activate.ps1` et définir les variables
avec `$env:NOM = 'valeur'`. Les jobs ne chargent pas automatiquement un fichier
`.env` et ne contiennent aucune connexion de secours avec un mot de passe.

## Extracteur SQL

Un passage, puis une reprise sur le même état :

```sh
python -m ingestion.extract_orders
python -m ingestion.extract_orders
```

Pour interroger périodiquement sans relancer à la main :

```sh
python -m ingestion.extract_orders --interval-seconds 300
```

Le script sélectionne explicitement les cinq colonnes de `orders`. Il lit les
IDs strictement supérieurs au dernier ID stocké, dans un snapshot repeatable-read.
Le checkpoint GCS `bronze/_state/manual/orders.json` survit au processus et à
la machine. Un objet est durable avant l'avancement de l'état. En cas de panne
de connexion, cinq tentatives avec délai croissant précèdent l'arrêt.

Les fichiers sont sous `manual/orders/ingested_date=YYYY-MM-DD/`, pour limiter
les petits objets pendant le chargement initial. La date métier reste dans
`order_date`. Une nouvelle table ou base doit avoir son propre préfixe et son
état ; ne pas réutiliser un curseur d'une autre source. Ne pas effacer un
checkpoint pour « réparer » une erreur sans prévoir la gestion du rejeu.

Cette extraction ne capture pas les UPDATE, DELETE ni les commits tardifs dont
l'ID est déjà sous le curseur. Un seul writer est prévu par source ; la
précondition de génération GCS fait échouer un writer utilisant un état périmé.

## Consumer Kafka

```sh
python -m ingestion.consume_clickstream
```

Pour un essai borné :

```sh
python -m ingestion.consume_clickstream --max-messages 200
```

Chaque message est validé avec le contrat correspondant à `schema_version`.
Seule la version 1 est définie. Un champ inattendu, un type invalide, un JSON
malformé ou une version inconnue part en DLQ, avec ses octets d'origine, le
motif, l'heure, le topic, la partition et l'offset. Un rejet ne bloque pas le
message valide suivant.

Les événements valides vont dans `clickstream/v1/dt=YYYY-MM-DD/`, selon
`event_time` en UTC. Les rejets vont dans `_dlq/clickstream/dt=YYYY-MM-DD/`,
selon leur heure de quarantaine. Le consumer confirme les offsets **après**
les deux sorties ; si l'une échoue, le lot reste à reprendre. Des doublons
sont possibles après un crash : aucune déduplication n'est faite en bronze.

Le consumer group du projet est `group6-bronze-clickstream`. Un seul consumer
de ce groupe doit écrire dans le bucket du groupe à un instant donné. Changer de
groupe relit tous les messages encore retenus par Kafka et les écrit une
seconde fois : le faire volontairement, avec un préfixe de validation distinct.
Pour rattraper un gros backlog, `KAFKA_BATCH_SIZE=2000` limite le nombre de
petits fichiers. Les options TLS/SASL éventuelles vont dans un fichier local
ignoré, dont le chemin est fourni par `KAFKA_CLIENT_CONFIG`.

## Raccorder Airbyte

Route 1 du cours : Airbyte local (`abctl`), de la base de la stack vers le
bucket du groupe. Tout se fait dans l'UI `http://localhost:8000` ; le mot de
passe est réaffiché par `abctl local credentials`. Aucun secret de cette
procédure ne va dans Git.

### 1. La clé HMAC de la destination

La destination GCS d'Airbyte n'accepte qu'une clé HMAC. C'est une clé longue
durée : noter son ID d'accès (jamais le secret) dans
[le suivi des pannes](../docs/ingestion-failure-modes.md#slots-et-clés).

Option recommandée, un compte de service limité au bucket :

```sh
gcloud iam service-accounts create airbyte-bronze-writer \
  --display-name="Airbyte bronze writer"
gcloud storage buckets add-iam-policy-binding gs://data-engineering-i1-group6 \
  --member="serviceAccount:airbyte-bronze-writer@data-engineering-i1.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
gcloud storage hmac create \
  airbyte-bronze-writer@data-engineering-i1.iam.gserviceaccount.com
```

`objectAdmin` est nécessaire car le test de connexion d'Airbyte écrit puis
supprime un fichier. Ce rôle permet donc aussi de supprimer des objets bronze.

Si le compte n'a pas le droit de créer un compte de service, solution de repli :
console Cloud Storage → Paramètres → Interopérabilité → clé pour le compte
utilisateur. Cette clé porte alors tous les droits du compte : à révoquer dès
qu'un compte de service est disponible.

Sur le projet du cours, les comptes étudiants ne peuvent pas créer de compte de
service (constaté le 16/10/2026) : la clé utilisée est donc une clé de compte
utilisateur, consignée dans le suivi des pannes.

### 2. La source PostgreSQL

| Champ | Valeur |
|---|---|
| Host / Port | `host.docker.internal` / `5433` (port publié sur cette machine) |
| Database / Schema | `marketplace` / `public` |
| User / Password | l'accès local de la stack, saisi seulement dans Airbyte |
| SSL mode | `disable` (base locale) |
| Update method | **Detect Changes with Xmin System Column** |

Xmin voit les insertions et les mises à jour sans curseur choisi à la main,
mais pas les suppressions. Le choix est argumenté dans l'ADR-0003.

### 3. La destination GCS

| Champ | Valeur |
|---|---|
| Bucket name / path | `data-engineering-i1-group6` / `bronze/airbyte` |
| Bucket region | `europe-west1` |
| Credential | la clé HMAC de l'étape 1 |
| Output format | Parquet, compression `SNAPPY` |

### 4. La connexion

1. Streams : les **sept** de [airbyte/selection.json](airbyte/selection.json),
   plus `customer` et `payment_details` pour prouver les exclusions.
2. Sync mode : **Incremental | Append** pour chaque stream (curseur `xmin`
   fixé par la source).
3. Dans l'onglet Schema, ouvrir `customer` et décocher `pwd` ; ouvrir
   `payment_details` et décocher `card_no` et `cvv`.
4. Schedule : **Scheduled, every 24 hours**, cohérent avec le flux C2.
5. Détection des changements de schéma : approbation manuelle, sans
   propagation automatique des nouvelles colonnes.
6. Lancer **Sync now** une fois, puis une seconde fois pour voir le
   comportement incrémental.

### 5. La preuve

Dans `ingestion/airbyte/` :

- [customer-pwd-deselected.png](airbyte/customer-pwd-deselected.png) et
  [payment-details-card-no-cvv-deselected.png](airbyte/payment-details-card-no-cvv-deselected.png) :
  colonnes décochées dans la connexion. Ces captures datent de la création,
  quand les streams étaient encore en Full refresh ; le mode actuel est dans
  la preuve JSON ci-dessous.
- [connection-schedule-24h.png](airbyte/connection-schedule-24h.png) : synchro
  planifiée toutes les 24 heures.
- [connection-evidence.json](airbyte/connection-evidence.json) : catalogue
  réellement appliqué, vérifié par le script ci-dessous.

`pg_replication_slots` reste vide : Xmin ne crée pas de slot.

### 6. Mémoire

La source et la destination d'Airbyte peuvent chacune demander jusqu'à 4 Go.
Avec 7,7 Go donnés à Docker, la source a été tuée (`OOMKilled`) pendant les
synchros du 16/10/2026. Donner au moins 12 Go à Docker (Settings → Resources),
puis relancer les conteneurs de la stack, qui ne redémarrent pas tous seuls.

### Exporter et vérifier le catalogue

L'export lit l'API locale avec les identifiants d'`abctl`, sans les afficher, et
ne garde que le catalogue et l'issue des jobs. Le conserver dans un fichier
`*.local.json`, jamais dans Git :

```sh
python3 -m ingestion.export_airbyte_catalog data/airbyte-export.local.json
```

Le vérificateur accepte ce format interne `syncCatalog` (`streams[].stream` et
`streams[].config`) :

```sh
python -m ingestion.check_airbyte_export data/airbyte-export.local.json \
  --output ingestion/airbyte/connection-evidence.json
```

Il refuse une connexion manuelle/inactive, un stream requis absent ou non
incrémental, et toute sélection de colonnes interdites. Sa sortie est limitée
au catalogue, sans configuration d'authentification. Elle ne prouve pas à elle
seule le mode de réplication, la destination ou la réussite de la synchronisation.

## Vérifications

Les tests unitaires et les vérifications de panne tournent sans accès cloud :

```sh
python -m unittest discover --start-directory tests --verbose
```

Pour refaire le test complet avec la stack et le bucket configurés :

```sh
python -m scripts.verify_ingestion --report data/l03-validation.local.json
```

Ce test crée puis supprime un schéma PostgreSQL, un topic Kafka et un groupe
à noms uniques. Il écrit des données synthétiques sous `bronze/_validation/`,
et un rejet volontaire sous `bronze/_dlq/clickstream/`. Les commandes et topics
métier ne sont pas modifiés. Les fichiers de preuve GCS sont conservés.

Le 16/10/2026, deux événements volontairement cassés ont aussi été envoyés dans
le vrai topic `clickstream`, sans `session_id`. Ils sont dans
`bronze/_dlq/clickstream/dt=2026-10-16/` et le message suivant de chaque
partition a été accepté ; voir [le compte rendu](../docs/evidence/l03-live-run.json).

Pour des tests sur disque, remplacer `BRONZE_URI` par `data/bronze` : mêmes
formats et mêmes règles, avec un seul writer local. Les images Docker et
l'orchestration complète seront ajoutées dans les étapes L06 et L07.
