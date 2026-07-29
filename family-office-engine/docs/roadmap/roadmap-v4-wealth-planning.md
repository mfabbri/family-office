# V4 Roadmap — Wealth Planning

## Obiettivo

Usare il Decision Core per confrontare strategie patrimoniali lecite e realistiche, ottimizzando rendimento netto, liquidità, fiscalità, protezione familiare e reversibilità.

Gli incrementi V4 devono mantenere semplice l'uso della CLI: preferire comandi corti con default del workspace, demo/smoke sintetici e preparazione guidata degli input. La compilazione manuale di JSON deve restare minima e giustificata; quando inevitabile, servono draft, template, guida leggibile e validazione locale.

## Prerequisiti

- Gate V3 completato.
- Raccomandazioni spiegabili e metriche multi-obiettivo disponibili.
- Rule pack fiscali versionati per gli anni simulati.

## Incrementi

### V4.1 — Goals and constraints model

**Stato:** `done`
**Tipo:** `functional`

Formalizzare obiettivi, priorità, soglie minime, orizzonte, rischio, liquidità, eventi familiari e vincoli legali.

- Repository: `engine`, `workspace`.
- Output: `planning-goals/v1`.
- Test: obiettivi incompatibili, priorità, soglie e campi mancanti.
- Done quando: l'ottimizzazione usa vincoli dichiarati invece di preferenze implicite.

Esito: completato con contratto e snapshot `planning-goals/v1`, validatore deterministico, CLI, fixture sintetica, draft workspace e test. Non calcola strategie, imposte, rendimenti, scoring o raccomandazioni.

### V4.2 — Liquidity buckets and emergency reserve

**Stato:** `done`
**Tipo:** `functional`

Dividere gli asset in riserva, breve, medio e lungo termine tenendo conto di vincoli, volatilità e date di disponibilità.

- Dipende da: V4.1 e V3.3.
- Repository: `engine`, `rules`.
- Output: `liquidity-plan/v1`.
- Test: riserva insufficiente, asset vincolati, valuta estera, concentrazione.
- Done quando: il piano non usa per spese correnti asset non liquidabili.

Esito: completato con contratto e snapshot `liquidity-plan/v1`, builder deterministico, CLI, fixture sintetiche e test. La riserva usa spese mensili esplicite e mesi dichiarati; asset non liquidabili, locked, vincolati, in valuta estera o senza classificazione non finanziano spese correnti. Non calcola rendimenti, imposte, FX, ottimizzazioni, scoring o raccomandazioni.

### V4.2a — Code audit after liquidity plan

**Stato:** `done`
**Tipo:** `audit`

Audit periodico dopo quattro o piu' incrementi funzionali completati dall'ultimo audit V3.10a.

- Dipende da: V4.2.
- Repository: `engine`.
- Output: audit checklist e follow-up espliciti, se presenti.
- Test: suite pertinente e verifica allineamento schema, builder, CLI, fixture, docs e privacy.
- Done quando: eventuali debiti non corretti sono registrati e non bloccano o bloccano esplicitamente V4.3.

Esito: audit completato sul perimetro `liquidity-plan/v1` con piano operativo, checklist, correzione mirata e regression suite. Corretto il caso in cui un asset immediato in valuta estera era marcato come bloccato ma restava nel bucket `emergency_reserve`: ora non finanzia la riserva senza conversione FX. Nessun follow-up bloccante per V4.3.

### V4.3 — Retirement decumulation strategies

**Stato:** `done`
**Tipo:** `functional`

Confrontare ordine dei prelievi, cash buffer, ribilanciamento, RITA, prestazioni pensionistiche e uso degli asset imponibili.

- Dipende da: V4.2 e V3.5e.
- Repository: `knowledge`, `rules`, `engine`.
- Output: `decumulation-strategy/v1`.
- Test: diverse età, sequenza rendimenti, longevità, RITA sì/no.
- Done quando: il sistema confronta più policy di decumulo con metriche nette.

