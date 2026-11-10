# Runbook : un run du DAG `group6_marketplace_daily` a échoué

Pour la personne d'astreinte qui n'a pas construit le pipeline. Suivre les
étapes dans l'ordre et s'arrêter dès que la cause est trouvée.

## 1. Comment je sais que quelque chose ne va pas

- **Un e-mail** arrive à l'adresse `ALERT_EMAIL_TO`, avec pour objet
  `[group6 Airflow] group6_marketplace_daily.<tâche> failed`. Le corps donne la
  période (`data_interval_start`), le `run_id` et le numéro de tentative.
- L'e-mail ne part qu'après **le dernier** essai (3 tentatives, 5 minutes
  d'écart). Quand il arrive, Airflow a déjà réessayé deux fois : ce n'est pas
  un incident passager.
- **Sans e-mail**, le symptôme est un `fct_daily_demand` sans la journée d'hier,
  ou une alerte de fraîcheur dbt (`dbt source freshness`, avertissement à 26 h,
  erreur à 48 h).
- **Un run vert ne prouve pas qu'il a travaillé.** Vu le 2026-11-06 : un run
  pour une date antérieure au `start_date` du DAG (2026-09-15) est passé au vert
  en une seconde, sans créer aucune tâche
  ([preuve](../evidence/l07/01-empty-green-run.log)). Un jour sans commande
  donne aussi un run vert qui n'écrit rien. Dans les deux cas, seul le compte
  de lignes (`n_staged` dans le log de `load_*`) ou la fraîcheur le montrent.

## 2. Ce que je regarde en premier

1. Airflow UI (<http://localhost:8080> en local), DAG
   `group6_marketplace_daily`, vue **Grid**. Le carré rouge donne la tâche et
   le run.
2. Cliquer sur le carré rouge, onglet **Logs**, dernière tentative. La cause
   est dans les 20 dernières lignes, juste avant `Task failed with exception`.
3. Noter la tâche : elle dit quelle partie a cassé.

| Tâche en échec | Ce qui a cassé |
|---|---|
| `extract_*` | La base source, ou l'image d'ingestion |
| `load_*` | Les droits BigQuery, le fichier Parquet, ou le `MERGE` |
| `drop_staging` | Rarement grave : des tables de staging restent (voir 4) |
| `dbt_build` | Soit un modèle ne compile plus ou les droits sur les datasets dbt manquent (`ERROR` sur un modèle), soit **les données** : un test L05 a trouvé une ligne fausse (`FAIL` sur un test, quality gate). Les modèles en aval d'un test en échec sont `SKIP` : gold garde la version de la veille. |

## 3. Les trois pannes les plus probables

**a. Identifiants Google expirés.** Dans le log :
`Reauthentication failed. cannot prompt during non-interactive execution`, ou
`invalid_grant`. Vu le 2026-11-06 sur `load_*`. Les tâches utilisent les
Application Default Credentials de la machine qui héberge Airflow. Sur cette
machine :

```bash
gcloud auth application-default login
```

Puis relancer (voir 4). Aucune donnée n'a été écrite par la tâche en échec.

**b. La base source est injoignable.** Dans le log de `extract_*` :
`Extraction failed (OperationalError); nothing was published.` Le message ne
contient volontairement aucun détail de connexion. Vérifier que le conteneur de
la base tourne et qu'il est sur le réseau `albert-marketplace_default` :

```bash
docker ps --filter name=albert-marketplace-db
docker network inspect albert-marketplace_default
```

**c. Une image introuvable.** Dans le log : `No such image`, `manifest unknown`,
ou **`403 Client Error ... images/create`** (vu le 2026-11-06 sur
`extract_order_items`, [preuve](../evidence/l07/02-alarm-image-pull-403.log)).
Le 403 veut dire que l'image n'est pas sur la machine et que le worker a tenté
de la télécharger : il n'a pas d'identifiants pour Artifact Registry, il ne
peut pas. Le DAG nomme les images dans `INGESTION_IMAGE` et `TRANSFORM_IMAGE`.
Sur la machine hôte :

```bash
gcloud auth configure-docker europe-west1-docker.pkg.dev
docker pull <image:tag du DAG>
docker image inspect <image:tag du DAG> --format '{{index .RepoDigests 0}}'
```

Le digest affiché doit être celui noté en commentaire dans le DAG et dans
[reproduce.md](../reproduce.md). S'il diffère, le tag a été déplacé : s'arrêter
et prévenir le groupe. Ne jamais reconstruire sous un ancien tag (ADR-0006) :
construire un nouveau tag et mettre le DAG à jour.

**d. `dbt_build` en échec sur un test.** Le log liste les tests en `FAIL` avec
le nombre de lignes, et les modèles sautés (`SKIP`). C'est le quality gate : une
donnée fausse est arrivée dans bronze, et gold n'a pas été reconstruit (il garde
la version précédente, juste mais en retard d'un jour). Vu à l'exercice du
2026-11-06 : `unique_combination_of_columns(order_id, p_id)` sur
`stg_order_items`, pour une ligne de commande en double.
**Ne pas relancer tant que la donnée n'est pas corrigée**, le test échouera
pareil. Retrouver les lignes avec la requête du test
(`target/compiled/.../<test>.sql` dans le log, ou `dbt test --select <test>
--store-failures`), puis prévenir le groupe (voir 5) : corriger bronze à la
main est une décision, pas un réflexe. Une fois la ligne fausse retirée,
relancer la période la remet d'aplomb : le `MERGE` réinsère depuis la source la
vraie ligne si elle a été supprimée avec la fausse.

## 4. Est-ce que je peux simplement relancer ?

**Oui, pour toutes les tâches, une fois la cause corrigée.** Chaque tâche qui
écrit est idempotente ([orchestration.md](../orchestration.md#idempotence--pourquoi-relancer-est-sans-danger),
[ADR-0007](../adr/0007-idempotency.md)) : le Parquet de la période est écrasé, le
staging est remplacé, le `MERGE` met à jour au lieu d'ajouter, gold est
reconstruit. Le backfill du 15 et du 16 septembre lancé deux fois a donné les
mêmes compteurs.

Pour relancer :

- **Une tâche et la suite :** carré rouge → **Clear task** → cocher
  **Downstream** → **Clear**.
- **Une ou plusieurs journées passées :**

  ```bash
  airflow backfill create --dag-id group6_marketplace_daily \
    --from-date AAAA-MM-JJ --to-date AAAA-MM-JJ --reprocess-behavior failed --dry-run
  ```

  Lire la liste du dry-run, puis relancer sans `--dry-run`. **Si la liste est
  vide**, ces jours ont déjà un run réussi : Airflow ne connaît que l'état de
  ses runs, pas celui de BigQuery. Pour les retraiter quand même, utiliser
  `--reprocess-behavior completed` (sans danger : tout est idempotent).
- **Attention aux runs manuels déjà présents.** Une date logique ne porte qu'un
  seul run, et un run garde la période avec laquelle il a été créé. Le
  2026-11-06, un run créé par `airflow dags test ... 2026-09-15` couvrait le 14 ;
  le back-fill du 15 l'a réutilisé et a retraité le 14 au lieu du 15. Avant un
  back-fill, vérifier `airflow dags list-runs group6_marketplace_daily` : un run
  `manual__` sur une date du back-fill doit être supprimé d'abord.
- **Ne pas** utiliser `airflow dags test` pendant que le scheduler tourne : il
  exécute les tâches en même temps que le worker, qui en marque une en échec à
  tort (`TaskAlreadyRunningError`).
- **Ne pas** utiliser **Trigger DAG** pour rejouer une date passée : Airflow 3
  donne à un run manuel la période de la veille du déclenchement, pas celle
  de la date demandée.

Ce qu'une relance ne répare pas :

- un `dbt_build` en échec à cause des données (3d) ;
- une commande supprimée dans la source : elle reste dans bronze (ADR-0007) ;
- des tables `group6_bronze.stage_*` oubliées si `drop_staging` a échoué :
  elles ne faussent rien, mais il faut les supprimer
  (`DROP TABLE IF EXISTS ...stage_<table>_<YYYYMMDD>`).

## 5. Qui prévenir, et quand s'arrêter

- **Toujours :** un message dans la conversation du groupe 6, avec la tâche, la
  période et la cause trouvée (ou « cause inconnue »).
- **Prévenir l'équipe ML** si le run de la veille n'est pas réparé à 8 h : son
  entraînement du matin lit `fct_daily_demand`.
- **S'arrêter et passer la main** si la cause n'est pas une des pannes de la
  section 3, si `dbt_build` échoue sur des données, ou après deux relances qui
  échouent de la même façon. Une troisième relance identique n'apprend rien.
