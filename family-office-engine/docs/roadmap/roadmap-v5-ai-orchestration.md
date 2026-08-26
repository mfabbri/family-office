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

**Stato:** `done`
**Tipo:** `functional`

Definire famiglie di domande, tool richiesti, dati minimi, output attesi e casi da rifiutare o rinviare a un professionista.

- Dipende da: V5.1 e V5.2.
- Repository: `bootstrap`, `engine`.
- Output: catalogo versionato di intenti e capability matrix.
- Test: copertura, intenti sovrapposti e domanda fuori perimetro.
- Done quando: il sistema sa dichiarare cosa può e non può risolvere.

Esito: completato con `supported-question-catalog/v1` e `question-capability-assessment/v1`. Il catalogo copre tutti i tool registrati con dati minimi, output, rischio ed escalation; non instrada testo libero e non invoca tool. Le domande su asset produttivi sono `planned` e non eseguibili fino al blocco V5.3a-V5.3h. Selezioni sovrapposte, sconosciute, incomplete o riservate a un professionista producono problemi espliciti. Verifiche: 4 test V5.3, 6 registry, 6 citation-index, regression unit engine 515 test e `roadmap_audit.py` OK.

## Deterministic investment-opportunity enabling block

Dopo V5.3 e prima dell'intent router V5.4, V5 introduce un blocco deterministico per asset produttivi. Questo preserva la regola di non anticipazione dell'AI: appartamenti a reddito, camper/veicoli noleggiabili e futuri asset analoghi devono essere valutabili da contratti, servizi e rule pack prima di diventare intenti eseguibili dal router conversazionale.

La tassonomia V5.3 puo' gia' classificare queste domande come capability pianificata/non ancora eseguibile; gli incrementi seguenti rendono la capability realmente disponibile prima che V5.4 inizi a instradarla verso tool concreti.

### V5.3a — Generic investment opportunity core

**Stato:** `done`
**Tipo:** `functional`

Definire un contratto generico `investment-opportunity/v1` e un servizio deterministico per acquisition basis, operating cash flow, residual value, owner time, personal-use benefit separato, scenari e metriche comuni.

- Dipende da: V4.2, V4.5, V4.10, V5.1 e V5.3.
- Repository: `engine`, `bootstrap`.
- Riusa: planning goals, liquidity plan, tax-aware portfolio, wealth strategy, provenance/data-gap conventions.
- Output: `investment-opportunity/v1`.
- Metriche candidate: NOI, free cash flow, cash-on-cash, payback, NPV, IRR, equity multiple; cap rate/DSCR solo quando semanticamente applicabili.
- Vincoli: nessun rendimento di mercato, occupancy, tariffa, rivalutazione o residual value inventato; ogni assumption e' input/versionata.
- Test: zero/negative cash flow, missing assumptions, residual value, owner-time cost, personal-use separation, deterministic hash/provenance.
- Done quando: due adapter diversi possono usare lo stesso core senza duplicare formule o mescolare benefici personali con redditi imponibili.

Esito: completato con contratto e servizio deterministico `investment-opportunity/v1`, schema input/output, fixture sintetiche per immobile a reddito e asset mobile noleggiabile e CLI `fo planning investment-opportunity build|demo`. Il core calcola soltanto importi espliciti: acquisition basis, ricavi/costi, NOI, free cash flow annuo, valore residuo/costi di uscita e costo del tempo del proprietario. Il beneficio economico dell'uso personale resta fuori da NOI e cash flow; fiscalita', classificazione dell'attivita', finanziamento, rendimenti, utilizzo e valori residui non dichiarati restano input o data gap. Verifiche: 8 test mirati OK, regression unit engine 516 test OK, smoke `fo planning investment-opportunity demo` OK e `roadmap_audit.py` OK.

### V5.3b — Periodic code and contract audit

**Stato:** `done`
**Tipo:** `audit`

