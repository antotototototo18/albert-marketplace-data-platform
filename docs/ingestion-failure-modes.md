# Pannes et limites de l'ingestion L03

Les trois chemins ont tourné le 16 octobre 2026 avec la stack locale
(PostgreSQL, Kafka, Airbyte) et le bucket du groupe `gs://data-engineering-i1-group6`.
Ce tableau décrit l'état vérifié. Les garanties des scripts ne s'étendent pas
au connecteur : pour Airbyte, la sélection des colonnes est vérifiée, mais le
premier chargement est incomplet (voir la ligne sur la mémoire).

| Cas | Pris en charge ? | Mécanisme / preuve | Conséquence ou limite |
|---|---|---|---|
| Nouvelles commandes à ID croissant | Oui, lorsqu'elles sont visibles dans le snapshot | Curseur `order_id`, checkpoint après fichier ; insertion du même jour retrouvée dans le test réel | Pas de comparaison sur une date tronquée. |
| Modification d'une ancienne commande | **Non** pour le script | L'UPDATE de l'ordre test 1 ne déplace pas son ID ; passage suivant : 0 ligne | Bronze garde l'ancienne valeur. Xmin devrait la capturer côté Airbyte : non testé par le groupe. |
| Suppression source | **Non** pour le script ; non avec Xmin proposé | DELETE test de l'ordre 2 ; sa ligne reste dans bronze | Pas de tombstone ; ne pas interpréter l'absence de nouveaux fichiers comme une suppression. |
| Transaction tardive avec ID inférieur au curseur | **Non** | Les séquences ordonnent l'allocation des IDs, pas les commits ; limite de conception | Prévoir CDC ou une réconciliation si ce cas doit être couvert. |
| PostgreSQL indisponible à la connexion | Oui, tentatives bornées | 5 tentatives ; pauses 1, 2, 4, 8 s par défaut ; test de croissance et d'arrêt | Après échec, arrêt du job. Un échec en cours de requête arrête aussi le job ; reprise au dernier checkpoint. |
| Fichier impossible à écrire | Oui pour la conservation du point de reprise | Test du writer en panne : pas de checkpoint ni de commit Kafka | Le lot sera relu après réparation ; des fichiers partiellement publiés par un lot peuvent être répétés. |
| État GCS modifié par un autre writer | Détecté | Écriture avec `if_generation_match` | Le writer perdant s'arrête ; ses objets déjà écrits peuvent être des doublons. En local, un seul writer est requis. |
| JSON malformé, UTF-8 invalide, champ obligatoire absent ou mauvais timestamp | Oui | Validation avant acceptation ; payload original, motif, heure et position en DLQ. Testé dans le vrai topic : 2 événements sans `session_id` en DLQ, message suivant accepté | Le flux continue après les rejets. Le motif nomme le champ manquant, sans copier de valeur. La DLQ peut contenir des données personnelles. |
| Évolution de schéma | Mise en quarantaine | Version v1 uniquement, propriétés explicites ; version inconnue et champ inattendu testés | Ajouter le contrat avant de rejouer ; pas de propagation silencieuse de colonnes. |
| Doublon après crash / reprise | **Pas de déduplication en bronze** | Fichier avant offset/état ; test d'échec du commit puis rejeu | At least once. Les clés de provenance servent aux tests et à silver. |
| DLQ indisponible | Pas de perte silencieuse | Test : rejet impossible à écrire, donc aucun offset du lot n'est confirmé | Arrêt, puis rejeu de l'ensemble du lot. |
| Rebalance Kafka | Flush avant révocation | Callback `on_revoke`, offsets explicites par partition | Si le broker refuse le commit, arrêt et rejeu possible ; pas d'exactly-once. |
| Kafka indisponible / erreur de poll | Arrêt sur erreur remontée | Pas d'auto-commit ni d'auto-store d'offsets | Pas de bascule de cluster ni d'alerte installée ; le message reste soumis à la rétention du broker. |
| Identifiant PostgreSQL ou Kafka expiré | **Pas de rotation automatique** | Credentials relus au démarrage, tentatives SQL bornées | Corriger les accès puis relancer. Les tokens ADC GCS sont rafraîchis par le SDK quand possible ; un grant retiré arrête les écritures. |
| Clé HMAC Airbyte révoquée | **Non** pour l'alerte | Aucune surveillance installée ; la clé n'expire pas d'elle-même | Les synchros échouent jusqu'à ce qu'une nouvelle clé soit saisie dans la destination. Comportement à confirmer au premier test. |
| Source Airbyte tuée faute de mémoire | **Non** | Constaté le 16/10/2026 : Docker n'a que 7,7 Go, la source PostgreSQL d'Airbyte est tuée (`OOMKilled`, code 137) pendant les synchros 1 et 2 ; Airbyte retente | Les streams déjà validés restent dans bronze. Synchro 2 : 6 streams complets, `product` et `order_items` partiels, `orders` absent. Les synchros planifiées échoueront tant que Docker n'aura pas plus de mémoire (12 Go proposés). |
| Mauvais mode de synchro choisi | Corrigé à la main | Synchro 1 lancée en Full refresh \| Overwrite par erreur, puis annulée après 2 tentatives : `review` avait 149 179 lignes pour 111 322 en base | Les 11 fichiers de cette synchro (`_airbyte_meta.sync_id = 1`) ont été supprimés le 16/10/2026 après vérification. Le mode est désormais vérifié par `check_airbyte_export`. |
| Rétention Kafka dépassée avant reprise | **Non** | Aucun archivage Kafka supplémentaire dans ce lot | Les messages expirés ne sont pas récupérables par ce consumer. |

