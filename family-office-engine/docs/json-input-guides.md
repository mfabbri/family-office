# JSON input guides

Questa pagina elenca gli input JSON che l'utente puo' dover compilare manualmente per le capability CLI attive. I file reali stanno in `family-office-workspace/`; gli esempi in `examples/` sono sintetici.

## Regole generali

- Mantieni lo stesso `household_id` tra file collegati.
- Usa ID tecnici, non dati personali reali.
- Usa date ISO `YYYY-MM-DD` e valute ISO maiuscole come `EUR`.
- Metti le incertezze note in `data_gaps` invece di trasformarle in dati certi.
- Non inserire calcoli fiscali, pensionistici o finanziari stimati a mano se il campo richiede un fatto osservato.
- Preferisci i wizard disponibili prima di modificare JSON a mano; usano i dati gia' salvati come contesto e salvano progressivamente le risposte.

## `scenario-draft/v1`

- Comandi: `orchestration scenario-draft build --question "..."`, `orchestration scenario-draft demo`.
- Nessun JSON di input da compilare: passa una domanda in linguaggio naturale; il testo non viene conservato nello snapshot.
- Il draft mostra solo proposte esplicite da confermare e non è compatibile direttamente con `decision-scenario/v2`. Età pensionabile, date ISO, budget EUR e università dei figli sono riconosciuti soltanto quando espressi chiaramente.
- Completa prima le `confirmation_requests`, risolvi `conflicts` e `rejected_values`, poi costruisci un input `decision-scenario/v2` privato con fonti e assunzioni confermate. Non usare il draft come scenario eseguibile.

## `execution-plan-input/v1`

- Default: `../family-office-workspace/planning/execution-plan.json`.
- Comandi: `orchestration question-intent route`, `orchestration execution-plan build`, `orchestration execution-plan demo`.
- Prima instrada la domanda con i dati minimi dichiarati e copia lo snapshot `question-intent/v1` ottenuto nel campo `question_intent` del piano. Non inserire il testo della domanda.
- Ogni nodo dichiara `node_id`, `tool_id`, `depends_on` e `input_bindings`. Ogni binding contiene solo `source` (`workspace_path`, `rule_pack`, `prior_node_output` o `citation_index`), `reference`, `sensitivity` e, per output di un nodo, `node_id`.
- I valori personali o finanziari non devono essere inseriti nel piano: restano nei file privati del workspace richiamati dal binding. Un binding `sensitive` richiede `authorization: explicit_user_consent`.
- Il file descrive una preview: non invoca tool e non produce calcoli. Usa `demo` per vedere un DAG sintetico valido prima di predisporre un input privato.

## `execution-request/v1`

- Default: `../family-office-workspace/planning/execution-request.json`.
- Comando: `orchestration execute --input ../family-office-workspace/planning/execution-request.json`.
- Contiene un `execution-plan/v1` gia' `ready`, grant di autorizzazione per nodo e valori privati dei binding associati esattamente ai riferimenti del piano. Il bundle conserva riferimenti e hash dei valori, non i valori grezzi; conserva output, stati, errori e data gaps. I retry sono limitati ai tool `read_only`.

## `base-assumptions.json`

- Default: `../family-office-workspace/assumptions/base-assumptions.json`.
- Template/draft: `../family-office-workspace/assumptions/base-assumptions.template.json`, `base-assumptions.draft.json`.
- Comandi: `assumptions prepare`, `assumptions import`, `assumptions check`.
- Campi principali: `personal` per eta' e pensionamento target, `cashflow` per redditi/spese esplicite, `returns` per ipotesi tecniche dichiarate.

## `household-facts/v1`

- Default: `../family-office-workspace/household/household-facts.json`.
- Esempio: `examples/household-facts-sample.json`.
- Draft: `../family-office-workspace/household/household-facts.draft.json`.
- Comando: `household validate`.
- Campi: `household_id`, `persons`, `relationships`, `tax_residences`, `economic_roles`, `relevant_dates`, `data_gaps`.

