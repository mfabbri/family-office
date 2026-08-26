# API

## Payroll Ingestion

Modulo:

```text
family_office_engine.ingestion.payroll
```

Funzioni principali:

- `import_payroll(input_dir, output_path)`: legge PDF payroll e scrive uno snapshot `payroll/v1`.
- `diagnose_payroll_input(input_dir)`: legge gli stessi input e restituisce diagnostica `payroll-diagnostics/v1`.
- `parse_payroll_text(text, filename)`: parser deterministico del testo estratto dal PDF.

`payroll/v1` registra solo valori presenti nel cedolino: periodo, datore di lavoro, netto pagato, imponibile IRPEF, IRPEF trattenuta e trattenute riconosciute. Non calcola imposte, contributi o netto da lordo.

`payroll-diagnostics/v1` espone path input, conteggio documenti, conteggio record, conteggio gap, stato per documento e prossime azioni operative. La diagnostica e' pensata per capire perche' un import risulta `not_extracted` o `partial_extracted` senza ispezionare importi personali.

## Tax Calculation

Modulo:

```text
family_office_engine.services.tax_calculation
```

Funzioni principali:

- `load_rule_pack(rule_pack_path)`: carica e valida un rule pack JSON `tax-rule-pack/v1`.
- `calculate_tax(rule_pack_path, tax_year, jurisdiction, taxable_income, output_path)`: applica scaglioni progressivi e scrive `tax-calculation/v1`.

Il runtime usa `Decimal`, non float. Ogni tranche applicata cita `rule_id`, `valid_from` e `valid_to`. Se manca una regola applicabile per anno o giurisdizione, lo snapshot viene scritto con `status: blocked_missing_rule` e `data_gaps`.

Il rule pack `family-office-rules/italy/2026/irpef-national.json` calcola solo l'IRPEF nazionale lorda 2026 su imponibile gia' determinato. Lo snapshot riporta anche `source_refs` e `limitations` del rule pack. Detrazioni, addizionali, crediti, acconti e dichiarazione completa restano fuori perimetro.

Il rule pack sintetico in `family-office-rules/tests/fixtures` resta una fixture tecnica e non e' una regola fiscale reale.

## RITA Options

Modulo:

```text
family_office_engine.services.rita_options
```

Funzioni principali:

- `load_rule_pack(rule_pack_path)`: carica e valida un rule pack `rita-rule-pack/v1` JSON compatibile con YAML.
- `optimize_rita_options(rule_pack_path, output_path, ...)`: verifica i requisiti minimi RITA da input espliciti e scrive `rita-options/v1`.

`rita-options/v1` espone input, rule pack, eligibility, options e data gaps. In V1 l'unica opzione calcolata e' un prelievo lordo lineare: montante complementare diviso per durata in mesi. Il servizio non calcola pensione pubblica, tassazione, rendimenti, costi o vincoli specifici del fondo.

Stati principali:

- `complete`: requisiti minimi verificati e opzione prodotta;
- `blocked_missing_inputs`: input essenziali o importi/durata mancanti;
- `not_eligible`: requisiti minimi non soddisfatti.

## Estate Baseline

Modulo:

```text
family_office_engine.services.estate_baseline
```

Funzioni principali:

- `load_rule_pack(rule_pack_path)`: carica e valida un rule pack `estate-rule-pack/v1`.
- `build_estate_baseline(net_worth_snapshot_path, rule_pack_path, output_path, ...)`: costruisce `estate-baseline/v1` da patrimonio osservato e input familiari espliciti.

`estate-baseline/v1` espone componenti patrimoniali, masse osservate, massa successoria nota, quote teoriche, riepilogo liquidita' e data gaps. La massa successoria viene calcolata solo per componenti con `ownership.share` esplicito; altrimenti il componente resta osservato ma genera `missing_ownership`.

Il rule pack `family-office-rules/succession/italy-current.json` copre solo successione legittima semplice con coniuge e/o figli. Polizze, fondi pensione, asset esteri, immobili, testamento, donazioni pregresse, debiti, imposte e verifica notarile restano fuori perimetro o gap espliciti.

## Household Facts

Modulo:

```text
family_office_engine.services.household_facts
```

Funzioni principali:

- `validate_household_facts(data)`: valida un documento `household-facts/v1` e restituisce gap non bloccanti.
- `import_household_facts(input_path, output_path)`: valida e normalizza i facts in uno snapshot `household-facts/v1`.

Il contratto rappresenta persone, relazioni, residenze fiscali, ruoli economici e date rilevanti. Non inventa persone o relazioni mancanti: riferimenti a ID inesistenti sono errori, mentre informazioni incomplete come data/anno di nascita o residenza fiscale mancante diventano `data_gaps`.

Schema e fixture:

- `schemas/household-facts.schema.json`
- `examples/household-facts-sample.json`

## Ownership Beneficiary Graph

Modulo:

```text
family_office_engine.services.ownership_graph
```

Funzioni principali:

- `validate_ownership_graph(data, household_snapshot=None)`: valida un documento `ownership-beneficiary-graph/v1` e restituisce gap non bloccanti.
- `import_ownership_graph(input_path, output_path, household_snapshot_path=None)`: valida e normalizza il grafo in uno snapshot `ownership-beneficiary-graph/v1`.

Il contratto collega asset e debiti a persone tramite quote esplicite, nuda proprieta', usufrutto, debitori, garanti e beneficiari. Quando e' disponibile uno snapshot `household-facts/v1`, i riferimenti a persone inesistenti sono errori. Ownership o beneficiari sconosciuti restano `data_gaps`; il servizio non attribuisce quote per inferenza.

Schema e fixture:

- `schemas/ownership-beneficiary-graph.schema.json`
- `examples/ownership-beneficiary-graph-sample.json`

## Asset Availability

Modulo:

```text
family_office_engine.services.asset_availability
```

Funzioni principali:

- `validate_asset_availability(data, ownership_snapshot=None)`: valida un documento `asset-availability/v1` e restituisce gap non bloccanti.
- `import_asset_availability(input_path, output_path, ownership_snapshot_path=None)`: valida e normalizza la classificazione asset in uno snapshot `asset-availability/v1`.

Il contratto classifica gli asset per classe, rischio, valuta, giurisdizione, liquidita', vincoli, trattamento fiscale dichiarativo e prima data di disponibilita'. Quando e' disponibile uno snapshot `ownership-beneficiary-graph/v1`, i riferimenti ad asset inesistenti sono errori. Campi mancanti o dichiarati `unknown` diventano `data_gaps`; il servizio non inferisce liquidita', rischio, tassazione o vincoli.

