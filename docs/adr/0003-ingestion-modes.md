# ADR-0003: Xmin pour le connecteur, curseur d'ID pour l'extracteur, Kafka au moins une fois

- **Status:** proposed — à relire par le groupe
- **Date:** 2026-10-16
- **Author:** Anthony Rascle
- **Lesson:** L03

## Context

Le bronze du groupe est le bucket `data-engineering-i1-group6`, créé le
16 octobre 2026 dans `europe-west1`, avec accès uniforme et accès public bloqué.
Chaque chemin d'ingestion écrit dans son propre préfixe de `bronze/`. Les livrables
L02 (ADR-0002, lifecycle, IAM, coûts) ne sont pas faits : le bucket n'a ni règle
de lifecycle ni binding au-delà des rôles par défaut du projet.

Les essais individuels L03 donnent trois éléments : le curseur strict sur
`order_date` a manqué 12 nouvelles commandes du même jour ; relire la journée
a répété 32, puis 44 lignes ; deux interruptions du consumer ont produit
51 doublons sur 2 409 lignes, dont 2 358 événements distincts. Un slot CDC a
retenu 127 kB de WAL et montré l'insertion, la modification puis la suppression
de `EX1AR`, invisibles à un batch ultérieur. Ce sont les mesures du rendu
`Exercise/L03/EX1-ingest-three-ways/README.md`, pas de nouveaux essais du connecteur.

Les [essais isolés](../evidence/l03-validation.json) utilisent une table et un
topic temporaires, avec des écritures réelles dans le bucket du groupe : deux
commandes initiales, une insertion du même jour retrouvée après reprise, une
modification et une suppression non capturées ; côté Kafka, deux événements
acceptés et un rejet persisté, suivi d'un événement valide traité.

Le [chargement réel](../evidence/l03-live-run.json) a écrit 228 028 commandes
(47 objets, 9,0 Mo), puis 2 de plus à la reprise. Le consumer a rattrapé
69 335 événements valides sur 22 jours d'`event_time` (152 objets, 16,3 Mo).
Deux événements cassés envoyés dans le vrai topic sont en DLQ, et le message
suivant de chaque partition a été accepté.

## Options considered

| Source | Option retenue ou proposée | Alternative écartée et raison |
|---|---|---|
| Extracteur `orders` | `order_id > curseur`, SQL avec psycopg, état durable après écriture | Date seule : trop grossière. Relecture complète : coûteuse et répétitive. Un identifiant ne capture toutefois pas les mises à jour, suppressions ou transactions tardives sous le curseur. |
| Sept streams Airbyte requis | Xmin, Incremental \| Append vers GCS, toutes les 24 heures | Standard avec curseur manuel sur `p_id` ou une date : l'exercice a montré que la correction de prix sous le curseur n'arrive jamais. CDC : capture les suppressions, mais exige une publication et un slot qui retient le WAL (127 kB en quelques minutes dans l'exercice) ; à retenir si les suppressions deviennent nécessaires. |
| Clickstream | Consumer `confluent-kafka`, schéma v1 explicite, fichiers puis commit synchrone des offsets | Commit avant fichier : risque de perte. Exactly-once entre Kafka et GCS : absence de transaction commune dans ce code. |

## Criteria

- **Complétude :** annoncer les changements effectivement observables et les cas manqués.
- **Reprise :** conserver le curseur dans GCS et ne confirmer Kafka qu'après les sorties valides et la DLQ.
- **Sécurité :** sélectionner les colonnes avant ingestion ; lire les accès dans l'environnement ou ADC.
- **Exploitabilité :** schéma versionné, rejets consultables et tests de panne reproductibles.
- **Coût :** éviter un objet par ligne et séparer les producteurs pour pouvoir tracer leurs doublons.

## Decision

L'extracteur utilise psycopg sans ORM et un snapshot PostgreSQL repeatable-read.
Il écrit les cinq colonnes de `orders` en Parquet Snappy dans
`bronze/manual/orders/ingested_date=YYYY-MM-DD/`. Le jour d'ingestion évite de
morceler chaque page du backfill entre les trois années de dates métier ;
`order_date` est conservée dans la ligne. Dans le bucket du groupe, les deux
passages ont produit 47 objets, soit 9 007 781 octets ; voir le
[compte rendu](../evidence/l03-live-run.json).

Le cursor checkpoint est écrit après chaque fichier. Sur GCS, une précondition
de génération empêche d'écraser un état modifié entre-temps. Un crash entre
fichier et état répète les lignes, sans réécrire les objets existants. Le mode
local sert aux tests avec un seul writer ; il ne fournit pas de verrou distribué.

Le consumer partitionne selon **`event_time` converti en UTC**, pour conserver
le jour métier malgré un événement reçu plus tard. Il préserve le JSON original
dans `raw_event`. Les événements invalides vont dans `bronze/_dlq/clickstream/`,
partitionnés par date de quarantaine, même si leur timestamp est absent.
Les offsets explicites de chaque partition ne sont confirmés qu'après tous les
fichiers du lot. Cette garantie est **at least once**, dans les limites de la
rétention Kafka et d'un stockage durable disponible.

Airbyte alimente son propre préfixe `bronze/airbyte/`, en Incremental | Append
avec la méthode Xmin et une synchronisation toutes les 24 heures. Sa clé HMAC est
pour l'instant celle d'un compte utilisateur, faute de droit pour créer un compte
de service : elle donne plus de droits que nécessaire. Son catalogue contient les sept streams imposés, plus `customer` et
`payment_details` avec `pwd`, `card_no` et `cvv` décochés. La procédure est dans
[ingestion/README.md](../../ingestion/README.md#raccorder-airbyte). La connexion
a été créée le 16/10/2026. Les fichiers écrits ne contiennent ni `pwd`, ni
`card_no`, ni `cvv`, et portent les quatre colonnes `_airbyte_*`. La première
synchro incrémentale s'est arrêtée faute de mémoire dans Docker : 6 streams
complets, `product` et `order_items` partiels, `orders` absent. La capture
d'une mise à jour par Xmin n'a pas été testée par le groupe.

## Consequences

Les rejets ne disparaissent pas et une panne d'écriture ne fait pas avancer
les offsets ou le curseur du lot concerné. Les relectures créent toutefois des
doublons, à traiter en silver avec provenance et clés. Le batch manuel manque
les modifications, suppressions et insertions dont l'ID devient visible après
le passage du curseur. Xmin ne résout pas les suppressions : si elles deviennent
nécessaires, il faudra tester CDC et documenter la suppression des slots inutilisés.

Airbyte local demande plus de mémoire que les 7,7 Go donnés à Docker : sans
correction, ses synchros planifiées échouent et `orders` n'arrive que par
l'extracteur. Une nouvelle version de schéma doit être ajoutée et testée avant acceptation ;
une version inconnue reste en DLQ. Les reprises automatiques après expiration
d'un secret, les alertes et le scheduling complet restent à mettre en place
ou à raccorder. Les tests et les limites sont détaillés dans
[ingestion-failure-modes.md](../ingestion-failure-modes.md).
