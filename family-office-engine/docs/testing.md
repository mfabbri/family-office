# Testing

## Unit Test

Dal repository `family-office-engine`:

```text
$env:PYTHONPATH='src'; python -m unittest discover -s tests/unit
```

## Payroll

Verifica diagnostica:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main payroll diagnose
```

Verifica import:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main payroll import
```

Se l'import mostra `not_extracted`, lanciare prima `payroll diagnose` per controllare:

- directory input effettiva;
- numero di PDF visti;
- stato per documento;
- codici gap.

I test dell'engine usano solo fixture sintetiche e non includono dati personali.

## Tax Rules

Verifica calcolo con rule pack IRPEF nazionale 2026:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main tax calculate --taxable-income 60000.00
```

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\tax-calculation.snapshot.json
```

Il default calcola solo imposta lorda nazionale su imponibile gia' determinato. Non include detrazioni, addizionali, crediti o dichiarazione completa.

Verifica runtime con fixture sintetica:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main tax calculate --rule-pack ..\family-office-rules\tests\fixtures\synthetic-progressive-tax.json --jurisdiction SYNTH --taxable-income 45000.00
```

La fixture `SYNTH` serve solo a testare loader, scaglioni progressivi, explainability e gap per regole mancanti. Non usare questo output come calcolo fiscale reale.

## RITA

Verifica opzioni RITA V1 con input sintetici:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main rita optimize --age 62 --years-to-public-pension 4 --employment-status ceased --mandatory-contribution-years 32 --complementary-pension-years 8 --complementary-balance 120000.00 --duration-months 48 --monthly-need 3000.00
```

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\rita-options.snapshot.json
```

Il comando calcola solo una rendita lorda lineare da montante e durata espliciti. Non calcola tassazione, pensione pubblica, rendimenti, costi o vincoli del fondo.

## Estate Baseline

Verifica baseline successoria V1:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main estate baseline --has-spouse --children-count 2 --prior-donations 0.00
```

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\estate-baseline.snapshot.json
```

Se il net worth reale non contiene quote di titolarita' esplicite, lo snapshot e' `partial` e registra `missing_ownership` invece di inventare masse successorie.

## Household Facts

Verifica contratto household con fixture sintetica:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main household validate --input examples/household-facts-sample.json
```

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\household-facts.snapshot.json
```

Il file reale privato atteso e':

```text
..\family-office-workspace\household\household-facts.json
```

Il repository workspace contiene un draft vuoto in `household/household-facts.draft.json`.

## Ownership Beneficiary Graph

Verifica contratto ownership/beneficiari con fixture sintetica:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main household ownership validate --input examples/ownership-beneficiary-graph-sample.json
```

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\ownership-beneficiary-graph.snapshot.json
```

Il file reale privato atteso e':

```text
..\family-office-workspace\household\ownership-beneficiaries.json
```

Il repository workspace contiene un draft vuoto in `household/ownership-beneficiaries.draft.json`.

## Asset Availability

Verifica contratto classificazione e disponibilita' asset con fixture sintetica:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main household availability validate --input examples/asset-availability-sample.json
```

Verifica CLI sul workspace privato:

```text
fo household availability wizard
fo household availability validate --skip-ownership-check
```

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\asset-availability.snapshot.json
```

Il file reale privato atteso e':

```text
..\family-office-workspace\household\asset-availability.json
```

Il repository workspace contiene un draft vuoto in `household/asset-availability.draft.json` e una guida compilabile in `household/household-input-guide.md`. Il wizard parte dagli asset del net worth, valida input come paese e data, salva progressivamente e permette `unknown` per disponibilita' non nota; `--skip-ownership-check` serve quando gli asset classificati arrivano dal net worth e il grafo ownership non e' ancora allineato.

## Timeline Events

Verifica contratto timeline con fixture sintetica:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main household timeline validate --input examples/timeline-events-sample.json
```

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\timeline-events.snapshot.json
```

Il file reale privato atteso e':

```text
..\family-office-workspace\household\timeline-events.json
```

La policy tecnica di default e':

```text
..\family-office-rules\timeline\default-overlap-policy.json
```

Il repository workspace contiene un draft vuoto in `household/timeline-events.draft.json`.

## Spanish Contribution History

Verifica import previdenziale spagnolo:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main pension import-spain
```

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\spanish-contribution-history.snapshot.json
```

Il comando legge documenti reali privati da:

```text
..\family-office-workspace\documents\pensione\spagna
```

I test unitari usano solo testi e CSV sintetici:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_spanish_contribution_history
```