Schema e fixture:

- `schemas/asset-availability.schema.json`
- `examples/asset-availability-sample.json`

## Timeline Events

Modulo:

```text
family_office_engine.services.timeline_events
```

Funzioni principali:

- `validate_timeline_events(data, household_snapshot=None, asset_availability_snapshot=None, policy=None)`: valida un documento `timeline-events/v1` e restituisce gap non bloccanti e occorrenze ordinate.
- `import_timeline_events(input_path, output_path, policy_path=None, household_snapshot_path=None, asset_availability_snapshot_path=None)`: valida e normalizza gli eventi in uno snapshot `timeline-events/v1`.

Il contratto rappresenta eventi puntuali, periodi e ricorrenze. La policy `timeline-overlap-policy/v1` definisce priorita' di ordinamento e conflitti tecnici, senza interpretare norme fiscali, previdenziali o legali. Quando sono disponibili snapshot household e asset availability, i riferimenti a persone o asset inesistenti sono errori. Date mancanti o ricorrenze incomplete restano `data_gaps`; il servizio non inventa date o importi.

Schema, fixture e policy:

- `schemas/timeline-events.schema.json`
- `examples/timeline-events-sample.json`
- `../family-office-rules/timeline/default-overlap-policy.json`

## Spanish Contribution History

Modulo:

```text
family_office_engine.ingestion.spanish_contribution_history
```

Funzioni principali:

- `import_spanish_contribution_history(input_dir, output_path)`: legge documenti spagnoli classificati e scrive uno snapshot `spanish-contribution-history/v1`.
- `parse_spanish_contribution_text(text, filename)`: parser deterministico per testi estratti da Vida Laboral, Informe de bases de cotizacion e nominas.
- `parse_spanish_contribution_csv(text, filename)`: parser deterministico per CSV sintetici o export tabellari di basi mensili.

`spanish-contribution-history/v1` normalizza periodi contributivi da Vida Laboral e basi mensili documentate da fonti ufficiali o nominas. L'Informe de bases e' supportato anche nel layout tabellare annuale con mesi in colonne. Le basi ufficiali sono marcate con `confidence: high`; le nominas sono fonti integrative con `confidence: medium`. Documenti duplicati, non leggibili, mesi coperti da un periodo ma senza base e formati non supportati restano `data_gaps`.

Il modulo non stima pensioni, diritti, base reguladora, coordinamento UE, imposte o riconciliazione finale tra fonti. La gerarchia completa delle evidenze appartiene a `spanish-contribution-reconciliation/v1`.

Fixture:

- `examples/spanish-contribution-history-sample.json`

## Spanish Contribution Reconciliation

Modulo:

```text
family_office_engine.services.spanish_contribution_reconciliation
```

Funzione principale:

- `reconcile_spanish_contributions(contribution_history_snapshot_path, output_path)`: legge `spanish-contribution-history/v1` e scrive `spanish-contribution-reconciliation/v1`.

`spanish-contribution-reconciliation/v1` costruisce una griglia mensile che confronta copertura Vida Laboral, basi ufficiali e basi da nomina. Le basi ufficiali prevalgono sempre sulle nominas; le nominas possono integrare un mese senza base ufficiale, ma in quel caso il mese resta gap `payroll_base_without_official_base` e non viene marcato come utilizzabile dall'estimatore. Differenze tra base ufficiale e nomina, basi multiple nello stesso mese, mesi coperti senza base e basi senza periodo Vida Laboral sono esposti come `anomalies` o `data_gaps`.

Il servizio non calcola pensione, diritto, base reguladora, coordinamento UE o fiscalita'. Le somme mensili di piu' basi ufficiali sono solo aggregazioni documentali per rendere visibile la contribuzione del mese.

Fixture:

- `examples/spanish-contribution-reconciliation-sample.json`

## Spanish Pension Rules

Modulo:

```text
family_office_engine.services.spanish_pension_rules
```

Funzioni principali:

- `load_rule_pack(rule_pack_path)`: carica e valida un rule pack JSON `spanish-statutory-pension-rule-pack/v1`.
- `ordinary_retirement_age(rule_pack, year, contribution_months)`: restituisce eta' ordinaria applicabile per anno e mesi contributivi.
- `base_reguladora_parameters(rule_pack, year)`: restituisce i parametri transitori della base reguladora per l'anno.
- `accrued_pension_percentage(rule_pack, year, contribution_months)`: calcola la percentuale maturata della base reguladora in base a mesi contributivi e anno.

Il rule pack `../family-office-rules/spain/statutory-retirement-general.json` e' un baseline tecnico, basato su fonte BOE, per abilitare il futuro estimatore V3.5c. Non calcola pensione, diritto finale, importi, coordinamento UE o fiscalita'. Il loader rifiuta rule pack senza fonti ufficiali, limitazioni esplicite, requisiti minimi, eta' ordinaria, parametri della base reguladora e progressione percentuale completa.

## Spanish Statutory Pension

Modulo:

```text
family_office_engine.services.spanish_statutory_pension
```

Funzione principale:

- `estimate_spanish_statutory_pension(reconciliation_snapshot_path, rule_pack_path, output_path, retirement_year, retirement_month=12, scenario="ordinary")`: legge `spanish-contribution-reconciliation/v1`, applica `spanish-statutory-pension-rule-pack/v1` e scrive `spanish-statutory-pension/v1`.

`spanish-statutory-pension/v1` produce una stima interna lorda della pensione ordinaria spagnola: verifica requisiti contributivi codificati, seleziona le migliori basi ufficiali nella finestra base reguladora, applica divisor, percentuale maturata e periodicita' annua versionata. Se mancano basi ufficiali sufficienti o requisiti minimi, lo stato e' `blocked_missing_inputs` e non viene prodotto alcun importo.

Il servizio non calcola pensione ufficiale, anticipo, differimento, caps, minimi, supplementi, rivalutazione basi, integrazione lagune, fiscalita' o coordinamento UE.

## EU Pension Coordination Italy-Spain

Modulo:

```text
family_office_engine.services.eu_pension_coordination
```

Funzioni principali:

- `load_rule_pack(rule_pack_path)`: carica e valida `eu-pension-coordination-rule-pack/v1`.
- `coordinate_it_es_pensions(inps_snapshot_path, spanish_pension_snapshot_path, rule_pack_path, output_path, italian_contribution_months=None)`: legge `inps-pension/v1` e `spanish-statutory-pension/v1`, applica il metodo UE e scrive `eu-pension-coordination-it-es/v1`.

`eu-pension-coordination-it-es/v1` mantiene separate le prestazioni nazionali Italia e Spagna, registra i periodi normalizzati disponibili, espone i rapporti di periodo quando calcolabili e dichiara il pro-rata come non calcolabile finche' manca un importo teorico nazionale. La totalizzazione e' rappresentata solo come criterio di diritto/diagnostica: i contributi non vengono trasferiti o fusi.

Il servizio non calcola pensione INPS da regole normative, non produce P1 ufficiale, non calcola fiscalita', netto, cambio valuta, domande amministrative o coordinamento di pensioni complementari.

## Pension Income

Modulo:

```text
family_office_engine.services.pension_income
```

Funzione principale:

- `compose_pension_income(inps_snapshot_path, spanish_pension_snapshot_path, output_path, rita_options_snapshot_path=None, eu_coordination_snapshot_path=None, include_rita=True)`: legge snapshot pensionistici disponibili e scrive `pension-income/v1`.

`pension-income/v1` compone flussi separati per fonte: INPS come proiezione documentale, pensione pubblica spagnola come stima interna, RITA come opzione ponte finita. Ogni flusso mantiene paese, payer, tipo prestazione, decorrenza, periodicita', importi lordi, stato del netto, confidence e gap.

Il composer non calcola pensioni, fiscalita', netto, cambi valuta o annualizzazioni mancanti. Il riepilogo `gross_annual_recurring_total` somma solo importi lordi annuali ricorrenti, espliciti e in EUR; flussi mensili senza annuale documentato e flussi RITA finiti restano separati ed esclusi dal totale.

Il simulatore `retirement-simulation/v1` puo' ricevere opzionalmente `pension-income/v1` e usa solo `summary.gross_annual_recurring_total` come offset lordo annuo dei prelievi post-pensionamento. Se lo snapshot non viene passato, il comportamento resta invariato.

## Lifecycle Expenses

Modulo:

```text
family_office_engine.services.lifecycle_expenses
```

Funzione principale:

- `build_lifecycle_expenses(input_path, output_path, household_snapshot_path=None, timeline_snapshot_path=None)`: legge un piano spese esplicito e scrive `lifecycle-expenses/v1`.

`lifecycle-expenses/v1` produce un cashflow annuo di spesa per categoria, fase di vita, owner household/persona, periodo e provenance. Le spese ricorrenti usano `start_year`, `end_year`, importo annuo e inflazione annua esplicita; le spese una tantum possono usare un anno dichiarato o un evento di `timeline-events/v1`.

Il servizio usa solo importi espliciti in EUR. Non stima spese mancanti, costo sanitario, fiscalita', rendimenti, cambio valuta, inflazione implicita, scoring o raccomandazioni.

## Decision Scenario V2

Modulo:

```text
family_office_engine.services.decision_scenario
```

Funzione principale:

- `compose_decision_scenario(scenario_input_path, output_path, household_snapshot_path, ownership_snapshot_path, asset_availability_snapshot_path, timeline_snapshot_path, pension_income_snapshot_path=None, lifecycle_expenses_snapshot_path=None)`: compone `decision-scenario/v2`.

`decision-scenario/v2` e' un artefatto deterministico e rieseguibile che combina riferimenti e summary da household facts, ownership graph, asset availability, timeline, pension income, lifecycle expenses e assunzioni scenario esplicite. Produce un hash SHA-256 del contenuto canonico per verificare riproducibilita'.

Il composer separa facts, assunzioni, obiettivi, constraints e data gaps. Non esegue simulazioni, non calcola rendimenti, imposte, pensioni, scoring, stress test o raccomandazioni.

## Decision Outcome

Modulo:

```text
family_office_engine.services.decision_outcome
```

Funzione principale:

- `build_decision_outcome(decision_scenario_snapshot_path, outcome_input_path, output_path)`: esegue un evaluator deterministico registrato sopra `decision-scenario/v2` e scrive `decision-outcome/v1`.
- `evaluate_decision_outcome(scenario, outcome_input, decision_scenario_path=None, outcome_input_path=None)`: esegue lo stesso evaluator in memoria; e' usata dalla sensitivity outcome-linked per evitare file temporanei.

Il primo evaluator supportato e' `retirement-monte-carlo/v1`. Legge dallo scenario input espliciti sotto `assumptions.personal`, `assumptions.portfolio`, `assumptions.cashflow` e `assumptions.market`, li adatta in memoria al simulatore Monte Carlo V1 esistente e produce metriche realmente calcolate. Ogni metrica contiene scenario hash, evaluator/versione e seed nella provenance.

Scenario incompatibile o input mancanti producono `blocked_missing_inputs` e gap espliciti senza metriche. Schema sorgente, evaluator o parametri non supportati generano `DecisionOutcomeError`. Il servizio non legge sorgenti implicite e non calcola imposte, diritti pensionistici o raccomandazioni.

Fixture:

- `examples/decision-outcome-input-sample.json`
- `examples/decision-scenario-input-sample.json`

## Sensitivity Analysis

Modulo:

```text
family_office_engine.services.sensitivity_analysis
```

Funzione principale:

- `build_sensitivity_analysis(decision_scenario_snapshot_path, sensitivity_input_path, output_path)`: legge `decision-scenario/v2` e una specifica esplicita di sensitivities, poi scrive `sensitivity-analysis/v1`.

`sensitivity-analysis/v1` applica perturbazioni deterministiche alle sole assunzioni dello scenario. Le sensitivities supportano `absolute`, `relative` e `set`; ogni path deve partire da `assumptions`.

Se l'input contiene `outcome_evaluation`, il servizio usa la configurazione `DecisionOutcomeInput` incorporata per rieseguire lo stesso evaluator sulla baseline, su ogni variante valida e su ogni stress combinato. L'output include `baseline_outcome`, outcome e `metric_deltas` per caso, provenance degli hash outcome e un `tornado_data` ordinato per impatto assoluto sulla `impact_metric_id` dichiarata. Senza `outcome_evaluation` il formato V3.8 legacy resta supportato e il tornado usa la magnitudine della perturbazione.

