# Family Office AI — Agent Map

Questo file deve restare breve. È una mappa, non un manuale completo.

## Regole invarianti

- Non copiare dati personali fuori da `family-office-workspace/`.
- Non usare LLM per calcoli fiscali, previdenziali o finanziari: usare servizi deterministici, rule pack e test.
- Per cambi normativi seguire: `knowledge → rules → tests → engine`.
- Fare la modifica minima verificabile; evitare refactor non richiesti.
- Non rendere la modifica manuale di JSON il percorso operativo normale: per ogni capability utente preferire CLI con wizard, import, generatori o `prepare`; un JSON diretto e' ammesso solo quando strettamente necessario e con motivazione, guida e validazione locale.
- Progettare la UX utente a partire da una domanda o decisione familiare, non dalla sequenza di comandi o dagli snapshot: mostrare fatti disponibili, assunzioni, `data_gaps`, limiti e prossima azione; lasciare JSON e comandi tecnici come infrastruttura.
- Aggiornare test e documentazione solo quando realmente impattati.
- Non dichiarare completato un incremento senza verifiche riproducibili.

## Avvio a contesto ridotto

1. Leggere `family-office-bootstrap/docs/playbooks/00-task-router.md`.
2. Classificare il task da T0 a T5.
3. Leggere solo i file richiesti dal relativo playbook.
4. Per lavoro di roadmap leggere inizialmente soltanto:
   - `family-office-engine/docs/roadmap/roadmap-index.md`;
   - `family-office-engine/docs/current-next-increment.md`;
   - la sola roadmap attiva.
5. Prima di selezionare o implementare il prossimo incremento eseguire
   `python family-office-engine/src/family_office_engine/governance/roadmap_audit.py`;
   un errore blocca gli incrementi funzionali finche' la cadenza audit non e' ripristinata.
6. Consultare decision log, long-term roadmap o altre roadmap solo in presenza di una dipendenza concreta.

## Playbook

Indice: `family-office-bootstrap/docs/playbooks/README.md`.

Per investimenti in asset produttivi (immobili a reddito, camper/veicoli noleggiabili, financing, leverage, cash flow, opportunity cost) usare `family-office-bootstrap/docs/playbooks/11-investment-opportunity.md` e trattare il task come T4 quando cambia semantica finanziaria o fiscale.

## Repository locali

- `family-office-engine/AGENTS.md`
- `family-office-rules/AGENTS.md`
- `family-office-knowledge/AGENTS.md`

Le istruzioni più vicine al file modificato prevalgono per il relativo ambito.
