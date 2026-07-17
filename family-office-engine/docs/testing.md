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