Il primo evaluator supportato resta `retirement-monte-carlo/v1`. Baseline o varianti bloccate producono gap espliciti e nessun delta inventato. Il servizio non calcola fiscalita', diritti pensionistici, scoring, ranking decisionale o raccomandazioni.

Fixture:

- `examples/sensitivity-analysis-input-sample.json`

## Decision Score

Modulo:

```text
family_office_engine.services.decision_score
```

Funzione principale:

- `build_decision_score(decision_scenario_snapshot_path, sensitivity_analysis_snapshot_path, scoring_input_path, policy_path, output_path)`: legge scenario, sensitivity, input di scoring e policy pack, poi scrive `decision-score/v1`.

`decision-score/v1` normalizza metriche risolte da outcome deterministici usando il rule pack tecnico `decision-score-policy/v1`, applica pesi dichiarati nell'input e produce punteggi separati per metrica, totale pesato e ranking stabile. Ogni alternativa deve dichiarare `outcome_ref` verso baseline, sensitivity o stress di `sensitivity-analysis/v1`; ogni metrica pesata deve mappare esplicitamente una metrica policy a un `outcome_metric_id`. Le metriche supportate dal policy pack includono sostenibilita', patrimonio finale, liquidita', fiscal drag, rischio, complessita', reversibilita' e compliance; valori e pesi non sono inventati dal servizio.

Metriche manuali prive di outcome lineage, riferimenti outcome mancanti e unita' incompatibili diventano gap bloccanti e non entrano in un ranking raccomandabile. Il servizio registra anche gap per metriche mancanti, metriche non ammesse, input sorgenti parziali o policy non valida. Non calcola imposte, rendimenti, pensioni, metriche sottostanti, ottimizzazioni o raccomandazioni.

Fixture:

- `examples/decision-score-input-sample.json`

## Decision Dossier

Modulo:

```text
family_office_engine.services.decision_dossier
```

Funzione principale:

- `build_decision_dossier(decision_scenario_snapshot_path, sensitivity_analysis_snapshot_path, decision_score_snapshot_path, dossier_input_path, output_path, markdown_output_path)`: legge scenario, sensitivity, score e configurazione dossier, poi scrive `decision-dossier/v1` e un report Markdown.

`decision-dossier/v1` raccoglie facts summary, assunzioni, alternative, ranking, motivi del ranking, rischi da sensitivity, gap, limiti, lineage summary e azioni successive. La raccomandazione deterministica e' prodotta solo se lo score e' completo, il ranking esiste, il lineage delle metriche classificate e' completo e non sono presenti gap bloccanti.

Il servizio non calcola imposte, rendimenti, pensioni, nuove metriche, ottimizzazioni o raccomandazioni AI. Il dossier e' sempre soggetto a revisione umana.

Fixture:

- `examples/decision-dossier-input-sample.json`

## Planning Goals

Modulo:

```text
family_office_engine.services.planning_goals
```

Funzioni principali:

- `validate_planning_goals(data, timeline_snapshot=None)`: valida un documento `planning-goals/v1` e restituisce gap non bloccanti.
- `import_planning_goals(input_path, output_path, timeline_snapshot_path=None)`: valida e normalizza obiettivi e vincoli in uno snapshot `planning-goals/v1`.

`planning-goals/v1` rappresenta obiettivi dichiarati, priorita', soglie, orizzonte, profilo di rischio, politica di liquidita' e vincoli legali/familiari/temporali. I vincoli possono riferirsi a obiettivi e, se disponibile uno snapshot `timeline-events/v1`, a eventi della timeline.

Il servizio rigetta ID duplicati, priorita' non positive o duplicate, soglie incoerenti, orizzonti invalidi e riferimenti a obiettivi inesistenti. Campi opzionali mancanti, profili `unknown`, vincoli senza soglia e riferimenti timeline non verificabili diventano `data_gaps`. Non calcola rendimenti, imposte, ottimizzazioni, scoring, trade-off o raccomandazioni.

Fixture:

- `examples/planning-goals-sample.json`

## Liquidity Plan

Modulo:

```text
family_office_engine.services.liquidity_plan
```

Funzione principale:

- `build_liquidity_plan(input_path, output_path, net_worth_snapshot_path=None, asset_availability_snapshot_path=None, planning_goals_snapshot_path=None)`: legge input esplicito e snapshot disponibili, poi scrive `liquidity-plan/v1`.

`liquidity-plan/v1` assegna asset valorizzati a bucket `emergency_reserve`, `short_term`, `medium_term`, `long_term` e `restricted`. Il target di riserva usa `monthly_expenses` e i mesi minimi dichiarati in `planning-goals/v1`, con fallback all'input se lo snapshot goals non e' disponibile.

Il piano segnala shortfall di riserva, asset bloccati per spese correnti, asset in valuta diversa dalla valuta base, classificazioni mancanti e concentrazione oltre soglia. Asset illiquidi, locked, co-owned, gravati da lien, soggetti a policy terms, in valuta estera o senza classificazione restano fuori dalla riserva disponibile. Non calcola rendimenti, imposte, cambi valuta, ottimizzazioni, scoring o raccomandazioni.

Fixture:

- `examples/liquidity-plan-input-sample.json`
- `examples/liquidity-plan-net-worth-sample.json`

## Decumulation Strategy

Modulo:

```text
family_office_engine.services.decumulation_strategy
```

Funzione principale:

- `build_decumulation_strategy(input_path, output_path, net_worth_snapshot_path=None, liquidity_plan_snapshot_path=None, pension_income_snapshot_path=None, rita_options_snapshot_path=None)`: confronta policy di decumulo esplicite e scrive `decumulation-strategy/v1`.

`decumulation-strategy/v1` usa asset valorizzati, bucket di liquidita', pension income e opzioni RITA disponibili per simulare cashflow annui per policy. Ogni policy dichiara eta' pensionamento, eta' fine orizzonte, fabbisogno netto annuo, cash buffer target, ordine prelievi, sequenza rendimenti, tassi espliciti e scelta RITA si'/no.

Le metriche includono saldo finale, eta' di depletion, anni e importo di shortfall, spesa netta coperta, prelievi lordi, pensione netta usata e RITA netta usata. I tassi netti sono solo quelli dichiarati nell'input: il servizio non calcola fiscalita' normativa, rendimenti attesi, cambi valuta, ottimizzazioni o raccomandazioni.

Fixture:

- `examples/decumulation-policy-set-sample.json`
- `examples/decumulation-net-worth-sample.json`
- `examples/decumulation-liquidity-plan-sample.json`
- `examples/decumulation-pension-income-sample.json`
- `examples/decumulation-rita-options-sample.json`

