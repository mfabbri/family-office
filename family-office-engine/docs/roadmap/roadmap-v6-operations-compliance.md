# V6 Roadmap — Operations, Security, Compliance and Operator Experience

## Obiettivo

Rendere il family office un sistema mantenibile nel tempo e utilizzabile per decisioni familiari: aggiornamenti documentali, monitoraggio, sicurezza, audit, normativa, backup, release, revisione periodica e journey operatore question-first sopra capability deterministiche.

## Prerequisiti

- Gate V5 completato per le funzioni AI.
- I requisiti di privacy e sicurezza restano comunque trasversali e possono essere anticipati come incrementi abilitanti.

## Incrementi

### V6.1 — Pipeline refresh orchestrator

**Stato:** `done`
**Tipo:** `functional`

Creare un comando unico che rilevi input cambiati, esegua solo gli step necessari e produca un run manifest.

- Repository: `engine`, `workspace`.
- Output: `fo pipeline refresh`, DAG degli step e `pipeline-run/v1`.
- Test: run completo, incrementale, errore parziale, idempotenza.
- Done quando: gli snapshot non devono essere rigenerati manualmente in ordine.

Esito: completato con `pipeline-run/v1`, il servizio deterministico `pipeline_refresh` e CLI `fo pipeline refresh [--dry-run]`. Il DAG iniziale e' statico e locale: aggiorna `document_inventory` e il dipendente `snapshot_catalog` soltanto quando hash di input, output o dipendenze lo richiedono. Il manifest usa solo path relativi al workspace, stati espliciti e scrittura atomica dopo successo; un fallimento conserva il baseline precedente. Non esegue shell o comandi arbitrari, non interpreta documenti e non effettua calcoli fiscali, previdenziali o finanziari. Verifiche: 4 test V6.1 (completo, incrementale, modifica input, errore, idempotenza, dry-run e confinamento) OK; 11 test document inventory, 11 test audit roadmap e regression engine 586 test OK; smoke help CLI, compilazione, `git diff --check`, architecture/privacy scan e `roadmap_audit.py` OK.

### V6.2 — Lineage, hashes and freshness

**Stato:** `done`
**Tipo:** `functional`

Aggiungere hash input, versione parser/regola, timestamp, path relativi e policy di scadenza a snapshot e report.

- Dipende da: V6.1.
- Repository: `engine`, `workspace`.
- Output: `artifact-lineage/v1` e freshness checker.
- Test: documento cambiato, rule pack aggiornato, snapshot obsoleto, path multipiattaforma.
- Done quando: ogni risultato dichiara se è aggiornato e da quali input deriva.

Esito: completato con sidecar generico `artifact-lineage/v1`, builder/checker deterministici e CLI `fo pipeline lineage build|check`. Il sidecar registra artefatto, fonti `input` e `rule_pack`, SHA-256, versioni dichiarate, data di osservazione, path relativi normalizzati e policy di freshness; la scrittura e' atomica. Il checker, con data esplicita, rende visibili fonti/rule pack modificati o mancanti, artefatto modificato o assente e scadenza; nessun path assoluto o esterno al workspace e' accettato. Verifiche: 4 test V6.2 (hash/versioni, sorgenti/rule/scadenza, path e CLI), 21 test mirati V6.1-V6.2/document inventory/CLI wrapper e regression engine 590 test OK; smoke help CLI, compilazione, `git diff --check`, privacy scan del perimetro e `roadmap_audit.py` OK.

### V6.3 — Document intake and data-quality monitoring

**Stato:** `done`
**Tipo:** `functional`

Controllare nuovi documenti, duplicati, periodi mancanti, variazioni anomale e riconciliazione degli asset.

- Dipende da: V6.2.
- Repository: `engine`, `workspace`.
- Output: `data-quality-report/v1` e code di remediation.
- Test: duplicati, gap mensili, totale incoerente e documento non classificato.
- Done quando: una decisione non usa silenziosamente dati vecchi o incompleti.

Esito: completato con `data-quality-report/v1`, generato localmente da un inventario `document-inventory/v1` e da una dichiarazione `data-quality-input/v1`. I periodi mensili e i totali documentali attesi restano input espliciti; il report mette in coda remediation per duplicati SHA-256, documenti non classificati, mesi mancanti e totali incoerenti. Non legge o copia contenuti documentali, scrive atomicamente e rifiuta path assoluti, Windows assoluti o esterni al workspace. Disponibile `fo pipeline quality --input quality-input.json`.

Verifiche: 3 test V6.3, 22 test mirati V6.1-V6.3/document inventory/CLI e regression engine 593 test OK; smoke `fo pipeline quality --help`, compilazione, `git diff --check`, controllo del confine (solo libreria standard nel servizio), privacy scan del perimetro e `roadmap_audit.py` OK. Nessuna decisione architetturale o modifica a rule/knowledge richiede decision log.

### V6.3a - Data-quality CLI guided setup

**Stato:** `done`
**Tipo:** `functional`

