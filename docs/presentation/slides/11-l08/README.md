# Slide 11 — L08, Terraform

**Qui parle :** Lenny · **Durée :** 1 min 15

## Message clé

La plateforme est décrite en code, et Terraform voit quand quelqu'un la modifie
à la main.

## À dire

- Dix ressources sont suivies dans l'état Terraform, reprises sans être
  recréées ; le plan affiche « No changes ».
- Antoine a déclaré le bucket de L02 et le dataset de L04.
- État distant dans un bucket GCS versionné, hors de Git.
- Test de dérive : l'âge Nearline du lifecycle passé de 45 à 46 jours hors
  Terraform, détecté par le plan puis écrasé.
- `fmt` et `validate` tournent en CI, sans identifiants cloud.
- Limite : aucun compte de service, car le créer demande des droits d'admin.

## Si on nous demande

- Ressources, dérive et plans : [infra.md](../../../infra.md),
  [evidence/l08/](../../../evidence/l08/).
- Décision : [ADR-0008](../../../adr/0008-remote-state.md).
- Code : [infra/terraform/](../../../../infra/terraform/).
