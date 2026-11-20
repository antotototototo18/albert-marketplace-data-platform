# Runbook : effacer une personne (RGPD, article 17)

Pour la personne qui traite une demande d'effacement sans avoir construit la
plateforme. Testé une fois, le 2026-11-20, sur un vrai acheteur
([preuve](../evidence/l10/09-erasure-test.txt)).

**En bref :** le bucket bronze, les tables natives, silver et gold sont
effacés en une dizaine de minutes avec `scripts/erase_person.py` et dbt. Il
reste des copies que ce runbook n'efface pas : 7 jours de soft delete et de
time travel, les datasets personnels des membres, et la source elle-même.
Elles sont listées à l'étape 6.

## 0. Avant de commencer

- La demande est une issue « Demande RGPD » : qui demande, l'identifiant
  (`buyer_id`), la date. L'issue est le registre de la demande. Écrire
  l'identifiant **en clair uniquement dans l'issue privée ou par message**,
  jamais dans le dépôt : dans le dépôt, on écrit son SHA-256.
- Vérifier que l'effacement est dû. Les commandes peuvent relever d'une
  obligation de conservation comptable (article 17(3)(b)). Ici, nous
  effaçons tout, parce que c'est un jeu de cours. Dans une vraie entreprise,
  il faut poser la question au juriste avant de supprimer des commandes.
- Prévenir le groupe : les chiffres de gold changent (34 commandes en moins
  lors du test).
- Droits nécessaires : écriture sur le bucket `data-engineering-i1-group6` et
  sur `group6_bronze` et `group6_warehouse`. Le compte qui lance les
  chargements (L04, L07) les a. `scripts/apply_policy_tags.py` n'a pas besoin
  d'être relancé : un `DELETE` garde les policy tags (seul un
  `CREATE OR REPLACE` les perd).
- Environnement : `pip install -r transform/requirements.txt pyarrow
  google-cloud-storage`, puis `gcloud auth application-default login`.

## 1. Trouver la personne : chaque table et colonne qui la porte

```bash
W=/private/tmp/erasure-<numéro de l'issue>   # hors du dépôt
python scripts/erase_person.py find --buyer-id '<buyer_id>' --workdir "$W"
```

Le script part du `buyer_id` et retrouve les identifiants liés dans le
warehouse : commandes, paiement, adresses, avis, sessions clickstream. Il
télécharge ensuite tout `bronze/` (316 objets, 1,17 Go, environ 1 minute) et
compte les lignes de la personne dans chaque fichier. Il compte enfin les
lignes dans les quatre datasets du groupe.

Les colonnes qui portent la personne (voir [governance.md](../governance.md)) :

| Identifiant | Colonnes | Tables |
|---|---|---|
| acheteur | `buyer_id`, `c_id` (même valeur) | orders, review, buyer, customer, customer_shipping, customer_payment, cart, returns, subscription, wishlist_item, clickstream |
| adresse | `address_id` | customer_shipping, shipping_details |
| paiement | `payment_id` | orders, payment, payment_details, customer_payment |
| commande | `order_id` | orders, order_items, payment, shipment, clickstream |
| avis | `review_id` | review, product_reviews, seller_reviews, review_images |
| session | `session_id` | clickstream |
| texte libre | n'importe où dans la chaîne | `raw_event` du clickstream, DLQ |

Les lignes de commande, de livraison et les images d'avis sont effacées
aussi : elles ne nomment personne, mais elles décrivent ce que la personne a
acheté ou publié.

**Lancer `find` avant toute suppression**, et garder `$W/ids.json` jusqu'à
la fin. Les identifiants liés sont lus dans le warehouse : une fois
`orders` effacée, ils ne peuvent plus être retrouvés.

Lors du test : 54 objets du bucket et 13 tables natives contenaient la
personne.

## 2. Bronze : le bucket

```bash
python scripts/erase_person.py erase --workdir "$W" --dry-run   # compte, n'écrit rien
python scripts/erase_person.py erase --workdir "$W"
```

Le bronze est immuable par conception (ADR-0002). L'effacer veut donc dire
**réécrire** chaque fichier Parquet concerné sans les lignes de la personne.
Le nouveau fichier garde le même nom et la même compression. L'upload est
conditionné à la génération lue par `find` : si quelqu'un a réécrit le
fichier entre-temps, il échoue, et il faut relancer `find`.

Les tables externes de `group6_bronze` lisent directement ces fichiers : il
n'y a rien d'autre à faire pour elles.

Un fichier qui n'est pas en Parquet (DLQ JSON, état, validation) est signalé
`NOT PARQUET` et doit être traité à la main. Il n'y en a pas eu lors du test.

Durée du test : 54 objets réécrits, 1 419 lignes retirées, 39 s. Cela
concerne surtout `airbyte/`, qui garde un instantané par synchronisation :
la même commande y est présente 7 fois.

