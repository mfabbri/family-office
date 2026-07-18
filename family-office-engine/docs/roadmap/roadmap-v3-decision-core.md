# V3 Roadmap — Decision Core

## Obiettivo

Trasformare gli snapshot separati in un modello decisionale familiare coerente, temporale, spiegabile e utilizzabile da simulatori e ottimizzatori. La V3 non introduce ancora una chat AI: costruisce le primitive deterministiche che l'AI userà in seguito.

## Prerequisiti

- Gate V2 completato secondo `roadmap-index.md`.
- Contratti V1 di net worth, cashflow, rule engine e simulazione disponibili.
- Dati personali confinati nel workspace.

## Incrementi

### V3.1 — Household facts contract

**Stato:** `done`

Definire un contratto versionato per persone, nucleo familiare, relazioni, residenza fiscale, date rilevanti e ruoli economici.

- Repository: `engine`, `workspace`.
- Output: `household-facts/v1`, schema JSON e fixture sintetiche.
- Test: validazione tipi, identificatori, date, assenza di dati obbligatori inventati.
- Done quando: il nucleo può essere rappresentato senza duplicare dati nei singoli snapshot.

### V3.2 — Ownership and beneficiary graph

**Stato:** `done`

Rappresentare titolarità, cointestazione, beneficiari, nuda proprietà, usufrutto, debiti e relazioni fra persone e asset.

- Dipende da: V3.1.
- Repository: `engine`, `workspace`.
- Output: estensione JSON-LD del graph contract e builder deterministico.
- Test: quote di proprietà, somme quote, ownership sconosciuta, asset del coniuge e dei figli.
- Done quando: ogni componente patrimoniale può essere collegato a uno o più soggetti con provenance.

### V3.3 — Asset classification and availability

**Stato:** `done`

Classificare gli asset per classe, rischio, valuta, giurisdizione, liquidità, vincoli, tassazione e prima data di disponibilità.

- Dipende da: V3.2.
- Repository: `engine`, `rules`, `workspace`.
- Output: `asset-availability/v1`, tassonomia versionata e template/guida compilabile per completare `household-facts/v1` e `ownership-beneficiary-graph/v1` senza dover leggere gli schema JSON.
- Test: liquidità immediata, fondi pensione vincolati, polizze, immobili, asset esteri, validazione dei template guidati con fixture sintetiche.
- Nota UX: i draft JSON V3.1/V3.2 sono corretti per la macchina ma poco chiari per la compilazione manuale; V3.3 deve aggiungere esempi guidati, legenda campi e percorso di validazione locale per l'utente.
- Done quando: le simulazioni possono distinguere patrimonio netto da patrimonio effettivamente utilizzabile.

### V3.4 — Timeline and event model

**Stato:** `done`

Definire eventi puntuali e ricorrenti: pensionamento, fine agevolazione, scadenze, contribuzioni, spese straordinarie, successione e cambio di residenza.

- Dipende da: V3.1 e V3.3.
- Repository: `engine`, `rules`.
- Output: `timeline-events/v1`, priorità e regole di sovrapposizione.
- Test: eventi nello stesso anno, eventi ricorrenti, date mancanti, conflitti.
- Done quando: uno scenario può essere espresso senza aggiungere parametri ad hoc al simulatore.

### V3.4a — Code audit cadence 1

**Stato:** `done`

Eseguire il primo audit tecnico dopo quattro incrementi funzionali V3 completati (`V3.1`-`V3.4`) e registrare eventuali follow-up prima di procedere a V3.5a.

- Dipende da: V3.4.
- Repository: `bootstrap`, `engine`, `rules`, `workspace`.
- Output: audit documentato in `current-next-increment.md`, eventuali follow-up in roadmap o decision log.
- Test: regression suite engine, controllo privacy/dati personali, allineamento schema-builder-CLI-docs-test, controllo duplicazioni e complessità.
- Done quando: i risultati dell'audit sono tracciati e il prossimo incremento funzionale può procedere senza debiti impliciti.

