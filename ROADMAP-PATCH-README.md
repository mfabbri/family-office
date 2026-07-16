# Roadmap Patch

Questo pacchetto aggiunge le roadmap V3–V6, le collega al flusso agentico esistente e include la pipeline esplicita per il calcolo della pensione spagnola.

## Applicazione

Estrarre il contenuto nella root che contiene le cartelle:

- `family-office-bootstrap`
- `family-office-engine`

Consentire la sovrascrittura dei file esistenti.

## File principali

- `family-office-engine/docs/roadmap/roadmap-index.md`
- `family-office-engine/docs/roadmap/roadmap-v3-decision-core.md`
- `family-office-engine/docs/roadmap/roadmap-v4-wealth-planning.md`
- `family-office-engine/docs/roadmap/roadmap-v5-ai-orchestration.md`
- `family-office-engine/docs/roadmap/roadmap-v6-operations-compliance.md`

Sono aggiornati anche AGENTS, developer plan, workflow, V2, long-term roadmap, decision log e README.

Il primo incremento che il flusso selezionerà, dato lo stato corrente, è `V2.5 — Cashflow from payroll V1`.

## Aggiornamento pensione spagnola

La roadmap V3 include ora micro-incrementi autonomi per:

1. import di Vida Laboral, Informe de bases de cotización e nóminas;
2. riconciliazione di periodi e basi;
3. stima normativa della pensione pubblica spagnola;
4. coordinamento previdenziale UE Italia–Spagna;
5. composizione con INPS, Fon.Te e RITA.

La roadmap V4 separa il calcolo previdenziale lordo dalla tassazione Italia–Spagna, dal netto per residente italiano e dagli obblighi RW/IVAFE/IVIE.