Il contratto registra periodi e basi contributive documentate. Non calcola pensione spagnola, diritto, coordinamento UE o fiscalita'.

## Spanish Contribution Reconciliation

Verifica riconciliazione previdenziale spagnola:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main pension reconcile-spain
```

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\spanish-contribution-reconciliation.snapshot.json
```

Input atteso:

```text
..\family-office-workspace\snapshots\spanish-contribution-history.snapshot.json
```

Test unitari:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_spanish_contribution_reconciliation
```

La riconciliazione seleziona basi mensili documentali e rende visibili gap/anomalie. Non calcola pensione spagnola, diritto, base reguladora, coordinamento UE o fiscalita'.

## Spanish Pension Rules

Verifica loader e validatore del rule pack spagnolo:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_spanish_pension_rules
```

Il test usa il rule pack pubblico:

```text
..\family-office-rules\spain\statutory-retirement-general.json
```

Il baseline valida fonti, limitazioni, eta' ordinaria, parametri della base reguladora e progressione della percentuale maturata. Non produce ancora snapshot ne' importi pensionistici.

## Spanish Statutory Pension

Verifica estimatore ordinario spagnolo con fixture sintetiche:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_spanish_statutory_pension
```

Verifica CLI sul workspace privato:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main pension estimate-spain --retirement-year 2026
```

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\spanish-statutory-pension.snapshot.json
```

L'estimatore produce `spanish-statutory-pension/v1` solo per pensione ordinaria lorda. In assenza di basi ufficiali sufficienti o requisiti minimi scrive `blocked_missing_inputs`. Non calcola risultato ufficiale, anticipo, differimento, caps, fiscalita', supplementi, rivalutazione basi, integrazione lagune o coordinamento UE.

## EU Pension Coordination Italy-Spain

Verifica coordinamento con fixture sintetiche:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_eu_pension_coordination
```

Verifica CLI sul workspace privato:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main pension coordinate-it-es --italian-contribution-months 240
```

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\eu-pension-coordination-it-es.snapshot.json
```

Il dossier mantiene separate pensione INPS e pensione spagnola. La totalizzazione serve solo per diritto/diagnostica e il pro-rata resta non calcolabile senza importi teorici nazionali e periodi normalizzati. Non calcola P1 ufficiale, pensione INPS normativa, fiscalita', netto o trasferimenti di contributi.

## Pension Income Composer

Verifica composer con fixture sintetiche:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_pension_income
```

Verifica CLI sul workspace privato:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main pension compose-income
```

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\pension-income.snapshot.json
```

Il composer produce `pension-income/v1` mantenendo separati INPS, pensione spagnola e RITA. Somma solo importi lordi annuali ricorrenti, espliciti e in EUR; non calcola netto, fiscalita', pensione INPS normativa o annualizzazioni mancanti.

Verifica uso opzionale nella simulazione retirement:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main retirement simulate --pension-income-snapshot ..\family-office-workspace\snapshots\pension-income.snapshot.json
```

La simulazione usa il totale lordo annuo ricorrente come offset dei prelievi post-pensionamento, senza calcolare imposte o decorrenze mensili.

## Lifecycle Expenses

Verifica modello spese lifecycle con fixture sintetiche:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_lifecycle_expenses
```

Verifica CLI sul workspace privato:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main expenses build-lifecycle
```

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\lifecycle-expenses.snapshot.json
```

Il modello produce `lifecycle-expenses/v1` da un piano spese esplicito in `household/lifecycle-expenses.json`. Applica inflazione solo quando dichiarata e registra gap per periodi o eventi mancanti; non stima budget, fiscalita', sanita', cambi, rendimenti o raccomandazioni.

## Decision Scenario V2

Verifica composer con fixture sintetiche:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_decision_scenario
```

Verifica CLI sul workspace privato:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main scenarios compose-v2
```

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\decision-scenario-v2.snapshot.json
```

Il composer produce `decision-scenario/v2` da snapshot e assunzioni scenario esplicite. Include un hash riproducibile del contenuto canonico e non esegue simulazioni, scoring, imposte, rendimenti o raccomandazioni.

## Decision Outcome

