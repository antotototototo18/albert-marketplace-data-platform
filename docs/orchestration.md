# Orchestration (L07)

DAG [`group6_marketplace_daily`](../orchestration/dags/group6_marketplace_daily.py),
Airflow 3.3.2 en local (installation : [orchestration/README.md](../orchestration/README.md)).
Décision sur les relances : [ADR-0007](adr/0007-idempotency.md). Que faire en cas
d'échec : [runbook](runbooks/failed-run.md). Preuves : [evidence/l07/](evidence/l07/).
Toutes les mesures datent du 6 novembre 2026, avec `DBT_DATASET=group6_l07_bc`
(silver et gold dans des datasets personnels, pour ne pas toucher aux datasets
partagés avant la relecture de la PR).

## Le DAG

```text
extract_orders ──────> load_orders ──────┬──> dbt_build
extract_order_items ─> load_order_items ─┤
                                         └──> drop_staging (all_done)
```

| Réglage | Valeur | Pourquoi |
|---|---|---|
| Planning | `CronDataIntervalTimetable("@daily", timezone="UTC")` | Airflow 3 exécute `"@daily"` comme un intervalle de durée nulle par défaut (`create_cron_data_intervals=False`) : `data_interval_start` = `data_interval_end`, et `SINCE`/`UNTIL` seraient égaux. Ce timetable redonne la sémantique du cours : le run du 15 septembre couvre le 15, de minuit à minuit UTC, et part une fois la journée finie. UTC pour ne jamais sauter ni doubler une heure au changement d'heure. |
| `start_date` | 2026-09-15 | Premier jour que le DAG possède : l'export legacy s'arrête au 14. |
| `catchup` | `False` | Le passé se rattrape par back-fill explicite, pas en activant le DAG. |
| `max_active_runs` | 1 | Deux runs ne fusionnent jamais en même temps dans les mêmes tables. |
| Période | `SINCE={{ data_interval_start \| ds }}`, `UNTIL={{ data_interval_end \| ds }}` | Lue par l'extracteur dans son environnement ; jamais l'horloge. |
| Images | `group6-ingestion` et `group6-transform`, tag `20261106T-step7-01` | Voir « Écart avec l'ADR-0006 » plus bas. |

Le fichier du DAG ne contient que de la structure : aucun import lourd, aucune
connexion au niveau du module. `tests/test_dag_structure.py` le vérifie en CI
sans installer Airflow ; `airflow dags list-import-errors` est vide en local.

**Le DAG tourne depuis le planning, sans étape manuelle** : le run planifié
`scheduled__2026-11-06` (période du 5 novembre) a réussi. Il n'a extrait aucune
ligne, ce qui est juste : l'horloge simulée de la base source s'arrête au
16 septembre.

## Idempotence : pourquoi relancer est sans danger

Une ligne par tâche qui écrit. Le choix entre les options est dans
l'[ADR-0007](adr/0007-idempotency.md).

| Tâche | Ce qu'elle écrit | Pourquoi la lancer deux fois est sans danger |
|---|---|---|
| `extract_orders`, `extract_order_items` | `C:\de\l07\out\<table>\<SINCE>.parquet` | Nom déterministe par période, **remplacé** (`os.replace`) : un rejeu écrase son propre fichier, il ne s'ajoute pas à côté. Testé dans `tests/test_ingestion.py`. |
| `load_orders` | `group6_bronze.stage_orders_<YYYYMMDD>`, puis `orders_raw` | Staging chargé avec `bq load --replace` ; puis **`MERGE` sur `order_id`** : une commande déjà présente est mise à jour, jamais insérée deux fois. |
| `load_order_items` | `group6_bronze.stage_order_items_<YYYYMMDD>`, puis `order_items_raw` | Idem, **`MERGE` sur `(order_id, p_id)`**. |
| `drop_staging` | supprime les deux tables de staging | `DROP TABLE IF EXISTS` ; `trigger_rule="all_done"` pour qu'elles partent même si un chargement échoue. |
| `dbt_build` | vues `<dataset>_silver`, tables `<dataset>_gold` | **`CREATE OR REPLACE`** : silver est en vues, gold est reconstruit en entier (ADR-0005). |

