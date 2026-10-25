# V4B Roadmap — Work Transition & Retirement Bridge

### V4.15c - Code audit after RITA fund-stream intake

**Stato:** `done`
**Tipo:** `audit`

Audit ricorrente eseguito dopo quattro incrementi funzionali completati. Verificati confini del servizio RITA, allineamento contratto/builder/test, regressioni, data gaps, provenance, privacy delle fixture e compatibilità dei path. Nessun blocker nel corrective pass V4.15b; follow-up non bloccante sul riesame end-to-end del timing del chiamante CLI. Suite Engine 797/0/0/0 e guardrail superati; V4.14/V4.15 restano bloccate dai prerequisiti già dichiarati.

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

**Stato:** `done`
**Gate:** GO normativo limitato alla specifica documentale v0.17; nessun GO per Knowledge/Rules/Tests/Engine, calcoli o decisioni.
**Tipo:** `audit`

Documentare un contratto source-bound completo secondo i finding V4.14m prima di qualsiasi modifica runtime.

- Dipende da: V4.14m e V4.14l.
- Review v0.2-v0.17: NO-GO limitati, finding recepiti progressivamente. La review finale indipendente ha dato GO limitato alla specifica documentale v0.17 dopo aver verificato hash c14n-v4, golden duration-mode razionale e `human_review_required: true` obbligatorio. Nessun GO per Knowledge/Rules/Tests/Engine, calcoli o decisioni; V4.14 resta `blocked`.
- Separare eligibility nazionale, eccezione art. 57, inclusione importo teorico, pro-rata e obbligo nazionale di pagamento. Usare stati ternari con short-circuit semantico e `not_applicable` per campi condizionali non pertinenti.
- Output: specifica con fonti/versioni, JSON contract v0.17, casi limite, `data_gaps`, GO documentale limitato e verifiche concluse; ogni successiva implementazione richiede uno scope e gate distinti.
- Fuori scope: Rules/Tests/Engine, importi o date individuali e mese pensionistico complessivo. V4.14 resta `blocked`.

### V4.14a — Work-transition normative and contract audit

**Stato:** `done`
**Tipo:** `audit`

Audit diagnostico eseguito il 2026-10-18: readiness e scenario rispettano lineage/provenance, ma employment net/contributions, entitlement/payment, gross/net end-to-end, RITA V2 e rental/AML classification restano gap espliciti. Il criterio di completamento non è soddisfatto; il gate V4.14 resta bloccato e V4.15 non è selezionabile.

- Dipende da: V4.14.
- Repository: `bootstrap`, `knowledge`, `rules`, `engine`.
- Checklist: `family-office-bootstrap/docs/code-audit-checklist.md` + `11-work-transition-retirement-bridge.md`.
- Done quando: timeline, gross/net, contribuzione e entitlement sono coerenti, testati e senza blocker impliciti.

### V4.14o — EU source-currentness audit for the Art. 57 contract

**Stato:** `done`
**Tipo:** `audit`

**Dipende da:** V4.14n.
**Scope:** verifica documentale delle fonti autentiche UE richiamate dal contratto Art. 57: Reg. 883/2004 artt. 50-57 e Allegato VIII parti 1/2; Reg. 987/2009 artt. 12-13, 43, 46-47 e 93-94. Confrontare atti modificativi, rettifiche, date di efficacia/applicazione e ambito territoriale al 2026-10-16.
**Fuori scope:** casi individuali, regole nazionali salvo dipendenza concreta, rule pack, test funzionali, Engine, calcoli e dati personali.
**Chiusura 2026-10-16 — GO limitato alla documentazione:** EUR-Lex conferma consolidati correnti 883/2004 (31-07-2019) e 987/2009 (01-01-2018). Review indipendente verifica 2019/1149 (non modifica 883 artt. 50-57), 2017/492 (tocca Allegato VIII per Polonia/Svezia/Regno Unito, non Italia/Spagna; e modifica solo Allegati 1/3 di 987), rettifiche linguistiche successive e proposta COM(2026) 980 non vigente. Note Knowledge aggiornate con limiti e collegamenti ufficiali. Suite completa 762 test, 0 failure, 0 errori, 0 skipped; audit roadmap, schema planner, guardrails e diff-check passano. Nessuna modifica Rules/Tests/Engine o calcolo; V4.14 resta `blocked`.

**Done quando:** matrice fonte-disposizione-versione-efficacia è verificata da reviewer normativo indipendente; note Knowledge e decision log sono aggiornati solo entro il GO ricevuto. Ogni incertezza resta un gap e V4.14 rimane `blocked`; nessuna autorizzazione alla timeline o al runtime.

### V4.14p — Spanish national first-eligibility-month contract audit

**Stato:** `done`
**Tipo:** `audit`

Definire e sottoporre a review normativa indipendente il contratto per cercare il primo mese supportato di eligibility della pensione contributiva ordinaria spagnola nel solo Regimen General, colmando il blocker individuato da V4.14k. Il consumer spagnolo corrente valuta un mese fornito e non effettua una ricerca temporale; il rule pack non codifica ancora il hecho causante né gli anchor differenziati della carencia específica.

- Dipende da: V4.14b, V4.14c, V4.14k e V4.14o.
- Fonti candidate: LGSS artt. 165/205 e DT 7, RD 453/2022 artt. 3-4, Seguridad Social ufficiale; Reg. 883/2004 artt. 6 e 50-52 e disposizioni applicative pertinenti del Reg. 987/2009.
- Scope: pensione contributiva ordinaria nel Regimen General; determinazione del fatto causante per stato assicurativo; carenza generica e specifica, inclusa la finestra dalla cessazione dell'obbligo di cotizzare quando prevista; rilevanza dei periodi di altri Stati membri per acquisizione del diritto; precisione mese/giorno e distinzione dagli effetti economici.
- Output: matrice source-bound delle condizioni e contratto temporale per una ricerca mensile ordinata, con input minimi/provenance, stop fail-closed al primo candidato materiale non valutabile e `null + data_gaps`; l'output non è riconoscimento, data di decorrenza, pagamento o prima data complessiva IT/ES/UE.
- Regressioni da prescrivere per il successivo slice eseguibile: alta con obbligo contributivo, alta assimilada senza obbligo, non alta; anchor recente presente/assente; cambio d'anno nella soglia d'età; mesi incompleti e frazioni; periodi UE sovrapposti/non classificati; storia e fonti fuori copertura; candidato anteriore non valutabile.
- Fuori scope: regimi diversi, pensionamento anticipato/parziale/flessibile, importi e pro-rata, riconoscimento amministrativo, decorrenza/pagamento, Rules/Tests/Engine, input personali.
- **Esito review normativa indipendente (2026-10-16):** GO limitato alla definibilità documentale; NO-GO alla bozza esaminata come contratto implementabile. LGSS consolidata al 2026-10-03; RD 453/2022 efficace dal 2022-06-16 e artt. 3-4 senza modifiche successive rilevate; consolidati EUR-Lex 883/2004 (2019-07-31) e 987/2009 (2018-01-01), da non confondere con testi autentici. Finding: scansione per giorno e mese solo proiettato; distinguere fatto causante/domanda/percorso art. 3; status separato dall'obbligo e dalla cessazione dell'obbligo contributivo; validità non anteriore al 2022-06-16 senza pack storico; aggiungere 883/2004 artt. 1(t), 6, 50-52 e 51 e 987/2009 artt. 12-13; definire lower bound/materialità e gap per periodi UE non datati/unità/overlap ignoti; guidance amministrativa subordinata alla fonte primaria. Nessuna approvazione Knowledge/Rules/Tests/Engine, casi individuali, pro-rata/importi o timeline.
- **Chiusura 2026-10-16:** review indipendente ha delimitato il contratto e reso espliciti i gap. Suite Engine 762/762, 0 failure, 0 errori, 0 skipped; roadmap audit, guardrails e diff-check passano. Nessuna modifica Knowledge/Rules/Tests/Engine; V4.14 resta `blocked`.

### V4.14q — Spanish date-level eligibility contract remediation and review

**Stato:** `done`
**Tipo:** `audit`

Recepire i finding di V4.14p in una nuova specifica documentale versionata e ottenere una nuova review normativa indipendente sulla versione esatta. Questo ciclo non eredita il GO limitato o il budget di review di V4.14p.

