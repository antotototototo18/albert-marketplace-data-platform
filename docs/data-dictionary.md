# Dictionnaire des données — L03

Les colonnes relationnelles ci-dessous ont été lues dans le schéma du PostgreSQL
local. Le script a chargé `orders` ; le connecteur Airbyte est configuré pour
les sept streams requis plus `customer` et `payment_details`, et ses colonnes
ont été relues dans les fichiers Parquet du bucket (synchro du 16/10/2026,
incomplète pour `orders`, `product` et `order_items`). Les noms
singuliers et les types correspondent au legacy, pas à la base simulée du
notebook L01.

## Chemins et provenance

Bucket du groupe : `gs://data-engineering-i1-group6` (`europe-west1`).

| Chemin dans le bucket | Producteur | État |
|---|---|---|
| `bronze/manual/orders/ingested_date=YYYY-MM-DD/` | `extract_orders.py` ; cinq colonnes SQL, sans métadonnées Airbyte | Exécuté, checkpoint dans `bronze/_state/manual/orders.json`. |
| `bronze/clickstream/v1/dt=YYYY-MM-DD/` | `consume_clickstream.py` ; événement et provenance Kafka | Exécuté ; `dt` est la date UTC de `event_time`. |
| `bronze/_dlq/clickstream/dt=YYYY-MM-DD/` | Même consumer ; rejets | Rejet volontaire stocké et relu ; `dt` est le jour de quarantaine. |
| `bronze/airbyte/<stream>/AAAA_MM_JJ_<epoch>_<n>.parquet` | Connecteur Airbyte (Xmin), 9 streams | Chargement partiel : `orders` absent, `product` et `order_items` incomplets (source tuée faute de mémoire). Pas de dossier `dt=` : la date n'est que dans le nom du fichier. |
| `bronze/_validation/` | Tests d'intégration isolés | Données synthétiques ; à exclure des sources analytiques. |

Les colonnes de partition sont dans les clés des objets. Les fichiers SQL
conservent `order_date` sans modification ; aucune jointure ni déduplication
métier n'est faite dans bronze. Les identifiants de produit restent des chaînes.

`orders` arrive par deux chemins : `manual/orders/` (cinq colonnes, sans
métadonnées) et `airbyte/` (mêmes colonnes plus les quatre `_airbyte_*`). Silver
doit choisir une source par table, ou dédupliquer sur `order_id` en sachant
d'où vient chaque ligne.

## `orders`

| Colonne | Type source / Parquet manuel | Sens | Donnée personnelle ? |
|---|---|---|---|
| `order_id` | INTEGER / int32 | Identifiant de commande, curseur du script | Indirectement, relié au client |
| `buyer_id` | VARCHAR / string | Identifiant client | Oui, pseudonyme |
| `discount_id` | INTEGER / int32, nullable | Remise associée | Pas isolément |
| `payment_id` | INTEGER / int32, nullable | Référence de paiement | Indirectement |
| `order_date` | DATE / date32 | Date métier, sans heure ni statut de paiement | Indirectement dans une ligne client |

## `order_items`

| Colonne | Type PostgreSQL | Sens | Donnée personnelle ? |
|---|---|---|---|
| `order_id` | INTEGER | Commande parente | Indirectement |
| `p_id` | VARCHAR | Produit acheté | Pas isolément |
| `qty` | INTEGER | Quantité commandée | Pas isolément |
| `price_at_purchase` | NUMERIC | Prix enregistré à l'achat | Pas isolément |

## `review`

| Colonne | Type PostgreSQL | Sens | Donnée personnelle ? |
|---|---|---|---|
| `review_id` | INTEGER | Identifiant d'avis | Indirectement |
| `buyer_id` | VARCHAR | Auteur | Oui, pseudonyme |
| `r_desc` | VARCHAR | Texte libre de l'avis | Potentiellement ; contenu non classifié |
| `title` | VARCHAR | Titre libre | Potentiellement ; contenu non classifié |
| `rating` | INTEGER | Note | Indirectement avec l'auteur |
| `seller_product_flag` | CHAR | Indicateur vendeur/produit, valeurs à profiler | Indirectement avec l'avis |

