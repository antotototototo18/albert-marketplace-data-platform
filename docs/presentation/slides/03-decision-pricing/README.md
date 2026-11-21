# Slide 3 — Décision 1 : payer à la requête, plafonner à 1 GiB

**Qui parle :** Benjamin · **Durée :** 2 min

## Message clé

On reste à la demande parce que notre charge est 7 600 fois sous le seuil où
les slots deviennent rentables. Le vrai risque est la requête imprudente : on
le traite avec un plafond, pas en changeant de modèle de prix.

## À dire

Le texte exact, en anglais, est dans [SCRIPT.md](../../SCRIPT.md), section
« Slide 3 — Decision 1: how we pay for BigQuery ». Il est aussi dans les notes de la slide.

## Si on nous demande

- Tout le calcul : [ADR-0004](../../../adr/0004-warehouse-pricing.md).
- Le seuil : (T − 1) × 7,50 $ = 50 slots × 730 h × 0,0528 $ = 1 927,20 $,
  donc T ≈ 258 Tio par mois.
- La charge (environ 0,034 Tio par mois) est **estimée**. Un membre a mesuré
  0,0012 Tio en 30 jours. Le dire si on nous pose la question.
- Les prix des slots viennent d'une source secondaire de 2024 : à revérifier
  avant tout achat. L'ADR le dit.
- Les mesures de partitionnement (78× sur un jour d'`order_items`) : slide A5
  et [warehouse-tuning.md](../../../warehouse-tuning.md).