## `ownership-beneficiary-graph/v1`

- Default: `../family-office-workspace/household/ownership-beneficiaries.json`.
- Esempio: `examples/ownership-beneficiary-graph-sample.json`.
- Draft: `../family-office-workspace/household/ownership-beneficiaries.draft.json`.
- Comando: `household ownership validate`.
- Campi: asset, debiti, quote, beneficiari, provenance, data gaps e riferimenti agli ID persona.

## `asset-availability/v1`

- Default: `../family-office-workspace/household/asset-availability.json`.
- Esempio: `examples/asset-availability-sample.json`.
- Draft/guida: `../family-office-workspace/household/asset-availability.draft.json`, `asset-availability-guide.md`.
- Comandi: `household availability wizard`, `household availability validate`.
- Campi: `asset_id`, asset class, rischio, valuta, giurisdizione, liquidita', vincoli, trattamento fiscale dichiarativo, prima disponibilita' e provenance.
- Nota: per il piano liquidita' puoi validare asset provenienti dal net worth anche prima dell'allineamento ownership con `household availability validate --skip-ownership-check`.

## `timeline-events/v1`

- Default: `../family-office-workspace/household/timeline-events.json`.
- Esempio: `examples/timeline-events-sample.json`.
- Draft: `../family-office-workspace/household/timeline-events.draft.json`.
- Comando: `household timeline validate`.
- Campi: eventi puntuali, periodi, ricorrenze, priorita', persone o asset collegati, date e data gaps.

## `lifecycle-expenses/v1` input

- Default: `../family-office-workspace/household/lifecycle-expenses.json`.
- Comando: `expenses build-lifecycle`.
- Campi: anni o periodi, categorie di spesa, importi annui o ricorrenti, valuta, inflazione dichiarata e provenance.
- Nota: il motore annualizza solo spese dichiarate e non stima budget mancanti.

## `planning-goals/v1`

- Default: `../family-office-workspace/household/planning-goals.json`.
- Esempio: `examples/planning-goals-sample.json`.
- Draft: `../family-office-workspace/household/planning-goals.draft.json`.
- Comandi: `planning goals wizard`, `planning goals prepare`, `planning goals status`, `planning goals validate`, `planning goals demo`.
- Campi: `objectives`, `constraints`, `planning_horizon`, `risk_profile`, `liquidity_policy`, `data_gaps`.

## `liquidity-plan-input/v1`

- Default: `../family-office-workspace/planning/liquidity-plan-input.json`.
- Esempio: `examples/liquidity-plan-input-sample.json`.
- Guida: `examples/liquidity-plan-input-guide.md`.
- Draft: `../family-office-workspace/planning/liquidity-plan-input.draft.json`.
- Comandi: `planning liquidity wizard`, `planning liquidity build`, `planning liquidity explain`, `planning liquidity demo`.
- Campi: `household_id`, `as_of_date`, `base_currency`, `monthly_expenses`, `minimum_reserve_months`, `concentration_threshold`, `data_gaps`.
- Nota: `explain` traduce lo snapshot costruito in asset utilizzabili/non utilizzabili e motivi leggibili.

## `decumulation-policy-set/v1`

- Default: `../family-office-workspace/planning/decumulation-policy-set.json`.
- Esempio: `examples/decumulation-policy-set-sample.json`.
- Guida: `examples/decumulation-policy-set-guide.md`.
- Draft: `../family-office-workspace/planning/decumulation-policy-set.draft.json`.
- Comandi: `planning decumulation wizard`, `planning decumulation build`, `planning decumulation demo`.
- Campi: `household_id`, `as_of_date`, `base_currency`, `current_age`, `policies`, `data_gaps`.
- Ogni policy dichiara `policy_id`, `label`, `retirement_age`, `end_age`, `annual_spending_need`, `cash_buffer_target`, `withdrawal_order`, `annual_return_sequence`, tassi espliciti e `include_rita`.
- Nota: il wizard deriva nucleo, data, valuta, fabbisogno annuo, cuscinetto e asset prelevabili da goals/liquidita'. Aliquote lasciate a `0.00` restano gap da stimare, non ipotesi fiscali definitive.