### V3.5a — Spanish pension document ingestion

**Stato:** `done`

Acquisire e normalizzare la documentazione necessaria a ricostruire la carriera previdenziale spagnola senza stimare importi non documentati.

- Dipende da: V3.1 e V3.4.
- Repository: `knowledge`, `engine`, `workspace`.
- Fonti prioritarie:
  - `Vida Laboral` per periodi di alta, regimi, datori di lavoro e giorni contributivi;
  - `Informe de bases de cotización` come fonte primaria delle basi mensili;
  - nóminas/buste paga spagnole come fonte integrativa e di controllo;
  - certificazioni INSS o dati manuali solo se dichiarati e con provenance esplicita.
- Output: `spanish-contribution-history/v1` con periodi, regime, giorni, basi mensili, valuta, fonte, confidence e data gaps.
- Test: Vida Laboral testuale, basi mensili, nómina supportata, mese mancante, documento duplicato, PDF non leggibile.
- Done quando: periodi e basi contributive sono disponibili in un contratto unico, senza dedurre la pensione dalla sola retribuzione lorda o dalla sola Vida Laboral.

### V3.5b — Spanish contribution reconciliation

**Stato:** `done`

Riconciliare periodi e basi provenienti da fonti differenti, mantenendo la gerarchia delle evidenze e rendendo visibili anomalie e coperture incomplete.

- Dipende da: V3.5a.
- Repository: `engine`, `workspace`.
- Regola fonti: le basi ufficiali prevalgono sulle nóminas; le nóminas possono integrare o segnalare differenze, ma non sovrascrivono silenziosamente dati ufficiali.
- Output: `spanish-contribution-reconciliation/v1` con mesi coperti, mancanti, duplicati, incoerenti e fonte selezionata.
- Test: periodo in Vida Laboral senza base, base senza periodo, doppia contribuzione, differenza nómina/base ufficiale, lacune pluriennali.
- Done quando: il motore può dichiarare quali mesi sono utilizzabili per il calcolo e quali richiedono documentazione o revisione.

### V3.5c-a — Spanish statutory pension rule pack baseline

**Stato:** `done`

Creare il baseline normativo e tecnico necessario prima dell'estimatore spagnolo, senza calcolare ancora importi pensionistici.

- Dipende da: V3.5b.
- Repository: `knowledge`, `rules`, `engine`.
- Output: knowledge note spagnola, rule pack `spanish-statutory-pension-rule-pack/v1`, loader/validatore deterministico e lookup per eta' ordinaria/base reguladora.
- Test: rule pack valido, fonte BOE obbligatoria, limitazioni obbligatorie, eta' ordinaria 2026, base reguladora 2026.
- Done quando: V3.5c puo' partire da regole versionate invece di inventare parametri previdenziali.

### V3.5c-b — Spanish pension accrued percentage rules

**Stato:** `done`

Completare nel rule pack spagnolo la progressione percentuale maturata oltre i primi 15 anni, senza calcolare ancora importi pensionistici.

- Dipende da: V3.5c-a.
- Repository: `knowledge`, `rules`, `engine`.
- Output: `spanish-statutory-pension-rule-pack/v1` esteso con schedule percentuale e helper deterministico `accrued_pension_percentage`.
- Test: rule pack valido, schedule deferred rigettata, 15 anni = 50%, 25 anni nel 2026 = 73,78%, cap al 100% dal 2027.
- Done quando: V3.5c puo' calcolare la percentuale maturata da regole versionate, senza inventare progressioni normative.

### V3.5c-c — Code audit cadence 2 before Spanish statutory pension estimator

**Stato:** `done`

Eseguire il secondo audit tecnico periodico dopo quattro incrementi funzionali V3 completati dall'ultimo audit (`V3.5a`, `V3.5b`, `V3.5c-a`, `V3.5c-b`) prima di procedere all'estimatore V3.5c.

