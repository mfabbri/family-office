# Current Next Increment

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

### Prossimo gate — V4.14n — Complete Art. 57 contract specification

**Stato:** `in_progress` — documentazione/planner, nessun runtime
**Tipo:** `audit`

Redigere la specifica completa recependo i finding V4.14m: oggetto normativo legato a Stato, prestazione, schema, legislazione/versione, data di materializzazione del rischio e data di valutazione; periodi comunicati classificati e rilevanti per il beneficio; art. 12 con categorie/enumerazioni e par. 6 per date imprecise; art. 13 solo quando e per lo scopo di conversione pertinente, distinguendo comunicazione aggregata/annuale, unità sorgente/destinazione, direzione, frazioni/arrotondamenti e massimo annuale; art. 43(1) per teorico ed effettivo; verifica autonoma nazionale source-bound; Allegato VIII parte 2; orchestrazione multi-istituzione per art. 57(3); status ternari separati e short-circuit con gap solo sui campi decisivi non valutati.

Il risultato resta fail-closed senza trasformare ogni `null` in gap: campi condizionali non pertinenti assumono `not_applicable`; condizioni false decisive short-circuitano; dati decisivi mancanti producono `article_57_not_assessed + data_gaps`. Il reviewer ha richiesto un nuovo gate normativo pre-implementazione sul contratto completo. Nessuna implementazione o calcolo finché il gate non dà GO. V4.14 resta `blocked` anche dopo un eventuale GO limitato.

#### Contratto candidato v0.5 — correzioni post-review, gate pendente

Il record è una valutazione di uno specifico beneficio, schema, normativa e data di rischio, non un totale generico degli anni contributivi.

| Campo | Forma/valori | Vincolo |
|---|---|---|
| `member_state`, `benefit_id`, `benefit_type` | ID di giurisdizione e beneficio | Necessari per isolare il beneficio esaminato |
| `scheme_id`, `competent_institution` | ID versionati | Devono identificare lo schema nazionale e l'istituzione che comunica/applica i periodi |
| `applicable_legislation_id`, `applicable_legislation_version` | ID/versione + `valid_from`/`valid_to` | Devono coprire `risk_materialization_date` |
| `risk_materialization_date`, `assessment_date` | date ISO | La prima fissa il momento rilevante per le condizioni; la seconda documenta quando è stata valutata la regola |
| `periods[]` | periodi comunicati per Stato/schema | Conservare valore/unità originari, inizio/fine o precisione disponibile e `evidence_refs` |
| `period_kind` | `insurance`, `employment`, `self_employment`, `residence` | Tipo del periodo; è un asse distinto dalla natura assicurativa |
| `insurance_nature` | `compulsory`, `voluntary`, `continued_optional`, `equivalent`, `not_applicable` | Natura attestata/classificata con fonte; non inferirla dal solo intervallo temporale |
| `qualifies_for_or_directly_increases_benefit` | `true`, `false`, `null` | Determinato per il beneficio specifico secondo la legislazione sotto cui il periodo è maturato |
| `article_12_treatments[]` | record `{rule, competing_period_refs[], resolution, evidence_refs[]}` | Ammette più relazioni/trattamenti pertinenti senza comprimere casi concorrenti in un singolo enum |
| `aggregation_needed_under_article_6` | `true`, `false`, `null` + `aggregation_purpose` | Per art. 12(2), indica se l'aggregazione è necessaria e per quale scopo ex art. 6; non aggiunge periodi indiscriminatamente |

Art. 12(6) non equivale a “overlap ignoto = gap”: se non è possibile determinare precisamente quando il periodo è maturato, la presunzione di non sovrapposizione opera solo se è favorevole all'interessato e ragionevolmente applicabile. Vanno conservati i fatti che provano entrambe le condizioni; altrimenti il trattamento resta non valutato. Per equivalenze concorrenti, art. 12(5) assegna il periodo all'istituzione dello Stato cui la persona era soggetta obbligatoriamente per ultima prima del periodo, oppure alla prima successiva se prima non vi era assoggettamento obbligatorio.

Matrice operativa obbligatoria per `article_12_treatments[]` (i riferimenti sono a periodi/stati concreti; ogni risoluzione deve registrare regola, concorrenti, esito e prove):