Eseguire l'audit immediatamente dopo V5.3a. V5.1 e V5.2 sono gia' completati; completando V5.3 e V5.3a si raggiunge la soglia di quattro incrementi funzionali dall'ultimo audit prevista da `roadmap_audit.py`.

- Dipende da: V5.3 e V5.3a.
- Repository: `bootstrap`, `knowledge`, `engine` e `rules` se toccati.
- Checklist: `family-office-bootstrap/docs/code-audit-checklist.md`.
- Focus: taxonomy/capability matrix, formule comuni, contratti, personal-use separation, provenance, data gaps e regression.
- Done quando: non restano blocker impliciti prima degli adapter asset-specific.

Esito: audit completato sui confini V5.1-V5.3a. Registry, citation index, taxonomy e core mantengono responsabilita' separate: il registry invoca soltanto tool espliciti, l'indice conserva fonti/gap senza interpretare norme, la taxonomy non instrada testo libero ne' espone capability pianificate, e il core calcola sola aritmetica da input dichiarati separando il beneficio d'uso personale dal cash flow. L'audit ha corretto un disallineamento schema-servizio di `investment-opportunity/v1`: campi sconosciuti, date non ISO e decimali non finiti sono ora rifiutati invece di essere ignorati o propagati. Nessuna dipendenza aggiuntiva, dato personale reale, duplicazione bloccante o debito tecnico che richieda decision log. Verifiche: 25 test mirati V5 OK, regression unit engine 517 test OK, smoke CLI `planning investment-opportunity demo` OK, `roadmap_audit.py` OK e controllo privacy sui file V5 senza dati personali reali (le sole occorrenze di identificativi fiscali sono fixture marcatamente sintetiche preesistenti).

### V5.3c — Income-producing real estate adapter V2

**Stato:** `done`
**Tipo:** `functional`

Estendere la capability immobiliare da `hold/rent/sell` a un vero modello di investimento a reddito.

- Dipende da: V5.3b.
- Repository: `engine`, `knowledge`, `rules` solo se servono nuove regole fiscali.
- Output: `real-estate-investment/v2`.
- Modelli iniziali: long-term rental, short-term rental, mixed personal/rental use.
- Driver: purchase/acquisition costs, capex, rent/nightly rate, occupancy/vacancy, agency/property-management fee, condominium, utilities, insurance, maintenance, taxes, financing link, exit costs/value.
- Fiscalita': nessuna aliquota hard-coded; `knowledge -> rules -> tests -> engine`, oppure data gap esplicito.
- Test: vacancy, management fee, maintenance shock, personal-use days, exit costs, missing tax classification.
- Done quando: il sistema distingue NOI, cash flow, tax drag e valore residuo e puo' confrontare l'immobile con altre alternative sullo stesso capitale/orizzonte.

Esito: completato con l'adapter deterministico `real-estate-investment/v2`, costruito sopra `investment-opportunity/v1` senza duplicarne formule comuni. Supporta flussi long-term, short-term e mixed-use con vacancy, disponibilita'/prenotazioni, commissione di gestione, costi operativi, tax drag dichiarato, giorni e beneficio di uso personale separati, acquisition basis, exit costs e valore residuo. La classificazione fiscale senza input o regola versionata produce `missing_tax_classification`; non sono state introdotte aliquote, classificazioni dedotte, rule pack o knowledge note. Scenari con acquisition basis diverse sono marcati non comparabili. Disponibili schema, fixture sintetica e CLI `fo planning real-estate-investment build|demo`. Verifiche: 20 test mirati/integrativi OK, regression unit engine 522 test OK, smoke CLI OK, privacy scan sui file V5.3c senza dati personali reali, `git diff --check` OK e `roadmap_audit.py` OK.

### V5.3d — Rentable movable asset / camper adapter

**Stato:** `done`
**Tipo:** `functional`

Aggiungere un adapter per asset mobili ad uso misto, con il camper come primo caso reale.

