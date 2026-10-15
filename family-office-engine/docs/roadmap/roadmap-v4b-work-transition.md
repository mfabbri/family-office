# V4B Roadmap — Work Transition & Retirement Bridge

## Obiettivo

## Perimetro escluso dal freshness V4.14

Aggiornamento: il perimetro attivo è ora di cinque pack; il paragrafo seguente conserva il perimetro storico precedente all'aggiunta del pack eligibility e mantiene valide le tre esclusioni V4.4/V4.6a/V4.6b.

Non fanno parte dei quattro pack attivi né dei consumer coperti dal gate V4.14: `family-office-rules/italy/2026/pension-contribution-deduction.json` (consumer contribution-deduction V4.4), `family-office-rules/cross-border/it-es-pension-tax-classification.json` (consumer tax-classification V4.6a) e `family-office-rules/cross-border/spanish-pension-net-it-resident.json` (consumer gross-to-net tax V4.6b). Questi pack non devono essere dichiarati `fresh` o `stale` sulla base dell'audit V4.14; senza un audit dedicato lo stato resta non determinato. La loro governance richiede un proprio scope, un contratto di metadati delle fonti e una decisione separata su consumer e release gate.

La nota di stato precedente alla chiusura è storica: V4.14b e V4.14c sono ora `done` per il gate abilitante/freshness e il contratto gap-aware. V4.14 resta `blocked` e non viene approvata alcuna timeline.

Trasformare la capability V4.8c da ricerca di un hard stop annuale a un motore deterministico che trovi **quando ridurre il lavoro full-time, quanto lavorare part-time, quando cessare del tutto e come finanziare il ponte fino alle pensioni**, preservando liquidita', obiettivi familiari e un livello di rischio dichiarato.

Il motore deve produrre almeno tre date distinte: `earliest_full_time_exit_date`, `recommended_full_time_exit_date` e `full_work_exit_date`. Le decorrenze INPS, Seguridad Social e RITA sono stream separati e non coincidono per default con la cessazione.

## Perche' questa roadmap esiste

V4.8c `work-exit-feasibility/v1` e' utile come proof-of-capability ma non e' sufficiente per il golden use case:

- usa granularita' annuale;
- prima della candidate date assume implicitamente che il lavoro copra le spese e non modella il risparmio accumulato;
- non rappresenta fasi 100% → 80/60/50/40% → 0%;
- l'INPS interno viene calcolato sulla candidate date, senza un entitlement timeline separato dalla cessazione;
- non modella netto da lavoro e contribuzione futura come funzione dell'FTE;
- non compone in modo nativo RITA, redditi familiari e prelievi patrimoniali con start/end mensili;
- non applica sequence-of-returns risk a una transizione plurifase;
- puo' confrontare importi lordi pensionistici con fabbisogni di spesa senza un unico contratto gross/net household.

Per coerenza con la regola di non anticipazione dell'AI, V5.1 e V5.2 restano completati ma V5.3+ attendono questo gate.

## Invarianti di dominio

1. `full_time_exit_date`, `work_cessation_date`, `pension_entitlement_date` e `pension_payment_start_date` non sono sinonimi.
2. Il calcolo primario usa timeline mensile; gli aggregati annuali sono derivati.
3. Ogni fase lavorativa ha FTE, start/end e regola di compensazione dichiarata.
4. Il netto non e' ottenuto moltiplicando il netto full-time per l'FTE.
5. Contributi INPS, TFR e previdenza complementare variano con la fase lavorativa secondo regole versionate o gap espliciti.
6. Ogni pensione e RITA ha diritto, start/end, lordo/netto, tassazione e provenance separati dove disponibili.
7. Gli asset sono spendibili solo quando il liquidity plan li rende disponibili.
8. Il baseline deterministico precede lo stress stochastic; il Monte Carlo non maschera input mancanti.
9. Un dato mancante che puo' cambiare la data di uscita produce `blocked` o riduce confidence; non viene stimato dall'LLM.
10. Tutti gli optimizer devono spiegare candidate scartate, vincoli violati e sensitivity principali.

## Pipeline target

```text
workspace facts + freshness/provenance
        ↓
work-transition-readiness/v1
        ↓
work-transition-scenario/v1 (fasi FTE mensili)
        ↓
employment-income-projection/v1
        ↓
pension-entitlement-timeline/v1
        ↓
retirement-bridge-timeline/v1
        ↓
work-transition-simulation/v1
        ↓
work-transition-candidate-set/v1
        ↓
work-transition-optimizer/v1
        ↓
work-transition-plan/v1 + evidence
```

## Incrementi

### V4.11 — Work-transition data readiness and lineage gate

**Stato:** `done`
**Tipo:** `functional`

Riconciliare freshness, provenance e precedence degli snapshot necessari al golden use case prima di aggiungere nuovi calcoli.

- Dipende da: V4.2, V4.3, V4.6e, V4.8a, V4.8c.
- Repository: `engine`, `workspace`.
- Output: `work-transition-readiness/v1`.
- Test: payroll vs manual assumptions, spouse income, spese, liquidita', asset duplicati, gross/net mismatch, snapshot stale, path multipiattaforma.
- Done quando: ogni input necessario e' selezionato o bloccato con lineage e freshness espliciti.

### V4.12 — Monthly work-transition scenario contract

**Stato:** `done`
**Tipo:** `functional`

Definire fasi lavorative mensili per ogni adulto: full-time, uno o piu' livelli part-time, cessazione e opzionale rientro.

- Dipende da: V4.11.
- Repository: `engine`, `workspace`.
- Output: `work-transition-scenario/v1`.
- Campi minimi: persona, start/end, FTE, status, compensation policy, contribuzione/benefit policy reference, vincoli contrattuali dichiarati.
- Test: 100→60→0, fasi sovrapposte, gap temporali, durata zero, due adulti, date invalide.
- Done quando: `full_time_exit_date` e `work_cessation_date` sono derivabili senza assumere pensionamento.

### V4.13 — Italian employment net-income and contribution projection

**Stato:** `done`
**Tipo:** `functional`

**Esito review normativa (2026-10-11): GO limitato.** IRPEF riusabile solo come imposta nazionale lorda su imponibile annuo esplicito; aliquota INPS di computo riusabile solo per montante teorico su base/gestione dichiarate, non come trattenuta dipendente. TFR e Fon.Te solo pass-through di importi osservati/dichiarati. Netto payroll completo, contributi del lavoratore, detrazioni/addizionali, maturazione TFR e matching Fon.Te devono restare `null` con `data_gaps` bloccanti finché non esistono fonti e rule pack adeguati.

