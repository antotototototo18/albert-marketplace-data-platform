# ADR-0010 : Donner l'accès par classe de données, pas par table

- **Statut :** proposé pour relecture du groupe
- **Date :** 2026-11-20
- **Auteur :** Anthony Rascle
- **Leçon :** L10

## Contexte

Le 16 novembre, n'importe quel compte du projet partagé `data-engineering-i1`
pouvait lire les 200 001 adresses et téléphones de
`group6_warehouse.shipping_details`
([preuve](../evidence/l10/01-who-can-see-what.txt)). Personne ne l'avait
décidé : c'était la somme des droits posés en L02 et L04 pour charger les
données.

[governance.md](../governance.md) donne maintenant une classe et un
propriétaire à chaque colonne. Cet ADR répond à une autre question : sur quoi
accrocher les droits d'accès.

Les faits qui comptent :

- Les colonnes personnelles sont peu nombreuses et concentrées. Le contact
  (`street_address`, `phone`) et la localisation fine (`city`, `zip`) ne sont
  que dans `shipping_details`. Les identifiants pseudonymes (`buyer_id`,
  `c_id`, `address_id`, `session_id`) sont dans une dizaine de tables, sur
  quatre couches.
- Aucun modèle dbt, aucune requête L04 et aucun tableau de bord ne lit le
  contact. `stg_shipping_details` supprime déjà la rue, le téléphone, la ville
  et le code postal. Le test `assert_no_personal_columns_in_gold` (C13) échoue
  si une colonne personnelle arrive en gold.
- `shipping_details` est recréée par `CREATE OR REPLACE` à chaque rechargement
  (`warehouse/03_native_load.sql`). Tout ce qui est posé sur la table, et pas
  dans le code, disparaît à ce moment-là.
- Les droits IAM du projet sont gérés par l'équipe enseignante. Le rôle
  étudiant donne déjà `bigquery.tables.getData` et
  `datacatalog.categoryFineGrainedReader` sur tout le projet
  ([permissions mesurées](../evidence/l10/02-project-permissions.txt)).

## Options

| Option | Apporte | Coûte |
|---|---|---|
| **Classer les colonnes, donner l'accès sur la classe** (policy tags) | Une règle par classe, qui couvre aussi les tables futures. Le droit et sa raison se lisent au même endroit. La table reste unique. | Deux clés à raisonner (lire la table, lire le tag). Un tag mal configuré ne protège rien, sans erreur visible. Les tags sautent à chaque `CREATE OR REPLACE`. |
| **Une vue par consommateur** | Chaque consommateur voit exactement la forme dont il a besoin, sans tag. | Une vue à maintenir par consommateur, pour toujours. Il faut aussi des vues autorisées, et retirer l'accès à la table source à chaque fois. |
| **Un dataset par niveau de sensibilité** | Simple, grossier, difficile à mal configurer : un droit par dataset. | Les mêmes données copiées deux fois, et deux copies à garder alignées. Une colonne sensible ajoutée au mauvais dataset est lisible par tous ses lecteurs. |
| **Faire confiance** | Rien à construire. | Ce n'est pas un contrôle. Le journal des jobs montre déjà 13 `SELECT *` sur `shipping_details` en bronze ([preuve](../evidence/l10/03-who-read-shipping.txt)). |

## Critères

| Critère | Classes | Vue par consommateur | Dataset par niveau | Confiance |
|---|---|---|---|---|
| Tient quand une table s'ajoute | Oui, si la colonne est classée | Non, une vue de plus | Oui, si elle va au bon dataset | — |
| Coût de maintenance pour 5 personnes | Faible : 2 tags, 1 script | Élevé : une vue par usage | Moyen : une copie à synchroniser | Nul |
| Répond à « qui peut lire quoi ? » par un fichier | Oui : matrice et `governance.tf` | En partie : il faut lire chaque vue | Oui : ACL des datasets | Non |
| Échec silencieux possible | Oui : taxonomie supprimée ou désactivée, tag perdu au rechargement | Faible | Faible | Toujours |
| Faisable dans le projet partagé | Oui à créer, mais ne refuse rien aux étudiants (voir plus bas) | Oui, même limite au niveau projet | Oui, même limite | Oui |

Aucune option ne bat les autres sur tous les critères. Les vues et les
datasets séparés sont plus difficiles à mal configurer. Les classes sont
moins chères à maintenir et elles restent vraies quand le schéma change.

## Décision proposée

Accrocher l'accès à la **classe** de la colonne, via la taxonomie
`group6-marketplace-pii` et ses policy tags (`pii-contact`,
`pii-location-coarse`). Le second droit (`categoryFineGrainedReader` sur
`pii-contact`) n'est donné à personne, sauf pendant une demande RGPD
(`pii_contact_readers` dans `governance.tf`).

La classe ne remplace pas la minimisation, elle s'y ajoute. dbt reste la
première barrière : silver supprime les colonnes de contact et gold n'en
contient aucune (C13). En pratique, gold joue déjà le rôle d'un « dataset
sans données personnelles ». Les policy tags protègent ce qui reste en amont,
là où les données brutes doivent rester.

Pourquoi pas les vues : nos consommateurs sont un modèle dbt et quelques
requêtes. Une vue par consommateur n'apporterait pas plus que ce que silver
fait déjà, et devrait être maintenue en plus. Pourquoi pas un dataset par
niveau : bronze et warehouse ont été construits en L02 à L04 autour d'une
copie par couche. En ajouter une par niveau doublerait les chargements et le
risque de décalage, pour quatre colonnes.

## Ce qui ne marche pas encore

La décision est appliquée mais **elle ne refuse rien aujourd'hui**. Le 17
novembre, le compte qui a posé les tags a lu les 200 001 rues et téléphones
([preuve](../evidence/l10/07-not-refused-student-key.txt)). Le rôle étudiant
contient la seconde clé au niveau du projet. Nous ne pouvons pas la retirer.

Cela ne change pas le choix : les autres options butent sur la même limite,
puisque le même rôle donne aussi la lecture de toutes les tables du projet.
Dans un projet dont nous serions administrateurs, la décision s'appliquerait
telle quelle. Les sept écarts entre la matrice et ce qui est appliqué sont
listés dans [governance.md](../governance.md#gaps-between-the-matrix-and-what-is-enforced).

## Conséquences

- Plus facile : répondre à « montrez-moi qui peut lire le téléphone » avec
  `governance.md` et `governance.tf`. Une nouvelle colonne de contact est
  protégée dès qu'on lui pose le tag, sans nouvelle vue.
- Plus difficile : il faut raisonner avec deux clés. La seule preuve qu'une
  colonne est protégée est un refus, pas le schéma : le schéma garde le tag
  même si la taxonomie a été supprimée.
- À surveiller :
  - relancer `scripts/apply_policy_tags.py` après chaque rechargement de
    `shipping_details` ;
  - traiter `roles/datacatalog.categoryAdmin` et `governance.tf` comme
    privilégiés ;
  - refaire le test de refus avec un compte qui n'a pas le rôle étudiant,
    dès que l'équipe enseignante peut en fournir un ;
  - les colonnes de texte libre (`unclassified`) ne sont pas taggées. Si on
    les tague un jour, ce sera avec `pii-contact`, pas avec une classe à part.