- Dipende da: V5.3c.
- Repository: `engine`, `knowledge`, `rules` solo se necessari.
- Output: `rentable-movable-asset/v1`.
- Driver: available days, personal-use days, rental days, daily rate, platform/agency fee, insurance, storage, cleaning, delivery/collection, maintenance, tyres, mileage/wear, downtime, major repair, residual value.
- Beneficio personale: `personal_use_economic_benefit` separato dal cash flow e mai trattato automaticamente come reddito o deduzione fiscale.
- Activity classification: `personal | occasional_rental | habitual_rental | business` come input/regola validata; non dedurla dalla sola frequenza.
- Test: utilization, downtime, major repair, mixed use, zero rental, residual-value shock, classification gap.
- Done quando: il camper e' confrontabile economicamente senza confondere utilita' personale, cash flow da noleggio e trattamento fiscale.

Esito: completato con `rentable-movable-asset/v1`, adapter deterministico sopra `investment-opportunity/v1`, fixture sintetica e CLI `fo planning rentable-movable-asset build|demo`. Il contratto conserva disponibilita', uso personale, noleggio e downtime separati; calcola ricavi da tariffa/giorni, fee piattaforma, costi operativi inclusi major repair, NOI, cash flow, utilizzo e valore netto di uscita. La classificazione dell'attivita' e' solo input validato (`personal`, `occasional_rental`, `habitual_rental`, `business`): se manca produce `missing_activity_classification`, senza deduzioni fiscali o basate sulla frequenza. Il beneficio d'uso personale resta economico e fuori dal cash flow imponibile. Verifiche: 5 test mirati, 19 test core/adapter, smoke CLI, regression unit engine 527 test, `git diff --check` e `roadmap_audit.py` OK.

### V5.3e — Financing and leverage analyzer

**Stato:** `done`
**Tipo:** `functional`

Introdurre un contratto riusabile `financing-plan/v1` per asset acquistati con debito.

- Dipende da: V5.3b.
- Repository: `engine`.
- Output: debt schedule con interest, principal, remaining balance, annual debt service, LTV e DSCR dove applicabile.
- Input: down payment, loan amount, fixed/variable rate assumption, duration, fees, balloon/early repayment se dichiarati.
- Vincolo: separare asset return da equity return; la leva non deve mascherare un asset economicamente debole.
- Test: fixed/variable assumption, zero debt, high LTV, debt-service stress, early repayment fee.
- Done quando: real estate e camper possono usare lo stesso financing contract senza formule duplicate.

Esito: completato con contratto e servizio deterministico `financing-plan/v1`, fixture sintetica e CLI `fo planning financing-plan build|demo`. Il piano annuale riusa lo stesso contratto per qualunque asset tramite un `asset_reference` e cash flow dichiarato; espone interessi, capitale, rimborso anticipato, fee, debt service, debito residuo, LTV e DSCR. Il cash flow dell'asset prima del finanziamento resta separato dal cash flow dell'equity dopo debt service. Tassi fissi/variabili, fee e rimborsi sono input obbligatori o gap; non vengono dedotti fiscalita', rendimenti, valori di garanzia o percorsi dei tassi. Verifiche: 6 test mirati, 25 test core/adapter integrati, smoke CLI, regression unit engine 533 test, `git diff --check` e `roadmap_audit.py` OK.

### V5.3f — Stress test and opportunity-cost comparator

**Stato:** `done`
**Tipo:** `functional`

Confrontare base/upside/adverse e l'uso alternativo dello stesso capitale sullo stesso orizzonte.

- Dipende da: V5.3c, V5.3d e V5.3e.
- Repository: `engine`.
- Output: `investment-opportunity-comparison/v1`.
- Stress real estate: occupancy/rent down, maintenance up, rate shock, exit-value shock.
- Stress camper: rental days/daily rate down, maintenance/insurance up, downtime, major repair, residual-value shock.
- Opportunity cost: benchmark esplicito da cash/tax-aware portfolio o altro scenario dichiarato; se manca, data gap.
- Household checks: liquidity reserve, concentration, retirement/work-exit impact, reversibility.
- Monte Carlo: fuori perimetro iniziale; prima base/upside/adverse deterministici.
- Test: same-capital/same-horizon enforcement, missing benchmark, adverse negative cash flow, liquidity breach.
- Done quando: il ranking mostra rendimento, rischio, liquidita' e management burden senza trasformare assumption in facts.

