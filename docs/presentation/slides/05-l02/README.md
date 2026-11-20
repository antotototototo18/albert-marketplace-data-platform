# Slide 5 — L02, bronze

**Qui parle :** Antoine · **Durée :** 1 min

## Message clé

L'export legacy est dans le bronze, sans secrets, dans un format choisi par la
mesure.

## À dire

- 27 tables legacy écrites en Parquet dans `gs://data-engineering-i1-group6`,
  62 Mo au total.
- Mots de passe et numéros de carte exclus avant l'écriture.
- On a mesuré les layouts avant de choisir : zstd compresse 2,58×, snappy
  seulement 1,42×.
- Dictionnaire de données v1, avec un niveau de donnée personnelle par colonne.
- Lifecycle et IAM lus sur le vrai bucket, pas supposés.

## Si on nous demande

- Décision et mesures : [ADR-0002](../../../adr/0002-bronze-layout.md),
  [mesures](../../../evidence/l02-layout-measurements.json).
- Colonnes et données personnelles : [data-dictionary.md](../../../data-dictionary.md).