Esito: completato con contratto e snapshot `decumulation-strategy/v1`, builder deterministico, CLI, fixture sintetiche e test. Il confronto usa policy esplicite, patrimonio, liquidity plan, pension income e RITA options opzionali; produce cashflow annui, metriche nette, shortfall, depletion age, warning, data gaps e ranking tecnico. I tassi netti sono dichiarati nell'input; non calcola fiscalita' normativa, rendimenti attesi, FX, ottimizzazioni o raccomandazioni.

### V4.3a — CLI and JSON input guides

**Stato:** `done`
**Tipo:** `docs`

Ridurre la compilazione manuale fragile documentando in modo operativo ogni JSON che l'utente deve compilare e una guida generale alle funzioni disponibili da CLI.

- Dipende da: V4.3.
- Repository: `engine`, `workspace`.
- Output: guide campo-per-campo per i JSON compilabili, draft/template mancanti, guida generale CLI per capability e ordine d'uso.
- Test: smoke CLI esistenti, verifica presenza guide per input JSON attivi, link/documentazione coerenti.
- Done quando: ogni input JSON richiesto da una capability CLI ha guida leggibile, esempio sintetico o draft/template, e la guida generale spiega quali comandi usare senza dover leggere il codice.

Esito: completato con guida generale CLI, mappa degli input JSON attivi, guida campo-per-campo per `decumulation-policy-set/v1`, draft sintetico workspace per decumulation, link in `docs/cli.md` e test documentale di copertura. Nessuna modifica a rules o knowledge; non sono stati introdotti calcoli, parser o dati reali.

### V4.3b — Interactive JSON input wizard

**Stato:** `done`
**Tipo:** `functional`

Ridurre ulteriormente la compilazione manuale dei JSON aggiungendo supporto CLI guidato da domande concrete, con salvataggio di draft validabili nel workspace.

- Dipende da: V4.3a.
- Repository: `engine`, `workspace`.
- Output: comandi CLI `prepare`/wizard per gli input JSON attivi piu' usati, partendo da `planning-goals`, `liquidity-plan-input` e `decumulation-policy-set`.
- Test: sessioni simulate stdin/stdout, overwrite sicuro, default non personali, validazione immediata del JSON generato, smoke CLI sui draft prodotti.
- Done quando: l'utente puo' creare o aggiornare i principali input JSON rispondendo a domande leggibili, senza aprire il file a mano salvo revisione finale, e senza copiare dati personali nel repository software.

Note di perimetro: il wizard deve porre domande deterministiche e salvare solo nel workspace privato. Non usa LLM per dedurre importi, aliquote, rendimenti, diritti pensionistici o raccomandazioni; valori incerti devono diventare `data_gaps`.

Esito: completato con wizard CLI per `planning-goals/v1`, `liquidity-plan-input/v1` e `decumulation-policy-set/v1`, scrittura sicura con `--overwrite`, validazione input immediata, test stdin/stdout simulati e documentazione CLI aggiornata. Nessuna modifica a rules o knowledge; non sono stati introdotti calcoli, parser, import automatici o dati reali.

### V4.4 — Pension contribution optimizer

**Stato:** `done`
**Tipo:** `functional`

Valutare contribuzioni future a previdenza complementare, TFR, deducibilità, liquidità persa e beneficio atteso.

- Dipende da: V3.5e e rule engine fiscale.
- Repository: `knowledge`, `rules`, `engine`.
- Output: `pension-contribution-options/v1`.
- Test: plafond, contributo datore, orizzonti e aliquote marginali.
- Done quando: ogni opzione mostra beneficio fiscale, costo opportunità e vincoli.

Esito: completato con knowledge note italiana, rule pack `it.pension-contribution-deduction.2026.v1`, contratto `pension-contribution-options/v1`, servizio deterministico, fixture sintetica, CLI build/demo, test su plafond ordinario, contributo datore, extra prima occupazione, TFR separato, liquidita' e anno non coperto. Il beneficio fiscale usa solo aliquota marginale dichiarata; non calcola IRPEF completa, rendimenti, matching contrattuale non dichiarato o raccomandazioni.

### V4.5 — Tax-aware investment planning

**Stato:** `done`
**Tipo:** `functional`

Confrontare regimi amministrato, gestito e dichiarativo, fiscal drag, minusvalenze, bollo/IVAFE e strumenti compatibili con gli obiettivi.

