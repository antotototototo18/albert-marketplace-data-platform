# Partie 1 — Antoine · le schéma · 0:00 → 1:00

**Ton rôle :** ouvrir la vidéo et expliquer en une minute ce que fait la
plateforme, et pour qui. Pas de détail technique.

## Avant l'enregistrement

**Le jour J, tout se passe sur le PC de Benjamin.** Tu prends la souris et le clavier pendant ta partie, puis tu laisses la place au suivant.

- Sur le PC de Benjamin, **onglet 1** du navigateur : <https://github.com/antotototototo18/albert-marketplace-data-platform/blob/main/docs/architecture.md>.
- Fais défiler jusqu'au schéma (le grand diagramme) et mets le zoom du
  navigateur à 125 %.
- Tu ouvres la vidéo : Anthony lance l'enregistrement, puis tu prends la souris.

## Pendant ta partie

| Quand | Ce que tu fais | Ce que tu dis |
|---|---|---|
| Début | Onglet 1 : le schéma est visible | « Hi, we are group 6. This is the data platform we built for Albert's Marketplace, an online shop. » |
| 0:10 | Tu montres la gauche du schéma avec la souris | « On the left, the sources: the shop database, the clicks on the website, and an old export. » |
| 0:20 | Tu montres le bucket bronze | « Everything lands first in **bronze**, a raw copy kept exactly as it arrived. » |
| 0:30 | Tu montres le bloc BigQuery | « Then BigQuery and a tool called **dbt** turn it into **silver**, cleaned data, and **gold**, the tables people read. » |
| 0:40 | Tu montres les flèches vers les analystes et le ML | « Who is it for? The analysts, who need one correct revenue figure, and the data science team, who need units sold per product, per country, per day. » |
| 0:50 | Tu montres le bloc Airflow | « Every day, **Airflow** runs the whole chain. In this video you will see it run for real. Colin. » |
| Fin | Tu laisses la place à Colin | — |

## Les mots à expliquer si on te le demande

- **Bronze** : la copie brute. **Silver** : les données nettoyées. **Gold** :
  les tables que les gens lisent.
- **dbt** : l'outil qui construit et teste les tables en SQL.
- **Airflow** : le programme qui lance les étapes chaque jour, dans l'ordre.