**Esito gate indipendente post-implementazione: GO limitato, non chiude V4.13.** Il contratto machine-only resta bloccato e non alimenta l'optimizer; IRPEF lavoro-only e' solo illustrativa con gap per gli altri imponibili. Nel gate iniziale mancava la data di verifica della fonte IRPEF, poi corretta con il versioning indicato sotto. Il montante INPS resta null finche' gestione, periodicita' e precisione non sono supportate.

**Correzione IRPEF 2026 e gate indipendente (2026-10-11): GO limitato.** La L. 199/2025, art. 1 comma 3 sostituisce il 35% con il 33% dal periodo d'imposta 2026. Il pack 2026 v2 e il consumer cross-border sono aggiornati; il pack storico 2025 conserva 23%/35%/43% e `retrieved_on`. Sample e dossier cross-border sono allineati; il consumer rifiuta un ID IRPEF caricato diverso da quello dichiarato. La suite focalizzata passa 131/131 test. Questo gate non sblocca l'IRPEF lavoro-only come imposta totale né il montante INPS mensile.

**Chiusura V4.13 (2026-10-11):** i criteri di uscita sono soddisfatti: il journey CLI raccoglie fasi e basi esplicite senza chiedere date pensionistiche/candidate; ogni componente supportata è tracciabile e ogni componente non supportata resta `null` con `data_gaps` bloccanti; nessun netto è derivato da `net_full_time × FTE`. I gap per payroll netto, contributi dipendente, detrazioni/addizionali, TFR futuro, matching Fon.Te e precisione/periodicità INPS sono limiti deliberati del contratto, non calcoli impliciti. V4.14 può iniziare, ma non deve trasformare questi gap in importi.

**Stato CLI parziale:** `fo planning work-transition plan` crea/riprende il manifest nel workspace, guida il binding esplicito delle fonti e raccoglie fasi FTE e basi mensili dichiarate con salvataggio progressivo. Quando la readiness lo consente, orchestra scenario V4.12 e proiezione V4.13, mantenendo provenance e gap bloccanti. Non chiede date pensionistiche o candidate dell'optimizer e non calcola una data sostenibile. I prossimi passi operativi e i rispettivi gate sono registrati in `docs/current-next-increment.md` e `docs/roadmap/work-transition-implementation-plan.md`.

Calcolare per fase il cashflow da lavoro e l'accumulo previdenziale usando rule pack italiani versionati e dati dichiarati/observed.

- Dipende da: V4.12 e rule pack fiscali/contributivi disponibili.
- Repository: `knowledge`, `rules`, `engine`.
- Output: `employment-income-projection/v1`.
- Contratto e limiti: `docs/employment-income-projection.md` (contratto interno; il percorso CLI question-first è introdotto progressivamente, il JSON manuale non è il flusso operativo utente).
- Include dove supportato: lordo, contributi lavoratore, imponibile, IRPEF/addizionali, netto, TFR, Fon.Te/previdenza complementare lavoratore e datore.
- Test: FTE 100/60/40, mensilita' aggiuntive, soglie fiscali, contributi, part-time non lineare sul netto, dato documentale vs proiezione.
- Prossime attività: verificare ogni ulteriore trattamento tramite Knowledge → Rules → Tests → Engine; mantenere i calcoli non supportati come gap bloccanti.
- Done quando: ogni fase produce netto e contribuzione tracciabili oppure gap; nessun `net_full_time × FTE`; il journey CLI raccoglie gli input ammessi senza chiedere date di pensionamento o candidate di cessazione.

### V4.14 — Entitlement-driven pension timeline IT/ES/EU

**Stato:** `blocked`
**Tipo:** `functional`

**Gate normativo indipendente (2026-10-11): NO-GO.** Il contratto completo non è implementabile finché non sono corretti il perimetro italiano per gestione e periodo, la versione delle fonti/rules spagnole, il coordinamento UE per gli artt. 50, 52, 56 e 57 del Reg. 883/2004 e la distinzione tra eleggibilità, requisiti computazionalmente soddisfatti, riconoscimento amministrativo, decorrenza economica e primo pagamento. V4.14b e V4.14c sono prerequisiti abilitanti; l'assenza di regole supportate deve restare `null` con `data_gaps`.

Ricalcolare pensione e decorrenze in funzione della carriera generata dallo scenario, mantenendo separati diritto, decorrenza e importo.

- Dipende da: V4.13, V4.6e, V4.8a, V4.14b, V4.14c.
- Repository: `knowledge`, `rules`, `engine`.
- Output: `pension-entitlement-timeline/v1`.
- Include: stima INPS interna per scenario, benchmark INPS documentale, entitlement/eligibility rules, Spagna teorica e pro-rata UE, stream del coniuge.
- Test: cessazione prima della pensione, part-time che cambia montante, date diritto diverse dalle date pagamento, totalizzazione UE, regole future non consolidate, spouse gap.
- Done quando: nessuno stream pensionistico inizia per default alla `work_cessation_date`.

### V4.14b — Pension normative remediation and source freshness gate

**Stato:** `done`
**Tipo:** `functional`

**Review post-implementazione (2026-10-11): GO limitato dopo le correzioni.** Cessazione sempre verificata/source-bound; evidenze contributive e di importo applicabili alla data/anno candidato; ramo alternativo a 71 anni con ignoti restituisce gap; soglie, coorte e gestioni provengono dal pack. Ulteriore hardening rifiuta schema, intervalli, periodi delle disposizioni, schedule o soglie malformate. I test relativi passano 78/78. La copertura freshness è di cinque pack e sette consumer diretti (sei servizi pensionistici più proiezione del reddito). Il GO resta limitato: V4.14 è `blocked` e nessuna timeline è approvata.