Eliminare la compilazione manuale di dichiarazioni JSON dal percorso operativo di controllo qualità: la CLI deve mostrare copertura e gap rilevabili e raccogliere soltanto le aspettative di monitoraggio non deducibili.

- Dipende da: V6.3.
- Repository: `engine`, `workspace`.
- Output: `fo pipeline quality` leggibile e `fo pipeline quality setup` con configurazione workspace-local gestita dalla CLI.
- Test: report senza configurazione, wizard con default da inventario, gap mensile configurato, resume/configurazione e CLI.
- Done quando: l’operatore non deve creare o modificare JSON per sapere cosa manca; i criteri non deducibili diventano data gap o domande esplicite.

Esito: completato con il report workspace-local senza `--input` e `fo pipeline quality setup`. Il report espone documenti, finding e data gap delle coperture mensili non configurate; il setup usa categoria e mesi osservati come contesto, salva progressivamente `data-quality-policy/v1` e permette di escludere esplicitamente una categoria. Nessun totale, regola di qualità o contenuto documentale è dedotto o copiato. Verifiche: 5 test mirati V6.3/V6.3a, smoke `fo pipeline quality --help` e `fo pipeline quality setup --help`, regression engine 596 test, compilazione, audit roadmap, `git diff --check`, controllo import del servizio (sola libreria standard) e privacy scan del perimetro OK.

### V6.3b - Operations compliance code audit

**Stato:** `done`
**Tipo:** `audit`

Esito: audit completato. Corretto un difetto di compatibilita' dei default CLI: con `--workspace` non predefinito, refresh, lineage e quality ora derivano manifest, sidecar e report dal workspace selezionato invece che dal default di repository. Verifiche: 16 test mirati V6.1-V6.3b, smoke `fo` dei quattro comandi pipeline, regression engine 600 test, compilazione, `git diff --check`, controllo dipendenze dei servizi e audit roadmap OK. Nessun follow-up o decision log necessario.

Eseguire il code audit obbligatorio dopo V6.1, V6.2, V6.3 e V6.3a, usando la checklist del bootstrap e verificando confini, contratti, test, privacy, data gaps, error handling e duplicazioni. Correggere soltanto difetti piccoli e verificabili oppure registrare follow-up espliciti.

- Dipende da: V6.3a.
- Repository: `engine`, `workspace`.
- Test: test mirati dei moduli V6, smoke CLI, regression e audit roadmap.
- Done quando: il contatore audit è azzerato con evidenze riproducibili e ogni debito residuo è esplicito.

### V6.3c - Question-first operator analysis journey

**Stato:** `done`
**Tipo:** `functional`

Esito: completato con `fo ask [question]` e `operator-analysis/v1`. Il journey usa router/catalogo V5 ma non esegue tool: inventaria solo gli `schema_version` degli snapshot workspace-local e restituisce diagnosi, fatti, assunzioni, gap, limiti, provenienza e prossima azione, senza persistere la domanda o richiedere JSON manuale. Verifiche: 21 test mirati V6.3c/router/catalogo/registry, smoke `fo ask --help`, regression engine 605 test, compilazione, audit roadmap, controllo dipendenze/privacy e `git diff --check` OK.

Esporre un singolo ingresso guidato per domande decisionali familiari, riusando le capability deterministiche e gli snapshot esistenti senza chiedere sequenze di comandi tecnici o lettura/modifica manuale di JSON.

- Dipende da: V6.3b, V5.12.
- Repository: `engine`, `workspace`.
- Output: journey `fo` question-first, selezione/riconoscimento della domanda supportata, raccolta progressiva dei soli dati mancanti e risposta leggibile.
- Test: journey end-to-end con fixture sintetiche; fatti già presenti, dati mancanti, errore recuperabile, provenance/limiti, tool non supportato e assenza di JSON manuale.
- Done quando: l'operatore ottiene da una domanda una diagnosi o risposta leggibile con fatti, assunzioni, `data_gaps`, limiti, provenienza e prossima azione; i calcoli restano esclusivamente nei tool deterministici registrati.

### V6.3d - Local LLM intent-assist with deterministic gates

**Stato:** `done`
**Tipo:** `functional`

Integrare facoltativamente un LLM eseguito solo in locale per proporre intenti e chiarimenti nel journey `fo ask`, mantenendo il router/catalogo deterministici come autorita' per supporto, dati minimi e autorizzazione dei tool.

- Dipende da: V6.3c, V5.11, V5.12.
- Repository: `engine`, `workspace`.
- Output: proposta locale di intenti con confidence e motivazione, validata contro `supported-question-catalog/v1`, con fallback al routing lessicale.
- Vincoli: modello/prompt/testo domanda restano locali e non sono persistiti; un output del modello non puo' invocare tool, scegliere dati, autorizzare piani, calcolare valori fiscali, previdenziali o finanziari, ne' superare rifiuti/gap/guardrail deterministici.
- Test: modello locale assente, output malformato o fuori catalogo, prompt injection, conflitto fra proposta e router, fallback, privacy e evaluation suite sintetica.
- Done quando: il journey espone separatamente proposta LLM e validazione deterministica, conserva il fallback riproducibile e rifiuta qualsiasi percorso che aggiri catalogo, planner, executor o guardrail.