| Regola | Condizione | Trattamento deterministico |
|---|---|---|
| `article_12_2_aggregation` | Periodi di assicurazione, lavoro subordinato, lavoro autonomo o residenza in Stati diversi | Aggregare ai fini dell'art. 6 soltanto quanto necessario e solo se i periodi non si sovrappongono. |
| `article_12_3_compulsory_over_voluntary` | Periodo di assicurazione/residenza obbligatoria coincide con periodo volontario o volontario continuato secondo la legislazione di un altro Stato | Considerare soltanto il periodo obbligatorio. |
| `article_12_4_non_equivalent_over_equivalent` | Periodo di assicurazione/residenza non equivalente coincide con periodo equivalente di un altro Stato | Considerare soltanto il periodo non equivalente. |
| `article_12_5_equivalent_assignment` | Periodo equivalente concorrente attribuibile a uno Stato | Assegnare all'istituzione dello Stato di ultima assicurazione obbligatoria prima del periodo; se assente, a quella del primo assoggettamento obbligatorio successivo. |
| `article_12_6_imprecise_timing_presumption` | Il momento di completamento di periodi di assicurazione/residenza non è determinabile precisamente | Presumere non sovrapposizione con periodi di assicurazione/residenza di altri Stati e tenerne conto solo se vantaggioso e ragionevolmente possibile. |

`article_12_treatments[].rule` accetta esclusivamente gli identificatori della matrice; `resolution` è vincolato dalla regola: art. 12(2) `aggregate_non_overlapping_if_needed` / `not_aggregated_not_needed` / `overlap_source_bound_single_count` / `overlap_not_assessed`; art. 12(3) `include_compulsory_exclude_voluntary`; art. 12(4) `include_non_equivalent_exclude_equivalent`; art. 12(5) `assign_last_prior_compulsory_state` / `assign_first_subsequent_if_no_prior`; art. 12(6) `presume_non_overlap_and_include` / `not_applied_not_advantageous` / `not_applied_not_reasonably_possible`. Se i fatti non consentono di selezionare in modo affidabile la risoluzione e ciò può cambiare il risultato, usare `not_assessed` e registrare il gap decisivo. Quando una sovrapposizione è risolta ai sensi dei parr. 3-4, i segmenti selezionati sono quindi trattati secondo il par. 2 per l'aggregazione necessaria ex art. 6; il par. 2 non viene usato per annullare le regole specifiche di precedenza.

Il periodo grezzo non riceve un unico esito se contiene porzioni temporalmente diverse. Prima della classificazione produrre `period_coordination_segments[]`; ciascun segmento rappresenta un intervallo/durata nativa in cui il set dei periodi concorrenti e la regola applicabile restano costanti:

```text
period_coordination_segments[]:
  segment_id
  parent_period_refs[]
  native_interval_or_duration: {value_or_start_end, unit, precision}
  competing_period_refs[]
  overlap_relation: none | partial | full | unknown
  rule
  resolution
  included_native_duration
  excluded_native_duration
  result: included_after_article_12 | excluded_by_treatment_ref | not_assessed
  evidence_refs[]
```

La segmentazione conserva tutte le porzioni residue non sovrapposte. Gli artt. 12(3)-(4) si applicano solo al segmento coincidente per cui i rispettivi presupposti sono provati; non eliminano il residuo del periodo volontario/equivalente che non coincide. Per gli altri overlap del par. 2 (inclusi obbligatorio-obbligatorio o non equivalente-non equivalente) non scegliere arbitrariamente Stato o periodo: `overlap_source_bound_single_count` richiede metodo/provenance istituzionale per contare la porzione una volta sola; se non disponibile e decisivo, `overlap_not_assessed` + `data_gaps`. Unità o precisione che non permettono segmentazione deterministica producono `not_assessed` salvo presunzione art. 12(6) provata. `period_coordination_result` è una vista aggregata dei segmenti e può essere `included_after_article_12` solo quando tutte le porzioni decisive sono risolte. Ai fini del teorico/effettivo, art. 43(1) richiama espressamente l'applicazione mutatis mutandis dei soli artt. 12(3)-(6).

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

Fonti di controllo: [Reg. 987/2009 consolidato al 1° gennaio 2018](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02009R0987-20180101), artt. 12, 13 e 43; [Reg. 883/2004 consolidato al 31 luglio 2019](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02004R0883-20190731), artt. 6, 52, 57 e Allegato VIII. Verifica documentale: 15 ottobre 2026. I testi autentici restano quelli pubblicati nella Gazzetta ufficiale.

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