## `pension-contribution-input/v1`

- Default: `../family-office-workspace/planning/pension-contribution-input.json`.
- Esempio: `examples/pension-contribution-input-sample.json`.
- Comandi: `planning pension-contributions wizard`, `planning pension-contributions build`, `planning pension-contributions demo`.
- Campi: `household_id`, `as_of_date`, `tax_year`, `jurisdiction`, `marginal_tax_rate`, `already_deducted_contributions`, `first_employment_extra_deduction_room`, `available_liquidity`, `minimum_liquidity_after_contributions`, `options`, `data_gaps`.
- Ogni opzione dichiara `option_id`, `label`, `employee_contribution`, `employer_contribution`, `tfr_transfer`, `opportunity_cost_rate` e `horizon_years`.
- Nota: il wizard usa il piano liquidita' come contesto per liquidita' disponibile e minimo da preservare. `marginal_tax_rate`, contributi gia dedotti, extra deducibilita', costo opportunita' e contributi sono input dichiarati; se lasci `0.00` dove indicato, il valore resta gap da stimare. Il motore non calcola IRPEF completa o rendimenti.

## `tax-aware-portfolio-input/v1`

- Default: `../family-office-workspace/planning/tax-aware-portfolio-input.json`.
- Esempio: `examples/tax-aware-portfolio-input-sample.json`.
- Comandi: `planning tax-aware-portfolio build`, `planning tax-aware-portfolio demo`.
- Campi: `household_id`, `as_of_date`, `tax_year`, `jurisdiction`, `base_currency`, `options`, `data_gaps`.
- Ogni opzione dichiara `option_id`, `label`, `tax_regime`, `available_loss_offset` e `positions`.
- Ogni posizione dichiara `position_id`, `label`, `tax_category`, `tax_category_documented`, `holding_location`, `market_value`, `expected_gross_return_rate`, `annual_cost_rate` e `turnover_rate`.
- Nota: categorie fiscali, rendimenti, costi, turnover e minusvalenze sono input espliciti; il motore applica solo il rule pack versionato e non stima classificazioni o rendimenti.

## `it-es-pension-tax-classification-input/v1`

- Default: `../family-office-workspace/planning/it-es-pension-tax-classification-input.json`.
- Esempio: `examples/it-es-pension-tax-classification-input-sample.json`.
- Comandi: `planning it-es-pension-tax classify`, `planning it-es-pension-tax demo`.
- Campi: `household_id`, `as_of_date`, `tax_year`, `recipient`, `stream_classifications`, `data_gaps`.
- `recipient` dichiara `person_id`, `fiscal_residence` e `nationalities`.
- Ogni `stream_classifications` dichiara `stream_id`, `payer_country`, `service_sector`, `payer_type` e `benefit_origin`.
- Nota: il servizio non deduce automaticamente se una pensione previdenziale pubblica estera deriva da impiego privato o servizio pubblico; senza classificazione esplicita produce gap.

## `spanish-pension-net-it-resident-input/v1`

- Default: `../family-office-workspace/planning/spanish-pension-net-it-resident-input.json`.
- Esempio: `examples/spanish-pension-net-it-resident-input-sample.json`.
- Comandi: `planning spanish-pension-net build`, `planning spanish-pension-net demo`.
- Campi: `household_id`, `as_of_date`, `tax_year`, `resident_country`, `other_italian_taxable_income`, `streams`, `data_gaps`.
- Ogni stream dichiara `stream_id`, `gross_annual_amount`, `spanish_tax_withheld`, `spanish_tax_definitive`, `foreign_tax_credit_applicable` e opzionalmente `declared_credit_capacity`.
- Nota: altri redditi, lordo, ritenute e capienza credito sono input espliciti; il motore applica solo rule pack versionati e non calcola dichiarazione completa.

## `it-es-eu-pension-pro-rata-input/v1`

