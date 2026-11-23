# Vidéo de démo — guide et script

Le guide est en français, le texte à dire est en anglais. La vidéo dure entre
5 et 8 minutes. On vise **7 minutes**.

## Ce que le prof exige

D'après la consigne de l'étape 11 (`videotask.md`) :

- [ ] Entre 5 et 8 minutes.
- [ ] **Chaque membre parle**, pour une vraie partie.
- [ ] À l'écran : **un run du DAG qui passe au vert**, **les données qui
      arrivent**, et **une requête qui renvoie des lignes qui n'étaient pas là
      avant**.
- [ ] Un lien dans `README.md`. « Non répertoriée » est accepté, « privée »
      ne l'est pas.
- [ ] Si quelque chose casse pendant l'enregistrement et qu'on le diagnostique,
      **on le garde**. C'est une meilleure preuve qu'un run parfait.
- [ ] Interdit : parler sur l'enregistrement de l'écran de quelqu'un d'autre, ou
      montrer un pipeline qu'on n'a pas fait tourner. **C'est éliminatoire.**

## Le format : une machine, une pièce, une seule prise

Tout se passe sur **le PC Windows de Benjamin**, où Airflow et la base de la
boutique tournent déjà. Les cinq membres sont dans la même pièce, devant ce PC.
On enregistre l'écran et le micro en une seule prise, sans montage et sans
coupure.

- **Chacun prend la souris et le clavier pendant sa partie**, et parle en
  direct sur ce qu'il fait. On ne parle jamais sur l'enregistrement d'un écran
  fait par quelqu'un d'autre, ce que la consigne interdit.
- **Un seul micro** : un micro-casque branché sur le PC, ou le micro du portable
  si la pièce est calme. Celui qui parle s'approche du micro.
- **Le changement d'orateur** : la phrase de passage, puis on échange de place.
  Ça prend quelques secondes, c'est normal.
- Si on se trompe, on recommence tout : ça ne coûte que 7 minutes.

**Pour enregistrer sous Windows 11 :** l'**Outil Capture** (Snipping Tool).
Taper `Win + Maj + R`, sélectionner tout l'écran, **activer le micro** dans la
barre de l'outil, puis cliquer sur **Démarrer**. À la fin, cliquer sur **Arrêter**
et enregistrer le `.mp4`. Si l'outil n'enregistre pas le son, utiliser
**OBS Studio** (gratuit) : une source « Capture d'écran », une source « Capture
audio d'entrée » pour le micro, puis **Démarrer l'enregistrement**.

## Les fiches de chacun

Une fiche par personne : quoi préparer, quoi cliquer, quoi dire, et quoi faire
si ça casse. Chacun lit uniquement la sienne.