Esito: completato con il contratto e servizio deterministico `investment-opportunity-comparison/v1`, schema, fixture sintetica e CLI `fo planning investment-opportunity-comparison build|demo`. Il comparatore richiede nella capability primaria esattamente base/upside/adverse, riusa soltanto metriche e stress dichiarati da adapter/financing, impone capitale e orizzonte uguali tramite gap espliciti e non inventa benchmark. Il benchmark mancante o uno scenario benchmark non allineato restano data gap; cash flow negativo, liquidity/concentration breach e management burden sono osservabili separatamente. Non produce un ranking automatico e non sottrae due volte il costo del tempo del proprietario quando gia' incluso nei flussi dell'adapter. Verifiche: 5 test mirati, 30 test del blocco investment-opportunity, smoke `fo` nel venv locale, regression unit engine 538 test OK, `git diff --check`, privacy scan dei nuovi file e `roadmap_audit.py` OK.

### V5.3g — Investment opportunity code audit

**Stato:** `done`
**Tipo:** `audit`

Audit dopo quattro incrementi funzionali V5.3c-V5.3f.

- Dipende da: V5.3f.
- Repository: tutti quelli toccati dal blocco.
- Focus: contract reuse, formula definitions, leverage separation, fiscal gaps, household constraints, CLI/docs, privacy, regression e roadmap cadence.
- Done quando: il blocco deterministico e' stabile prima dell'integrazione strategica e del routing AI.

Esito: audit completato sui confini V5.3c-V5.3f. Il core resta l'unico punto per le metriche comuni; gli adapter riusano il core, il financing plan mantiene separati cash flow dell'asset e dell'equity, e il comparatore riceve solo flussi, valori di uscita, stress e vincoli household dichiarati senza ranking o doppio conteggio del costo del tempo. Classificazione fiscale/attivita', benchmark, soglie di liquidita' e concentrazione restano regole/input o data gap espliciti. L'audit ha corretto il drift locale dello schema input `investment-opportunity-comparison/v1`, documentando i campi annidati gia' richiesti dal servizio e proteggendoli con test. Nessuna dipendenza aggiuntiva, dato personale reale, formula duplicata o debito bloccante; non serve una decisione architetturale aggiuntiva. Verifiche: 31 test mirati/integrativi del blocco OK, smoke `fo` nel venv locale OK, JSON schema parse OK, regression unit engine e `roadmap_audit.py` OK, `git diff --check` OK e privacy scan del perimetro V5.3c-V5.3g senza dati personali reali.

### V5.3h — Wealth-strategy integration

**Stato:** `done`
**Tipo:** `functional`

Integrare le opportunita' nel compositore `wealth-strategy/v1` come alternative verificabili.

- Dipende da: V5.3g.
- Repository: `engine`.
- Package examples: keep portfolio, buy income property, buy mixed-use camper, alternative financial allocation.
- Ranking dimensions: expected net return dichiarato/derivato, cash yield, liquidity, capital at risk, tax drag, management burden, owner time, concentration, reversibility, personal utility, retirement cash-flow contribution, estate complexity.
- Vincolo: `wealth-strategy` compone output esistenti; non ricalcola imposte, IRR o fiscalita'.
- Test: missing adapter, blocked tax classification, liquidity breach, ranking tie, personal utility not treated as taxable cash flow.
- Done quando: appartamento e camper possono comparire nello stesso business case insieme al portafoglio finanziario con lineage completo.