- Dipende da: V4.1 e tax rules V1.
- Repository: `knowledge`, `rules`, `engine`.
- Output: `tax-aware-portfolio/v1`.
- Test: 26%, 12,5% ove applicabile, bollo/IVAFE, costi e turnover.
- Done quando: il rendimento confrontato è netto di imposte e costi espliciti.

Esito: completato con knowledge note italiana, rule pack `it.tax-aware-investment.2026.v1`, contratto `tax-aware-portfolio/v1`, servizio deterministico, fixture sintetica, CLI build/demo e test su aliquota 26%, 12,5% documentata, bollo, IVAFE, costi, turnover, minusvalenze, regime incompatibile e anno non coperto. Il confronto usa solo rendimenti, costi, turnover, categorie fiscali e minusvalenze dichiarati nell'input; non calcola rendimenti attesi, fiscalita' estera completa, dichiarazione, PIR, cripto-attivita' o raccomandazioni.

### V4.6a — Italy–Spain pension tax classification

**Stato:** `done`
**Tipo:** `functional`

Classificare la pensione spagnola e gli altri flussi previdenziali transfrontalieri secondo residenza fiscale, natura della prestazione, soggetto erogatore e convenzione applicabile.

- Dipende da: V3.1, V3.5c–V3.5e e tax rules V1.
- Repository: `knowledge`, `rules`, `engine`.
- Output: `it-es-pension-tax-classification/v1` con potestà impositiva, ritenute attese, documenti e warning.
- Test: residente italiano, cambio di residenza, pensione pubblica/privata ove rilevante, classificazione incerta.
- Done quando: il sistema distingue il calcolo lordo previdenziale dal trattamento fiscale e non applica automaticamente una regola convenzionale senza classificazione.

Esito: completato con knowledge note Convenzione Italia-Spagna, rule pack `it-es.pension-tax-classification.2026.v1`, contratto `it-es-pension-tax-classification/v1`, servizio deterministico, fixture sintetiche, CLI classify/demo e test su residente italiano, cambio di residenza, pensione pubblica, pensione privata, eccezione di nazionalita', classificazione incerta e anno non coperto. Il sistema classifica potesta' impositiva e ritenuta attesa qualitativa senza calcolare netto, IRPEF, IRPF spagnola, crediti d'imposta o dichiarazione completa.

### V4.6b — Net Spanish pension for an Italian tax resident

**Stato:** `done`
**Tipo:** `functional`

Calcolare il flusso netto atteso della pensione spagnola per un residente fiscale italiano, includendo ritenute, imposte italiane, credito per imposte estere quando applicabile e periodicità.

- Dipende da: V4.6a e rule pack fiscali versionati per gli anni simulati.
- Repository: `knowledge`, `rules`, `engine`.
- Output: `spanish-pension-net-it-resident/v1` con lordo, imposte per Paese, credito, netto e confidence.
- Test: assenza/presenza di ritenuta spagnola, credito capiente/non capiente, cambio di aliquote, dato incompleto.
- Done quando: il pension income composer può usare un netto fiscale spiegabile senza confondere stima previdenziale e tassazione.

Esito: completato con knowledge note su pensione spagnola netta per residente italiano, rule pack `it.spanish-pension-net-it-resident.2026.v1`, contratto `spanish-pension-net-it-resident/v1`, servizio deterministico, fixture sintetiche, CLI build/demo e test su assenza/presenza di ritenuta spagnola, credito capiente, credito limitato da capienza dichiarata, ritenuta non definitiva, classificazione mancante e anno non coperto. Il servizio usa pension income, classificazione IT-ES, input fiscale esplicito e rule pack IRPEF nazionale; non calcola detrazioni, addizionali, acconti, rimborsi, imposte spagnole da aliquote spagnole o dichiarazione completa.

### V4.6c — Italy–Spain foreign asset monitoring

**Stato:** `done`
**Tipo:** `functional`

Integrare conti, fondi, piani pensionistici e immobili spagnoli con quadro RW, IVAFE/IVIE, tax events e relativi documenti.

