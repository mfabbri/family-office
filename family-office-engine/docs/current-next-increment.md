# Current Next Increment

## Incremento corrente — V4.14w — Source-bound Art. 57 duration in the EU pension consumer

**Stato:** `in_progress` — suite Engine 774/0/0/0; review normativa finale evento 11 NO-GO; budget autorizzato esaurito, runtime non approvato
**Tipo:** `functional`
**Contratto normativo esatto:** Art. 57 `v0.17`, `fo-art57-c14n-v4`.

### Esito del ciclo correttivo finale (2026-10-17) — NO-GO

Il ciclo autorizzato ha usato l'evento 10 per la correzione e l'evento 11 per la review indipendente read-only. I moduli mirati passano 127/127; la suite Engine completa passa **774 test, 0 failure, 0 errori, 0 skipped**. Roadmap audit, schema planner, execution guardrails (`in_progress`, 11 eventi) e `git diff --check` passano.

Il reviewer finale dà **NO-GO**. P0: completezza istituzionale assente/null/mismatch non porta sempre `not_assessed + data_gaps`; i record Art. 57(3) non provano l'appartenenza allo stesso caso/beneficio coordinato né la coerenza del risultato root; `matched_scheme_entry` non è verificata contro un elenco versionato dell'Annex VIII. P1: la validazione c14n-v4 controlla solo il primo parent/bound e può ignorare bound successivi malformati. Il reviewer conferma invece root v0.17 e rifiuto di `schema_version`, grammatica transitoria completa/fail-closed, data del diritto autonomo legata al rischio root e rimozione del claim consumer di pagamento separato.

Il contratto attuale non definisce sufficientemente alcuni binding probatori: non si deve inventare uguaglianza tra identificativi nazionali né materializzare un match Annex senza la tabella/versione primaria. Tutti gli 11 eventi autorizzati sono esauriti. V4.14w resta `in_progress`; runtime non approvato e ulteriori modifiche/review richiedono nuova autorizzazione esplicita.

### Riesecuzione e review fallback precedente (2026-10-17) — NO-GO

Il test CLI `test_main_planning_it_es_eu_pension_build_uses_default_theoretical_snapshot` inizialmente falliva perché il sample Art. 57 non includeva i nuovi root bindings/versione Annex; aggiornato il fixture sintetico al contratto corrente e al rule pack, il test passa 1/1. Suite Engine completa: **772 test, 0 failure, 0 errori, 0 skipped**. Roadmap audit, schema planner, execution guardrails (`in_progress`, 9 eventi) e `git diff --check` passano.

La review indipendente fallback ha dato **NO-GO**. P0: grammar c14n-v4 incompleta (accettazione di `schema_version` al root, transitorio ridotto e `null` che solleva eccezione, rischio autonomo non legato alla data root); record Art. 57(3) e completezza istituzionale non legati a un insieme coerente di benefici/legislazioni. P1: data/versione Annex non legata alla data di rischio; manca `matched_scheme_entry`, lo stato di match ammette stringhe arbitrarie e la chiave di prova non segue il contratto. La review ha verificato che il claim consumer generale di pagamento separato non è più presente. Il reviewer non ha modificato file; ha indicato che i test mirati nella propria sessione erano bloccati da ACL, ma la suite completa è stata eseguita dal parent e passa.

L'evento 9 è stato seguito dal ciclo 10/11 descritto sopra; i budget autorizzati sono esauriti. Non usare il consumer per decisioni pensionistiche.

### Ciclo correttivo autorizzato (2026-10-17) — concluso con NO-GO

Il `procedi` ha autorizzato esattamente gli eventi 10 `fo_implementer` e 11 `fo_normative_reviewer` indipendente, read-only, massimo 5 minuti. Entrambi conclusi; esito normativo finale NO-GO come sopra. Nessuna modifica ulteriore è autorizzata senza nuovo consenso.

### Obiettivo e piano

Rimuovere il predicato eseguibile basato su `spain_months < 12` nel consumer UE Art. 57 e sostituirlo con dati source-bound deterministici coerenti con il contratto v0.17. Ordine obbligatorio: verificare/aggiornare Knowledge con fonte e periodo; versionare il rule pack; aggiungere fixture/test sintetici per confini, unknown e interazioni; integrare il consumer Engine. Nessuna conversione normativa viene inventata e nessun mese di calendario sostituisce la durata legale.

Il percorso deve restare fail-closed: senza schema/legge/versione, periodi pertinenti/unità/base, durata e comparatore, diritto autonomo nazionale, stato Allegato VIII o insieme delle istituzioni sufficientemente provati, produrre `not_assessed + data_gaps`; mai assumere 12 mesi, zero, esenzione o pagatore. Separare eligibility nazionale, eccezione art. 57, inclusione ex 57(2) nel teorico, pro-rata downstream e obbligo/pagatore ex 57(1)/(3). `human_review_required: true` resta invariato.

**Fuori scope:** ricerca della prima eligibility mensile spagnola, percorso italiano pre-1996, reducer della prima data IT/ES/UE, decorrenza/riconoscimento/pagamento, importi individuali, CLI/workspace e dati personali. Anche a chiusura V4.14w la timeline complessiva V4.14 resta `blocked` finché gli altri percorsi non sono valutati.

**Test:** durata `<`, `=` e `>` un anno; mesi civili non equivalenti alla durata legale; ogni predicato isolato; schema Allegato VIII `true/false/unknown`; overlap/conversione ignoti; tutte le istituzioni esonerate e last-state mancante; mismatch v0.17/c14n-v4 e rifiuto degli esempi legacy v0.16/c14n-v3; invarianti output separati.

**Gate:** test mirati, suite completa Engine con 0 failure/errori/skipped, review normativa post-implementazione exact-version, audit roadmap, planner schema, guardrail e `git diff --check`. In caso di dato o ramo non supportato, mantenere `not_assessed + data_gaps`, non ampliare lo scope.

### Esito della verifica V4.14w (2026-10-16) — NO-GO, incremento aperto

I 21 test mirati passano fuori sandbox; `py_compile` e `git diff --check` passano. La suite Engine completa ha eseguito 766 test ma ha 3 failure e 5 errori: il consumer coordinamento legacy richiede ancora il vecchio campo `article_57_under_one_year`, mentre i fixture/consumer downstream senza assessment source-bound ora diventano `blocked_missing_inputs`. La suite non soddisfa il gate e nessun failure è waivato.

La review normativa indipendente sul diff esatto ha dato **NO-GO limitato**. Blocker principali: confronto razionale errato (confronto lessicografico invece che per cross-multiplication); hash di durata non equivale a validazione c14n-v4 completa né lega la durata al preimage; mancano binding obbligatori di giurisdizione, beneficio, schema, legislazione/versione e validità/transitorio; Art. 57(3) si basa su aggregati non derivati e può inventare il payer; short-circuit ternario non conforme; il pack non include la provenienza autentica/versionata del Reg. 988/2009 per Allegato VIII; test insufficienti rispetto al contratto esatto. Nessuna review successiva o modifica correttiva è autorizzata implicitamente da questo NO-GO. V4.14w resta `in_progress`; il consumer non va usato per decisioni pensionistiche.

### Riesecuzione dopo il ciclo correttivo (2026-10-16)

Risolti i 5 errori del consumer legacy migrando la validazione al blocco `article_57_source_bound`; corretta la comparazione razionale con cross-multiplication e aggiunta regressione `2/3 < 1`. Aggiornate le sole fixture sintetiche downstream con assessment Art. 57 source-bound; corretto l'hash del sample in base al preimage. Moduli mirati: 37 test OK; test CLI del sample: 1 OK; suite Engine completa: **768 test, 0 failure, 0 errori, 0 skipped**. Il NO-GO precedente vincola il diff allora esaminato e non è superato da questi test: il runtime resta non approvato e V4.14w resta `in_progress` finché una nuova review normativa exact-version non verifica le correzioni e i finding residui.

### Review normativa exact-version post-fix (2026-10-16) — NO-GO

Il quarto e ultimo evento di delega autorizzato dall'utente ha esaminato in sola lettura il diff corrente e ha confermato la correzione del confronto razionale, ma **non** ha approvato l'implementazione. Restano bloccanti: (P0) validazione grammaticale e binding semantico c14n-v4 incompleti, inclusi razionali booleani/negativi; (P0) pagatore Art. 57(3) basato su aggregati dichiarati anziché record istituzionali verificati; (P1) ordering non sempre fail-closed; (P1) provenance del Reg. 988/2009 e versione applicabile dell'Allegato VIII assenti dal rule pack; (P1) il secondo consumer può ancora affermare un pagamento non dimostrato. Copertura insufficiente per date, record, input malformati e rami negativi.

La delega autorizzata è esaurita. V4.14w resta `in_progress`; nessuna decisione individuale o runtime può basarsi sull'implementazione. Un ulteriore ciclo di correzione/review richiede nuova autorizzazione esplicita. Fonti citate dal reviewer: [Reg. 883/2004, Art. 57](https://eur-lex.europa.eu/eli/reg/2004/883/2019-07-31/eng), [Reg. 988/2009](https://eur-lex.europa.eu/eli/reg/2009/988/oj/eng), [Reg. 987/2009, artt. 12–13](https://eur-lex.europa.eu/eli/reg/2009/987/2018-01-01/eng).

### Secondo ciclo correttivo e review finale (2026-10-16) — NO-GO

Il ciclo autorizzato con “procedi” ha usato l'evento 5 per implementazione e l'evento 6 per review normativa. I test mirati sono 39/39. La suite completa ha inizialmente trovato un test di freshness che valutava al 13 ottobre una fonte correttamente verificata il 16 ottobre; è stato aggiornato solo l'`as_of` del test, senza retrodatare la fonte. Riesecuzione completa: **770 test, 0 failure, 0 errori, 0 skipped**.

Il reviewer conferma miglioramenti su binding duration-mode, validazione dei razionali, uso dei record istituzionali e provenance Reg. 988/2009, ma dà **NO-GO** perché: (P0) il consumer non implementa la grammar c14n-v4 completa né i root bindings di Stato, beneficio, schema, istituzione, legislazione/versione, validità, risk/assessment date e transitorio; (P0) per Art. 57(3) non è dimostrata la completezza di tutte le istituzioni interessate e gli esiti/order/evidenze non sono sufficientemente legati a beneficio e legislazione; (P1) le date di rischio e applicabilità Annex sono controllate solo per truthiness e non contro formato/validità del pack; (P1) il pack non materializza la versione/data applicabile dell'Allegato VIII e il runtime accetta stringhe arbitrarie; (P1) il consumer esporta ancora `separate_payment_by_country: true` senza assessment Art. 57. Mancano inoltre regressioni avverse per NFC, date, insiemi multi-istituzione, mismatch Annex e assenza totale di claim di pagamento.

Tutti i sei eventi del budget sono esauriti. V4.14w resta `in_progress`, il runtime non è approvato; ulteriori correzioni e review richiedono una nuova autorizzazione esplicita. L'esito completo e i riferimenti puntuali sono nella review finale del 2026-10-16 e nel planner; nessun dato individuale è stato usato.

## Incremento completato — V4.14v — Art. 57 source-bound duration implementation authorization gate

**Stato:** `done` — GO limitato pre-implementazione sulla sola specifica v0.17; runtime escluso
**Tipo:** `audit`
**Versione esatta sotto review:** contratto Art. 57 `v0.17` in questo documento, sezione “Contratto v0.17 — numeri esatti e revisione umana obbligatoria”.

### Obiettivo e piano

Rimuovere il blocker eseguibile più circoscritto di V4.14: il rule pack UE mantiene `less_than_one_year_threshold_months: 12`, mentre il contratto v0.17 documenta durata assicurativa legalmente pertinente, unità source-bound e conversioni solo per scopo. La review indipendente deve stabilire se il contratto v0.17 è normativamente sufficiente come base per un successivo slice d'implementazione e se separa correttamente eligibility, diritto autonomo, inclusione nel teorico/pro-rata e obbligo di pagamento.

Il gate è unicamente read-only sulla versione esatta v0.17, con fonti primarie EUR-Lex e timebox massimo di 5 minuti. Include la pertinenza di periodi, unità/conversioni e overlap (Reg. 987/2009 artt. 12-13), diritto nazionale autonomo, Allegato VIII parte 2 e coordinamento inter-istituzionale ex art. 57(3). Esclude qualsiasi patch o approvazione automatica di Knowledge, Rules, Tests, Engine, CLI o runtime.

Dipendenze documentali: V4.14k/l/m/n/o/u `done`. V4.14 resta `blocked`; V4.14a e V4.15 non sono selezionabili finché il prerequisito non è rimosso.

**Esito review (2026-10-16): GO limitato pre-implementazione** sulla sola specifica v0.17/c14n-v4. È sufficientemente determinata per pianificare il futuro slice che rimuove il threshold `12`; nessuna approvazione di Knowledge/Rules/Tests/Engine o runtime. Il reviewer prescrive test che rifiutino i campioni legacy v0.16/c14n-v3 e conferma come blocker attuale il threshold nel pack/service/test.

**Chiusura verificata (2026-10-16):** suite Engine completa 762 test, 0 failure, 0 errori, 0 skipped; roadmap audit, planner schema, execution guardrails e `git diff --check` passano. Review exact-version v0.17 dà GO limitato pre-implementazione. Per il runtime è stato aperto il task envelope separato V4.14w, in ordine Knowledge → Rules → Tests → Engine. V4.14 resta blocked nel suo complesso.

## Incremento completato — V4.14u — Spanish eligibility temporal applicability and Annex VIII exclusions

**Stato:** `done` — audit documentale chiuso con GO limitato sulla versione v8 esatta; nessuna approvazione runtime
**Tipo:** `audit`
**Versione candidata esatta:** `spanish-first-eligibility-contract/v8`

Il terzo evento autorizzato dall'utente è stato usato per la review read-only v8: `fo_normative_reviewer`, conclusa entro 5 minuti. Nessun quarto evento, retry o v9 è autorizzato; l'esito non concede GO runtime.

### Contratto v8 proposto dopo NO-GO circoscritto v7

V4.14u preserva senza modifiche semantiche tutti i vincoli della v5 e aggiunge soltanto i due caveat del reviewer: applicabilità scheme-specific dell'art. 57(4)/Allegato VIII, parte 2, e coordinamento temporale/transitorio attorno al 1° maggio 2010. Nessuna modifica a Knowledge/Rules/Tests/Engine, nessun rule pack eseguibile, importo, pro-rata o valutazione individuale.

#### Gate scheme-specific — Reg. 883/2004 art. 57(4)

Prima di applicare qualsiasi ramo dell'art. 57(1)-(3), il dossier identifica in modo source-bound Stato, istituzione, regime specifico, prestazione/rischio e versione normativa applicabile alla data del fatto rilevante. Verifica quindi se quello specifico schema/prestazione ricade nell'Allegato VIII, parte 2, nella versione efficace per la valutazione. Non basta il nome del Paese, la categoria generica “old-age pension” o l'inclusione in Allegato VIII parte 1.

- Se l'inclusione in parte 2 è provata, l'art. 57 non si applica a quello schema: nessuna esenzione <1 anno o fallback basati su art. 57(1)-(3) per tale schema. La conseguenza sull'art. 51(3) non viene risolta per analogia: se la condizione non è determinabile indipendentemente dal rinvio all'art. 57, `not_assessed` + `data_gaps`.
- Se l'esclusione è provata attraverso la versione ufficiale completa dell'Allegato pertinente, il dossier può proseguire con la truth table v5, sempre subordinata agli altri requisiti.
- Se versione, schema o classificazione della prestazione mancano/sono ambigui, esito `not_assessed` + gap; non presumere che art. 57 sia applicabile o escluso.

Art. 57(4) e art. 52(5) non sono intercambiabili: il primo esclude l'intero art. 57 per gli schemi elencati; il secondo disciplina la non-applicazione del calcolo pro-rata per i medesimi schemi. La v8 non decide in astratto quali prestazioni spagnole o italiane siano incluse: richiede classificazione puntuale e fonte versionata.

#### Ambito temporale e disposizioni transitorie

Il Reg. 987/2009 art. 97 fissa l'entrata in vigore al 01/05/2010; il Reg. 988/2009 art. 2 ne coordina l'applicazione con l'entrata in vigore del regolamento di attuazione. Le relazioni EUR-Lex indicano il 01/05/2010 come data di sostituzione dell'art. 51(3) e di inserimento dell'art. 57(4). Il testo sostitutivo del 51(3) non può essere retrodatato automaticamente.

Il selettore temporale non usa il solo anno del periodo assicurativo né una regola binaria “prima = vecchio regolamento / dopo = nuovo regolamento”. Reg. 883/2004 art. 87(1)-(3),(5)-(7) e Reg. 987/2009 artt. 93-94 impongono di distinguere periodo/prestazione, contingenza, domanda e stato della liquidazione/revisione. Per ciascuno Stato interessato si registra la data di applicazione e la versione di Reg. 883/2004/988/2009/987/2009 e degli Allegati. La matrice minima è:

| Caso documentato | Regola di transizione da applicare | Output del contratto |
|---|---|---|
| Periodo di prestazione anteriore alla data d'applicazione | Art. 87(1): nessun diritto sotto il Reg. 883/2004 per il tratto anteriore | Separare quel tratto; non estendere a ritroso il testo modificato |
| Periodi assicurativi anteriori usati per un diritto maturato nel regime nuovo | Art. 87(2): i periodi anteriori sono presi in considerazione per determinare i diritti secondo il regolamento | Periodi ammessi come evidenza, ma non sono da soli il selettore della norma sul fatto causante |
| Contingenza anteriore, valutazione/diritto nel regime nuovo | Art. 87(3), fatto salvo il par. 1: può sorgere un diritto secondo il regolamento anche se la contingenza è precedente | Valutare le condizioni del nuovo regime per il periodo consentito; nessun esito automatico dalla sola data della contingenza |
| Contingenza anteriore alla data d'applicazione **e** domanda non liquidata prima di quella data **e** prestazioni dovute per un periodo anteriore | Tutte e tre le condizioni cumulative dell'art. 94(1) Reg. 987/2009: doppia liquidazione; Reg. 1408/71/accordi per il tratto anteriore e regolamento di base per il tratto dalla data d'applicazione; salvaguardia dell'importo più alto | Registrare i due segmenti normativi solo se l'intera congiunzione è provata; il confronto/importo non viene calcolato qui. Se un predicato manca o è ignoto, non attivare il ramo; gap se la prova è insufficiente |
| Pensione già attribuita prima e persona richiede revisione ai sensi dell'art. 87(5) | Art. 87(5)-(7): revisione su richiesta; entro due anni, effetto dalla data d'applicazione; oltre due anni, effetto dalla richiesta soltanto se il diritto non è decaduto/prescritto secondo legge documentata, salva norma nazionale più favorevole | Registrare data richiesta, confine dei due anni e fonte sullo stato del diritto. Se prescrizione/decadenza o legge applicabile non determinabile: `not_assessed` + `data_gaps`; nessun importo |
| Domanda qualificata di invalidità, vecchiaia o superstiti presentata dal giorno d'applicazione, per una stessa contingenza per cui una o più pensioni erano già state attribuite prima | Art. 94(2) Reg. 987/2009: la nuova domanda attiva il riesame d'ufficio secondo il regolamento di base; il riesame non può ridurre l'importo già attribuito | Separare l'evento di domanda dal riesame su richiesta ex art. 87(5); niente riesame spontaneo senza domanda qualificata e niente calcolo comparativo |
| Stato/data/award status o presupposti di transizione mancanti; sospensione per nazionalità/residenza o altro ramo transitorio non modellato | Verifica delle disposizioni specifiche (incluso art. 87(4) se pertinente) necessaria | `not_assessed` + `data_gaps`; niente default o conclusione individuale |