- Dipende da: V4.14p, V4.14b, V4.14c, V4.14k e V4.14o.
- Specificare la ricerca giornaliera e l'eventuale proiezione al mese; input per data candidata, fatto causante, domanda/ipotesi e percorso RD 453 art. 3; status al fatto causante, obbligo contributivo e cessazione dell'obbligo distinti.
- Vincolare la validità del pack a 2022-06-16 o documentare rule pack storico; includere nel contratto UE Reg. 883/2004 artt. 1(t), 6, 50-52 e 51, Reg. 987/2009 artt. 12-13, con periodi comunicati e temporalmente localizzati.
- Formalizzare lower bound e materialità: nessun candidato successivo se un giorno precedente potenzialmente qualificante non è valutabile; unità, overlap o date mancanti producono `null + data_gaps` salvo presunzioni normative provate.
- Tenere fuori scope Knowledge/Rules/Tests/Engine, pro-rata/importi, riconoscimento, decorrenza, pagamento e timeline complessiva fino a un GO separato.
- Test successivi: confini giornalieri in mese e anno, domanda entro ±3 mesi, tutte le vie dell'art. 3.2, anchor e cessazione obbligo, anzianità, transitorio 2022, periodi UE temporalmente classificati, candidato anteriore non valutabile, storia e fonti fuori validità.
- **Contratto sottoposto a review:** `spanish-first-eligibility-contract/v2`, in `docs/current-next-increment.md`; ricerca day-level, campi candidati/fatto causante/domanda/percorso art. 3 distinti, status/obbligo/cessazione distinti, validità da 2022-06-16 o pack storico, overlay UE esplicito, lower bound/materialità e stop fail-closed.
- **Autorizzazione:** il 2026-10-16 l'utente ha autorizzato un nuovo gate normativo read-only sulla versione v2 esatta, un tentativo e timebox complessivo di cinque minuti. La traccia e il budget V4.14p non sono riutilizzati.
- **Stop:** timeout è fallback senza verdetto; NO-GO mantiene V4.14 `blocked` e richiede nuova autorizzazione prima di altro ciclo. GO, se concesso, resta limitato alla specifica documentale v2: nessun GO ereditato per Knowledge/Rules/Tests/Engine, timeline o calcolo.
- **Esito (2026-10-16):** review normativa indipendente conclusa nel timebox autorizzato, NO-GO sulla versione v2 esatta. Sei gap registrati in `current-next-increment.md`: specifica dei path/domanda art. 3 RD 453 e transitorio; ancoraggio/versionamento dei requisiti LGSS; schema computazionale dell'overlay UE; semantica verificabile di lower bound/materialità e invalidità/gap; gate umano obbligatorio. Suite Engine 762/762, 0 failure, 0 errori, 0 skipped; audit roadmap, schema planner, guardrails e diff-check passano. Nessuna modifica a Knowledge/Rules/Tests/Engine o dati personali.

### V4.14r — Spanish date-level contract v3 after normative NO-GO

**Stato:** `done`
**Tipo:** `audit`

Recepire i quattro finding della review v2 in un contratto documentale v3 deterministico e source-bound. L'artefatto normativo sottoposto al gate è `spanish-first-eligibility-contract/v3` nella sezione storica V4.14r di `docs/current-next-increment.md`.

- Dipende da: V4.14q, V4.14p, V4.14b, V4.14c, V4.14k e V4.14o.
- Matrice articolo-per-percorso per RD 453/2022 art. 3.1, 3.2(a-e), 3.3; domanda nazionale/internazionale, applicabilità e transitorio combinano data domanda, HCD, path e versione pack.
- Matrice LGSS 165.1, 205.1(a-b), 205.3 e DT 7 con 15 anni, 2/15 e anchor stato/obbligo/cessazione distinti; art. 205.3 non alta/multi-regime non si presume coperto.
- Overlay UE per periodi qualificati istituzionalmente, autonomo vs totalizzato, art. 51, overlap/presunzione art. 12(6) e conversione 5/6/7 con regole/art. 13 e cap annuali.
- Definire invalidità strutturale vs gap probatorio, logica ternaria per path, lower bound completo, materialità, output potenziale e `human_review_required: true`.
- **Autorizzazione:** l'utente il 2026-10-16 ha chiesto di procedere e avviare una nuova review normativa. Un solo tentativo read-only sulla v3 esatta, timebox massimo totale 5 minuti; nessun retry o trasferimento del budget v2.
- **Stop:** NO-GO/timeout non autorizzano Knowledge/Rules/Tests/Engine. GO, se concesso, vale solo per la specifica documentale v3. Nessun calcolo individuale, dato personale o timeline complessiva.
- **Esito (2026-10-16):** il reviewer normativo indipendente dà NO-GO limitato alla v3 esatta. Quattro gap documentali registrati in current-next: input probatorio di volontà/strumento internazionale; scope preciso della regola anni/mesi completi; corretta separazione 883/2004 artt. 6, 50, 51(3), 52; limite superiore e truth table deterministica della scansione. Rami RD 453, transitorio, LGSS, unità/conversione art. 12/13, distinzione invalidità/gap e revisione umana sono stati confermati nel perimetro review. Suite Engine 762/762, 0 failure/errori/skipped; schema planner, guardrails, audit roadmap e diff-check passano. Nessuna modifica Knowledge/Rules/Tests/Engine o dato personale.

### V4.14s — Spanish date-level contract v4 after normative NO-GO

**Stato:** `done`
**Tipo:** `audit`

Preparare `spanish-first-eligibility-contract/v4` in `docs/current-next-increment.md`, correggendo i quattro gap della review v3: `applicant_intent` probatorio distinto dal path derivato e base internazionale con ambito personale/materiale/temporale; unità della fascia d'età distinta dalle carenze 15y e 2/15; semantica UE corretta per artt. 6, 50, 51(3), 52; dominio finito `search_lower_bound/search_upper_bound/as_of_date` con truth table fra path compatibili e `no_candidate_in_complete_range` solo a copertura completa.

- **Autorizzazione:** il 2026-10-16 l'utente ha autorizzato un singolo ciclo e un solo gate normativo read-only sulla v4 esatta, con timeout massimo complessivo di 5 minuti. Nessun retry o ulteriore gate senza nuova autorizzazione.
- **Stop:** timeout/NO-GO non autorizzano Knowledge/Rules/Tests/Engine o runtime; nessun calcolo individuale/dato personale. Suite completa deve chiudere con 0 failure, 0 errori e 0 skipped; altrimenti lo stato non è `done`.
- **Test/verifiche richiesti:** review normativa exact-version; suite Engine completa; roadmap audit, schema planner, execution guardrails e diff check.
- **Esito review (2026-10-16):** NO-GO limitato alla v4 esatta. Restano incompleti: rinvio diretto e predicati/fallback dell'art. 57 con art. 51(3); trattamento source-bound dei periodi frazionari per 205.1(b) 15y e 2/15; vincolo formale fra search bounds, `as_of_date` e cutoff probatorio. `applicant_intent`/base internazionale recepiti. Suite Engine 762 test, 0 failure/errori/skipped; roadmap audit, schema planner, guardrails e diff check passano. V4.14s si chiude come audit documentale, senza GO runtime; V4.14t richiede nuova autorizzazione per una review successiva.

### V4.14t — Spanish date-level contract v5 after normative NO-GO

**Stato:** `done`
**Tipo:** `audit`

Preparare `spanish-first-eligibility-contract/v5` in `docs/current-next-increment.md` per i tre finding v4: applicazione diretta Reg. 883/2004 artt. 51(3)/57 e fallback; soglie di carenza 5.475 e 730 giorni con provenienza normativa/amministrativa distinta e gap source-bound; vincoli formali fra lower/upper, as-of/evaluation date, evidence coverage e orizzonte ipotetico.