- Dipende da: V3.1, V3.2, V4.5 e classificazione delle fonti spagnole.
- Repository: `knowledge`, `rules`, `engine`.
- Output: `it-es-foreign-assets/v1` con obblighi, esenzioni motivate, basi imponibili, warning e data gaps.
- Test: conto, fondi, piano pensionistico, immobile, intermediario residente/non residente e dato non classificato.
- Done quando: lo scenario mostra obblighi dichiarativi e impatti senza occultare titolarità e senza dedurre esenzioni non documentate.

Esito: completato con knowledge note RW/IVAFE/IVIE verificata il 2026-07-24, rule pack `it-es.foreign-asset-monitoring.2026.v2`, contratto `it-es-foreign-assets/v1`, servizio deterministico, fixture sintetica, CLI build/demo e test su conto, fondi, piano pensionistico, immobile, intermediario italiano documentato, dato non classificato, soglie aggregate conto, IVIE a mesi/soglia/credito, valuta, hash e anno non coperto. Il sistema espone obbligo RW, basi dichiarate, digest rule pack, regola applicata, IVAFE/IVIE, tax events, documenti richiesti, warning e gap; non prepara dichiarazioni, non assegna ogni codice RW, non calcola redditi esteri, credito estero non dichiarato, fiscalita' spagnola, cripto-attivita' o raccomandazioni.

### V4.6d — Italy–Spain cross-border dossier

**Stato:** `done`
**Tipo:** `functional`

Comporre pensione, attività finanziarie, monitoraggio e doppia imposizione in un dossier transfrontaliero unico e verificabile.

- Dipende da: V4.6a–V4.6c.
- Repository: `knowledge`, `rules`, `engine`, `workspace`.
- Output: `cross-border-it-es/v1` con flussi, obblighi, tax events, documenti mancanti, rischi e azioni operative.
- Test: pensione con asset spagnoli, sola pensione, soli asset, cambio di residenza e classificazione bloccante.
- Done quando: il piano distingue diritti previdenziali, tassazione del reddito e monitoraggio patrimoniale, indicando chiaramente le verifiche professionali richieste.

Esito: completato con contratto `cross-border-it-es/v1`, servizio deterministico, fixture sintetiche, CLI build/demo e test su pensione con asset, sola pensione, soli asset, cambio residenza, classificazione bloccante, gap annidati, `blocked_*`, mismatch di contesto, pension income senza contesto, provenance e vincolo privacy output. Il dossier compone flussi pensionistici, diritto/pro-rata UE, tassazione pensionistica, monitoraggio asset, tax events, documenti, rischi e azioni operative senza ricalcolare pensioni, imposte, crediti, valori patrimoniali, dichiarazioni o raccomandazioni.

### V4.6e — Italy–Spain EU pension entitlement and pro-rata estimate

**Stato:** `done`
**Tipo:** `functional`

Calcolare il diritto pensionistico spagnolo in regime UE e la quota spagnola pro-rata usando periodi assicurativi italiani e spagnoli datati, senza trasferire o fondere contributi.

- Dipende da: V3.5c, V3.5d e fonti istituzionali UE/Spagna aggiornate.
- Repository: `knowledge`, `rules`, `engine`, `workspace`.
- Output: `it-es-eu-pension-pro-rata/v1` con diritto autonomo/totalizzato, periodi non sovrapposti, importo teorico spagnolo, quota pro-rata, assunzioni, gap e provenance.
- Test: requisito autonomo, diritto per totalizzazione, sovrapposizioni IT-ES, requisito recente, dati futuri mancanti, quota pro-rata e regole/anno non coperti.
- Done quando: la stima distingue diritto e importo, non usa i periodi italiani come basi spagnole e produce un blocco esplicito quando mancano cronologia INPS o assunzioni future.

Motivazione di priorita': il simulatore pubblico spagnolo non consente la simulazione del caso misto dell'utente; questo incremento abilita l'uso corretto dei dati reali prima della composizione del dossier transfrontaliero.

