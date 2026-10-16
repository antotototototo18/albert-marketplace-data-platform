# Flux de données d'Albert's Marketplace

Version L01, proposée à la relecture du groupe le 16 octobre 2026. Le diagnostic
reprend le notebook `Exercise/L01/EX1-diagnose/data_flow_mapping.ipynb` fourni
avec les exercices. Les ajouts cibles viennent des consignes L02 à L05.

## Situation actuelle décrite dans le brief

| # | Source | Données | Consommateur | Fréquence | Format | Observation |
|---|---|---|---|---|---|---|
| A1 | Clients et vendeurs | Comptes, commandes, produits, avis, informations de paiement | Boutique web | À chaque action | Formulaires web / JSON | Le parcours opérationnel reçoit aussi des secrets et des données personnelles. |
| A2 | Boutique web | Créations et modifications des données métier | PostgreSQL opérationnel | Au fil des transactions | Écritures SQL | Le brief décrit une base de 25 tables, commune à la boutique et aux analystes. |
| A3 | PostgreSQL | Catalogue, comptes et commandes affichés | Boutique web | À chaque consultation | Résultats SQL | Ces lectures servent les clients ; elles partagent les ressources avec A4. |
| A4 | PostgreSQL | Tables utilisées pour les analyses | Analystes | À la demande | SQL direct | Les analyses peuvent concurrencer le checkout et exposer des colonnes sensibles. |
| A5 | PostgreSQL | Exports des tables | Fichiers CSV | Chaque nuit | CSV | Le périmètre exact des colonnes exportées doit être inventorié ; ne pas supposer une exclusion des secrets. |
| A6 | Exports CSV | Données arrêtées à l'export de la nuit | Tableurs des analystes | Quotidienne, ouverture manuelle | CSV puis classeurs | Copies locales et transformations difficiles à tracer. |
| A7 | Requêtes directes et tableurs | Agrégats, dont le chiffre d'affaires | Rapports métier | À la demande | Résultats SQL et classeurs | Fraîcheur et définitions peuvent différer selon le rapport. |
| A8 | Aucun producteur industrialisé dans le brief | Unités par produit, pays et jour | Équipe ML | Besoin quotidien | Table attendue | Besoin cible, pas un flux existant. Le notebook démontre une forme sur une base simulée. |

## Flux de la plateforme cible

Ces flux sont prévus dans [l'architecture](architecture.md) ; leur présence dans
cette matrice ne constitue pas une preuve de déploiement.

| # | Source | Données | Consommateur | Fréquence cible | Format | Étape et contrat |
|---|---|---|---|---|---|---|
| C1 | Exports autorisés / PostgreSQL | Tables relationnelles dont commandes, lignes, produits et adresses nécessaires | Bronze GCS | Chargement initial, puis batch quotidien proposé | CSV source / SQL vers Parquet | L02-L03. Exclure `pwd`, `card_no`, `cvv` avant écriture ; préserver ensuite le contenu métier reçu. |
| C2 | PostgreSQL | Sept streams requis : `orders`, `order_items`, `review`, `product_reviews`, `product`, `customer_shipping`, `shipping_details` | Connecteur vers bronze GCS | Incrémental ; cadence et mode à justifier en L03 | Parquet et métadonnées du connecteur | Curseur ou CDC à décider à partir des essais ; ne pas promettre la capture des mises à jour et suppressions avec un simple identifiant croissant. |
| C3 | Topic Kafka `clickstream` | Événements de navigation versionnés | Consumer vers bronze GCS | Lecture continue, écriture par lots | JSON vers Parquet | L03. Schéma validé avant acceptation ; garantie de livraison à démontrer par les tests de panne. |
| C4 | Consumer clickstream | Événement invalide, motif, horodatage et position Kafka | `bronze/_dlq/` | À chaque rejet | Enveloppe de quarantaine persistée | L03. Un événement invalide reste retrouvable et ne bloque pas les événements valides. |
| C5 | Bronze GCS | Jeu de travail des tables nécessaires aux analyses | Tables natives de chargement BigQuery | Après ingestion réussie | Parquet vers tables natives | L04. Les fichiers bronze restent la référence de rejeu ; toutes les tables ne sont pas chargées par principe. |
| C6 | Tables de chargement BigQuery | Données typées, dédupliquées et jointures maîtrisées | Silver, via dbt | Quotidienne proposée | SQL | L05. Un seul traitement par défaut documenté ; préserver les preuves dans bronze. |
| C7 | Silver | Faits de commande, dimensions et demande quotidienne | Gold, via dbt | Après tests des dépendances | Tables SQL | L05. Grain déclaré et testé ; sens de chaque mesure explicite. |
| C8 | Gold | Mesures partagées et jeux de données autorisés | Analystes, rapports et équipe ML | Après publication, consultation à la demande | SQL / extraction contrôlée | Écarter les identifiants personnels des agrégats ML ; ne plus reconstruire les métriques depuis l'OLTP ou les CSV. |

La demande quotidienne ML n'impose pas une alimentation en temps réel. Le
clickstream continu est une exigence L03 distincte ; le SLA de publication gold
reste à convenir avec le groupe.

## Quels flux portent des données personnelles ?

A1-A6 peuvent transporter des identifiants clients, noms, coordonnées et
informations de paiement. Les mots de passe et données de carte ne sont pas
nécessaires à l'analytique et ne doivent pas franchir la frontière d'ingestion.
C1-C2 conservent encore des identifiants et adresses autorisés : retirer les
secrets ne rend pas ces données anonymes. C3-C4 peuvent contenir `buyer_id`,
`session_id` et du contenu libre ; la quarantaine requiert donc aussi des accès
restreints. A7 et C8 doivent être évalués selon les colonnes effectivement
exposées, même lorsqu'il s'agit d'agrégats.

## Quels consommateurs lisent le système qui sert les clients ?

La boutique (A3) et les analystes (A4) interrogent la même base PostgreSQL ;
l'export nocturne (A5) la lit aussi. La cible déplace les analyses vers BigQuery,
mais l'extraction PostgreSQL garde une charge sur la source : son mode, sa
fréquence et ses volumes devront être mesurés en L03.

## Où un même chiffre peut-il être calculé différemment ?

A7 combine des calculs SQL sur l'état courant et des calculs manuels sur des
exports plus anciens. Des règles différentes sur remises, taxes, annulations,
retours, dates ou devises peuvent produire des chiffres différents ; ce sont
des causes à vérifier, pas des règles déjà établies pour le schéma legacy.
La cible publie une définition par métrique dans gold, avec ses limites de
source et ses tests. Le [modèle quotidien](model/star-daily-demand.md) précise
notamment pourquoi les colonnes disponibles ne prouvent pas qu'une commande
est payée.