**GO normativo limitato (2026-10-11):** è approvata soltanto una regola deterministica di sola eligibility per il percorso ordinario di vecchiaia di dipendenti FPLD/AGO, con una sola gestione/ambito confermato e requisiti soddisfatti nel 2026-2028. Per la coorte con prima contribuzione anteriore al 1996: età 67 / 67a1m / 67a3m e 20 anni qualificanti. Per la prima contribuzione dal 1996: le stesse età e 20 anni qualificanti più pensione mensile documentata almeno pari all'assegno sociale mensile applicabile documentato, oppure età 71 / 71a1m / 71a3m e 5 anni di contribuzione effettiva, esclusa quella figurativa. L'evidenza source-bound comprende DOB, coorte, categoria di gestione/rapporto confermata, storia contributiva datata o totali validati, importo e soglia documentati per il percorso contributivo ventennale e cessazione documentata. Sconosciuti, fuori periodo, eccezioni, più gestioni o aggregazioni estere/UE producono `null` con `data_gaps`, mai un esito negativo.

Nota storica antecedente alla chiusura: il dedicated eligibility pack e il service erano in implementazione. Ora sono verificati con GO limitato post-fix; non calcolano importi né date di riconoscimento, decorrenza economica o primo pagamento. Il pack importi esistente e il consumer legacy `work_exit_feasibility` restano separati e non modificati. V4.14 resta `blocked`.

Nota storica precedente alla chiusura: il gate indipendente sul fix temporale e la review scoped della freshness avevano dato GO limitato; il contratto gap-aware è stato ora formalizzato senza approvare la timeline V4.14.

Rimuovere il NO-GO normativo con il perimetro più ristretto sostenuto da fonti primarie, regole versionate, test sintetici e contratto timeline gap-aware.

**Avanzamento 2026-10-11 (storico, prima della chiusura):** fonti Knowledge IT/ES/UE ricontrollate; il rule pack UE è v2, limitato al 2026, con riferimenti a Reg. 883/2004 e 987/2009; il pack pensione ordinaria ES v2 dichiara copertura fino al 2036. Overlap IT/ES non classificati e casi art. 57 sotto un anno restano gap fail-closed; `insured/equivalent` è solo input dichiarato, non prova né conclusione legale. La review indipendente ha rilevato che, pur con dossier `partial` e gap per date fuori validità, gli stati delle prestazioni nazionali potevano restare positivi. Il consumer ora declassa entrambi a `not_assessed_rule_pack_period` quando la data è mancante, invalida o fuori periodo; il reviewer ha dato GO limitato su questo fix, senza blocker evidente nel diff. Il reviewer non ha rieseguito i test; il parent ha verificato 58 test mirati, incluso il blocco del 2037 e la regressione di stato. La freshness runtime V4.14c ha poi ricevuto GO limitato scoped dopo 69 test parent e smoke release gate. In seguito, V4.14b e V4.14c sono passati a `done`; il GO limitato non revoca il NO-GO sulla timeline V4.14.

**Freshness runtime iniziale (2026-10-11, storico):** il primo rilascio copriva quattro pack e sei consumer; dopo l'aggiunta del pack eligibility italiana, il perimetro corrente è cinque pack e sette consumer diretti, audit CLI 5/5 fresh. Il gate richiede fonti HTTPS ufficiali, provenance e review non oltre 90 giorni, distingue le date di review dalla validità legale e non usa la rete. La CLI espone audit riproducibile e wizard di conferma umana; `fo release check` lo esegue anche con unit regression disattivata e rende il suo fallimento bloccante. I tre pack contributivo/tax dei percorsi V4.4/V4.6a/V4.6b restano esclusi dal gate V4.14; richiedono governance separata. V4.14b e V4.14c sono `done`; la timeline V4.14 resta `blocked`.

**Chiusura V4.14b (2026-10-11):** completati il rule pack e lo screening source-bound per la sola eligibility ordinaria IT approvata, il gate freshness su cinque pack/sette consumer, la checklist di review periodica e il contratto gap-aware `schemas/pension-entitlement-timeline.schema.json`. Reviewer indipendente: GO limitato sul perimetro eligibility dopo i fix. Schema e test impediscono di rappresentare un evento non valutato come data supportata; nessun calcolo di timeline o importo è aggiunto. 81 test correlati passano, audit CLI 5/5 fresh senza rete, roadmap/schema planner/guardrail/diff-check validi. V4.14b è `done`; V4.14 resta `blocked` dal NO-GO sul contratto completo e non riceve alcun GO per importi, stream o timeline.

- Dipende da: V4.13.
- Repository: `knowledge`, `rules`, `engine`.
- Include: Italia limitata a regimi e requisiti documentati; regole spagnole versionate per periodo legale; coordinamento UE corretto secondo Reg. 883/2004 artt. 50, 52, 56 e 57 e fonti attuative necessarie; campi separati `eligibility_date`, `requirements_met_date`, `official_recognition_date`, `economic_effective_date` e `first_cash_payment_date`.
- Fonti: registrare URL ufficiale, autorità, giurisdizione, atto/articolo, `retrieved_on`, validità giuridica della disposizione e validità del rule pack in campi distinti. `valid_to: null` non va usato per fingere copertura futura non verificata.
- Regole non consolidate, periodi UE non classificabili, gestione INPS sconosciuta, riconoscimento amministrativo o primo accredito non derivabili producono `null` e `data_gaps`; nessun benchmark documentale viene sovrascritto.
- Test: versioni/periodi; requisiti IT per i soli casi approvati; ES 2026 e periodi futuri; totalizzazione e calcolo teorico/pro-rata separati; art. 57 nei diversi rami; cessazione prima della pensione; date giornaliere e spouse gap.
- Done quando: il reviewer normativo indipendente approva fonti, periodi, gestione e limiti; i test dimostrano che nessun diritto, importo o data non supportati viene emesso.

### V4.14c — Quarterly pension-source freshness audit

**Stato:** `done`
**Tipo:** `audit`

Il controllo e il release-gate sono implementati e hanno ricevuto GO limitato scoped. V4.14c è `done`; il ciclo operativo è ricorrente e la prossima review è dovuta entro 2027-01-09, oppure prima se una modifica ufficiale la richiede.

Impedire che una regola pensionistica non riesaminata venga riutilizzata come se fosse corrente. Questo audit ricorre almeno ogni 90 giorni; una modifica ufficiale rilevante anticipa immediatamente la review.