## Résultats mesurés

- [Test isolé dans la vraie stack](evidence/l03-validation.json) : 2 commandes,
  puis 1 insertion du même jour ; après UPDATE/DELETE, 0 ligne supplémentaire.
  Kafka : 2 événements acceptés, 1 rejet exact en DLQ, événement valide suivant retrouvé.
- [Chargement des vraies sources](evidence/l03-live-run.json) : 228 028 commandes
  au premier passage, 2 supplémentaires après reprise ; 47 objets Parquet,
  9 007 781 octets. Clickstream : 69 335 événements acceptés depuis le début du
  topic, 152 objets sur 22 jours d'`event_time`, 2 rejets volontaires en DLQ.
- Airbyte, synchro 2 (Incremental | Append) : `customer`, `customer_shipping`,
  `payment_details`, `product_reviews`, `review` et `shipping_details` complets ;
  `product` (23 012 / 42 858) et `order_items` (95 379 / 418 832) partiels ;
  `orders` absent. Aucun fichier ne contient `pwd`, `card_no` ou `cvv`.
- Rendu individuel L03 fourni : 51 doublons parmi 2 409 lignes après deux
  interruptions ; 12 commandes manquées par `order_date > curseur` ; slot CDC
  conservant 127 kB de WAL. Ces résultats restent distincts des essais de ce lot.

## Accès utilisés

| Accès | Emplacement et lecteur | État dans ce lot |
|---|---|---|
| PostgreSQL | `DATABASE_URL` dans l'environnement du job ; fichier `.env` local exclu de Git si utilisé | Le test a utilisé la connexion locale déjà fournie avec l'exercice. Aucun DSN réel n'est enregistré dans le code ou les preuves. |
| GCS | Application Default Credentials locales, lues par `google-cloud-storage` sous le compte qui lance le job | Bucket `data-engineering-i1-group6`. Aucune clé de compte de service ou HMAC n'est utilisée par les scripts. |
| Kafka local | `KAFKA_BOOTSTRAP` et `CONSUMER_GROUP` | Broker local sans nouveau secret créé. TLS/SASL éventuel via `KAFKA_CLIENT_CONFIG`, fichier `*.local.json` ignoré. |
| Airbyte | Mot de passe de la source et clé HMAC de la destination, stockés dans l'instance Airbyte locale (cluster `abctl` sur la machine d'Anthony) ; lisibles par qui a accès à cette machine et à l'UI | Connexion créée le 16/10/2026. La clé HMAC est consignée dans la section suivante. |