Verifica evaluator bridge con fixture sintetiche:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_decision_outcome
```

Verifica CLI sul workspace privato, dopo aver predisposto scenario e configurazione outcome:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main scenarios evaluate
```

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\decision-outcome.snapshot.json
```

I test coprono metriche Monte Carlo calcolate, seed e hash stabili, provenance per metrica, scenario parziale, input mancanti, schema incompatibile ed evaluator non supportato. I dati sono esclusivamente sintetici.

## Sensitivity Analysis

Verifica analyzer con fixture sintetiche:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_sensitivity_analysis
```

Verifica CLI sul workspace privato:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main scenarios sensitivity
```

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\sensitivity-analysis.snapshot.json
```

L'analyzer produce `sensitivity-analysis/v1` da `decision-scenario/v2` e da una specifica esplicita in `scenarios/sensitivity-analysis.json`. Con `outcome_evaluation` riesegue il Monte Carlo deterministico per baseline, varianti e stress, calcola delta per le metriche comuni e ordina il tornado sulla metrica dichiarata.

I test coprono perturbazione con effetto, perturbazione senza effetto, stress combinato, singola esecuzione per variante, evaluator bloccato, gap espliciti, seed/hash stabili e compatibilita' con il formato legacy senza outcome. Non vengono calcolati fiscalita', diritti pensionistici, scoring o raccomandazioni.

## V3 Golden Pipeline

Verifica end-to-end del gate V3 -> V4 con fixture sintetiche:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_v3_golden_pipeline
```

Il golden attraversa `decision-scenario/v2`, `sensitivity-analysis/v1` con outcome Monte Carlo deterministico, `decision-score/v1` outcome-linked e `decision-dossier/v1`. Verifica hash stabili, ranking tracciabile, dossier completo e assenza di gap bloccanti.

## Decision Score

Verifica scorer con fixture sintetiche:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_decision_score
```

Verifica CLI sul workspace privato:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main scenarios score
```

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\decision-score.snapshot.json
```

Lo scorer produce `decision-score/v1` da pesi espliciti in `scenarios/decision-score.json` e metriche risolte dagli outcome deterministici contenuti in `sensitivity-analysis/v1`, normalizzati dal policy pack `..\family-office-rules\decision\score-policy-v1.json`. Metriche manuali prive di outcome lineage sono gap bloccanti. Non calcola metriche sottostanti, fiscalita', rendimenti, pensioni, ottimizzazioni o raccomandazioni.

## Decision Dossier

Verifica dossier con fixture sintetiche:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_decision_dossier
```

Verifica CLI sul workspace privato:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main scenarios dossier
```

Gli output risultanti vengono scritti in:

```text
..\family-office-workspace\snapshots\decision-dossier.snapshot.json
..\family-office-workspace\reports\decision-dossier.md
```

Il dossier produce `decision-dossier/v1` e un report Markdown da scenario, sensitivity e score. Blocca la raccomandazione quando sono presenti gap bloccanti, ranking incompleto o lineage metrica incompleto; non calcola nuove metriche, fiscalita', rendimenti, pensioni, ottimizzazioni o raccomandazioni AI.

## Planning Goals

Verifica contratto obiettivi e vincoli V4 con fixture sintetiche:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_planning_goals
```

Verifica CLI sul workspace privato:

```text
fo planning goals status
fo planning goals prepare
fo planning goals validate
```

Da checkout sorgente:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning goals status
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning goals prepare
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning goals validate
```

Verifica demo sintetica senza ricordare path JSON:

```text
fo planning goals demo
```

Da checkout sorgente:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning goals demo
```

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\planning-goals.snapshot.json
```

Il contratto `planning-goals/v1` registra obiettivi, priorita', soglie, orizzonte, rischio, liquidita' e vincoli dichiarati. I test coprono snapshot completo, hash stabile, priorita' duplicate, soglie range incoerenti, riferimenti a obiettivi inesistenti, riferimenti timeline mancanti e data gaps. Non vengono calcolati rendimenti, imposte, ottimizzazioni, scoring o raccomandazioni.

## Liquidity Plan

Verifica contratto bucket di liquidita' V4 con fixture sintetiche:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_liquidity_plan
```

Verifica CLI sul workspace privato:

```text
fo planning liquidity build
fo planning liquidity explain
```

Da checkout sorgente:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning liquidity build
```

Verifica demo sintetica senza ricordare path JSON:

```text
fo planning liquidity demo
```

Da checkout sorgente:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning liquidity demo
```

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\liquidity-plan.snapshot.json
```

