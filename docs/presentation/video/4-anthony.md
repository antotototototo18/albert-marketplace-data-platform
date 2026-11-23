# Partie 5 — Anthony · le rapport quotidien et une protection · 5:00 → 6:00

**Ton rôle :** montrer ce que gold apporte au métier (le rapport du jour), puis
une protection des données personnelles. Tu es aussi **celui qui lance et arrête
l'enregistrement**.

## Avant l'enregistrement

**Le jour J, tout se passe sur le PC de Benjamin.** Tu prends la souris et le clavier pendant ta partie, puis tu laisses la place au suivant.

1. Sur le PC de Benjamin, **onglet 5** du navigateur : BigQuery, une requête avec :

   ```sql
   SELECT
     country_code,
     SUM(units_sold)          AS units,
     ROUND(SUM(revenue), 2)   AS revenue_eur
   FROM `data-engineering-i1.group6_gold.fct_daily_demand`
   WHERE order_date = '2026-09-16'
   GROUP BY country_code
   ORDER BY units DESC;
   ```

2. **Onglet 6** : BigQuery, la table
   `group6_warehouse.shipping_details`, onglet **Schema**. On y voit une
   étiquette (« Policy tag ») sur `street_address`, `city`, `zip` et `phone`.
3. Zoom du navigateur à 125 %.
4. **L'enregistrement :** quand tout le monde est prêt, `Win + Maj + R`, tout
   l'écran, **micro activé**, **Démarrer**. Tu le lances avant la phrase
   d'Antoine et tu l'arrêtes après le « Thanks for watching » de Lenny.

## Ce que la requête donne (vérifié le 23 novembre)

| Pays | Unités | CA (€) |
|---|---:|---:|
| DE | 336 | 8 598,29 |
| FR | 296 | 8 320,74 |
| ES | 212 | 5 159,35 |
| IT | 197 | 6 366,26 |
| BE | 96 | 3 086,67 |
| NL | 42 | 749,45 |
| UNKNOWN | 22 | 521,59 |
| **Total** | **1 201** | **32 802,35** |

## Pendant ta partie

| Quand | Ce que tu fais | Ce que tu dis |
|---|---|---|
| Début | Onglet 5 : le rapport, tu cliques **Run** | « This is the daily report, read from gold: units and revenue per country, for the 16th of September. » |
| 5:10 | Tu montres les premières lignes | « Germany first with 336 units, then France with 296. In total, 1,201 units and about 32,800 euros. » |
| 5:20 | — | « Each order is counted once here. The old export counted every order twice and doubled revenue. » |
| 5:30 | Onglet 6 : `shipping_details` → **Schema** | « One protection. The street, phone, city and zip columns carry a label, a **policy tag**, that decides who can read them. » |
| 5:40 | Tu montres une colonne avec son étiquette | « Our cleaning step also drops them before gold, and a test fails if personal data ever reaches gold. » |
| 5:50 | — | « Honest limit: on this school project, every student holds the key to the label, so today it blocks nobody. Lenny. » |
| Fin | Tu laisses la place à Lenny. **Tu n'arrêtes pas l'enregistrement.** | — |

## Les mots à expliquer si on te le demande

- **Policy tag** : une étiquette sur une colonne, qui décide qui peut la lire.
- **UNKNOWN** : des commandes dont on ne connaît pas le pays de l'acheteur.
