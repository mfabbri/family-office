# Agent Playbooks

Questi playbook riducono consumo di token e deriva operativa tramite caricamento progressivo del contesto, planner persistente, routing dinamico per rischio e uso selettivo dei custom agent.

## Ordine d'uso

1. `00-task-router.md`
2. `01-context-budget.md`
3. `02-model-routing.md`
4. `03-subagent-policy.md`
5. un solo playbook specifico del task
6. `08-testing-and-review.md`

## Playbook disponibili

- `00-task-router.md` — classificazione T0–T5 e selezione del flusso.
- `01-context-budget.md` — limiti iniziali a listing, ricerche, letture e output.
- `02-model-routing.md` — scelta di custom agent, modello e reasoning effort.
- `03-subagent-policy.md` — quando e come delegare.
- `04-micro-increment.md` — implementazione roadmap.
- `05-bug-fix.md` — correzioni circoscritte.
- `06-cross-repository-change.md` — modifiche con più repository o contratti.
- `07-normative-change.md` — aggiornamenti fiscali, previdenziali o compliance.
- `08-testing-and-review.md` — verifica proporzionata al rischio.
- `09-roadmap-maintenance.md` — aggiornamento minimo dello stato.
- `10-code-audit.md` — audit periodico o richiesto.
- `11-investment-opportunity.md` — asset produttivi, immobili, camper/veicoli, leverage, cash flow e opportunity cost.
- `11-work-transition-retirement-bridge.md` — transizione full-time/part-time/cessazione e ponte verso pensione.

Planner: `../../planning/README.md`.
Prompt sessione: `../agent-session-prompt.md`.

## Principio fondamentale

Non leggere un documento perché esiste. Leggerlo solo perché il router, il planner o un'evidenza concreta lo rende necessario. Non aumentare reasoning o numero di agenti finché non è stato ridotto il contesto al minimo necessario.
