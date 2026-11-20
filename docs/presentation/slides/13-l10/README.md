# Slide 13 — L10, gouvernance

**Qui parle :** Benjamin, puis Colin et Anthony · **Durée :** 1 min 45

## Message clé

Chaque colonne a une classe et un propriétaire, et quatre colonnes ont un
policy tag. Mais le tag ne refuse personne : le rôle étudiant donne déjà la
seconde clé. Le runbook d'effacement et l'ADR-0010 restent à faire.

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
    warehouse, car seul le membre qui lance les chargements y écrit.
- **Colin (20 s) :** le runbook d'effacement, à tester une fois sur un vrai
  identifiant.
- **Anthony (20 s) :** l'ADR-0010, qui explique pourquoi on donne l'accès par
  classe plutôt que par table.

## Sources

- PR #16, fusionnée le 20 novembre
- [governance.md](../../../governance.md) (classes, matrice, 7 lacunes)
- [governance.tf](../../../../infra/terraform/governance.tf),
  [apply_policy_tags.py](../../../../scripts/apply_policy_tags.py)
- Preuves : [colonnes taggées](../../../evidence/l10/06-columns-tagged.txt),
  [pas de refus](../../../evidence/l10/07-not-refused-student-key.txt),
  [qui écrit](../../../evidence/l10/08-who-writes.txt)

## Points à confirmer

- D'après Git, les trois commits L10 sont de Benjamin. Si Lenny ou Antoine ont
  contribué à la classification ou à la matrice, corriger les noms ici.
- Le runbook et l'ADR n'existent pas encore. Mettre cette slide à jour dès
  qu'ils sont fusionnés.
