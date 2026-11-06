# ADR-0007 : Une période par run, fusionnée sur la clé de la source

- **Statut :** proposé
- **Date :** 2026-11-06
- **Auteur :** Benjamin Caujolle
- **Leçon :** L07

## Contexte

Le DAG `group6_marketplace_daily` extrait chaque jour les commandes et les lignes
de commande de la base de l'entreprise, les charge dans bronze, puis lance dbt.
Airflow relance une tâche d'office (2 retries) et l'équipe en relancera à la main :
après une panne, pour un backfill, ou par erreur. Une tâche qui écrit doit donc
pouvoir tourner deux fois pour la même période sans rien changer la deuxième fois.

Les faits qui comptent :

- Bronze `orders` et `order_items` étaient des tables externes sur l'export legacy
  (ADR-0002). On ne peut ni y faire de `MERGE`, ni y insérer de ligne.
- `order_items` n'a pas de date : une ligne appartient à la période de sa commande.
- Toutes les colonnes de bronze sont en `STRING` (ADR-0002), `order_date` compris.
  Une partition par date demanderait de typer la colonne dans bronze.
- Les clés de la source sont `orders.order_id` et `(order_items.order_id, p_id)`.
  Les tests L05 (`unique` sur `stg_orders.order_id`, `unique_combination_of_columns`
  sur `stg_order_items`) vérifient qu'elles le restent, parce que BigQuery ne
  l'impose pas.
- La base source s'arrête au 2026-09-16 ; l'export legacy, au 2026-09-14.
  Les 15 et 16 septembre comptent 468 commandes et 856 lignes (requête sur la
  base source, 2026-11-06).

## Options envisagées

| Option | Marche quand | Casse quand |
|---|---|---|
| Accepter les doublons (`INSERT` simple) | jamais, ici | toujours : un retry ou un backfill double la période, et L04 a montré ce qu'un doublon fait au chiffre d'affaires. |
| `DELETE` de la période puis `INSERT` | la période correspond à une partition | le `DELETE` réussit et l'`INSERT` échoue (trou dans bronze). `order_items` n'a pas de date : il faut une jointure pour savoir quoi supprimer. |
| Remplacer une partition (`table$YYYYMMDD`, `WRITE_TRUNCATE`) | la table est partitionnée par la date de la période | `order_date` est en `STRING` dans bronze et `order_items` n'a pas de date. |
| Écrire une nouvelle table, puis l'échanger | la table est petite | le stockage double pendant l'échange ; bronze garde aussi le legacy, qu'il faudrait recopier à chaque run. |
| **Staging par période, puis `MERGE` sur la clé métier** | on a une clé fiable | la clé n'est pas unique, ce que les tests L05 vérifient. Une ligne supprimée dans la source reste dans bronze. |

## Critères

1. **Un rejeu ne change pas le nombre de lignes.** Seuls le `MERGE` et le
   remplacement de partition le garantissent en une opération atomique.
2. **La période vient du run, jamais de l'horloge.** Toutes les options le
   permettent, à condition que l'extracteur reçoive `SINCE`/`UNTIL` du DAG.
3. **Pas de changement de schéma dans bronze.** Le remplacement de partition
   l'exige ; les autres non.
4. **Coût.** Le `MERGE` lit la table cible entière (environ 220 000 commandes,
   quelques Mo), ce qui reste très loin du plafond de 1 Gio par requête (ADR-0004).

## Décision

Chaque tâche qui écrit est rendue idempotente par sa clé :

| Tâche | Ce qu'elle écrit | Pourquoi un rejeu est sans effet |
|---|---|---|
| `extract_<table>` | `out/<table>/<SINCE>.parquet` | Le nom du fichier ne dépend que de la table et de `SINCE` : un rejeu écrase son propre fichier. |
| `load_<table>` | `stage_<table>_<YYYYMMDD>`, puis `MERGE` dans `<table>_raw` | Le staging est chargé avec `--replace`. Le `MERGE` met à jour les lignes déjà présentes (même clé) et n'insère que les nouvelles. |
| `drop_staging` | supprime les deux tables de staging | `DROP TABLE IF EXISTS` ; `trigger_rule="all_done"` pour qu'elles partent même si un chargement échoue. |
| `dbt_build` | `<dataset>_silver` (vues), `<dataset>_gold` (tables) | `CREATE OR REPLACE` : silver est en vues, gold est reconstruit en entier à chaque run (ADR-0005). C'est l'option « nouvelle table puis échange », acceptable ici parce que gold est petit. |

Bronze `orders_raw` et `order_items_raw` deviennent des tables natives
(`warehouse/06_bronze_native.sql`). L'export legacy y est recopié une fois,
avec la même clé, ce qui rend le script lui aussi rejouable.

**La tâche dont on est le moins sûr : `load_order_items`.** Sa clé est fiable :
la source impose `PRIMARY KEY (order_id, p_id)`. Ce qui ne l'est pas, ce sont
les suppressions. La source déclare `FOREIGN KEY (order_id) REFERENCES
orders ON DELETE CASCADE` : supprimer une commande, ou retirer un produit d'une
commande, efface des lignes que le `MERGE` ne voit jamais, puisqu'il ne lit que
ce qui existe encore. Rejouer la période ne corrige rien, et aucun test
n'échoue : bronze garde une ligne de trop et `fct_daily_demand` compte des unités
qui n'existent plus. Aucune suppression n'a été observée à ce jour.

## Conséquences

- **Plus facile :** relancer un run en échec, ou rejouer n'importe quelle période,
  sans rien nettoyer avant. Le backfill du 15 et du 16 septembre lancé deux fois
  donne les mêmes compteurs (preuves dans `docs/evidence/l07/`).
- **Plus difficile :** une commande supprimée dans la source n'est jamais
  supprimée dans bronze (voir ci-dessus). Si des suppressions apparaissent, il
  faudra un `WHEN NOT MATCHED BY SOURCE` limité aux commandes de la période.
- **À surveiller :** l'unicité des clés n'est garantie que par les tests dbt. Si
  la source livre deux fois la même clé dans une période, le `MERGE` échoue
  (« UPDATE/MERGE must match at most one source row ») : c'est voulu, l'alerte
  part et le runbook `failed-run.md` dit quoi faire.
- **À surveiller :** `_loaded_at` est réécrit à chaque rejeu. Il dit quand une
  ligne est arrivée pour la dernière fois, pas la première ; c'est ce que la
  fraîcheur dbt (C16) a besoin de savoir.
