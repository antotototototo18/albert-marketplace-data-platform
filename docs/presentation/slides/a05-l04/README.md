# Annexe A5 — L04, warehouse

**Hors pitch :** slide de secours, montrée seulement si une question y mène · **Qui répond :** Benjamin

## Message clé

Chaque réglage du warehouse a été mesuré, cache désactivé, et chaque requête
est plafonnée.

## À dire

- Sept tables natives typées dans `group6_warehouse`.
- Partition par mois sur `orders` et `order_items` : un scan d'une journée
  d'`order_items` lit 78× moins d'octets (78,49×).
- Vue matérialisée `daily_demand` pour le besoin ML.
- Tarif à la demande, avec un plafond de 1 GiB par requête, vu en échec.
- On a aussi noté les réglages qui n'ont rien apporté.

## Si on nous demande

- Mesures avant/après : [warehouse-tuning.md](../../../warehouse-tuning.md).
- Pourquoi à la demande : [ADR-0004](../../../adr/0004-warehouse-pricing.md).
- Runbook : [slow-query.md](../../../runbooks/slow-query.md).
- Pas de quota au niveau du projet : voir la slide 14.