La matrice non equipara data dei periodi, contingenza, domanda, award status e decorrenza. Gli artt. 87(5) e 94(2) sono trigger distinti: richiesta di revisione personale vs nuova domanda che impone un riesame d'ufficio. Per i rami che richiedono importi o determinazioni amministrative l'output resta non calcolato. Nessuna norma è applicata retroattivamente per analogia. Se una condizione transitoria, versione dell'Allegato, stato di liquidazione, legge applicabile o data di applicazione territoriale non è determinabile: `not_assessed` + gap.

#### Regressioni contrattuali sintetiche richieste

1. Schema/prestazione presente in Allegato VIII parte 2 nella versione applicabile: art. 57 interamente disattivato, pur con durata <1 anno; non usare il fallback 57(3).
2. Schema non presente in parte 2, con prova completa: art. 57(1)-(3) disponibile secondo la v5. Inclusione solo in parte 1 o in art. 52(4) non equivale a esclusione ex 57(4).
3. Paese noto ma regime/prestazione o versione Annex ignoti: `not_assessed` + gap; nessun default.
4. Verificare a cavallo del 30/04/2010 e 01/05/2010 la decorrenza e l'applicazione degli artt. 51(3), 57(4) e dell'Allegato, distinguendo periodi/prestazione, contingenza, domanda e data applicativa nello Stato.
5. Coprire art. 87(1)-(3): prestazione per periodo anteriore; periodi contributivi anteriori conteggiati nel regime nuovo; contingenza anteriore valutata nel regime nuovo.
6. Coprire art. 94(1) con test indipendenti per ciascun predicato e combinazione: contingenza pre-data, domanda non liquidata, prestazione dovuta per periodo pre-data; solo la congiunzione attiva i due segmenti. Variare contingenza pre/post con domanda altrimenti identica.
7. Distinguere art. 87(5) revisione su richiesta da art. 94(2) nuovo claim che attiva riesame d'ufficio per prestazione precedentemente attribuita; testare evento-trigger e non-riduzione senza calcolo d'importo.
8. Art. 87(6)-(7): data esattamente al confine dei due anni, appena prima/dopo; per il ramo oltre termine provare diritto non decaduto/prescritto e legge applicabile, altrimenti `not_assessed` + gap.
9. Data/Stato/award status non provati, o invocazione di accordo bilaterale/deroga senza fonte: `not_assessed` + gap; conservare Annex VIII parte 2 true/false/unknown.
10. Conservare i test v5 su art. 57(1)-(3), LGSS, evidence coverage, multi-path, `human_review_required: true` e separazione eligibility/amount.

#### Fonti primarie e perimetro del gate

