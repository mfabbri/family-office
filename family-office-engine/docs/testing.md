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

Lo snapshot risultante viene scritto in:

```text
..\family-office-workspace\snapshots\asset-availability.snapshot.json
```

Il file reale privato atteso e':

```text
..\family-office-workspace\household\asset-availability.json
```

Il repository workspace contiene un draft vuoto in `household/asset-availability.draft.json` e una guida compilabile in `household/household-input-guide.md`.

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

Il contratto `liquidity-plan/v1` assegna asset valorizzati a riserva, breve, medio, lungo termine e restricted usando net worth, asset availability e planning goals. I test coprono shortfall di riserva, asset bloccati per spese correnti, valuta estera senza conversione e senza funding della riserva, concentrazione, hash stabile e input mancanti. Non vengono calcolati rendimenti, imposte, cambi valuta, ottimizzazioni, scoring o raccomandazioni.

## Decumulation Strategy

Verifica contratto strategie di decumulo V4 con fixture sintetiche:

```text
$env:PYTHONPATH='src'; python -m unittest tests.unit.test_decumulation_strategy
```

Verifica CLI sul workspace privato:

```text
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

Il contratto `decumulation-strategy/v1` confronta policy dichiarate usando net worth, liquidity plan, pension income e RITA options. I test coprono piu' eta' di pensionamento, sequenza rendimenti, longevita', RITA si'/no, hash stabile e input mancanti. Non vengono calcolati fiscalita' normativa, rendimenti attesi, cambi valuta, ottimizzazioni o raccomandazioni.

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