## Pension Contribution Options

Modulo:

```text
family_office_engine.services.pension_contribution_options
```

Funzione principale:

- `build_pension_contribution_options(input_path, rule_pack_path, output_path)`: confronta opzioni esplicite di contribuzione a previdenza complementare e scrive `pension-contribution-options/v1`.

`pension-contribution-options/v1` usa un rule pack versionato per limiti di deducibilita' e input dichiarati per aliquota marginale, contributi gia' dedotti, opzioni future, liquidita' e costo opportunita'. Ogni opzione separa contributo lavoratore, contributo datore e TFR, indicando importi deducibili/non deducibili, beneficio fiscale stimato, liquidita' bloccata, costo opportunita', vincoli e gap.

Il servizio non calcola IRPEF completa, detrazioni, addizionali, rendimenti, matching contrattuale non dichiarato o raccomandazioni.

Fixture:

- `examples/pension-contribution-input-sample.json`

## Tax-aware Portfolio

Modulo:

```text
family_office_engine.services.tax_aware_portfolio
```

Funzione principale:

- `build_tax_aware_portfolio(input_path, rule_pack_path, output_path)`: confronta opzioni esplicite di portafoglio e scrive `tax-aware-portfolio/v1`.

`tax-aware-portfolio/v1` usa un rule pack versionato per aliquote finanziarie, bollo e IVAFE. Ogni opzione dichiara regime fiscale, minusvalenze compensabili e posizioni con valore, categoria fiscale, luogo di detenzione, rendimento lordo atteso esplicito, costi e turnover. Il servizio calcola rendimento lordo, costi, imponibile realizzato, offset minusvalenze, imposte, bollo/IVAFE, fiscal drag, stima della fiscalita' differita e rendimento netto.

Regimi incompatibili con luogo di detenzione e categorie agevolate non documentate diventano vincoli o data gaps. Il servizio non calcola rendimenti attesi, rischio, dichiarazione completa, fiscalita' estera, PIR, cripto-attivita' o raccomandazioni.

Fixture:

- `examples/tax-aware-portfolio-input-sample.json`

## IT-ES Pension Tax Classification

Modulo:

```text
family_office_engine.services.it_es_pension_tax_classification
```

Funzione principale:

- `classify_it_es_pension_tax(input_path, pension_income_snapshot_path, rule_pack_path, output_path)`: classifica stream pensionistici secondo la Convenzione Italia-Spagna e scrive `it-es-pension-tax-classification/v1`.

`it-es-pension-tax-classification/v1` legge `pension-income/v1` e un input esplicito con residenza fiscale, nazionalita' e fatti di classificazione per stream. Il servizio distingue pensioni da precedente impiego privato, pensioni da servizio pubblico e l'eccezione per beneficiario residente/nazionale dello Stato di residenza. Ogni stream espone articolo convenzionale candidato, Stato con potesta' impositiva, ritenuta attesa in termini qualitativi, documenti richiesti, warning, confidence e data gaps.

Il servizio non calcola ritenute effettive, IRPEF, IRPF spagnola, crediti per imposte estere, netto pensionistico, rimborsi o dichiarazione completa.

Fixture:

- `examples/it-es-pension-tax-classification-input-sample.json`
- `examples/it-es-pension-income-sample.json`

## Spanish Pension Net IT Resident

Modulo:

```text
family_office_engine.services.spanish_pension_net_it_resident
```

Funzione principale:

- `build_spanish_pension_net_it_resident(input_path, pension_income_snapshot_path, classification_snapshot_path, rule_pack_path, irpef_rule_pack_path, output_path)`: calcola un ponte lordo-netto per pensioni spagnole di residente fiscale italiano e scrive `spanish-pension-net-it-resident/v1`.

`spanish-pension-net-it-resident/v1` legge `pension-income/v1`, `it-es-pension-tax-classification/v1`, input fiscale esplicito e rule pack IRPEF nazionale. Per pensioni imponibili in Italia calcola IRPEF nazionale incrementale su altri redditi imponibili dichiarati piu' pensione, eventuale credito art. 165 su imposte estere definitive e netto annuo. Per pensioni con potesta' impositiva spagnola esclusiva non applica IRPEF italiana e usa solo la ritenuta spagnola dichiarata.

Il servizio non calcola detrazioni, addizionali, acconti, rimborsi, imposte spagnole da aliquote spagnole, regime art. 24-ter o dichiarazione completa.

Fixture:

- `examples/spanish-pension-net-it-resident-input-sample.json`
- `examples/spanish-pension-net-it-es-classification-sample.json`

## IT-ES Foreign Assets

Modulo:

```text
family_office_engine.services.it_es_foreign_assets
```

Funzione principale:

- `build_it_es_foreign_assets(input_path, rule_pack_path, output_path)`: classifica attivita' spagnole detenute da residente fiscale italiano e scrive `it-es-foreign-assets/v1`.

`it-es-foreign-assets/v1` legge input esplicito `it-es-foreign-assets-input/v1` e rule pack `it-es.foreign-asset-monitoring.2026.v2`. Il servizio copre conti/depositi spagnoli, prodotti finanziari, piani pensionistici esteri con classificazione strutturata e immobili esteri; produce obbligo RW, motivazione, categoria di monitoraggio, documenti richiesti, basi dichiarate, IVAFE/IVIE calcolate da valori, quote, giorni o mesi dichiarati, tax events, warning e data gaps.

Intermediari italiani o sostituti d'imposta sono trattati come esenzione/area di review solo quando l'input documenta la condizione. Attivita' non classificate, valori mancanti, piano pensionistico non qualificato e anno non coperto diventano gap. Il servizio non prepara la dichiarazione, non assegna ogni codice RW, non calcola redditi esteri, crediti esteri, fiscalita' spagnola, cripto-attivita' o raccomandazioni.

Fixture:

- `examples/it-es-foreign-assets-input-sample.json`

## Cross-Border IT-ES Dossier

Modulo:

```text
family_office_engine.services.cross_border_it_es_dossier
```

Funzione principale:

- `build_cross_border_it_es_dossier(output_path, pension_scenario_snapshot_path=None, pension_income_snapshot_path=None, pension_tax_classification_snapshot_path=None, spanish_pension_net_snapshot_path=None, eu_pension_pro_rata_snapshot_path=None, foreign_assets_snapshot_path=None)`: compone snapshot IT-ES deterministici e scrive `cross-border-it-es/v1`.