- Dipende da: V3.5c-b.
- Repository: `bootstrap`, `engine`, `rules`, `knowledge`, con verifica di confine sul `workspace`.
- Output: audit documentato in `current-next-increment.md`, eventuali follow-up in roadmap o decision log.
- Test: regression suite engine, controllo privacy/dati personali, allineamento import-riconciliazione-rule pack-docs-test, data gaps ed error handling.
- Done quando: i risultati dell'audit sono tracciati e V3.5c puo' procedere senza debiti impliciti.

### V3.5c — Spanish statutory pension estimator

**Stato:** `done`

Stimare la pensione pubblica spagnola applicando rule pack versionati per data di pensionamento e distinguendo sempre risultato ufficiale, stima interna e assunzione.

- Dipende da: V3.5b e rule engine previdenziale spagnolo, incluso V3.5c-b.
- Repository: `knowledge`, `rules`, `engine`.
- Calcoli minimi:
  - età pensionabile e requisiti contributivi stimati;
  - periodi e basi utilizzabili secondo la normativa applicabile;
  - base reguladora e percentuale maturata;
  - pensione lorda mensile e annuale;
  - scenari ordinario, anticipato e differito quando applicabili;
  - confidence, regole applicate e dati mancanti.
- Output: `spanish-statutory-pension/v1`.
- Test: carriera completa, carriera breve, basi mancanti, transizione normativa, pensionamento in date differenti, scenario non calcolabile.
- Done quando: ogni importo ordinario è riproducibile da basi, regole e data di riferimento; in assenza di basi sufficienti il risultato è `blocked_missing_inputs`, non una stima inventata. Anticipo e differimento restano fuori finche' non esistono rule pack dedicati.

### V3.5d — EU pension coordination Italy–Spain

**Stato:** `done`

Applicare il coordinamento previdenziale UE mantenendo separati i diritti nazionali e modellando, quando previsto, calcolo nazionale e pro-rata.

- Dipende da: V3.5c e disponibilità dei dati INPS.
- Repository: `knowledge`, `rules`, `engine`.
- Output: `eu-pension-coordination-it-es/v1` con periodi italiani e spagnoli, totalizzazione ai soli fini del diritto, quote nazionali, decorrenze e warning.
- Test: diritto autonomo in entrambi i Paesi, diritto maturato tramite totalizzazione, date di decorrenza differenti, sovrapposizioni e periodi non riconosciuti.
- Done quando: il sistema non trasferisce o fonde contributi tra INPS e Seguridad Social, ma espone separatamente ogni prestazione e il criterio di coordinamento usato. Il pro-rata resta diagnostico/non calcolabile finche' mancano importi teorici nazionali e periodi normalizzati completi.

### V3.5e — Pension income composer

**Stato:** `done`

Comporre le entrate pensionistiche da INPS, pensione spagnola, Fon.Te, RITA e altre prestazioni, mantenendo separati valori documentali, stime e assunzioni.

- Dipende da: V3.4, V2.7 e V3.5a–V3.5d.
- Repository: `knowledge`, `rules`, `engine`, `workspace`.
- Output: `pension-income/v1` con flussi lordi/netti, Paese erogatore, decorrenza, periodicità, confidence e data gaps.
- Test: sola INPS, INPS+Spagna, decorrenze differenti, RITA opzionale, prestazione non stimabile.
- Done quando: il reddito pensionistico entra automaticamente negli scenari senza input manuale duplicato e senza sommare importi non omogenei o privi di fonte. In V1 il simulatore usa solo il totale lordo annuo ricorrente esplicito di `pension-income/v1`; netto, fiscalita', decorrenze mensili e annualizzazioni mancanti restano fuori perimetro.

### V3.6 — Lifecycle expense model

**Stato:** `done`

Modellare spese per fase della vita, inflazione, figli, sanità, abitazione e spese straordinarie.

- Dipende da: V3.1 e V3.4.
- Repository: `engine`, `workspace`.
- Output: `lifecycle-expenses/v1` e cashflow annuo spiegabile.
- Test: inflazione, periodi, spesa una tantum, categorie mancanti.
- Done quando: le spese non sono più un unico importo costante per tutta la simulazione.