Esito: completato con adapter `local_intent_assist` della sola libreria standard, limitato a HTTP loopback OpenAI-compatible e attivato esplicitamente da `fo ask --local-intent-assist`. Il modello produce soltanto una proposta effimera di intenti/confidence; `operator-analysis/v1` espone proposta, validation e fallback separati, ma la route selezionata resta quella lessicale deterministica. Injection non raggiunge il modello; indisponibilita', output malformato, intenti fuori catalogo o conflitti non modificano route, dati minimi, tool, planner, executor o guardrail. Prompt, domanda, output e modello non sono persistiti e non sono introdotti calcoli fiscali, previdenziali o finanziari. Verifiche: 18 test mirati (inclusa evaluation sintetica e CLI), regression engine 613 test, compilazione, smoke `fo ask --help`, controllo loopback/import, privacy scan, `git diff --check` e audit roadmap OK.

### V6.3e - Question-first analysis response rendering

**Stato:** `done`
**Tipo:** `functional`

Trasformare l'esito di `fo ask` da diagnostica tecnica a risposta operativa leggibile, senza eseguire automaticamente tool o calcoli.

- Dipende da: V6.3d.
- Repository: `engine`, `workspace`.
- Output: rendering `fo ask` question-first con sintesi della domanda riconosciuta, soli fatti minimi rilevanti, stato espresso in linguaggio naturale, limiti e prossima azione eseguibile o motivo esplicito per cui non e' ancora disponibile.
- Vincoli: non mostrare l'inventario completo degli snapshot come risposta primaria; non presentare ID di tool o `schema_version` come istruzioni per l'operatore; `ready_for_analysis` non puo' suggerire che un calcolo sia gia' stato eseguito; nessun tool viene invocato, nessun calcolo fiscale/previdenziale/finanziario viene introdotto e nessun testo della domanda viene persistito.
- Rendering richiesto: per una domanda supportata, indicare (1) decisione compresa, (2) fatti minimi presenti e mancanti con nomi leggibili, (3) cosa il sistema puo' preparare ma non ha ancora eseguito, (4) limiti e revisione umana richiesta, (5) una prossima azione realmente disponibile. Se il piano separato non e' ancora esposto da CLI, dirlo esplicitamente senza fingere un comando di approvazione.
- Test: fixture con molti snapshot irrilevanti, input completo, gap, domanda non supportata, injection, assistente locale disponibile/non disponibile, assenza di JSON tecnico nel rendering e coerenza fra testo leggibile e `operator-analysis/v1`.
- Done quando: un operatore comprende da solo che cosa e' stato capito, quali soli dati contano per la domanda, se si tratta di una diagnosi o di un'analisi eseguita e qual e' il prossimo passo concretamente disponibile; nessun inventario tecnico o istruzione non eseguibile resta nel percorso primario.

Esito: completato con il campo `presentation` di `operator-analysis/v1` e il rendering CLI question-first. Per una domanda di liquidita', la CLI mostra la decisione, tre soli fatti rilevanti con label leggibili, diagnosi di prontezza e nessun calcolo eseguito; snapshot irrilevanti, ID di tool e versioni schema restano fuori dall'output primario. Gap e prossima azione usano gli stessi label leggibili; quando l'analisi e' pronta ma il comando per il piano manca, il limite e' dichiarato senza simulare un'azione. L'assistente locale resta opzionale e comprensibile, ma non rende visibili ID tecnici ne' modifica il router. Verifiche: 19 test mirati, regression engine 614 test, smoke reale `fo ask`, compilazione, controllo confini/privacy, `git diff --check` e audit roadmap OK. Nessuna modifica a rules/knowledge o decision log necessaria.

### V6.4 — Compliance calendar and alerts

**Stato:** `done`
**Tipo:** `functional`

Gestire scadenze fiscali, documentali, previdenziali, polizze, rinnovi, review e trigger familiari.

- Dipende da: V3.4 e V6.2.
- Repository: `knowledge`, `rules`, `engine`, `workspace`.
- Output: `compliance-calendar/v1` e alert locali.
- Test: ricorrenze, scadenze mobili, alert duplicati e timezone.
- Done quando: ogni alert mostra fonte, responsabilità e azione richiesta.

Esito: completato con `compliance-calendar/v1`, policy `it.compliance-calendar.2026.v1`, alert locali deduplicati e journey `fo compliance calendar|setup`. Il rule pack dichiarativo porta fonte, validita', owner e azione; l'engine calcola solamente ricorrenze annuali, date una tantum, ultimo giorno lavorativo e timezone. Le scadenze locali sono raccolte progressivamente senza JSON manuale e una fonte mancante diventa `source_not_verified`, non un obbligo implicito. Nessun importo, debito o obbligo fiscale individuale e' calcolato.