- **Autorizzazione:** l'utente il 2026-10-16 ha richiesto il nuovo gate normativo; un singolo tentativo read-only sulla v5 esatta, bounded a 5 minuti.
- **Stop:** timeout/NO-GO non autorizzano runtime o modifiche Knowledge/Rules/Tests/Engine; nessun calcolo individuale/dato personale. Nessun gate v6 senza nuova autorizzazione.
- **Verifiche:** review exact-version, suite Engine 0/0/0, roadmap audit, planner schema, execution guardrails e diff check.
- **Esito (2026-10-16):** GO limitato all'esatta v5; Reg. 883/2004 artt. 51(3)/57, unità LGSS carenze e dominio temporale/evidence sono confermati nel perimetro. Limiti: escludere art. 57(4)/Allegato VIII parte 2 quando applicabile; la modifica Reg. 988/2009 art. 51(3) è efficace dal 2010-05-01; 730 giorni è criterio amministrativo/giurisprudenziale e non si generalizza oltre la STS 607/2026. Suite Engine 762, 0 failure/errori/skipped; audit, schema, guardrail e diff check passano. Nessun GO runtime. V4.14u pianificata e ogni ulteriore gate richiede nuova autorizzazione.

### V4.14u — Spanish eligibility temporal applicability and Annex VIII exclusions

**Stato:** `done`
**Tipo:** `audit`

Formalizzare i limiti della review v5 in `spanish-first-eligibility-contract/v8`: applicabilità scheme-specific dell'art. 57(4)/Allegato VIII parte 2 e regime temporale/transitorio di Reg. 883/2004 artt. 87/91 e Reg. 988/2009/987/2009 attorno al 2010-05-01. Il modello distingue periodi, fatto causante, domanda/revisione, Stato e versione degli Allegati; dati insufficienti producono `not_assessed` + gap. Test regressivi contrattuali sintetici, senza modifiche a Knowledge/Rules/Tests/Engine.

- **Autorizzazione:** con “procedi”, il 2026-10-16 l'utente ha autorizzato un singolo gate normativo read-only sulla v6 esatta, reviewer critico indipendente, massimo 5 minuti complessivi.
- **Stop:** nessun retry su v7, nessuna modifica runtime o calcolo. Suite completa con 0 failure/errori/skipped e governance valida prima di `done`; altrimenti `in_progress`/`blocked`.
- **Verifiche:** fonti ufficiali EUR-Lex/DOUE, review exact-version, suite Engine, roadmap audit, planner schema, guardrail e diff check.
- **Esito review v6 (2026-10-16):** NO-GO limitato alla v6 esatta. Art. 57(4)/Allegato VIII parte 2 è approvato nel perimetro; la matrice transitoria non definiva gli effetti di Reg. 883/2004 art. 87(5)-(7) e Reg. 987/2009 artt. 93-94. Finding recepito nella v7; un nuovo gate v7 richiede autorizzazione separata. Suite completa Engine 762/762, 0 failure/errori/skipped; la v7 non è approvata né implementata.
- **Nuova autorizzazione (2026-10-16):** l'utente ha autorizzato un singolo gate normativo read-only sulla v7 esatta, massimo 5 minuti totali. Nessun retry su v8 o approvazione runtime implicita.
- **Esito review v7 (2026-10-16):** NO-GO limitato alla v7 esatta. Vengono richiesti tre chiarimenti bounded: congiunzione dei presupposti art. 94(1); distinzione fra revisione su richiesta ex art. 87(5) e riesame d'ufficio triggerato da una domanda qualificata ex art. 94(2); prova di diritto non decaduto/non prescritto per art. 87(7), altrimenti gap. Recepite nella candidata documentale v8. Nessun terzo gate autorizzato; default di due deleghe sostanziali raggiunto.
- **Autorizzazione (2026-10-16):** l'utente autorizza esplicitamente il terzo evento per un solo gate normativo read-only sulla versione esatta `spanish-first-eligibility-contract/v8`, affidato a `fo_normative_reviewer`, timebox massimo 5 minuti. Nessun quarto evento, retry o v9; nessun GO runtime implicito.
- **Esito review v8 (2026-10-16):** **GO limitato** sulla sola specifica documentale v8. Reviewer conferma artt. 94(1), 94(2), 87(5)-(7), art. 57(4)/Allegato VIII parte 2 e matrice transitoria; regressioni contrattuali v8 confermate. Non valutati schemi nazionali concreti, SEE/Svizzera, casi individuali, importi/effetti economici o runtime. Suite Engine completa 762 test, 0 failure/errori/skipped (ultima esecuzione completa); audit roadmap, schema planner, guardrail e diff check passano. Nessun GO a Knowledge/Rules/Tests/Engine o calcoli. V4.15 è il prossimo incremento pianificato.

### V4.14v — Art. 57 source-bound duration implementation authorization gate

**Stato:** `done`
**Tipo:** `audit`

Valutare con review normativa indipendente se il contratto documentale Art. 57 `v0.17` sia sufficiente come base pre-implementazione per rimuovere il threshold fisso di 12 mesi di calendario dal rule pack. La review riguarda durata legale source-bound, periodi pertinenti, unità/conversioni e overlap ex Reg. 987/2009 artt. 12-13, diritto autonomo, Allegato VIII parte 2, fallback art. 57(3) e separazione dell'obbligo di pagamento.

- Dipende da: V4.14k, l, m, n, o e u (tutte `done`).
- Review: un solo tentativo read-only sulla versione esatta v0.17, `fo_normative_reviewer`, massimo 5 minuti; fonti primarie EUR-Lex/DOUE. Il comando utente “procedi” autorizza questo gate soltanto.
- Fuori scope: modifiche a Knowledge/Rules/Tests/Engine/CLI, runtime, calcoli individuali, importi/pro-rata, ricerca nazionale ES/IT o reducer complessivo.
- Stop: NO-GO/timeout non autorizza implementazione; V4.14 resta `blocked` e V4.14a/V4.15 non sono selezionabili.
- **Esito review (2026-10-16): GO limitato pre-implementazione** alla sola specifica v0.17/fo-art57-c14n-v4. Il reviewer conferma la struttura source-bound per durata <1 anno, unità/conversioni, Art. 57(1)-(4), Reg. 987/2009 artt. 12-13, separazione eligibility/teorico/pro-rata/payment obligation. N-06: test futuri rifiutano fixture legacy v0.16/c14n-v3. N-07: il pack/service/test dipendono ancora dal 12 fisso, blocker confermato e non approvato. Nessun GO runtime o alla prima data complessiva.
- **Chiusura verificata:** suite Engine 762 test, 0 failure/errori/skipped; roadmap audit, planner schema, guardrail e diff check passano. V4.14v `done`; V4.14w avviato come slice deterministico separato.

### V4.14w — Source-bound Art. 57 duration in the EU pension consumer

**Stato:** `blocked`
**Esito corrente:** suite Engine 774/0/0/0; review normativa finale evento 11 conclusa con **NO-GO**; budget autorizzato esaurito. Runtime non approvato.
**Tipo:** `functional`

Implementare nel consumer UE il contratto source-bound v0.17 per la durata Art. 57, eliminando il threshold fisso `spain_months < 12`. Ordine: Knowledge → Rules → Tests → Engine. Lo stato incompleto/ignoto resta `not_assessed + data_gaps`; separare eligibility, eccezione Art. 57, importo teorico, pro-rata e obbligo/pagatore. Mantenere `human_review_required: true`.