## `product_reviews`

| Colonne | Type PostgreSQL | Sens | Donnée personnelle ? |
|---|---|---|---|
| `p_id` | VARCHAR | Produit de la relation | Non isolément |
| `review_id` | INTEGER | Avis relié | Indirectement, via l'auteur |

Cette table peut avoir plusieurs avis par produit. Agréger les avis avant une
jointure avec les faits de vente, sans multiplier les lignes de commande.

## `product`

| Colonne | Type PostgreSQL | Sens | Donnée personnelle ? |
|---|---|---|---|
| `p_id` | VARCHAR | Identifiant produit | Non |
| `p_name` | VARCHAR | Nom du produit | Pas attendu, texte à surveiller |
| `p_desc` | VARCHAR | Description libre | Potentiellement, contenu non classifié |
| `price` | NUMERIC | Prix courant, différent du prix historique d'achat | Non |
| `qty` | INTEGER | Quantité du catalogue / stock, à confirmer avec le producteur | Non |
| `category_id` | INTEGER | Référence de catégorie | Non |

## `customer_shipping`

| Colonne | Type PostgreSQL | Sens | Donnée personnelle ? |
|---|---|---|---|
| `address_id` | INTEGER | Adresse liée au client | Oui, indirectement |
| `c_id` | VARCHAR | Client | Oui, pseudonyme |
| `is_default` | CHAR | Adresse par défaut, observée avec `1` / `0` | Liée au client |

Ce lien décrit l'adresse actuelle. Il ne reconstitue pas l'adresse historique
de chaque commande ; cette limite reste celle du modèle L01.

## `shipping_details`

| Colonne | Type PostgreSQL | Sens | Donnée personnelle ? |
|---|---|---|---|
| `address_id` | INTEGER | Clé d'adresse | Oui, indirectement |
| `street_address` | VARCHAR | Adresse postale | Oui |
| `city` | VARCHAR | Ville | Indirectement dans cette table |
| `state` | VARCHAR | Région administrative | Indirectement dans cette table |
| `zip` | VARCHAR | Code postal, chaîne à préserver | Indirectement |
| `country` | VARCHAR | Libellé de pays | Indirectement dans la ligne d'adresse |
| `phone` | VARCHAR | Numéro de téléphone | Oui |

## Streams sensibles

Ils ne font pas partie des sept streams obligatoires, mais sont synchronisés pour
prouver les exclusions. Les colonnes interdites sont décochées dans la connexion ;
leur absence a été vérifiée dans les fichiers écrits :

| Stream | Colonnes autorisées | Colonnes interdites | Données personnelles restantes |
|---|---|---|---|
| `customer` | `c_id` VARCHAR, `fname` VARCHAR, `lname` VARCHAR, `phone` VARCHAR, `email` VARCHAR | `pwd` | Identifiant, nom, prénom, téléphone et email : oui |
| `payment_details` | `payment_id` INTEGER, `expiry_date` DATE, `billing_address` VARCHAR | `card_no`, `cvv` | Référence et informations liées au paiement : oui |

Le catalogue source peut décrire les colonnes interdites pour permettre de les
désélectionner ; leur description n'autorise pas leur écriture dans bronze.

## Métadonnées Airbyte

Airbyte ajoute ces quatre colonnes à chaque stream ; les types sont ceux lus
dans ses fichiers Parquet. L'extracteur n'en écrit aucune : bronze n'a donc pas
une seule forme, et silver doit savoir de quel chemin vient chaque table.

