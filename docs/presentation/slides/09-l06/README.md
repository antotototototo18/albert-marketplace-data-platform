# Slide 9 — L06, images

**Qui parle :** Lenny · **Durée :** 1 min

## Message clé

Les jobs sont emballés dans des images que n'importe qui peut récupérer et
relancer.

## À dire

- Deux Dockerfiles : ingestion et dbt.
- Bases fixées, utilisateur non root (UID 10001), aucun secret dans l'image.
- Images poussées dans l'Artifact Registry privé, en `europe-west1`.
- Test de reproduction : l'image d'ingestion a été supprimée puis récupérée, et
  le digest est le même qu'au push.
- Préciser que ce cycle n'a pas été fait pour l'image dbt.
- Benjamin a resserré le contexte Docker et le script de reproduction.

## Si on nous demande

- Digests et transcript : [reproduce.md](../../../reproduce.md),
  [evidence/l06/](../../../evidence/l06/).
- Décision : [ADR-0006](../../../adr/0006-image-tags.md).