Verifiche: 5 test V6.4 (ricorrenza, mobile, timezone, deduplicazione, errori, source gap e CLI) e regression engine 619 test OK; smoke `fo compliance calendar --help`, compilazione, JSON validation knowledge/rules, `git diff --check`, privacy/confine (sola libreria standard, workspace-local) e audit roadmap OK. Il quarto incremento funzionale dopo V6.3b rende dovuto l'audit prima del prossimo incremento funzionale.

### V6.4a - Operations compliance code audit

**Stato:** `done`
**Tipo:** `audit`

Eseguire il code audit obbligatorio dopo V6.3c, V6.3d, V6.3e e V6.4 con la checklist del bootstrap. Il perimetro e' `operator_analysis`, `local_intent_assist`, `compliance_calendar`, CLI e relativi contratti, test e documentazione. Correggere solo difetti piccoli e verificabili; registrare come follow-up ogni debito non risolto nello stesso audit.

- Dipende da: V6.3c, V6.3d, V6.3e e V6.4.
- Repository: `engine`, `rules`, `knowledge`, `workspace`.
- Test: test mirati del perimetro, smoke CLI, regression engine e audit roadmap.
- Done quando: il contatore audit e' azzerato con evidenze riproducibili e ogni debito residuo e' esplicito.

Esito: audit completato. Nel perimetro V6.3c-V6.4, journey operatore, assistente locale e calendario restano confinati a dati workspace-local/sintetici, routing deterministico, data gaps espliciti e path compatibili; nessun dato personale reale, dipendenza non dichiarata o disallineamento sostanziale fra CLI, servizi, contratti, test e documentazione e' stato rilevato. Corrette due lacune piccole: il calendario rifiuta ID evento duplicati anche tra rule pack e scadenze locali, e `tzdata>=2025.2` e' dichiarato/installato per supportare IANA timezone su Windows. Nessun follow-up o decision log necessario.

Verifiche: `pip check`, 33 test mirati e regression engine 620 test OK; compilazione, validazione JSON rule pack, smoke `fo ask --help` e `fo compliance calendar --help`, `git diff --check` e audit roadmap OK.

### V6.5 — Regulatory update workflow

**Stato:** `done`
**Tipo:** `functional`

Rilevare e valutare cambi normativi seguendo Knowledge → Rules → Tests → Engine, con validità temporale e approvazione.

- Repository: `bootstrap`, `knowledge`, `rules`, `engine`.
- Output: change proposal, impact assessment e release checklist normativa.
- Test: nuova aliquota, norma retroattiva, fonte non autorevole e rollback.
- Done quando: una regola non può cambiare senza fonte, test e periodo di validità.

Esito: completato con contratto `regulatory-change/v1`, servizio locale deterministico e CLI `fo compliance regulatory prepare|approve|rollback`. La proposta registra fonte, autorita', giurisdizione, periodo di validita', retroattivita', rule pack impattati, test richiesti, data gaps, checklist, approvazione e strategia di rollback. Fonti non autorevoli e cambi retroattivi restano in revisione; il servizio non usa rete, non modifica knowledge/rules e non interpreta aliquote o risultati fiscali. Verifiche: 6 test mirati con integrazione CLI, compilazione, smoke help e controlli finali di regression, privacy/architettura, `git diff --check` e `roadmap_audit.py` OK.

### V6.6 — Secrets, encryption and access control

**Stato:** `done`
**Tipo:** `functional`

Proteggere workspace, token, backup e dati identificativi con cifratura, secret store e least privilege.

- Repository: `bootstrap`, `engine`, `workspace`.
- Output: threat model, configurazione locale e security checks.
- Test: segreto nel repository, permessi eccessivi, file non cifrato e log sensibile.
- Done quando: nessun segreto o documento personale entra in pacchetti software o log diagnostici.

Piano V6.6: il contratto `security-check/v1` e' locale e deterministico; il comando `fo security check` esegue la diagnostica con default workspace, mentre cifratura e decifratura autenticata restano operazioni esplicite e confinabili. Il secret store e' creato con chiave casuale e permessi del proprietario su POSIX; su Windows il report non simula una verifica ACL che Python non puo' attestare. Lo scanner non legge o stampa contenuti nei finding, non usa rete e non modifica snapshot esistenti.

Esito: completato con `security-check/v1`, servizio `security`, secret store locale e CLI `fo security check`. Verifiche: test mirati 17 OK con 1 skip Windows motivato, regression engine 631 OK con 1 skip, `pip check`, compilazione, smoke CLI, validazione planner stdlib, audit roadmap, scansione privacy/confini e `git diff --check` OK.

### V6.6a — Guided planning input wizards

**Stato:** `done`
**Tipo:** `functional`

Rendere inseribili dalla CLI gli input mancanti che `fo ask` identifica per patrimonio, protezione e successione, senza richiedere la modifica manuale di JSON.

