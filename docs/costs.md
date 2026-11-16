# Coûts de la plateforme

Fichier enrichi à chaque leçon ; il sert d'entrée au travail FinOps de L09.

La [mesure L09 du 10 novembre](#l09--attribution-et-optimisation-mesurée)
actualise l'inventaire. Les sections L02 et L04 ci-dessous restent des relevés
historiques, avec leurs dates et hypothèses.

## Tarifs utilisés

Lus le **16 octobre 2026** sur la [page de tarification de Cloud Storage](https://cloud.google.com/storage/pricing),
pour un bucket mono-région `europe-west1` (Belgique), en USD. Selon la page,
les dernières hausses sont entrées en vigueur le 1er octobre 2022 et le
1er avril 2023.

| Classe | Stockage (par GiB et par mois) | Opérations classe A (par 1 000) | Opérations classe B (par 1 000) | Frais de lecture (par GiB) | Durée minimale |
|---|---|---|---|---|---|
| Standard | $0.02 | $0.005 | $0.0004 | $0 | aucune |
| Nearline | $0.01 | $0.01 | $0.001 | $0.01 | 30 jours |
| Coldline | $0.004 | $0.02 | $0.01 | $0.02 | 90 jours |
| Archive | $0.0012 | $0.05 | $0.05 | $0.05 | 365 jours |

Points qui s'appliquent à notre cas :

- **Opérations :** les écritures (A) et les lectures ou listages (B) sont
  facturées par 1 000 requêtes. Les tarifs ci-dessus valent pour un espace de
  noms plat, celui de notre bucket.
- **Free tier :** il ne s'applique pas. Le quota gratuit (5 Go-mois) ne couvre
  que `us-west1`, `us-central1` et `us-east1`.
- **Transfert :** les données qui restent dans la même région sont gratuites.
  Un dataset BigQuery en `europe-west1` qui lit le bucket ne paie donc aucun
  transfert. Un téléchargement vers Internet coûte $0.12 par GiB.
- **Suppression :** un objet supprimé reste facturé 7 jours, la durée de la
  suppression réversible du bucket.

## L02 — bronze sur Cloud Storage

État du bucket `gs://data-engineering-i1-group6` le 16 octobre 2026.

| Élément | Volume | Coût mensuel | Source du volume |
|---|---|---|---|
| `bronze/legacy/`, 27 fichiers Parquet | 62 328 870 o = 0,0580 GiB | $0.00116 | [manifeste](evidence/l02-bronze-legacy-manifest.json) |
| `bronze/manual/`, `bronze/clickstream/` et préfixes techniques (L03), en croissance | 25 337 171 o = 0,0236 GiB | $0.00047 | `gcloud storage du -s`, moins `legacy/` |
| **Total stockage, classe Standard** | **87 666 041 o = 0,0816 GiB** | **$0.0016 par mois** | |

Opérations :

| Opération | Nombre | Coût |
|---|---|---|
| Écriture du chargement legacy (classe A) | 27 objets | $0.00014, une fois |
| Écritures L03 déjà présentes (classe A) | 207 objets | $0.00104, une fois |
| Lecture complète du legacy pour le chargement BigQuery de L04 (classe B) | 27 objets | $0.00001 par chargement |

**Effet du [lifecycle](../infra/lifecycle.json)** sur `bronze/legacy/` :

- **Calendrier :** Standard le premier mois, Nearline jusqu'à 90 jours, puis
  Coldline jusqu'à un an.
- **Coût sur la première année :** environ **$0.005**, transitions comprises
  (27 × $0.01 + 27 × $0.02 pour 1 000 opérations). Sans lifecycle, ce serait
  $0.014.
- **Contrepartie :** une relecture complète après 30 jours coûte $0.0006 de
  frais de récupération. Les chargements de L04-L05 doivent donc avoir lieu
  dans le premier mois, ou accepter ce coût.

À ce volume, la facture est inférieure à un centime par mois. Le format compte
déjà : les mêmes données en CSV (206 290 602 o) coûteraient 3,3 fois plus cher
à stocker.

## L04 : warehouse BigQuery

État de `group6_warehouse` le 26 octobre 2026
([mesures](evidence/l04-warehouse-measurements.json)). Le choix du compteur est
dans l'[ADR-0004](adr/0004-warehouse-pricing.md).

| Élément | Volume | Coût | Source |
|---|---|---|---|
| Tables natives, vue `daily_demand` comprise | 219 602 295 o de stockage logique, dont 88 253 584 o de copies de mesure (`*_untuned`, `order_items_day`) | ~$0.004 par mois à $0.020 par GiB-mois (tarif du cours L04) ; moitié moins après 90 jours sans modification | Tailles lues par l'API BigQuery |
| Tables externes `group6_bronze` | Aucune ligne stockée | $0 ; chaque requête relit le bucket | |
| Requête type du projet, à la demande | 4 à 13 Mo traités, 10 à 40 Mio facturés (minimum de 10 Mio par table lue) | $0.00007 à $0.0003 par requête, dans le Tio gratuit mensuel | [warehouse-tuning.md](warehouse-tuning.md) |
| Plafond par requête | 1 GiB | Au plus $0.0073 par requête avant refus ; un refus ne coûte rien | Jobs refusés, `JOBS_BY_USER` |

Supprimer les copies de mesure après relecture retire 40 % du stockage.

## Si les données étaient cent fois plus volumineuses

Le legacy passerait à 5,8 GiB, soit environ $0.12 par mois en Standard
($0.16 pour tout le bucket). Le layout actuel reste sobre en opérations : un
chargement écrit toujours 27 objets.

Ce qui changerait vraiment :

- **Partitionner par jour coûterait cher en opérations.** Il faudrait environ
  46 600 objets par chargement ($0.23 en écritures), multipliés par le nombre de
  lectures et de listages.
- **Des instantanés complets quotidiens rendraient le stockage dominant.**
  Ils ajouteraient environ $3.50 par mois, de façon cumulative. Il faudrait
  alors passer à l'incrémental ou au CDC (L03) et rendre le lifecycle
  indispensable.
- **Un téléchargement complet hors de GCP** coûterait environ $0.70 de
  transfert par copie.

## L09 — Attribution et optimisation mesurée

Relevé du **10 novembre 2026**, région `europe-west1`, sur `antho`.
Les [mesures](evidence/l09/inventory.json) viennent des API de métadonnées et de
`INFORMATION_SCHEMA.JOBS_BY_PROJECT`, pas d'une facture. Aucun dataset d'export
de facturation n'a été identifié parmi ceux visibles. Le
[SQL de facturation](../warehouse/queries/l09_billing_daily.sql) est prêt pour
la vue que fournira l'enseignant ; son nom reste à renseigner.

### Convention de labels

| Clé | Valeur | Pourquoi |
|---|---|---|
| `team` | `group6` | Retrouver le responsable dans le projet partagé. |
| `environment` | `course` | Distinguer les exercices d'un futur environnement de production. |
| `pipeline` | `marketplace` | Rassembler ingestion, transformation et analyse du même produit. |
| `component` | `bronze`, `warehouse`, `silver`, `gold`, `finops`, `quality` ou `transform` | Séparer les usages qui font varier la consommation. |

Cette convention est proposée à la relecture du groupe. Le bucket bronze et les
quatre datasets ont reçu leurs quatre labels **par Terraform** : plan limité
à cinq mises à jour de labels, application réussie, puis plan sans changement.
Voir [labels.tf](../infra/terraform/labels.tf) et les
[vérifications](evidence/l09/validation.txt).

Les cinq ressources IAM n'acceptent pas de labels et n'ont pas de coût direct :
on les rattache au dataset qu'elles protègent. Le budget ne possède pas non plus
de labels ; le canal Monitoring utilise `user_labels`, ses `labels` techniques
servant à l'adresse e-mail. Le bucket d'état, amorcé hors Terraform en L08,
reste sans labels ; son coût est suivi par son nom dans le registre.

**Les labels ne s'appliquent qu'à partir de leur pose.** L'historique précédent
reste sans attribution par labels. Les jobs passés sont rapprochés du groupe
par leurs tables référencées `group6_*`, ce qui est une approximation : un job
qui lit plusieurs équipes ne peut pas être ventilé avec cette seule méthode.

Les tables et vues BigQuery n'héritent pas des labels des datasets, et les
requêtes ont leurs propres labels. Les futurs modèles et jobs dbt portent donc
la convention ; la sonde `dbt show SELECT 1` a confirmé les quatre labels sur
un vrai job, et les configurations des 16 modèles ont été vérifiées
([preuve](evidence/l09/job-label-probe.json)). Les anciens modèles ne sont pas
réécrits pour ce test : leurs labels de tables seront posés au prochain build.
Les commandes `bq load` et `bq query` du DAG ont également les labels de jobs.
Les jobs manuels sans ces options restent non attribués.

Références : [labels BigQuery](https://docs.cloud.google.com/bigquery/docs/adding-labels),
[labels des jobs dbt](https://docs.getdbt.com/reference/resource-configs/bigquery-configs#applying-labels-to-jobs).

### Budget et destinataire : création bloquée

Le [budget Terraform](../infra/terraform/budget.tf) propose **10 USD par mois**,
avec seuils réels à 50 %, 90 % et 100 %, vers **Anthony Rascle,
`arascle@albertschool.com`**. Il couvre tout le projet pédagogique partagé,
pas seulement le groupe 6 : une requête non labellisée reste dans son périmètre.
Les crédits sont inclus dans le calcul, donc ils peuvent retarder un seuil.

**Ce budget n'existe pas encore et aucun e-mail de budget n'a été reçu.**
L'API `billingbudgets.googleapis.com` est désactivée, et la tentative
d'activation retourne `PERMISSION_DENIED` sur `serviceusage.services.enable`
([constat](evidence/l09/budget-access.json)). `enable_budget_alert` reste donc
à `false`. Aucun droit projet ni accès au compte de facturation n'a été ajouté.

À faire avec l'administrateur : activer l'API, confirmer la devise et le montant
dans le compte de facturation, puis accorder l'accès de gestion du budget et
du canal. Revoir `terraform plan -var=enable_budget_alert=true`, appliquer le
plan approuvé et vérifier le budget, le destinataire et la réception d'une
notification quand un seuil est atteint. Cette réception reste à prouver.

**A budget alert does not stop spending** : elle prévient avec un délai de
remontée des coûts ; elle ne coupe ni les jobs ni la facturation. Le plafond
BigQuery de 1 GiB par requête reste une protection distincte.
[Fonctionnement des budgets](https://docs.cloud.google.com/billing/docs/how-to/budgets).

### Poste principal et forme de consommation

Le repli sur les unités porte sur **30 jours, du 11 octobre inclus au
10 novembre exclu**. Il écarte les sondes L09 du 10 novembre. Le
[SQL quotidien](../warehouse/queries/l09_jobs_daily.sql) exclut les parents
`SCRIPT` pour ne pas recompter leurs requêtes enfants, ainsi que les échecs.

| Jour UTC | Jobs | Octets traités | Octets facturables avant franchises |
|---|---:|---:|---:|
| 2026-10-26 | 89 | 853 150 018 | 1 373 634 560 |
| 2026-10-29 | 1 | 0 | 0 |
| 2026-11-03 | 110 | 632 045 324 | 1 275 068 416 |
| 2026-11-06 | 1 358 | 6 622 429 115 | 15 409 872 896 |
| Total | 1 558 | 8 107 624 457 | 18 058 575 872 |

La forme observée est celle de **pics de traitements batch**, surtout le
6 novembre (tests, builds et backfills L07), plutôt qu'une charge continue.
Les jours sans job sont absents de la source ; leur absence n'est pas une
preuve d'absence de coûts de stockage. Cette fenêtre ne prouve pas encore
un rythme quotidien stable du DAG.

Le poste estimé le plus élevé sur ce périmètre est **BigQuery, SKU d'analyse
à la demande en Belgique** : 16,818 GiB facturables × $7.50/TiB ≈ **$0.1232**
sur la fenêtre, avant franchise et crédits. Le `sku.id` exact et le classement
de la facture restent à confirmer avec l'export. Ce montant dépasse les postes
de stockage estimés à volume constant ci-dessous, mais n'est pas une dépense
réellement débitée. La franchise BigQuery est partagée au niveau du compte :
on ne peut pas affirmer que notre groupe dispose encore du TiB gratuit.

### Optimisation : rendre la partition visible

Cas mesuré sur les données réelles : demande par produit et jour de septembre
2026, dans `group6_gold.fct_order_items`, déjà partitionnée par mois en L05.
Le [cas initial](../warehouse/queries/l09_monthly_demand_before.sql) utilise une
regex sur la date convertie en texte ; la
[requête retenue](../warehouse/queries/l09_monthly_demand.sql) utilise une plage
de dates, début inclus et fin exclue. Le cas initial est une sonde construite
pour L09 ; ce n'est pas une régression attribuée au DAG existant.

| Mesure du 10 novembre | Avant : regex | Après : plage de dates |
|---|---:|---:|
| Octets traités | 5 719 840 | 69 384 |
| Octets facturés | 10 485 760 | 10 485 760 |
| Résultats | 2 440 lignes | 2 440 lignes, identiques |
| Cache | Désactivé | Désactivé |
| Prix théorique des octets traités à $7.50/TiB | $0.0000390 | $0.000000473 |
| Prix des octets facturés, avant franchise | $0.0000715 | $0.0000715 |

**98,79 % d'octets traités en moins, zéro économie monétaire mesurable à cette
taille** : les deux requêtes restent sous le minimum facturé de 10 MiB.
Les slot-ms passent de 152 à 18 sur cette paire ; une seule exécution ne suffit
pas à en déduire un gain de latence stable.

Le [script de mesure](../scripts/measure_finops.py) compare toutes les pages de
résultats triés et publie seulement leurs empreintes et statistiques. Les
[empreintes sont identiques](evidence/l09/optimization.json). L'optimisation
serait refusée si les résultats divergeaient ; une absence de baisse des octets
sur une autre période invaliderait le gain attendu. Ne pas extrapoler le
pourcentage à toute la pipeline.

### Registre des ressources et prix

Tarifs USD d'`europe-west1` relus le **10 novembre 2026** :
[BigQuery](https://cloud.google.com/bigquery/pricing),
[Cloud Storage](https://cloud.google.com/storage/pricing),
[Artifact Registry](https://cloud.google.com/artifact-registry/pricing).
Le [relevé des tarifs](evidence/l09/prices.json) distingue la région Belgique
du tableau Iowa affiché par défaut. Les estimations sont hors franchises,
crédits, taxes, opérations et transferts, avec un volume figé pendant un mois.

| Ressource | Ce qui fait varier le coût | Prix unitaire au 10/11/2026 | Estimation USD/mois |
|---|---|---|---:|
| Bucket bronze | 1 171 013 274 octets Standard, 316 versions d'objets | $0.02/GiB-mois | 0.021812 |
| Bucket d'état | 91 784 octets Standard, 25 versions | $0.02/GiB-mois | 0.000002 |
| Dataset bronze | 31 790 730 octets natifs ; les tables externes restent dans GCS | $0.02/GiB-mois logique actif | 0.000592 |
| Dataset warehouse | 219 602 295 octets logiques, copies L04 comprises | $0.02/GiB-mois logique actif | 0.004090 |
| Dataset silver | Vues, pas de données stockées | $0 de stockage ; requêtes à $7.50/TiB | 0 |
| Dataset gold | 34 085 635 octets logiques | $0.02/GiB-mois logique actif | 0.000635 |
| IAM `writer[bronze_arabeau]` | Aucun coût direct de liaison | $0 | 0 |
| IAM `writer[bronze_csibieude]` | Idem | $0 | 0 |
| IAM `writer[warehouse_arabeau]` | Idem | $0 | 0 |
| IAM `writer[warehouse_csibieude]` | Idem | $0 | 0 |
| IAM `bronze_reader_arabeau` | Idem | $0 | 0 |
| Images `dataeng/group6-ingestion` | 248 471 635 octets cumulés de manifestes | $0.10/GiB-mois | ~0.023141 |
| Images `dataeng/group6-transform` | 449 732 688 octets cumulés de manifestes | $0.10/GiB-mois | ~0.041884 |
| Image `dataeng/group6-retention-probe` | 447 octets déclarés par l'API | $0.10/GiB-mois | <0.000001 |
| Canal e-mail et budget proposés | Désactivés, aucune ressource créée | Pas de coût d'alerte budgétaire | 0 |

Le [registre CSV détaillé](evidence/l09/resource-ledger.csv) comporte **55 lignes**,
dont une par table ou vue des quatre datasets (39), avec prix, date, formule
et source. Il compte le stockage BigQuery dans les lignes des tables uniquement,
pour ne pas additionner deux fois datasets et tables. Total de stockage estimé :
**environ $0.0922/mois**, distinct des $0.1232 d'analyse sur la fenêtre historique.

Les tailles Artifact Registry peuvent recompter les couches partagées ; elles
ne donnent pas le stockage facturé exact. Sa franchise de 0,5 GiB est également
partagée. GCS compte ici les versions et objets supprimés réversibles observés
(zéro objet supprimé réversible au relevé). BigQuery est estimé au tarif actif,
sans attribuer au groupe une franchise commune.

Les datasets personnels `group6_l07_*`, le PostgreSQL fourni par le cours et
les autres groupes restent hors de ce registre de stockage partagé. Leurs
coûts ne sont pas supposés nuls. Airflow et Docker tournent localement : aucun
Composer ou serveur GCP dédié au groupe n'a été déclaré.

### Reproduire et terminer L09

```sh
python -m pip install -r warehouse/requirements.txt
python scripts/capture_finops.py --end-date 2026-11-10 --output docs/evidence/l09/inventory.json
python scripts/measure_finops.py --month 2026-09 --output docs/evidence/l09/optimization.json
python scripts/build_finops_ledger.py --inventory docs/evidence/l09/inventory.json --output docs/evidence/l09/resource-ledger.csv
```

L'authentification utilise les ADC personnelles, comme dbt. Les scripts cloud
bornent chaque requête à 1 GiB et désactivent le cache pour la mesure. Le registre
refuse une nouvelle classe GCS ou un modèle de facturation BigQuery physique
tant que ses prix n'ont pas été adaptés.

Restent ouverts : création et réception de l'alerte avec l'administrateur,
accès à la vraie vue de facturation et au SKU exact, relecture de la convention
et contributions individuelles du groupe. L09 n'est pas déclaré terminé tant
que l'alerte n'existe pas. La CI GitHub reste bloquée par les crédits Actions
épuisés, comme indiqué dans [ci-cd.md](ci-cd.md).

Décision : [ADR-0009 — Attribution des coûts](adr/0009-cost-attribution.md).