- Dipende da: V4.14b.
- Repository: `bootstrap`, `rules`, `engine`.
- Output: audit locale deterministico delle fonti pensionistiche attive, invocato prima dei consumer pensionistici e dal gate di release/test. Invocazione consumer e check esplicito nel release gate sono implementati e testati.
- Ogni fonte attiva deve avere `reviewed_on`, `next_review_due`, URL/provenance, giurisdizione e riferimento alla disposizione; `reviewed_on`/`next_review_due` misurano la freshness e non sostituiscono `valid_from`/`valid_to` legali o del pack.
- L'audit controlla i metadati senza rete: se il termine è superato o la provenance manca, blocca l'uso della regola e produce `normative_source_review_overdue` o gap equivalente. Non simula un controllo automatico dei siti ufficiali.
- Trigger immediato: pubblicazione o efficacia di legge, decreto, circolare, aggiornamento ufficiale della fonte o correzione del rule pack.
- Test: source fresh, prossima alla scadenza, overdue, missing provenance, fonte sostituita, validità futura e calendario trimestrale; fixture esclusivamente sintetiche.
- Done quando: comando, consumer e release gate falliscono in modo chiuso sulle regole stale; la checklist operativa indica responsabile, data review e scadenza successiva; il ciclo è ripetibile trimestralmente senza riaprire il contratto e il reviewer indipendente approva il perimetro freshness.

### V4.14d — Event-level pension timeline normative support matrix

**Stato:** `done`
**Tipo:** `audit`

V4.14 resta `blocked` dopo il NO-GO sul contratto completo. Questo micro-incremento documentale isola i cinque eventi del contratto e, per IT/ES/UE, distingue atti normativi vincolanti da fonti amministrative ufficiali e prove individuali; registra l'ambito temporale, le evidenze necessarie e i limiti di derivabilità. La matrice Knowledge ha ricevuto GO normativo limitato; il periodo italiano dopo 2026-09-09 e gli eventi individuali non dimostrati restano gap espliciti.

- Dipende da: V4.14b e V4.14c.
- Repository: `knowledge`, `engine` (solo contratti/documentazione), `bootstrap` (planner).
- Output: matrice verificata per `eligibility_date`, `requirements_met_date`, `official_recognition_date`, `economic_effective_date`, `first_cash_payment_date`.
- Done quando: atti e periodi sono verificati per ogni affermazione, distinti dalle fonti amministrative; review indipendente approva solo il perimetro effettivamente supportato e conferma i gap; V4.14 rimane bloccata per ogni regola o evento non approvato. **Verificato:** GO limitato post-fix; nessun calcolo o regola aggiunti.
- Stop: nessun rule pack, codice engine, importo, data individuale o stream è implementato in questo audit.

### V4.14e — Italian pension-law validity checkpoint for 2026-2028

**Stato:** `done`
**Tipo:** `audit`

Verificare il gap temporale italiano lasciato dalla versione Normattiva consultata da V4.14d con vigenza restituita al 2026-09-09. Il perimetro è esclusivamente la validità delle fonti per l'eligibility ordinaria già approvata in V4.14b: dipendenti FPLD/AGO, gestione singola confermata, requisiti nel 2026-2028. Nessuna estensione alle deroghe, ai profili speciali o alla timeline completa.

- Fonte legislativa primaria: L. 30 dicembre 2025, n. 199, art. 1, comma 185. Atto attuativo vincolante: decreto direttoriale MEF-Lavoro 19 dicembre 2025, pubblicato in G.U. n. 301 del 30 dicembre 2025; non classificarlo come fonte legislativa primaria.
- Fonte amministrativa esplicativa: circolare INPS n. 28 del 16 marzo 2026; la circolare non sostituisce le fonti normative.
- Scope: confrontare le età già codificate e l'alternativa contributiva post-1995 con le finestre 2026-2028; considerare le deroghe solo per confermare che restano fuori dal rule pack.
- Output: nota Knowledge aggiornata con fonti, date, periodo, distinzione tra legge, atto attuativo e guidance, limiti della snapshot Normattiva, gap di tracciabilità storica per il valore base 71 e provenance INPS-only del rule pack; review indipendente.
- Stop: nessun cambiamento a rules/engine, nessun calcolo individuale e nessuno sblocco di V4.14. Se le fonti non sostengono il perimetro esistente, mantenere gap/NO-GO e aprire un incremento Knowledge → Rules → Tests → Engine solo dopo il gate.
- Done quando: reviewer normativo indipendente conferma la corretta gerarchia delle fonti e approva solo le affermazioni supportate, confermando i gap residui; verifiche di governance passano. **Verificato:** GO limitato solo per la documentazione della gerarchia delle fonti e dei gap; non certifica la provenance del rule pack.

### V4.14f — Italian eligibility rule-pack legal provenance traceability

**Stato:** `done`
**Tipo:** `audit`

Ricostruire e sottoporre a review la catena delle fonti legislative e degli atti attuativi che sostiene i requisiti annuali del rule pack `it.inps-old-age-eligibility.2026-2028.v2`, in particolare l'età base di 71 anni e gli adeguamenti fino al 2028. Aggiornare Knowledge e provenance senza alterare valori o scope; aggiungere regressioni sintetiche per validità temporale e versione del pack. Verificare fail-closed dei consumer su fonti/periodi mancanti o duplicati.

- Dipende da: V4.14b e V4.14e.
- Repository: `knowledge`, `rules`, `engine` (solo se richiesto da regressioni fail-closed).
- Stop: nessuna estensione a gestioni/profili speciali; nessun calcolo individuale o timeline; se la catena normativa non è documentabile, mantenere il pack non certificato e il gap.
- Done quando: fonti ufficiali e atti/periodi sono revisionati indipendentemente; riferimenti source-bound del pack e regressioni sintetiche sono verificati; nessun esito positivo deriva da provenance mancante o profilo non classificato. V4.14 resta `blocked`.

**Chiusura 2026-10-13 — GO limitato:** due review post-implementazione hanno restituito NO-GO circoscritti; i finding sono stati corretti. Nel terzo tentativo il reviewer ha verificato i binding schedule, gli incrementi cumulativi, i periodi aperti, il ruolo INPS, i mutation test e ha rettificato il finding parser dopo il riscontro del test `ItalianOldAgeEligibilityError`. La suite mirata passa 22/22; roadmap audit, planner schema, guardrail, compilazione e diff-check passano. Il GO riguarda esclusivamente provenance e screening ordinario IT FPLD/AGO a data candidata; V4.14 resta `blocked` e nessuna timeline/importo/data individuale è approvata.

