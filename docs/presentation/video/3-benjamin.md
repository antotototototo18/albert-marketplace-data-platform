# Partie 3 — Benjamin · le run Airflow · 1:45 → 4:15

**Ton rôle :** lancer le pipeline pour de vrai, puis commenter pendant qu'il
tourne. C'est la partie la plus importante pour le prof : un DAG qui passe au
vert.

## Avant l'enregistrement

**Le jour J, tout se passe sur ton PC.** Tes camarades prennent la souris pendant leur partie. La liste complète des fenêtres à ouvrir est dans [VIDEO.md](../VIDEO.md), préparation, étape 5.

1. Airflow tourne : `docker compose up -d` dans `C:\de\l07`. <http://localhost:8080>
   s'ouvre (airflow / airflow).
2. La base de la boutique tourne : `docker compose up -d db` dans le dépôt
   `albert-marketplace`.
3. `C:\de\l07\.env` contient `DBT_DATASET=group6`.
4. Tes identifiants Google sont frais : `gcloud auth application-default login`.
5. Aucun run `manual__` sur le 16 septembre :

   ```powershell
   docker compose exec airflow-scheduler airflow dags list-runs group6_marketplace_daily
   ```

6. **Terminal 1** : ouvre un terminal PowerShell dans `C:\de\l07`, en gros caractères, avec la
   commande déjà tapée mais **pas lancée** :

   ```powershell
   docker compose exec airflow-scheduler airflow backfill create --dag-id group6_marketplace_daily --from-date 2026-09-16 --to-date 2026-09-16 --reprocess-behavior completed
   ```

7. **Onglet 4** du navigateur : ouvre le DAG `group6_marketplace_daily` dans Airflow.
8. Lors de la répétition, note **combien de temps** dure le run. Si c'est plus
   de 2 min 30, préviens le groupe : on devra parler un peu plus longtemps
   pendant l'attente.

## Pendant ta partie

| Quand | Ce que tu fais | Ce que tu dis |
|---|---|---|
| Début | Terminal 1 | « This is our pipeline in Airflow. I am asking it to re-run one past day, the 16th of September. We call that a **back-fill**. » |
| 1:55 | Tu appuies sur **Entrée**, puis tu passes au navigateur, run du 16 septembre, vue **Graph** | « There are six steps. » |
| 2:05 | Tu montres `extract_orders` et `extract_order_items` | « First, two extract steps read that day's orders and order lines from the shop database and write them to a file. » |
| 2:20 | Tu montres `load_orders` et `load_order_items` | « Then two load steps put them in BigQuery, with a **MERGE**: an order already there is updated, a new one is added. So if we run this day twice, nothing is duplicated. We tested that: a second run adds zero rows. » |
| 2:50 | Tu montres `drop_staging` | « This step deletes the temporary tables, even if a load failed. » |
| 3:00 | Tu montres `dbt_build` pendant qu'il tourne | « Now **dbt build**. It rebuilds silver and gold, and it tests each table right after building it. If a test fails, everything after it is skipped, so a bad number never reaches gold. That is our quality gate. » |
| Pendant l'attente | Si dbt n'a pas fini, tu continues | « The first version, from the course, built everything and tested after. In a drill, that let 10 extra units into gold. This version stops it at the first table. » |
| Quand tout est vert | Tu montres le Graph tout vert | « All green. » |
| Juste après | Tu ouvres le log de `dbt_build` et tu descends jusqu'en bas | « Here is the dbt summary: every test passed, zero errors. Colin, let's see if the data is there. » |
| Fin | Tu laisses la place à Colin | — |

Dans le résumé dbt, lis ce que tu vois. Le 20 novembre, c'était
`PASS=92 WARN=2 ERROR=0`. Les deux avertissements sont connus : six produits
sans nom, et un code pays `UNKNOWN`.

## Si une tâche passe en jaune ou en rouge

**Ne t'arrête pas, c'est autorisé et même apprécié.**

1. Clique sur la tâche, puis **Logs**.
2. Lis l'erreur à voix haute et dis ce qu'elle veut dire.
3. Dis ce que tu ferais pour la corriger. Les cas connus sont dans
   `docs/runbooks/failed-run.md` :
   - `403` ou image introuvable : l'image n'est pas sur la machine → `docker pull`.
   - `Reauthentication failed` : les identifiants Google ont expiré →
     `gcloud auth application-default login`.
   - Échec d'un test dbt : la donnée est fausse. On ne relance pas avant de
     l'avoir corrigée.
4. Une tâche réessaie toute seule après 5 minutes. Si l'erreur est corrigée,
   tu peux faire **Clear** sur la tâche pour relancer tout de suite.

## Les mots à expliquer si on te le demande

- **DAG** : la liste des étapes qu'Airflow lance, dans l'ordre.
- **Back-fill** : relancer le pipeline pour des jours passés.
- **MERGE** : met à jour une ligne si elle existe, l'ajoute sinon.
- **Idempotent** : le lancer deux fois donne le même résultat qu'une fois.
