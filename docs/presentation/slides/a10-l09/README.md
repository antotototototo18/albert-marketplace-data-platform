# Annexe A10 — L09, FinOps

**Hors pitch :** slide de secours, montrée seulement si une question y mène · **Qui répond :** Anthony

## Message clé

On sait attribuer chaque coût, et une optimisation a été mesurée en octets.

## À dire

- Quatre labels : `team`, `environment`, `pipeline`, `component`.
- Posés sur les cinq ressources qui acceptent des labels ; le plan Terraform
  reste nul ensuite.
- Registre de 55 ressources.
- La sonde mensuelle lit 98,79 % d'octets en moins, avec les mêmes résultats.
- Être précis : le minimum facturé par requête ne change pas, donc il n'y a
  pas encore d'économie en euros mesurable.
- Le budget n'existe pas : l'API des budgets est désactivée et son activation
  nous a été refusée.

## Si on nous demande

- Attribution, optimisation et blocage du budget : [costs.md](../../../costs.md).
- Décision : [ADR-0009](../../../adr/0009-cost-attribution.md).
- Preuve du refus : [budget-access.json](../../../evidence/l09/budget-access.json).