BigQuery n'impose pas l'unicité d'une clé : ce sont les tests L05 (`unique` sur
`stg_orders.order_id`, `unique_combination_of_columns` sur `stg_order_items`) qui
vérifient que la clé du `MERGE` en est vraiment une.

Preuve : le même back-fill lancé deux fois laisse les mêmes comptes (section
Back-fill), et le script d'initialisation `warehouse/06_bronze_native.sql`, passé
deux fois, aussi (222 644 et 408 560 lignes).

## Retries et alerte

- **Retries :** 2 par tâche (3 essais), espacés de **5 minutes**. Plus long que
  ce qui est réessayé : l'extracteur réessaie déjà sa connexion pendant environ
  une minute, dbt et `bq` réessaient leurs propres jobs une fois. Un retry
  immédiat retomberait sur la même panne.
- **Alerte :** `on_failure_callback`, qui ne part qu'une fois les retries
  épuisés (pas `on_retry_callback`, qui partirait à chaque essai). E-mail via
  Gmail SMTP ; identifiants dans le `.env` local, jamais dans Git.
- **Qui la reçoit, et quoi faire :** Benjamin Caujolle, d'astreinte pour L07, à
  l'adresse configurée dans `ALERT_EMAIL_TO`. Il ouvre le
  [runbook](runbooks/failed-run.md) et commence par le log de la tâche nommée
  dans l'objet du mail.

**Preuve, alerte reçue :** le 6 novembre 2026 à 13 h 54 (heure de Paris),
`extract_order_items` a échoué trois fois sur un `403` en tentant de
télécharger son image ([log](evidence/l07/02-alarm-image-pull-403.log)). Un
seul e-mail est arrivé, après le troisième essai :

> group6_marketplace_daily.extract_order_items failed for 2026-09-14 00:00:00+00:00
> (run manual__2026-11-06T12:44:39.364995+00:00, attempt 3).

C'est l'une des pannes que cite la consigne (une image que le worker ne peut pas
obtenir) ; la cause et la correction sont dans le runbook (3c).

## Quality gate

La gate, ce sont les tests L05 lancés par le scheduler. Exercice fait le
6 novembre 2026 avec une poison row conçue contre un test précis
([script](evidence/l07/04-poison-row.sql)) : un second exemplaire de la ligne
`(222935, B019QY5QVS, qty 10)` du 16 septembre dans `order_items_raw`. Test
visé : `unique_combination_of_columns(order_id, p_id)` sur `stg_order_items`.

### Avant : `dbt_run >> dbt_test`, une alarme

Run `backfill__2026-09-17` (période du 16 septembre), DAG avec `dbt_run` puis
`dbt_test` comme dans le cours :

- `dbt_run` a réussi : gold a été reconstruit **avec** la ligne en double.
- `dbt_test` a échoué à ses trois essais sur deux tests :
  `unique_combination_of_columns(order_id, p_id)` sur `stg_order_items` (la
  cible) et le même test sur `fct_order_items` (le grain du mart), qui n'a pu
  échouer que parce que la ligne était déjà dans gold
  ([log](evidence/l07/05-gate-v1-dbt-test-failed.log)).
- Le run est passé au rouge et l'alerte est partie après le dernier essai.

| Gold, 16 septembre | Avant la poison row | Après le run |
|---|---|---|
| Unités (`fct_daily_demand`) | 1 201 | **1 211** |
| Lignes (`fct_order_items`) | 364 | **365** |
| Chiffre d'affaires | 32 802,35 € | **32 890,25 €** |
| Exemplaires de la ligne dans gold | 1 | **2** |

**Le mauvais chiffre a atteint les marts** : 10 unités et 87,90 € de trop, qu'un
lecteur de `fct_daily_demand` aurait pris pour vrais entre le `dbt_run` et la
correction. Cette gate est une alarme, pas un verrou
([mesures](evidence/l07/05-gate-v1-marts.txt)).

### Après : `dbt_build`, un verrou