`cross-border-it-es/v1` aggrega scenario pensionistico esplicito, pension income, classificazione fiscale pensione, netto pensione spagnola, quota pro-rata UE e monitoraggio asset esteri senza ricalcolare imposte, pensioni o valori patrimoniali. Il dossier separa assunzioni future, flussi pensionistici, diritti previdenziali, tassazione del reddito pensionistico, monitoraggio patrimoniale, tax events, documenti richiesti, rischi, azioni operative, provenance, rule pack/source refs/limitations disponibili e hash delle fonti.

Snapshot mancanti o bloccati diventano gap o `blocked_source`; il dossier mantiene comunque le sezioni disponibili. Il servizio non prepara dichiarazioni, non calcola nuovi crediti d'imposta, non stima prestazioni, non ottimizza strategie e non produce raccomandazioni automatiche.

Fixture:

- `examples/cross-border-spanish-pension-net-sample.json`
- `examples/cross-border-it-es-eu-pension-pro-rata-sample.json`
- `examples/cross-border-it-es-foreign-assets-sample.json`

## Pension Scenario

Modulo:

```text
family_office_engine.services.pension_scenario
```

Funzione principale:

- `build_pension_scenario(input_path, output_path)`: valida assunzioni pensionistiche Italia-Spagna esplicite e scrive `pension-scenario/v1`.

`pension-scenario/v1` registra scenario selezionato, alternative, data di conferma, pensionamento, residenza fiscale iniziale, trasferimenti post-pensionamento, contributi futuri IT/ES e provenance. Le fixture sintetiche sono ammesse solo per household sintetici; per household personali il servizio le rifiuta.

Il servizio non calcola pensioni, basi contributive, imposte, netto, diritto UE, pro-rata o raccomandazioni.

Fixture:

- `examples/pension-scenario-sample.json`
- `examples/pension-scenario-snapshot-sample.json`

## Real Estate Plan

Modulo:

```text
family_office_engine.services.real_estate_plan
```

Funzione principale:

- `build_real_estate_plan(input_path, output_path)`: confronta alternative immobiliari esplicite e scrive `real-estate-plan/v1`.

`real-estate-plan/v1` normalizza immobili, quote di titolarita', costi annui, imposte dichiarate, ipotesi di locazione, vacancy e vendita. Produce alternative `hold`, `rent` e `sell` con cashflow/proventi annui, liquidita' attesa, gap e hash riproducibile.

Il servizio non calcola imposte normative, successione, perizie, finanziamenti, FX, raccomandazioni o dichiarazioni. Imposte, costi, canoni, vacancy e prezzo di vendita devono essere espliciti nell'input oppure diventano data gap.

Fixture:

- `examples/real-estate-plan-sample.json`

## Protection Gap

Modulo:

```text
family_office_engine.services.protection_gap
```

Funzione principale:

- `build_protection_gap(input_path, output_path)`: confronta fabbisogni familiari e polizze assicurative esplicite e scrive `protection-gap/v1`.

`protection-gap/v1` normalizza bisogni familiari, polizze vita/rischio, inabilita', miste e investimento, beneficiari, capitali assicurati, premi e riscatti. Produce gap di protezione per evento coperto, separando la copertura rischio dal valore di riscatto investimento.

Il servizio non calcola consulenza assicurativa, sanitaria, attuariale, legale, fiscale, underwriting, successione o raccomandazioni. Beneficiari, capitali, fabbisogni, premi e riscatti devono essere espliciti oppure diventano gap.

Fixture:

- `examples/protection-gap-sample.json`

## Estate Plan

Modulo:

```text
family_office_engine.services.estate_plan
```

Funzione principale:

- `build_estate_plan(input_path, rule_pack_path, output_path)`: confronta attribuzioni successorie dichiarate, donazioni pregresse, beneficiari, polizze e liquidita' fiscale e scrive `estate-plan/v2`.

`estate-plan/v2` usa un rule pack versionato per casi italiani semplici con coniuge e/o figli. Calcola massa ereditaria nota, massa fittizia dichiarata, quote di riserva, conflitti civilistici, stime di imposta successione/donazione per relazioni coperte e gap per estero, polizze non documentate, attribuzioni incomplete e liquidita' fiscale mancante.

Il servizio non calcola collazione, riduzione, base catastale, successione estera, trust, patti, contenzioso, dichiarazioni o raccomandazioni.

Fixture:

- `examples/estate-plan-sample.json`

## Investment Opportunity

Modulo:

```text
family_office_engine.services.investment_opportunity
```

Funzione principale:

- `build_investment_opportunity(input_path, output_path)`: trasforma scenari con sole assunzioni esplicite in `investment-opportunity/v1`.

Il core calcola acquisition basis, ricavi e costi operativi annui, NOI, free cash flow annuo, valore residuo/costi di uscita e costo del tempo del proprietario. Il beneficio economico dell'uso personale resta una metrica separata: non entra in NOI o free cash flow e non riceve alcun trattamento fiscale implicito.

Non inferisce rendimenti, tassi di occupazione/utilizzo, tariffe, fiscalita', classificazioni dell'attivita', finanziamento o valore residuo. Ognuno deve essere un input esplicito e versionato oppure un `data_gap`.

Fixture:

- `examples/investment-opportunity-income-property-sample.json`
- `examples/investment-opportunity-rentable-movable-asset-sample.json`

## Real-estate Investment V2

Modulo:

```text
family_office_engine.services.real_estate_investment
```

Funzione principale:

- `build_real_estate_investment(input_path, output_path)`: adatta driver immobiliari dichiarati a `investment-opportunity/v1` e produce `real-estate-investment/v2`.

Il servizio calcola solo ricavi da locazione lunga/breve dichiarati, vacancy, commissione di gestione, costi operativi, NOI, cash flow, tax drag dichiarato e valore netto di uscita. Giorni e beneficio di uso personale restano separati dal cash flow. In assenza di classificazione fiscale esplicita e versionata restituisce `missing_tax_classification`; non deduce aliquote o classificazioni.

Fixture:

- `examples/real-estate-investment-v2-sample.json`

## Rentable Movable Asset V1

Modulo:

```text
family_office_engine.services.rentable_movable_asset
```

Funzione principale:

- `build_rentable_movable_asset(input_path, output_path)`: adatta driver dichiarati di un asset mobile noleggiabile a `investment-opportunity/v1` e produce `rentable-movable-asset/v1`.

