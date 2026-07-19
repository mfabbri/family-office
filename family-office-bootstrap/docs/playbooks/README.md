# Agent Playbooks

Questi playbook riducono consumo di token e deriva operativa tramite caricamento progressivo del contesto, routing per complessità e uso selettivo dei subagent.

## Ordine d'uso

1. `00-task-router.md`
2. `01-context-budget.md`
3. `02-model-routing.md`
4. playbook specifico del task
5. `08-testing-and-review.md`

## Playbook disponibili

- `00-task-router.md` — classificazione T0–T5 e selezione del flusso.
- `01-context-budget.md` — limiti iniziali a listing, ricerche, letture e output.
- `02-model-routing.md` — scelta di modello e reasoning effort.
- `03-subagent-policy.md` — quando delegare e quando restare single-agent.
- `04-micro-increment.md` — implementazione roadmap.
- `05-bug-fix.md` — correzioni circoscritte.
- `06-cross-repository-change.md` — modifiche con più repository o contratti.
- `07-normative-change.md` — aggiornamenti fiscali, previdenziali o compliance.
- `08-testing-and-review.md` — verifica proporzionata al rischio.
- `09-roadmap-maintenance.md` — aggiornamento minimo dello stato.
- `10-code-audit.md` — audit periodico o richiesto.

## Principio fondamentale

Non leggere un documento perché esiste. Leggerlo solo perché il router o un'evidenza concreta lo rende necessario.