Esito: completato con knowledge note UE/Spagna verificata il 2026-07-23, rule pack `eu.it-es.pension-coordination.2026.v2` con requisiti spagnoli 2026 e metodo art. 52, contratto `it-es-eu-pension-pro-rata/v1`, servizio deterministico, fixture sintetica, CLI prepare/build/demo, guide API/CLI/input e test. Il sistema distingue diritto autonomo spagnolo e diritto per totalizzazione, verifica validita' temporale del rule pack, eta' ordinaria, anchor del requisito recente e completezza delle assunzioni, conta le sovrapposizioni una sola volta nel denominatore UE, calcola la quota spagnola pro-rata solo da importo teorico esplicito con provenance spagnola e produce gap bloccanti se mancano precondizioni. Non calcola pensione INPS normativa, fiscalita', netto, P1 ufficiale, basi spagnole da periodi italiani o contribuzione futura non dichiarata.

### V4.6f — Code audit cadence and deterministic selection gate

**Stato:** `done`
**Tipo:** `audit`

Eseguire l'audit periodico dovuto dopo V4.2a e rendere la cadenza verificabile automaticamente prima della selezione di un incremento funzionale.

- Dipende da: V4.6e.
- Repository: `bootstrap`, `engine`.
- Output: audit checklist, classificazione esplicita degli incrementi e validatore deterministico della cadenza.
- Test: soglia 0-3, quarto incremento, quinto bloccato, reset dopo audit, metadati mancanti e selezione corrente incoerente.
- Done quando: i risultati dell'audit e gli eventuali follow-up sono tracciati, la regression e' verde e V4.7 non puo' essere selezionato quando un audit e' dovuto.

Esito: audit completato sul perimetro V4.3-V4.6e con checklist di cadenza, validatore deterministico `roadmap_audit.py`, classificazione esplicita `Tipo` degli incrementi, test mirati su soglie/metadati/selezione corrente e regression engine completa. La suite passa con 391 test e il comando `python family-office-engine/src/family_office_engine/governance/roadmap_audit.py` verifica la coerenza della roadmap attiva. Non sono emersi dati personali reali nei repository software, nuove dipendenze non dichiarate o blocker per V4.7. Follow-up non bloccante: valutare in un futuro audit se spezzare `tests/unit/test_validate.py`, che resta molto grande ma stabile.

### V4.6g — Multi-scenario Italy–Spain retirement assumptions and provenance

**Stato:** `done`
**Tipo:** `functional`

Introdurre uno scenario pensionistico personale versionato che renda espliciti contributi futuri, paese e data di pensionamento, residenza fiscale iniziale e successivi trasferimenti, senza dedurli da documenti storici o fixture sintetiche.

- Dipende da: V4.6a, V4.6b, V4.6d, V4.6e e V4.6f.
- Repository: `knowledge`, `rules`, `engine`, `workspace`.
- Output: `pension-scenario/v1` nel workspace, con provenance, data di conferma, scenari alternativi e riferimenti ai dossier IT-ES.
- Scenario base da supportare: nessun contributo spagnolo futuro, soli contributi italiani fino al pensionamento, pensionamento e residenza iniziale in Italia.
- Scenari alternativi da supportare: permanenza o trasferimento in Spagna dopo il pensionamento, con data di efficacia e residenza fiscale esplicite; nessuna residenza o contribuzione futura puo' essere inferita automaticamente.
- Vincoli: i dati sintetici/demo non possono essere selezionati come input di una simulazione personale; i contributi italiani restano distinti dalle basi spagnole; la totalizzazione UE resta limitata al diritto e al pro-rata previsti dalle regole applicabili.
- Test: scenario base Italia, trasferimento post-pensionamento in Spagna, data di trasferimento mancante, assunzioni contributive mancanti o contraddittorie, provenance incompleta, fixture sintetica rifiutata e composizione del dossier con piu' scenari.
- Done quando: il motore puo' confrontare combinazioni riproducibili senza confondere dati documentati, assunzioni future e risultati normativi/fiscali; ogni output identifica lo scenario selezionato e i relativi gap.

Motivazione di priorita': i documenti previdenziali spagnoli sono gia' presenti e importati; il limite attuale e' l'assenza di una fonte di verita' per le assunzioni future. Il dossier `cross-border-it-es/v1` esistente compone fonti a monte e non puo' fungere da scenario personale, in particolare quando una sua fonte e' una fixture sintetica.

