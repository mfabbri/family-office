# Bootstrap Agent Instructions

Leggere prima `../AGENTS.md` e poi il router:

- `docs/playbooks/00-task-router.md`

Il bootstrap governa metodo, playbook e orchestrazione. Non contiene dati personali, logica fiscale eseguibile o codice applicativo.

## Regole locali

- Non caricare tutti i documenti di governance all'avvio.
- Usare progressive disclosure e il budget in `docs/playbooks/01-context-budget.md`.
- Usare il tier di modello indicato da `docs/playbooks/02-model-routing.md`.
- Usare subagent solo secondo `docs/playbooks/03-subagent-policy.md`.
- Per il prossimo incremento usare `docs/playbooks/04-micro-increment.md`.
- Per transizioni full-time/part-time/cessazione/pensione usare anche `docs/playbooks/11-work-transition-retirement-bridge.md`.
- Aggiornare un documento di governance solo se la modifica ne cambia davvero il contenuto operativo.