### V4.14g — Primo mese di eligibility path-specific (post-1995, 71 anni/5 effettivi)

**Stato:** `done`
**Esito review:** GO limitato post-implementazione, tentativo 3/3.
**Tipo:** `functional`

Il reviewer normativo ha dato GO limitato al contratto di ricerca del primo mese per il solo percorso contributivo alternativo post-1995: requisito d'età 71/71a1m/71a3m e cinque anni di contribuzione effettiva (figurativi esclusi), dipendenti FPLD/AGO, gestione singola confermata, anni 2026-2028. Il risultato non è la prima data complessiva, né una decorrenza o un pagamento.

- Dipende da: V4.14b, V4.14e e V4.14f.
- Repository: `knowledge`, `rules`, `engine` (implementazione solo dopo gate normativo positivo).
- Review: gate pre-implementazione NO-GO per la prima data complessiva e GO limitato per il ramo path-specific; review post-implementazione ciclo 1/3 e 2/3 NO-GO corretti, 3/3 GO limitato.
- Evidenza: storia mensile completa e source-bound degli accrediti, unità/tipo originali, data di nascita e coorte verificate, gestione/categoria/assenza eccezioni confermate, cessazione documentata. Non inferire accrediti successivi all'ultimo periodo osservato.
- Output: primo mese supportato del solo percorso alternativo 71 anni/5 anni effettivi. Se input mensile non sostiene giorno esatto, non emettere data giornaliera.
- Stop: periodi mancanti/sovrapposti, unità o contribuzione effettiva ambigue, cessazione non verificata, fonte scaduta, pack fuori validità o profilo non coperto producono `null` + `data_gaps`; nessuna estensione a prima data complessiva, ramo 20 anni/importi, ES/UE, riconoscimento, decorrenza o pagamento. V4.14 resta `blocked`.
- Done quando: ricerca deterministica path-specific e regressioni fail-closed passano; il reviewer post-implementazione conferma il solo perimetro approvato. **Completato:** GO limitato al consumer mensile path-specific.
- Esito 2026-10-13: i tentativi post-implementazione 1/3 e 2/3 hanno dato NO-GO limitati; i finding su cronologia coorte, unità duplicate, coverage profilo oltre la prova e date ISO malformate sono stati corretti. 19 test eligibility + 11 freshness passano. Tentativo 3/3: GO limitato, nessun blocker sul diff. Prima data complessiva, ramo 20 anni/importo, riconoscimento/decorrenza/pagamento e timeline V4.14 restano fuori scope; V4.14 resta `blocked`.

### V4.14h — Italian post-1995 20-year contribution plus threshold eligibility path

**Stato:** `done`
**Tipo:** `functional`

Micro-incremento abilitante indicato dal decision log dopo V4.14g. Deve valutare e, solo dopo un GO normativo indipendente, implementare il ramo post-1995 con 20 anni qualificanti e importo pensionistico mensile documentato almeno pari alla soglia applicabile. Il risultato sarà il primo mese supportato di questo solo ramo, non la prima data complessiva.

- Dipende da: V4.14b, V4.14e, V4.14f e V4.14g.
- Repository: `knowledge`, `rules`, `engine`.
- Evidenze obbligatorie: coorte e gestione FPLD/AGO confermate, storia contributiva mensile completa e source-bound, importo pensionistico documentato da prova separata valida nel mese candidato, soglia annuale dal pack, cessazione verificata entro il mese candidato, pack fresco e nel periodo 2026-2028.
- Fail-closed: storia incompleta, soglia/importo/coorte/gestione non provati, date malformate, freshness scaduta o profilo fuori scope producono `null` + `data_gaps`; nessuna proiezione futura.
- Fuori scope: prima data complessiva, ramo 71/5, profili speciali, altre gestioni, ES/UE, importi calcolati, riconoscimento, decorrenza e pagamento. V4.14 resta `blocked`.
- Gate implementazione: consumer path-specific e regressioni eligibility 26/26; GO normativo limitato pre e post-implementazione.
- Gate completamento: **superato il 2026-10-14**; suite completa engine 762/762, 0 failure, 0 errori, 0 skip. La remediation ha mantenuto i guardrail fail-closed e non ha modificato soglie, formule o rule pack.
- **Enabling slice completata:** GO normativo limitato del 2026-10-14 su binding annuale 2026, gap 2027-2028, scope FPLD e provenance separate.
- **Gate pre-implementazione mensile:** GO limitato del 2026-10-14 dopo un NO-GO contrattuale risolto. Valutare i requisiti a fine mese; prova mensile source-bound separata per i 20 anni e per l'importo; fermarsi al primo candidato age+20 con soglia annuale non supportata, senza saltare 2027-2028. Nessuno sblocco della timeline V4.14.
- **Verifica post-implementazione:** GO limitato per `search_first_post_1996_ordinary_threshold_eligibility_month`; 26 test eligibility passano, incluso il consumer esistente 71/5. V4.14, prima data complessiva e riconoscimento/decorrenza/pagamento restano fuori scope.
- **Chiusura suite 2026-10-14:** 156 test mirati e l'intera suite 762/762 passano con 0/0/0; `jsonschema` 4.26.0 è installato nel venv e dichiarato nell'extra `test`. La review normativa ha dato GO limitato alle correzioni di fixture/aspettative ES/UE, senza cambi a regole o calcoli. V4.14h è `done`; V4.14 timeline resta `blocked`.

### V4.14i — EU Article 57 under-one-year evidence and contract audit

**Stato:** `done`
**Esito:** GO limitato documentale.
**Tipo:** `docs`

Micro-incremento documentale abilitante derivato dal NO-GO della timeline V4.14. Verificare esclusivamente le fonti/versioni ufficiali e le condizioni del coordinamento UE per i periodi inferiori a un anno ai sensi dell'art. 57 del Reg. 883/2004; aggiornare la nota Knowledge/il contratto descrittivo solo quanto sostenuto dalle fonti e registrare review normativa indipendente GO/NO-GO limitata.

