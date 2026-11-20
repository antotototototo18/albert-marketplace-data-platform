# Slide 10 — L07, orchestration

**Qui parle :** Benjamin · **Durée :** 1 min 15

## Message clé

La pipeline tourne chaque jour, et la relancer ne crée pas de doublons.

## À dire

- DAG Airflow `group6_marketplace_daily` : une période par run, pour que les
  back-fills aient un sens.
- Chaque tâche qui écrit est idempotente grâce à sa clé.
- Preuve : le même back-fill lancé deux fois laisse les mêmes comptes.
- L'alerte e-mail a été reçue (6 novembre 2026) et le quality gate s'est
  déclenché sur une ligne en double ajoutée exprès.
- `catchup` est désactivé : le passé se rattrape par back-fill explicite.
- Runbook des runs en échec, structure du DAG vérifiée en CI.

## Si on nous demande

- Détails et preuves : [orchestration.md](../../../orchestration.md),
  [evidence/l07/](../../../evidence/l07/).
- Décision : [ADR-0007](../../../adr/0007-idempotency.md).
- Runbook : [failed-run.md](../../../runbooks/failed-run.md).
