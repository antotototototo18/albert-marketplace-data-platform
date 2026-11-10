# Orchestration (L07)

Le DAG [`group6_marketplace_daily`](dags/group6_marketplace_daily.py) fait tourner
chaque jour le pipeline de bout en bout : extraction d'une journée de commandes et
de lignes depuis la base de l'entreprise, `MERGE` dans bronze, puis dbt. Ce qu'il
fait, pourquoi relancer est sans danger et ce qui a été mesuré :
[docs/orchestration.md](../docs/orchestration.md).

## Installer Airflow en local

Suivre la page du cours « Before session 7: setup » à la lettre (Airflow 3.3.2,
dossier court `C:\de\l07`), avec ces trois fichiers à la place de ceux du cours :

| Fichier du dépôt | À copier dans `C:\de\l07` sous le nom | Différence avec le cours |
|---|---|---|
| [Dockerfile](Dockerfile) | `Dockerfile` | Aucune : Airflow 3.3.2 + provider Docker 4.5.9 |
| [docker-compose.override.yaml](docker-compose.override.yaml) | `docker-compose.override.yaml` | `dags/` monté depuis ce dossier, variables du DAG et de l'alerte |
| [.env.example](.env.example) | `.env` | Chemins, base source, SMTP, dataset dbt. **Ne jamais committer `.env`.** |

Puis, depuis `C:\de\l07` :

```powershell
curl.exe -sfSLO 'https://airflow.apache.org/docs/apache-airflow/3.3.2/docker-compose.yaml'
New-Item -ItemType Directory -Force -Path logs, plugins, config, out | Out-Null
docker build -t albert-airflow:3.3.2 .
docker compose pull --ignore-buildable
docker compose up airflow-init
docker compose up -d
```

## Avant le premier run

1. **La base source tourne** : dans le dépôt `albert-marketplace`,
   `docker compose up -d db`. Le DAG la joint sur le réseau
   `albert-marketplace_default`.
2. **Les images sont sur la machine.** Les tâches sont lancées par le Docker de
   l'hôte, et le worker n'a pas d'identifiants pour Artifact Registry : il ne
   peut pas les télécharger lui-même.

   ```powershell
   gcloud auth configure-docker europe-west1-docker.pkg.dev
   docker pull europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-ingestion:20261106T-step7-01
   docker pull europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-transform:20261106T-step7-01
   docker pull google/cloud-sdk:slim
   ```

3. **Les identifiants Google sont frais** : toutes les tâches lisent les
   Application Default Credentials de la machine (`gcloud auth application-default login`).
4. **Les tables bronze natives existent** : `python scripts/run_sql.py warehouse/06_bronze_native.sql`.

Contrôles : `airflow dags list-import-errors` doit être vide, et le DAG apparaît
dans <http://localhost:8080> (airflow / airflow) dans les 30 secondes.