| Partie | Qui | Fiche |
|---|---|---|
| 1 · Le schéma | Antoine | [video/1-antoine.md](video/1-antoine.md) |
| 2 et 4 · Avant / après | Colin | [video/2-colin.md](video/2-colin.md) |
| 3 · Le run Airflow | Benjamin | [video/3-benjamin.md](video/3-benjamin.md) |
| 5 · Rapport et protection | Anthony (lance et arrête l'enregistrement) | [video/4-anthony.md](video/4-anthony.md) |
| 6 · Terraform et la suite | Lenny | [video/5-lenny.md](video/5-lenny.md) |

Le reste de ce guide donne la préparation commune et le texte complet dans
l'ordre.

## Qui fait quoi

| Temps | Qui | À l'écran | Ce qu'on voit |
|---|---|---|---|
| 0:00 – 1:00 | Antoine | GitHub, `docs/architecture.md` | Le schéma : ce que fait la plateforme, et pour qui |
| 1:00 – 1:45 | Colin | Console BigQuery | **Avant** : aucune commande du 16 septembre dans bronze ni dans gold |
| 1:45 – 4:15 | Benjamin | Terminal et Airflow | Lancer le run du 16 septembre, le regarder tourner, **vert** |
| 4:15 – 5:00 | Colin | Console BigQuery et GCS | **Après** : les lignes sont arrivées dans bronze et dans gold |
| 5:00 – 6:00 | Anthony | Console BigQuery | Le rapport quotidien, et une colonne protégée par une étiquette |
| 6:00 – 7:00 | Lenny | Terminal | `terraform plan` : rien n'a changé à la main |
| 7:00 – 7:30 | Lenny | Face au micro | Ce qu'on ferait avec un mois de plus |

## L'idée de la démo, en une phrase

Le 16 septembre est le dernier jour de la base de la boutique. **Avant
l'enregistrement, on retire ce jour de bronze et de gold.** Pendant la vidéo,
Airflow le recharge, et on voit les lignes réapparaître : 208 commandes, et
1 201 unités dans gold. On le dit clairement à l'écran, sans le cacher.

---

## Préparation (la veille)

### 1. Benjamin : Airflow prêt à tourner

Suivre `orchestration/README.md`. Points à vérifier :

- [ ] La base source tourne : `docker compose up -d db` dans le dépôt
      `albert-marketplace`.
- [ ] Airflow tourne : `docker compose up -d` dans `C:\de\l07`, puis
      <http://localhost:8080> s'ouvre (airflow / airflow).
- [ ] Les trois images sont sur la machine : `docker images` affiche
      `group6-ingestion` et `group6-transform` avec le tag
      `20261106T-step7-01`, ainsi que `google/cloud-sdk:slim`. Sinon, voir
      `orchestration/README.md`, étape 2.
- [ ] **`DBT_DATASET=group6`** dans `C:\de\l07\.env` : dbt doit écrire dans
      les datasets partagés `group6_silver` et `group6_gold`, pas dans un
      dataset personnel. Après un changement : `docker compose up -d`.
- [ ] Le compte de Benjamin peut écrire dans `group6_silver` et `group6_gold`.
      La répétition (étape 3) le vérifie.
- [ ] Aucun run `manual__` sur le 16 septembre :
      `docker compose exec airflow-scheduler airflow dags list-runs group6_marketplace_daily`.
      Si un run manuel existe à cette date, le supprimer d'abord (runbook
      `docs/runbooks/failed-run.md`, section 4).

### 2. Anthony : retirer le 16 septembre (« l'état avant »)

Dans la console BigQuery. Le script ne supprime que les lignes chargées par le
DAG pour le 16 septembre. On peut les recharger depuis la base source : c'est
justement ce que fait la vidéo.

```sql
-- Avant : noter les deux compteurs.
SELECT
  (SELECT COUNT(*) FROM `data-engineering-i1.group6_bronze.orders_raw`
    WHERE unnamed_0 IS NULL AND STARTS_WITH(order_date, '2026-09-16')) AS orders_16_sept,
  (SELECT COUNT(*) FROM `data-engineering-i1.group6_bronze.order_items_raw`
    WHERE order_id IN (SELECT order_id FROM `data-engineering-i1.group6_bronze.orders_raw`
                       WHERE unnamed_0 IS NULL AND STARTS_WITH(order_date, '2026-09-16'))) AS lines_16_sept;
-- Attendu : 208 et 364.

BEGIN TRANSACTION;
DELETE FROM `data-engineering-i1.group6_bronze.order_items_raw`
WHERE order_id IN (SELECT order_id FROM `data-engineering-i1.group6_bronze.orders_raw`
                   WHERE unnamed_0 IS NULL AND STARTS_WITH(order_date, '2026-09-16'));
DELETE FROM `data-engineering-i1.group6_bronze.orders_raw`
WHERE unnamed_0 IS NULL AND STARTS_WITH(order_date, '2026-09-16');
COMMIT TRANSACTION;
```

