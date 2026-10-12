# Current Next Increment

## Ultimo micro-incremento completato — V4.14e

**Titolo:** Italian pension-law validity checkpoint for 2026-2028
**Stato:** `done`
**Tipo:** audit normativo documentale, nessuna nuova regola.

### Piano

1. Verificare la base normativa italiana successiva alla snapshot Normattiva restituita con vigenza 2026-09-09: L. 199/2025, art. 1, comma 185, e decreto direttoriale attuativo MEF-Lavoro 19-12-2025, pubblicato in G.U. n. 301/2025.
2. Confrontare solo il perimetro già approvato di pensione di vecchiaia ordinaria FPLD/AGO per dipendenti con età 67/67a1m/67a3m e, per coorte contributiva post-1995, alternativa 71/71a1m/71a3m nel 2026-2028.
3. Registrare fonte legislativa primaria, atto attuativo vincolante, fonte amministrativa esplicativa e deroghe non coperte nella nota Knowledge; sottoporre il confronto a reviewer normativo indipendente.
4. Non cambiare rule pack o engine, non estendere il GO alle deroghe/profili speciali e non sbloccare la timeline V4.14.

**Esito fonti:** la L. 199/2025 è fonte legislativa primaria; il decreto direttoriale MEF-Lavoro 19-12-2025 è atto attuativo vincolante. Il combinato quadro prevede incremento di un mese nel 2027 e tre mesi nel 2028; la circolare INPS 28/2026 ne riepiloga l'applicazione e specifica deroghe e comparti speciali. Per l'alternativa a 71 anni, la tabella puntuale è confermata dall'INPS, ma gli atti storici che producono il valore base 71 non sono stati ricostruiti qui. La provenance del rule pack resta un gap; nessuna modifica al pack in questo audit.
**Esito gate:** GO limitato indipendente esclusivamente per la documentazione della gerarchia delle fonti e la registrazione dei gap, dopo due correzioni editoriali; nessuna ricertificazione del rule pack, nessun nuovo GO eseguibile e nessuno sblocco di V4.14.
**Verifica:** review indipendente, roadmap audit, planner JSON Schema, execution guardrails e `git diff --check` passati. Test runtime non applicabili: nessun rule pack o codice modificato.
**Stop condition:** tracciabilità storica del valore 71 e provenance normativa diretta del rule pack restano gap per ogni uso o estensione che richieda copertura completa. `V4.14` resta `blocked`.

Nota Knowledge: `family-office-knowledge/pensions/pension-timeline-events-it-es-eu.md`.

---

## Prossimo micro-incremento pianificato — V4.14f

**Titolo:** Italian eligibility rule-pack legal provenance traceability
**Stato:** `planned`
**Tipo:** audit abilitante Knowledge → Rules → Tests → Engine.

Ricostruire la catena delle disposizioni e degli atti attuativi che sostiene i requisiti annuali del rule pack `it.inps-old-age-eligibility.2026-2028.v1`, soprattutto la base dei 71 anni; integrare riferimenti ufficiali source-bound nel pack solo dopo review normativa. Aggiungere test sintetici di source-period/version binding e verificare che profili speciali, eccezioni, dati ignoti o provenance insufficiente restino fail-closed. Modificare engine solo se i test evidenziano un'apertura non sicura nel consumer.

- Fuori scope: ampliamento a gestioni o categorie speciali, calcolo pensionistico individuale, timeline completa, importi, date di riconoscimento/pagamento e accesso al workspace.
- Done quando: catena ufficiale legislativa/attuativa documentata e revisionata; pack provenance allineata senza cambiare valori non approvati; regressioni sintetiche passano e i consumer falliscono chiuso sui gap di fonte/periodo.
- V4.14 rimane `blocked` fino a un gate autonomo sulla timeline completa.

---

## Ultimo micro-incremento completato — V4.14d

**Titolo:** Event-level pension timeline normative support matrix
**Stato:** `done`
**Tipo:** audit normativo documentale, nessuna regola eseguibile.

### Piano

