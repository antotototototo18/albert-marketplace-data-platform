# Slide 4 — Décision 2 : l'accès par classe de données

**Qui parle :** Anthony · **Durée :** 2 min

## Message clé

On accroche les droits à la classe de la colonne, pas à la table. Aujourd'hui
le tag ne refuse personne, et on peut expliquer pourquoi.

## À dire

Le texte exact, en anglais, est dans [SCRIPT.md](../../SCRIPT.md), section
« Slide 4 — Decision 2: who can read personal data ». Il est aussi dans les notes de la slide.

## Si on nous demande

- L'ADR : [ADR-0010](../../../adr/0010-data-classification.md), et la matrice
  d'accès dans [governance.md](../../../governance.md).
- « Montrez-moi votre classification et votre matrice d'accès » :
  [governance.md](../../../governance.md) et `infra/terraform/governance.tf`.
- La preuve que le tag ne refuse rien :
  [evidence/l10/07](../../../evidence/l10/07-not-refused-student-key.txt).
- Les 13 `SELECT *` sur `shipping_details` :
  [evidence/l10/03](../../../evidence/l10/03-who-read-shipping.txt).
- **À valider par Anthony :** la ligne « changer d'avis » vient du tableau de
  critères de l'ADR, l'ADR ne le dit pas en une phrase. L'ajouter à l'ADR
  avant la soutenance, ou changer la slide.