**Esito finale 2026-10-15:** dopo due NO-GO circoscritti corretti nella nota Knowledge, la review normativa indipendente ha emesso GO limitato per le sole affermazioni documentali su art. 57(2)-(3), raccordo con art. 52 e regime transitorio art. 94(1). Il reviewer richiede di esplicitare art. 52(4)(i)-(ii), incluse condizioni anti-cumulo artt. 54-55 e l'eccezione art. 55(2), prima di qualsiasi uso eseguibile: registrato come gap futuro, non incluso nell'approvazione. Suite engine completa 762/762, 0 failure, 0 errori, 0 skip. V4.14i `completed` solo per questo audit; nessuna approvazione Rules/Engine, calcoli, date o timeline. V4.14 resta `blocked` e V4.14a non selezionabile.

- Dipende da: V4.14b, V4.14c e V4.14d.
- Repository: `family-office-knowledge`, `family-office-engine` (sola documentazione/roadmap).
- Evidenze: giurisdizione, articoli e versioni applicabili di Reg. 883/2004 e Reg. 987/2009; condizioni, istituzione competente e dati/prove necessari per valutare i periodi inferiori a un anno; limiti temporali e fonti non consolidate.
- Output: nota source-bound con perimetro supportato, casi non valutabili e `data_gaps`; esito di review indipendente limitato agli artefatti esaminati.
- Fuori scope: modifica di rule pack, test/engine, calcolo di entitlement o pro-rata, confronto delle date IT/ES, prima data complessiva, riconoscimento, decorrenza economica e primo pagamento. V4.14 resta `blocked`.
- Done quando: ogni affermazione è collegata alla fonte ufficiale e al periodo applicabile, i casi non coperti restano espliciti, il reviewer emette un GO/NO-GO limitato e passano i controlli documentali/governance. Un GO non autorizza implementazione; l'eventuale slice Rules → Tests → Engine richiede un successivo task envelope e routing normative/implementation.

### V4.14j — Art. 52(4)(i)-(ii) conditions audit

**Stato:** `done`
**Tipo:** `docs`

Slice documentale abilitante selezionata dopo il GO limitato V4.14i, perché il reviewer ha richiesto di esplicitare le condizioni dell'art. 52(4)(i)-(ii) prima di qualsiasi uso eseguibile del coordinamento UE.

- Dipende da: V4.14i, V4.14b e V4.14c.
- Repository: `family-office-knowledge`, `family-office-engine` (sola documentazione/roadmap), `family-office-bootstrap` (planner).
- Piano: verificare il testo ufficiale applicabile del Reg. 883/2004 art. 52(4)(i)-(iii), artt. 54-55 e 57; distinguere la condizione di inclusione in Allegato VIII parte 1 dal test anti-cumulo e dall'eccezione art. 55(2); aggiornare la nota Knowledge solo quanto sostenuto; ottenere review normativa indipendente.
- Fuori scope: modifica di rules/test/engine, calcoli o timeline pensionistica; importi e quote pro-rata individuali; dati del workspace.
- Done quando: condizioni e fatti necessari sono documentati con fonte/versione/periodo, i casi non classificati restano `data_gaps`, il reviewer emette GO/NO-GO limitato e passano i controlli documentali/governance. Nessun GO abilita automaticamente il runtime: V4.14 resta `blocked` fino al gate completo.

**Esito finale 2026-10-15:** reviewer normativo indipendente GO limitato al diff Knowledge. La nota riporta correttamente le condizioni cumulative dell'art. 52(4)(i)-(iii), il rinvio alle regole anti-cumulo degli artt. 54-55 e l'eccezione specifica dell'art. 55(2), distinguendo Allegato VIII parte 1 da parte 2 e collegando art. 57. Il riscontro su Italia/Spagna è limitato al consolidato 2019 e non sostituisce la classificazione di uno schema concreto né l'aggiornamento degli atti. La suite completa passa 762/762, 0 failure, 0 errori, 0 skip. Nessuna approvazione di Rules, Engine, calcoli o timeline; V4.14 resta `blocked`.

### V4.14k — First overall pension month contract reassessment

**Stato:** `done`
**Tipo:** `audit`

Micro-incremento abilitante successivo ai GO documentali V4.14i/j. Richiedere a reviewer normativo indipendente di riesaminare i precedenti NO-GO e valutare se un contratto source-bound per il primo mese complessivo di eligibility IT/ES/UE sia definibile sulle fonti primarie e versioni applicabili.

- Dipende da: V4.14b, V4.14c, V4.14i e V4.14j.
- Repository in lettura: `family-office-knowledge`, `family-office-rules`, `family-office-engine`; planner/governance in scrittura.
- Verificare: soglie e percorsi nazionali IT/ES per il periodo coperto; totalizzazione e calcolo teorico/pro-rata secondo il coordinamento UE; condizioni dell'art. 52(4), anti-cumulo artt. 54-55 e art. 57; distinzione tra eligibility, riconoscimento, decorrenza economica e pagamento; freshness/validità dei rule pack e prove individuali richieste.
- Output: GO/NO-GO indipendente limitato al contratto, requisiti/condizioni implementabili collegati a fonte e periodo, data_gaps e proposta del successivo slice Knowledge → Rules → Tests → Engine.
- Fuori scope: calcolo su persone reali, accesso a `family-office-workspace/`, modifiche Rules/Tests/Engine, date individuali, riconoscimento, decorrenza o pagamento.
- Done quando: il reviewer dà un esito esplicito supportato da fonti primarie correnti e il piano registra i gate successivi senza trasformare il GO in una data o in un'approvazione runtime. In caso di NO-GO, creare il più piccolo incremento abilitante e mantenere V4.14 `blocked`.

**Esito 2026-10-15:** NO-GO per restituire il primo mese complessivo IT/ES/UE con i consumer attuali; GO limitato solo a pianificare un reducer fail-closed sopra ricerche nazionali indipendenti. Finding: manca una ricerca mensile ES con stato assicurativo/hecho causante/anchor 24-180 e RD 453/2022; manca la ricerca IT pre-1996 e la copertura dei percorsi totalizzati; il consumer UE usa una data singola e richiede un perimetro nazionale completo prima di aggregare. La regola eseguibile Art.57 usa invece soglia `12` mesi di calendario, incoerente con Knowledge e non sufficiente a provare durata assicurativa giuridica; l'output non separa l'obbligo di pagamento. Nessuna modifica runtime o dati personali. Fonti consultate: EUR-Lex Reg. 883/2004 e 987/2009; BOE LGSS consolidato al 2026-10-03 e RD 453/2022.

### V4.14l — Art. 57 duration and payment-obligation contract audit

**Stato:** `done`
**Tipo:** `audit`