Esito: completato con contratto `pension-scenario/v1`, servizio deterministico, fixture sintetiche baseline/trasferimento, CLI `planning pension-scenario build/demo`, integrazione opzionale nel dossier `cross-border-it-es/v1`, documentazione API/CLI/input/testing e test. Il sistema registra assunzioni future esplicite su contribuzione IT/ES, pensionamento, residenza iniziale e trasferimenti post-pensionamento, propaga scenario id/provenance/gap nel dossier e rifiuta fonti sintetiche per scenari o dossier personali. Non calcola pensioni, basi contributive, fiscalita', netto, diritto UE, pro-rata, trasferimenti amministrativi o raccomandazioni. Snapshot personali non rigenerati per assenza di `family-office-workspace/planning/pension-scenario.json`; la capability e' verificata con fixture sintetiche e CLI demo.

### V4.7 — Real-estate planning

**Stato:** `done`
**Tipo:** `functional`

Modellare immobile, proprietà, locazione, imposte, manutenzione, vendita, successione e liquidità.

- Dipende da: V3.2 e V3.4.
- Repository: `knowledge`, `rules`, `engine`.
- Output: `real-estate-plan/v1`.
- Test: locazione, vacancy, vendita, costi e titolarità del coniuge.
- Done quando: mantenere, vendere o trasferire l'immobile può essere confrontato su basi omogenee.

Esito: completato con contratto `real-estate-plan/v1`, servizio deterministico, fixture sintetica, CLI `planning real-estate build/demo`, documentazione API/CLI/input/testing e test. Il sistema confronta alternative `hold`, `rent` e `sell` usando valore immobile, quote di titolarita', costi, imposte dichiarate, canone, vacancy, prezzo di vendita e tempi di liquidita' espliciti; conserva provenance, gap e hash riproducibile. Le imposte immobiliari sono input espliciti o data gap, senza calcolo normativo. Non calcola successione, perizie, finanziamenti, FX, dichiarazioni, ottimizzazioni o raccomandazioni.

### V4.8 — Insurance and family protection

**Stato:** `done`
**Tipo:** `functional`

Valutare polizze vita, beneficiari, coperture, riscatti, costi, eventi morte/inabilità e fabbisogno familiare.

- Dipende da: V3.1–V3.3.
- Repository: `knowledge`, `rules`, `engine`.
- Output: `protection-gap/v1`.
- Test: beneficiario mancante, capitale insufficiente, polizza investimento vs protezione.
- Done quando: coperture e gap sono separati dalla mera valorizzazione patrimoniale.

Esito: completato con contratto `protection-gap/v1`, servizio deterministico, fixture sintetica, CLI `planning protection build/demo`, documentazione API/CLI/input/testing e test. Il sistema confronta fabbisogni familiari e polizze usando beneficiari, capitali assicurati, eventi coperti, premi, riscatti e provenance espliciti; separa polizze rischio, inabilita', miste e investimento, tracciando il valore di riscatto investimento senza contarlo come copertura rischio. Non calcola consulenza assicurativa, sanitaria, attuariale, legale, fiscale, underwriting, successione, ottimizzazioni o raccomandazioni.

### V4.8a — Spanish EU theoretical pension amount

**Stato:** `done`
**Tipo:** `functional`

Calcolare l'importo teorico spagnolo in regime UE quando la pensione spagnola autonoma non e' simulabile per carenza contributiva nazionale, ma il diritto puo' essere raggiunto per totalizzazione Italia-Spagna.

- Dipende da: V4.6e, V4.6g e V4.8.
- Repository: `knowledge`, `rules`, `engine`, `workspace`.
- Output: `spanish-eu-theoretical-pension/v1`, collegabile a `it-es-eu-pension-pro-rata/v1`.
- Test: nessun contributo spagnolo futuro, periodi IT usati solo per totalizzazione, basi ES reali, periodi esteri nella finestra base reguladora valorizzati con la base ES piu' vicina nel tempo aggiornata IPC, anno non coperto, importo teorico mancante e pro-rata alimentato automaticamente.
- Done quando: il caso misto IT-ES puo' produrre una pensione teorica spagnola lorda da regole UE/Spagna versionate senza usare LLM, senza fondere contributi italiani con basi spagnole e senza richiedere edit manuale del JSON.