Ensuite, il faut reconstruire gold pour que le 16 septembre en disparaisse
aussi. **Benjamin** lance un run normal : dans Airflow, **Trigger DAG**, sans
changer la date. Ce run porte sur la veille, il n'extrait donc aucune commande
(la base s'arrête au 16 septembre), mais son `dbt_build` reconstruit gold sans
le 16. Ne pas utiliser Trigger DAG pour une date passée (voir le runbook).

### 3. Benjamin et Colin : une répétition complète, sans enregistrer

Faire les étapes 2 et 3 de la vidéo (Colin « avant », Benjamin lance le run,
Colin « après ») une première fois, pour de vrai. Ça permet de :
- vérifier que le run passe au vert et de **chronométrer sa durée** (environ
  1 min 30 à 2 min attendues pour un jour) ;
- vérifier que les requêtes de Colin donnent bien 0, puis 208 / 364 / 1 201.

Puis **refaire l'étape 2** (retirer le 16 septembre) pour remettre « l'état
avant » juste avant l'enregistrement.

### 4. Benjamin et Lenny : Terraform sur le PC de Benjamin

Le dépôt fixe Terraform à la version exacte **1.13.5**, et son fichier de
verrouillage ne connaît que macOS et Linux. Sous Windows, on lance donc
Terraform **dans Docker**, avec l'image Linux officielle. Docker est déjà
installé pour Airflow.

1. Cloner le dépôt sur le PC de Benjamin, s'il n'y est pas déjà.
2. Dans PowerShell, depuis `infra\terraform` du dépôt :

   ```powershell
   docker pull hashicorp/terraform:1.13.5
   docker run --rm -v "${PWD}:/work" -w /work -v "$env:APPDATA\gcloud:/gcloud:ro" -e GOOGLE_APPLICATION_CREDENTIALS=/gcloud/application_default_credentials.json hashicorp/terraform:1.13.5 init -lockfile=readonly
   docker run --rm -v "${PWD}:/work" -w /work -v "$env:APPDATA\gcloud:/gcloud:ro" -e GOOGLE_APPLICATION_CREDENTIALS=/gcloud/application_default_credentials.json hashicorp/terraform:1.13.5 plan -detailed-exitcode -no-color
   ```

   Ce sont les identifiants Google de Benjamin qui servent, ceux qu'Airflow
   utilise déjà.
3. Lire le résultat du plan :
   - [ ] **« No changes »** : c'est ce qu'on veut montrer.
   - [ ] **Des changements proposés :** c'est probablement le passage d'Antoine
         et Colin en lecture seule (`iam.tf`), écrit mais jamais appliqué. Le
         mieux : Antoine et Colin donnent leur accord, puis on fait `apply`
         avant la vidéo (même commande avec `apply` à la place de `plan`).
         Sinon, on montre le plan tel quel et Lenny l'explique.
   - [ ] **Une erreur de verrou (lock) :** le compte de Benjamin ne peut pas
         écrire le verrou dans le bucket d'état. Ajouter `-lock=false` à la
         commande `plan` : un plan ne modifie rien.

### 5. Le PC de Benjamin, prêt pour tout le monde

Tout est ouvert **avant** d'appuyer sur « Enregistrer », dans cet ordre de
fenêtres :

- [ ] **Navigateur, onglet 1** (Antoine) : `docs/architecture.md` sur GitHub,
      descendu jusqu'au schéma.
- [ ] **Navigateur, onglet 2** (Colin) : BigQuery, la requête « avant / après »
      collée.
- [ ] **Navigateur, onglet 3** (Colin) : le bucket GCS, dossier `bronze/`.
- [ ] **Navigateur, onglet 4** (Benjamin) : Airflow, le DAG
      `group6_marketplace_daily`.
- [ ] **Navigateur, onglet 5** (Anthony) : BigQuery, la requête du rapport
      quotidien collée.
- [ ] **Navigateur, onglet 6** (Anthony) : BigQuery, table
      `group6_warehouse.shipping_details`, onglet **Schema**.
- [ ] **Terminal 1** (Benjamin) : PowerShell dans `C:\de\l07`, la commande de
      back-fill tapée mais pas lancée.
- [ ] **Terminal 2** (Lenny) : PowerShell dans `infra\terraform`, la commande
      `plan` tapée mais pas lancée.
- [ ] Le navigateur zoomé à 125 % et les terminaux en gros caractères.
- [ ] Les notifications coupées : Windows (Assistant de concentration), mails,
      messageries.
- [ ] Le navigateur connecté à Google Cloud avec le compte de Benjamin.

### 6. Un essai d'enregistrement de 30 secondes

Enregistrer 30 secondes en parlant, puis relire le fichier : le son est clair,
le texte est lisible, et on entend aussi quelqu'un qui parle à un mètre du PC.

---

## Le jour J : déroulé et texte à dire

Avant d'appuyer sur « Enregistrer » : l'état « avant » est en place (étape 2),
et toutes les fenêtres de l'étape 5 sont ouvertes. Anthony lance
l'enregistrement, Antoine prend la souris.

### 0:00 – 1:00 · Antoine · le schéma

**À l'écran :** `docs/architecture.md` sur GitHub, le schéma Mermaid.

> Hi, we are group 6. This is the data platform we built for Albert's
> Marketplace, an online shop.
>
> On the left, the sources: the shop database, the clicks on the website, and
> an old export. Everything lands first in **bronze**, a raw copy kept exactly
> as it arrived. Then BigQuery and a tool called **dbt** turn it into **silver**,
> cleaned data, and **gold**, the tables people read.
>
> Who is it for? The analysts, who need one correct revenue figure, and the data
> science team, who need units sold per product, per country, per day.
>
> Every day, **Airflow** runs the whole chain. In this video you will see it
> run for real. Colin.

### 1:00 – 1:45 · Colin · avant

**À l'écran :** console BigQuery. Lancer la requête « avant / après » :

```sql
SELECT
  (SELECT COUNT(*) FROM `data-engineering-i1.group6_bronze.orders_raw`
    WHERE STARTS_WITH(order_date, '2026-09-16')) AS bronze_orders,
  (SELECT COUNT(*) FROM `data-engineering-i1.group6_gold.fct_order_items`
    WHERE order_date = '2026-09-16') AS gold_lines,
  (SELECT IFNULL(SUM(units_sold), 0) FROM `data-engineering-i1.group6_gold.fct_daily_demand`
    WHERE order_date = '2026-09-16') AS gold_units;
```

Attendu : **0, 0, 0.**

> The shop database stops on the 16th of September. Before recording, we
> removed that day from our platform, so you can watch it come back.
>
> This query counts the 16th in three places: orders in bronze, order lines in
> gold, and units in the daily table for the data science team. Right now: zero,
> zero, zero. Benjamin will load that day.

### 1:45 – 4:15 · Benjamin · le run Airflow

**À l'écran :** un terminal dans `C:\de\l07`, puis Airflow.

```powershell
docker compose exec airflow-scheduler airflow backfill create --dag-id group6_marketplace_daily --from-date 2026-09-16 --to-date 2026-09-16 --reprocess-behavior completed
```

Puis, dans Airflow : DAG `group6_marketplace_daily` → le run du 16 septembre →
vue **Graph**. Laisser tourner et commenter.

> This is our pipeline in Airflow. I am asking it to re-run one past day, the
> 16th of September. We call that a **back-fill**.
>
> *(the run starts)*
>
> There are six steps. First, two extract steps read that day's orders and
> order lines from the shop database and write them to a file. Then two load
> steps put them in BigQuery, with a **MERGE**: an order already there is
> updated, a new one is added. So if we run this day twice, nothing is
> duplicated. We tested that: a second run adds zero rows.
>
> *(while dbt_build runs)*
>
> Now **dbt build**. It rebuilds silver and gold, and it tests each table right
> after building it. If a test fails, everything after it is skipped, so a bad
> number never reaches gold. That is our quality gate.
>
> *(when it is green)*
>
> All green. *(open the dbt_build log, scroll to the end)* Here is the dbt
> summary: every test passed, zero errors. Colin, let's see if the data is
> there.

**Si une tâche passe en jaune ou en rouge :** ne pas arrêter. Ouvrir son log,
lire l'erreur à voix haute et dire ce qu'elle veut dire. Une tâche réessaie
toute seule après 5 minutes. Si l'erreur est claire (identifiants expirés,
image absente), dire ce qu'on ferait pour la corriger, puis passer à la suite.
La consigne dit de garder ça dans la vidéo.