- Dipende da: V6.6.
- Repository: `engine`, `workspace`.
- Output: `fo planning wealth-strategy wizard`, `fo planning protection wizard` e `fo planning estate wizard`, con draft privati, salvataggio progressivo e validazione locale.
- UX: partire dalla decisione familiare, mostrare fatti già disponibili, chiedere solo dati mancanti, dichiarare assunzioni, `data_gaps`, limiti, provenance e prossima azione.
- Test: ripresa con `--overwrite`, input incompleti, valori incerti come gap, path confinati al workspace, privacy, fixture sintetiche e coerenza con `fo ask`.
- Out of scope: calcoli fiscali, previdenziali o finanziari nuovi; consulenza legale; import automatico da fonti non dichiarate; esecuzione automatica dei piani.
- Done quando: ogni input richiesto dalle tre capability ha un percorso CLI guidato documentato e testato, e `fo ask` indica un prossimo comando realmente disponibile.

Esito: completato con i tre wizard workspace-local `fo planning wealth-strategy wizard`, `fo planning protection wizard` e `fo planning estate wizard`. I draft usano salvataggio progressivo, `--overwrite`, provenance dichiarata e `data_gaps`; i path esterni sono rifiutati. `fo ask` propone i wizard quando mancano gli input corrispondenti. Valori di protezione incerti non vengono presentati come coperti: il builder restituisce `review_required`. Verifiche: 21 test mirati, regression engine 637 test OK con 1 skip Windows, compilazione, `pip check`, smoke help, audit roadmap, validazione routing strutturale, privacy/path boundary e `git diff --check` OK. Nessun dato personale reale, rete, import o nuovo calcolo introdotto.

### V6.6b — Plain-language questions and contextual explanations

Sostituire nei wizard le richieste tecniche e criptiche con domande semplici orientate alla decisione familiare e aggiungere spiegazioni contestuali prima di ogni risposta.

**Stato:** `done`
**Tipo:** `functional`

- Dipende da: V6.6a.
- Repository: `engine`, `workspace`.
- Output: testi question-first per i wizard wealth-strategy, protection ed estate; spiegazioni di data, pacchetto strategico, fatti disponibili, valori incerti e prossima azione.
- UX: distinguere chiaramente dati già disponibili, dati richiesti, esempi e valori ancora da verificare; non chiedere identificativi tecnici senza spiegarne lo scopo.
- Test: prompt comprensibili, default spiegati, input vuoti trasformati in `data_gaps`, ripresa con `--overwrite`, output senza gergo non spiegato e coerenza con `fo ask`.
- Out of scope: nuovi calcoli, raccomandazioni automatiche, consulenza fiscale/legale/finanziaria e modifica dei contratti deterministici.
- Done quando: un operatore non tecnico può completare o riprendere ciascun wizard comprendendo cosa sta inserendo, perché viene richiesto e quale sarà il passo successivo.

Esito: completato con prompt question-first in linguaggio semplice, spiegazioni contestuali per etichette locali, data di riferimento, valori incerti e alternative strategiche, riepilogo dei fatti disponibili con nomi comprensibili e messaggi finali orientati al passo successivo. I contratti e i calcoli restano invariati. Verifiche: 12 test UX mirati, regression engine 637 test OK con 1 skip Windows, compilazione, `pip check`, smoke CLI, audit roadmap, validazione planner e `git diff --check` OK. Il draft personale presente nel workspace è rimasto fuori dal cambiamento e dal commit.

### V6.6c — Operations compliance code audit

**Stato:** `done`
**Tipo:** `audit`

Eseguire il code audit obbligatorio dopo i quattro incrementi funzionali successivi all’audit V6.4a: V6.5, V6.6, V6.6a e V6.6b.

- Dipende da: V6.6b.
Esito: audit completato. Corrette quattro lacune piccole e verificabili: l'approvazione regulatory-change/v1 richiede checklist Knowledge/Rules completa e test evidence nominativa; il calendario rende needs_review una policy fuori validità e rifiuta intervalli incoerenti; lo scanner non può essere eluso da marker synthetic/fixture nel contenuto; il setup locale sceglie il primo ID libero. Follow-up esplicito: rendere parametrica la data dei wizard V6.6b per garantire riproducibilità cross-day, senza ampliare questo audit.

Verifiche: 26 test mirati del perimetro (1 skip ACL Windows), regression engine 640 test OK (1 skip), compilazione, pip check, smoke CLI, validazione JSON planner, routing validator, git diff --check, privacy scan e roadmap_audit.py OK.
- Perimetro: contratti, CLI, wizard, servizi di sicurezza/compliance, test, documentazione, privacy, data gaps, dipendenze e duplicazioni.
- Done quando: la checklist di audit è completata, i difetti piccoli sono corretti o registrati come follow-up espliciti e `audit_due=false`.

### V6.6d — Work-exit guided input wizard

**Stato:** `done`
**Tipo:** `functional`

Raccogliere dalla CLI gli input necessari per stimare la prima data sostenibile di uscita dal lavoro, senza richiedere la compilazione manuale di JSON.

