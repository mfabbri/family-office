# V5 Roadmap — AI Orchestration

## Obiettivo

Consentire domande in linguaggio naturale e risposte sofisticate usando retrieval, pianificazione e tool deterministici. L'LLM orchestra e spiega; non calcola imposte, pensioni, rendimenti o saldi.

## Prerequisiti

- Gate V4 completato.
- Tool deterministici con input/output versionati.
- Knowledge con fonti e validità temporale.
- Golden scenarios per le decisioni principali.

## Principio architetturale

```text
Domanda → classificazione → piano strumenti → esecuzione deterministica
        → verifica evidenze → composizione risposta con citazioni e limiti
```

L'output dell'LLM non diventa automaticamente un fatto del workspace.

## Incrementi

### V5.1 — Tool registry and invocation contract

**Stato:** `done`
**Tipo:** `functional`

Registrare tool disponibili, schema input/output, prerequisiti, livello di rischio e policy di autorizzazione.

- Repository: `engine`.
- Output: `tool-registry/v1` e adapter locale.
- Test: schema validation, tool inesistente, versione incompatibile.
- Done quando: ogni capacità decisionale può essere invocata senza accesso diretto alle funzioni interne.

Esito: completato con contratto `tool-registry/v1`, servizio deterministico `family_office_engine.services.tool_registry`, adapter locale `invoke_registered_tool`, CLI `orchestration tool-registry build/list`, documentazione API/CLI/testing e test. Il registry espone 15 tool decisionali con schema input/output, parametri richiesti/opzionali, prerequisiti, rischio, policy di autorizzazione e note di perimetro; l'adapter rifiuta tool non registrati, versioni output incompatibili, parametri mancanti o sconosciuti. Non abilita discovery dinamica delle funzioni interne e non usa LLM per calcoli fiscali, previdenziali o finanziari. Verifiche: 7 test mirati OK, smoke CLI build/list OK (`complete 15 tools`), regression unit engine 464 test OK, `roadmap_audit.py` OK.

### V5.2 — Knowledge corpus and citation index

**Stato:** `done`
**Tipo:** `functional`

Indicizzare knowledge, contratti e fonti normative con giurisdizione, data di validità, tema e livello di autorità.

- Dipende da: V5.1.
- Repository: `knowledge`, `engine`.
- Output: indice locale riproducibile e citation contract.
- Test: retrieval temporale, fonte abrogata, citazione mancante, deduplica.
- Done quando: ogni affermazione normativa può rinviare a una fonte identificabile.

Readiness: non richiede dati personali. Il corpus pubblico esistente e' sufficiente come base iniziale, ma i metadati non sono ancora uniformi tra le note. V5.2 deve normalizzare il template e produrre gap espliciti per giurisdizione, validita', autorita' o riferimento mancanti, senza escludere silenziosamente la fonte o dedurne l'autorevolezza. I gap V1 restano non bloccanti salvo perimetri dichiarati esaustivi.

Esito: completato con catalogo `knowledge-citation-catalog/v1`, servizio deterministico `citation-index/v1`/`citation-search/v1`, hash dei documenti, deduplica, inventario contratti dal registry, filtro temporale e CLI `orchestration citations build/search`. Il corpus iniziale contiene 11 citazioni, 13 documenti e 28 contratti; 7 gap restano espliciti e non bloccanti, inclusi i documenti senza citation ID e la fonte RITA senza validita'/verifica documentate. `knowledge.citations.search` e' un tool registrato read-only. Verifiche: 13 test mirati/integration OK, smoke CLI build/search OK, regression unit engine 471 test OK, `roadmap_audit.py` OK (`functional_since_audit=2`, `audit_due=false`).

### V5.3 — Supported-question taxonomy

**Stato:** `planned`
**Tipo:** `functional`

Definire famiglie di domande, tool richiesti, dati minimi, output attesi e casi da rifiutare o rinviare a un professionista.

- Dipende da: V5.1 e V5.2.
- Repository: `bootstrap`, `engine`.
- Output: catalogo versionato di intenti e capability matrix.
- Test: copertura, intenti sovrapposti e domanda fuori perimetro.
- Done quando: il sistema sa dichiarare cosa può e non può risolvere.

### V5.4 — Intent router

**Stato:** `planned`
**Tipo:** `functional`

Classificare la domanda in uno o più intenti, estrarre entità e indicare dati mancanti senza eseguire calcoli.

- Dipende da: V5.3.
- Repository: `engine`.
- Output: `question-intent/v1`.
- Test: dataset sintetico, ambiguità, prompt injection e richiesta non supportata.
- Done quando: il routing ha confidence e fallback deterministici.

### V5.4a — Periodic code and contract audit

**Stato:** `planned`
**Tipo:** `audit`

Verificare il primo blocco funzionale V5 prima di introdurre il query planner.