### 4:15 – 5:00 · Colin · après

**À l'écran :** relancer la même requête dans BigQuery.

Attendu : **208, 364, 1 201.**

> Same query as before. Now: 208 orders in bronze, 364 order lines in gold, and
> 1,201 units in the daily table. These rows were not there two minutes ago.
>
> *(open the bucket gs://data-engineering-i1-group6, folder bronze/)*
>
> And this is the raw side, in Google Cloud Storage: bronze keeps the original
> files, so we can always rebuild everything. Anthony.

### 5:00 – 6:00 · Anthony · le rapport quotidien et une protection

**À l'écran :** console BigQuery.

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

> This is the daily report, read from gold: units and revenue per country for
> the 16th of September. Germany first with 336 units, then France with 296.
> In total, 1,201 units and about 32,800 euros. Each
> order is counted once here. The old export counted every order twice and
> doubled revenue.
>
> *(open group6_warehouse → shipping_details → Schema)*
>
> One protection: the phone and street columns carry a label, a **policy tag**,
> that decides who can read them. Our cleaning step also drops them before
> gold, and a test fails if personal data ever reaches gold. Honest limit: on
> this school project, every student holds the key to the label, so today it
> blocks nobody. Lenny.

### 6:00 – 7:30 · Lenny · Terraform, puis la suite

**À l'écran :** le terminal 2, dans `infra\terraform`. Lancer la commande `plan` de la préparation (étape 4).

> Our cloud setup is written as code with **Terraform**: the bucket, the
> datasets, the access rights, the labels. This command compares the code with
> what really exists in Google Cloud.
>
> *(the result is shown)*
>
> "No changes": nobody changed anything by hand, the cloud matches the code.
> *(If it shows changes: "It shows one change we wrote but have not applied
> yet: making two members read-only. We apply it once they agree.")*
>
> With one more month, we would do four things: make those two members
> read-only, prove the labels block someone with an account outside the
> student role, handle orders deleted in the shop, and get the admin rights we
> lack for a project-wide query limit and a budget alert. Thanks for watching.

Anthony arrête l'enregistrement.

---

## Après l'enregistrement

1. **Vérifier la durée :** entre 5 et 8 minutes. Si c'est en dehors, on
   recommence. On ne coupe pas.
2. **Mettre en ligne sur YouTube**, visibilité **« Non répertoriée »** (pas
   « Privée » : le prof ne pourrait pas l'ouvrir).
3. **Tester le lien** dans une fenêtre privée, sur un autre ordinateur que
   celui qui a enregistré.
4. **Ajouter le lien dans `README.md`**, en haut, dans une section
   `## Demo video`, puis ouvrir une PR.
5. **Rien à remettre en état :** après la vidéo, le 16 septembre est de nouveau
   chargé, comme avant la préparation.

## Si on doit recommencer

Refaire l'étape 2 de la préparation (retirer le 16 septembre, puis Trigger DAG
pour reconstruire gold), vérifier que la requête de Colin redonne 0, 0, 0, puis
relancer l'enregistrement.

## Vérifié le 23 novembre 2026

- Toutes les requêtes de ce guide ont été lancées sur BigQuery.
- `order_date` est bien au format `2026-09-16` dans bronze. Les lignes du
  16 septembre viennent toutes du DAG (`unnamed_0` vide).
- État actuel, donc « après » : **208** commandes en bronze, **364** lignes dans
  le script de retrait, **364** lignes et **1 201** unités dans gold,
  **32 802,35 €** pour la journée.
- L'étiquette est posée sur `street_address`, `city`, `zip` et `phone` dans
  `group6_warehouse.shipping_details`.
- **Pas encore vérifié :** la durée du run chez Benjamin, ses droits d'écriture
  sur `group6_silver` et `group6_gold`, et le résultat de `terraform plan` chez
  Lenny. C'est le rôle de la répétition.
