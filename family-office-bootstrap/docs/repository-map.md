# Repository Map

Questo documento descrive il layout operativo del progetto e i confini tra codice, regole, conoscenza e dati privati. Serve agli agenti per orientarsi prima di scegliere un incremento o modificare file.

## Root del progetto

La root attesa contiene cinque repository/cartelle sibling:

- `family-office-bootstrap/`: metodo operativo, istruzioni agentiche, workflow e playbook.
- `family-office-engine/`: codice Python riusabile, CLI, servizi deterministici, simulatori, reporting, test e documentazione tecnica.
- `family-office-rules/`: rule pack fiscali, previdenziali e compliance versionati, senza dati personali.
- `family-office-knowledge/`: note normative, fonti, glossario e contesto generale, senza dati personali.
- `family-office-workspace/`: caso concreto privato, documenti reali, assunzioni, snapshot e report locali.

## Confini dei dati

- I dati personali e i documenti reali restano solo in `family-office-workspace/`.
- `family-office-engine/`, `family-office-rules/`, `family-office-knowledge/` e `family-office-bootstrap/` non devono contenere dati personali reali.
- I test nei repository software devono usare fixture sintetiche o dati pubblici non personali.
- Gli snapshot generati da CLI e servizi devono essere scritti nel workspace, di norma in `family-office-workspace/snapshots/`.
- I report locali derivati da dati privati devono restare in `family-office-workspace/reports/`.

## Responsabilita' dei repository

### `family-office-bootstrap`

Contiene la governance del lavoro:

- `AGENTS.md`: istruzioni obbligatorie per gli agenti.
- `docs/developer-playbook.md`: procedura di sviluppo.
- `docs/workflow.md`: flussi dati, sviluppo, normativa e AI.
- `docs/next-increment-developer-plan.md`: procedura per scegliere e pianificare il prossimo incremento.
- `docs/repository-map.md`: questo documento.

Non contiene codice applicativo, rule pack o dati personali.

### `family-office-engine`

Contiene il motore deterministico:

- `src/family_office_engine/`: servizi, ingestion, simulazioni, reporting e CLI.
- `tests/`: test unitari e fixture sintetiche.
- `docs/`: API, CLI, testing, roadmap, decision log e current increment.

L'engine legge input dal workspace e rule pack da `family-office-rules/`. Non deve incorporare normative come logica implicita non versionata se esiste o serve un rule pack.

Path chiave:

- `family-office-engine/docs/current-next-increment.md`
- `family-office-engine/docs/decision-log.md`
- `family-office-engine/docs/roadmap/roadmap-index.md`
- `family-office-engine/docs/roadmap/roadmap-v2.md`

### `family-office-rules`

Contiene regole calcolabili e versionate:

- `italy/<anno>/`: rule pack italiani per anno.
- `italy/current/`: regole correnti parametrizzate o eventi fiscali generali.
- `tests/fixtures/`: fixture sintetiche per testare il runtime.

Ogni rule pack deve dichiarare almeno schema, ID, giurisdizione, valuta, periodo di validita', fonti o riferimenti knowledge, limiti e regole testabili.

Le regole non devono inventare dati mancanti e non devono contenere dati personali.

### `family-office-knowledge`

Contiene conoscenza normativa e contesto:

- note fiscali, previdenziali, patrimoniali e documentali;
- fonti ufficiali o riferimenti verificabili;
- limiti interpretativi e avvertenze operative.

Quando cambia una norma, il flusso corretto e':

```text
knowledge -> rules -> tests -> engine
```

### `family-office-workspace`

Contiene il caso privato:

- `documents/`: archivio classificato dei documenti reali.
- `documents/manifest.json`: manifest di provenance dei documenti.
- `inbox/`: deposito temporaneo legacy o di prima acquisizione.
- `assumptions/base-assumptions.json`: assunzioni private.
- `snapshots/`: output JSON normalizzati e derivati.
- `reports/`: report locali generati.

I file in questo repository possono contenere dati personali. Non copiarne contenuti in engine, rules, knowledge, bootstrap, test o documentazione pubblicabile.

## Integrazioni standard

L'engine risolve i repository sibling dalla root del progetto:

- rules: `../family-office-rules`
- knowledge: `../family-office-knowledge`
- workspace: `../family-office-workspace`

Override supportati:

- `FO_RULES_PATH`
- `FO_KNOWLEDGE_PATH`
- `FO_WORKSPACE_PATH`

La CLI puo' verificare il layout con:

```text
python -m family_office_engine.cli.main validate
```

## Path operativi principali

- Assunzioni private: `family-office-workspace/assumptions/base-assumptions.json`
- Manifest documenti: `family-office-workspace/documents/manifest.json`
- Snapshot: `family-office-workspace/snapshots/`
- Report: `family-office-workspace/reports/`
- Rule pack IRPEF 2026: `family-office-rules/italy/2026/irpef-national.json`
- Roadmap index: `family-office-engine/docs/roadmap/roadmap-index.md`
- Incremento corrente: `family-office-engine/docs/current-next-increment.md`
- Decision log: `family-office-engine/docs/decision-log.md`

## Regole operative per gli agenti

- Leggere questo documento all'inizio della sessione, dopo `AGENTS.md`.
- Usare `roadmap-index.md` e `current-next-increment.md` per scegliere il prossimo incremento.
- Salvare il piano in `current-next-increment.md` prima di modificare codice, regole, knowledge o workspace.
- Aggiornare nello stesso incremento codice, test, documentazione, roadmap e decision log quando impattati.
- Non usare LLM per calcoli fiscali, previdenziali o finanziari.
- Non anticipare la roadmap AI per compensare dati, regole o simulatori mancanti.
- Se un incremento e' bloccato da input mancanti o contratto assente, creare il piu' piccolo incremento abilitante nella stessa roadmap.

## Cosa va dove

| Necessita' | Posizione corretta |
|---|---|
| Nuova istruzione agentica | `family-office-bootstrap/AGENTS.md` o `family-office-bootstrap/docs/` |
| Nuova fonte normativa o spiegazione | `family-office-knowledge/` |
| Nuova regola calcolabile | `family-office-rules/` |
| Nuovo servizio, parser, CLI o simulatore | `family-office-engine/src/` |
| Nuovo test sintetico | `family-office-engine/tests/` o fixture sintetica in `family-office-rules/tests/fixtures/` |
| Documento reale personale | `family-office-workspace/documents/` |
| Output generato da dati personali | `family-office-workspace/snapshots/` o `family-office-workspace/reports/` |
