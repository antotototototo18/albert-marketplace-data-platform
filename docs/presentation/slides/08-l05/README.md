# Slide 8 — L05, dbt

**Qui parle :** Antoine · **Durée :** 1 min 15

## Message clé

dbt transforme le bronze en silver et gold, avec des grains déclarés et testés.

## À dire

- Un modèle de staging par source, chacun corrige un défaut nommé.
- En silver : les commandes en double sont retirées et les jointures qui
  dupliquent des lignes (fan-out) sont traitées.
- En gold : un schéma en étoile dont chaque grain est testé.
- Silver en vues, gold en tables.
- Résultat du `dbt build` du 3 novembre 2026 : 93 tests passent, 1 warn
  attendu, 0 erreur.

## Si on nous demande

- Projet : [transform/](../../../../transform/).
- Critères et lignage : [acceptance-criteria.md](../../../acceptance-criteria.md),
  [lineage.md](../../../lineage.md).
- Décision : [ADR-0005](../../../adr/0005-materialisations.md).
