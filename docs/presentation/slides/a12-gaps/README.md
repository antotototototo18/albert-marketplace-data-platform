# Annexe A12 — Lacunes ouvertes

**Hors pitch :** slide de secours, montrée seulement si une question y mène · **Qui répond :** le responsable de la ligne

## Message clé

Ce qui n'a pas marché est écrit, avec sa cause. Une lacune documentée est un
constat, pas un échec caché.

## À dire, ligne par ligne

Toutes ces lignes ont été vérifiées le 20 novembre 2026 dans les fichiers
indiqués.

| Ligne | Qui | Ce qu'il faut dire | Source |
|---|---|---|---|
| L03 — Airbyte | Anthony | Synchro incomplète : la source a été tuée faute de mémoire (Docker n'avait que 7,7 Go) pendant les synchros 1 et 2 du 16 octobre. 12 Go proposés. | [ingestion-failure-modes.md](../../../ingestion-failure-modes.md) |
| L04 — Quota | Benjamin | Le plafond de 1 GiB par requête existe. Ce qui manque, c'est le quota journalier du projet : il est partagé avec les autres groupes et nos comptes n'ont pas ce droit. | [warehouse-tuning.md](../../../warehouse-tuning.md), [ADR-0004](../../../adr/0004-warehouse-pricing.md) |
| L08 — Compte de service | Lenny | Aucun compte de service adopté : sa création et ses permissions demandent des droits d'admin. | [infra.md](../../../infra.md) |
| L09 — Budget | Anthony | Pas d'alerte budget : l'API des budgets est désactivée et l'activation a été refusée (`PERMISSION_DENIED`). Le budget Terraform reste désactivé. | [costs.md](../../../costs.md) |
| CI | Anthony | Depuis le 10 novembre, GitHub ne démarre pas les jobs à cause d'un blocage de facturation. Le dernier run sur `main` (16 novembre) le montre encore. On joint les vérifications locales aux PR. | [ci-cd.md](../../../ci-cd.md) |
| L10 — Policy tags | Benjamin | Les tags sont posés mais ne refusent personne : le rôle étudiant donne `categoryFineGrainedReader` à tout le projet. Le compte qui a posé les tags lit toujours les 200 001 adresses et téléphones (test du 17 novembre). | [governance.md](../../../governance.md), lacune 1 ; [preuve](../../../evidence/l10/07-not-refused-student-key.txt) |

## À vérifier avant l'oral

Relire cette slide la veille : si une lacune a été corrigée, la retirer ou la
mettre à jour, et changer le document source en même temps.