Correction, comme le propose la consigne : `dbt_run >> dbt_test` remplacé par une
seule tâche `dbt_build`, qui teste chaque modèle dès qu'il est construit et saute
tout ce qui en dépend. Puis le même exercice :

1. Poison row retirée, run propre du 16 septembre : le `MERGE` réinsère la vraie
   ligne une fois, gold reconstruit (1 201 unités, 364 lignes).
2. Même poison row réinsérée, run du 16 septembre avec `dbt_build`.

- `dbt_build` a échoué à ses trois essais : `FAIL 1` sur
  `unique_combination_of_columns(order_id, p_id)` de `stg_order_items`, puis
  **38 nœuds sautés** en aval, dont `int_orders__deduplicated`,
  `fct_order_items` et `fct_daily_demand` (`PASS=54 WARN=1 ERROR=1 SKIP=38`,
  [log](evidence/l07/07-gate-v2-dbt-build-failed.log)).
- Le run est passé au rouge et l'alerte est partie après le dernier essai.

| Gold, 16 septembre | Avant la poison row | Après le run |
|---|---|---|
| Unités (`fct_daily_demand`) | 1 201 | **1 201** |
| Lignes (`fct_order_items`) | 364 | **364** |
| Chiffre d'affaires | 32 802,35 € | **32 802,35 €** |
| Exemplaires de la ligne | bronze 1, gold 1 | **bronze 2, gold 1** |

**La ligne fausse s'est arrêtée à staging** : gold garde la version précédente,
juste, et ne prend simplement pas la nouvelle journée tant que la donnée n'est
pas corrigée. C'est un verrou ([mesures](evidence/l07/07-gate-v2-marts.txt)).

Pour finir, la poison row a été supprimée et le 16 septembre relancé : bronze
223 112 / 409 416, gold 2 794 unités sur les 15 et 16, aucune table de staging
restante. Ce que l'exercice a appris au runbook : section 3d (un échec de
`dbt_build` sur un test ne se relance pas avant correction, et une relance
réinsère depuis la source une vraie ligne supprimée avec la fausse).

## Back-fill

### Prédiction, écrite avant toute exécution

Plage : **2026-09-15 au 2026-09-16**. Ce sont les deux seuls jours que la base
source contient et que le bronze n'a pas : l'export legacy s'arrête au
2026-09-14, la source a des commandes live les 15 et 16.

État de départ, après remise à zéro du bronze
([03-reset-before-backfill](evidence/l07/03-reset-before-backfill.txt)) :
`orders_raw` = 222 644 lignes, `order_items_raw` = 408 560 lignes.

| Jour | Commandes source | Lignes source | Commandes gardées par la déduplication | Unités gardées |
|---|---|---|---|---|
| 2026-09-15 | 260 | 492 | 239 | 1 593 |
| 2026-09-16 | 208 | 364 | 208 | 1 201 |
| **Total** | **468** | **856** | **447** | **2 794** |

1. `--dry-run` liste **deux runs**, datés 2026-09-15 et 2026-09-16.
2. Bronze après le back-fill : `orders_raw` **+468** (223 112), `order_items_raw`
   **+856** (409 416). Les commandes sont nouvelles, chaque `MERGE` insère tout.
3. Les 21 paires du 15 septembre (même acheteur, même paiement, mêmes lignes,
   `order_id` séparés de 47) sont des doublons du flux live : la déduplication
   retire le second de chaque paire. Gold gagne **447 commandes et 2 794 unités**.
4. Le test C1 passe : il ne regarde que l'export legacy.
5. Un **second back-fill identique** n'ajoute **aucune ligne**.

Hypothèse fragile : le calcul déduplique les deux jours isolément, alors que le
modèle dbt cherche les jumeaux dans tout l'historique.

### Exécution et écarts

| Étape | Prédit | Réel |
|---|---|---|
| `--dry-run` | 2 runs | **0 run**, puis 2 avec `--reprocess-behavior completed` |
| Premier back-fill, bronze | +468 / +856 | **+208 / +364**, puis +468 / +856 après correction |
| Gold, commandes gardées le 15 / le 16 | 239 / 208 | **239 / 208** |
| Gold, unités le 15 / le 16 | 1 593 / 1 201 | **1 593 / 1 201** |
| Second back-fill identique, bronze | +0 | **+0** (223 112 / 409 416 ; seul `_loaded_at` avance) |

