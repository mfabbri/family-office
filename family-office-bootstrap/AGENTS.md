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
- Prima della chiusura eseguire `python planning/validate-execution-guardrails.py`; il gate controlla evidenze, review, blocker e budget deleghe.

## Governance della convergenza

Per lavori sul blocco V4.14 e per review ripetute leggere `docs/playbooks/12-dual-gate-and-convergence.md`. Le revisioni di compatibilità software di regole immutate non richiedono automaticamente una nuova pre-review giuridica. Mantenere separati esito software ed esito giuridico per output. Evitare di ripetere lo stesso gate senza un nuovo artefatto, fonte o finding sostanziale.

## Budget e migrazione modelli v4.0

Il routing attivo per nuovi task e' in `02-model-routing.md` v4.0; lo storico del planner gia' bloccato resta con policy 3.1 senza alterare esiti passati. Prima di aprire nuove review usare il test del diff e degli hash; raccogliere solo conteggi reali Codex `turn.completed.usage` tramite `planning/report-token-usage.py`. Un run che non produce nuova evidenza non autorizza ulteriori suffissi di roadmap.
