# Slide 13 — L10, gouvernance

**Qui parle :** Benjamin, puis Anthony · **Durée :** 1 min 45

## Message clé

Chaque colonne a une classe et un propriétaire, une personne peut être
effacée, et l'ADR-0010 explique le choix. Mais le tag ne refuse personne :
le rôle étudiant donne déjà la seconde clé. Le droit réduit n'est pas encore
appliqué.

## À dire

- **Benjamin (1 min) :**
  - Classification : chaque colonne du warehouse a une classe, un propriétaire
    et une raison. Le texte libre (`r_desc`, `title`, `raw_event`) est marqué
    `unclassified`.
  - Matrice d'accès : un rôle par classe, et pour chaque « non » un moyen de
    demander l'accès. Personne ne lit `pii.contact` en routine.
  - Application : taxonomie créée par Terraform, `street_address` et `phone`
    taggés `pii-contact`, `city` et `zip` taggés `pii-location-coarse`.
  - Test du 17 novembre : le compte qui a posé les tags lit toujours les
    200 001 adresses et téléphones. Le rôle étudiant contient
    `categoryFineGrainedReader` au niveau du projet. On ne peut pas le changer.
  - Droit réduit : `dataEditor` remplacé par `dataViewer` sur bronze et
    warehouse dans `iam.tf`. **Pas encore appliqué** : le 20 novembre, Antoine
    et Colin avaient encore `WRITER`. Il manque leur accord, puis un
    `terraform apply`.
- **Anthony (45 s) :**
  - Effacement testé le 20 novembre sur un vrai acheteur : 54 fichiers bronze
    réécrits (1 419 lignes), 13 tables natives, gold reconstruit. 0 ligne
    restante dans tout ce que le groupe possède.
  - Ce qui survit : 7 jours de soft delete et de time travel, les datasets
    personnels des membres, et la source. Un rechargement depuis la source
    ramène la personne.
  - ADR-0010 : accès par classe plutôt qu'une vue par consommateur ou un
    dataset par niveau. dbt reste la première barrière : gold n'a aucune
    colonne personnelle.

## Sources

- PR #16, fusionnée le 20 novembre
- [governance.md](../../../governance.md) (classes, matrice, 7 lacunes)
- [governance.tf](../../../../infra/terraform/governance.tf),
  [apply_policy_tags.py](../../../../scripts/apply_policy_tags.py),
  [iam.tf](../../../../infra/terraform/iam.tf)
- Preuves : [colonnes taggées](../../../evidence/l10/06-columns-tagged.txt),
  [pas de refus](../../../evidence/l10/07-not-refused-student-key.txt),
  [qui écrit](../../../evidence/l10/08-who-writes.txt),
  [effacement](../../../evidence/l10/09-erasure-test.txt)
- [Runbook d'effacement](../../../runbooks/erasure.md),
  [erase_person.py](../../../../scripts/erase_person.py),
  [ADR-0010](../../../adr/0010-data-classification.md)

## Points à confirmer

- D'après Git, les trois commits de classification, matrice et tags sont de
  Benjamin. Si Lenny ou Antoine y ont contribué, corriger les noms ici.
- Le runbook était prévu pour Colin ; Anthony l'a écrit et testé. Colin le
  relit.
- Mettre « Apply pending » à jour dès que `terraform apply` est fait.