| Colonne | Type Parquet observé | Sens | Donnée personnelle ? |
|---|---|---|---|
| `_airbyte_raw_id` | string (UUID) | Identifiant de ligne produit par Airbyte | Traçabilité indirecte |
| `_airbyte_extracted_at` | timestamp[ms, UTC] | Heure d'extraction | Pas isolément |
| `_airbyte_meta` | struct `sync_id` int64, `changes` list de struct (`field`, `change`, `reason`) | Synchro d'origine et colonnes modifiées au chargement | Pas attendu : noms de champs, pas de valeurs |
| `_airbyte_generation_id` | int64 | Génération du stream, incrémentée à chaque réinitialisation | Non isolément |

## Clickstream v1

Le [JSON Schema](../ingestion/clickstream.schema.json) fait foi à la frontière.
Les trois types observés sont `product_viewed`, `added_to_cart`, `order_placed`.
Les champs spécifiques ne sont pas obligatoires pour les autres types.

| Champ | Type JSON / Parquet | Sens | Donnée personnelle ? |
|---|---|---|---|
| `schema_version` | integer / int64 | Version du contrat, actuellement 1 | Non |
| `event_id` | string | Identifiant d'événement, utile au rejeu | Indirectement |
| `event_type` | string enum | Type d'action | Indirectement avec une session |
| `event_time` | date-time / string | Moment de l'action ; partition UTC | Indirectement |
| `emitted_at` | date-time / string | Moment d'émission | Indirectement |
| `session_id` | string | Session de navigation | Oui, identifiant pseudonyme |
| `buyer_id` | string ou null | Client, potentiellement absent d'identité connue | Oui lorsqu'il est présent |
| `p_id` | string ou null | Produit consulté ou ajouté | Non isolément |
| `price` | number ou null / double | Prix du produit dans l'événement | Non isolément |
| `qty` | integer ou null / int64 | Quantité ajoutée au panier | Non isolément |
| `order_id` | integer ou null / int64 | Commande passée | Indirectement |
| `payment_method` | string ou null | Mode de paiement, pas un numéro de carte | Indirectement |
| `amount` | number ou null / double | Montant de la commande | Indirectement |
| `currency` | string ou null | Code monétaire sur trois lettres | Non isolément |
| `items` | array ou null / list of struct | Lignes de l'événement de commande | Indirectement avec la commande |
| `items[].p_id` | string | Produit commandé | Non isolément |
| `items[].qty` | integer / int64 | Quantité, strictement positive | Non isolément |
| `items[].price` | number / double | Prix de la ligne | Non isolément |
| `raw_event` | string | JSON reçu, conservé sans nettoyage | Oui, contient les identifiants originaux |
| `_kafka_topic` | string | Topic source | Non isolément |
| `_kafka_partition` | integer / int32 | Partition Kafka | Non isolément |
| `_kafka_offset` | integer / int64 | Position source ; rejouable | Traçabilité indirecte |
| `_ingested_at` | date-time / string | Moment de réception par le job | Non isolément |

Les champs JSON optionnels absents deviennent null dans la projection Parquet ;
`raw_event` conserve la distinction et le texte original. Aucune déduplication
par `event_id` ou offset n'est faite ici.

## DLQ clickstream

| Champ | Type Parquet | Sens | Donnée personnelle ? |
|---|---|---|---|
| `raw` | binary, nullable | Octets exacts reçus ; null pour un tombstone | Potentiellement, contenu non classifié |
| `reason` | string | Motif du rejet, par exemple `/: missing required session_id` | Pas attendu : chemin et nom de champ, sans valeur de l'événement |
| `quarantined_at` | date-time / string | Heure de quarantaine | Non isolément |
| `topic` | string | Topic source | Non isolément |
| `partition` | int32 | Partition Kafka | Non isolément |
| `offset` | int64 | Position rejetée | Traçabilité indirecte |

La DLQ est soumise aux mêmes restrictions de lecture que les données brutes.
Son contenu doit être examiné avant rejeu ; une nouvelle version de schéma ne
rend pas automatiquement tous les rejets valides.