Les deux écarts viennent de l'état d'Airflow, pas des données :

- **Le dry-run vide.** Ces deux jours avaient déjà un run réussi : un premier
  back-fill, lancé plus tôt pendant la mise au point (sa trace est dans
  [backfill.json](evidence/l07/backfill.json) ; ses comptes étaient déjà
  223 112 / 409 416, puis identiques au rejeu), avant la remise à zéro du bronze. Par défaut, un back-fill saute les périodes terminées.
  Airflow connaît l'état de ses runs, pas celui de BigQuery : il fallait le
  demander explicitement avec `--reprocess-behavior completed`.
- **Le 15 septembre manquant.** Le run de date logique 2026-09-15 existait déjà :
  il avait été créé par `airflow dags test`, qui lui avait donné la période d'un
  run manuel, la veille (14 → 15). Une date logique ne porte qu'un run, et un run
  garde sa période : le back-fill l'a réutilisé et a retraité le 14 (402
  commandes mises à jour par le `MERGE`, aucune ajoutée). Après suppression de ce
  run manuel des métadonnées, le back-fill du 15 a extrait les 260 commandes
  attendues et les comptes ont rejoint la prédiction. Les deux leçons sont dans
  le runbook (section 4).

L'hypothèse fragile ne s'est pas réalisée : aucune commande live ne reproduit un
panier legacy récent.

## Écart avec l'ADR-0006

L'ADR-0006 demande de référencer les images par digest dans l'orchestration. Le
provider Docker 4.5.9 ne retrouve pas une image locale nommée par digest : il
tente de la télécharger, et le worker n'a pas d'identifiants pour Artifact
Registry (`403`, preuve ci-dessus). Le DAG référence donc le **tag**
`20261106T-step7-01`, jamais réutilisé (règle d'équipe, le dépôt est mutable), et
note les digests en commentaire ; le runbook (3c) vérifie que le tag pointe
toujours sur ce digest. Digests :
`group6-ingestion` `sha256:d273c33b…b3b4`, `group6-transform` `sha256:e05e888f…38a2`
([reproduce.md](reproduce.md)).

## Inventaire pour L08 (ressources créées à la main en L07)

| Ressource | Créée par | Terraform en L08 ? |
|---|---|---|
| `group6_bronze.orders_raw`, `order_items_raw` | `warehouse/06_bronze_native.sql` | Le dataset est déjà dans le périmètre L08. Les tables : à adopter ou à laisser au SQL, à décider en L08 ; leur schéma et leurs labels sont dans le script. |
| `group6_bronze.stage_<table>_<YYYYMMDD>` | le DAG, supprimées à chaque run | Non : éphémères. |
| `group6_l07_bc_silver`, `group6_l07_bc_gold` | dbt, `DBT_DATASET=group6_l07_bc` | Non : temporaires, à supprimer après la fusion de la PR. |
| Images `group6-*:20261106T-step7-01` | `docker push` | Le dépôt `dataeng` n'est pas au groupe ; les images ne relèvent pas de Terraform. |
| Airflow | Docker Compose local, `C:\de\l07` | Non en L08 ; la consigne évoque la machine du scheduler comme extension. |

Accès : toutes les tâches s'exécutent avec les identifiants du membre qui
héberge Airflow (Application Default Credentials), pas avec le compte de service
de L02. Droits nécessaires : écriture sur `group6_bronze` (propriétaire
aujourd'hui) et sur les datasets `<DBT_DATASET>_silver` et `_gold`. Avant de passer
à `DBT_DATASET=group6`, le membre doit obtenir l'écriture sur `group6_silver` et
`group6_gold`. Pour L10, `buyer_id` a désormais une seconde copie bronze
(`orders_raw`) à classer et à couvrir dans la procédure d'effacement (data
dictionary).