Esito: completato estendendo `wealth-strategy/v1` con piu' sorgenti `investment-opportunity-comparison/v1`, selezionate per `comparison_id` e scenario. Il business case sintetico include portafoglio, immobile a reddito e camper nello stesso snapshot, con hash sorgente, scenario avverso e breach di liquidita' visibili. L'utilita' personale e' una dichiarazione economica separata `not_taxable_cash_flow`; tax/activity gap, benchmark e vincoli household restano gap della fonte. Una parita' assegna lo stesso rank e, insieme ai gap critici, disabilita `automatic_ranking_produced` e fa stampare `top=review_required`. Nessuna formula di imposte, IRR, rendimento, cash flow o classificazione viene duplicata o ricalcolata. Verifiche: test unitari/integrativi V5.3h, smoke `fo planning wealth-strategy demo`, regression engine, `roadmap_audit.py`, controllo JSON, `git diff --check` e privacy scan OK.

### V5.4 — Intent router

**Stato:** `done`
**Tipo:** `functional`

Classificare la domanda in uno o più intenti, estrarre entità e indicare dati mancanti senza eseguire calcoli.

- Dipende da: V5.3 e V5.3h.
- Repository: `engine`.
- Output: `question-intent/v1`.
- Test: dataset sintetico, ambiguità, prompt injection e richiesta non supportata.
- Done quando: il routing ha confidence e fallback deterministici.

Esito: completato con `question-intent/v1`, router lessicale deterministico che riusa `supported-question-catalog/v1`, restituisce confidence, intenti candidati, entita' proposte e dati minimi mancanti senza invocare tool, calcolare valori o scrivere facts. L'output conserva solo fingerprint della domanda. Prompt injection/istruzioni di tool, richieste fuori perimetro e collisioni di intenti restano `needs_clarification`. Il comparatore di opportunita' e' registrato come tool deterministico e la capability d'investimento richiede confronti e gap dichiarati; il router non lo invoca. Verifiche: test mirati catalog/router/registry, smoke `fo orchestration question-intent demo`, regression engine, `roadmap_audit.py`, `git diff --check` e privacy scan OK.

### V5.4a — Periodic code and contract audit

**Stato:** `done`
**Tipo:** `audit`

Verificare il primo blocco funzionale V5 prima di introdurre il query planner.

- Dipende da: V5.2, V5.3, V5.3h e V5.4.
- Repository: `bootstrap`, `knowledge`, `engine`.
- Checklist: `family-office-bootstrap/docs/code-audit-checklist.md`.
- Test: regression pertinente, privacy, allineamento contratti/CLI/docs e `roadmap_audit.py`.
- Done quando: citation index, tassonomia, investment-opportunity tools e router risultano coerenti e non restano blocker impliciti per V5.5.

Esito: audit completato su V5.2-V5.4. Citation index mantiene i contratti derivati dal registry (29 dopo il tool di confronto), il catalogo copre ogni tool disponibile una sola volta e dichiara il router `question-intent/v1` come sola classificazione senza invocazioni. Il comparatore di investimenti, il compositore wealth strategy e il registry condividono correttamente snapshot paths singolari/plurali; l'audit ha corretto la normalizzazione di `investment_opportunity_comparison_snapshot_paths` e il policy marker V5.3 che era rimasto obsoleto dopo V5.4. Schema, fixture, CLI, API docs, data gaps, privacy e confini restano coerenti; nessun dato personale reale, dipendenza non dichiarata, formula duplicata o follow-up residuo. Verifiche: 22 test mirati, smoke `fo` registry/question-intent/citations, regression engine 548 test OK, `roadmap_audit.py` OK, `git diff --check` e privacy scan OK.

### V5.5 — Query planner

**Stato:** `done`
**Tipo:** `functional`

Trasformare gli intenti in un DAG di tool con dipendenze, input, controlli e criteri di arresto.

- Dipende da: V5.4a.
- Repository: `engine`.
- Output: `execution-plan/v1`.
- Test: piano valido, ciclo, tool mancante, dato sensibile non autorizzato.
- Done quando: il piano è ispezionabile prima dell'esecuzione.