- Default: `../family-office-workspace/planning/it-es-eu-pension-pro-rata-input.json`.
- Esempio: `examples/it-es-eu-pension-pro-rata-input-sample.json`.
- Draft: `../family-office-workspace/planning/it-es-eu-pension-pro-rata-input.draft.json`.
- Comandi: `planning it-es-eu-pension wizard`, `planning it-es-eu-pension prepare`, `planning it-es-eu-pension build`, `planning it-es-eu-pension demo`, `planning spanish-eu-theoretical-pension build`, `planning spanish-eu-theoretical-pension demo`.
- Campi: `scenario`, `retirement_date`, `date_of_birth`, `recent_contribution_anchor_date`, `inps_history_status`, `future_assumptions_status`, `sources`, `insurance_periods`, `spanish_theoretical_pension`, `data_gaps`.
- Ogni periodo dichiara `country`, `start_date`, `end_date`, `period_type` e `source_document`; i Paesi ammessi nel contratto sono `IT` ed `ES`.
- I periodi devono coprire mesi interi. Periodi parziali o successivi allo scenario vanno risolti prima dell'input oppure dichiarati come gap.
- `spanish_theoretical_pension` dichiara importo lordo mensile e/o annuo coerente, valuta, paghe annue, fonte, `source_country: ES` e `basis: spanish_only_bases`.
- Nota: i periodi italiani servono solo per verificare il diritto per totalizzazione UE. Il comando non usa contributi italiani come basi spagnole e non deduce contribuzione futura.
- Il wizard crea un input personale nel workspace: chiede conferma esplicita di nessun contributo spagnolo futuro e registra come gap l'importo teorico spagnolo se non e' disponibile.
- `planning spanish-eu-theoretical-pension build` genera lo snapshot teorico usando i default del workspace; per anni futuri usa assunzioni proiettive dichiarate e marcate come non ufficiali. `planning it-es-eu-pension build` lo usa automaticamente se esiste, senza edit manuale dell'importo e senza passare path JSON.

## `work-exit-feasibility-input/v1` planned

- Stato: pianificato in V4.8c; non ancora disponibile nella CLI.
- Comando previsto: `planning work-exit build`.
- Obiettivo: cercare la prima data sostenibile per smettere di lavorare, non calcolare solo una data predefinita.
- Default previsto: usare snapshot gia' presenti nel workspace per INPS, pro-rata spagnolo, pensione del coniuge, pension income, patrimonio, liquidita' e spese.
- Campi probabili: data di partenza ricerca, granularita' date candidate, adulti del nucleo inclusi, vincoli minimi di sostenibilita', assunzioni future esplicite, riferimenti a snapshot e data gaps.
- Nota: date come `2037` devono essere candidate o filtri diagnostici; il risultato primario resta la prima data sostenibile con spiegazione delle date scartate. La pensione del coniuge e' parte del calcolo household; se manca, deve restare un gap esplicito.

## `pension-scenario/v1`

- Default: `../family-office-workspace/planning/pension-scenario.json`.
- Esempio: `examples/pension-scenario-sample.json`.
- Comandi: `planning pension-scenario build`, `planning pension-scenario demo`.
- Campi: `household_id`, `as_of_date`, `confirmed_at`, `selected_scenario_id`, `sources`, `scenarios`, `data_gaps`.
- Ogni scenario dichiara `scenario_id`, `label`, `assumption_status`, `retirement`, `initial_fiscal_residence`, `future_contributions`, `post_retirement_residence_changes` e `provenance`.
- `future_contributions` deve dichiarare separatamente Italia e Spagna; per il baseline Spagna usa `status: none`.
- Ogni trasferimento post-pensionamento richiede `effective_date` e `fiscal_residence`.
- Nota: il contratto registra assunzioni personali versionate. Non deduce residenza o contribuzione futura e non calcola effetti fiscali/previdenziali.

## `real-estate-plan/v1`