### V3.6a — Code audit cadence 3 before scenario contract V2

**Stato:** `done`

Eseguire il terzo audit tecnico periodico dopo quattro incrementi funzionali V3 completati dall'ultimo audit (`V3.5c`, `V3.5d`, `V3.5e`, `V3.6`) prima di procedere a V3.7.

- Dipende da: V3.6.
- Repository: `bootstrap`, `engine`, `rules`, `knowledge`, con verifica di confine sul `workspace`.
- Output: audit documentato in `current-next-increment.md`, eventuali follow-up in roadmap o decision log.
- Test: regression suite engine, controllo privacy/dati personali, allineamento pensioni-lifecycle-scenario readiness-docs-test, data gaps ed error handling.
- Done quando: i risultati dell'audit sono tracciati e V3.7 può procedere senza debiti impliciti.

### V3.7 — Scenario contract V2 and composer

**Stato:** `done`

Creare un contratto di scenario che combini facts, eventi, regole, ipotesi di mercato, policy di prelievo e obiettivi.

- Dipende da: V3.3, V3.4, V3.5a–V3.5e e V3.6.
- Repository: `engine`.
- Output: `decision-scenario/v2`, composer e migrazione dagli scenari pensionamento V1.
- Test: scenario base, ottimistico, avverso, input incompatibili, hash riproducibile.
- Done quando: ogni scenario è un artefatto versionato e rieseguibile.

### V3.8 — Sensitivity and stress testing

**Stato:** `done`

Eseguire variazioni controllate su rendimenti, inflazione, redditi, longevità, spese, fiscalità e timing degli eventi.

- Dipende da: V3.7.
- Repository: `engine`.
- Output: `sensitivity-analysis/v1`, tornado data e stress matrix.
- Test: perturbazioni isolate, scenari combinati, seed e ordinamento stabili.
- Done quando: il sistema identifica quali assunzioni cambiano realmente la decisione.

### V3.9 — Multi-objective scoring

**Stato:** `done`

Valutare alternative per sostenibilità, patrimonio finale, liquidità, fiscal drag, rischio, complessità, reversibilità e compliance.

- Dipende da: V3.7 e V3.8.
- Repository: `engine`, `rules`.
- Output: `decision-score/v1` con pesi espliciti e metriche separate.
- Test: dominanza, pareggi, pesi diversi, metrica mancante.
- Done quando: il ranking non dipende da una singola percentuale di successo.

### V3.10 — Explainable recommendation dossier

**Stato:** `done`

Produrre una raccomandazione deterministica che mostri fatti, assunzioni, alternative, motivi del ranking, rischi, gap e azioni successive.

- Dipende da: V3.9.
- Repository: `engine`, `workspace`.
- Output: snapshot e report Markdown `decision-dossier/v1`.
- Test: provenance completa, nessuna raccomandazione con gap bloccanti, stabilità del report.
- Done quando: un revisore può ricostruire il risultato senza consultare il codice.

### V3.10a — Code audit cadence 4 and V3 exit readiness

**Stato:** `done`

Eseguire il quarto audit tecnico periodico dopo quattro incrementi funzionali V3 completati dall'ultimo audit (`V3.7`, `V3.8`, `V3.9`, `V3.10`) prima di procedere alla roadmap V4.

- Dipende da: V3.10.
- Repository: `bootstrap`, `engine`, `rules`, `knowledge`, con verifica di confine sul `workspace`.
- Output: audit documentato in `current-next-increment.md`, eventuali follow-up in roadmap o decision log, verifica exit criteria V3.
- Test: regression suite engine, controllo privacy/dati personali, allineamento scenario-sensitivity-score-dossier-docs-test, data gaps ed error handling.
- Done quando: i risultati dell'audit sono tracciati e il gate V3 -> V4 può essere valutato senza debiti impliciti.