Gate normativo abilitante per risolvere la divergenza tra la Knowledge approvata e il criterio eseguibile `less_than_one_year_threshold_months: 12`.

- Dipende da: V4.14k, V4.14b, V4.14c e V4.14i/j.
- Piano: stabilire da fonti primarie il test cumulativo dell'art. 57(1), la rappresentazione della durata/unità assicurativa, le conversioni applicabili ex Reg. 987/2009 artt. 12-13 e lo stato distinto di esonero/obbligo di pagamento ex art. 57(3); chiarire le interazioni con artt. 50-52 e 54-55 del Reg. 883/2004 e con gli Allegati VIII.
- Output: contratto source-bound e testabile con unità, provenienza, periodi, condizioni, casi limite e `data_gaps`; esito indipendente GO/NO-GO limitato.
- Fuori scope: modifiche Rules/Tests/Engine, eligibility individuale o prima data IT/ES/UE, riconoscimento, decorrenza e pagamento effettivo.
- Stop condition: senza fonte/periodo che determini il criterio di durata e il trattamento dell'obbligo di pagamento, mantenere il consumer bloccato/non valutabile e non tradurre 12 mesi in una regola eseguibile.

**Esito 2026-10-15:** GO limitato alla formulazione Knowledge; NO-GO per `less_than_one_year_threshold_months: 12` e qualunque calcolo Art.57 fondato direttamente sui mesi di calendario. Il test è cumulativo: durata dello specifico schema strettamente < un anno e nessun diritto autonomo considerando soltanto i periodi dello Stato. Reg. 987/2009 artt. 12-13 richiede unità nativa comunicata, overlap risolto, base giorni ove pertinente e conversione deterministica. I parr. 2-3 separano inclusione nell'importo teorico e obbligo di pagamento da eligibility e pro-rata. Nessun file o calcolo individuale modificato.

### V4.14m — Art. 57 source-bound duration contract

**Stato:** `done`
**Tipo:** `audit`

Definire e sottoporre a review normativa indipendente il contratto dati source-bound che sostituirà la soglia fissa di 12 mesi: schema/istituzione, periodi comunicati, unità nativa, base giorni (5/6/7), classificazione overlap ex art. 12 e conversione ex art. 13, durata legale strettamente inferiore a un anno, diritto autonomo sui soli periodi e status Allegato VIII parte 2. Valori ignoti, unità non classificata, overlap irrisolto o versione non provata devono produrre `article_57_not_assessed` con `data_gaps`. Tenere distinti eligibility nazionale, applicabilità dell'art. 57, inclusione nel teorico, pro-rata e obbligo di pagamento.

- Dipende da: V4.14l, V4.14b e V4.14i/j.
- Ordine dopo il GO pre-implementazione: Knowledge → Rules → Tests → Engine. Modifiche esclusivamente sintetiche e fail-closed; nessun calcolo individuale o sblocco di V4.14.
- Regressioni: 11 mesi di calendario ma un anno convertito; esattamente un anno; unità giorni su base 5/6/7; overlap; ciascuna condizione Art.57 isolata; Allegato VIII parte 2; tutte le istituzioni esonerate; separazione eligibility/teorico/pro-rata/obbligo di pagamento.
- Stop: se lo schema concreto o la conversione non sono provati, mantenere il consumer non valutabile; non sostituire il dato con una soglia calendario.

**Esito review 2026-10-15:** NO-GO sul contratto proposto, senza modifiche runtime. La specifica deve includere Stato/prestazione/legislazione/versione/data del rischio e rilevanza dei periodi per il beneficio; conversione art. 13 vincolata a scopo e granularità, con frazioni/arrotondamento/massimo annuale e distinzione aggregato vs anno per anno; enumerazioni art. 12(2)-(6), presunzione per date imprecise e riferimento art. 43(1) Reg. 987/2009 per teorico/effettivo; verifica autonoma nazionale source-bound; orchestrazione inter-istituzionale art. 57(3); stati distinti e logica ternaria short-circuit. Condizioni false decisive non diventano gap; i campi condizionali non pertinenti usano `not_applicable`; solo input decisivi ignoti producono `article_57_not_assessed + data_gaps`. Serve nuova review pre-implementazione dopo l'aggiornamento della specifica.

### V4.14n — Complete Art. 57 contract specification

**Stato:** `in_progress`
**Tipo:** `audit`

Documentare un contratto source-bound completo secondo i finding V4.14m prima di qualsiasi modifica runtime.

- Dipende da: V4.14m e V4.14l.
- Review v0.2: NO-GO limitato, quattro correzioni finite recepite in v0.3. Review v0.3: NO-GO limitato; corretti in v0.4 matrice/enum art. 12 e identificatori. Review v0.4: NO-GO limitato; resta la rappresentazione di overlap parziali e overlap ex art. 12(2) non risolti dai parr. 3-4. La candidata v0.5 introduce `period_coordination_segments[]`, conserva i residui non coincidenti, applica 12(3)-(4) solo alla porzione coincidente e richiede conteggio singolo source-bound o `not_assessed` per gli altri overlap, con regressioni dedicate. Un quarto ciclo di review indipendente richiede nuova decisione dell'utente; nessun GO runtime.
- Separare eligibility nazionale, eccezione art. 57, inclusione importo teorico, pro-rata e obbligo nazionale di pagamento. Usare stati ternari con short-circuit semantico e `not_applicable` per campi condizionali non pertinenti.
- Output: specifica con fonti/versioni, JSON contract candidate v0.5, casi limite e `data_gaps`; nuovo gate normativo indipendente sulla versione esatta prima di qualsiasi implementazione.
- Fuori scope: Rules/Tests/Engine, importi o date individuali e mese pensionistico complessivo. V4.14 resta `blocked`.

### V4.14a — Work-transition normative and contract audit

**Stato:** `planned`
**Tipo:** `audit`

Audit dovuto dopo V4.11-V4.14 prima di introdurre il decumulo integrato.

- Dipende da: V4.14.
- Repository: `bootstrap`, `knowledge`, `rules`, `engine`.
- Checklist: `family-office-bootstrap/docs/code-audit-checklist.md` + `11-work-transition-retirement-bridge.md`.
- Done quando: timeline, gross/net, contribuzione e entitlement sono coerenti, testati e senza blocker impliciti.

### V4.15 — Retirement bridge income composer

