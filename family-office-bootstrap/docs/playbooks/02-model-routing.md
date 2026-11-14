# Model routing

Obiettivo: usare il modello meno costoso compatibile con rischio, fase e contratto del task, senza sacrificare i reviewer specialistici del Family Office AI.

Il routing usa custom agent, non `[profiles.*]` project-local. Il parent `gpt-5.6-luna` / `medium` classifica, delega e sintetizza; non assorbe silenziosamente lavoro medium/review/high/critical.

| Tier | Agent | Model | Reasoning | Uso tipico |
|---|---|---|---:|---|
| low | `fo_explorer` | `gpt-5.6-luna` | low | discovery bounded/read-only |
| low | `fo_docs_reviewer` | `gpt-5.6-luna` | medium | review documentale/contratti |
| low | `fo_docs_editor` | `gpt-5.6-luna` | medium | docs/planner/config agent |
| medium | `fo_planner` | `gpt-5.6-terra` | medium | planning cross-module con architettura già decisa |
| medium | `fo_implementer` | `gpt-5.6-terra` | medium | implementazione T1–T3 entro contratti definiti |
| review | `fo_reviewer` | `gpt-5.6-terra` | high | quality gate, regressioni, privacy/provenance |
| high | `fo_architect` | `gpt-5.6-sol` | high | architettura, migrazioni, trade-off |
| high | `fo_financial_reviewer` | `gpt-5.6-sol` | high | IRR/NPV/DSCR, leverage, cash-flow, scenario assumptions, opportunity cost |
| critical | `fo_normative_reviewer` | `gpt-5.6-sol` | xhigh | fiscalità, pensioni, RW/IVAFE/IVIE, successione, AML/CRS/DAC, compliance |

## Routing rules

1. Creare il task envelope e registrarlo in `planning/current-work.json`.
2. Se il diff **introduce o modifica** una regola, un periodo, una classificazione giuridica o una conclusione normativa T4, usare lo specialista normativo Sol/xhigh per il gate. Se collega **senza modificarli** pack/evidenze già revisionati a un consumer fail-closed, classificare la fase come implementazione tecnica T1–T3 con Terra/medium e reviewer tecnico; escalare al normativo soltanto su un trigger semantico concreto.
3. Se la fase è finanziaria ma non introduce una nuova interpretazione normativa, usare `fo_financial_reviewer` Sol/high per formule, scenari e ranking.
4. Se serve planning cross-module ma architettura e regole sono già decise, usare `fo_planner` Terra/medium.
5. Implementare codice deterministico con `fo_implementer` Terra/medium quando regole e contratti sono definiti.
6. Usare `fo_reviewer` Terra/high per review indipendente T3 o quality/audit.
7. Usare `fo_architect` Sol/high per architettura/migrazione, non per semplici modifiche di codice.
8. Per T4, dopo implementazione Terra, tornare al reviewer specialistico appropriato quando il playbook richiede un gate indipendente.
9. Registrare `delegated`, `escalated` o `fallback` nella trace prima di cambiare route.
10. Non sostituire silenziosamente un modello non disponibile.

Dopo un NO-GO, applicare soltanto correzioni bounded già autorizzate. Una nuova autorizzazione dell'utente apre un ciclo distinto e deve nominare versione, scope, blocker, budget massimo di eventi e condizione di stop; non è un'approvazione generale per retry o modifiche ulteriori. L'autorizzazione a una sequenza di più incrementi definisce l'ordine da tentare, ma non supera i gate: dopo ogni incremento verificare nuovamente predecessori e roadmap; un NO-GO o una review pending blocca i discendenti. Il budget di review/correzione è specifico per incremento e ciclo, non si trasferisce agli incrementi successivi. La trace corrente deve contenere solo il ciclo attivo. Finding ed esiti dei cicli precedenti restano invece conservati nel verification/decision log e non si sovrascrivono.

## Regole di risparmio token

1. Ridurre prima contesto e reasoning, poi cambiare modello.
2. Luna deve restituire sintesi, non dump di file o log.
3. Un subagent deve sostituire una lettura/esplorazione costosa del parent, non duplicarla.
4. Preferire un singolo reviewer specializzato a più reviewer generici.
5. Non usare Sol per typo, listing, boilerplate, test già localizzati o documentazione meccanica.
6. Non aumentare reasoning per compensare requisiti ambigui: chiarire il contratto o leggere l'evidenza mancante.
7. `xhigh` è riservato al reviewer normativo critico; la matematica finanziaria ordinaria resta Sol/high e deterministica nei servizi/test.

## Trigger per Sol/xhigh

Usare `fo_normative_reviewer` / xhigh solo se almeno uno è vero:

- interpretazione normativa con più letture plausibili e impatto materiale;
- validità temporale/transitoria della norma non ovvia;
- fiscalità, pensioni, monitoraggio fiscale o successione cambiano materialmente il risultato;
- obblighi AML/CRS/DAC o altre regole di compliance richiedono una decisione interpretativa.

Per nuove formule finanziarie o cambi di semantica IRR/NPV/DSCR usare prima `fo_financial_reviewer` Sol/high; escalare al reviewer normativo solo se il problema è anche legale/fiscale.

## Compatibility e fallback

Usare solo identificatori completi:

- `gpt-5.6-luna`
- `gpt-5.6-terra`
- `gpt-5.6-sol`

L'alias non suffissato `gpt-5.6` non deve apparire come valore `model` nella configurazione eseguibile.

Se il client/account non espone il modello richiesto, registrare un evento `fallback` nel planner e usare un modello disponibile senza cambiare i contratti del task. Il fallback non deve essere silenzioso.

## Modelli e semplicità (audit OpenAI 2026)

Non introdurre nuovi nomi modello in `.codex/config.toml` finché non sono stati verificati disponibilità e schema del client Codex installato; il validator locale fissa attualmente la matrice v3.1 ai nomi gpt-5.6. Il criterio OpenAI 2026 è minimizzare istruzioni ridondanti e deleghe non necessarie; non forzare un subagent per un edit locale sicuro. Un aggiornamento a GPT-6/Astra richiede **migrazione separata**, con aggiornamento atomico di config, agent TOML, validator, skill e smoke della CLI.

Una review tecnica di binding con Rules identiche non va promossa a una seconda review normativa solo per la parola "pension" nel nome del file. La matrice di impatto è in `12-dual-gate-and-convergence.md`.
