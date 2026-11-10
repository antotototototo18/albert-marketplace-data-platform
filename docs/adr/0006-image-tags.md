# ADR-0006 — Images privées et tags de build

Date : 2026-11-03. Statut : proposé pour relecture ; rétention bloquée par IAM.

## Contexte

L'extracteur SQL, le consumer Kafka (même environnement d'ingestion) et dbt
doivent tourner sans Python installé sur la machine hôte. Un tag doit désigner
un seul build ; le digest du registre est l'identifiant définitif de son contenu.
Les sources de production évoluent : la preuve utilise trois commandes SQL
figées, dans une base isolée sans port publié, et deux volumes de sortie neufs.

## Décision

Utiliser Artifact Registry privé, projet `data-engineering-i1`, dépôt existant
`dataeng`, région `europe-west1`, sous les noms `group6-ingestion` et
`group6-transform`. Les membres autorisés du projet peuvent télécharger les
images ; aucun accès public ni compte supplémentaire n'est créé. Ce choix
réutilise l'authentification et la région de la plateforme GCS/BigQuery.
Le stockage du registre est à surveiller dans la facturation du projet.

Format : `YYYYMMDDT-step6-NN`, date UTC et numéro de build jamais réutilisé,
par exemple `20261103T-step6-01`. Toute reconstruction reçoit le numéro suivant,
même sans changement de code. Aucun alias flottant n'est publié. Avant un push,
lister les tags avec `gcloud artifacts docker tags list IMAGE` et refuser un
nom existant. Ne jamais déplacer un tag ni reconstruire sous un ancien nom.
Conserver le digest du push dans les preuves et utiliser `IMAGE@sha256:…`
pour les exécutions d'orchestration et les retours arrière.

La création d'un dépôt dédié avec `--immutable-tags` a été essayée, mais le
compte étudiant n'a pas `artifactregistry.repositories.create`. Le dépôt partagé
existant est mutable : l'interdiction de réaffecter les tags est actuellement
une règle d'équipe, pas une garantie IAM. Ne pas prétendre le contraire.
Un administrateur devra fournir un dépôt immuable pour imposer cette règle
côté serveur ; les digests utilisés au déploiement restent immuables.

La base Python est fixée par version et digest OCI. Les fichiers
`requirements.lock` fixent aussi les dépendances transitives. `dbt_utils`
est fixé par `packages.yml` et `package-lock.yml` et installé au build.
La plateforme publiée est `linux/amd64` ; Docker Desktop sur Apple Silicon
l'exécute par émulation. Les jobs tournent sous UID/GID `10001:10001`.
Les secrets arrivent uniquement à l'exécution, via variables ou montage ADC
en lecture seule. Le contexte Docker racine utilise une liste d'inclusion.

## Retour arrière

Relever le digest de la version validée dans `docs/reproduce.md`, puis :

```sh
IMAGE=europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-ingestion
DIGEST=sha256:45174dffd123b9a406624c736dfc6ac0b137ce26584b98d9271faa1b3003bfd7
docker pull --platform linux/amd64 "$IMAGE@$DIGEST"
docker run --rm --platform linux/amd64 --env-file .env "$IMAGE@$DIGEST"
```

Pour dbt, prendre le digest `group6-transform` des preuves, monter les ADC comme
dans le README, puis exécuter `dbt build` par la commande Docker documentée.
Restaurer une image ne restaure pas les données ou les checkpoints : vérifier
leur compatibilité avant de relancer un writer. Ne jamais supprimer un checkpoint
de production pour obtenir artificiellement le même nombre de lignes.

## Rétention et application

- Conserver la version évaluée L06 et toute version actuellement déployée
  jusqu'à la fin du cours et 30 jours après la soutenance.
- Pour chaque job, conserver les trois builds validés les plus récents et
  tous les builds de moins de 30 jours. Les autres sont supprimables seulement
  s'ils ne sont référencés par aucun déploiement ou preuve encore nécessaire.
- Les builds échoués/non validés expirent après 7 jours. Les images explicitement
  jetables de test de rétention sont supprimées dès la fin du test.
- Avant chaque publication, puis mensuellement, l'auteur inventorie les tags,
  sélectionne les versions expirées de ses seuls chemins `group6-*`, vérifie
  les références et supprime les digests sélectionnés. Garder commande, sortie
  et inventaire après suppression dans les preuves. Ne pas supprimer des
  manifests enfants OCI encore référencés par un index conservé.

Commande exécutée pour l'image jetable dédiée (pas un alias d'une release) :

```sh
gcloud artifacts docker images delete \
  europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group6-retention-probe:20261103-step6-01 \
  --delete-tags --quiet
```

La suppression a été refusée : `artifactregistry.tags.delete` manque au compte
étudiant. La sortie réelle et l'inventaire après la tentative sont dans
[le transcript de reproduction](../reproduce.md). L'image jetable reste présente.
**L'application effective de la rétention reste à faire** par un administrateur
ou après attribution des permissions de suppression. Aucun build de production
n'est encore expiré. Ne pas présenter cette tentative comme une preuve de
suppression réussie.
Une suppression de digest avec `--delete-tags` retire tous ses tags : toujours
vérifier qu'il ne partage pas le digest d'une release protégée.

## Alternatives

Docker Hub public simplifierait les pulls, mais exposerait le code d'un dépôt
privé et le modèle du cours. Des tags de version sémantique conviennent à un
produit publié ; ils n'identifient pas chaque build étudiant sans convention
supplémentaire. Une date seule distingue mal plusieurs builds dans la journée.
Un SHA Git seul ne distingue pas deux builds du même commit ; un digest complète
donc toujours le tag humain.

## Conséquences et réexamen

Le pull exige l'authentification au registre privé. La reproduction peut se
faire sans SDK GCP installé sur l'hôte via le conteneur CLI du README. Les
digests garantissent l'identité de l'image téléchargée, pas celle des données
externes. Les fichiers Parquet comportent des noms et checkpoints horodatés :
le test compare exactement les lignes normalisées, pas les métadonnées variables.

Revoir ce choix si le projet du cours ferme, si le coût devient significatif,
si une distribution publique est autorisée ou si plusieurs architectures
deviennent nécessaires. Un registre dédié immuable est prioritaire dès que
les droits administrateur sont disponibles.