**Stato:** `planned`
**Tipo:** `functional`

Comporre gli stream che finanziano il periodo tra riduzione/cessazione e pensioni.

- Dipende da: V4.14a, V4.2, V4.3, RITA V2.
- Repository: `engine`, `rules`, `workspace`.
- Output: `retirement-bridge-timeline/v1`.
- Stream: reddito proprio residuo, coniuge, affitti, RITA, pensioni gia' attive, liquidita'/asset withdrawals e altri flussi espliciti.
- Test: RITA con start/end, asset vincolato, reddito coniuge, affitto, gap di eleggibilita', doppio conteggio.
- Done quando: il bridge e' una timeline mensile di stream con disponibilita' e trattamento gross/net espliciti.

### V4.16 — Monthly decumulation and sequence-risk simulation

**Stato:** `planned`
**Tipo:** `functional`

Eseguire il bilancio mensile household e il decumulo per bucket, prima deterministico e poi con stress stochastic separato.

- Dipende da: V4.15, V4.3, V4.5.
- Repository: `engine`.
- Output: `work-transition-simulation/v1`.
- Metriche: shortfall mensile, prelievi, reserve months, depletion, terminal wealth, tax/cost drag supportato, P05/P50/P95 e success probability per stress.
- Test: inflazione, crash iniziale, ponte lungo, RITA temporanea, pensioni differite, emergenza minima, seed riproducibile.
- Done quando: sequence-of-returns e liquidita' possono cambiare l'esito senza alterare il baseline deterministico.

### V4.17 — Phased-work candidate generator

**Stato:** `planned`
**Tipo:** `functional`

Generare una griglia controllata di alternative full-time/part-time/cessazione evitando combinazioni opache o ingestibili.

- Dipende da: V4.16.
- Repository: `engine`, `workspace`.
- Output: `work-transition-candidate-set/v1`.
- Dimensioni: data uscita full-time, FTE ammessi, durata fasi, data cessazione, policy RITA/bridge ammesse, constraint familiari.
- Test: griglia limitata, candidate duplicate, vincoli incompatibili, pruning spiegabile.
- Done quando: ogni candidate ha ID/hash, scenario derivato e motivo di inclusione/esclusione.

### V4.18 — Earliest/recommended/full work-exit optimizer

**Stato:** `planned`
**Tipo:** `functional`

Valutare le candidate e restituire date e alternative ordinate secondo constraint trasparenti.

- Dipende da: V4.17.
- Repository: `engine`.
- Output: `work-transition-optimizer/v1`.
- Output minimo: `earliest_full_time_exit_date`, `recommended_full_time_exit_date`, `full_work_exit_date`, piano FTE, pension start dates, success probability, P05 terminal wealth, minimum liquidity buffer, rejected candidates e sensitivity.
- Test: earliest non recommended, part-time migliore di hard stop, nessuna candidate sostenibile, constraint terminal wealth, probability threshold, reversibilita'.
- Done quando: il ranking e' spiegabile e una data non viene emessa se un gap bloccante puo' materialmente modificarla.

### V4.18a — Optimizer and stochastic audit

**Stato:** `planned`
**Tipo:** `audit`

Audit dovuto dopo V4.15-V4.18.

- Dipende da: V4.18.
- Repository: `engine`, `rules`, `knowledge`.
- Focus: determinismo, seed, pruning, metriche, no gross/net mixing, no pension-start shortcut, performance e regressioni.
- Done quando: nessun difetto di contract o simulazione blocca l'integrazione con tool registry.

### V4.19 — Legacy work-exit migration and tool-registry integration

**Stato:** `planned`
**Tipo:** `functional`

Integrare i nuovi tool nel registry V5.1 e definire il destino di `work-exit-feasibility/v1` senza rompere gli utenti esistenti.

- Dipende da: V4.18a, V5.1.
- Repository: `engine`, `bootstrap`.
- Output: registry aggiornato, compatibility adapter o deprecation notice versionata, migration guide.
- Test: vecchio comando continua o fallisce con migrazione esplicita; versioni tool; planner future-proof.
- Done quando: V5 puo' invocare soltanto i nuovi tool registrati per il golden use case e il legacy non viene confuso con l'optimizer completo.

### V4.20 — Golden use case and V5 resume gate

**Stato:** `planned`
**Tipo:** `functional`

Chiudere la roadmap con un workflow end-to-end sintetico e un readiness report applicabile al workspace reale.

- Dipende da: V4.19.
- Repository: `engine`, `bootstrap`, `workspace`.
- Output: `work-transition-plan/v1`, comando breve `fo planning work-transition plan` e golden scenario sintetico.
- Golden path: full-time → part-time → cessazione → RITA/patrimonio → pensione ES → pensione INPS, con spouse income e stress avverso.
- Test: end-to-end, lineage, data gaps, Windows/Linux, reproducibility, no personal data nelle fixture.
- Done quando: il comando produce le tre date, piano per fasi, bridge, pension start dates, metriche di rischio, motivi delle candidate scartate e blocker; il gate V4B → V5 e' verificato e, nello stesso aggiornamento di governance, `roadmap-v4b-work-transition.md` passa a `done`, V5 torna `in_progress` e `current-next-increment.md` viene posizionato su V5.3.

## Exit criteria V4B

- Il sistema non usa piu' `work-exit-feasibility/v1` come risposta completa al phased retirement.
- La data di uscita dal full-time puo' precedere di anni la cessazione e la pensione.
- Il part-time modifica sia cashflow corrente sia contribuzione/pensione futura.
- RITA e asset bridge rispettano eleggibilita', start/end e liquidita'.
- Il risultato distingue lordo/netto e segnala tassazione non disponibile.
- Il baseline e' mensile e deterministico; lo stress stochastic e' riproducibile.
- Le tre date chiave e almeno 2 alternative sono spiegabili e tracciabili.
- V5.1 tool registry e' aggiornato; V5.3 puo' riprendere senza chiedere all'LLM di inventare calcoli mancanti.

## Fuori perimetro

- negoziazione con il datore di lavoro o garanzia che un part-time sia contrattualmente ottenibile;
- certificazione ufficiale INPS/Seguridad Social/P1;
- consulenza legale, fiscale o previdenziale sostitutiva del professionista;
- previsione certa di norme future;
- ottimizzazione opaca non riconducibile a scenario, regole e metriche.