- Default: `../family-office-workspace/planning/real-estate-plan.json`.
- Esempio: `examples/real-estate-plan-sample.json`.
- Comandi: `planning real-estate build`, `planning real-estate demo`.
- Campi: `household_id`, `as_of_date`, `base_currency`, `properties`, `data_gaps`.
- Ogni immobile dichiara `property_id`, `asset_id`, `label`, `jurisdiction`, `currency`, `market_value`, `ownership`, `annual_costs`, `declared_taxes`, `rent_assumption`, `sale_assumption` e `provenance`.
- `ownership` richiede quote esplicite; una quota del coniuge resta tracciata e non viene fusa con quella personale.
- `rent_assumption` richiede `monthly_gross_rent` e `vacancy_months` per confrontare la locazione.
- `sale_assumption` richiede `estimated_sale_price`, `months_to_liquidity` e costi di vendita espliciti per confrontare la vendita.
- Nota: imposte, costi, canoni, vacancy e prezzo di vendita sono input espliciti. Il motore non calcola fiscalita' immobiliare normativa, successione, perizie, finanziamenti, FX o raccomandazioni.

## `investment-opportunity-comparison/v1`

- Default: `../family-office-workspace/planning/investment-opportunity-comparison.json`.
- Esempio: `examples/investment-opportunity-comparison-v1-sample.json`.
- Comandi: `planning investment-opportunity-comparison build`, `planning investment-opportunity-comparison demo`.
- Campi principali: `capital_amount`, `horizon_years`, `primary`, `benchmark`, `assumptions`, `provenance`, `data_gaps`.
- `primary` richiede esattamente gli scenari `base`, `upside` e `adverse`; ogni scenario dichiara `annual_equity_cash_flow`, `net_exit_value`, stress espliciti, ore/costo del proprietario e `household_constraints`.
- `benchmark` e' opzionale: se manca, il build resta utile ma produce `missing_benchmark` e non calcola `opportunity_cost`. Se e' presente, usa lo stesso capitale e orizzonte di `primary`.
- `household_constraints` include riserva liquida, liquidita' dopo l'impegno, limite e concentrazione prevista, impatto sul cash flow di work-exit e reversibilita'. I valori ignoti devono restare gap espliciti.
- Nota: il file confronta soltanto dati gia' dichiarati da adapter e financing; non inserire rendimenti di mercato, imposte, tassi, valori di uscita o soglie household non supportati. L'output non e' un ranking o una raccomandazione.

## `protection-gap/v1`

- Default: `../family-office-workspace/planning/protection-gap.json`.
- Esempio: `examples/protection-gap-sample.json`.
- Comandi: `planning protection build`, `planning protection demo`.
- Campi: `household_id`, `as_of_date`, `base_currency`, `family_needs`, `policies`, `data_gaps`.
- Ogni bisogno familiare dichiara `need_id`, `event_type`, `required_capital`, persone coperte e `provenance`.
- Ogni polizza dichiara `policy_id`, `policy_type`, contraente, assicurati, beneficiari, eventi coperti, capitale assicurato, premio, riscatto e `provenance`.
- Le polizze investimento sono tracciate per valore di riscatto ma non contano come copertura rischio.
- Nota: beneficiari, capitali, fabbisogni, premi e riscatti sono input espliciti. Il motore non calcola consulenza assicurativa, sanitaria, attuariale, legale, fiscale, underwriting, successione o raccomandazioni.

## `estate-plan/v2`

- Default: `../family-office-workspace/planning/estate-plan.json`.
- Esempio: `examples/estate-plan-sample.json`.
- Comandi: `planning estate build`, `planning estate demo`.
- Campi: `household_id`, `as_of_date`, `base_currency`, `decedent_person_id`, `family`, `assets`, `prior_donations`, `insurance_policies`, `tax_liquidity`, `scenarios`, `data_gaps`.
- `family` dichiara coniuge e figli; il rule pack V2 copre solo casi semplici con coniuge e/o figli.
- Ogni asset richiede valore, quota di titolarita', giurisdizione, valuta e `provenance`; asset esteri o senza quota producono gap.
- Ogni donazione pregressa richiede beneficiario, relazione, importo, flag `include_in_notional_mass` e `provenance`.
- Ogni polizza deve dichiarare beneficiari e `estate_treatment`; se il trattamento successorio e' ignoto resta gap.
- Ogni scenario assegna quote degli asset ai beneficiari. Quote incomplete, asset non allocati e relazioni fiscali non coperte restano gap.
- Nota: il motore segnala conflitti e gap. Non calcola collazione, riduzione, base catastale, successione estera, trust, contenzioso o raccomandazioni.