- **Dipende da:** V4.14l/m/n (contratto v0.17 GO documentale); V4.14v (GO normativo limitato pre-implementazione).
- **Repository:** `family-office-knowledge`, `family-office-rules`, `family-office-engine`.
- **Test obbligatori:** confine durata legale `<`, `=`, `>` un anno; dati source-bound mancanti/unknown; diritto autonomo true/false/unknown; Allegato VIII parte 2; overlap e conversione; ramo inter-istituzionale art. 57(3); profilo legacy v0.16/c14n-v3 respinto.
- **Fuori scope:** prima data mensile ES, ramo IT pre-1996, reducer complessivo IT/ES/UE, importi, pagatore individuale, decorrenza, riconoscimento o workspace personale.
- **Done quando:** nessuna decisione dipende da mesi di calendario; input insufficiente è fail-closed con gap; suite completa 0/0/0; review normativa post-implementazione GO limitato al diff e governance passata. V4.14 resta `blocked` finché gli altri rami della prima data non sono coperti.
- **Esito verifica 2026-10-16:** 21 test mirati OK (fuori sandbox); suite completa 766 test con 3 failure e 5 errori, quindi non soddisfa il gate. Review normativa indipendente exact-diff: **NO-GO** per confronto razionale, validazione/binding c14n-v4 incompleti, contesto legale/temporale non vincolato, aggregazione Art. 57(3) non derivata, short-circuit non conforme, provenienza Reg. 988/2009 mancante dal rule pack e copertura test insufficiente. Incremento mantenuto `in_progress`; non usare per decisioni pensionistiche. Correzioni/nuova review richiedono autorizzazione esplicita per estendere il perimetro.
  - **Riesecuzione post-fix 2026-10-16:** migrato il consumer legacy al campo `article_57_source_bound`, corretta la comparazione razionale, aggiunte fixture sintetiche source-bound e digest corretto nel sample. Test mirati 37/37 e test CLI 1/1; suite Engine completa **768 test, 0 failure, 0 errori, 0 skipped**.
  - **Review normativa post-fix 2026-10-16 — NO-GO:** confermata la comparazione razionale corretta; restano blocker P0 su grammar/binding c14n-v4 e derivazione source-bound del pagatore Art. 57(3), oltre a ordering fail-closed, provenance Reg. 988/2009/Allegato VIII, affermazione di pagamento nel secondo consumer e test negativi/date insufficienti. Quarto evento esaurito; stato `in_progress`, runtime non approvato. Qualsiasi altro ciclo richiede nuova autorizzazione esplicita.
  - **Secondo ciclo correttivo, review finale 2026-10-16 — NO-GO:** 39 test mirati OK; suite completa **770/0/0/0**. Il reviewer conferma i fix duration-mode/razionali e la fonte 988/2009, ma rileva ancora grammar/root binding c14n-v4 incompleti, set istituzionale Art. 57(3) non provato completo, risk/applicability dates e versione Annex non validate, `separate_payment_by_country: true` incondizionato e regressioni avverse insufficienti. La suite è verde ma non sostituisce il gate normativo. Eventi 5 e 6 esauriti; `in_progress`, runtime non approvato; ulteriore ciclo solo con nuova autorizzazione utente.
  - **NO-GO fallback 2026-10-17 e nuova autorizzazione:** suite completa 772/0/0/0; review evento 9 rileva P0 su grammar/transitorio v0.17 e records/completeness Art.57(3), P1 sul match Annex; conferma che il claim generale di pagamento separato è assente. Il successivo `procedi` autorizza solo eventi 10 (implementazione) e 11 (review normativa read-only, massimo 5 minuti). Scope: aderire ai campi gia definiti da v0.17/c14n-v4, aggiungere regressioni sintetiche, fermarsi su semantica nuova. Runtime non approvato.
  - **Ciclo eventi 10/11 concluso 2026-10-17 — NO-GO:** test mirati 127/127 e suite completa **774/0/0/0**; audit roadmap, schema planner, guardrail (11 eventi) e diff-check OK. Reviewer finale rileva P0: completezza istituzionale non fail-closed per record assente/null/mismatch; record Art.57(3) non legati probatoriamente allo stesso caso/beneficio coordinato né coerenti col root; `matched_scheme_entry` non verificata contro elenco Annex VIII versionato. P1: c14n-v4 valida solo il primo parent/bound. Confermati root/transitorio corretti, data autonomous-right legata al rischio e claim generale pagamento separato assente. V4.14w `blocked`, runtime non approvato.

### V4.14x — Art. 57(3) evidence-binding and Annex VIII Part 2 source audit

**Stato:** `blocked`
**Tipo:** `audit`
**Dipende da:** V4.14w (NO-GO, bloccato da binding non sufficientemente specificati).
**Obiettivo:** audit indipendente delle fonti primarie e specifica candidata per i binding probatori necessari prima di ogni implementazione Art. 57.
**Scope:** versione e catena degli atti EUR-Lex per art. 57 e Allegato VIII parte 2; prova completa di match/non-match contro elenco versionato; relazione dei record nazionali allo stesso caso coordinato senza uguaglianza automatica degli ID nazionali; consistenza del record root; verifica di tutti i parent/bound nel segmento c14n-v4.
**Fuori scope:** modifiche al runtime, rule pack eseguibili o calcoli; casi individuali/dati personali; GO di V4.14w o sblocco di V4.14a/V4.15.
**Done quando:** audit fonti/versioni/date e limiti registrato; candidato documentale esatto sottoposto a review normativa; ogni relazione non sostenuta resta `not_assessed + data_gaps`; planner e governance validati. L'esito di questo audit non approva il runtime.
- **Avvio 2026-10-17:** selezionato dopo il nuovo "procedi" dell'utente in applicazione della regola per blocchi di `roadmap-index.md`. Budget ordinario di due eventi: review fonti/read-only, redazione candidata bounded, review normativa exact-version finale.
- **Evento 1 — findings bounded (2026-10-17):** il reviewer è rientrato dopo timeout; nessun GO o file modificato. Confermati il limite testuale dell'Art.57(3) (nessun ID tecnico prescritto), il flusso art.47(4)-(7) Reg.987/2009 e la catena Annex VIII rilevata: Reg.988/2009, 1244/2010, 1224/2012, 517/2013, 1372/2013 e 2017/492. Consolidato 883/2004 al 31-07-2019: 15 Stati/23 voci Part 2. Finding per Rules successivo: riferimento art.1(27) invece di art.1(16) Reg.988/2009 e versione catalogo 2010 senza scadenza. Candidato e scope residuo in `family-office-knowledge/international/eu-pension-art57-evidence-binding-audit-candidate-v0.18.md`; gli atti autentici e le 23 voci restano da riconciliare prima di un catalogo eseguibile.
- **Evento 2/2 (2026-10-17) — NO-GO limitato:** sintesi normativa e catena atti verificate; la candidata v0.18 non materializza le 23 entry/sub-entry e il ledger per entry con date di efficacia, non completa il testo del §57(3), tratta l'ultima istituzione come ordine temporale senza definire la prova istituzionale, e contraddice cardinalità c14n 1 con test multi-posizione. UK/SEE/Svizzera post-Brexit restano fuori scope. Il finding Art.1(16) vs (27) è confermato. V4.14x non approva il contratto/runtime; il catalogo è demandato al nuovo V4.14y.

### V4.14y — Annex VIII Part 2 versioned catalogue and temporal ledger

**Stato:** `done`
**Tipo:** `audit`
**Dipende da:** V4.14x (NO-GO sul candidato, requisiti di source completeness definiti).
**Obiettivo:** produrre una tabella documentale completa delle 23 entry/sub-entry testuali nel consolidato EUR-Lex 31-07-2019 e un ledger entry-by-entry degli atti GUUE di inserimento/modifica/sostituzione, con efficacia temporale e provenance.
**Scope:** Reg. 883/2004 Annex VIII Part 2; Reg. 988/2009, 1244/2010, 1224/2012, 517/2013, 1372/2013 e 2017/492; differenziare entry text e schema nazionale, fissare snapshot e intervalli, tenere UK/SEE/Svizzera fuori dall'applicabilità operativa non verificata.
**Fuori scope:** classificazione di schemi individuali, attivazione del catalogo in Rules/Engine, record personali, binding Art.57(3) o c14n-v4, modifiche runtime.
**Done quando:** ogni entry è reconciliata con gli atti autentici e l'intervallo supportato, i limiti non provati restano gaps e la versione esatta riceve review normativa GO limitato. Budget massimo due eventi per questo incremento.
- **Avvio 2026-10-17:** creato candidato documentale `family-office-knowledge/international/eu-annex-viii-part-2-catalogue-candidate-v0.1.md`; nessuna regola eseguibile aggiornata.
- **Review evento 1/2:** catena degli atti e date verificate; indicati interventi puntuali su ledger, locator OJ, efficacia e voci storiche.
- **Review evento 2/2:** NO-GO alla versione pre-fix, con autorizzazione esplicita e circoscritta a un GO documentale dopo dieci correzioni letterali e finite, senza ulteriore review. Applicate le correzioni alle righe `CZ-1`, `DK-c`, `LV-1`, `AT-b/c/e/f/g`, `PT-1`, `UK-1`; non ne deriva approvazione dell'applicabilità territoriale UK/SEE/Svizzera o di un catalogo eseguibile.
- **Verifiche finali:** citation index mirato 6/6; suite Engine 774 test, 0 failure, 0 errori, 0 skipped; roadmap audit, schema planner, execution guardrails e `git diff --check` superati. V4.14w e il runtime restano bloccati/non approvati.
- **Limite dell'esito:** `completed` chiude solo il deliverable documentale V4.14y; non certifica Rules/Engine, classificazioni individuali o applicabilità UK/SEE/Svizzera.