1. Verificare fonti normative primarie e fonti amministrative ufficiali IT, ES e UE distinguendole, con data di consultazione e periodo/ambito dichiarato.
2. Aggiungere la matrice Knowledge per `eligibility_date`, `requirements_met_date`, `official_recognition_date`, `economic_effective_date` e `first_cash_payment_date`; distinguere l'evento computabile dalla prova amministrativa o bancaria.
3. Sottoporre la sola matrice a review normativa indipendente. Ogni evento o profilo non sufficientemente supportato resta `null` con `data_gaps`.
4. Chiudere solo V4.14d; non sbloccare V4.14 e non aggiungere regole, servizi o date calcolate.

**Esito gate:** GO limitato del reviewer normativo sulla matrice dopo la revisione delle fonti. Riferimenti a Reg. 987/2009 art. 48 aggiunti per la notifica delle decisioni; data di consultazione e vigenza restituita di Normattiva esplicitamente separate. Il gap italiano successivo al 2026-09-09 rimane aperto. Nessuna timeline individuale è approvata.

**Fuori scope:** rule pack, codice engine, importi, proiezione di date, decisioni individuali e accesso a `family-office-workspace/`.
**Verifica:** review delle fonti, roadmap audit, planner schema, execution guardrails e `git diff --check`; nessun test runtime previsto per questo slice documentale.
**Stop condition:** rilievo normativo materiale o fonte/periodo non verificabile mantiene il micro-incremento aperto e la timeline bloccata.

La matrice verificata con limiti/gap è in `family-office-knowledge/pensions/pension-timeline-events-it-es-eu.md`.

---

## Storico ultimo incremento chiuso — V4.14b

## ID e titolo

V4.14b — Pension normative remediation and source freshness gate.

## Stato

`done`

### GO normativo limitato: eligibility ordinaria solo

Il GO riguarda soltanto una regola deterministica di sola eligibility per il percorso ordinario di vecchiaia di dipendenti FPLD/AGO, con una sola gestione/ambito confermato e requisiti soddisfatti nel 2026-2028. Per la coorte con prima contribuzione anteriore al 1996: eta 67 / 67a1m / 67a3m e 20 anni qualificanti. Per la prima contribuzione dal 1996: le stesse eta e 20 anni qualificanti piu pensione mensile documentata almeno pari all'assegno sociale mensile applicabile documentato, oppure eta 71 / 71a1m / 71a3m e 5 anni di contribuzione effettiva, esclusa quella figurativa.

L'evidenza source-bound richiesta comprende DOB, coorte, categoria di gestione/rapporto confermata, storia contributiva datata o totali validati, importo e soglia documentati per il percorso contributivo ventennale e cessazione documentata. Sconosciuti, fuori periodo, eccezioni, piu gestioni o aggregazioni estere/UE producono `null` con `data_gaps`, mai un esito negativo.

Il dedicated eligibility pack e il service sono completati con GO normativo limitato post-fix e validazione pack fail-closed. Non calcolano importi e non emettono riconoscimento, decorrenza economica o primo pagamento. Il pack importi esistente e il consumer legacy `work_exit_feasibility` restano separati e non modificati. V4.14b è `done`; V4.14 resta `blocked` dal NO-GO sul contratto completo.

Il gate post-fix ha dato GO limitato sul downgrade temporale e una seconda review scoped ha dato GO limitato sulla freshness. L'incremento resta aperto per il perimetro V4.14 più ampio; nessuno dei due esiti approva la timeline pensionistica.

## Avanzamento verificato — 2026-10-11 (note storiche della prima fase, prima dell'aggiunta del pack eligibility)

