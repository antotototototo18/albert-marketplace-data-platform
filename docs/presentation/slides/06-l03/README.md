# Slide 6 — L03, ingestion

**Qui parle :** Anthony · **Durée :** 1 min 15

## Message clé

Trois chemins d'entrée, chacun avec son mode de panne testé.

## À dire

- Connecteur Airbyte depuis PostgreSQL, secrets exclus à la source.
- Extracteur des commandes : curseur durable et retries.
- Consumer Kafka du clickstream, validé par un JSON Schema v1.
- Un événement invalide part dans la DLQ et le flux continue.
- Être honnête : la synchro Airbyte est incomplète. La source a été tuée faute
  de mémoire (Docker n'avait que 7,7 Go), 12 Go sont proposés.

## Si on nous demande

- Modes de panne, dont la mémoire : [ingestion-failure-modes.md](../../../ingestion-failure-modes.md).
- Décision : [ADR-0003](../../../adr/0003-ingestion-modes.md).
- Code : [ingestion/](../../../../ingestion/).