Il contratto `liquidity-plan/v1` assegna asset valorizzati a riserva, breve, medio, lungo termine e restricted usando net worth, asset availability e planning goals. I test coprono shortfall di riserva, asset bloccati per spese correnti, spiegazione CLI degli asset non usabili, valuta estera senza conversione e senza funding della riserva, concentrazione, hash stabile e input mancanti. Non vengono calcolati rendimenti, imposte, cambi valuta, ottimizzazioni, scoring o raccomandazioni.

## Decumulation Strategy

Verifica contratto strategie di decumulo V4 con fixture sintetiche:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_decumulation_strategy
```

Verifica CLI sul workspace privato:

```text
fo planning decumulation wizard
fo planning decumulation build
```

Da checkout sorgente:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning decumulation build
```

Verifica demo sintetica senza ricordare path JSON:

```text
fo planning decumulation demo
```

Da checkout sorgente:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning decumulation demo
```

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\decumulation-strategy.snapshot.json
```

Il contratto `decumulation-strategy/v1` confronta policy dichiarate usando net worth, liquidity plan, pension income e RITA options. I test coprono piu' eta' di pensionamento, sequenza rendimenti, longevita', RITA si'/no, wizard con contesto goals/liquidita', salvataggio progressivo, aliquote ignote come gap, hash stabile e input mancanti. Non vengono calcolati fiscalita' normativa, rendimenti attesi, cambi valuta, ottimizzazioni o raccomandazioni.

## Pension Contribution Options

Verifica contratto opzioni contributive V4 con fixture sintetiche:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_pension_contribution_options
```

Verifica CLI sul workspace privato:

```text
fo planning pension-contributions wizard
fo planning pension-contributions build
```

Demo sintetica senza ricordare path JSON:

```text
fo planning pension-contributions demo
```

Da checkout sorgente:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning pension-contributions demo
```

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\pension-contribution-options.snapshot.json
```

Il contratto `pension-contribution-options/v1` confronta opzioni esplicite con rule pack di deducibilita' previdenza complementare. I test coprono plafond ordinario, contributo datore, extra prima occupazione, TFR separato, vincolo liquidita', wizard da contesto liquidita', errore missing-input con next step, anno non coperto e CLI demo. Non vengono calcolati IRPEF completa, rendimenti, matching contrattuale non dichiarato, ottimizzazioni o raccomandazioni.

## Tax-aware Portfolio

Verifica contratto portafoglio fiscalmente consapevole V4 con fixture sintetiche:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_tax_aware_portfolio
```

Verifica CLI sul workspace privato:

```text
fo planning tax-aware-portfolio build
```

Demo sintetica senza ricordare path JSON:

```text
fo planning tax-aware-portfolio demo
```

Da checkout sorgente:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning tax-aware-portfolio demo
```

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\tax-aware-portfolio.snapshot.json
```

Il contratto `tax-aware-portfolio/v1` confronta opzioni esplicite con rule pack fiscale investimenti. I test coprono aliquota 26%, aliquota 12,5% documentata, costi, turnover, bollo, IVAFE, uso minusvalenze, regime incompatibile, anno non coperto e CLI demo. Non vengono calcolati rendimenti attesi, fiscalita' estera completa, dichiarazione, PIR, cripto-attivita', ottimizzazioni o raccomandazioni.

## IT-ES Pension Tax Classification

Verifica contratto classificazione fiscale pensioni Italia-Spagna V4 con fixture sintetiche:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_it_es_pension_tax_classification
```

Verifica CLI sul workspace privato:

```text
fo planning it-es-pension-tax classify
```

Demo sintetica senza ricordare path JSON:

```text
fo planning it-es-pension-tax demo
```

Da checkout sorgente:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning it-es-pension-tax demo
```

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\it-es-pension-tax-classification.snapshot.json
```

Il contratto `it-es-pension-tax-classification/v1` classifica stream pensionistici transfrontalieri usando pension income e rule pack Convenzione Italia-Spagna. I test coprono residente italiano, cambio di residenza, pensione pubblica, pensione privata, eccezione di nazionalita', classificazione incerta, anno non coperto e CLI demo. Non vengono calcolati ritenute effettive, IRPEF, IRPF spagnola, crediti d'imposta, netto pensionistico o dichiarazione completa.

## Spanish Pension Net IT Resident

Verifica contratto netto pensione spagnola per residente fiscale italiano V4 con fixture sintetiche:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_spanish_pension_net_it_resident
```