Esito: completato con il servizio deterministico `execution-plan/v1`, che valida un `question-intent/v1` gia' routed con lineage del catalogo corrente e costruisce un DAG topologicamente ordinato di soli tool registrati e consentiti dagli intenti selezionati. I binding dichiarano esclusivamente sorgente/riferimento/sensibilita'/autorizzazione: nessun valore personale o numerico entra nel piano; un binding sensibile richiede consenso esplicito. Tool non registrati o fuori catalogo, parametri obbligatori mancanti, dipendenze mancanti, cicli e lineage obsoleta sono rifiutati esplicitamente. Ogni nodo mostra controlli e stop criteria ma resta `not_executed`; il planner non importa l'adapter d'invocazione, non esegue tool e non calcola imposte, pensioni o valori finanziari. Disponibili `fo orchestration execution-plan build|demo`, guida JSON, API/CLI docs e decision log. Verifiche: 19 test mirati planner/router/registry OK, smoke `fo` demo OK, regression unit engine 555 test OK, `git diff --check`, privacy scan e controllo del confine non-esecutore OK; `roadmap_audit.py` era verde prima della chiusura.

### V5.6 — Natural-language scenario builder

**Stato:** `done`
**Tipo:** `functional`

Convertire richieste come “pensione a 62 anni con università dei figli” in draft di scenario strutturato, mai direttamente in risultato.

- Dipende da: V5.5 e scenario contract V2.
- Repository: `engine`, `workspace`.
- Output: scenario draft con facts proposti, assunzioni e richieste di conferma.
- Test: date, importi, conflitti, omissioni e valori non supportati.
- Done quando: nessuna assunzione implicita viene eseguita senza essere resa visibile.

Esito: completato con `scenario-draft/v1`, builder deterministico da domanda a preview non eseguibile. Il draft conserva solo fingerprint della domanda e `question-intent/v1`; promuove età pensionabile, date ISO, budget EUR e obiettivo università dei figli esclusivamente se espliciti, sempre come proposte `confirmation_required`. Età confliggenti, valori fuori range, budget non positivi, omissioni e istruzioni di tool restano conflitti, rifiuti o data gaps, senza diventare facts o assunzioni del contratto `decision-scenario/v2`. Disponibili `fo orchestration scenario-draft build|demo`, guida JSON aggiornata, API/CLI docs e decision log. Il builder non compone/esegue scenari né calcola imposte, pensioni, rendimenti o saldi. Verifiche: 15 test mirati draft/router/scenario V2 OK, smoke `fo` demo e build OK, regression unit engine 560 test OK, controllo del confine non-esecutore, privacy scan e `git diff --check` OK; `roadmap_audit.py` era verde prima della chiusura.

### V5.7 — Deterministic executor and evidence bundle

**Stato:** `done`
**Tipo:** `functional`

Eseguire il piano, raccogliere output, log, hash, fonti, errori e data gaps in un bundle unico.

- Dipende da: V5.5.
- Repository: `engine`, `workspace`.
- Output: `evidence-bundle/v1`.
- Test: esecuzione parziale, retry sicuro, timeout, versioni e riproducibilità.
- Done quando: la risposta può essere rigenerata dagli stessi input.

Esito: completato con `execution-request/v1` ed executor deterministico che accetta solo piani `execution-plan/v1` pronti con lineage corrente e invoca esclusivamente `invoke_registered_tool`. `evidence-bundle/v1` conserva output, stati, errori, data gaps, fonti/riferimenti e hash dei valori privati senza copiarli; grant, contratti output e policy devono coincidere con il registry. Retry fino a tre tentativi e' consentito solo ai tool read-only; timeout, fallimenti, skip per dipendenza o autorizzazione e risultati parziali restano espliciti. Disponibile `fo orchestration execute`. Verifiche: 18 test mirati executor/planner/registry OK, smoke CLI, regression unit engine 564 test OK, `git diff --check` e `roadmap_audit.py` OK.

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