- Dipende da: V6.6c.
- Repository: `engine`, `workspace`.
- Output: `fo planning work-exit wizard`, manifest `work-transition-readiness/v1` e input `work-exit-feasibility/v1` workspace-local, con salvataggio progressivo e ripresa.
- UX: partire dalla decisione familiare, mostrare gli snapshot già disponibili, chiedere solo dati mancanti e distinguere fatti, assunzioni, `data_gaps`, limiti e prossima azione.
- Test: wizard completato, ripresa/interruzione, input mancanti o incerti, path confinati, privacy, coerenza con readiness e calcolo work-exit.
- Out of scope: nuovi calcoli pensionistici o finanziari, import automatici, certificazioni INPS, consulenza fiscale o raccomandazioni.
- Done quando: un operatore può introdurre e validare i dati necessari dalla CLI e poi eseguire il calcolo work-exit senza modificare JSON manualmente.

Esito: completato con `fo planning work-exit wizard`. Il wizard raccoglie dati dichiarati, salva progressivamente input e manifest readiness nel workspace, supporta revisione con `--overwrite`, mostra il contesto degli snapshot senza copiarne contenuti e conserva gli incerti come `data_gaps`. I path sono confinati e distinti; date adulte mancanti mantengono il nucleo esplicito ma bloccano l'invito al build. Il manifest non inventa fonti: gli snapshot devono essere collegati nel relativo workflow di readiness prima del calcolo. Nessun nuovo calcolo pensionistico, finanziario o fiscale e' stato introdotto.

Verifiche: 7 test wizard mirati; regression engine 647 test OK (1 skip); compilazione, `pip check`, routing validator, `roadmap_audit.py`, privacy/path review e `git diff --check` OK. La documentazione CLI e testing e' allineata; V6.7 resta pianificato e non avviato.

### V6.7 — Sanitized export and packaging

**Stato:** `done`
**Tipo:** `functional`

Esito: completato con `fo export sanitized`. L'engine produce un archivio ZIP deterministico con allowlist fissa per codice Python, roadmap e report dichiarati; esclude workspace, snapshot, backup, `.venv`, `.history`, PDF e symlink, redige marker deterministici per dati sensibili nei file testuali ammessi e registra `manifest.json` con hash SHA-256 dei byte esportati, conteggi, esclusioni e radici allowlist mancanti. Il target resta confinato al workspace, la sostituzione richiede `--overwrite` e la scrittura usa un temporaneo univoco e atomico. Non sono stati introdotti upload, backup, restore, rete o dati personali.

Verifiche: 15 test mirati export/security/validate OK (2 skip ambientali); regression engine 657 test OK (2 skip); help CLI, compilazione, `pip check`, `git diff --check`, routing validator, privacy/path review e `roadmap_audit.py` OK. Review indipendente finale approvata; V6.8 resta pianificato e non avviato.

Creare export allowlist per codice, roadmap e report, con redazione dei dati personali e manifest dei file.

- Dipende da: V6.6.
- Repository: `bootstrap`, `engine`.
- Output: `fo export sanitized` e policy di packaging.
- Test: `.venv`, `.history`, backup, snapshot e PDF personali esclusi.
- Done quando: uno ZIP condivisibile non può contenere dati privati per default.

### V6.8 — Backup, restore and disaster recovery

**Stato:** `done`
**Tipo:** `functional`

Implementare backup cifrati, retention, verifica integrità, restore selettivo e recovery drill con manifest riproducibile.

- Dipende da: V6.6.
- Repository: `bootstrap`, `workspace`.
- Output: runbook e manifest backup.
- Test: restore su directory vuota, backup corrotto, chiave mancante e versioni.
- Done quando: il workspace può essere ricostruito con una prova documentata.
- Piano corrente: ownership del contratto e del runtime nell'engine; secret store workspace-local già introdotto da V6.6; archivio ZIP deterministico cifrato con manifest laterale, retention esplicita, restore selettivo confinato e drill su destinazione vuota. La chiave non viene inclusa nel backup e upload/cloud restano fuori scope.
- Esito: completato con `fo backup create|verify|restore|drill`. Il payload ZIP è deterministico prima della cifratura Fernet, il manifest laterale conserva hash e dimensioni senza contenuti, retention conserva le copie più recenti, verify controlla autenticazione/ZIP/hash, restore accetta solo selezioni relative e destinazioni workspace-local, drill richiede una directory vuota. Secret store, backup, cache, temporanei, virtualenv, history e symlink sono esclusi.
- Verifiche: 5 test mirati backup, regression engine 662 test OK con 2 skip ambientali, compileall, `pip check`, smoke `fo backup --help`, routing validator, privacy/path review, `git diff --check` e `roadmap_audit.py` OK.

### V6.9 — Audit trail and approvals

**Stato:** `done`
**Tipo:** `functional`

Registrare chi o cosa ha importato dati, modificato assunzioni, approvato scenari e generato raccomandazioni.