Verifica CLI sul workspace privato:

```text
fo planning spanish-pension-net build
```

Demo sintetica senza ricordare path JSON:

```text
fo planning spanish-pension-net demo
```

Da checkout sorgente:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning spanish-pension-net demo
```

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\spanish-pension-net-it-resident.snapshot.json
```

Il contratto `spanish-pension-net-it-resident/v1` calcola un ponte lordo-netto usando pension income, classificazione IT-ES, input fiscale esplicito, rule pack netto e IRPEF nazionale. I test coprono assenza/presenza ritenuta spagnola, credito capiente, credito limitato da capienza dichiarata, ritenuta non definitiva, classificazione mancante, anno non coperto e CLI demo. Non vengono calcolati detrazioni, addizionali, acconti, rimborsi, imposte spagnole da aliquote spagnole o dichiarazione completa.

## IT-ES Foreign Assets

Verifica contratto monitoraggio asset esteri Italia-Spagna V4:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_it_es_foreign_assets
```

Demo sintetica senza ricordare path JSON:

```text
fo planning it-es-foreign-assets demo
```

Da checkout sorgente:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning it-es-foreign-assets demo
```

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\it-es-foreign-assets.snapshot.json
```

Il contratto `it-es-foreign-assets/v1` usa input esplicito e rule pack RW/IVAFE/IVIE. I test coprono conto, fondi, piano pensionistico, immobile, intermediario italiano documentato, dato non classificato e anno non coperto. Non vengono calcolati dichiarazione completa, redditi esteri, crediti esteri, fiscalita' spagnola, cripto-attivita' o raccomandazioni.

## Cross-Border IT-ES Dossier

Verifica dossier transfrontaliero Italia-Spagna V4:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_cross_border_it_es_dossier
```

Demo sintetica senza ricordare path JSON:

```text
fo planning cross-border-it-es demo
```

Da checkout sorgente:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning cross-border-it-es demo
```

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\cross-border-it-es.snapshot.json
```

Il contratto `cross-border-it-es/v1` compone snapshot deterministici di scenario pensionistico, pensione, fiscalita' pensionistica, quota pro-rata UE e asset spagnoli. I test coprono pensione con asset, sola pensione, soli asset, cambio di residenza, classificazione bloccante, gap annidati, `blocked_not_eligible`, mismatch di contesto, pension income senza contesto, scenario pensionistico sintetico rifiutato per household personali, fonte configurata mancante, vincolo privacy su output fuori workspace e assenza totale di fonti. Non vengono ricalcolati pensioni, imposte, crediti, valori patrimoniali, dichiarazioni o raccomandazioni.

## Pension Scenario

Verifica contratto assunzioni pensionistiche Italia-Spagna V4:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_pension_scenario
```

Demo sintetica senza ricordare path JSON:

```text
fo planning pension-scenario demo
```

Da checkout sorgente:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning pension-scenario demo
```

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\pension-scenario.snapshot.json
```

Il contratto `pension-scenario/v1` registra baseline, alternative, pensionamento, residenza, trasferimenti post-pensionamento, contributi futuri e provenance. I test coprono baseline Italia, trasferimento in Spagna, data trasferimento mancante, assunzioni contributive mancanti o contraddittorie, provenance mancante e rifiuto di fonti sintetiche per household personali. Non vengono calcolati pensioni, imposte, netto, diritto UE, pro-rata o raccomandazioni.

## Real Estate Plan

Verifica contratto pianificazione immobiliare V4:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_real_estate_plan
```

Demo sintetica senza ricordare path JSON:

```text
fo planning real-estate demo
```

Da checkout sorgente:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning real-estate demo
```

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\real-estate-plan.snapshot.json
```

Il contratto `real-estate-plan/v1` confronta mantenimento, locazione e vendita usando immobili, quote di titolarita', costi, imposte dichiarate, canone, vacancy e prezzo di vendita espliciti. I test coprono locazione, vacancy mancante, vendita, costi, titolarita' del coniuge, gap fiscali e quote non valide. Non vengono calcolati imposte normative, successione, perizie, finanziamenti, FX, dichiarazioni o raccomandazioni.

## Protection Gap

