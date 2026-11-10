# ADR-0008 : État Terraform partagé dans GCS

- **Statut :** proposé pour relecture ; backend vérifié dans GCP
- **Date :** 2026-11-10
- **Leçon :** L08

## Contexte

L'équipe adopte les ressources L02-L07. L'état associe leurs identifiants aux
adresses Terraform ; il doit être partagé sans devenir un fichier versionné
dans Git. Plusieurs membres pourront lancer un plan ou une application.

## Options

| Option | Apporte | Coûte |
|---|---|---|
| État local | Aucun service à préparer. | Un ordinateur détient la seule copie ; partage manuel, risques de copies divergentes. |
| Bucket GCS | État partagé, verrouillage et versions récupérables. | Amorçage et accès du bucket à gérer séparément. |
| Terraform Cloud | Verrouillage, historique et politiques gérés. | Comptes supplémentaires et état confié à une plateforme externe. |

## Décision

Utiliser `gs://data-engineering-i1-group6-tfstate`, en `europe-west1`, avec
versioning activé, accès uniforme et accès public bloqué. Le workspace
`default` stockera l'objet `platform/default.tfstate`, conformément au backend
dans `infra/terraform/versions.tf`. GCS assure le verrouillage des opérations
Terraform concurrentes. Ne pas désactiver le verrouillage pour contourner
une opération en cours.

Ce bucket est amorcé une fois en dehors de cette configuration afin que
`terraform init` dispose déjà du stockage dont il a besoin. Le bucket et cet objet existaient déjà le 10 novembre ; les dix ressources
suivies ont été conservées, sans migration ni recréation. Les preuves de
versioning et des générations sont dans `docs/evidence/l08/`.

## Qui peut lire le bucket ?

La politique du bucket lue le 10 novembre comporte six liaisons par défaut :

| Principal | Droits observés sur le bucket |
|---|---|
| `projectOwner:data-engineering-i1` | `roles/storage.legacyBucketOwner` et `roles/storage.legacyObjectOwner` : administration du bucket et lecture/écriture des objets. |
| `projectEditor:data-engineering-i1` | Mêmes deux rôles, donc lecture/écriture de l'état. |
| `projectViewer:data-engineering-i1` | `roles/storage.legacyBucketReader` et `roles/storage.legacyObjectReader` : lecture de l'état. |

[Politique observée](../evidence/l08/06-backend-iam.json). Les personnes derrière
ces groupes projet ne sont pas connues avec nos permissions : **l'état n'est
pas limité aux cinq membres du groupe**. La prévention d'accès public ne réduit
pas ces droits internes. Aucun droit supplémentaire ni aucune identité CI n'a
été ajouté. L'état peut contenir des valeurs sensibles, d'où un bucket séparé
du bronze et l'absence de clés dans la configuration.

La cible L10 est l'accès des seuls membres autorisés à appliquer et des
administrateurs, à faire confirmer par l'enseignant avec les accès hérités.
Aucun rôle projet ne sera géré dans ce Terraform. Le backend requiert lecture,
écriture et suppression d'objets pour gérer état et verrou ; la simple lecture
ne suffit pas pour appliquer.

## Si quelqu'un supprime l'état

Arrêter les applications. Ne pas lancer un apply sur un état vide : Terraform
pourrait proposer des créations de ressources qui existent encore. L'état
effacé ne détruit pas ces ressources mais fait perdre leur association au code.

Lister les générations de `platform/default.tfstate`, choisir la dernière
version valide et la restaurer comme version courante avec l'administrateur,
sans opération Terraform concurrente. Vérifier les ressources et le plan avant
de reprendre. Le versioning permet cette récupération après suppression de
la version courante ; il ne protège pas contre l'effacement de toutes les
générations ni la destruction du bucket. La suppression réversible offre une
protection supplémentaire si elle est activée et sa fenêtre non expirée.

Sans version récupérable ni sauvegarde, reconstruire l'état par import de chaque
ressource, puis comparer intégralement le plan. Cela coûte un nouvel inventaire,
des imports et une revue ; les données cloud ne sont pas une sauvegarde de l'état.

## Conséquences et vérification

Le groupe partage un état et une procédure de récupération ; le bucket et ses
accès deviennent une dépendance préalable. Versioning, politique IAM,
emplacement et plan nul ont été vérifiés le 10 novembre ; l'acceptation
reste soumise à la relecture du groupe. La CI se limite à
`init -backend=false`, format et validation, sans accès au backend.

Références : [backend GCS et verrouillage](https://developer.hashicorp.com/terraform/language/backend/gcs),
[état Terraform dans Cloud Storage](https://docs.cloud.google.com/docs/terraform/resource-management/store-state).