Note di perimetro: seguire `knowledge -> rules -> tests -> engine`; servono fonti ufficiali UE/Spagna e rule pack che coprano l'anno di pensionamento simulato. Fuori perimetro: P1 ufficiale, domanda amministrativa, minimi/massimali non codificati, fiscalita', netto, rivalutazioni non versionate e raccomandazioni.

Esito: completato con knowledge note aggiornata su Reg. UE 883/2004 art. 52 e metodo spagnolo, rule pack `eu.es.spanish-eu-theoretical-pension.2026.v1`, contratto `spanish-eu-theoretical-pension/v1`, servizio deterministico, fixture sintetiche, CLI `planning spanish-eu-theoretical-pension build/demo`, opzione `--spanish-theoretical-snapshot` per alimentare `it-es-eu-pension-pro-rata/v1`, documentazione API/CLI/testing e test. Il sistema calcola l'importo teorico lordo da basi spagnole ufficiali e, per mesi UE esteri nella finestra, dalla base spagnola reale piu' vicina aggiornata tramite IPC versionato; se IPC, anno o basi non sono coperti produce data gaps. I periodi italiani restano usati solo come periodi UE totalizzati e non diventano basi contributive spagnole. Non calcola P1 ufficiale, fiscalita', netto, minimi/massimali, rivalutazioni non versionate, domanda amministrativa o raccomandazioni. Verifiche: 17 test mirati OK, smoke CLI teorico/pro-rata OK, regression unit engine 434 test OK.

### V4.8b — Code audit after Spanish EU theoretical pension

**Stato:** `done`
**Tipo:** `audit`

Audit periodico dovuto dopo quattro incrementi funzionali completati dall'ultimo audit V4.6f: V4.6g, V4.7, V4.8 e V4.8a.

- Dipende da: V4.8a.
- Repository: `engine`, `rules`, `knowledge`.
- Output: audit checklist e follow-up espliciti, se presenti.
- Test: suite pertinente e verifica allineamento knowledge, rule pack, schema, builder, CLI, fixture, docs e privacy.
- Done quando: eventuali debiti non corretti sono registrati e non bloccano o bloccano esplicitamente V4.9.

Esito: audit completato sul perimetro V4.6g-V4.8a con checklist su confini modulo, allineamento knowledge/rules/engine/docs, copertura test, CLI, data gaps, privacy, dipendenze e roadmap. Corretto un gap di copertura aggiungendo test CLI per `planning spanish-eu-theoretical-pension demo` e rimossa una helper pubblica non usata da `spanish_eu_theoretical_pension.py`. Verifiche: 44 test mirati OK sul perimetro audit, smoke CLI `pension-scenario`, `real-estate`, `protection`, `spanish-eu-theoretical-pension` e pro-rata da snapshot teorico OK, regression unit engine 435 test OK, `roadmap_audit.py` OK. Nessun blocker per V4.9. Follow-up non bloccante: valutare in un futuro audit se estrarre i subcomandi `planning` da `cli/main.py`, che resta grande ma coperto da test.

### V4.8c — Earliest work-exit date with internal INPS estimate

**Stato:** `done`
**Tipo:** `functional`

Trovare la prima data sostenibile, a partire da oggi, in cui il nucleo puo' smettere di lavorare secondo vincoli dichiarati, stimando internamente la pensione INPS lorda lungo una griglia di date candidate e componendola con quota spagnola pro-rata, pensione del coniuge, patrimonio, spese e opzioni ponte disponibili.

- Dipende da: V3.5e, V4.6e, V4.6g, V4.8a e V4.8b.
- Repository: `knowledge`, `rules`, `engine`, `workspace`.
- Output: `work-exit-feasibility/v1` con date candidate, prima data sostenibile, motivi di fallimento delle date precedenti, adulti del nucleo inclusi, `inps-theoretical-pension/v1` per candidato/persona e totale lordo separato per persona e fonte.
- Test: ricerca da oggi, candidata 2037 vs 2039, prima data trovata, nessuna data sostenibile, importo documentale INPS disponibile come benchmark, importo documentale mancante, pensione del coniuge presente/mancante, contributi italiani storici/proiettati, totalizzazione UE, Spagna pro-rata, anno futuro proiettivo e gap per regole mancanti.
- Done quando: l'utente puo' lanciare un comando CLI breve per trovare la prima data di uscita dal lavoro sostenibile del nucleo e ottenere importi lordi separati per persona e fonte, totale congiunto, vincoli verificati e spiegazione delle date scartate, senza edit manuale di JSON e senza usare LLM per calcoli previdenziali o finanziari.