- Knowledge aggiornato con fonti INPS, BOE, EUR-Lex 883/2004 e 987/2009 verificate il 2026-10-11.
- Rule pack di coordinamento UE versionato v2 per il perimetro 2026; pack pensione ordinaria spagnola v2 con copertura della transizione della base reguladora fino al 2036.
- 58 test mirati e di regressione passano: overlap IT/ES non classificato, status assicurativo spagnolo non confermato e date pensionistiche fuori validità bloccano l'esito; art. 57 sotto un anno non produce pro-rata automatico; il 2037 fuori schedule fallisce chiuso.
- L'ultimo reviewer ha dato NO-GO circoscritto: il dossier EU poteva risultare `complete` con candidate date 2039 fuori dal rule pack 2026. Il consumer ora produce gap su date fuori periodo o mancanti/invalide.
- Il gate indipendente autorizzato ha dato GO limitato: il consumer declassa entrambe le prestazioni a `not_assessed_rule_pack_period` quando le date mancano o escono dalla validità del pack; nessun blocker sul diff circoscritto. Il reviewer non ha rieseguito i test; il parent ha verificato 58 test mirati. Questo non approva la timeline completa.
- Freshness runtime implementato per quattro rule pack pensionistici attivi: provenance HTTPS ufficiale, giurisdizione/disposizioni e date di recupero/review obbligatorie; scadenza massima 90 giorni; sei consumer pensionistici fail-closed. `fo planning pension-sources audit` è locale/no-network e il wizard `review` aggiorna solo le date dopo conferma umana. Il report del 2026-10-11 risulta `fresh` per 4/4 pack. `fo release check` esegue l'audit come controllo indipendente anche con unit regression disattivata e fallisce se la freshness è bloccata; 69 test focalizzati passano.
- Review normativa indipendente scoped sulla freshness: GO limitato dopo una finestra estesa, sulla base di review statica; il reviewer non ha rieseguito i test. Il gate è limitato ai quattro pack dichiarati e non approva la timeline V4.14.
- Perimetro escluso dalla freshness V4.14 dopo review normativa: i pack contributivo V4.4 e tax V4.6a/V4.6b hanno consumer distinti e non sono coperti da questo gate; richiedono governance separata. Il contratto gap-aware dei cinque eventi è formalizzato nello schema, ma il calcolo della timeline completa, gli importi e i relativi stream restano fuori dal GO limitato; V4.14 resta `blocked`.

## Roadmap

`docs/roadmap/roadmap-v4b-work-transition.md`

## Perimetro freshness V4.14

### Aggiornamento corrente — 2026-10-11

Le note storiche qui sotto che riportano quattro pack e sei consumer descrivono il perimetro precedente all'aggiunta dell'eligibility italiana. La copertura effettiva è ora di cinque pack e sette consumer diretti (sei servizi pensionistici e il proiettore del reddito da lavoro); l'audit locale ha riportato 5/5 fresh. Il reviewer indipendente ha dato GO limitato dopo i fix; il pack è fail-closed, source-bound e version-driven. Lo schema [`pension-entitlement-timeline/v1`](../schemas/pension-entitlement-timeline.schema.json) formalizza i cinque eventi separati, richiedendo `null`+`data_gaps` per eventi non valutati e fonti per date supportate, senza implementare calcoli. La suite aggiornata passa 81 test. V4.14b è `done`; il GO non autorizza importi o timeline e V4.14 resta `blocked` dal NO-GO sul contratto completo.

Il freshness gate V4.14 copre soltanto i quattro pack pensionistici dichiarati. Sono esclusi e non devono essere classificati `fresh` o `stale` senza un audit dedicato: `family-office-rules/italy/2026/pension-contribution-deduction.json` (consumer contributivo V4.4, contribution-deduction), `family-office-rules/cross-border/it-es-pension-tax-classification.json` (consumer tax-classification V4.6a) e `family-office-rules/cross-border/spanish-pension-net-it-resident.json` (consumer gross-to-net tax V4.6b). Per questi pack serve una governance separata con scope proprio, contratto di metadati delle fonti e decisione esplicita su consumer e release gate.

V4.14b è chiusa per il perimetro abilitante descritto sopra. V4.14 resta `blocked`: il contratto completo e l'implementazione della timeline attendono un GO normativo indipendente separato. Nessuna data non supportata può essere sostituita con la cessazione dal lavoro.

