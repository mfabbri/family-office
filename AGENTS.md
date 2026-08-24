# Family Office AI — Agent Map

Questo file deve restare breve. È una mappa, non un manuale completo.

## Regole invarianti

- Non copiare dati personali fuori da `family-office-workspace/`.
- Non usare LLM per calcoli fiscali, previdenziali o finanziari: usare servizi deterministici, rule pack e test.
- Per cambi normativi seguire: `knowledge → rules → tests → engine`.
- Fare la modifica minima verificabile; evitare refactor non richiesti.
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

## Work Transition e pension bridge

Per task su data di uscita dal full-time, part-time, cessazione, RITA, ponte patrimoniale o decorrenze pensionistiche leggere anche `family-office-bootstrap/docs/playbooks/11-work-transition-retirement-bridge.md`. Questi task sono almeno T4 e devono mantenere separate data di riduzione lavoro, cessazione, maturazione del diritto e decorrenza di ciascuna pensione.

Quando `roadmap-v4b-work-transition.md` e' attiva, non proseguire con incrementi AI V5.3+ finche' il gate V4B -> V5 non e' completato. V5.1 e V5.2 restano validi e non vanno annullati.

## Playbook

Indice: `family-office-bootstrap/docs/playbooks/README.md`.

## Repository locali

- `family-office-engine/AGENTS.md`
- `family-office-rules/AGENTS.md`
- `family-office-knowledge/AGENTS.md`

Le istruzioni più vicine al file modificato prevalgono per il relativo ambito.