- Dipende da: V6.1 e V5.10.
- Repository: `engine`, `workspace`.
- Output: append-only `audit-event/v1` e approval workflow.
- Test: modifica, revoca, replay, clock skew e tamper detection.
- Done quando: ogni raccomandazione ad alto impatto ha una catena di approvazione ricostruibile.

Esito: completato con `audit-event/v1`, servizio locale append-only e CLI `fo audit append|verify|replay`. Ogni evento conserva sequenza, timestamp con timezone, attore, soggetto, azione, riferimento, hash del precedente e SHA-256 proprio; il log non contiene documenti o testo personale. Il replay ricostruisce approvazioni e revoche senza riscrivere eventi, mentre verify rileva modifica, inserimento, cancellazione o riordinamento e rifiuta clock skew oltre cinque minuti. Firma remota, identita' federata e rete restano fuori scope.

Verifiche: 4 test mirati V6.9, regression engine 666 test con 2 skip ambientali, smoke `fo audit --help` e CLI append/verify/replay, compilazione, `pip check`, validazione planner, `roadmap_audit.py`, `git diff --check` e review privacy/path OK.

### V6.10 — Regression, release and model governance

**Stato:** `done`
**Tipo:** `functional`

Unificare test unitari, golden data, scenari, regole, AI evaluations e migrazioni in gate di release.

- Dipende da: V5.11 e V6.5.
- Repository: tutti tranne workspace reale.
- Output: release pipeline, version matrix e rollback plan.
- Test: release candidata, regressione fiscale, modello AI diverso e schema incompatibile.
- Done quando: ogni release ha evidenze, versioni e criteri di rollback.

Piano corrente: ownership del contratto `release-gate/v1` e del runtime nell'engine; `fo release check` genera una matrice versioni/hash e coordina soltanto controlli locali allowlistati, inclusa evaluation sintetica V5.11 e regression engine. Il rollback è un piano dichiarativo e non esegue deploy, restore o upload.

Esito: completato con servizio deterministico `release_governance`, contratto `release-gate/v1` e CLI `fo release check`. Il gate raccoglie versioni/hash di engine, rule pack ed evaluation, esegue solo regression, compilazione, dipendenze, audit roadmap ed evaluation sintetica V5.11, rileva regressioni baseline e incompatibilità di schema e conserva un rollback plan non automatico. Nessuna rete, upload, deploy, workspace reale, nuova regola o nuovo calcolo è stato introdotto.

Verifiche: 14 test mirati V6.10/V5.11/tool registry OK; gate reale passed con 5 controlli; regression engine 670 test OK con 2 skip ambientali; compileall, pip check, routing validator, planner JSON, privacy/architettura, `git diff --check` e `roadmap_audit.py` OK. V6.11 resta pianificato e non avviato.

### V6.10a — Initial feature guide

**Stato:** `done`
**Tipo:** `docs`

Creare una guida iniziale unica e concisa, orientata alle domande familiari, che renda scopribili tutte le feature disponibili senza richiedere la lettura della reference tecnica.

- Dipende da: V6.10.
- Repository: `engine`.
- Output: guida question-first unica collegata dalla documentazione CLI/workflow.
- Contenuto minimo: domande supportate, percorso `fo ask`, wizard e build, scenari e report, demo sintetiche, import documentali, compliance/security/backup/audit, data gaps, limiti e prossima azione.
- Test/review: link e comandi verificati, nessun comando obsoleto, distinzione fra demo sintetiche e dati reali, privacy review e controllo di completezza rispetto alla CLI pubblica.
- Done quando: un nuovo operatore può partire da una domanda come “quando posso smettere di lavorare?” e trovare il percorso corretto fino all'output, senza JSON manuale o gergo non spiegato.

Esito: completato con `docs/feature-guide.md`, collegato da `cli-workflow.md` e `cli.md`. La guida copre il percorso `fo ask`, work-exit, patrimonio/protezione/successione, scenari e investimenti, import e qualità dati, pensioni/cashflow/fiscalità, compliance/sicurezza/backup/audit/release, demo sintetiche, stati, gap, limiti e prossime azioni. I comandi pubblici citati sono stati verificati con `fo ... --help`; nessun runtime, contratto, regola o dato personale è stato modificato. Nessun decision log update necessario: non sono state introdotte nuove decisioni architetturali o normative.

### V6.10b — Guided work-transition source binding

**Stato:** `done`
**Tipo:** `functional`

Rendere utilizzabile il percorso Work Transition collegando dalla CLI gli snapshot già disponibili alle fonti richieste da `work-transition-readiness/v1`.