Verifica contratto protezione familiare V4:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_protection_gap
```

Demo sintetica senza ricordare path JSON:

```text
fo planning protection demo
```

Da checkout sorgente:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning protection demo
```

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\protection-gap.snapshot.json
```

Il contratto `protection-gap/v1` confronta fabbisogni familiari e polizze usando beneficiari, capitali assicurati, premi, riscatti e provenance espliciti. I test coprono beneficiario mancante, capitale insufficiente, distinzione tra polizza investimento e protezione, share beneficiario non valida e smoke CLI. Non vengono calcolati consulenza assicurativa, sanitaria, attuariale, legale, fiscale, underwriting, successione o raccomandazioni.

## IT-ES EU Pension Pro-Rata

Verifica contratto diritto spagnolo UE e quota pro-rata V4:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_it_es_eu_pension_pro_rata
```

Demo sintetica senza ricordare path JSON:

```text
fo planning it-es-eu-pension demo
```

Demo sintetiche senza path JSON:

```text
fo planning spanish-eu-theoretical-pension demo
fo planning it-es-eu-pension demo
```

Percorso personale ordinario senza path JSON:

```text
fo planning it-es-eu-pension wizard
fo planning spanish-eu-theoretical-pension build
fo planning it-es-eu-pension build
```

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\it-es-eu-pension-pro-rata.snapshot.json
```

Il contratto `spanish-eu-theoretical-pension/v1` calcola l'importo teorico spagnolo lordo usando basi ES ufficiali e basi ES piu' vicine aggiornate IPC per mesi UE esteri nella finestra; `it-es-eu-pension-pro-rata/v1` puo' usare lo snapshot teorico senza edit manuale dell'input. I test coprono diritto autonomo, diritto per totalizzazione, sovrapposizioni, requisito recente, importo teorico mancante, fonti non ufficiali, IPC mancante, anno non coperto, nessun uso di contributi italiani come basi spagnole e quota pro-rata. Non vengono calcolati pensione INPS normativa, fiscalita', netto, P1 ufficiale, basi spagnole da periodi italiani o contribuzione futura non dichiarata.

Verifica riconciliazione documentale:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main tax reconcile
```

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\tax-reconciliation.snapshot.json
```

La riconciliazione confronta payroll e documenti fiscali gia' importati, ma non calcola imposte.

## Tax Documents

Verifica diagnostica:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main tax-documents diagnose
```

Verifica import:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main tax-documents import
```

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\tax-documents.snapshot.json
```

CU e dichiarazioni reali restano nel workspace. I test usano solo testi sintetici.

## Work-exit feasibility

Test mirati:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_work_exit_feasibility
```

Smoke CLI:

```text
fo planning work-exit demo
```

Fallback tecnico:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning work-exit demo
```

Output personale previsto:

```text
..\family-office-workspace\snapshots\work-exit-feasibility.snapshot.json
```

Il contratto `work-exit-feasibility/v1` cerca la prima data sostenibile di uscita dal lavoro usando date candidate, vincoli di spesa/patrimonio, stime `inps-theoretical-pension/v1`, quota spagnola pro-rata e pensione del coniuge come stream lordi separati. I test coprono 2037 vs 2039, prima data trovata, nessuna data sostenibile, benchmark documentale INPS, pensione del coniuge mancante, rule pack proiettivo e data gaps. Non vengono calcolati netto fiscale, certificazioni INPS, P1, ricongiunzioni, riscatti, decorrenze amministrative o raccomandazioni.

## Estate plan V2

Test mirati:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_estate_plan
```

Smoke CLI:

```text
fo planning estate demo
```

Fallback tecnico:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning estate demo
```

Output personale previsto:

```text
..\family-office-workspace\snapshots\estate-plan.snapshot.json
```

Il contratto `estate-plan/v2` confronta scenari di attribuzione dichiarati con quote di riserva, donazioni pregresse, beneficiari, polizze, estero e liquidita' fiscale. I test coprono coniuge e due figli, asset illiquidi, polizze, asset estero, conflitti civilistici, relazione fiscale non familiare, gap dati e smoke CLI. Non vengono calcolati collazione, riduzione, base catastale, successione estera, trust, contenzioso o raccomandazioni.

## Wealth strategy

Test mirati:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_wealth_strategy
```

Smoke CLI:

```text
fo planning wealth-strategy demo
```

Fallback tecnico:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning wealth-strategy demo
```

Output personale previsto:

```text
..\family-office-workspace\snapshots\wealth-strategy.snapshot.json
```