- Dipende da: V5.2, V5.3 e V5.4.
- Repository: `bootstrap`, `knowledge`, `engine`.
- Checklist: `family-office-bootstrap/docs/code-audit-checklist.md`.
- Test: regression pertinente, privacy, allineamento contratti/CLI/docs e `roadmap_audit.py`.
- Done quando: citation index, tassonomia e router risultano coerenti e non restano blocker impliciti per V5.5.

### V5.5 — Query planner

**Stato:** `planned`
**Tipo:** `functional`

Trasformare gli intenti in un DAG di tool con dipendenze, input, controlli e criteri di arresto.

- Dipende da: V5.4a.
- Repository: `engine`.
- Output: `execution-plan/v1`.
- Test: piano valido, ciclo, tool mancante, dato sensibile non autorizzato.
- Done quando: il piano è ispezionabile prima dell'esecuzione.

### V5.6 — Natural-language scenario builder

**Stato:** `planned`
**Tipo:** `functional`

Convertire richieste come “pensione a 62 anni con università dei figli” in draft di scenario strutturato, mai direttamente in risultato.

- Dipende da: V5.5 e scenario contract V2.
- Repository: `engine`, `workspace`.
- Output: scenario draft con facts proposti, assunzioni e richieste di conferma.
- Test: date, importi, conflitti, omissioni e valori non supportati.
- Done quando: nessuna assunzione implicita viene eseguita senza essere resa visibile.

### V5.7 — Deterministic executor and evidence bundle

**Stato:** `planned`
**Tipo:** `functional`

Eseguire il piano, raccogliere output, log, hash, fonti, errori e data gaps in un bundle unico.

- Dipende da: V5.5.
- Repository: `engine`, `workspace`.
- Output: `evidence-bundle/v1`.
- Test: esecuzione parziale, retry sicuro, timeout, versioni e riproducibilità.
- Done quando: la risposta può essere rigenerata dagli stessi input.

### V5.8 — Response composer with citations

**Stato:** `planned`
**Tipo:** `functional`

Comporre executive summary, alternative, motivazioni, numeri, fonti, assunzioni, rischi e azioni usando solo l'evidence bundle.

- Dipende da: V5.2 e V5.7.
- Repository: `engine`.
- Output: `advisory-response/v1`.
- Test: citazioni obbligatorie, numero non supportato, conflitto fra fonti e risposta parziale.
- Vincolo evidenze: una citazione collegata al documento knowledge non supporta automaticamente ogni frase; il composer deve collegare ciascuna affermazione alla specifica evidenza pertinente oppure dichiararla non supportata.
- Done quando: ogni numero e conclusione è collegato a un elemento del bundle.

### V5.9 — Guardrails, confidence and escalation

**Stato:** `planned`
**Tipo:** `functional`

Bloccare richieste di evasione/opacità, risultati con dati insufficienti, azioni ad alto rischio o conclusioni normative non aggiornate.

- Dipende da: V5.8.
- Repository: `bootstrap`, `knowledge`, `rules`, `engine`.
- Output: policy engine e `answer-confidence/v1`.
- Test: AML/CRS bypass, anonimato assoluto, tax rule scaduta, gap critico.
- Done quando: il sistema distingue risposta informativa, simulazione e raccomandazione da validare.

### V5.10 — Decision memory and comparison history

**Stato:** `planned`
**Tipo:** `functional`

Memorizzare decisioni, scenari confrontati, assunzioni approvate e motivi, senza trasformare conversazioni non validate in facts.

- Dipende da: V5.7–V5.9.
- Repository: `engine`, `workspace`.
- Output: `decision-memory/v1` con versioni e supersession.
- Test: aggiornamento, revoca, conflitto e separazione dati personali.
- Done quando: una decisione futura può mostrare cosa è cambiato rispetto alla precedente.

### V5.11 — AI evaluation suite

**Stato:** `planned`
**Tipo:** `functional`

Creare benchmark per routing, planning, tool use, citazioni, hallucination, privacy, fiscal safety e qualità delle spiegazioni.

- Dipende da: V5.4–V5.10.
- Repository: `engine`, `bootstrap`.
- Output: dataset sintetico, metriche e soglie di release.
- Test: esecuzione locale ripetibile e report regressioni.
- Done quando: un cambio di modello o prompt non può essere rilasciato senza misure comparative.

### V5.12 — Local API and conversational interface

**Stato:** `planned`
**Tipo:** `functional`

Esporre il flusso come API locale e interfaccia conversazionale con sessione, preview del piano e approvazioni.

- Dipende da: V5.11.
- Repository: `engine`.
- Output: API versionata e client minimo.
- Test: autenticazione locale, autorizzazioni, concorrenza, cancel e audit.
- Done quando: l'interfaccia non bypassa planner, executor o guardrail.

## Exit criteria V5

- Nessun calcolo numerico critico è prodotto dall'LLM.
- Le risposte derivano da evidence bundle riproducibili.
- Citazioni, confidence, gaps ed escalation sono obbligatori.
- Prompt e modelli sono valutati con benchmark prima del rilascio.
- La memoria distingue fatti validati, assunzioni e conversazione.