Le righe precedenti che riportano quattro pack e sei consumer sono storiche e descrivono la prima attivazione. Il perimetro vigente è cinque pack/sette consumer; i tre pack V4.4/V4.6a/V4.6b elencati restano esclusi.

## Obiettivo

Rimuovere il NO-GO normativo di V4.14 con un perimetro pensionistico supportato, regole e fonti versionate, e un controllo periodico che blocchi l'uso di fonti prive di provenance o oltre la data di revisione.

## Scope

- Aggiornare Knowledge e rule pack da fonti primarie, registrando giurisdizione, atto/articolo, `retrieved_on`, validità giuridica e validità del pack come metadati distinti.
- Limitare l'Italia a gestioni/requisiti dimostrati; versionare le regole spagnole per periodo; correggere il coordinamento UE secondo Reg. 883/2004 artt. 50, 52, 56 e 57.
- Definire nel contratto timeline date distinte per eleggibilità, requisiti computazionalmente soddisfatti, riconoscimento ufficiale, decorrenza economica e primo pagamento.
- Implementare test e un audit locale deterministico che richieda revisione almeno ogni 90 giorni e alla pubblicazione di modifiche ufficiali rilevanti; `review_due` superata o provenance mancante blocca l'uso della regola.
- Lasciare date/importi non supportati come `null` con `data_gaps`; nessuno stream inizia per default alla `work_cessation_date`.

## Fuori scope

- Bridge, RITA, decumulo, simulazione e optimizer (V4.15–V4.18).
- Nuove formule/aliquote pensionistiche senza approvazione normativa indipendente e fixture sintetiche.
- Importazione o lettura dei dati personali del workspace.
- Qualsiasi uso di LLM per calcolare importi o decorrenze.

## Prerequisito V4.13

V4.13 è chiusa il 2026-10-11 con GO limitato post-review e 131 test focalizzati. I suoi output restano consapevolmente parziali: IRPEF nazionale lavoro-only è illustrativa; payroll netto, contributi del lavoratore, detrazioni/addizionali, TFR futuro, matching Fon.Te e montante INPS mensile senza precisione/periodicità supportata rimangono `null`/gap. V4.14 non può riempire tali gap per inferenza né consentire che una timeline bloccata alimenti un optimizer.

## Piano e gate

1. Correggere Knowledge → Rules → Tests per i rilievi NO-GO, con fonte primaria e periodo per ogni requisito e coordinamento.
2. Definire i campi di freshness (`reviewed_on`, `next_review_due`) senza confonderli con `valid_from`/`valid_to`, che descrivono l'applicabilità normativa del pack.
3. V4.14c freshness audit è implementato e ha GO limitato scoped: comando locale senza rete, sette consumer fail-closed, release gate bloccante, revisione massima 90 giorni e trigger umano immediato su modifiche ufficiali. V4.14c è chiuso insieme alla dipendenza V4.14b; il prossimo gate resta la timeline V4.14, ancora bloccata.
4. Implementare la timeline solo dopo il GO indipendente, mantenendo distinti i cinque eventi e null/gap per riconoscimento, decorrenza o pagamento non derivabili.
5. Se resta un gap materiale, mantenere V4.14 bloccata e non collegare la timeline a bridge o optimizer.

## Verifiche e stop condition

- Test sintetici per fonti mancanti/scadute/future, cambio ufficiale, regole fuori periodo, art. 57, periodi sovrapposti e date di pagamento non supportate.
- Il controllo di freshness deve fallire in modo chiuso quando `next_review_due` è superata; non effettua né dichiara monitoraggio automatico della rete.
- Nessuna regola eseguibile prima del gate Knowledge → Rules → Tests → Engine.
- Fermarsi se le fonti non distinguono in modo verificabile requisito, decorrenza e pagamento o se manca una base/precisione necessaria; non sostituire le evidenze con un'aliquota o una data presunta.
- Nessun accesso ai dati personali in `family-office-workspace/` durante questa fase di pianificazione/review.
- L'audit periodico non equivale a certificazione INPS/Seguridad Social o a riconoscimento amministrativo del diritto.
