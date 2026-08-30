---
name: family-office-session
description: Avvia e chiude una sessione Family Office AI con contesto minimo, task envelope, roadmap audit e guardrail deterministici.
---

# Family Office AI session

## Input minimo

Leggi:

1. `AGENTS.md`;
2. `family-office-bootstrap/planning/current-work.json`;
3. `family-office-engine/docs/current-next-increment.md`;
4. solo la roadmap attiva e i contratti direttamente necessari.

Prima di selezionare/implementare un incremento funzionale esegui `roadmap_audit.py`.

## Task envelope

Prima di modificare file registra nel planner:

```yaml
mode: discovery-lite | docs-edit | scoped-fix | feature-slice | quality-slice | normative-change | architecture-review
risk_domain: general | privacy | tax | pension | financial | compliance
objective: una frase verificabile
repositories: []
read_set: []
write_set: []
test_command: ""
stop_conditions: []
```

Usa progressive disclosure e i limiti di `docs/playbooks/01-context-budget.md`.

## Routing

Dopo il task envelope usa `$family-office-model-router`. Il parent Luna/medium e'
un router/controller e delega task medium/review/high/critical al custom agent previsto.

## Chiusura

Aggiorna planner, test/result e `next_action`. Aggiorna roadmap/current-next/decision log
solo se la modifica li impatta semanticamente. Non anticipare un nuovo incremento solo
per riempire il planner.
