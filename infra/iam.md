# Accès au bucket bronze

État lu le 16 octobre 2026 avec
`gcloud storage buckets get-iam-policy gs://data-engineering-i1-group6`.
Ces fichiers deviendront du Terraform en L08 ; ils doivent toujours
correspondre au bucket réel.

## Configuration du bucket

Lue avec `gcloud storage buckets describe gs://data-engineering-i1-group6` :

| Réglage | Valeur | Pourquoi |
|---|---|---|
| Projet | `data-engineering-i1` (n° 671557693556), partagé par toute la promotion | Imposé par le cours |
| Région | `europe-west1`, mono-région | Consigne L02 ; même région que les futurs datasets BigQuery, donc lecture sans frais de transfert |
| Classe par défaut | `STANDARD` | Données relues en L04-L05 ; le [lifecycle](lifecycle.json) les déplace ensuite |
| Accès uniforme au niveau du bucket | Activé | Droits gérés uniquement par IAM, sans ACL par objet |
| Prévention de l'accès public | `enforced` | Aucun objet ne peut être rendu public |
| Suppression réversible (soft delete) | 7 jours | Un objet supprimé par erreur reste récupérable une semaine |
| Versioning | Désactivé | Bronze n'est jamais réécrit : chaque chargement crée une nouvelle partition |

## Liaisons IAM du bucket

| Principal | Rôle | Portée | Pourquoi |
|---|---|---|---|
| `projectOwner:data-engineering-i1` | `roles/storage.legacyBucketOwner` | Bucket | Liaison par défaut de GCS : les propriétaires du projet administrent le bucket |
| `projectEditor:data-engineering-i1` | `roles/storage.legacyBucketOwner` | Bucket | Liaison par défaut : les éditeurs du projet administrent le bucket et peuvent écrire dans bronze |
| `projectViewer:data-engineering-i1` | `roles/storage.legacyBucketReader` | Bucket | Liaison par défaut : les lecteurs du projet peuvent lister le bucket |
| `projectOwner:data-engineering-i1` | `roles/storage.legacyObjectOwner` | Objets du bucket | Liaison par défaut : lecture et écriture des objets |
| `projectEditor:data-engineering-i1` | `roles/storage.legacyObjectOwner` | Objets du bucket | Liaison par défaut : lecture et écriture des objets |
| `projectViewer:data-engineering-i1` | `roles/storage.legacyObjectReader` | Objets du bucket | Liaison par défaut : lecture des objets, donc des données personnelles de bronze |

Aucune liaison n'a été ajoutée par le groupe : ce sont les six liaisons
créées automatiquement avec le bucket. Le compte `arabeau@albertschool.com`
dispose de tous les droits testés (`storage.buckets.get`, `update`,
`getIamPolicy`, `setIamPolicy`, `storage.objects.list`, `get`, `create` et
`delete`), vérifiés avec l'API `testIamPermissions`.

## Ce que cela implique

- **Les personnes concernées ne sont pas connues.** Les membres des rôles
  projet n'ont pas pu être listés : `gcloud projects get-iam-policy` est refusé
  à nos comptes. Si la promotion entière est éditrice du projet, **d'autres
  groupes peuvent lire, écrire et supprimer notre bronze**, données
  personnelles comprises.
- **Le moindre privilège n'est pas encore atteint.** La cible est la suivante :
  - un compte de service d'ingestion avec `roles/storage.objectCreator` sur ce
    seul bucket ;
  - un compte de service de chargement BigQuery avec
    `roles/storage.objectViewer` ;
  - les membres du groupe en `roles/storage.objectAdmin` sur le bucket ;
  - le retrait des liaisons `legacy*` héritées du projet.
- **Ce qui manque pour y arriver :** la création de comptes de service n'est
  pas autorisée à nos comptes (voir [infra.md](../docs/infra.md)).
  Il faut la demander à l'enseignant. C'est l'objet de L10.

## Vérifier

```sh
gcloud storage buckets describe gs://data-engineering-i1-group6
gcloud storage buckets get-iam-policy gs://data-engineering-i1-group6
```