Lecteurs actuels du bucket, lus sur sa politique IAM le 16/10/2026 : seulement
les rôles par défaut du projet `data-engineering-i1` (propriétaires et éditeurs
en lecture/écriture, lecteurs du projet en lecture). Aucun binding propre au
groupe n'existe encore ; c'est un livrable L02 non traité.

Ne pas publier de fichier `.env`, de fichier TLS/SASL ni d'export complet
Airbyte : il peut embarquer la configuration des acteurs. Le vérificateur
produit une preuve limitée au catalogue et à la sélection des colonnes.

Les fichiers bronze restent personnels ou indirectement identifiants ; les
exclusions de `pwd`, `card_no` et `cvv` ne rendent pas les autres colonnes anonymes.

## Slots et clés

Le 16/10/2026, `pg_replication_slots` est vide : les scripts n'en créent pas, et
le slot `cdc_ar` de l'exercice a bien été supprimé. Xmin n'en crée pas non plus.
Avant de clore le connecteur, relister :

```sql
SELECT slot_name, active, restart_lsn FROM pg_replication_slots;
```

Pour un slot de test identifié et inutilisé, sa suppression est :

```sql
SELECT pg_drop_replication_slot('nom_du_slot_de_test');
```

Ne pas supprimer tous les slots : ceux d'une autre connexion peuvent être actifs.

La destination GCS d'Airbyte exige une clé HMAC, qui reste valide tant qu'on ne
la révoque pas. Compléter ce tableau à sa création, sans jamais noter le secret :

| Clé | Propriétaire | Créée le | Usage | État |
|---|---|---|---|---|
| `GOOG4JERZPTQRBWYSKDYXBVP` | Compte utilisateur Google d'Anthony Rascle (repli) | 2026-10-16 | Destination Airbyte vers `bronze/airbyte/` | Active |

Le 16/10/2026, le compte étudiant n'a pu créer ni le compte de service
(`iam.serviceAccounts.create` refusé), ni une clé HMAC de compte de service
(`storage.hmacKeys.list` refusé). La clé est donc une clé de compte utilisateur,
créée depuis la console. Elle porte **tous les droits de ce compte** sur le
projet, pas seulement le bucket du groupe : c'est un écart au moindre privilège,
à corriger dès qu'un compte de service limité au bucket est disponible.
Le secret n'est stocké que dans la destination Airbyte locale.

Révocation de cette clé utilisateur : console Cloud Storage → Paramètres →
Interopérabilité → clé `GOOG4JERZPTQRBWYSKDYXBVP` → Désactiver, puis Supprimer.
Les commandes `gcloud storage hmac` ne gèrent que les clés de comptes de service.
Si un compte de service est créé plus tard, sa clé se révoque ainsi :

```sh
gcloud storage hmac update ACCESS_ID --deactivate
gcloud storage hmac delete ACCESS_ID
gcloud storage hmac list --service-account=airbyte-bronze-writer@data-engineering-i1.iam.gserviceaccount.com
```

## Refaire les essais

Suivre les commandes dans [ingestion/README.md](../ingestion/README.md).
`scripts.verify_ingestion` crée une table et un topic à noms uniques, puis les
supprime avec le consumer group. Il conserve les fichiers de preuve dans
`bronze/_validation/` et le rejet dans `bronze/_dlq/clickstream/`.
Les événements synthétiques valides ne sont jamais mélangés au préfixe métier
`bronze/clickstream/v1/`.