Note di perimetro: seguire `knowledge -> rules -> tests -> engine`. Le date target esplicite, come 2037, sono solo candidate diagnostiche dentro la ricerca, non l'obiettivo primario. La pensione del coniuge deve entrare nel calcolo household come stream separato; se non e' disponibile o stimabile, lo snapshot deve produrre un gap esplicito invece di calcolare una data di uscita incompleta. Per anni futuri non osservabili usare solo assunzioni proiettive dichiarate nel rule pack, marcate come stima di pianificazione e non come legge futura ufficiale. La stima INPS interna deve restare distinta dalla proiezione documentale INPS importata; quando entrambe esistono, il sistema deve mostrare provenance e differenze invece di sovrascrivere il dato documentale. Fuori perimetro: certificazione ufficiale INPS, P1 ufficiale, netto fiscale non gia' disponibile, decorrenze amministrative non codificate, ricongiunzioni, riscatto laurea, opzione donna/APE/quote speciali e raccomandazioni.

Esito: completato con knowledge note INPS verificata il 2026-07-29, rule pack `it.inps-theoretical-pension.2026.v1`, contratto `work-exit-feasibility/v1`, componente `inps-theoretical-pension/v1`, servizio deterministico, fixture sintetiche, CLI `planning work-exit build/demo`, documentazione API/CLI/input/testing e test. Il sistema cerca date candidate, conserva importi lordi separati per persona e fonte, integra stima INPS interna, benchmark documentale INPS, quota spagnola pro-rata e pensione del coniuge, segnala data gaps bloccanti se manca la pensione del coniuge e spiega le date scartate. Le regole future sono marcate come proiezione di pianificazione, non come legge futura ufficiale. Non calcola netto fiscale, certificazioni INPS, P1, ricongiunzioni, riscatti, decorrenze amministrative, opzioni speciali o raccomandazioni. Verifiche: 5 test mirati OK, test CLI work-exit demo OK, smoke CLI `planning work-exit demo` OK (`first=2039-01-01`), regression unit engine 446 test OK, `roadmap_audit.py` OK.

### V4.9 — Succession and donation planning V2

**Stato:** `planned`
**Tipo:** `functional`

Estendere la V2 con quote di legittima, attribuzioni, liquidità per imposte, beneficiari, donazioni pregresse e alternative operative.

- Dipende da: V2.8, V3.2, V4.7-V4.8 e V4.8a.
- Repository: `knowledge`, `rules`, `engine`.
- Output: `estate-plan/v2` e scenari comparati.
- Test: coniuge e due figli, asset illiquidi, polizze, estero e dati incompleti.
- Done quando: il piano segnala conflitti civilistici e non propone schermi opachi.

### V4.10 — Strategy optimizer and implementation plan

**Stato:** `planned`
**Tipo:** `functional`

Combinare le opzioni V4 in pacchetti coerenti e produrre piano 90/180 giorni, costi, dipendenze, reversibilità e controlli.

- Dipende da: V4.2–V4.5, V4.6a–V4.6d e V4.7–V4.9.
- Repository: `engine`, `workspace`.
- Output: `wealth-strategy/v1`, tabella comparativa e checklist operativa.
- Test: vincoli, opzioni incompatibili, ranking, scenario avverso e gap bloccanti.
- Done quando: il sistema propone 2–4 alternative comparabili e motivate, non una soluzione unica opaca.

## Exit criteria V4

- Le alternative sono confrontate al netto di imposte e costi.
- Liquidità e protezione familiare sono vincoli espliciti.
- Cross-border, successione e beneficiari sono tracciati.
- La pensione spagnola è esposta separando importo previdenziale lordo, coordinamento UE, tassazione e netto per residente italiano.
- Ogni strategia include iter operativo, documenti, rischi e reversibilità.
- Le conclusioni ad alto impatto richiedono revisione professionale dichiarata.
