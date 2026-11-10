# ADR-0009 : Attribution des coûts du projet partagé

- **Statut :** proposé pour relecture du groupe
- **Date :** 2026-11-10
- **Leçon :** L09

## Contexte

Le projet `data-engineering-i1` est partagé entre plusieurs groupes. Les noms
de ressources identifient souvent leur propriétaire, mais les jobs BigQuery
et les coûts passés n'ont pas tous de labels. Le groupe ne dispose ni de
l'administration de l'organisation, ni d'un export de facturation identifié.

L08 a adopté le bucket et les quatre datasets partagés. L09 doit permettre
d'en retrouver les coûts sans confondre unités consommées, estimations et facture.

## Options

| Option | Apporte | Coûte |
|---|---|---|
| Labels sur les ressources et jobs | Un projet et une facture ; attribution par requête. | Effet uniquement futur, labels incomplets possibles, prise en charge variable selon la ressource. |
| Un projet par équipe | Attribution native par projet, séparation des accès et quotas. | Projets à provisionner, administration de facturation et échanges entre projets. |
| Tags | Héritage et contraintes possibles par politiques. | Mise en place au niveau organisation, inaccessible au groupe ; prise en charge des services à vérifier. |
| Répartition manuelle | Aucun déploiement supplémentaire. | Travail récurrent, approximations sur les jobs partagés et erreurs difficiles à détecter. |

## Décision proposée

Garder le projet pédagogique partagé et appliquer quatre clés : `team`,
`environment`, `pipeline`, `component`. Leurs valeurs et raisons sont dans
[costs.md](../costs.md#convention-de-labels). Les labels des cinq ressources
compatibles ont été posés par Terraform ; un plan final sans changement
confirme leur présence. Les membres IAM n'acceptent pas de labels et sont
rattachés à leur dataset. Le bucket d'état hors Terraform reste une exception
visible, suivie par nom.

Les labels de dataset ne suffisent pas pour les requêtes : le DAG envoie des
labels aux jobs `bq`, et dbt configure à la fois ses modèles et ses jobs.
Une sonde réelle a vérifié les labels d'un job dbt. Les labels des anciennes
tables seront appliqués au prochain build ; aucune réécriture des données
n'a été faite uniquement pour les ajouter.

Quand la vue de facturation sera accessible, grouper par jour, service, SKU,
devise et équipe, en conservant la catégorie `unattributed`. Additionner les
crédits sans multiplier les coûts par les lignes de labels. Le SQL est versionné
dans `warehouse/queries/l09_billing_daily.sql`.

En attendant, utiliser les octets des jobs et les métadonnées de stockage.
L'historique est rapproché par les tables `group6_*` référencées : cela aide à
analyser les pics mais ne reconstitue pas une attribution comptable exacte.
Les jours sans activité sont absents de la vue des jobs. Les prix publics
datés servent à estimer ; les franchises partagées ne sont pas allouées
arbitrairement au groupe.

## Alerte et limites

Un budget projet de 10 USD/mois vers Anthony est préparé dans Terraform mais
désactivé : l'API Budget est coupée et son activation est refusée au compte
étudiant. Il couvre tout le projet, donc aussi les autres groupes. Le montant,
la devise et les accès doivent être confirmés avec l'administrateur avant
activation ; la réception d'une alerte reste à prouver.

L'alerte **does not stop spending**. Les coûts remontent avec un délai et les
crédits inclus peuvent retarder les seuils. Les plafonds par requête restent
nécessaires. Les labels n'isolent pas les données et ne donnent aucun droit IAM.

## Avec dix équipes

Demander un projet par équipe et par environnement, rattaché à la facturation
commune, avec export centralisé, budgets par projet et droits administrés
au niveau organisation. Conserver des labels pour les composants à l'intérieur
d'un projet ; définir explicitement comment répartir les services mutualisés.
Ajouter des contrôles de présence des clés au provisioning. Multiplier les
valeurs de labels dans un seul projet ne fournit ni frontière d'accès, ni
garantie de couverture des jobs manuels.

## Conséquences

La consommation future est plus lisible sans déplacer de données. L'ancien
historique reste partiellement non attribuable et les scripts peuvent manquer
des ressources personnelles hors périmètre. Le registre expose ces limites.
L'alerte et la relecture du groupe restent nécessaires pour clôturer L09.