## `wealth-strategy-input/v1`

- Default: `../family-office-workspace/planning/wealth-strategy-input.json`.
- Esempio: `examples/wealth-strategy-input-sample.json`.
- Comandi: `planning wealth-strategy build`, `planning wealth-strategy demo`.
- Campi: `household_id`, `as_of_date`, `base_currency`, `comparison_weights`, `packages`, `incompatibilities`, `data_gaps`.
- Ogni pacchetto dichiara `package_id`, componenti, punteggi espliciti, azioni 90/180 giorni, costi, dipendenze, reversibilita', controlli, rischi e scenari avversi.
- Ogni componente usa `source_key` e un selettore verso uno snapshot V4 esistente; se la sorgente manca, e' parziale/bloccata o il selettore non trova l'opzione dichiarata, il builder produce gap.
- `incompatibilities` serve a dichiarare combinazioni non ammesse di componenti nello stesso pacchetto.
- Nota: il ranking usa pesi e punteggi dichiarati. Il motore non inventa pacchetti, non ottimizza in modo opaco e non calcola nuove imposte, pensioni, rendimenti o raccomandazioni.

## Scenario decisionale

### `decision-scenario-v2.json`

- Default: `../family-office-workspace/scenarios/decision-scenario-v2.json`.
- Esempio: `examples/decision-scenario-input-sample.json`.
- Comando: `scenarios compose-v2`.
- Campi: riferimenti scenario, summary, assunzioni esplicite, obiettivi e data gaps.

### `decision-outcome.json`

- Default: `../family-office-workspace/scenarios/decision-outcome.json`.
- Esempio: `examples/decision-outcome-input-sample.json`.
- Comando: `scenarios evaluate`.
- Campi: evaluator, parametri, seed e metriche richieste.

### `sensitivity-analysis.json`

- Default: `../family-office-workspace/scenarios/sensitivity-analysis.json`.
- Esempio: `examples/sensitivity-analysis-input-sample.json`.
- Comando: `scenarios sensitivity`.
- Campi: variabili perturbate, stress combinati, metrica di impatto e opzionale `outcome_evaluation`.

### `decision-score.json`

- Default: `../family-office-workspace/scenarios/decision-score.json`.
- Esempio: `examples/decision-score-input-sample.json`.
- Comando: `scenarios score`.
- Campi: alternative, `outcome_ref`, pesi, mapping da metriche policy a metriche outcome.

### `decision-dossier.json`

- Default: `../family-office-workspace/scenarios/decision-dossier.json`.
- Esempio: `examples/decision-dossier-input-sample.json`.
- Comando: `scenarios dossier`.
- Campi: titolo dossier, sezioni, alternative incluse, note di revisione e limiti.

## `work-exit-feasibility-input/v1`

- Default: `../family-office-workspace/planning/work-exit-feasibility.json`.
- Esempio: `examples/work-exit-feasibility-sample.json`.
- Comandi: `planning work-exit build`, `planning work-exit demo`.
- Campi chiave: `as_of_date`, `candidate_dates` o `candidate_grid`, `sustainability_constraints`, `adults`.
- Ogni adulto deve dichiarare `person_id`, `role`, `date_of_birth` e, se stimabile, `inps_contributory_estimate` con montante storico o basi annue e contributi futuri espliciti.
- La pensione del coniuge deve essere presente come stream separato o come stima deterministica; se manca, il build produce un data gap bloccante.
- Le date future usano il rule pack INPS proiettivo di pianificazione, non una previsione ufficiale di legge futura.