Nota successiva all'audit: una verifica semantica del codice ha rilevato che il gate non e' ancora superato. `sensitivity-analysis/v1` produce varianti delle assunzioni ma non outcome rivalutati, mentre `decision-score/v1` accetta metriche esplicite senza lineage obbligatorio verso simulazioni. L'audit resta completato come attivita', ma la sua conclusione di readiness e' corretta dagli incrementi V3.10b-V3.10d.

### V3.10b — Decision outcome contract and deterministic evaluator bridge

**Stato:** `done`

Collegare `decision-scenario/v2` a un primo caso verticale realmente supportato dai valutatori deterministici esistenti e produrre outcome riproducibili utilizzabili dagli incrementi successivi.

- Dipende da: V3.7 e V3.10a.
- Repository: `engine`, `workspace`.
- Output: `decision-outcome/v1` con metriche calcolate, evaluator/versione, seed, provenance, data gaps e hash riproducibile.
- Test: outcome calcolato, riproducibilita', scenario incompatibile, evaluator non supportato, provenance completa e smoke CLI.
- Done quando: almeno un caso verticale trasforma uno scenario V2 in metriche calcolate senza copiare metriche manuali e senza leggere input impliciti.

### V3.10c — Outcome-linked sensitivity and stress execution

**Stato:** `done`

Estendere la sensitivity affinche' ogni variante supportata riesegua il valutatore deterministico e confronti gli outcome con la baseline.

- Dipende da: V3.10b.
- Repository: `engine`.
- Output: estensione compatibile di `sensitivity-analysis/v1` oppure nuova versione se il contratto cambia in modo incompatibile, con baseline outcome, variant outcome, delta metriche e tornado ordinato per impatto dichiarato.
- Test: perturbazione senza effetto, cambio outcome, stress combinato, ordinamento per impatto, evaluator bloccato, seed e hash stabili.
- Done quando: il sistema identifica quali assunzioni cambiano gli outcome e rende verificabile se cambia il ranking decisionale.

### V3.10d — Traceable scoring pipeline and V3 gate verification

**Stato:** `done`

Collegare scoring e dossier agli outcome calcolati, rendere obbligatoria la provenance delle metriche usate per una raccomandazione e rivalutare il gate V3 -> V4 con un golden scenario end-to-end.

- Dipende da: V3.10c.
- Repository: `bootstrap`, `engine`, `rules`, `workspace` con sole fixture sintetiche nei repository pubblicabili.
- Output: scoring con lineage scenario -> evaluator -> outcome -> sensitivity -> ranking -> dossier; golden scenario sintetico; esito documentato del gate V3 -> V4.
- Test: metriche senza provenance bloccanti, ranking modificato da outcome, dossier ricostruibile, golden end-to-end e regression suite completa.
- Done quando: ogni raccomandazione e' riconducibile a facts, regole, simulazioni e metriche calcolate; solo allora V3 puo' essere marcata `done` nell'indice e V4.1 diventa selezionabile.

Esito: completato con scoring outcome-linked, blocchi su lineage mancante, dossier con verifica della provenance e golden pipeline sintetica end-to-end. La regression suite engine passa con 273 test.

## Exit criteria V3

- Il patrimonio è attribuito a soggetti e vincoli.
- Cashflow e pensioni sono collocati su una timeline comune.
- La pensione spagnola usa periodi e basi riconciliati, regole versionate e coordinamento UE esplicito; nessun importo deriva dalla sola Vida Laboral.
- Gli scenari sono artefatti versionati, non insiemi di parametri CLI.
- Sensitivity e scoring sono deterministici e spiegabili.
- Le raccomandazioni vengono bloccate quando mancano facts essenziali.

## Stato del gate V3 -> V4

`passed`

Le primitive V3.1-V3.10d sono disponibili e la regression suite passa. Il lineage eseguibile tra scenario, outcome simulati, sensitivity, scoring e dossier e' verificato da test mirati e da un golden scenario sintetico end-to-end. V4.1 puo' essere selezionato come prossimo incremento.