- Dipende da: V6.10a.
- Repository: `engine`, `workspace`.
- Output: `fo planning work-transition sources setup` o percorso guidato equivalente, con manifest `work-transition-readiness-input/v1` workspace-local e salvataggio progressivo.
- Scope: rilevare snapshot disponibili, mostrare categoria/member/value basis/schema, chiedere solo conferma o dati mancanti, generare binding pointer e provenance, validare freshness/stream bounds/liquidità e rieseguire readiness.
- Categorie minime: reddito principale e coniuge, spese, patrimonio, liquidità ponte, RITA, INPS, Spagna/UE e altri redditi.
- UX: partire dalla domanda “quali dati posso usare per stimare quando smettere di lavorare?”, distinguere fonti disponibili, fonti mancanti, conflitti e gap; JSON manuale resta fallback avanzato documentato.
- Out of scope: nuovi calcoli pensionistici/finanziari/fiscali, import automatico non dichiarato, scelta silenziosa della fonte, dati personali fuori workspace.
- Done quando: il wizard work-exit può portare da `sources: []` a una readiness validata o a gap specifici e azionabili, senza richiedere la modifica manuale del manifest.

Esito: completato con servizio deterministico di discovery/binding workspace-local e comando `fo planning work-transition sources setup`. Il setup rileva solo snapshot con schema supportato, mostra categoria/membro/basis/data, richiede scelta esplicita, salva progressivamente adapter con provenance, hash e `binding_pointer`, preserva periodi, bounds, liquidità e coverage dichiarati e lascia gap azionabili quando i metadata mancano. Il readiness gate verifica a ogni esecuzione presenza e hash della snapshot originale, workspace configurabile, compatibilità del manifest e path sicuri. Nessun nuovo calcolo pensionistico, finanziario o fiscale è stato introdotto.

Verifiche: 23 test mirati V6.10b + readiness OK; regression engine 677 test OK con 2 skip ambientali; readiness CLI 2/2 OK; review T3 indipendente GO; compileall, pip check, privacy/path review, planner JSON, `git diff --check` e `roadmap_audit.py` OK. V6.11 resta pianificato e non avviato.

### V6.11 — Annual review and contingency plan

**Stato:** `done`
**Tipo:** `functional`

Produrre una review annuale con KPI, eventi, cambi normativi, scostamenti, rischi e piano di aggiornamento.

- Dipende da: V6.3–V6.10.
- Repository: `engine`, `workspace`.
- Output: `annual-review/v1`, KPI e contingency actions.
- Test: anno incompleto, dati obsoleti, cambio residenza e evento straordinario.
- Done quando: il sistema indica cosa riesaminare, perché e con quale priorità.

Esito: completato con contratto `annual-review/v1`, servizio deterministico workspace-local e comando `fo review annual`. La review usa solo metadati degli snapshot, produce KPI di copertura/freshness/gap, intercetta eventi dichiarati di cambio residenza o straordinari e genera finding prioritari e contingency actions; `needs_review` resta esplicito e richiede revisione umana. Nessun contenuto personale viene ristampato, nessuna rete o import automatico è usato e nessun calcolo fiscale, previdenziale o finanziario è stato introdotto.

Verifiche: 5 test mirati annual review/CLI, regression engine 682 test OK con 2 skip ambientali, compileall, pip check, smoke `fo review annual --help`, roadmap audit, validation execution guardrails, review architetturale/privacy del perimetro e `git diff --check` OK.

## Exit criteria V6

- Pipeline e aggiornamenti sono incrementali, tracciati e riproducibili.
- Dati privati, segreti, backup ed export hanno policy verificabili.
- Normativa e modelli AI sono soggetti a governance e regression test.
- Alert e review hanno owner, fonte e azione.
- Il sistema è recuperabile e auditabile senza dipendere dalla memoria dell'operatore.
### V6.9a - Operations compliance code audit

**Stato:** `done`
**Tipo:** `audit`

Eseguire il code audit obbligatorio dopo V6.6d, V6.7, V6.8 e V6.9 con la checklist del bootstrap. Il perimetro comprende backup, audit trail, approval workflow, CLI, contratti, test, documentazione e planner. Correggere solo difetti piccoli e verificabili; registrare follow-up espliciti per ogni debito non risolto.

- Dipende da: V6.9.
- Repository: `bootstrap`, `engine`, `workspace`.
- Test: test mirati del perimetro, smoke CLI, regression e audit roadmap.
- Done quando: il contatore audit e' azzerato con evidenze riproducibili e ogni debito residuo e' esplicito.

Esito: audit completato sul perimetro V6.6d-V6.9. Confini dei servizi, contratti, CLI, test, documentazione, privacy, path workspace-local, data gaps, error handling e dipendenze risultano coerenti; backup e restore escludono segreti, backup precedenti, temporanei e symlink, mentre audit trail e approval replay mantengono catena hashata e riferimenti senza contenuti personali. Non sono state rilevate lacune piccole e verificabili da correggere né follow-up tecnici da aprire. La modifica preesistente al draft personale nel workspace è rimasta fuori dal cambiamento.

Verifiche: 46 test mirati V6.6d-V6.9 e 15 test cadenza/CLI OK; regression completa engine, compilazione, pip check, smoke `fo backup --help`/`fo audit --help`, validazione planner, privacy/path review, `git diff --check` e `roadmap_audit.py` OK. V6.10 resta pianificato e non avviato.