Verifica fonti iniziale: 2026-10-16. [Reg. 883/2004, EUR-Lex — artt. 57, 87, 91 e cronologia di modifica degli Allegati](https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=CELEX%3A32004R0883); [Reg. 988/2009, atto autentico — sostituzione art. 51(3), aggiunta artt. 52(5)/57(4) e art. 2](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32009R0988); [Reg. 987/2009, atto autentico — artt. 93-94 e 97](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32009R0987); [Reg. 988/2009, testo DOUE autentico, modifica Allegato VIII](https://eur-lex.europa.eu/eli/reg/2009/988/oj/eng/pdf). La versione completa dell'Allegato VIII e le modifiche ufficiali intervenute dopo la sua sostituzione devono essere ricostruite per la data e per lo schema concreto; una pagina consolidata o una lista parziale non certifica l'assenza di una voce.

Il gate normativo read-only v7 del 2026-10-16 ha dato **NO-GO limitato**; i finding bounded sono recepiti nella v8. La review indipendente v8 ha dato **GO limitato**: conferma la congiunzione art. 94(1), la distinzione art. 87(5)/94(2), la cautela art. 87(7), il gate scheme-specific art. 57(4)/Allegato VIII parte 2 e la matrice temporale. Confermate le regressioni contrattuali richieste. Non sono valutati schemi nazionali concreti, SEE/Svizzera, casi individuali, importi o effetti economici. Fuori scope e non approvati Knowledge/Rules/Tests/Engine, codice, calcoli e runtime.

### Verifica V4.14u

**Chiusura verificata (2026-10-16):** review indipendente esatta v8 conclusa con GO limitato entro 5 minuti; suite Engine completa 762 test, 0 failure, 0 errori, 0 skipped (ultima esecuzione completa); roadmap audit, schema planner, execution guardrails e `git diff --check` passano. V4.14u è `done` come audit documentale. I GO/NO-GO di questo incremento non approvano né sbloccano calcoli o runtime; V4.14v è il prossimo gate abilitante.

## Incremento completato — V4.14t — Spanish date-level contract v5 after normative NO-GO

**Stato:** `done` — audit documentale concluso con GO limitato alla specifica v5; nessuna approvazione runtime
**Tipo:** `audit`
**Versione candidata esatta:** `spanish-first-eligibility-contract/v5`

### Specifica v5 proposta

V4.14t aggiorna il solo contratto documentale per il possibile primo hecho causante di pensione contributiva ordinaria spagnola nel solo Régimen General. Mantiene i contratti precedenti non contestati, inclusi `applicant_intent` e la derivazione del path, e recepisce i tre finding v4 senza modifiche a Knowledge/Rules/Tests/Engine, calcoli o dati personali. Nessun risultato equivale a riconoscimento o decorrenza economica.

#### Reg. 883/2004 artt. 51(3) e 57

Il record per ogni Stato/istituzione conserva i periodi certificati secondo la legislazione competente, data di materializzazione del rischio, rischio/prestazione, regime, prova e risposta istituzionale. Per art. 57 la macchina degli stati è:

1. Per ciascuna istituzione, determinare se i periodi compiuti sotto la sua legge e accreditati al materializzarsi del rischio durano **meno di un anno** e se, considerando soltanto quei periodi, non nasce alcun diritto secondo quella legge. Le due condizioni sono congiunte; esattamente un anno non soddisfa il primo test.
2. Se entrambe sono vere, la sola istituzione interessata non è obbligata a concedere una prestazione per quei periodi; l'esenzione non elimina i periodi dal coordinamento. Il Reg. 883/2004 art. 57(2) impone alle altre istituzioni interessate di considerarli per il solo calcolo previsto dall'art. 52(1)(b)(i), che resta fuori dal presente contratto di eligibility e non viene calcolato.
3. Valutare il fallback art. 57(3): se applicare l'esenzione lascerebbe **tutte** le istituzioni interessate libere da obblighi, il diritto è valutato soltanto secondo la legge dell'ultimo Stato le cui condizioni sono soddisfatte, come se tutti i periodi totalizzati secondo art. 6 e art. 51(1)-(2) fossero compiuti sotto tale legge. Il record deve provare l'insieme completo degli Stati interessati, le condizioni soddisfatte e l'ordine temporale. Predicato o comunicazione istituzionale mancante => `not_assessed` + `data_gaps`; non assumere né l'esenzione universale né lo Stato di fallback.

L'art. 51(3) non introduce un requisito generale di Allegato XI. Il predicato conserva: precedente soggezione/assicurazione nel regime nazionale in cui si valuta il requisito; alla data del rischio, assicurazione contro **lo stesso rischio** in un altro Stato membro, oppure, in assenza, prestazione dovuta per lo stesso rischio sotto la legge di un altro Stato. La condizione è considerata soddisfatta nei casi previsti dall'art. 57; questa deroga è una regola diretta art. 51(3)→57. Ogni ramo ha valore `true/false/unknown` e fonte. I rami art. 57 che dipendono da calcoli dell'importo art. 52(1)(b)(i) sono tracciati come dipendenza esterna non computata: se non si può determinare l'effetto sulla sola acquisizione del diritto senza calcolare importi, `not_assessed`, non una supposizione.

#### LGSS 205.1(b): unità source-bound

La norma primaria enuncia 15 anni complessivi e almeno 2 anni entro i 15 immediatamente precedenti il hecho causante, o entro la finestra ancorata alla cessazione dell'obbligo nei casi previsti; esclude la quota proporzionale delle paghe straordinarie. Le unità sono distinte dalla regola degli anni/mesi completi pertinente alla fascia d'età 205.1(a)/DT 7.

Per il contratto operativo, i periodi di carenza 205.1(b) sono rappresentati in **giorni effettivi accreditati**, senza trasformare frazioni in mesi/anni: `general_carence_15y` ha soglia operativa 5.475 giorni; `specific_carence_2_of_15` ha soglia operativa 730 giorni entro la finestra temporale applicabile. Si contano soltanto contributi effettivi o assimilati riconosciuti dalla legge, si escludono i giorni figurativi delle paghe extra e si applicano prima le regole legalmente rilevanti per part-time/fissi discontinui, periodi UE e sovrapposizioni. I giorni sono attribuiti alle date coperte dalla certificazione, non convertiti da un totale mensile/annuale privo di distribuzione.

Provenienza distinta: art. 205.1(b) e atti autentici BOE sono la base normativa; la pagina informativa ufficiale Seguridad Social espone la traduzione amministrativa in 5.475 giorni e il requisito specifico di due anni, mentre la conversione operativa di 730 giorni va citata come criterio amministrativo/giurisprudenziale e non come testo letterale dell'articolo. Se fonte, regime transitorio, modalità di contribuzione o classificazione dei giorni non consente di applicare univocamente le soglie, il ramo è `not_assessed` + gap. Nessuna inferenza per analogia dalla regola 205.1(a); ogni scostamento fra periodo civile e conteggio in giorni resta legato a fonte e versione. Non si valutano periodi privilegiati o eccezioni non modellati.

#### Dominio temporale e completezza

Campi ISO obbligatori: `search_lower_bound`, `search_upper_bound` (estremi inclusi e finiti), `as_of_date`, `evaluation_date` (generata dal sistema e non anteriore ad `as_of_date`), `evaluation_mode` (`actual` / `hypothetical`), `evidence_complete_through`, copertura per ciascuna famiglia di prove e `rule_pack_valid_from`/`rule_pack_valid_through`. Vincoli:

- `search_lower_bound <= search_upper_bound`; `as_of_date` non può essere successivo alla data di valutazione (`evaluation_date`). `evidence_complete_through <= as_of_date` e ogni record probatorio ha una data/versione verificabile.
- `evidence_complete_through` e le coperture di ogni famiglia devono arrivare almeno a `min(search_upper_bound, as_of_date)` e coprire senza lacune l'intersezione ricercata fino a tale cutoff; per ipotesi future, ogni scenario deve coprire dall'inizio del tratto post-cutoff fino a `search_upper_bound`.
- `actual`: `search_upper_bound <= as_of_date`; l'evidenza di ogni famiglia rilevante copre senza lacune l'intero intervallo richiesto e le regole applicabili coprono ogni data candidata. Solo una scansione completa così definita può restituire `no_candidate_in_complete_range`.
- `hypothetical`: l'intervallo può superare `as_of_date`, ma i fatti osservati sono limitati a tale data. Date successive richiedono assunzioni/scenari espliciti, deterministicamente versionati, con copertura fino a `search_upper_bound`; altrimenti condizioni future sono `unknown` e l'esito resta `not_assessed`. L'esito senza candidato è `no_candidate_in_complete_scenario`, mai il risultato storico `no_candidate_in_complete_range`.
- Il rule pack deve coprire l'intero intervallo con una validità dichiarata. Per date successive alla validità nota si può fornire solo uno scenario che dichiari esplicitamente la continuità ipotizzata della regola; nessuna norma futura è trattata come fatto.

La semantica multi-path resta: positivo se almeno un path compatibile è tutto `true`; scartabile solo se ciascun path ha almeno un `false` decisivo; `not_assessed` se nessun path è positivo e almeno uno può ancora esserlo. `unknown` su un path alternativo non blocca un path già provato. Ogni risposta mantiene lineage, lacune e `human_review_required: true`.

#### Test contrattuali richiesti

Art. 57: periodo inferiore/esattamente pari/superiore a un anno; con/senza diritto autonomo su quel periodo; singola e multipla istituzione esente; art. 57(2) indicato ma importo non calcolato; fallback art. 57(3) con tutti/alcuni Stati esenti, ultimo Stato le cui condizioni risultano soddisfatte e input istituzionale mancante; art. 51(3) stesso rischio, prestazione dovuta e rinvio art. 57 senza requisito Allegato XI inventato. LGSS: 5.474/5.475 e 729/730 giorni; 15y e 2/15 separati; paghe extra escluse; finestra 15 anni e anchor cessazione obbligo; date di accredito, sovrapposizioni, part-time/fisso discontinuo ed evidenza priva di granularità. Tempo: lower>upper, estremi inclusivi, cutoff dopo evaluation date, `actual` con upper>as_of rifiutato, `hypothetical` con/senza scenario completo, validità pack che non copre range, evidence coverage non continua, stato no-candidate storico vs scenario. Conservare la truth table multi-path, invalid-vs-gap e revisione umana della v4.

#### Fonti e autorizzazione del gate

Verifica fonti: 2026-10-16. [LGSS consolidata BOE aggiornata al 03/10/2026](https://www.boe.es/buscar/act.php?id=BOE-A-2015-11724&p=20261003&tn=0), art. 205.1(b), artt. 247 e disposizioni temporali pertinenti; [testo autentico di pubblicazione LGSS](https://boe.es/eli/es/rdlg/2015/10/30/8/dof/spa/pdf). Per l'applicazione operativa, [informazione ufficiale Seguridad Social sui periodi minimi](https://www.seg-social.es/wps/portal/wss/internet/Trabajadores/PrestacionesPensionesTrabajadores/10963/28393/28396/28472?changeLanguage=gl) (fonte amministrativa, non norma primaria); la verifica del criterio specifico 730 giorni deve considerare anche giurisprudenza pertinente, incluso TS, ECLI `ES:TS:2026:3239` (01/07/2026), senza estenderne la ratio oltre il caso deciso. [Reg. 883/2004, testo autentico DOUE](https://www.boe.es/doue/2004/166/L00001-00123.pdf), artt. 6, 51, 52, 57; [Reg. 988/2009, atto modificativo autentico](https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX%3A32009R0988), che sostituisce l'art. 51(3) con il rinvio all'art. 57; [consolidato EUR-Lex al 31/07/2019](https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX%3A02004R0883-20190731), da non confondere con gli atti autentici.

L'utente ha autorizzato il 2026-10-16 un solo nuovo gate normativo read-only sulla sola v5 esatta, bounded a 5 minuti. Nessun retry o gate sulla versione successiva senza nuova autorizzazione. Fuori scope Knowledge/Rules/Tests/Engine, rule pack, importi/pro-rata, riconoscimento, calcolo individuale e dati personali.

### Verifica V4.14t

Richiesti: review indipendente exact-version; suite Engine completa con 0 failure, 0 errori, 0 skipped; roadmap audit, schema planner, execution guardrails e diff check. NO-GO chiude l'audit documentale solo dopo verifiche riproducibili, senza approvare runtime; timeout o verifiche incomplete mantengono `in_progress`/`blocked`.

#### Esito review normativa indipendente — 2026-10-16

**GO limitato** esclusivamente per l'artefatto esatto `spanish-first-eligibility-contract/v5`. Il reviewer conferma la corretta recezione di Reg. 883/2004 artt. 51(3)/57 come modificato da Reg. 988/2009; la separazione fra testo LGSS 205.1(b) e unità operative 5.475/730 giorni, con 730 limitato a criterio operativo amministrativo/giurisprudenziale, non a conversione letterale della legge; e i vincoli temporali/evidence `actual`/`hypothetical`.

Limiti da preservare: (a) Reg. 883/2004 art. 57(4) esclude l'intero articolo per gli schemi elencati in Allegato VIII, parte 2; lo schema concreto va verificato e, se non determinabile, il risultato è `not_assessed`; (b) la modifica dell'art. 51(3) per Reg. 988/2009 opera dal 2010-05-01 ai sensi del suo art. 2 e Reg. 987/2009 art. 97; periodi precedenti richiedono versione normativa anteriore o `not_assessed`; (c) il criterio 730 giorni va applicato senza generalizzare oltre la ratio della STS 607/2026, ECLI `ES:TS:2026:3239`. Riferimenti: [Reg. 988/2009, atto EUR-Lex](https://eur-lex.europa.eu/legal-content/ES/TXT/HTML/?uri=CELEX:32009R0988), [Reg. 987/2009, art. 97](https://eur-lex.europa.eu/legal-content/es/TXT/?uri=CELEX:32009R0987), [STS 607/2026](https://www.poderjudicial.es/search/AN/openDocument/43237b3c96aebc4ea0a8778d75e36f0d/20260724). Il GO non approva Knowledge/Rules/Tests/Engine, rule pack, importi/pro-rata, riconoscimento o conclusioni individuali.

Verifiche: suite Engine `Ran 762 tests ... OK` (0 failure, 0 errori, 0 skipped); schema planner, roadmap audit, execution guardrails e diff check passano. V4.14t si chiude solo come audit documentale. V4.14u è il candidato successivo per formalizzare e testare questi due limiti (art. 57(4)/Allegato VIII e validità pre-01/05/2010); ogni nuovo gate normativo richiede autorizzazione utente separata.

### Prossimo incremento candidato — V4.14u

Precisare nel contratto e nei futuri test la non-applicabilità di art. 57 per gli schemi dell'Allegato VIII, parte 2, e il confine temporale 01/05/2010 della modifica dell'art. 51(3), incluse fonti storiche e fallback fail-closed. Nessun gate normativo successivo è autorizzato dal ciclo V4.14t.

---

## Incremento corrente — V4.14s — Spanish date-level contract v4 after normative NO-GO

**Stato:** `done` — audit documentale concluso con NO-GO limitato alla v4; nessuna approvazione runtime
**Tipo:** `audit`
**Versione candidata esatta:** `spanish-first-eligibility-contract/v4`

### Specifica v4 proposta

Il perimetro resta la ricerca giornaliera del primo hecho causante potenzialmente qualificante per la pensione contributiva ordinaria nel solo Régimen General. Il risultato è informativo, non un riconoscimento, una decorrenza economica o un importo. Il contratto è immutabile, versionato e source-bound.

#### Intento, path e domanda internazionale

`applicant_intent` è un input canonico scelto/confermato dalla persona, con provenienza, data e riferimento probatorio: indica se la persona propone una data per il caso generale dell'art. 3.1 o dichiara l'intento pertinente ai casi art. 3.2/3.3. È distinto da `article_3_path`, che resta derivato deterministamente da intento, fatti ed evidenze e non può essere scelto per far tornare una data. Intento mancante con schema valido produce `not_assessed` + `data_gaps`; intento contraddittorio con fatti o path produce `invalid_contract`.

Per una domanda presentata fuori dalla Spagna, `international_application_basis` deve identificare strumento, articolo/versione, intervallo di efficacia, Stato/autorità, termine applicabile e prove. La valutazione verifica esplicitamente ambito personale, materiale e temporale dello strumento per la persona e la domanda. Riferimento o predicati mancanti => `not_assessed` + gap; contraddizione o strumento fuori validità/inapplicabile dimostrato => `invalid_contract`/path non ammissibile, mai termine inventato. Per il percorso 3.1 restano distinti data di domanda e data candidata; per 3.2 vale la finestra propria del percorso.

#### Regole contributive con unità non intercambiabili

La regola degli anni/mesi completi si applica soltanto al periodo contributivo della fascia d'età previsto da LGSS art. 205.1(a) e DT 7. Le carenze di art. 205.1(b) — 15 anni complessivi e 2 anni nel periodo di riferimento — hanno verifiche autonome, rispettano la loro unità legale e non ereditano per analogia il troncamento anni/mesi della fascia d'età. L'implementazione futura deve modellare separatamente `age_band_contribution_period`, `general_carence_15y` e `specific_carence_2_of_15`; periodi parziali sono valutati secondo fonte e unità applicabile, non convertiti o arrotondati implicitamente. Resta distinto l'ancoraggio alla data del hecho causante o, quando previsto, alla cessazione dell'obbligo.

#### Coordinamento UE: diritto e computo

- Reg. 883/2004 art. 6 è la base per totalizzare periodi nella misura necessaria a stabilire il diritto; il diritto nazionale autonomo è valutato separatamente ai sensi dell'art. 52(1)(a).
- Art. 52(1)(b)-(5) riguarda il calcolo degli importi (teorico/pro-rata e confronto), qui fuori scope. Art. 50 riguarda liquidazione, differimento e riesame al maturare di diritti; non è la fonte normativa della totalizzazione.
- Art. 51(3) è applicabile solo se sono provati tutti i predicati: precedente assicurazione nel regime nazionale pertinente; al materializzarsi del rischio, assicurazione contro lo stesso rischio in un altro Stato membro oppure diritto a una prestazione per lo stesso rischio secondo la legislazione di tale Stato; applicazione dell'eventuale clausola dell'Allegato XI riferita all'art. 57. Il fascicolo conserva quale ramo e quali fonti provano ogni predicato. Un nome generico di status o di periodo non basta; predicato decisivo mancante => `not_assessed` + gap. Nessun importo o pro-rata è prodotto.

#### Dominio finito e verità fra path

Ogni richiesta include `search_lower_bound`, `search_upper_bound` e `as_of_date`; i limiti sono date valide, coerenti con `as_of_date` e definiscono un intervallo finito con estremi inclusi. L'assenza di `search_upper_bound` è input incompleto (`not_assessed` + gap), non ricerca illimitata. `no_candidate_in_complete_range` è ammesso solo quando l'intero intervallo è valutato e la copertura probatoria/normativa è completa.

Per ogni giorno si considerano tutti e soli i path compatibili, ciascuno con condizioni `true/false/unknown`. Il giorno è positivo (`potentially_eligible`) se almeno un path è interamente `true`, anche se un altro path contiene `unknown`. È scartabile solo se ogni path compatibile contiene almeno un `false` decisivo. Se nessun path è tutto `true` e almeno uno può ancora diventarlo, l'esito è `not_assessed` con gap; se tutti sono definitivamente falsi, si continua la scansione. Se il range finito è esaurito senza candidato e con valutazione completa, restituire `no_candidate_in_complete_range`; altrimenti non dichiarare completezza. Tutti gli esiti mantengono lineage e `human_review_required: true`.

#### Test contrattuali richiesti

Golden test per intento presente/mancante/contraddittorio e path derivato; base internazionale completa e valida, riferimento mancante, scaduto o fuori ambito personale/materiale; 205.1(a)/DT 7 con unità complete separato da 205.1(b) 15y e 2/15 con periodi frazionari secondo unità legale; ognuno dei predicati art. 51(3), rami alternativi stesso rischio/prestazione dovuta e clausola art. 57; errori di intervallo, upper bound mancante, as-of coerente e range completo senza candidato; truth table multi-path con (true+unknown), soli falsi decisivi, unknown potenzialmente vero, e range incompleto. Conservare i test già previsti per RD 453/2022, transitorio, DT 7, artt. 12-13 Reg. 987/2009, invalid-vs-gap e human review.

**Autorizzazione e limiti:** l'utente ha autorizzato il 2026-10-16 un solo ciclo e la review normativa read-only della v4 esatta, entro 5 minuti totali. Nessun retry/review ulteriore, modifica a Knowledge/Rules/Tests/Engine, calcolo individuale, accesso o copia di dati personali, implementazione runtime o GO d'uso sono autorizzati. Fonti primarie e consolidate BOE/EUR-Lex sono quelle elencate nella sezione storica V4.14r e restano vincolate alla validità temporale applicabile.

### Verifica e gate V4.14s

La review esatta v4, suite Engine completa, roadmap audit, validazione schema planner, execution guardrails e diff check sono richiesti. Un NO-GO chiude solo l'audit documentale se tutte le verifiche riproducibili passano; non approva la specifica per uso runtime. Timeout o verifiche incomplete mantengono lo stato non-`done`.

#### Esito review normativa indipendente — 2026-10-16

**NO-GO limitato** per l'esatta `spanish-first-eligibility-contract/v4`; nessuna review ulteriore è autorizzata dal ciclo corrente.

1. **Reg. 883/2004 artt. 51(3) e 57:** l'art. 51(3) rinvia direttamente all'art. 57 per la seconda alternativa, non a un'eventuale clausola dell'Allegato XI. Mancano condizioni e conseguenze deterministiche dell'art. 57(1)-(3): periodo inferiore a un anno, assenza di diritto autonomo su quel periodo, computo da parte delle altre istituzioni e fallback quando tutte sarebbero esonerate.
2. **LGSS art. 205.1(b):** la distinzione fra 205.1(a)/DT 7 e carenze 15y/2-of-15 è recepita, ma «unità legale» non definisce il trattamento source-bound dei periodi frazionari per queste ultime due carenze; i casi di confine restano ambigui.
3. **Dominio temporale:** i campi lower/upper/as-of e la truth table sono presenti, ma «coerenti con `as_of_date`» non stabilisce una relazione formale verificabile né il limite temporale dell'evidenza.

Il finding v3 su `applicant_intent` e base internazionale risulta recepito a livello documentale. Fonti reviewer: [Reg. 883/2004 consolidato EUR-Lex, artt. 51(3), 57](https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX%3A02004R0883-20190731), [LGSS consolidata BOE, art. 205.1 e DT 7](https://www.boe.es/buscar/act.php?id=BOE-A-2015-11724&p=20261003&tn=0), [RD 453/2022, art. 3](https://www.boe.es/eli/es/rd/2022/06/14/453/dof/spa/pdf). Il NO-GO non approva runtime, Knowledge/Rules/Tests/Engine, rule pack o calcoli.

Verifica conclusiva: suite Engine completa `Ran 762 tests ... OK` (0 failure, 0 errori, 0 skipped); roadmap audit, schema planner, execution guardrails e diff check passano. V4.14s si chiude come audit documentale NO-GO, non come GO normativo o runtime. Il prossimo candidato documentale è V4.14t, limitato ai tre finding sopra; ogni nuova review normativa richiede autorizzazione utente separata.

### Prossimo incremento candidato — V4.14t

Correggere esclusivamente i tre finding residui della review v4: recepire direttamente il rinvio dell'art. 51(3) al Reg. 883/2004 art. 57 e formalizzare condizioni/fallback dei paragrafi 1-3; rendere source-bound e non ambiguo il trattamento dei periodi frazionari per LGSS 205.1(b), sia 15 anni sia 2/15; definire vincoli formali fra `search_lower_bound`, `search_upper_bound`, `as_of_date` e cutoff probatorio. Nessuna nuova review è autorizzata dal ciclo V4.14s.

---

## Incremento completato precedente — V4.14r — Spanish date-level contract v3 after normative NO-GO

**Stato:** `done` — NO-GO normativo limitato alla specifica documentale v3; nessun GO runtime
**Tipo:** `audit`
**Versione candidata esatta:** `spanish-first-eligibility-contract/v3`

### Specifica v3 proposta

Scopo strettamente documentale: specificare un contratto deterministico e source-bound per cercare giorno per giorno il primo fatto causante potenzialmente qualificante per la pensione contributiva ordinaria nel solo Régimen General. Il giorno è l'unità di valutazione, con eventuale mese solo come proiezione; si rispetta tuttavia la data legale dell'art. 3.2(a), ultimo giorno del mese nel caso rinviato dall'art. 46.4.c RD 84/1996. Non è un diritto riconosciuto, una decorrenza economica né una data di pagamento.

#### Record minimo e risultati

Il record immutabile `spanish-first-eligibility-contract/v3` contiene: `contract_schema_version`; `rule_pack_id` e `rule_pack_version`; intervallo di efficacia e fonti/autenticità; `application_mode` (`actual` / `hypothetical`); data reale di domanda o data di domanda ipotizzata; paese/autorità di presentazione e fonte del termine se fuori Spagna; percorso dell'art. 3; data proposta dall'interessato o evento/ancora che la determina; `hecho_causante_date` derivato; status, obbligo di cotizzare e cessazione di tale obbligo alla data pertinente; periodi nazionali/UE con intervallo e unità nativa, regime/legislazione, natura obbligatoria/volontaria, comunicazione istituzionale e riferimenti probatori; copertura storica della documentazione.

Enum canonico `article_3_path`: `3.1_general_choice`, `3.2.a_registered_cessation`, `3.2.b_transfer_abroad`, `3.2.c_forced_leave_public_office`, `3.2.d_special_convention_termination`, `3.2.e_unemployment_extinction_at_ordinary_age`, `3.3_continued_work_art214`. Il path è derivato da fatti/evidenze e volontà della persona, mai scelto liberamente per far tornare il giorno. Conflitti tra evento, status, path e date rendono il record `invalid_contract`; fatti o prove decisive mancanti con struttura valida danno `not_assessed` + `data_gaps`.

#### Derivazione fatto causante/domanda e transitorio

- **Art. 3.1:** la data indicata dalla persona nella domanda è il fatto causante solo se in quella data sono provati i requisiti; domanda nazionale e data indicata devono rispettare la finestra da tre mesi prima a tre mesi dopo, compresa la coincidenza. Domanda presentata all'estero in base a norma internazionale usa il termine della legislazione del paese di presentazione, che deve essere source-bound; se manca, `not_assessed`.
- **Art. 3.2(a):** da alta con cessazione dell'attività/condizione d'inclusione: fatto causante al giorno della baja conseguente alla cessazione; eccezioni religiosi iscritti al RETA e sistema agrario in inattività al giorno della baja; per il caso art. 46.4.c RD 84/1996 il giorno legale è l'ultimo del mese naturale del cessazione. La sola cessazione dell'obbligo di cotizzare non equivale a cessazione dell'alta.
- **Art. 3.2(b):** assimilada per trasferimento fuori Spagna al servizio di impresa spagnola; fatto causante alla cessazione del lavoro.
- **Art. 3.2(c):** assimilada per excedencia forzosa per carica pubblica incompatibile con il lavoro; fatto causante alla cessazione della carica/funzioni.
- **Art. 3.2(d):** perdita della condizione ed estinzione dei soli convenios speciali elencati; fatto causante alla loro estinzione.
- **Art. 3.2(e):** estinzione di prestazione/sussidio di disoccupazione, incluso quello per maggiori di 52 anni, per raggiungimento dell'età ordinaria applicabile; fatto causante al giorno di compimento dell'età.
- **Art. 3.2 comune:** domanda non prima dei tre mesi precedenti il fatto causante o in qualsiasi momento successivo; questo non determina gli effetti economici ex art. 4, che restano fuori scope.
- **Art. 3.3:** lavoro subordinato/autonomo mantenuto senza interruzione dopo il riconoscimento ai sensi di LGSS art. 214; la domanda va presentata nei tre mesi immediatamente precedenti la data indicata. Poiché il pack non approva il ramo di pensione compatibile col lavoro, il record lo classifica `not_assessed`/`scope_gap`, mai come percorso falso o data utile.

Applicabilità: il pack del RD 453/2022 copre domande dal 2022-06-16 (disposizione finale decima). Per domande da tale data, il fatto causante non può precedere il 2022-06-16, salvo i percorsi dell'art. 3.2 per espressa deroga della disposizione transitoria unica. La decisione usa insieme modalità/data di domanda, percorso, fatto causante e versione del pack; applicare `valid_from` alla sola data candidata non basta. Domanda ipotetica restituisce soltanto scenario potenziale, mai data acquisita; domanda reale non è inferita da una data prevista.

#### Requisiti nazionali LGSS

La tabella regola-per-condizione lega fonte autentica, testo applicabile, validità, input/prova, unità e output ternario: LGSS art. 165.1 (alta/assimilada salvo eccezione espressa), art. 205.1(a) + DT 7 (età ordinaria e periodo richiesto), art. 205.1(b) (15 anni e almeno 2 negli ultimi 15 prima del fatto causante) e art. 205.1, secondo comma (se alta/assimilada senza obbligo, i 2 anni entro 15 prima della cessazione dell'obbligo). Il computo dell'età/anzianità usa anni e mesi completi: le frazioni non si equiparano a unità complete. LGSS art. 205.3 consente l'accesso da non alta se requisiti di età e contribuzione sono soddisfatti; se si valuta diritto in Régimen General e in altri regimi spagnoli, richiede inoltre sovrapposizione di almeno 15 anni delle contribuzioni accreditate in ciascuno. Senza il perimetro probatorio inter-regimi, quel ramo è `not_assessed`, non assunto soddisfatto. Status generale, obbligo alla data e data di cessazione restano attributi distinti.

Per la soglia anagrafica, la matrice temporale rinvia alla DT 7 vigente per il giorno e non hard-coda una soglia uniforme: regressioni di contratto includono i valori 2026 (66 anni e 10 mesi, oppure 65 con 38 anni e 3 mesi) e dal 2027 (67, oppure 65 con 38 anni e 6 mesi), e verifica che anni/mesi incompleti non soddisfino la soglia. Anni futuri non coperti dalla fonte/pack sono `not_assessed`.

#### Overlay UE per acquisizione del diritto (non importi)

Input solo da periodi comunicati/riconosciuti dalla legislazione competente: tipo ex art. 1(t) Reg. 883/2004, Stato e schema, intervallo preciso o granularità originale, unità, natura obbligatoria/volontaria/assimilata, regime e attività, prova, eventuale overlap e regime basato su 5/6/7 giorni. Prima si valuta il diritto autonomo nazionale; solo nella misura necessaria si valuta la totalizzazione ex artt. 6 e 50, mantenendo separati i rami nazionale e aggregato. Art. 51(1)-(2): requisiti di attività/occupazione in regime speciale si soddisfano con regime equivalente o, in mancanza, stessa occupazione/attività; se non basta per il regime speciale, verifica l'eventuale computo nel generale solo nei casi previsti e se la persona vi è stata iscritta; periodi di un regime speciale possono contare nel regime generale di altro Stato alle condizioni del par. 2. Art. 51(3): requisito nazionale di assicurazione al materializzarsi del rischio va valutato con la regola UE e l'Allegato XI applicabile, non inferito da un generico status UE. Non si desume la qualità assicurativa dal solo nome del periodo e non si calcola l'importo/pro-rata ex art. 52.

Risoluzione: Reg. 987/2009 art. 12(1)-(2) governa richiesta/conferma istituzionale e somma nella misura necessaria solo di periodi non sovrapposti; art. 12(3) dà precedenza al compulsory su voluntary/continued optional coincidente; art. 12(4) al periodo non assimilato su quello assimilato coincidente; art. 12(5) assegna periodi assimilati coincidenti fra Stati secondo l'ultima soggezione obbligatoria prima del periodo, o la prima successiva se non ve n'è una precedente; art. 12(6), se il tempo esatto non è determinabile, presume assenza di overlap e consente il computo quando favorevole e ragionevolmente praticabile, con evidenza separata della presunzione. Ogni altra sovrapposizione decisiva non classificata resta gap. Conversione solo quando necessaria e a partire dall'unità comunicata dall'istituzione ex art. 13(1)(a): applicare la tabella legale 5/6/7 giorni, conversioni per unità/frazioni e arrotondamento dell'art. 13(1)(b)-(e); imporre i massimi annuali dell'art. 13(2), la modalità unica vs anno per anno secondo comunicazione (13(3)) e la dichiarazione 5/6/7 (13(4)). Conservare input nativo, passaggi e output convertito; input non comunicato/ambiguo che cambia la conclusione => gap. Il controllo d'acquisizione non restituisce importo teorico/effettivo né pro-rata.

#### Ricerca, materialità e output

`search_lower_bound` è valido solo se una prova di completezza della storia (contributi nazionali, periodi UE potenzialmente rilevanti e copertura delle versioni normative) copre tutto l'intervallo precedente; altrimenti è `null` e nessun output può chiamarsi “primo”. Per ogni giorno e per ciascun percorso d'art. 3 compatibile, la condizione produce `true`, `false` o `unknown`. Contratto malformato/schema o enum incompatibile => `invalid_contract`; in record strutturalmente valido, prova/fonte assente => `unknown` + gap. Un giorno è scartabile solo se un falso verificato esclude tutti i percorsi pertinenti; un candidato anteriore con un ramo materialmente ignoto interrompe la scansione con `not_assessed`, `candidate_date=null`, `data_gaps`, e nessun giorno successivo è promosso. Primo giorno per cui tutti i requisiti di almeno un path in-scope sono provati => `potentially_eligible`, con path e lineage; non è accertamento legale né riconoscimento. Ogni risposta porta `human_review_required: true` non disattivabile e dichiara che è un supporto informativo non conclusivo.

#### Test contrattuali richiesti

Golden positivi/negativi per art. 3.1, 3.2(a-e), conflitti e art. 3.3 fuori scope; finestre di domanda distinte per 3.1, 3.2, 3.3 e domanda internazionale con termine provato/mancante; confine 15/16 giugno 2022 e deroga solo 3.2; status alta con obbligo, alta/assimilada senza obbligo, no-alta e anchor appropriato; art. 205.3 multi-regime con/senza 15 anni sovrapposti; fasce DT 7 2026/2027 e frazioni; diritto nazionale autonomo vs totalizzato, art. 51(1)-(3) equivalente/non equivalente, affiliation and Annex XI; art. 12(3)-(6) mandatory/voluntary, assimilated/non-assimilated, assignment priority and presumption; conversione 5/6/7, frazioni, arrotondamento, cap annuo, conversione totale vs annuale; lower bound completo/incompleto; falso anteriore decisivo, ignoto anteriore decisivo e ignoto non materiale; schema invalido distinto da prova mancante; `human_review_required` obbligatorio.

#### Fonti e limiti

Verifica fonti: 2026-10-16. [RD 453/2022, testo BOE](https://www.boe.es/eli/es/rd/2022/06/14/453/dof/spa/pdf) artt. 2-4, DT unica e DF decima; il consolidato BOE dichiara “sin modificaciones”. [LGSS, testo autentico di pubblicazione](https://boe.es/eli/es/rdlg/2015/10/30/8/dof/spa/pdf) e [consolidato informativo BOE aggiornato 2026-10-03](https://www.boe.es/buscar/act.php?id=BOE-A-2015-11724&p=20261003&tn=0), artt. 165/205 e DT 7; ogni campo normativo deve puntare alla versione temporale pertinente, il consolidato non sostituisce la pubblicazione autentica. [Reg. 883/2004, atto EUR-Lex](https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX%3A32004R0883) e [consolidato documentale 2019-07-31](https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX%3A02004R0883-20190731); [Reg. 987/2009, atto EUR-Lex](https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX%3A32009R0987) e [consolidato documentale 2018-01-01](https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX%3A02009R0987-20180101). Gli atti in GU/DOUE prevalgono sul consolidato. Nessuna guidance amministrativa sovrascrive la legge.

**Perimetro V4.14r:** solo specifica documentale v3 e review esatta. Fuori scope Knowledge/Rules/Tests/Engine, calcoli individuali, dati personali, AML/CRS/DAC non attivati da questo task, riconoscimento, effetti economici, pagamento, pro-rata/importi e timeline complessiva. Il gate è autorizzato dall'utente il 2026-10-16 per un solo tentativo bounded massimo 5 minuti; il risultato resta vincolato alla v3 e non autorizza runtime.

### Esito review normativa indipendente — 2026-10-16

**NO-GO** per l'esatta `spanish-first-eligibility-contract/v3`, conclusa read-only nel timebox. La struttura normativa è in gran parte corretta; restano quattro gap deterministici:

1. **Volontà e domanda internazionale:** introdurre `applicant_intent` canonico/provato, distinto dal path derivato; per la domanda estera richiedere il riferimento alla norma internazionale e la verifica della sua applicabilità personale, materiale e temporale. Intento/strumento mancante in struttura valida => `unknown/not_assessed + data_gaps`; contraddizione => `invalid_contract`.
2. **Unità contributive:** restringere la regola “anni e mesi completi” all'uso espressamente previsto dall'art. 205.1(a)/DT 7 per la soglia contributiva della fascia di età. La carenza 15 anni e 2/15 dell'art. 205.1(b) ha verifica e unità normative proprie, non ereditate per analogia.
3. **Coordinamento UE:** attribuire la totalizzazione dei periodi all'art. 6; distinguere art. 52(1)(a) (diritto nazionale autonomo) da art. 52(1)(b)-(5) (calcolo importi, fuori scope); trattare art. 50 come liquidazione/differimento/ricalcolo, non come fonte della totalizzazione. Rendere computabile l'intero test art. 51(3): precedente assicurazione nel regime nazionale e copertura dello stesso rischio nell'altro Stato alla data del rischio oppure prestazione dovuta per lo stesso rischio, inclusa la clausola art. 57.
4. **Dominio di ricerca:** definire `search_upper_bound`/`as_of_date`, intervallo finito obbligatorio e risultato distinto `no_candidate_in_complete_range`; usare la truth table per path compatibili: positivo se almeno un path è interamente true; scartabile se ogni path ha almeno un false decisivo; `not_assessed` se non esiste un path provato e almeno un path potrebbe ancora risultare true. Un unknown su un altro path non blocca quando un path è già provato.

Fonti e limiti verificati sono quelli elencati nella v3: atti autentici BOE/DOUE distinti dai consolidati informativi. La review conferma i rami RD 453/2022 3.1, 3.2(a-e), 3.3 e il transitorio; LGSS 165/205/DT 7, i calcoli 15/2 e art. 205.3; Reg. 987/2009 artt. 12(1)-(6) e 13(1)-(4), inclusa la presunzione 12(6). Il NO-GO non approva alcun rule pack, Knowledge/Rules/Tests/Engine, calcolo, data personale, riconoscimento, effetto economico, pagamento, pro-rata o timeline IT/ES/UE.

V4.14r si chiude solo come audit documentale NO-GO. Il prossimo candidato V4.14s dovrà produrre la v4 correggendo esattamente questi quattro gap e ottenere una nuova autorizzazione per la review; il gate v3 non si trasferisce.

### Prossimo incremento candidato — V4.14s

Preparare `spanish-first-eligibility-contract/v4` con: prova canonica della volontà e base internazionale della domanda estera; regole di complete-year/month circoscritte al requisito di età e carenze 15/2 versionate separatamente; separazione corretta fra aggregazione art. 6, prestazione autonoma art. 52(1)(a), art. 50 e calcolo art. 52(1)(b)-(5), con predicati art. 51(3); intervallo finito e truth table ternaria per ogni percorso. Una nuova review normativa richiede esplicita autorizzazione utente; nessun GO o budget di V4.14r si trasferisce.

---

## Incremento completato precedente — V4.14q — Spanish date-level eligibility contract remediation and review

**Stato:** `done` — NO-GO normativo limitato alla specifica documentale v2; nessun GO runtime
**Tipo:** `audit`
**Versione sottoposta al gate:** `spanish-first-eligibility-contract/v2`

### Contratto v2 proposto

La capability futura cerca il primo **giorno** supportato di possibile acquisizione del diritto alla pensione contributiva ordinaria spagnola nel solo Regimen General. Il mese è una proiezione descrittiva del giorno, non l'unità di valutazione. Non si valuta convenzionalmente l'ultimo giorno del mese. Il risultato è un candidato potenziale e non un diritto riconosciuto, una decorrenza economica o una data di pagamento.

Ogni valutazione giornaliera riceve separatamente: `candidate_date`; `hecho_causante_date`; `application_date_or_hypothesis`; `article_3_path` (caso concreto RD 453/2022 art. 3, incluso il relativo par. 2 quando applicabile); status al fatto causante; esistenza dell'obbligo contributivo in quella data; `contribution_obligation_cessation_date`; periodi contributivi con unità, intervalli, regime, fonte e provenienza. Data e ipotesi di domanda possono identificare un percorso potenziale, ma non provano domanda presentata, fatto acquisito o riconoscimento.

La verifica normativa separa requisiti anagrafici e contributivi LGSS, status, carenza generale e carenza specifica. Lo status sintetico `alta/assimilada/no_alta` non sostituisce il percorso normativo né gli input distinti sull'obbligo e sulla sua cessazione. I periodi devono essere localizzati temporalmente: unità o conversioni non provate, sovrapposizioni non risolte e date assenti sono gap, salvo una presunzione normativa esplicitamente applicabile e documentata.

Il rule pack corrente può supportare solo date da `valid_from=2022-06-16`, efficacia RD 453/2022; date precedenti richiedono un pack storico esplicito e non possono ereditare le regole correnti. Il contratto UE copre l'acquisizione del diritto secondo Reg. 883/2004 artt. 1(t), 6, 50-52 e 51 e Reg. 987/2009 artt. 12-13: distinguere diritto autonomo nazionale da totalizzazione potenziale e periodi computabili, senza calcolare pro-rata o importi. Prevale l'atto primario BOE/EUR-Lex applicabile; la guidance Seguridad Social è solo interpretativa e subordinata.

La ricerca richiede `search_lower_bound` source-bound e motivato. Per ciascun giorno in ordine cronologico si valuta se esiste almeno un percorso potenzialmente qualificante. Se un giorno precedente è potenzialmente qualificante ma non valutabile per storia incompleta, regola fuori copertura, status/obbligo ignoti o periodi decisivi non risolti, il risultato è `null` con `data_gaps`: non si salta al giorno seguente. Il lower bound non dimostrato completo non autorizza a presentare un giorno successivo come primo.

**Test contrattuali richiesti prima di un eventuale slice eseguibile:** soglie anagrafiche 2026/2027 e confini di anno; giorno di compleanno e fatto causante nello stesso mese; febbraio/leap day e fine mese; domanda nei limiti temporali dell'art. 3 e ciascun caso pertinente del par. 2; alta con/senza obbligo, assimilada e non alta con anchor di cessazione; soglie 15 anni e 2/15 su finestre ancorate alla data; periodi UE autonomi/totalizzati, unità, overlap e periodi non datati; un giorno anteriore non valutabile; date anteriori al 2022-06-16, fonti stale e validità/provenance.

**Perimetro V4.14q:** solo specifica documentale e review dell'esatto testo v2. Fuori scope: modifiche a Knowledge/Rules/Tests/Engine, calcoli individuali, riconoscimento, decorrenza, pagamento, pro-rata/importi e prima data complessiva IT/ES/UE. Un GO autorizza solo la specifica documentale v2, non runtime.

**Autorizzazione review:** l'utente ha ri-autorizzato il 2026-10-16 un solo tentativo indipendente, con timebox complessivo massimo di cinque minuti. Timeout significa esito non ricevuto, non GO/NO-GO; nessun retry ulteriore senza nuova autorizzazione.

### Esito review normativa indipendente — 2026-10-16

**NO-GO** per l'esatta specifica `spanish-first-eligibility-contract/v2`; review read-only conclusa nel timebox, senza dati personali o modifiche. La direzione day-level e fail-closed è confermata, ma per rendere il contratto implementabile restano sei blocchi: (1) matrice/enum e derivazione del fatto causante per RD 453/2022 art. 3.1, 3.2(a-e), 3.3 e finestre di domanda distinte; (2) regole temporali della disposizione finale decima e transitoria unica, inclusi i casi 3.2 e la distinzione fra domanda reale/ipotetica; (3) requisiti LGSS source-bound artt. 165.1, 205.1(a-b), 205.3 e DT 7, con anchor corretti, carenza 15 anni e 2/15, periodi completi e versionamento; (4) computo UE verificabile: periodo ex 1(t), totalizzazione necessaria ex art. 6, diritti autonomi/aggregati, art. 51, overlap ex 987/2009 art. 12 e conversioni art. 13; (5) schema testabile per lower bound, materialità, esiti ternari e differenza fra contratto invalido e prova mancante; (6) output con `human_review_required: true` obbligatorio e non conclusivo.

Fonti primarie indicate dal reviewer: [RD 453/2022, BOE testo autentico](https://www.boe.es/eli/es/rd/2022/06/14/453/dof/spa/pdf) e [pubblicazione BOE con disposizioni transitoria/finale](https://www.boe.es/buscar/doc.php?id=BOE-A-2022-9850&lang=es); [LGSS, testo autentico originario](https://boe.es/eli/es/rdlg/2015/10/30/8/dof/spa/pdf) e [consolidato informativo BOE](https://www.boe.es/buscar/act.php?id=BOE-A-2015-11724); [Reg. 883/2004 atto](https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX%3A32004R0883) e consolidato 2019-07-31; [Reg. 987/2009 atto](https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX%3A32009R0987) e consolidato 2018-01-01. Il consolidato resta documentale; prevalgono gli atti autentici pubblicati in GU/DOUE.

V4.14q chiude solo il ciclo documentale NO-GO; V4.14 resta `blocked`. Il successivo candidato V4.14r dovrà risolvere questi sei blocchi in una v3 documentale e ottenere una nuova autorizzazione esplicita prima del gate normativo. Nessuna modifica a Knowledge/Rules/Tests/Engine, calcolo, riconoscimento, decorrenza, pagamento, pro-rata o timeline complessiva.

---

## Incremento completato precedente — V4.14p — Spanish national first-eligibility-month contract audit

**Stato:** `done` — GO limitato alla definibilità documentale; NO-GO alla bozza come contratto implementabile
**Tipo:** `audit`

### Piano

Definire, prima di qualsiasi regola eseguibile, il contratto source-bound per la ricerca del primo mese in cui potrebbe essere acquisito il diritto alla pensione contributiva ordinaria spagnola nel solo Regimen General. Il perimetro candidato include: requisiti e scala d'età LGSS artt. 165/205 e DT 7; hecho causante secondo RD 453/2022; carenza generale e specifica secondo lo status al fatto causante e, quando applicabile, anchor dalla cessazione dell'obbligo contributivo; aggregazione UE dei soli periodi rilevanti per acquisire il diritto. Il contratto deve distinguere mese candidato, data del fatto causante e data/condizioni di domanda, e non deve inferire riconoscimento, decorrenza economica o pagamento.

La ricerca proposta scandisce i candidati in ordine cronologico usando solo periodi e status con provenienza/validità verificabili. Per ogni mese serve una valutazione separata delle condizioni nazionali e dell'eventuale totalizzazione UE. Primo candidato non valutabile, storia incompleta, status o anchor ignoto, regola non coperta o totalizzazione irrisolta interrompono la scansione con `null` e `data_gaps`: non si salta a un mese successivo. Output candidato: primo mese di eligibility supportato, non data pensionistica complessiva.

### Perimetro e stop

Solo audit del contratto per pensione ordinaria contributiva nel Regimen General e fonti ufficiali spagnole/UE. Fuori scope: altri regimi, anticipata/parziale/flessibile, pro-rata/importi, riconoscimento, decorrenza, pagamento, regole eseguibili e dati personali. Nessuna modifica a Knowledge/Rules/Tests/Engine prima dell'esito indipendente. V4.14 resta `blocked` finché i percorsi nazionali e l'overlay UE non sono valutati.

### Fonti e verifica

Fonti: BOE LGSS (consolidato aggiornato 2026-10-03), RD 453/2022 artt. 3-4, Seguridad Social ufficiale e EUR-Lex Reg. 883/2004/987/2009. La data consolidata non sostituisce il controllo degli atti ufficiali e delle date di efficacia. Review normativa indipendente conclusa con GO limitato alla definibilità e NO-GO alla bozza come implementabile. Suite completa Engine: 762 test, 0 failure, 0 errori, 0 skipped; roadmap audit, execution guardrails e diff-check passano. Nessuna modifica a Knowledge/Rules/Tests/Engine e nessun dato personale.

### Esito review normativa indipendente — 2026-10-16

Il reviewer concede **GO limitato alla definibilità documentale** e **NO-GO alla bozza corrente come contratto implementabile**. La LGSS consolidata BOE è aggiornata al 2026-10-03; RD 453/2022 è efficace dal 2022-06-16; EUR-Lex riporta i consolidati 883/2004 al 2019-07-31 e 987/2009 al 2018-01-01. Il consolidato resta informativo e va legato agli atti autentici.

Finding da risolvere in una nuova versione: (1) cercare per giorno e proiettare il mese, mai valutare convenzionalmente a fine mese; (2) distinguere data candidata, fatto causante, data/ipotesi di domanda e percorso ex art. 3 RD 453/2022; (3) acquisire separatamente status al fatto causante, obbligo contributivo in quella data e data di cessazione dell'obbligo; (4) limitare il pack corrente a `valid_from=2022-06-16` o aggiungere copertura storica; (5) includere Reg. 883/2004 artt. 1(t), 6, 50-52 e 51 e Reg. 987/2009 artt. 12-13 nel contratto UE; (6) formalizzare lower bound/materialità della scansione e trattare unità, overlap o periodi UE senza collocazione temporale come gap; (7) non elevare la guidance Seguridad Social sopra RD 453.

Nessun GO a modifiche Knowledge/Rules/Tests/Engine, pro-rata/importi, date individuali, riconoscimento, decorrenza, pagamento o prima data complessiva. Il successivo incremento candidato V4.14q dovrà presentare una specifica giornaliera v2 per review indipendente; il GO di V4.14p non si trasferisce a quella versione.

### Prossimo incremento candidato — V4.14q

Correggere la specifica date-level in documentazione/roadmap, legare le fonti e fissare gli input per i casi ex art. 3 RD 453, quindi richiedere un nuovo gate normativo sulla versione esatta prima di Knowledge/Rules/Tests/Engine. Questo è un nuovo ciclo: richiede autorizzazione esplicita; nessun dato personale.

## Incremento completato precedente — V4.14o — Audit di vigenza delle fonti UE per il contratto Art.57

**Stato:** `done` — GO normativo limitato all'aggiornamento documentale delle fonti UE
**Tipo:** `audit`

### Piano

Confrontare, alla data 2026-10-16, le disposizioni UE effettivamente invocate dal contratto V4.14n e dalle note IT/ES con gli atti autentici e le modifiche ufficiali pertinenti: Reg. 883/2004 artt. 50-57 e Allegato VIII parti 1/2; Reg. 987/2009 artt. 12-13, 43, 46-47 e 93-94. Registrare per ciascun riferimento l'atto, la modifica/rectifica, l'efficacia e l'ambito territoriale, distinguendo testo autentico da consolidato documentale.

### Perimetro e stop

Solo fonti UE necessarie a verificare il contratto Art.57 e aggiornamenti minimi delle note Knowledge dopo GO indipendente. Fuori scope: casi individuali, timeline o pro-rata eseguibili, rule pack, test funzionali, engine, modifiche normative nazionali non necessarie e dati del workspace. Massimo 2 deleghe. Se la vigenza o l'applicabilità territoriale non è provata, documentare i gap e mantenere V4.14 `blocked`; nessun GO runtime.

### Evidenza iniziale

**Esito del gate:** GO limitato alla nota Knowledge UE dopo confronto con gli atti autentici e review indipendente. Per 883/2004, il consolidato corrente EUR-Lex è 2019-07-31: 2019/1149 modifica l'art. 1 e inserisce l'art. 74a, non gli artt. 50-57; 2017/492 tocca Allegato VIII per voci Polonia/Svezia/Regno Unito, non Italia/Spagna. Per 987/2009, il consolidato corrente è 2018-01-01: 2017/492 modifica solo Allegati 1 e 3, non gli artt. 12-13, 43, 46-47 o 93-94. Sono state registrate le rettifiche 2016 al Reg. 1368/2014 (Allegato 1), 2018 (987/2009 art. 75(1), anche versione ES), 2023 (883/2004 art. 14(2), HR) e 2026 (987/2009, HR/SV), senza impatto sugli articoli richiamati. La proposta COM(2026) 980 è espressamente esclusa dal diritto vigente. Per Italia/Spagna, entrambe UE, il gate non estende l'esito a SEE/Svizzera.

### Verifica prevista

Verifiche finali: review normativa indipendente (GO limitato al documento), suite completa Engine 762 test, 0 failure, 0 errori, 0 skipped; validazione `current-work.schema.json`; `roadmap_audit.py` OK (`current=V4.14b`, `audit_due=false`); `validate-execution-guardrails.py` OK; `git diff --check` OK. Nessuna modifica a Rules, Tests, Engine o calcoli. V4.14n conserva GO limitato alla specifica documentale v0.17; V4.14 resta `blocked` e la timeline non è approvata.

## Ultimo incremento funzionale — V4.14h

**Titolo:** Italian post-1995 20-year contribution plus threshold eligibility path
**Stato:** `done` — GO normativo limitato sul path e suite engine completa verde, 762 test con 0 failure, 0 errori e 0 skip.
**Tipo:** functional

### Obiettivo

Costruire la ricerca deterministica del primo mese supportato per il ramo italiano post-1995 con 20 anni qualificanti e importo pensionistico mensile documentato almeno pari alla soglia dell'assegno sociale applicabile. Il GO normativo pre-implementazione è limitato a questo contratto; il ramo è separato da V4.14g (71 anni/5 anni effettivi) e non produce la prima data complessiva.

### Piano

1. Cercare solo nei mesi osservati coperti dal pack, a partire da 2026-01; definire il risultato come il primo mese in cui tutti i requisiti sono provati alla fine del mese, non come giorno esatto o prima data complessiva.
2. Per ogni mese, richiedere snapshot source-bound del totale cumulativo dei 20 anni qualificanti e prove separate dell’importo pensionistico documentato e della soglia annuale; non convertire unità, calcolare importi o proiettare contributi.
3. Vincolare ogni prova d’importo al mese o a un intervallo di validità che lo includa; mantenere scope source-bound per coorte post-1995, dipendente FPLD nell’AGO, gestione singola e profilo ordinario, con cessazione provata non oltre la fine del mese candidato.
4. Scansionare in ordine cronologico: se età e 20 anni sono provabili in un anno con soglia non supportata (2027–2028 nel pack corrente), fermarsi su quel primo candidato con `not_assessed` + `data_gaps`; non saltarlo per dichiarare eleggibile un mese successivo.
5. Rifiutare storia incompleta, fonti stale/fuori copertura, unità ambigue e profili esclusi; mantenere `human_review_required` e testare confini 2026–2028, amount evidence mensile, soglie esatte, gap annuali e storia incompleta.

**Fuori scope:** prima data complessiva, ramo 71/5 già chiuso in V4.14g, profili speciali, altre gestioni, ES/UE, importi calcolati, riconoscimento, decorrenza, pagamento, contribuzione futura, workspace.
**Stop condition:** il risultato è denominato esclusivamente “primo mese di eligibility — percorso post-1995 20 anni + soglia”; ogni gap resta esplicito e V4.14 rimane `blocked`.

### Gate normativo enabling slice — 2026-10-14

**Esito:** GO limitato sull’enabling slice. Il pack e il consumer vincolano il 2026 a 546,24 EUR/13 mensilità, separano le provenance e bloccano 2027–2028 come gap; lo scope è FPLD dipendente nell’AGO. Allora restavano fuori scope la ricerca mensile completa, la prima data complessiva e ogni timeline, importo calcolato, riconoscimento, decorrenza o pagamento.

### Gate normativo pre-implementazione ricerca mensile — 2026-10-14

**Esito:** GO limitato dopo revisione del contratto. NO-GO iniziale risolto precisando valutazione a fine mese, prove mensili source-bound separate per contribuzione e importo, validità dell'importo sul mese candidato, scansione cronologica con stop al primo candidato la cui soglia annuale non è supportata e fail-closed su storia/scope/freshness. Autorizza solo il consumer descritto sopra; non sblocca V4.14.

### Verifica implementazione e gate di chiusura — 2026-10-14

Il consumer `search_first_post_1996_ordinary_threshold_eligibility_month` e il modulo eligibility passano 26/26 test; il GO normativo post-implementazione è limitato a questo path e non rileva regressioni sul ramo 71/5. Il gruppo regressioni della remediation passa 156/156 test. La suite completa dell'engine passa 762/762 test, con 0 failure, 0 errori e 0 skip. V4.14h è chiusa; V4.14 resta `blocked` per i gate di timeline separati.

### Rettifica verifica suite — 2026-10-14

La remediation ha corretto il conteggio/catalogo del corpus citabile, aggiornato fixture sintetiche ES/UE per dichiarare lo status assicurativo richiesto e rispettare la validità 2026 del pack, allineato le aspettative al gate freshness condiviso, sostituito il test POSIX con una verifica platform-aware e il link privilegiato con una junction Windows rilevata dal consumer, e reso stabile il test di autenticazione API senza body anticipato. La review normativa indipendente ha dato GO limitato alle sole correzioni di fixture/aspettative: nessuna regola, soglia o formula è cambiata. V4.14 resta `blocked` finché non è definita e verificata la timeline IT/ES/UE e la distinzione fra eligibility, riconoscimento, decorrenza e primo pagamento.

### Incremento documentale chiuso — V4.14i

Roadmap audit eseguito il 2026-10-15: OK (`current=V4.14b`, `functional_since_audit=2`, `audit_due=false`). V4.14a non è selezionabile perché dipende dalla timeline V4.14, ancora `blocked` dal NO-GO sul contratto completo. V4.14i è `completed` come audit documentale: dopo i due NO-GO corretti, il reviewer indipendente ha emesso GO limitato sulle precisazioni di art. 57(2)-(3), raccordo con art. 52 e transitorio art. 94(1); suite completa engine 762/762, 0 failure, 0 errori, 0 skip. Caveat per un futuro uso eseguibile: esplicitare art. 52(4)(i)-(ii), incluse condizioni anti-cumulo artt. 54-55 ed eccezione art. 55(2). Nessuna modifica a Rules/Engine e nessun calcolo di date; il GO non approva timeline né V4.14, che resta `blocked`. Oggi il motore può cercare un mese di eligibility soltanto nei due rami italiani path-specific approvati; non calcola la prima data complessiva IT/ES/UE né riconoscimento, decorrenza economica o primo pagamento. Prossimo passo: ricalcolare con roadmap-index; V4.14a resta non selezionabile.

### Incremento documentale chiuso — V4.14j — Art. 52(4)(i)-(ii)

**Stato:** `done` — GO normativo limitato, solo Knowledge/documentazione.

Il caveat segnalato dal reviewer di V4.14i è stato verificato sul testo ufficiale/consolidato EUR-Lex e integrato nella nota Knowledge: art. 52(4) richiede condizioni cumulative (caso in Allegato VIII parte 1; regole anti-cumulo artt. 54-55 assenti o eccezione art. 55(2) applicabile; art. 57 non applicabile nel caso concreto). La nota distingue inoltre parte 1 e parte 2 dell'Allegato VIII e registra che la versione consolidata 2019 non elenca voci IT/ES in parte 1, con riserva sugli schemi specifici e atti successivi. Review normativa indipendente: GO limitato al diff documentale.

**Verifica:** suite completa engine 762/762 con 0 failure, 0 errori e 0 skip; roadmap audit, guardrail e schema planner da confermare al gate di chiusura. **Fuori scope:** rule pack, test eseguibili, Engine, importi/pro-rata, date individuali, timeline IT/ES/UE e accesso a `family-office-workspace/`. V4.14 resta `blocked`; nessun calcolo complessivo è approvato. Prossimo passo: V4.14k, riesame normativo indipendente del contratto per il primo mese complessivo IT/ES/UE; nessuna implementazione o data individuale prima di un GO esplicito.

### Incremento abilitante completato — V4.14k — First overall pension month contract reassessment

**Stato:** `done` — NO-GO per il primo mese complessivo; GO limitato alla pianificazione di ulteriori slice.
**Tipo:** `audit`

Il reviewer normativo indipendente conclude che l'attuale perimetro non può restituire un primo mese complessivo IT/ES/UE non nullo. Mancano la ricerca mensile nazionale spagnola, la ricerca del percorso italiano pre-1996, la copertura di tutti i percorsi potenzialmente anteriori e un overlay UE che separi diritti autonomi/totalizzati. Il consumer UE accetta un solo `retirement_date`; il consumer spagnolo valuta il mese fornito e non cerca il primo.

Finding immediato di coerenza: la Knowledge descrive l'art. 57 in termini di durata assicurativa giuridicamente riconosciuta e condizioni cumulative, mentre il rule pack/consumer eseguibile usa una soglia fissa di 12 mesi di calendario. Il contract non espone separatamente l'eventuale esonero dall'obbligo di pagamento. Inoltre la matrice timeline contiene una nota storica incoerente sullo stato del pack. Questi rilievi non sono stati corretti in V4.14k e richiedono un gate successivo.

**Decisione:** NO-GO per Rules/Engine, date individuali o prima data complessiva; GO solo per pianificare il contratto fail-closed che combina ricerche nazionali indipendenti e restituisce `null + data_gaps` se un percorso potenzialmente anteriore resta non valutato. Restano distinti eligibility, aggregazione/pro-rata, riconoscimento, decorrenza e pagamento. Review statica; nessun dato personale/workspace consultato.

**Fonti verificate:** EUR-Lex Reg. 883/2004 artt. 50-57 e Reg. 987/2009 artt. 12-13; BOE LGSS consolidato aggiornato al 2026-10-03, artt. 165/205 e DT 7; RD 453/2022, artt. 3-4. Le fonti amministrative INPS sono guidance ufficiale, non fonte legislativa primaria. Le fonti e i periodi specifici restano da legare nei rule pack.

### Gate normativo chiuso — V4.14l — Art. 57 duration and payment-obligation contract audit

**Stato:** `done` — GO limitato alla Knowledge; NO-GO al criterio eseguibile basato su 12 mesi di calendario
**Tipo:** `audit`

Il reviewer conferma che art. 57(1) richiede congiuntamente durata giuridica strettamente inferiore a un anno e assenza di diritto autonomo considerando soltanto i periodi dello Stato/schema; Reg. 987/2009 artt. 12-13 impone periodi comunicati, classificazione delle sovrapposizioni, unità originaria e conversioni specifiche. I parr. 2-3 riguardano importo teorico e attribuzione dell'obbligo di pagamento, distinti dall'eligibility nazionale e dal pro-rata. La soglia eseguibile `spain_months < 12` è NO-GO: la Knowledge non può giustificare un conteggio di mesi di calendario senza schema e conversione provati.

### Gate pre-implementazione chiuso — V4.14m — Art. 57 source-bound duration contract

**Stato:** `done` — NO-GO limitato sul contratto proposto
**Tipo:** `audit`

Il reviewer conferma che la struttura di base è corretta, ma non ancora sufficiente per autorizzare Rules/Tests/Engine. Richiede un contratto corretto e una nuova review pre-implementazione. Finding essenziali: aggiungere benefit/legislazione/versione/data di materializzazione del rischio e rilevanza di ogni periodo per quella prestazione; distinguere le conversioni art. 13 per scopo ex art. 6, art. 52 o non applicabile, includendo granularità, conversione aggregata/annuale, frazioni/arrotondamenti e massimi annuali; classificare tutti i casi art. 12, inclusa la presunzione del par. 6 e usare art. 43(1) Reg. 987/2009 per teorico/effettivo; source-bind diritto autonomo alla regola nazionale, validità, data di rischio e prove; orchestrare art. 57(3) per tutte le istituzioni; usare short-circuit ternario e `not_applicable` per i campi condizionali.

### Incremento completato — V4.14n — Complete Art. 57 contract specification

**Stato:** `done` — GO normativo limitato alla specifica documentale v0.17, nessun runtime
**Tipo:** `audit`

Redigere la specifica completa recependo i finding V4.14m: oggetto normativo legato a Stato, prestazione, schema, legislazione/versione, data di materializzazione del rischio e data di valutazione; periodi comunicati classificati e rilevanti per il beneficio; art. 12 con categorie/enumerazioni e par. 6 per date imprecise; art. 13 solo quando e per lo scopo di conversione pertinente, distinguendo comunicazione aggregata/annuale, unità sorgente/destinazione, direzione, frazioni/arrotondamenti e massimo annuale; art. 43(1) per teorico ed effettivo; verifica autonoma nazionale source-bound; Allegato VIII parte 2; orchestrazione multi-istituzione per art. 57(3); status ternari separati e short-circuit con gap solo sui campi decisivi non valutati.

Il risultato resta fail-closed senza trasformare ogni `null` in gap: campi condizionali non pertinenti assumono `not_applicable`; condizioni false decisive short-circuitano; dati decisivi mancanti producono `article_57_not_assessed + data_gaps`. Il reviewer indipendente ha dato GO limitato all'esatta specifica documentale v0.17 dopo aver ricalcolato i vettori v4 e verificato il golden duration-mode razionale e il gate umano. Il GO non autorizza modifiche Knowledge/Rules/Tests/Engine, calcoli o decisioni; V4.14 resta `blocked`.

#### Contratto v0.17 — numeri esatti e revisione umana obbligatoria, GO documentale limitato

Il record è una valutazione di uno specifico beneficio, schema, normativa e data di rischio, non un totale generico degli anni contributivi.

| Campo | Forma/valori | Vincolo |
|---|---|---|
| `contract_schema_version` | `v0.17` | Obbligatorio solo al root; missing/unknown/incompatible invalida strutturalmente il contratto; vietato nei nested |
| `canonicalization_profile` | `fo-art57-c14n-v4` | Obbligatorio al root, segment e treatment; deve coincidere esattamente ai tre livelli; missing/unknown/mismatch invalida strutturalmente il contratto |
| `human_review_required` | `true` | Obbligatorio e non disattivabile al root; conclusioni su Art. 57, obbligo o pagatore restano preliminari e non sono decisioni legali definitive |
| `member_state`, `benefit_id`, `benefit_type` | ID di giurisdizione e beneficio | Necessari per isolare il beneficio esaminato |
| `scheme_id`, `competent_institution` | ID versionati | Devono identificare lo schema nazionale e l'istituzione che comunica/applica i periodi |
| `applicable_legislation_id`, `applicable_legislation_version` | ID/versione + `valid_from`/`valid_to` | Devono coprire `risk_materialization_date` |
| `risk_materialization_date`, `assessment_date` | date ISO | La prima fissa il momento rilevante per le condizioni; la seconda documenta quando è stata valutata la regola |
| `transitional_applicability` | record source-bound per Stato e data di applicazione | Dichiara regola di transizione applicabile, date territoriali, disposizione, fatto trigger, stato ternario ed evidenze; l'ignoto decisivo blocca la valutazione |
| `periods[]` | periodi comunicati per Stato/schema | Conservare valore/unità originari, inizio/fine o precisione disponibile e `evidence_refs` |
| `period_kind` | `insurance`, `employment`, `self_employment`, `residence` | Tipo del periodo; è un asse distinto dalla natura assicurativa |
| `insurance_nature` | `compulsory`, `voluntary`, `continued_optional`, `equivalent`, `not_applicable` | Natura attestata/classificata con fonte; non inferirla dal solo intervallo temporale |
| `qualifies_for_or_directly_increases_benefit` | `true`, `false`, `null` | Determinato per il beneficio specifico secondo la legislazione sotto cui il periodo è maturato |
| `article_12_treatments[]` | record `{schema_version, canonicalization_profile, segment_id, treatment_id, rule, participant_period_refs[], competing_period_refs[], resolution, assignment_target, evidence_refs[]}` | `schema_version` e `canonicalization_profile` sono obbligatori e root-matched; `contract_schema_version` non è ammesso nei nested; trattamento legato a un solo segmento; `participant_period_refs[]` identifica tutti e soli i periodi le cui disposition lo referenziano; ID canonico univoco; per art. 12(5) `assignment_target` è obbligatorio e fonte-proveniente |
| `aggregation_needed_under_article_6` | `true`, `false`, `null` + `aggregation_purpose` | Per art. 12(2), indica se l'aggregazione è necessaria e per quale scopo ex art. 6; non aggiunge periodi indiscriminatamente |

Per v0.17 la codifica razionale è parte dello schema dei valori, non cambia la serializzazione JSON: oggetti `{numerator, denominator}` canonici con chiavi ASCII ordinate, interi decimali e nessun float. In tutte le grammatiche sottostanti, ogni placeholder `number` e ogni misura/risultato quantitativo usa questo oggetto razionale (anche quando è intero); fanno eccezione solo contatori/indici dichiarati esplicitamente interi. Il paragrafo di serializzazione e gli esempi v0.16 sottostanti descrivono la versione precedente; in questa candidata si applicano `contract_schema_version: v0.17` e `schema_version: v0.17` nei nested. `human_review_required` deve restare `true` in ogni output decisionale; mancante, `false` o sovrascritto rende invalido il contratto e nessun consumer può convertirlo in decisione definitiva.

Vettore v0.17 interval: mantenendo i campi del golden storico sottostante, ma impostando `canonicalization_profile: fo-art57-c14n-v4` e `schema_version: v0.17`, il preimage produce `segment_id=sha256:6d8f0bd5b7cce6a2c3e6e00aa88618f3de7a964b866fcb0ea7ee587021eb5b83`; con il medesimo treatment aggiornato al profilo/versione e al nuovo segment ID, `treatment_id=sha256:65e1749c07c5dd6f4fe34bad3b8cb06600c8440664c8e93cc8333efccca02355`. Il serializer base resta `015abd7f5cc57a2dd94b7590f04ad8084273905ee33ec5cebeae62276a97f862`.

Golden duration-mode v0.17, vettore sintetico non normativo: il preimage canonico `{"canonicalization_profile":"fo-art57-c14n-v4","parent_period_refs":["period-r"],"schema_version":"v0.17","source_bounds":[{"native_duration":{"precision":"exact","unit":"day","value":{"denominator":2,"numerator":3}},"native_end":null,"native_start":null,"period_ref":"period-r"}]}` contiene esattamente 3/2 giorni e produce `segment_id=sha256:de46b19ee6ba979c92f5bd3daa54d3c07f981df22db3e923176566574d5db604`. Il test deve ricostruire questi byte, rifiutare il corrispondente float `1.5`, la forma non ridotta `6/4`, denominatore non positivo e campi extra; valori razionali già normalizzati equivalenti hanno una sola rappresentazione e un solo hash canonico.

Art. 12(6) non equivale a “overlap ignoto = gap”: se non è possibile determinare precisamente quando il periodo è maturato, la presunzione di non sovrapposizione opera solo se è favorevole all'interessato e ragionevolmente applicabile. Vanno conservati i fatti che provano entrambe le condizioni; altrimenti il trattamento resta non valutato. Per equivalenze concorrenti, art. 12(5) assegna il periodo all'istituzione dello Stato cui la persona era soggetta obbligatoriamente per ultima prima del periodo, oppure alla prima successiva se prima non vi era assoggettamento obbligatorio.

Matrice operativa obbligatoria per `article_12_treatments[]` (i riferimenti sono a periodi/stati concreti; ogni risoluzione deve registrare regola, concorrenti, esito e prove):

| Regola | Condizione | Trattamento deterministico |
|---|---|---|
| `article_12_2_aggregation` | Periodi di assicurazione, lavoro subordinato, lavoro autonomo o residenza in Stati diversi | Aggregare ai fini dell'art. 6 soltanto quanto necessario e solo se i periodi non si sovrappongono. |
| `article_12_3_compulsory_over_voluntary` | Periodo di assicurazione/residenza obbligatoria coincide con periodo volontario o volontario continuato secondo la legislazione di un altro Stato | Considerare soltanto il periodo obbligatorio. |
| `article_12_4_non_equivalent_over_equivalent` | Periodo di assicurazione/residenza non equivalente coincide con periodo equivalente di un altro Stato | Considerare soltanto il periodo non equivalente. |
| `article_12_5_equivalent_assignment` | Periodo equivalente concorrente attribuibile a uno Stato | Assegnare all'istituzione dello Stato di ultima assicurazione obbligatoria prima del periodo; se assente, a quella del primo assoggettamento obbligatorio successivo. |
| `article_12_6_imprecise_timing_presumption` | Il momento di completamento di periodi di assicurazione/residenza non è determinabile precisamente | Presumere non sovrapposizione con periodi di assicurazione/residenza di altri Stati e tenerne conto solo se vantaggioso e ragionevolmente possibile. |

Il record espone solo al root `contract_schema_version: "v0.16"` e `canonicalization_profile: "fo-art57-c14n-v3"`; il root non usa `schema_version`. Ogni segmento e trattamento espone localmente `canonicalization_profile` e `schema_version`, entrambi obbligatori e identici ai valori del root (`schema_version == contract_schema_version` e `canonicalization_profile` uguale al root); i nested non possono contenere `contract_schema_version`. Non è ammessa inheritance: campi mancanti, profilo/schema sconosciuto o non compatibile, o qualunque mismatch root/segment/treatment invalidano strutturalmente il contratto. I preimage JSON hanno chiavi fisse e nessun campo aggiuntivo: `segment_id` usa `{canonicalization_profile, parent_period_refs, schema_version, source_bounds[]}`; `treatment_id` usa `{assignment_target, canonicalization_profile, competing_period_refs, evidence_refs, participant_period_refs, resolution, rule, schema_version, segment_id}`. Gli array di ID sono unici e ordinati per byte UTF-8. Le chiavi sono i nomi ASCII del contratto e ordinate lessicograficamente per byte UTF-8; collisioni dopo normalizzazione NFC sono invalide. La serializzazione canonica scrive i caratteri Unicode NFC direttamente in UTF-8 (senza BOM), senza whitespace; `/` resta letterale; `"` e `\\` sono escaped; ogni carattere U+0000–U+001F è escaped esclusivamente come `\\u00xx` con cifre esadecimali minuscole. Null obbligatori espliciti, campi opzionali assenti omessi; interi decimali senza zeri iniziali, floating point vietato. SHA-256 dei byte UTF-8 restituisce `sha256:` + 64 cifre esadecimali minuscole. Gli ID sorgente sono immutabili. `source_bounds[]` contiene sempre le stesse chiavi `period_ref`, `native_start`, `native_end`, `native_duration`; ciascun campo temporale è oggetto tipizzato o null. Modalità `interval`: start ed end sono entrambi non-null e duration è null; modalità `duration`: start/end null e duration non-null; modalità `unresolved`: start/end null e duration ha `value:null`, `precision:unknown`, `data_gaps` non vuoto. Nessuna chiave è omessa. Per il preimage segmento, `source_bounds[]` deve corrispondere biunivocamente a `parent_period_refs[]`: `period_ref` unici, stessi riferimenti senza mancanti/eccedenti, e ordinamento crescente dei record per `period_ref` in byte UTF-8; una violazione invalida il segmento. Ogni `competing_period_ref` e `participant_period_ref` deve appartenere a `parent_period_refs[]` e avere una disposition nel segmento; `participant_period_refs[]` è il set ordinato di tutti e soli i periodi la cui disposition referenzia quel `treatment_id`. Il set deve coincidere esattamente con l'insieme dei `period_ref` delle disposition che lo referenziano; competitor è un sottoinsieme dei participant. Riferimenti esterni o senza disposition invalidano strutturalmente il trattamento. `segment_id` si calcola su tutti i periodi parent e sui rispettivi bound ordinati secondo tale regola. `treatment_id` include `assignment_target:null` per regole diverse da art. 12(5), mentre per art. 12(5) include l'ID di istituzione selezionato; `assignment_target` è anche presente come dato di input/evidenza nel trattamento e l'output `assigned_institution_ref` è derivato esclusivamente dal singolo trattamento art. 12(5) referenziato e validato. L'ordinamento serializza gli output e non crea priorità legali.

Vettore golden segmento (due parent, modalità interval per entrambi): bytes UTF-8 del preimage `{"canonicalization_profile":"fo-art57-c14n-v3","parent_period_refs":["period-a","period-v"],"schema_version":"v0.16","source_bounds":[{"native_duration":null,"native_end":{"precision":"day","unit":"date","value":"2026-01-30"},"native_start":{"precision":"day","unit":"date","value":"2026-01-01"},"period_ref":"period-a"},{"native_duration":null,"native_end":{"precision":"day","unit":"date","value":"2026-02-13"},"native_start":{"precision":"day","unit":"date","value":"2026-01-15"},"period_ref":"period-v"}]}` producono `segment_id=sha256:2403435838bbb67faa3036fa4985febd5eb662b24608867b0b726c8168fa2ce1`. Golden test per il serializer base: `{"a":1}` → `sha256:015abd7f5cc57a2dd94b7590f04ad8084273905ee33ec5cebeae62276a97f862`.

Vettore golden trattamento: bytes UTF-8 del preimage `{"assignment_target":null,"canonicalization_profile":"fo-art57-c14n-v3","competing_period_refs":["period-v"],"evidence_refs":["evidence-1"],"participant_period_refs":["period-a","period-v"],"resolution":"include_compulsory_exclude_voluntary","rule":"article_12_3_compulsory_over_voluntary","schema_version":"v0.16","segment_id":"sha256:2403435838bbb67faa3036fa4985febd5eb662b24608867b0b726c8168fa2ce1"}` producono `treatment_id=sha256:0efb22b143e869fa15b47973c869922df9cc47c1e6407e61a39131d2c89a6590`.

Frammento golden integrato degli identificatori e dei riferimenti (gli altri campi di valutazione sono omessi perché non concorrono a questi hash):

```json
{
  "contract_schema_version": "v0.16",
  "canonicalization_profile": "fo-art57-c14n-v3",
  "segment": {
    "segment_id": "sha256:2403435838bbb67faa3036fa4985febd5eb662b24608867b0b726c8168fa2ce1",
    "canonicalization_profile": "fo-art57-c14n-v3",
    "schema_version": "v0.16",
    "parent_period_refs": ["period-a", "period-v"],
    "source_bounds": [
      {"native_duration": null, "native_end": {"precision": "day", "unit": "date", "value": "2026-01-30"}, "native_start": {"precision": "day", "unit": "date", "value": "2026-01-01"}, "period_ref": "period-a"},
      {"native_duration": null, "native_end": {"precision": "day", "unit": "date", "value": "2026-02-13"}, "native_start": {"precision": "day", "unit": "date", "value": "2026-01-15"}, "period_ref": "period-v"}
    ],
    "period_dispositions": [
      {"period_ref": "period-a", "treatment_refs": ["sha256:0efb22b143e869fa15b47973c869922df9cc47c1e6407e61a39131d2c89a6590"]},
      {"period_ref": "period-v", "treatment_refs": ["sha256:0efb22b143e869fa15b47973c869922df9cc47c1e6407e61a39131d2c89a6590"]}
    ]
  },
  "article_12_treatments": [
    {"assignment_target": null, "canonicalization_profile": "fo-art57-c14n-v3", "competing_period_refs": ["period-v"], "evidence_refs": ["evidence-1"], "participant_period_refs": ["period-a", "period-v"], "resolution": "include_compulsory_exclude_voluntary", "rule": "article_12_3_compulsory_over_voluntary", "schema_version": "v0.16", "segment_id": "sha256:2403435838bbb67faa3036fa4985febd5eb662b24608867b0b726c8168fa2ce1", "treatment_id": "sha256:0efb22b143e869fa15b47973c869922df9cc47c1e6407e61a39131d2c89a6590"}
  ]
}
```

Le `resolution` ammesse restano vincolate al `rule`: par. 2 `aggregate_non_overlapping_if_needed`, `not_aggregated_not_needed`, `overlap_source_bound_single_count`, `overlap_not_assessed`; par. 3 `include_compulsory_exclude_voluntary`; par. 4 `include_non_equivalent_exclude_equivalent`; par. 5 `assign_last_prior_compulsory_state`, `assign_first_subsequent_if_no_prior`; par. 6 `presume_non_overlap_and_include`, `not_applied_not_advantageous`, `not_applied_not_reasonably_possible`. Una combinazione rule/resolution incompatibile è invalida; più trattamenti compatibili sono mantenuti tutti, mentre conflitti non risolvibili dalle precedenze espresse restano non valutati.

Il periodo grezzo non riceve un unico esito se contiene porzioni temporalmente diverse. Prima della classificazione produrre `period_coordination_segments[]`; ciascun segmento rappresenta un intervallo/durata nativa in cui il set dei periodi concorrenti e la regola applicabile restano costanti:

```text
period_coordination_segments[]:
  segment_id
  canonicalization_profile
  schema_version
  parent_period_refs[]
  source_bounds[]  # una riga per parent, chiavi canoniche definite sopra
  native_interval_or_duration: {value_or_start_end, unit, precision}
  competing_period_refs[]
  overlap_relation: none | partial | full | unknown
  period_dispositions[]:
    period_ref
    source_native_duration: {value: number | null, unit, precision, data_gaps[]}
    included_native_duration: {value: number, unit, precision} | null
    excluded_native_duration: {value: number, unit, precision} | null
    treatment_refs[]
    derived_inclusion_result: included | excluded_by_treatment | not_assessed | not_applicable
    assignment_result: assigned_to_institution | not_applicable | not_assessed
    assigned_institution_ref | null
    data_gaps[]
    evidence_refs[]
  aggregation_under_article_6:
    aggregation_purpose
    retained_period_refs[]
    not_added_period_refs[]
    intersecting_native_durations[]: {period_ref, value: number | null, unit, precision, data_gaps[]}
    counted_once_duration: {value, unit, precision, conversion_method, evidence_refs[]} | null
    competent_institution
    institutional_evidence_refs[]
    result: aggregated_non_overlapping | overlap_source_bound_single_count | overlap_not_assessed | not_applicable
  evidence_refs[]
```

In ogni segmento, `period_dispositions[]` deve avere esattamente un elemento per ogni `parent_period_ref`: i `period_ref` sono unici e il loro insieme coincide con quello dei parent; elementi mancanti, extra o duplicati invalidano il segmento. Ogni `treatment_ref` deve risolvere univocamente un `article_12_treatments[]` record con `segment_id` uguale a quello del segmento e `treatment_id` ricalcolato sul preimage corrente; ref duplicati, dangling o cross-segment invalidano il record. Ogni treatment dichiarato deve essere referenziato da almeno una disposition del suo segmento (nessun treatment orfano). Una mutation a qualunque `source_bounds` invalida il `segment_id` e, a cascata, tutti i `treatment_id` e riferimenti derivati; non si accettano hash precedenti.

Vincolo v0.14 di partecipazione esatta: per ciascun `treatment_id`, `participant_period_refs[]` deve coincidere (stesso insieme, univoco e ordinato) con tutti e soli i `period_ref` le cui disposition contengono quel trattamento; `competing_period_refs[]` è un sottoinsieme dei partecipanti. Nessuna disposition può riferire il trattamento da fuori di tale set, e nessun partecipante può omettere il riferimento. Root: obbligatori `contract_schema_version` e `canonicalization_profile`, senza `schema_version`. Segment e treatment: obbligatori `schema_version` e `canonicalization_profile`, entrambi identici ai valori root. Il frammento golden contiene tutti e soli questi campi di versione, è autonomo per ricostruire entrambi gli ID e non richiede inheritance convenzionale.

La validazione strutturale precede la derivazione normativa: parent/bound/disposition cardinality errata, ID/preimage/hash non corrispondente, duplicato, dangling, orfano, cross-segment o participant-set non esatto rende l'intero record invalido (non `not_assessed`). `not_assessed + data_gaps` è riservato a una struttura valida con prova normativa decisiva assente/imprecisa, fonte non disponibile o condizione non valutabile; la mancanza della prova non si codifica come riferimento dangling.

I risultati delle disposition sono output derivati, non input indipendenti. Le quote sono anch'esse derivate e non possono essere impostate indipendentemente: se il risultato è `included`, `included_native_duration` deve coincidere esattamente con la durata sorgente e `excluded_native_duration` vale zero; per `excluded_by_treatment` vale l'opposto; se è `not_assessed`, entrambe sono null e `data_gaps` non è vuoto; per `not_applicable`, entrambe sono null senza gap di valutazione. Se la durata sorgente non è esatta, una disposizione che richiede quote esatte resta `not_assessed`. Derivazione: (a) con struttura e riferimenti validi, evidenza decisiva mancante, regole applicabili incompatibili o conflitto include/exclude senza precedenza esplicita → `derived_inclusion_result=not_assessed + data_gaps`; (b) il trattamento art. 12(3) o (4) esclude quel periodo sulla sola porzione coincidente → `excluded_by_treatment`; (c) periodo non pertinente al beneficio → `not_applicable`; (d) periodo pertinente, tutte le regole decisive risolte e nessuna esclusione applicabile → `included`; (e) art. 12(5) assegna un equivalente → `assignment_result=assigned_to_institution` soltanto se `treatment_refs[]` contiene esattamente un trattamento art. 12(5) strutturalmente valido e il suo `assignment_target` coincide con l'unica istituzione provata dalla regola; se l'assegnazione normativa non è decidibile per evidenza assente, `not_assessed + data_gaps`. Il par. 5 da solo non determina inclusione/esclusione. Art. 12(2) resta aggregazione separata e non sovrascrive la disposizione individuale.

`source_native_duration.value` e ogni valore in `intersecting_native_durations[]` possono essere null se limiti/precisione non determinano una misura: unità/precisione e `data_gaps` restano obbligatori. Solo con `derived_inclusion_result` incluso/escluso e valore sorgente esatto vale `included + excluded = source_native_duration`; non si fabbricano split o conversioni. L'intersezione single-count registra vettori per fonte/unità; `counted_once_duration` è valorizzato solo se una conversione supportata e source-bound produce unità comune, altrimenti null con gap. Per `overlap_source_bound_single_count`, periodi mantenuti/non aggiunti, vettore delle durate intersecate, scopo, istituzione competente ed evidenza sono obbligatori. `period_coordination_result` è derivato e incluso solo se tutte le disposition decisive sono risolte.

Per art. 43(1) il contratto espone due viste source-bound distinte: `theoretical_calculation_period_view` e `actual_calculation_period_view`. Ciascuna include `period_dispositions[]` riferite alle fonti e ai `treatment_id` condivisi, più `applied_article_12_paragraphs: [3,4,5,6]` e risultato ternario per ogni periodo. La vista teorica e quella effettiva conservano le rispettive unità, conversioni legalmente ammesse ed evidenze; differenze di risultato sono esplicite. Il par. 2 non appartiene a queste viste e non viene propagato per art. 43(1); l'aggregazione ex art. 6 resta un output separato. ID/preimage/profilo/versione assenti, dangling, cross-segment o stale hash rendono invalida l'intera struttura; solo una prova normativa sostanziale mancante con tutti gli identificatori validi produce `not_assessed + data_gaps` limitati ai fatti decisivi.

Il record transitorio è valutato per ciascuno Stato e per la relativa data territoriale di applicazione, mai assumendo un'unica data UE:

```text
transitional_applicability:
  basic_regulation_883_87:
    member_state
    territorial_application_date: {date, legal_source_ref}
    contingency_date
    pre_application_period_refs[]
    result: applicable | not_applicable | not_assessed
    evidence_refs[]
    data_gaps[]
  implementing_regulation_987_93: {result, evidence_refs[], data_gaps[]}
  regulation_465_2012_883_87a:
    title_ii_change_caused_by_465_2012: true | false | null
    legislation_before_change
    legislation_after_change
    relevant_situation_unchanged: true | false | null
    within_ten_year_limit: true | false | null
    opt_out_request_date: date | null
    opt_out_effective_date: date | null  # derived by the statutory date rule
    result: old_legislation_continues | new_legislation_applies | not_applicable | not_assessed
    evidence_refs[]
    data_gaps[]
  pension_transitional_987_94_1:
    benefits_due_for_pre_application_period: true | false | null
    contingency_pre_application: true | false | null
    claim_awarded_before_application_date: true | false | null
    prior_leg: {legal_basis, period, amount_result_ref, evidence_refs[]}
    basic_regulation_leg: {legal_basis, period, amount_result_ref, evidence_refs[]}
    comparison: prior_higher | basic_higher | equal | not_assessed | not_applicable
    preserved_result: prior_leg | basic_regulation_leg | not_assessed | not_applicable
    result: both_legs_assessed | not_applicable | not_assessed
    data_gaps[]
```

Artt. 87(1)-(3) Reg. 883/2004 e 93 Reg. 987/2009 restano il percorso transitorio generale; periodi anteriori possono concorrere alla determinazione di diritti sotto il nuovo regolamento, senza creare prestazioni per il tempo anteriore, e i diritti su eventi precedenti restano soggetti al par. 1. L'art. 93 è una regola di coordinamento procedurale: il suo esito si deriva dall'applicazione dell'art. 87 nello stesso Stato e alla stessa data, senza aggiungere un gate relativo a una domanda già liquidata. `claim_awarded_before_application_date` appartiene solo al distinto trigger dell'art. 94(1), non al record dell'art. 87. Art. 87a è valutato separatamente e solo se il cambio di legislazione Titolo II deriva dal Reg. 465/2012; richiede prova della situazione rimasta invariata, limite massimo di dieci anni ed eventuale richiesta di opt-out con `request_date` e data effettiva distinta: richiesta entro il 29-09-2012 compreso → efficacia 28-06-2012; richiesta successiva → efficacia dal primo giorno del mese successivo alla richiesta. La deroga opera al massimo per dieci anni dalla data di applicazione del Reg. 465/2012 e si arresta se la situazione cambia. Non è una regola generica per la decorrenza territoriale. Per art. 94(1), la salvaguardia è valutata solo se la prestazione è dovuta per il periodo anteriore all'applicazione territoriale, l'evento assicurato è anteriore e la domanda non era stata liquidata prima della data di applicazione. Si conservano due gambe temporali distinte: periodo precedente secondo Reg. 1408/71/accordi applicabili e periodo successivo secondo il regolamento base; se il risultato della gamba precedente è maggiore si mantiene quello, se il nuovo risultato è maggiore o uguale si applica la gamba del regolamento base. Se un trigger è falso → `not_applicable`; se ignoto, una gamba non è provata o gli importi non sono comparabili → `not_assessed + data_gaps`. Ogni data territoriale e fatto trigger è source-bound.

#### Conversione e durata sotto l'anno

La durata dell'art. 57(1) e la conversione per aggregazione sono risultati distinti. Art. 13 Reg. 987/2009 è la conversione necessaria per aggregare ai sensi dell'art. 6 Reg. 883/2004; non è un convertitore universale che decide da solo la durata nazionale “inferiore a un anno” dell'art. 57. Il test di durata deve essere attestato sulla base della legislazione/schema applicabile e dei periodi pertinenti dello Stato; `duration_basis`, `duration_assessment_evidence_refs` e `duration_strictly_less_than_one_year: true|false|null` ne tracciano la base. I periodi di altri Stati non entrano nel test del diritto autonomo acquisito considerando soltanto i periodi dello Stato valutato.

Quando una conversione è normativamente necessaria, il record riproducibile contiene:

```text
source_duration: {value, unit}
conversion_required: true | false | null
conversion_purpose: article_6_aggregation | article_52_calculation | not_applicable
source_unit, target_unit, conversion_direction, conversion_method
communication_granularity: aggregate | yearly
scheme_day_basis: 5_day | 6_day | 7_day | not_applicable
conversion_result:
  converted_value, converted_unit
  operation_scope: aggregate | yearly
  steps[]
  annual_maximum_applied
  evidence_refs[]
article_13_fraction_rule, article_13_rounding_rule
article_13_annual_maximum_check
legal_duration_for_article_57: {value, unit}
one_year_comparator: {value, unit, legal_basis_refs[]}
duration_basis, duration_assessment_evidence_refs
duration_strictly_less_than_one_year: true | false | null
```

La durata giuridica dell'art. 57(1) resta distinta dall'eventuale conversione per aggregazione ex art. 6: il comparatore di un anno e la durata effettivamente usata devono avere unità, valori e base normativa/evidenziale espliciti. Art. 13 Reg. 987/2009 non diventa un convertitore universale della soglia nazionale. L'uso in contesto art. 52 non autorizza a estendere art. 13 oltre il proprio ambito: applicare anche art. 43(1), che richiama art. 12(3)-(6) per importo teorico ed effettivo; ogni conversione aggiuntiva deve avere una base specifica, altrimenti `not_assessed`.

Per l'aggregazione ex art. 6, la conversione usa la base comunicata dall'istituzione dello Stato di completamento. Tabella art. 13(1)(b):

| Schema basato su | 1 giorno corrisponde a | 1 settimana | 1 mese | 1 trimestre | massimo giorni/anno |
|---|---:|---:|---:|---:|---:|
| 5 giorni | 9 ore | 5 giorni | 22 giorni | 66 giorni | 264 |
| 6 giorni | 8 ore | 6 giorni | 26 giorni | 78 giorni | 312 |
| 7 giorni | 6 ore | 7 giorni | 30 giorni | 90 giorni | 360 |

Per unità non giornaliere: 3 mesi/13 settimane = 1 trimestre; 1 anno = 4 trimestri/12 mesi/52 settimane; per settimane↔mesi si converte in giorni con la base a sei giorni. Art. 13(1)(d) richiede la conversione dei periodi frazionari alla successiva unità intera più piccola (con frazioni di anno convertite in mesi salvo schema a trimestri); il par. 1(e) richiede poi l'intero superiore quando il risultato convertito contiene una frazione. Sono operazioni diverse, da registrare nei passaggi, non un generico “doppio arrotondamento”. Art. 13(2) limita il totale convertito per anno civile a 264/312/360 giorni (secondo schema), 52 settimane, 12 mesi o 4 trimestri; se il periodo convertito corrisponde al massimo annuo previsto dallo schema d'origine, la conversione non può ridurlo sotto quel massimo. Art. 13(3): conversione in un'operazione se le comunicazioni sono aggregate, anno per anno se sono comunicate annualmente.

#### Diritto autonomo, orchestrazione e output

`autonomous_right_from_state_periods_only` è un record source-bound con `result: true|false|null`, `national_benefit_rule_pack_id`, `national_rule_version`, intervallo di validità, `risk_materialization_date`, periodi nazionali usati, condizioni diverse dalla contribuzione valutate, riferimenti probatori e gap. `risk_materialization_date` è il nome canonico anche per questo sotto-record; non esistono alias `risk_date` o `autonomous_right_result`. La prova determina se il beneficio matura sotto la legge nazionale considerando esclusivamente quei periodi; non equivale al semplice confronto con una soglia contributiva.

Per il par. 3 raccogliere `concerned_institutions[]`, risultato art. 57(1) per ognuna, prova di `all_concerned_institutions_relieved`, `article_57_3_last_state`, prova che le condizioni di quello Stato sono soddisfatte ed `article_57_3_evidence_refs`. Lo Stato residuale richiede evidenza/procedura istituzionale: mai inferirlo dall'ultima data o dall'ordine dell'input. Un'istituzione decisiva non valutata mantiene il par. 3 `not_assessed`.

Per evitare che una dichiarazione di completezza venga attribuita a un insieme diverso da quello valutato, `concerned_institutions_complete` usa `{result, institution_ids[], evidence_refs[]}`. `institution_ids[]` deve essere unico, ordinato per byte UTF-8 e coincidere esattamente con gli `institution_id` di `concerned_institutions[]`; altrimenti l'insieme non è provato e il payer resta `not_assessed + data_gaps`.

Output indipendenti: `national_eligibility_status`; `article_57_exception_status` (`applies`, `does_not_apply`, `excluded_by_57_4`, `not_assessed`); `theoretical_amount_period_inclusion` (`required_by_57_2`, `not_triggered`, `not_assessed`); `pro_rata_amount_status`; `national_payment_obligation_status` (`ordinary_article_52`, `relieved_under_57_1`, `payer_under_57_3`, `not_assessed`). Se l'art. 57 si applica ai periodi dell'altro Stato, `article_57_blocks_article_52_4_condition_iii: true`; non decide da solo gli altri presupposti dell'art. 52(4). Art. 57(4) (Allegato VIII parte 2) esclude l'articolo intero; l'art. 52(5) va valutato separatamente.

`annex_viii_part_2_applicability` è un record source-bound con `result: true|false|null`, `annex_consolidation_version`, `annex_validity_or_applicability_date`, `matched_scheme_entry`, `scheme_match_status` e `annex_evidence_refs[]`. Il valore `false` richiede il controllo dello schema concreto sulla versione applicabile dell'Allegato VIII; non si deduce dalla sola giurisdizione. Il record e il suo booleano non condividono lo stesso livello/identificatore.

Propagazione minima obbligatoria:

```text
article_57_exception_status == applies
  => theoretical_amount_period_inclusion = required_by_57_2
  => national_payment_obligation_status = relieved_under_57_1
     oppure payer_under_57_3 solo dopo il test multi-istituzione

all_concerned_institutions_relieved == true AND article_57_3_last_state provato
  => un solo payer_under_57_3
all_concerned_institutions_relieved == true AND last_state non provato
  => national_payment_obligation_status = not_assessed

article_57_exception_status == excluded_by_57_4
  => theoretical_amount_period_inclusion = not_triggered
     (non attivato dall'art. 57; art. 52(5) resta separato)

pro_rata_amount_status
  => not_assessed/downstream fino al distinto contratto art. 52
```

Logica di decisione minima:

```text
if annex_viii_part_2_applicability.result is true:
    article_57_exception_status = excluded_by_57_4
elif duration_strictly_less_than_one_year is false:
    article_57_exception_status = does_not_apply
elif autonomous_right_from_state_periods_only.result is true:
    article_57_exception_status = does_not_apply
elif duration_strictly_less_than_one_year is true
     and autonomous_right_from_state_periods_only.result is false
     and annex_viii_part_2_applicability.result is false:
    article_57_exception_status = applies
else:
    article_57_exception_status = not_assessed
    data_gaps += only_the_decisive_unknowns
```

Campi condizionali non pertinenti devono essere `not_applicable`, non `null`. Una condizione falsa che esclude art. 57 short-circuita e non richiede dati inutili sugli altri rami. Se art. 57 è applicabile per una o più istituzioni, il par. 3 richiede comunque la valutazione multi-istituzione prima di assegnare un pagatore residuale. Per art. 52(4), conservare come esiti separati Allegato VIII parte 1, artt. 54-55/55(2) e il blocco della condizione (iii); non emettere un singolo booleano “pro-rata waived” senza tutti i presupposti.

#### Regressioni di contratto richieste prima del runtime

- 11 mesi di calendario che, secondo l'unità e la legge provate, equivalgono a un anno; durata <, = e > un anno;
- conversioni giornaliere su basi 5/6/7, conversione settimana/mese, frazioni, unità intera successiva minore ex art. 13(1)(d), intero superiore ex art. 13(1)(e), massimo annuale e salvaguardia del massimo nello schema d'origine;
- comunicazione aggregata contro comunicazione per anno, con output di conversione riproducibile;
- overlap obbligatorio/volontario, non equivalente/equivalente, periodi equivalenti in più Stati e date imprecise ex art. 12(6) vantaggiose/non vantaggiose/non ragionevoli;
- ogni riga della matrice art. 12(2)-(6), inclusi enum `rule`/`resolution`, sovrapposizioni multiple e propagazione dell'esito normalizzato per periodo a calcolo art. 6/52 e art. 43(1);
- overlap parziale obbligatorio/volontario e non equivalente/equivalente con residuo non coincidente conservato; overlap obbligatorio-obbligatorio non risolto dai parr. 3-4; tre o più periodi concorrenti; segmentazione indeterminabile e metodo di conteggio singolo source-bound;
- ID trattamento canonici e univoci, risoluzioni ammesse per rule, riferimenti duplicati/dangling invalidi, serializzazione canonica e risultati byte-stabili sotto tutte le permutazioni dei periodi;
- conservazione delle durate per fonte con unità/precisione diverse; viste distinte teorica ed effettiva ex art. 43(1) che applicano solo i parr. 3-6 e mantengono lineage e gaps distinti;
- profilo/versione di canonicalizzazione e algoritmo `segment_id`; risoluzione derivata dai trattamenti riferiti, senza campo libero contraddittorio; output canonico anche per intervalli imprecisi o basati solo su durata;
- golden preimage/hash per segment e treatment; vettori validi interval/duration/unresolved e rifiuto ibridi; segmenti multi-parent con permutazioni stabili e `source_bounds.period_ref` duplicati/mancanti/extra invalidi; competitor presente/dangling/disposition assente e rigenerazione concatenata segment→treatment;
- record integrato golden con un'unica disposition per parent e trattamento nello stesso segmento; dispositions duplicate/mancanti/extra; treatment cross-segment e refs duplicati/orfani/dangling; mutation del bound che invalida ID e ref a cascata; permutazioni di parent, bound, disposition e ref; profile/schema root mancanti, sconosciuti o mismatched → invalidità strutturale; source, legislazione o evidenza normativa mancanti in record valido → `not_assessed + data_gaps`;
- ricalcolo ID dall'intero frammento root→segment→treatment senza campi ereditati; root contiene solo `contract_schema_version`+profilo, nested contiene `schema_version`+profilo; mismatch/missing/unknown contract profile/schema root/segment/treatment invalida; uguaglianza esatta `participant_period_refs`↔dispositions che referenziano il treatment; invalidità strutturale distinta da fonti/legislazione/evidenze normative mancanti in record valido (`not_assessed + data_gaps`);
- rifiuto di `contract_schema_version` nested e `schema_version` root; `canonicalization_profile` obbligatorio e uguale a root in ciascuno dei tre livelli;
- razionali ridotti e normalizzati (`gcd=1`, denominatore positivo, zero `0/1`), frazioni in input e nei passaggi Art. 13, vettori duration-mode/hash byte-stabili, frazioni equivalenti e arrotondamenti legali espliciti; rifiuto di float, razionali non ridotti/negativi nel denominatore/zero alternativo;
- `human_review_required` obbligatorio e sempre `true`; mancante, falso o disattivato invalida il record e ogni output downstream conserva il gate umano, senza etichettarsi come decisione definitiva;
- matrice root/segment/treatment che rifiuta `contract_schema_version` nei nested, richiede schema/profilo matching in segment e treatment, e rifiuta campi versionati in livello errato; per art. 43(1) ID assente/dangling/cross-segment/stale hash invalida, mentre prova normativa mancante con ID validi produce solo i gap decisivi;
- quote incluse/escluse con precisione per fonte; conservazione obbligatoria solo per disposition risolte; valori null + gap per durata non valutata; intersezioni miste mantenute per sorgente o convertite solo con metodo provato;
- `transitional_applicability` source-bound per data territoriale/giurisdizione secondo artt. 87 e 87a Reg. 883/2004 e artt. 93-94 Reg. 987/2009; casi pre/post-applicazione e pensione non liquidata con salvaguardia dell'importo maggiore quando dovuta;
- golden bytes/hash `{"a":1}` → `015abd7f5cc57a2dd94b7590f04ad8084273905ee33ec5cebeae62276a97f862`; test NFC-equivalenza, collisioni di chiavi normalizzate, null-vs-omesso e permutazioni;
- golden preimage completo e hash `segment_id`, casi intervallo/durata/unresolved, null espliciti, chiavi NFC duplicate e array riordinati;
- matrici di derivazione per ogni rule/resolution, quote incluse/escluse esatte o entrambe null secondo stato, attribuzione art. 12(5) derivata dal singolo trattamento e target validato, esiti contraddittori invalidi; durata sorgente/intersezione nulla con precisione ignota senza valori fabbricati;
- art. 87a solo per cambi Titolo II causati dal Reg. 465/2012, scenario invariato/cambiato, limite decennale, request date al 29-09-2012 e dopo, efficacia derivata 28-06-2012/primo giorno del mese successivo;
- art. 87 senza gate di domanda liquidata; art. 93 derivato per medesimo Stato/data; art. 94(1) tutti i trigger, prestazione dovuta/non dovuta, domanda liquidata/non liquidata, due gambe temporali, importo precedente maggiore, nuovo maggiore, uguale e non comparabile.
- disposizione distinta per ciascun periodo sorgente sullo stesso segmento, trattamento multiplo con ID univoci e ordinamento deterministico; invarianza rispetto all'ordine di input; attribuzione identica per periodo nel richiamo dell'art. 43(1);
- conteggio singolo source-bound con periodi mantenuti/non aggiunti, durata intersecata, scopo di aggregazione, istituzione competente ed evidenza istituzionale; `not_assessed + data_gaps` quando una prova decisiva manca;
- periodo irrilevante per il beneficio, diritto autonomo presente o assente, condizioni nazionali ulteriori, pack/versione fuori validità;
- Allegato VIII parte 2 vero/falso/ignoto; durata o diritto autonomo falsi che short-circuitano; `null` decisivo che produce solo i gap pertinenti;
- più istituzioni: una non valutata, tutte esonerate, ultimo Stato provato/non provato; nessuna inferenza dall'ordine dei dati;
- nessuna propagazione automatica fra eligibility nazionale, importo teorico, pro-rata, riconoscimento, decorrenza o obbligo/primo pagamento;
- art. 57 applicabile blocca solo la condizione 52(4)(iii), mentre gli altri presupposti 52(4) e il ramo 52(5) restano indipendenti.

#### Esito review indipendente v0.2 — 2026-10-15

**NO-GO limitato alla v0.2 esatta.** Il reviewer conferma il nucleo normativo e individua quattro correzioni contrattuali finite, recepite nella candidata v0.3 sopra: (1) separare `period_kind` e `insurance_nature`, consentire relazioni multiple art. 12 e indicare se l'aggregazione ex art. 6 è necessaria ai fini dell'art. 12(2); (2) registrare valori/unità sorgente, risultato e passaggi di conversione, durata legale e comparatore di un anno esplicito; correggere la descrizione degli artt. 13(1)(d)-(e); (3) definire l'applicabilità dell'Allegato VIII parte 2 con versione, schema abbinato ed evidenze; (4) fissare transizioni deterministiche tra eccezione art. 57, importo teorico, obbligo/pagatore e stato pro-rata. Dopo queste correzioni serve un nuovo gate sulla specifica esatta. Nessun GO runtime, modifica Rules/Tests/Engine o accesso a dati personali.

#### Esito review indipendente v0.3 — 2026-10-15

**NO-GO limitato alla v0.3 esatta.** Conversione/durata, Allegato VIII parte 2 e propagazione degli output sono stati chiusi. Restavano due correzioni finite, ora recepite nella candidata v0.4: rendere vincolante la matrice semantica degli artt. 12(2)-(6), con esito normalizzato per periodo e gap solo quando decisivo; canonicalizzare tre riferimenti inconsistenti (`duration`, `risk_date`/`autonomous_right_result`, e booleano-vs-record Allegato VIII). Il nucleo dell'art. 57 è confermato; il GO pre-implementazione resta pendente fino a review indipendente della v0.4. Verifica fonti al 15 ottobre 2026: consolidati EUR-Lex Reg. 883/2004 (31-07-2019) e Reg. 987/2009 (01-01-2018); Reg. 988/2009 introduce art. 57(4), art. 52(5) e sostituisce Allegato VIII con applicazione dal 01-05-2010. Nessun runtime, test eseguibile o dato personale.

#### Esito review indipendente v0.4 — 2026-10-15

**NO-GO limitato alla v0.4 esatta.** Reviewer conferma matrice/enum artt. 12(2)-(6), identificatori canonici, conversioni, art. 43(1), Allegato VIII e short-circuit. Un solo blocker residuo: l'esito unico per periodo e la risoluzione generica dell'overlap non rappresentavano deterministically gli overlap parziali (rimuovevano anche il residuo non coincidente) né gli overlap ex art. 12(2) non risolti dai parr. 3-4. La candidata v0.5 aggiunge segmenti con periodi sorgente, intervalli/durate native, concorrenti, relazione overlap, regola/risoluzione, quote incluse/escluse ed evidenze; gli overlap non prioritizzati richiedono conteggio singolo source-bound o `not_assessed` se decisivi. Aggiunte regressioni su overlap parziali, obbligatorio-obbligatorio, residui e almeno tre concorrenti. Nessun altro blocker normativo. Fonti e limiti confermati come nella review v0.3; nessun runtime, test eseguibile o dato personale. Il nuovo ciclo indipendente sulla v0.5 richiede una decisione utente separata.

#### Esito review indipendente v0.5 — 2026-10-16

**NO-GO limitato alla v0.5 esatta.** L'impostazione su overlap parziali, residui e fallimento chiuso è confermata; resta un difetto di attribuzione: un segmento con più `parent_period_refs[]` ha un solo esito, quindi non rappresenta periodi inclusi/esclusi diversamente, trattamenti concorrenti o il riferimento al trattamento escludente. La candidata v0.6 aggiunge `period_dispositions[]` per singolo periodo sorgente, `treatment_id` univoci, `treatment_refs[]`, ordine deterministico delle regole 3-6 prima dell'aggregazione ex par. 2 e invarianza rispetto all'ordine di input. Il single-count registra periodi mantenuti/non aggiunti, durata intersecata, scopo, istituzione ed evidenza; in assenza di prove decisive resta `overlap_not_assessed + data_gaps`. Regressioni richieste: overlap parziali con esito per periodo, tre concorrenti e trattamenti multipli, single-count source-bound con test d'invarianza e propagazione per periodo ex art. 43(1). La review non approva Knowledge, Rules, Tests, Engine o calcoli; il gate sulla candidata v0.6 resta pendente.

#### Esito review indipendente v0.6 — 2026-10-16

**NO-GO limitato alla v0.6 esatta.** Restano quattro blocker: esito single-count riuscito assente dall'enumerazione; ID/riferimenti dei trattamenti non integralmente definiti né canonici; durata nativa per fonte non rappresentabile con unità diverse; viste distinte teorica ed effettiva per art. 43(1) assenti. La candidata v0.7 aggiunge enum `overlap_source_bound_single_count`, ID SHA-256 da JSON canonico, integrità referenziale e ordinamento serializzato senza introdurre priorità legali, durata nativa source-specific con conservazione delle quote, e due viste ex art. 43(1) limitate ai parr. 3-6. Regressioni richieste comprendono duplicati/dangling/permutazioni, esito single-count supportato e non supportato, unità miste, viste teorico/effettivo distinte e output canonico. Scope review limitato ai consolidati EUR-Lex 2018/2019; nessuna autorizzazione Knowledge/Rules/Tests/Engine o calcolo. Nuovo gate indipendente sulla v0.7 pendente.

#### Esito review indipendente v0.7 — 2026-10-16

**NO-GO limitato alla v0.7 esatta.** Le viste teorica/effettiva e il single-count sono chiusi; restano gap nella canonicalizzazione/versione degli ID, nella coerenza fra trattamenti e disposizioni, nella rappresentazione di quote incerte/unità miste e nell'applicabilità transitoria. La candidata v0.8 definisce il profilo `fo-art57-c14n-v1`, generazione stabile degli ID segmento/trattamento, integrità dei riferimenti, risoluzioni derivate dai trattamenti, output canonico anche quando i confini non sono date esatte, conservazione condizionata alle disposizioni determinate e viste source-bound delle durate miste. Aggiunge `transitional_applicability` per Stato/data territoriale e artt. 87/87a Reg. 883/2004 e 93-94 Reg. 987/2009, incluse le condizioni della doppia valutazione pensionistica e della salvaguardia. Regressioni richieste: edge case canonicalizzazione/ID; conflitti treatment/disposition; durata non valutata senza valori inventati; single-count a unità miste; scenari pre/post 1-05-2010 e salvaguardia. Il consolidato è strumento documentale, non testo autentico GU né prova di vigenza 2026. La review non approva Knowledge, Rules, Tests, Engine o calcoli. Gate v0.8 pendente.

#### Esito review indipendente v0.8 — 2026-10-16

**NO-GO limitato alla v0.8 esatta.** Quattro finding: (1) il profilo di canonicalizzazione e gli ID mancavano della struttura preimage e dei vettori hash interoperabili; (2) il risultato di una disposition era ancora scrivibile indipendentemente dai trattamenti referenziati; (3) valori sorgente/intersezione non potevano essere null con data gap; (4) l'art. 87a era generalizzato oltre il trigger del Reg. 465/2012 e l'art. 94(1) non separava le due gambe temporali. La candidata v0.9 ha aggiunto versioni/schema e preimage/hash, derivazione deterministica, nullability source-bound e record separati. Fonti EUR-Lex consultate: Reg. 883/2004 consolidato 31-07-2019, artt. 87/87a; Reg. 987/2009 consolidato 01-01-2018, artt. 93/94. I consolidati sono strumenti documentali, non provano da soli la vigenza 2026. Nessuna approvazione Knowledge/Rules/Tests/Engine/calcoli.

#### Esito review indipendente v0.9 — 2026-10-16

**NO-GO limitato alla v0.9 esatta.** Il reviewer ha individuato cinque correzioni finite recepite nella candidata v0.10: (1) specificare senza ambiguità preimage, vettore completo/hash e forma di escaping JSON; (2) derivare quote incluse/escluse e assegnazione ex art. 12(5) dai trattamenti, rendendo `assignment_target` un input validato e l'output univoco; (3) separare art. 87 da art. 94 quanto al gate della domanda liquidata e derivare art. 93 dallo stesso Stato/data dell'art. 87; (4) rendere esplicita la data di richiesta/effective date dell'opt-out art. 87a e la regola temporale; (5) definire per art. 94(1) trigger della prestazione dovuta, due gambe e confronto deterministico (precedente maggiore: precedente; nuovo maggiore o pari: regolamento base). La review è limitata ai consolidati EUR-Lex 2018/2019 e non certifica l'applicabilità normativa al 2026. Nessun GO runtime né autorizzazione a modifiche Knowledge/Rules/Tests/Engine o calcoli; il gate v0.10 resta pendente.

Fonti di controllo: [Reg. 987/2009 consolidato al 1° gennaio 2018](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02009R0987-20180101), artt. 12, 13, 43, 93 e 94; [Reg. 883/2004 consolidato al 31 luglio 2019](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02004R0883-20190731), artt. 6, 52, 57, 87 e 87a. Verifica documentale: 16 ottobre 2026. I testi autentici restano quelli pubblicati nella Gazzetta ufficiale.

#### Esito review indipendente v0.10 — 2026-10-16

**NO-GO limitato alla v0.10 esatta.** Il reviewer ha rilevato tre difetti finiti recepiti nella v0.11: (1) il golden `segment_id` mescolava bound di intervallo e durata, in contrasto con le modalità ammesse; (2) mancavano corrispondenza biunivoca e ordinamento deterministico dei record `source_bounds[]` rispetto a `parent_period_refs[]`; (3) il golden `treatment_id` referenziava un competitor esterno ai parent del segmento. La v0.11 rende le modalità mutualmente esclusive, invalida bound mancanti/extra/duplicati, ordina per `period_ref` UTF-8, limita i competitor ai parent dotati di disposition e ricalcola entrambi i vettori/hash. Nessun ulteriore rilievo sostanziale nel perimetro normativo esaminato; fonti limitate ai consolidati EUR-Lex citati, senza certificazione dell'applicabilità 2026. Gate indipendente esatto v0.11 pendente; nessun GO Knowledge/Rules/Tests/Engine/calcoli.

#### Esito review indipendente v0.11 — 2026-10-16

**NO-GO limitato alla v0.11 esatta.** I golden sono conformi e gli hash ricalcolati coincidono. Restano due correzioni contrattuali finite recepite nella v0.12: materializzare nel grammar del segmento `source_bounds[]` e nel record treatment il relativo `segment_id`; fissare cardinalità e integrità referenziale esatte (una disposition unica per ogni parent e solo quelle, treatment ref univoci same-segment, nessun treatment orfano/dangling/cross-segment, invalidazione a cascata dopo mutation dei bound). Aggiunto un frammento golden integrato e regressioni su cardinalità, mutation, permutazioni e versioni ignote. Nessun GO runtime né autorizzazione Knowledge/Rules/Tests/Engine/calcoli; le fonti restano le snapshot EUR-Lex citate e non certificano applicabilità 2026. Gate v0.12 pendente.

#### Esito review indipendente v0.12 — 2026-10-16

**NO-GO limitato alla v0.12 esatta.** Gli hash sono corretti e i campi v0.11 sono materializzati, ma restano tre ambiguità recepite nella candidata v0.13: il record integrato deve esporre profilo/schema root e segment-local uguali per consentire il ricalcolo senza inheritance; i periodi partecipanti al trattamento devono coincidere esattamente con le disposition che lo referenziano; i riferimenti strutturalmente invalidi devono invalidare il contratto, mentre `not_assessed + data_gaps` resta riservato a dati normativi/probatori mancanti in una struttura valida. v0.13 aggiunge `participant_period_refs[]`, uguaglianza esplicita del profilo/versione, frammento golden autonomo e regressioni su mutation a cascata/partecipanti e distinzione invalidità-gap. Gate indipendente esatto v0.13 pendente; nessun GO a Knowledge/Rules/Tests/Engine/calcoli o applicabilità 2026.

#### Esito review indipendente v0.13 — 2026-10-16

**NO-GO limitato alla v0.13 esatta.** Incidenza partecipanti/disposition, frammento integrato e hash risultano corretti. Due correzioni finite recepite nella v0.14: fissare senza contraddizioni i campi root (`contract_schema_version` e profilo soltanto) rispetto ai campi locali segment/treatment (`schema_version` e profilo), con uguaglianza esplicita per tutti i livelli; distinguere schema/profilo contrattuale mancante/sconosciuto/incompatibile (record strutturalmente invalido) da fonti, legislazione o evidenze assenti in struttura valida (`not_assessed + data_gaps`). Aggiunte le regressioni corrispondenti. Nessun GO runtime/Knowledge/Rules/Tests/Engine/calcoli o applicabilità 2026; gate v0.14 pendente.

#### Esito review indipendente v0.14 — 2026-10-16

**NO-GO limitato alla v0.14 esatta.** Binding root/segment/treatment e hash sono confermati, ma la riga schema di `article_12_treatments[]` omette profilo/versione locali e art. 43(1) mescola ID mancanti con prove mancanti nello stesso esito. La v0.15 aggiunge i campi locali al record treatment, vieta `contract_schema_version` nei nested, e distingue invalidità per ID/profilo/schema/riferimenti non validi da `not_assessed + data_gaps` per sola prova normativa sostanziale mancante a struttura valida. Regressioni positive/negative richieste per i tre livelli e art. 43(1). Hash rigenerati per v0.15; gate indipendente esatto v0.15 pendente, nessuna approvazione runtime.

#### Esito review indipendente v0.15 — 2026-10-16

**NO-GO limitato alla v0.15 esatta.** Un solo difetto editoriale/di grammar: la riga combinata in tabella qualificava `canonicalization_profile` come root-only, mentre le regole dettagliate e i vettori lo richiedono anche in segment/treatment. La v0.16 separa le due righe: `contract_schema_version` solo root; profilo richiesto ai tre livelli e identico. Gli altri controlli passano, inclusa distinzione invalidità strutturale/prova mancante art. 43(1) e SHA-256 ricalcolati. Gate indipendente esatto v0.16 pendente; nessun GO runtime o per Knowledge/Rules/Tests/Engine/calcoli.

---

## Ultimo micro-incremento completato — V4.14g

**Titolo:** Primo mese di eligibility path-specific — alternativa post-1995 71 anni/5 effettivi
**Stato:** `done` — GO normativo limitato post-implementazione, tentativo 3/3
**Tipo:** functional

### Obiettivo

Implementare la ricerca deterministica del primo mese supportato di eligibility per il solo percorso post-1995 alternativo: età 71/71a1m/71a3m e cinque anni di contribuzione effettiva senza figurativi, dipendenti FPLD/AGO, gestione singola confermata, pack 2026-2028. Il reviewer normativo ha dato GO limitato al contratto path-specific. Il risultato deve restare distinto da una prima data complessiva e da decorrenza/pagamento.

### Piano

1. Accettare solo storia mensile completa e source-bound di accrediti, con unità/tipo originali e cumulo effettivo verificabile; nessuna proiezione dopo l'ultimo mese provato.
2. Scansionare i mesi con i requisiti del pack per ciascun anno, restituendo il primo mese eleggibile solo per il ramo a 71 anni/5 effettivi.
3. Restituire `null` + `data_gaps` su buchi, sovrapposizioni, unità o figurativi ambigui, coorte/gestione non confermate, cessazione non verificata, freshness scaduta o evidenza oltre il pack.
4. Aggiungere regressioni sintetiche sui confini temporali/contributivi e sottoporre il diff al reviewer nel tentativo 3/3.

**Fuori scope:** prima data complessiva fra tutti i rami; percorso a 20 anni con soglia d'importo; profili speciali, altre gestioni, ES/UE; giorno esatto se le prove sono mensili; importo, riconoscimento, decorrenza e pagamento; contribuzione futura e workspace.
**Verifica:** 19 test eligibility + 11 freshness; confini 2026/27/28, storia incompleta, date malformate/future, unità/tipi, figurativi, cessazione, coverage profilo, as_of esplicita e human-review marker. Reviewer normativo: GO limitato, ciclo post-implementazione tentativo 3/3. Roadmap audit, planner JSON Schema, execution guardrails, `py_compile` e `git diff --check` passano.
**Stop condition:** il risultato è denominato esclusivamente “primo mese di eligibility — percorso post-1995 alternativo”; non deve apparire come prima data complessiva o data di pensionamento/pagamento. Nessun mese oltre l'evidence o il pack può essere stimato.

**Gate normativo:** il gate pre-implementazione ha escluso la prima data complessiva (NO-GO) e autorizzato limitatamente il ramo path-specific (GO). Nel ciclo post-implementazione, i tentativi 1/3 e 2/3 hanno prodotto NO-GO circoscritti, tutti corretti; il tentativo 3/3 ha dato GO limitato al diff rivisto. V4.14g è `done`; la timeline complessiva V4.14 resta `blocked`.

**Contratto implementato:** `search_first_post_1996_alternative_eligibility_month` accetta snapshot cumulativi source-bound, consecutivi da 2026-01, con unità originale unica `years`, tipo originale e figurativi esplicitamente esclusi. Richiede periodi mensili completi, evidenza datata della coorte e cessazione, copertura source-bound del profilo su tutta la history e `as_of_date` esplicita. L'output include `as_of_date` e `human_review_required: true`; non converte unità, non proietta oltre le osservazioni e resta solo path-specific, senza giorno o data complessiva.

---

## Incremento precedente completato — V4.14e

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

## Ultimo micro-incremento completato — V4.14f

**Titolo:** Italian eligibility rule-pack legal provenance traceability
**Stato:** `done`
**Tipo:** audit abilitante Knowledge → Rules → Tests → Engine.

Ricostruire la catena delle disposizioni e degli atti attuativi che sostiene i requisiti annuali del rule pack `it.inps-old-age-eligibility.2026-2028.v2`, soprattutto la base dei 71 anni; integrare riferimenti ufficiali source-bound nel pack e rendere il consumer fail-closed su fonti e periodi mancanti. Aggiungere test sintetici di source-period/version binding; non alterare valori o scope.

- Fuori scope: ampliamento a gestioni o categorie speciali, calcolo pensionistico individuale, timeline completa, importi, date di riconoscimento/pagamento e accesso al workspace.
- Done quando: catena ufficiale legislativa/attuativa documentata e revisionata; pack provenance allineata senza cambiare valori non approvati; regressioni sintetiche passano e i consumer falliscono chiuso sui gap di fonte/periodo.
- V4.14 rimane `blocked` fino a un gate autonomo sulla timeline completa.

### Piano ed esito V4.14f — 2026-10-13

La ricostruzione documentale collega D.L. 201/2011 art. 24, gli incrementi cumulativi 2013/2016/2019, i decreti di pausa 2021/2023/2025-2026, la circolare INPS 62/2018 e la catena 2027-2028. La review indipendente ha inizialmente dato due NO-GO circoscritti; i finding sono stati corretti e il terzo tentativo, dopo verifica del percorso parser contro il test passato, ha restituito GO limitato per questo incremento.

Il consumer verifica gli ID e i ruoli obbligatori, separa efficacia giuridica da copertura pack e confronta lo schedule eseguibile con gli schedule fonte INPS; date ISO invalide e periodi invertiti falliscono chiuso. Una regressione verifica 70 anni + 3/4/5 mesi source-bound = 71 e i confini 2026-2028. Suite eligibility/freshness: 22 test passati; roadmap audit, planner schema, execution guardrails, `py_compile` e `git diff --check` passati. GO limitato solo alla provenance e allo screening ordinario IT FPLD/AGO a data candidata. Valori e perimetro non ampliati; nessuna timeline, importo, riconoscimento, decorrenza o pagamento individuale è approvato. V4.14 resta `blocked`.

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