Il contratto `wealth-strategy/v1` compone pacchetti dichiarati usando snapshot V4 esistenti come evidenza. I test coprono ranking ponderato, sorgenti mancanti, componenti incompatibili, numero pacchetti e smoke CLI. Non vengono calcolati nuove imposte, pensioni, rendimenti, effetti legali o raccomandazioni.

Nota operativa: `planning wealth-strategy demo` rigenera snapshot sintetici intermedi `cli-check-*` nel workspace prima di comporre `cli-check-wealth-strategy.synthetic.snapshot.json`. Questi output sono riproducibili e servono a verificare la catena demo, non a rappresentare dati personali.

## Tool registry

Test mirati:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_tool_registry
```

Smoke CLI:

```text
fo orchestration tool-registry build
fo orchestration tool-registry list
```

Fallback tecnico:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main orchestration tool-registry build
```

Output personale previsto:

```text
..\family-office-workspace\snapshots\tool-registry.snapshot.json
```

Il contratto `tool-registry/v1` registra i tool deterministici invocabili da V5 con schema input/output, prerequisiti, rischio e policy. I test coprono snapshot registry, scrittura, tool inesistente, versione incompatibile, parametri mancanti e invocazione controllata di un tool registrato.

## Citation index

Test mirati:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_citation_index
```

Smoke CLI:

```text
fo orchestration citations build --as-of-date 2026-08-09
fo orchestration citations search --jurisdiction IT --topic taxation --as-of-date 2026-08-09
```

Fallback tecnico:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main orchestration citations build --as-of-date 2026-08-09
```

Output locale previsto:

```text
..\family-office-workspace\snapshots\citation-index.snapshot.json
```

I test coprono catalogo reale, hash riproducibile, retrieval temporale, fonte abrogata, citation ID mancante, deduplica del locator, protezione dal path traversal, invocazione read-only tramite registry e smoke CLI build/search. I gap del corpus restano parte del contratto e non vengono risolti con metadati sintetici.

## Supported-question catalog

Test mirato:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_supported_question_catalog
```

I test verificano copertura completa dei tool registrati, hash riproducibile, capability investimento dichiarata `planned` e non eseguibile, data gaps minimi, sovrapposizioni, intenti sconosciuti e richieste da rinviare a un professionista. Il catalogo non fa routing di linguaggio naturale e non invoca strumenti.

## Investment Opportunity

Test mirati e integrazione CLI:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_investment_opportunity
```

Smoke CLI:

```text
fo planning investment-opportunity demo
```

Il contratto `investment-opportunity/v1` viene verificato con fixture sintetiche per immobile a reddito e asset mobile noleggiabile, cash flow zero e negativo, valore residuo, costo del tempo del proprietario, separazione del beneficio d'uso personale, gap delle assunzioni e hash riproducibile.

## Real-estate investment V2

Test mirati e smoke CLI:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_real_estate_investment
fo planning real-estate-investment demo
```

I test verificano modelli long-term, short-term e mixed-use, vacancy, commissione di gestione, maintenance shock, giorni di uso personale, costi/valore di uscita e il gap della classificazione fiscale. Il calcolo riusa `investment-opportunity/v1`; la fiscalità non viene dedotta.

## Work-transition readiness

Test mirati e integrazione CLI:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_work_transition_readiness tests.unit.test_work_transition_readiness_cli
```

Smoke CLI:

```text
fo planning work-transition readiness --demo
```

Output personale previsto:

```text
..\family-office-workspace\snapshots\work-transition-readiness.snapshot.json
```

Il contratto `work-transition-readiness/v1` verifica freshness, precedence, provenance, gross/net, periodi, bounds degli stream, liquidita' e doppio conteggio. Il comando produce sempre il report diagnostico; un blocker imposta `optimization_allowed=false` e impedisce ai successivi incrementi Work Transition di emettere date apparenti.

## Work-transition scenario

Test mirati e integrazione CLI:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_work_transition_scenario tests.unit.test_work_transition_scenario_cli
```

Smoke CLI:

```text
fo planning work-transition scenario --demo
```

Output personale previsto:

```text
..\family-office-workspace\snapshots\work-transition-scenario.snapshot.json
```

Il contratto `work-transition-scenario/v1` costruisce timeline mensili FTE per adulto da una readiness non bloccata. I test coprono 100% -> 60% -> 0%, piu' livelli part-time, due adulti, readiness bloccata, sovrapposizioni, gap non dichiarati, durate invalide, granularita' non mensile e separazione tra uscita full-time, cessazione e date pensionistiche.