## 3. Tables natives : bronze et warehouse

La même commande `erase` lance ensuite un `DELETE` sur les 13 tables natives
du groupe : `group6_bronze.orders_raw`, `order_items_raw`, et dans
`group6_warehouse` les tables `orders`, `order_items`, `order_items_day`,
`review`, `product_reviews`, `customer_shipping`, `shipping_details` et les
copies `*_untuned` de L04.

La vue matérialisée `daily_demand` se met à jour seule. Durée du test :
13 requêtes, 28 s.

## 4. Silver et gold

```bash
cd transform && dbt build --profiles-dir .
```

Silver est fait de vues : elles n'ont plus la personne dès l'étape 3. Gold
est fait de tables : `dbt build` les reconstruit toutes (`fct_order_items`,
`fct_daily_demand`, les dimensions) et relance les tests.

Lors du test : `PASS=92 WARN=2 ERROR=0`, en 37 s. Les deux avertissements
étaient déjà connus (C12, et le code pays de `fct_order_items`).

## 5. Prouver que c'est fait

```bash
python scripts/erase_person.py verify --workdir "$W"
```

Le script retélécharge tout le bucket, le parcourt à nouveau, et compte les
lignes dans les quatre datasets du groupe. Le résultat attendu est `0` objet
et `none` table.

Dans l'issue, et dans `docs/evidence/` si besoin, on note :

- le SHA-256 de l'identifiant ;
- les comptes avant et après par table ;
- les identifiants des jobs `DELETE` ;
- la date de suppression définitive (étape 6).

Puis **supprimer `$W`**. Il contient l'identifiant en clair et, pendant
`find`, une copie complète du bronze.

Une limite : le SHA-256 d'un identifiant pseudonyme reste un lien. Quelqu'un
qui a l'identifiant peut vérifier que cette personne a fait une demande. Nous
le gardons quand même, car il faut bien prouver quelle personne a été
effacée.

## 6. Les copies qui survivent

| Copie | Durée | Ce qu'on peut faire |
|---|---|---|
| **Soft delete du bucket** : les anciennes générations des 54 fichiers | 7 jours (`soft_delete_policy` = 604 800 s dans `main.tf`). Lors du test, restaurables jusqu'au 2026-11-27 09:38 UTC. Le versioning est désactivé, donc rien au-delà. | Rien avant l'échéance. Réduire la durée vaut pour tout le bucket et enlève aussi la protection contre une suppression par erreur. Nous la gardons à 7 jours et nous répondons à la demande avec cette date. |
| **Time travel BigQuery** sur les 4 datasets du groupe | 168 h, puis 7 jours de fail-safe que nous ne pouvons pas lire. Lors du test, `FOR SYSTEM_TIME AS OF` relisait encore les 34 commandes. | Le minimum est 48 h (`max_time_travel_hours`). C'est une décision du groupe, car le time travel sert aussi à réparer un mauvais chargement. Non changé. |
| **Datasets personnels et d'exercice** : `group6_l07_bc_gold` (Benjamin, L07), `l04_rabeau`, `l05_rabeau`, `l07_rabeau`, `l07_ex1_rabeau`, `rabeau_antoine` (Antoine) | Sans limite | Non touchés : ce sont les données de chacun. Leur propriétaire les supprime ou les efface. Le script ne les compte pas : utiliser la requête de comptage de la preuve, ou les supprimer à la fin du cours. |
| **La source** : `legacy_csv.tar.gz` sur les ordinateurs des membres, et la base source d'Airbyte | Sans limite | Hors de notre contrôle (fournies par le cours). **Recharger le bronze depuis la source ramène la personne.** Il manque une liste de suppression (les SHA-256 des personnes effacées) appliquée à l'ingestion. Ce n'est pas fait. |
| `docs/evidence/l02-bronze-legacy-manifest.json` | — | Il décrit encore les fichiers du 16 octobre (lignes, empreintes). Il ne contient pas de données personnelles, mais il n'est plus exact. |

## Ce que le test a montré

- Tout ce que le groupe possède a été effacé, et la preuve le montre : 0
  ligne restante dans le bucket, bronze, warehouse, silver et gold.
- La partie lente n'est pas l'effacement : c'est de trouver où la personne
  se trouve. Le premier passage, inventaire compris, a pris environ
  30 minutes. Avec le script, comptez environ 5 minutes de calcul et
  autant de relecture.
- Deux bugs du script ont été trouvés en le relançant après coup : une liste
  d'identifiants vide et un fichier Parquet sans ligne faisaient planter le
  scan. Ils sont corrigés.
- Ce qui n'est pas résolu : 7 jours de copies restaurables, les copies
  personnelles, et le retour de la personne au prochain rechargement depuis
  la source.
