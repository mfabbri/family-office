# Bootstrap Agent Instructions

Leggere prima `../AGENTS.md` e poi il router:

- `docs/playbooks/00-task-router.md`
- `planning/current-work.json`

Il bootstrap governa metodo, playbook, planner e orchestrazione. Non contiene dati personali, logica fiscale eseguibile o codice applicativo.

## Regole locali

- Non caricare tutti i documenti di governance all'avvio.
- Usare progressive disclosure e il budget in `docs/playbooks/01-context-budget.md`.
- Usare il routing reale indicato da `docs/playbooks/02-model-routing.md` e dalla skill `$family-office-model-router`.
- Registrare il routing intenzionale in `planning/current-work.json` prima della delega.
- Usare subagent secondo `docs/playbooks/03-subagent-policy.md`.
- Per il prossimo incremento usare `docs/playbooks/04-micro-increment.md`.
- Per transizioni full-time/part-time/cessazione/pensione usare anche `docs/playbooks/11-work-transition-retirement-bridge.md`.
- Aggiornare un documento di governance solo se la modifica ne cambia davvero il contenuto operativo.
- Il log `planning/.runtime/model-routing.ndjson` è telemetria locale: non versionarlo.