### V4.14z — Art. 57(3) evidence-binding and root consistency contract audit

**Stato:** `done`
**Tipo:** `audit`
**Dipende da:** V4.14w (blocked), V4.14x (blocked) e V4.14y (done; catalogo solo documentale).
**Obiettivo:** stabilire quali evidenze ufficiali collegano il claim coordinato, beneficio/legislazione, istituzioni e record Art. 57(1)-(3); distinguere obblighi normativi da binding tecnici e lasciare i non provati come `not_assessed + data_gaps`.
**Scope:** Reg. 883/2004 artt. 1(p)-(q), 52 e 57; Reg. 987/2009 artt. 45-48, in particolare 46(1) e 47(4)-(7); Reg. 988/2009 art. 1(16); catalogo documentale Annex VIII Part 2 V4.14y.
**Fuori scope:** modifiche Rules/Engine/CLI, match di schemi concreti, calcoli o dati personali, approvazione runtime.
**Done quando:** reviewer normativo indipendente verifica il contratto documentale esatto; evidenze e limiti sono source-bound; nessun ID condiviso, uguaglianza di ID nazionali, completezza o ordine è inventato; la roadmap mantiene esplicito ogni gap residuo.
    - **Review normativa indipendente (2026-10-18, secondo tentativo): GO limitato** al percorso amministrativo di collegamento del claim; **NO-GO** per ID software condiviso, completezza istituzionale inferita dalla sola lista disponibile, algoritmo root o ordine dei record. Reg. 987/2009 artt. 46(1), 47(4)-(7), 48(1) sostengono invii, scambio dei periodi/decisioni, notifica Art. 57 e riepilogo della contact institution; review distingue il caso Art. 44(3).
    - Per ogni istituzione servono prova di legislazione/schema/beneficio e data, periodi/durata e risultato nazionale ex Art. 57(1); Art. 57(3) richiede l'esonero di tutte e la prova dello Stato che soddisfa per ultimo. Set completo da corroborare con record di distribuzione della contact institution riconciliato con comunicazioni e decisioni; altrimenti `data_gaps`. Annex VIII resta solo documentale, nessun match automatico.
    - **Finding separato per follow-up:** Rule Pack cita Reg. 988/2009 art. 1(27), mentre l'atto autentico inserisce l'art. 57(4) con art. 1(16). Correzione futura secondo Knowledge → Rules → Tests → Engine; fuori scope qui. Nessun trade-off architetturale concreto: architetto non necessario.
    - **Verifica finale:** suite Engine 774 test, 0 failure, 0 errori, 0 skipped; roadmap audit, planner schema, execution guardrails e diff check superati. V4.14z `done` soltanto come audit documentale. V4.14w e V4.14 complessiva restano `blocked`, nessuna approvazione runtime.
  - Fonti: [Reg. 883/2004, artt. 1, 52 e 57](https://eur-lex.europa.eu/eli/reg/2004/883/2019-07-31/eng); [Reg. 987/2009, artt. 45-48](https://eur-lex.europa.eu/eli/reg/2009/987/2018-01-01/eng); [Reg. 988/2009, art. 1(16)](https://eur-lex.europa.eu/eli/reg/2009/988/oj/eng).

### V4.14z-a — Art. 57 Regulation 988/2009 source-citation correction

**Stato:** `done`
**Tipo:** `functional`
**Dipende da:** V4.14z (`done`, finding source-reference); non sblocca V4.14w.
**Scope:** correggere in Knowledge e Rule Pack il solo riferimento che introduce l'eccezione Art. 57(4), da Reg. 988/2009 art. 1(27) a art. 1(16), quindi aggiungere regressione sintetica e verificare il consumer Engine.
**Fuori scope:** mutamenti semantici o numerici, Art. 57 evidence bindings, completezza istituzionale, Annex VIII matching/versioning, root/order, dati personali o sblocco di V4.14w/V4.14/V4.15.
**Done quando:** il reviewer normativo conferma l'esatta versione post-fix; Knowledge documenta fonte/versione; Rule Pack ha entrambe le occorrenze corrette; test fallisce per la citazione errata e passa per quella corretta; suite Engine 0/0/0 e guardrail passano.
  **Gate 2026-10-18:** pre-review GO citation-only; implementazione e test mirato 1/1; dopo la correzione della frase Knowledge, review normativa exact-version GO limitato. Suite Engine 775/0/0/0, roadmap audit, schema planner, guardrail e diff check passano. La chiusura riguarda esclusivamente la citazione; V4.14w resta separatamente bloccata dai binding/evidenze del caso.

### V4.14z-b — Minimum technical contract for synthetic Art. 57 evidence binding

**Stato:** `blocked`
**Tipo:** `audit`
**Dipende da:** V4.14z, V4.14z-a (`done`); V4.14w resta `blocked`.
**Obiettivo:** definire il minimo contratto tecnico source-bound che consenta fixture sintetiche complete per il coordinamento Art. 57 senza presumere identificativi nazionali comuni, completezza dalla sola cardinalità o ordine di input.
**Scope:** proposta architetturale per legame al claim coordinato, completezza del set istituzionale, semantica root, validazione di tutti i parent/bound c14n-v4 e casi adversariali; successivo controllo normativo exact-version.
**Fuori scope:** cambi Rules/Engine o calcoli, dati personali/casi reali, classificazione eseguibile di schemi Annex VIII, sblocco automatico di V4.14w.
**Done quando:** architetto propone un contratto minimo implementabile e trade-off; reviewer normativo conferma che il disegno non inventi obblighi o automatismi e che i gap non provati restino fail-closed; il passo implementativo seguente è circoscritto e testabile. In caso di NO-GO o timeout, registrare il blocker preciso.
- **Selezione 2026-10-18:** roadmap audit OK (`current=V4.14z-a`, `functional_since_audit=1`, `audit_due=false`). Nessun incremento `planned` è eleggibile per il calcolo complessivo: V4.14w/x e V4.14 restano bloccati; V4.15 dipende da prerequisiti non completati. Selezionato questo audit abilitante dopo i NO-GO sulla completezza/binding Art. 57.
- **Routing:** `high/fo_architect` per il trade-off dati/evidence graph; poi `critical/fo_normative_reviewer` per la proposta esatta. Budget ordinario massimo due deleghe per questo incremento.
  - **Stato del gate:** architetto ha restituito GO limitato sulla forma tecnica. Reviewer normativo exact-version: NO-GO per contratto probatorio completo, GO condizionato sull'impostazione dopo chiarimenti; nessuna implementazione avviata.
  - **Proposta candidata v0.1 (2026-10-18):** manifest di coordinamento incorporato e root versionato nuovo; binding al medesimo manifest con riferimenti nazionali locali distinti; attestazione source-bound del set esatto; last-state senza inferenza da ordine; c14n-v4 limitato a 1 parent/1 bound; Annex VIII fail-closed. Proposta tecnica, non normativa.
  - **Esito review normativa:** NO-GO per approvare v0.1 come contratto probatorio completo. Coordinated benefit da definire come oggetto comune di coordinamento, non identità delle prestazioni nazionali. `attested_complete` richiede un criterio documentale verificabile (fascicolo/distribuzione contact institution, riscontri di invio, risposte/periodi, riconciliazione con claimant); possibili istituti o periodi irrisolti restano `not_assessed + data_gaps`. Per art. 57(3), attestare condizioni per ciascun istituto e sollievo di tutti; last-state non identifica da solo il payer, che richiede determinazione separata. Gli stati interni non sono attestazioni prescritte né prova legale sufficiente da soli. Annex VIII/c14n-v4 sono solo guardrail tecnici.
  - **Stop e prossimo prerequisito:** v0.2 con i chiarimenti e nuovo gate normativo exact-version; il budget di due deleghe sostanziali è esaurito, quindi occorre nuova autorizzazione prima di ogni ulteriore delega. Nessun runtime o fixture di calcolo in questo incremento.

### V4.14z-c — Evidence-bound Art. 57 v0.2 contract clarification

**Stato:** `done`
**Tipo:** `audit`
**Dipende da:** V4.14z-b (NO-GO v0.1 registrato); fonti primarie UE per artt. 1, 52, 57 e procedura artt. 46-48.
**Obiettivo:** redigere v0.2 della specifica documentale in risposta ai finding exact-version v0.1 e ottenere un nuovo gate normativo prima di qualsiasi fixture o runtime.
**Scope:** oggetto comune di coordinamento non identitario; criterio prudenziale documentale e fail-closed per set istituzionale; prove per Art. 57(1)/(3); determinazione distinta dell'istituto pagatore; distinzione tra legge e controlli interni.
**Fuori scope:** regole eseguibili, codice, fixture di calcolo, date individuali, dati personali, classificazione reale Annex VIII, sblocco V4.14w/V4.14.
**Done quando:** review normativa exact-version v0.2.2; suite completa Engine con 0 failure/errori/skipped; roadmap audit, schema planner, execution guardrails e diff check passano. GO documentale non si trasferisce a runtime.
**Stop:** se il criterio proposto non è supportato dalle fonti o non consente di delimitare i gap, lasciare l'incremento `blocked`; nessun test end-to-end viene dichiarato disponibile.

- **Selezione 2026-10-18:** roadmap audit OK (`current=V4.14z-b`, `functional_since_audit=1`, `audit_due=false`). Selezionato il minimo follow-up v0.2 dopo il NO-GO probatorio v0.1, su autorizzazione esplicita dell'utente.
- **Routing:** `critical/fo_normative_reviewer`, `gpt-5.6-sol`, `xhigh`; una review exact-version sulla candidata, budget ordinario massimo due eventi sostanziali (uno pianificato). Nessuna architettura runtime nuova: la soluzione tecnica resta il manifest v0.1 con criteri probatori circoscritti.
- **Fonti consultate il 2026-10-18:** Reg. 883/2004, testo consolidato disponibile EUR-Lex al 31/07/2019, artt. 1(p)-(q), 52, 57; Reg. 987/2009, artt. 46-48. Il criterio di completezza v0.2 è dichiarato controllo prudenziale del software, non forma o attestazione prevista dalla norma.
- **Review exact-version v0.2 (2026-10-18): NO-GO limitato.** GO per oggetto coordinato come procedura e per `supported_complete` quale criterio prudenziale interno non assoluto; GO per la separazione dello Stato dall'istituzione competente e per c14n-v4/Annex VIII come soli guardrail tecnici. NO-GO a usare `supported_complete` da solo come prova che sono considerate tutte le istituzioni interessate ex 57(3). Precisare anche riferimento temporale alla materializzazione del rischio per par.1 e alla data/evento in cui le condizioni si sono soddisfatte per ultimo (non data decisione); distinguere istituzione competente ex art.1(q) da soggetto materialmente pagatore.
- **Review exact-version v0.2.1 (2026-10-18): NO-GO limitato.** Il reviewer conferma che `supported_complete` è prudenziale e non è standard legale, ma non dimostra da solo che il set rappresenti tutte le istituzioni interessate ex 57(3); senza tale copertura stabilita per il caso, il ramo resta `not_assessed + data_gaps`.
- **Fix parent v0.2.2:** introdotto controllo separato `institution_scope_established` con fonte source-bound che espliciti perimetro completo, caso/oggetto e copertura temporale/procedurale. Lista di distribuzione, sole risposte o `supported_complete` non bastano; in assenza di prova il ramo 57(3) resta non valutabile.
- **Candidata v0.2.2:** in `docs/current-next-increment.md`, sezione “Contratto candidato v0.2.2 — correzione locale, gate pendente”. I verdetti v0.2 e v0.2.1 non si trasferiscono alla versione successiva.
- **Stato gate:** GO limitato alla specifica documentale v0.2.2 da `fo_normative_reviewer` Sol/xhigh. Rimane un suggerimento redazionale non bloccante sulla confrontabilità temporale degli Stati candidati. Suite Engine completa **775 test, 0 failure, 0 errori, 0 skipped**; roadmap audit, schema planner, execution guardrails e `git diff --check` superati. Incremento chiuso come audit documentale, senza fixture/runtime e senza sblocco di V4.14w/V4.14.
- **Riattivazione 2026-10-18:** dopo la candidata v0.2.2 con `institution_scope_established`, l'utente autorizza un solo ulteriore gate exact-version, entro il terzo evento di delega consentito. Scope strettamente read-only; nessun ulteriore ciclo autorizzato.

### V4.15 — Retirement bridge income composer

**Stato:** `blocked`
**Tipo:** `functional`

Comporre gli stream che finanziano il periodo tra riduzione/cessazione e pensioni.

- Dipende da: V4.14a, V4.14 (timeline pensionistica sbloccata), V4.2, V4.3 e RITA V2 source-bound.
- Repository: `engine`, `rules`, `workspace`.
- Output: `retirement-bridge-timeline/v1`.
- Stream: reddito proprio residuo, coniuge, affitti, RITA, pensioni gia' attive, liquidita'/asset withdrawals e altri flussi espliciti.
- Test: RITA con start/end, asset vincolato, reddito coniuge, affitto, gap di eleggibilita', doppio conteggio.
- Done quando: il bridge e' una timeline mensile di stream con disponibilita' e trattamento gross/net espliciti.

Bloccata: l'audit V4.14a ha rilevato lacune source-bound su entitlement/payment e basi gross/net; V4.14 resta bloccata e il contratto RITA disponibile e' `rita-options/v1`, che produce soltanto opzioni lorde teoriche senza accettazione/schedule individuale. Il GO documentale V4.14z-c non rimuove questi prerequisiti.

### V4.15a — RITA V2 source and retirement-bridge readiness audit

**Stato:** `done`
**Gate:** GO limitato alla specifica documentale RITA stream v0.1; nessun GO per Rules/Engine o V4.15
**Tipo:** `audit`
**Dipende da:** V4.14z-c (`done`, specifica documentale Art. 57); V4.15 bloccata dai prerequisiti pensionistici e RITA.
**Obiettivo:** delimitare la versione source-bound RITA consumabile dal bridge, distinguendo l'opzione lorda stimata dal diritto individuale, dall'accettazione e dai pagamenti.
**Scope:** fonte vigente D.Lgs. 252/2005 art. 11; Knowledge/Rule Pack/servizio/test RITA esistenti; input, output, date, schedule, gross/net, provenance e data gaps del futuro stream bridge.
**Fuori scope:** aggiornare eleggibilità o aliquote; modificare Knowledge/Rules/Engine; importi/date individuali; accesso al workspace; rimuovere il blocco V4.14w/V4.14.
**Done quando:** la specifica documentale esatta riceve review normativa indipendente, i gap normativi/di fondo sono dichiarati, il roadmap audit, schema planner, execution guardrails e diff check passano. Nessuna suite di calcolo è pertinente se non cambia codice/regole/fixture.
**Fonti consultate 2026-10-18:** Normattiva, D.Lgs. 252/2005 art. 11, testo in vigore dal 28-06-2026 al 31-12-2026; commi 4, 4-bis, 4-ter, 4-quater e 4-quinquies. La RITA è distinta dalle nuove prestazioni del comma 3-bis, soggette alle proprie decorrenze transitorie 2026. URL ufficiale registrato in `current-next-increment.md`. La verifica parent non equivale al gate indipendente.
- **Selezione 2026-10-18:** roadmap audit OK (`current=V4.14z-c`, `functional_since_audit=0`, `audit_due=false`). V4.15, primo funzionale planned, è stato marcato blocked perché V4.14 e RITA V2 non soddisfano i prerequisiti dichiarati in current-next; selezionato il più piccolo audit abilitante, senza saltare la sequenza.
- **Routing:** `critical/fo_normative_reviewer`, `gpt-5.6-sol`, `xhigh`; dopo l'autorizzazione esplicita dell'utente del 2026-10-18 è stato registrato un nuovo gate con budget di una sola delega. Nessun runtime o calcolo.
- **Candidate v0.1:** il bridge consuma solo stato e schedule RITA attestati da evidenza del fondo (eligibility status, domanda, accettazione, dates/schedule, importo lordo, base fiscale se nota, issuer, coverage e refs). Non inferire accettazione da cessazione/domanda né netto da importo lordo. Il servizio V1 produce opzioni teoriche lorde, non conferma disponibilità individuale.
- **Esito gate:** dopo nuova autorizzazione, il reviewer indipendente è rimasto `running` per 60 secondi e non ha restituito un verdetto. L'utente ha autorizzato un ulteriore tentativo con finestra ampliata a 180 secondi; anche questo si è chiuso senza verdetto. Il parent ha verificato la versione ufficiale Normattiva ma tale verifica non sostituisce il gate. Esito `pending`, non NO-GO. Nessun GO per Knowledge/Rules/Tests/Engine.
- **Retry completato (2026-10-18):** ulteriore autorizzazione esplicita dell'utente; una review normativa read-only entro la finestra bounded massima di 5 minuti ha prodotto il GO limitato riportato sotto.
- **Stop:** V4.15 e V4.14 restano bloccate; non esiste ancora un test di calcolo pensionistico end-to-end.
- **Esito review exact-version (2026-10-18): GO limitato** alla specifica documentale RITA stream v0.1 per Italia e art. 11 vigente 28-06-2026–31-12-2026. Domanda/accettazione, acceptance/start programmato/primo pagamento sono distinti; prove, schedule e accredito individuale restano source-bound al fondo. Il comma 3-bis e le sue decorrenze transitorie sono fuori dal contratto RITA. Nessuna approvazione per eleggibilità individuale, regole/servizio, netto fiscale, fixture, runtime o V4.15. Le regressioni richieste per un futuro incremento eseguibile sono riportate in `current-next-increment.md`.
- **Verifiche di chiusura:** suite completa Engine **775 test, 0 failure, 0 errori, 0 skipped**; planner schema, roadmap audit, execution guardrails e `git diff --check` passano. V4.15 e V4.14 restano bloccate; non esiste ancora un test di calcolo pensionistico end-to-end.

### V4.15b — Source-bound RITA fund-stream intake and validation

**Stato:** `done`
**Tipo:** `functional`
**Dipende da:** V4.15a (`done`, GO documentale limitato alla specifica RITA stream v0.1); non rimuove i prerequisiti V4.14 che bloccano il composer V4.15.

Implementare il minimo intake question-first, workspace-local e deterministico per normalizzare un flusso RITA esplicitamente documentato/accettato dal fondo secondo la specifica RITA stream v0.1 già revisionata. Contratto candidato: `rita-fund-stream/v1`; conservare separati richiesta, accettazione, schedule, pagamenti attestati, lordo/periodicità, stato fiscale, issuer, coverage/as-of e source refs. Validare date, importi e coerenza documentale senza decidere eleggibilità legale o fondo-specifica.

**Fuori scope:** modifiche alle soglie/eligibility `rita-rule-pack/v1`; calcolo RITA, importi, netto, rendimenti o entitlement pensionistico; inferenza di accettazione/pagamento da richiesta o cessazione; composizione `retirement-bridge-timeline/v1`; accesso a dati personali fuori da `family-office-workspace/`; sblocco V4.14/V4.15.

**Done quando:** Knowledge/contratto tecnico, CLI wizard question-first e validator Engine producono un record source-bound con `data_gaps` espliciti e nessuna derivazione legale; fixture sintetiche coprono prove mancanti/confliggenti e validazione date/importi; test mirati, suite Engine completa 0/0/0, review tecnica indipendente Terra/high, planner schema, roadmap audit, guardrails e diff-check passano. Se l'implementazione richiede semantica normativa nuova, fermarsi `blocked` per review Sol/xhigh.

**Gate (2026-10-25):** corrective pass bounded sui tre finding residui; test mirati 16/0/0 e suite Engine completa 797/0/0/0; schema planner, roadmap audit, execution guardrails e diff-check passano. Review tecnica indipendente exact-version `GO`: digest legato allo snapshot e fail-closed su mutazione, conflitti cronologici globali fail-closed, `benefit_type=other` non promosso. Il gap non bloccante sul timing del chiamante CLI non cambia il verdetto sul validator; nessun effetto sul blocco V4.15 per i prerequisiti V4.14.

### V4.14w-a — Art. 57 evidence-binding runtime fail-closed slice

**Stato:** `blocked`
**Tipo:** `functional`
**Dipende da:** V4.14w NO-GO; V4.14z-c v0.2.2 GO documentale limitato. Il GO documentale non approva il runtime.
**Obiettivo:** correggere i finding runtime su binding del medesimo caso/beneficio coordinato, coerenza dei record Art. 57(3), fail-closed della completezza e validazione integrale della grammatica c14n-v4.
**Scope:** Rules/Tests/Engine deterministici e fixture esclusivamente sintetiche; introdurre una versione esplicita del contratto; conservare riferimenti nazionali namespaced e non confrontare ID nazionali tra loro; nessun payer inferito; Annex VIII resta `not_assessed + data_gaps` senza catalogo eseguibile completo e versionato.
**Fuori scope:** costruzione/review del catalogo eseguibile Annex VIII, nuove conclusioni normative, casi o dati personali, importi/date individuali, sblocco complessivo V4.14/V4.15.
**Done quando:** tutti i finding inclusi hanno regressioni; suite completa Engine termina con 0 failure, 0 errori e 0 skipped; review normativa indipendente dà GO limitato all'esatta versione runtime; roadmap audit, planner schema, execution guardrails e diff check passano. In caso contrario resta `in_progress`/`blocked`.
**Selezione 2026-10-18:** audit roadmap OK; selezionato dopo che l'utente ha autorizzato di procedere allo sblocco di V4.14. Budget di delega ordinario massimo due eventi (implementazione e review exact-version). V4.14 resta `blocked` fino a chiusura dei finding V4.14w e degli ulteriori gap nazionali.
**Review exact-version v0.18:** primo tentativo `pending` dopo 5 minuti; retry autorizzato dall'utente il 2026-10-18 entro un ulteriore timebox massimo di 5 minuti con esito `NO-GO` limitato alla candidata `v0.18 / fo-art57-c14n-v4`. Finding: self-attestation di completezza senza prova verificata del perimetro/issuer/copertura; record istituzionali con soli booleani e riferimenti generici invece di periodi, durata e assenza di diritto autonomo source-bound; last-State senza legislazione/condizioni e prova comparativa della soddisfazione per ultima; Rule Pack senza richiamo al Reg. 987/2009 art. 47. Confermati non-inferenza del payer, c14n-v4 e fail-closed Annex VIII. Il test mirato tentato dal reviewer non ha raggiunto le asserzioni: sandbox read-only ha negato scrittura nella temp directory. Nessun GO runtime; V4.14w-a e V4.14 restano `blocked`. Fix e nuovo gate richiedono autorizzazione separata.

**Retry reviewer exact-version (2026-10-18):** `NO-GO` confermato per `v0.18 / fo-art57-c14n-v4`. Con permesso per scrittura temporanea, test mirato 28/28 OK; la suite completa 775/0/0/0 resta quella eseguita prima del retry. I rilievi probatori P0/P1 restano invariati, quindi V4.14w-a e V4.14 restano bloccate. Nessuna modifica codice.

### V4.14w-b — Source-bound Art. 57 institutional evidence completion

**Stato:** `blocked`
**Gate:** review exact-version v0.19/c14n-v4 `NO-GO` limitata.
**Tipo:** `functional`
**Dipende da:** V4.14w-a (`blocked`, NO-GO exact-version v0.18/c14n-v4); V4.14z-c v0.2.2 (`done`, GO documentale limitato).
**Obiettivo:** materializzare i requisiti source-bound del contratto v0.2.2 già approvato e correggere i finding P0/P1 senza introdurre interpretazioni legali nuove.
**Scope:** candidata runtime v0.19/c14n-v4; prova del perimetro completo con issuer, data e copertura source-bound e verifica operatore; per ogni istituto periodi pertinenti, durata/comparatore, legislazione e verifica distinta del diritto autonomo; last-State con condizioni/legislazione ed evidenza dell'evento, richiedendo comparabilità attestata senza dedurre automaticamente quale Stato sia legalmente ultimo; traceability Rules agli artt. 46-48 Reg. 987/2009, in particolare art. 47(4)-(7); regressioni sintetiche Knowledge → Rules → Tests → Engine.
**Fuori scope:** catalogo Annex VIII eseguibile, match/non-match positivi, inferenza di payer o istituzione competente, nuove regole nazionali, dati personali, importi/date individuali e sblocco complessivo V4.14/V4.15.
**Done quando:** ogni finding ha regressione eseguibile e ramo fail-closed; suite completa Engine con 0 failure/errori/skipped; schema planner, roadmap audit, execution guardrails e diff-check passano; reviewer normativo indipendente dà GO limitato alla precisa versione v0.19. In assenza di un gate GO, resta `in_progress`/`blocked`.

**Esito reviewer (2026-10-18):** reviewer Sol/xhigh read-only concluso entro 5 minuti; autorizzata la directory temporanea dedicata. NO-GO limitato: P1 riferimenti `resolved_source_refs` e prove last-State non risolti/verificati su registry (issuer/contenuto/digest/copertura); P1 `article_57_1_relief_result` non riconciliato con le prove e non capace di rappresentare correttamente i casi non-relief; P2 `source_segment_id` del sample duration discordante dal digest c14n. Confermati Art. 47(4)-(7), c14n-v4, Annex VIII fail-closed, payer non inferito e human review. Servono nuova autorizzazione e regressioni specifiche prima di qualsiasi altro gate; V4.14 resta bloccata.

### V4.14w-c — Art. 57 v0.20 evidence registry reconciliation

**Stato:** `blocked`
**Tipo:** `functional`
**Dipende da:** V4.14w-b (`blocked`, NO-GO exact-version v0.19/c14n-v4).

Chiudere i tre finding circoscritti del NO-GO v0.19: risoluzione dei `resolved_source_refs` contro un evidence registry source-bound con issuer/digest/copertura, riconciliazione deterministica del relief result Art. 57(1) inclusi i casi non-relief, e digest c14n-v4 coerente nel sample. Il registry del candidato è sintetico e dimostra solo il contratto tecnico; Annex VIII resta fail-closed e nessun payer o diritto viene inferito.

**Gate:** suite Engine 778/0/0 e verifiche di governance passano. Review normativa exact-version v0.20/c14n-v4 (retry autorizzato, 2026-10-20, timebox 5 minuti): NO-GO P1 sul registry. ID duplicati sovrascritti, digest non legato al contenuto, issuer del perimetro non confrontato col manifest e intervallo temporale non verificato; regressioni richieste. Relief Art. 57(1), non-relief, c14n sample, Annex VIII fail-closed e non-inferenza payer superati. V0.20 non approvata; V4.14w-c resta `blocked`.

### V4.14w-d — Art. 57 v0.21 registry content and coverage binding

**Stato:** `blocked`
**Tipo:** `functional`
**Dipende da:** V4.14w-c (`blocked`, NO-GO exact-version v0.20/c14n-v4); questo slice non approva né sblocca v0.20.

Chiudere esclusivamente i finding P1 del reviewer: ID registry e source refs univoci; digest SHA-256 strict verificato contro il contenuto UTF-8; issuer del perimetro uguale all'issuer del manifest; coverage registry che comprenda tutto l'intervallo temporale dichiarato dal perimetro. Ogni assenza, duplicato o mismatch resta fail-closed. Contenuti di casi reali restano nel workspace personale; fixtures sintetiche soltanto. Nessuna nuova conclusione legale, payer inference o esecuzione Annex VIII.

**Gate:** Knowledge v0.21 → Rules → test → Engine; test mirati 138/0/0 e suite completa Engine 779/0/0/0; roadmap audit, execution guardrails, schema planner e diff-check passano. Review normativa exact-version v0.21/c14n-v4: NO-GO P1. Il registry viene bypassato nei rami non-relief/Annex e non è riconciliata l'evidenza Art.57(1) root con quella per istituzione. Runtime non approvato; il fix richiede v0.22, regressioni end-to-end e nuovo gate. Budget del ciclo corrente esaurito; V4.14w resta bloccata.

### V4.14w-e — Art. 57 v0.22 end-to-end fail-closed reconciliation

**Stato:** `done`
**Esito precedente:** il NO-GO exact-version v0.22/c14n-v4 resta storico per il pacchetto privo delle regressioni pubbliche v0.23; il gate combinato V4.14w-g ha verificato il controllo runtime.
**Gate review:** GO indipendente limitato al pacchetto combinato runtime v0.22/c14n-v4 con regressioni pubbliche e citation v0.23.
**Tipo:** `functional`
**Dipende da:** V4.14w-d (`blocked`, NO-GO exact-version v0.21/c14n-v4); v0.21 resta non approvata.

Chiudere i due finding P1 senza introdurre semantica legale: tutti i rami decisionali devono validare manifest e registry prima di ritornare, inclusi Annex matched e non-relief; il record root e quello della stessa istituzione devono concordare sui predicati source-bound Art.57(1) (durata, comparatore, legislazione applicabile, diritto autonomo, relief). Qualunque duplicato, digest/issuer/coverage invalido o contraddizione produce `not_assessed + data_gaps`.

**Gate:** test mirati 139/0/0/0 e suite Engine 780/0/0/0; successivamente le regressioni end-to-end richieste sono state eseguite attraverso il builder pubblico e la suite Engine è risultata 781/0/0/0. La review combinata Sol/xhigh ha concluso `GO` senza finding bloccanti: registry validato prima degli esiti Annex/non-relief; evidenza Art.57(1) root/per-istituzione riconciliata; output fail-closed `not_assessed + data_gaps`, senza importi pro-rata o inferenza payer. L'entry citation v0.23 è esplicitamente asserita. GO limitato al runtime v0.22/c14n-v4 esaminato insieme alle regressioni/citation v0.23; non è approvazione del catalogo Annex VIII production o di casi individuali. I NO-GO storici v0.21 e del precedente package v0.22 restano nel decision log.

### V4.14w-f — Art. 57 v0.23 public-boundary regressions

**Stato:** `done`
**Tipo:** `functional`
**Dipende da:** V4.14w-e (controlli runtime v0.22 ora valutati nel gate combinato); nessun GO si trasferisce oltre il pacchetto esaminato.

Chiudere esclusivamente i finding della review v0.22: eseguire le regressioni al confine pubblico `build_it_es_eu_pension_pro_rata` per registry invalido con Annex matched e non-relief e mismatch root/istituzione in entrambe le direzioni; verificare lo snapshot pubblico `not_assessed`, `data_gaps` non vuoti, assenza di pro-rata calcolabile e nessuna payer inference. Aggiungere l'assert esplicito del documento v0.23 nel citation index. Mantenere fixture sintetiche e c14n-v4; modifiche runtime solo se i test pubblici dimostrano un difetto.

**Gate:** completato con test mirati 140/0/0/0 e suite Engine 781/0/0/0, planner schema, roadmap audit, execution guardrails e diff-check OK; review indipendente Sol/xhigh `GO` limitato alla candidata v0.23/c14n-v4 per regressioni public-builder/output e citation coverage. I test verificano snapshot restituito e scritto, `not_assessed`, `data_gaps`, nessun importo pro-rata e nessuna payer inference. Nessuna modifica runtime necessaria.
**Limite del GO:** non approva autonomamente Annex production e non sblocca V4.14w/V4.14; il distinto gate runtime combinato è V4.14w-g.

### V4.14w-g — Art. 57 runtime v0.22 exact-version gate

**Stato:** `done`
**Tipo:** `functional`
**Dipende da:** V4.14w-e (controlli runtime v0.22) e V4.14w-f (`done`, regressioni pubbliche/citation v0.23).

Review normativa read-only dell'esatto pacchetto: Knowledge runtime v0.22, Rule Pack/runtime `v0.22`/`fo-art57-c14n-v4` e regressioni/citation v0.23. La review deve stabilire se le regressioni v0.23 risolvono i finding P1/P2 rispetto al medesimo runtime, senza estendere il GO ad Annex production, all'intera V4.14w/V4.14 o a casi individuali. Nessuna modifica codice/regole in questo gate.

**Gate:** verdict indipendente Sol/xhigh `GO` limitato all'esatta combinazione runtime v0.22/c14n-v4 con test/citation v0.23; evidenza test parent 140/0/0/0 e suite completa Engine 781/0/0/0; schema planner, roadmap audit, execution guardrails e diff-check passano. Nessuna modifica runtime in questo gate. Restano fuori approvazione Annex VIII production, conclusioni individuali e sblocco complessivo V4.14w/V4.14.

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
