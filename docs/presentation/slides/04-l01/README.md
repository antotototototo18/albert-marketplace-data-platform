# Slide 4 — L01, architecture cible

**Qui parle :** Anthony · **Durée :** 1 min

## Message clé

On a choisi un modèle à deux étages après avoir comparé quatre options.

## À dire

- On a d'abord cartographié les flux de données et posé trois questions
  ouvertes (avec Antoine sur les flux sources).
- Quatre options comparées : warehouse, lake, two-tier, lakehouse.
- Two-tier retenu : GCS pour le bronze, BigQuery pour silver et gold.
- Esquisse d'un schéma en étoile pour la demande quotidienne, le besoin ML.
- Mise en place du dépôt, des règles de contribution et des contrôles CI.

## Si on nous demande

- Décision et options : [ADR-0001](../../../adr/0001-target-architecture.md).
- Flux : [data-flows.md](../../../data-flows.md).
- Modèle : [star-daily-demand.md](../../../model/star-daily-demand.md).