Il servizio conserva separati giorni disponibili, uso personale, noleggio e downtime; calcola ricavo da tariffa/giorni, fee piattaforma dichiarata, costi, NOI, cash flow e valore netto di uscita. Il beneficio d'uso personale non e' reddito o cash flow fiscale. La classificazione dell'attivita' non e' dedotta dalla frequenza: senza input validato produce `missing_activity_classification`.

Fixture:

- `examples/rentable-movable-asset-v1-sample.json`

## Financing Plan V1

Modulo:

```text
family_office_engine.services.financing_plan
```

Funzione principale:

- `build_financing_plan(input_path, output_path)`: costruisce il debt schedule annuale `financing-plan/v1` da termini, tassi, rimborsi e cash flow dell'asset dichiarati.

Il contratto espone separatamente interessi, capitale, rimborso anticipato, fee, debito residuo, LTV, debt service e DSCR quando il NOI e' dichiarato. Il cash flow dell'asset prima del finanziamento non viene mai confuso con il cash flow dell'equity dopo debt service. Tassi fissi/variabili, fee e rimborsi sono input espliciti; non inferisce fiscalita', performance dell'asset, valori delle garanzie o percorsi dei tassi.

Fixture:

- `examples/financing-plan-v1-sample.json`

## Wealth Strategy

Modulo:

```text
family_office_engine.services.wealth_strategy
```

Funzione principale:

- `build_wealth_strategy(input_path, output_path, ..., investment_opportunity_comparison_snapshot_paths=...)`: compone pacchetti strategici dichiarati, snapshot V4 e confronti `investment-opportunity-comparison/v1` in `wealth-strategy/v1`.

`wealth-strategy/v1` verifica sorgenti, schema, status, hash e selettori dei componenti; i confronti d'investimento sono selezionati per `comparison_id` e scenario e possono essere multipli. Produce 2-4 pacchetti comparabili con punteggi ponderati dichiarati, parita' esplicite, piano 90/180 giorni, costi, dipendenze, reversibilita', controlli, rischi, scenari avversi e data gaps. Utilita' personale dichiarata resta un'annotazione economica `not_taxable_cash_flow`; gap fiscali/household/benchmark o una parita' disabilitano `automatic_ranking_produced`.

Il servizio non calcola nuove imposte, pensioni, rendimenti, effetti legali o raccomandazioni. I punteggi e i pacchetti sono input espliciti; gli snapshot sorgente restano l'evidenza deterministica.

Fixture:

- `examples/wealth-strategy-input-sample.json`

## IT-ES EU Pension Pro-Rata

Modulo:

```text
family_office_engine.services.it_es_eu_pension_pro_rata
```

Funzione principale:

- `build_it_es_eu_pension_pro_rata(input_path, rule_pack_path, output_path, spanish_theoretical_snapshot_path=None)`: stima diritto spagnolo in coordinamento UE e scrive `it-es-eu-pension-pro-rata/v1`.
- `build_spanish_eu_theoretical_pension(pro_rata_input_path, reconciliation_snapshot_path, rule_pack_path, output_path)`: calcola `spanish-eu-theoretical-pension/v1` da periodi IT/ES datati, basi spagnole riconciliate e rule pack UE/Spagna.

`spanish-eu-theoretical-pension/v1` valorizza la finestra spagnola con basi ufficiali ES e, per mesi UE esteri nella finestra, con la base ES piu' vicina aggiornata tramite IPC versionato nel rule pack. I periodi italiani restano periodi UE totalizzati e non diventano basi contributive spagnole. `it-es-eu-pension-pro-rata/v1` legge periodi assicurativi IT/ES datati e un importo teorico spagnolo esplicito oppure uno snapshot teorico completo. Il servizio normalizza i mesi, conta una sola volta le sovrapposizioni nel denominatore UE, distingue diritto autonomo spagnolo e diritto per totalizzazione, quindi calcola la quota pro-rata spagnola da importo teorico e rapporto ES/UE.

Il servizio non calcola pensione INPS normativa, P1 ufficiale, fiscalita', netto, basi spagnole da periodi italiani, Paesi diversi da Italia/Spagna o contribuzione futura non dichiarata.

Fixture:

- `examples/it-es-eu-pension-pro-rata-input-sample.json`
- `examples/spanish-eu-theoretical-pension-pro-rata-input-sample.json`
- `examples/spanish-eu-theoretical-pension-reconciliation-sample.json`

## Tax Reconciliation

Modulo:

```text
family_office_engine.services.tax_reconciliation
```

Funzioni principali:

- `reconcile_tax_sources(payroll_snapshot_path, tax_documents_snapshot_path, output_path)`: confronta anni e campi disponibili da payroll, CU e dichiarazione e scrive `tax-reconciliation/v1`.

Il servizio non calcola imposte. Somma solo valori payroll gia' estratti per osservabilita' documentale e segnala gap temporali, duplicati e fonti fiscali mancanti.

## Tax Documents Ingestion

Modulo:

```text
family_office_engine.ingestion.tax_documents
```

Funzioni principali:

- `import_tax_documents(cu_dir, declarations_dir, output_path)`: legge CU e dichiarazioni classificate e scrive `tax-documents/v1`.
- `diagnose_tax_documents(cu_dir, declarations_dir)`: restituisce diagnostica senza scrivere snapshot.
- `parse_tax_document_text(text, filename, document_group)`: parser deterministico del testo PDF.

Il modulo registra solo valori esplicitamente presenti nei documenti fiscali e mantiene provenance per documento. Non esegue calcoli fiscali.

## Work-exit Feasibility

Modulo:

```text
family_office_engine.services.work_exit_feasibility
```

Funzione principale:

- `build_work_exit_feasibility(input_path, rule_pack_path, output_path, ...)`: cerca la prima data sostenibile di uscita dal lavoro e scrive `work-exit-feasibility/v1`.

`work-exit-feasibility/v1` valuta date candidate esplicite, stima `inps-theoretical-pension/v1` per persona con rule pack INPS contributivo, compone pensione INPS interna, benchmark documentale INPS, quota spagnola pro-rata e pensioni dichiarate del coniuge come stream separati. La sostenibilita' usa solo vincoli patrimoniali e di spesa dichiarati; non calcola netto fiscale, decorrenze amministrative, raccomandazioni o pensioni ufficiali.

Fixture:

- `examples/work-exit-feasibility-sample.json`
- `examples/work-exit-inps-snapshot-sample.json`
- `examples/work-exit-pro-rata-sample.json`

## Tool Registry

Modulo:

```text
family_office_engine.services.tool_registry
```

Funzioni principali:

- `build_tool_registry(output_path=None)`: costruisce `tool-registry/v1` con i tool deterministici locali registrati.
- `invoke_registered_tool(tool_id, requested_output_schema_version, parameters)`: invoca solo un tool registrato, valida versione output richiesta e parametri ammessi, quindi restituisce `tool-invocation/v1`.

`tool-registry/v1` espone identificativo tool, schema input/output, parametri richiesti/opzionali, prerequisiti, rischio, policy di autorizzazione e note di perimetro. Il registry e' esplicito: non abilita discovery dinamica delle funzioni interne e non consente all'LLM di calcolare imposte, pensioni, rendimenti o valori finanziari.

## Citation Index

Modulo:

```text
family_office_engine.services.citation_index
```

Funzioni principali:

- `build_citation_index(catalog_path, knowledge_root, contract_records=None, output_path=None, as_of_date=None)`: valida `knowledge-citation-catalog/v1` e costruisce `citation-index/v1`.
- `search_citation_index(index_path, query=None, jurisdiction=None, topic=None, as_of_date=None, include_inactive=False)`: ricerca fonti per testo, giurisdizione, tema e data, restituendo `citation-search/v1`.

`citation-index/v1` contiene fonti normalizzate, documenti knowledge con hash, contratti input/output derivati dal tool registry, alias deduplicati e data gaps. Le fonti sono ordinate per livello di autorita'; una fonte scaduta, abrogata, futura o ritirata non entra nei risultati correnti salvo richiesta esplicita `include_inactive`.

Il servizio non scarica fonti, non interpreta norme e non crea metadati mancanti. Un documento senza citation ID strutturato resta nell'indice con `knowledge_document_citation_missing`. La ricerca `knowledge.citations.search` e' registrata nel tool registry come capability read-only.

L'hash di `citation-index/v1` copre catalogo, hash dei documenti, data indice, gap e contratti input/output derivati dal tool registry. Di conseguenza l'aggiunta o la modifica di un tool cambia hash e conteggio dei contratti anche quando i file knowledge non cambiano; catalog hash e document hash permettono di distinguere le due cause.

## Supported-question catalog

Modulo:

```text
family_office_engine.services.supported_question_catalog
```

Funzioni principali:

- `build_supported_question_catalog()`: costruisce `supported-question-catalog/v1` con famiglie di domande, tool registrati, dati minimi, output, rischio, limiti ed escalation.
- `assess_question_capability(intent_ids, provided_data=None)`: valuta intenti gia' selezionati e restituisce `question-capability-assessment/v1`, senza classificare testo libero ne' invocare tool.

Il catalogo copre ogni tool del registry una sola volta nella capability disponibile. Le domande su investimenti a reddito o asset mobili noleggiabili richiedono ora un confronto deterministico e gap dichiarati; il routing da linguaggio naturale e' fornito da `question-intent/v1` (V5.4), ma non invoca tool. Dati minimi mancanti, intenti sovrapposti, sconosciuti o che richiedono consulenza professionale producono problemi espliciti.

## Question intent

Modulo:

```text
family_office_engine.services.question_intent
```

- `route_question_intent(question, provided_data=None)`: restituisce `question-intent/v1` da regole lessicali versionate, senza tool invocation, calcoli o scritture di facts.
- `build_question_intent(question, output_path, provided_data=None)`: scrive lo stesso snapshot nel workspace; conserva un fingerprint, non il testo della domanda.

Il router riusa `supported-question-catalog/v1`, propone soltanto entita' riconosciute e rende espliciti intenti ambigui, dati minimi mancanti, prompt injection e richieste fuori perimetro. Gli investimenti produttivi sono ora disponibili solo tramite il tool registrato `planning.investment_opportunity_comparison.build`, con confronti e gap dichiarati; il router non lo invoca.

## Scenario draft

Modulo:

```text
family_office_engine.services.scenario_draft
```

- `draft_scenario(question)`: restituisce `scenario-draft/v1` con sole proposte esplicite e richieste di conferma.
- `build_scenario_draft(question, output_path)`: scrive lo stesso draft senza persistere il testo della domanda.

Il builder usa il router solo per fingerprint e perimetro, poi estrae in modo deterministico età pensionabile, date ISO, budget EUR e obiettivi università dei figli quando sono espliciti. Ogni valore resta `confirmation_required`; età incoerenti, importi non positivi, date non valide, istruzioni di tool e omissioni producono conflitti, valori rifiutati o data gaps. `scenario-draft/v1` non è un `decision-scenario/v2`, non è eseguibile e non calcola imposte, pensioni, rendimenti o saldi.

## Execution executor and evidence bundle

Modulo `family_office_engine.services.execution_executor`: `execute_plan(request)` esegue soltanto un `execution-plan/v1` pronto con lineage corrente attraverso `invoke_registered_tool`; `build_evidence_bundle(input_path, output_path)` persiste `evidence-bundle/v1`. Il request privato fornisce valori ai binding ma il bundle conserva soltanto hash e riferimenti dei valori, oltre a output, fonti, stati, errori e data gaps. Le autorizzazioni devono soddisfare la policy del registry, i retry sono limitati a tool read-only e timeout/fallimenti/dependency skip restano riproducibili. L'executor non introduce calcoli LLM fiscali, previdenziali o finanziari.

## Execution plan

Modulo:

```text
family_office_engine.services.execution_plan
```

- `plan_execution(data)`: valida `execution-plan-input/v1` e restituisce un `execution-plan/v1` ispezionabile, senza invocare tool.
- `build_execution_plan(input_path, output_path)`: legge lo stesso input JSON e scrive il piano nel workspace.

Il planner accetta soltanto un `question-intent/v1` con stato `routed`, lineage del catalogo corrente e binding di input come metadati: non accetta valori grezzi. Ogni nodo deve usare un tool presente nel registry e autorizzato dagli intenti selezionati; i parametri obbligatori devono essere dichiarati, le dipendenze devono formare un DAG e un input sensibile richiede `explicit_user_consent`. L'output conserva ordine topologico, controlli, stop criteria, policy e hash; tutti i nodi restano `not_executed`. L'esecuzione appartiene a V5.7 e il servizio non calcola importi fiscali, previdenziali o finanziari.
