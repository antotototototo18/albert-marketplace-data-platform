# Partie 2 et 4 — Colin · avant / après · 1:00 → 1:45, puis 4:15 → 5:00

**Ton rôle :** prouver que les données arrivent. Tu lances **la même requête**
deux fois : avant le run (0, 0, 0) et après le run (208, 364, 1 201).

## Avant l'enregistrement

**Le jour J, tout se passe sur le PC de Benjamin.** Tu prends la souris et le clavier pendant ta partie, puis tu laisses la place au suivant.

1. Sur le PC de Benjamin, **onglet 2** du navigateur : la console BigQuery : <https://console.cloud.google.com/bigquery?project=data-engineering-i1>.
2. Ouvre un nouvel onglet de requête et colle **exactement** ceci :

   ```sql
   SELECT
     (SELECT COUNT(*) FROM `data-engineering-i1.group6_bronze.orders_raw`
       WHERE STARTS_WITH(order_date, '2026-09-16')) AS bronze_orders,
     (SELECT COUNT(*) FROM `data-engineering-i1.group6_gold.fct_order_items`
       WHERE order_date = '2026-09-16') AS gold_lines,
     (SELECT IFNULL(SUM(units_sold), 0) FROM `data-engineering-i1.group6_gold.fct_daily_demand`
       WHERE order_date = '2026-09-16') AS gold_units;
   ```

3. **Onglet 3** : le bucket
   <https://console.cloud.google.com/storage/browser/data-engineering-i1-group6/bronze?project=data-engineering-i1>.
4. Zoom du navigateur à 125 %.
5. Juste avant l'enregistrement, lance la requête une fois pour vérifier
   qu'elle donne **0, 0, 0**. Si elle ne donne pas 0, préviens Anthony : la
   préparation n'est pas faite.

## Partie 2 · AVANT · 1:00 → 1:45

| Quand | Ce que tu fais | Ce que tu dis |
|---|---|---|
| Début | Onglet 2 : BigQuery, avec la requête | « The shop database stops on the 16th of September. Before recording, we removed that day from our platform, so you can watch it come back. » |
| 1:15 | Tu montres les trois lignes de la requête | « This query counts the 16th in three places: orders in bronze, order lines in gold, and units in the daily table for the data science team. » |
| 1:25 | Tu cliques **Run** et tu montres le résultat | « Right now: zero, zero, zero. Benjamin will load that day. » |
| Fin | Tu laisses la place à Benjamin | — |

## Partie 4 · APRÈS · 4:15 → 5:00

Benjamin te passe la parole quand le run est vert.

| Quand | Ce que tu fais | Ce que tu dis |
|---|---|---|
| Début | Onglet 2, même requête, tu cliques **Run** | « Same query as before. » |
| 4:25 | Tu montres le résultat : **208, 364, 1201** | « Now: 208 orders in bronze, 364 order lines in gold, and 1,201 units in the daily table. These rows were not there two minutes ago. » |
| 4:40 | Onglet 3 : le bucket GCS, dossier `bronze/` | « And this is the raw side, in Google Cloud Storage. Bronze keeps the original files, so we can always rebuild everything. Anthony. » |
| Fin | Tu laisses la place à Anthony | — |

## Si le résultat n'est pas celui attendu

Ne t'arrête pas. Lis les chiffres à voix haute et dis ce qu'ils veulent dire,
par exemple : « Bronze has the orders but gold is still at zero: dbt has not
rebuilt gold yet. » Le prof demande de garder ces moments dans la vidéo.

## Les mots à expliquer si on te le demande

- **BigQuery** : la base de données de Google pour l'analyse.
- **Google Cloud Storage (GCS)** : là où sont rangés les fichiers bruts.
