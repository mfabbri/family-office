# CLI

## `fo payroll import`

Importa buste paga PDF dal workspace privato e scrive:

```text
../family-office-workspace/snapshots/payroll.snapshot.json
```

Uso:

```text
python -m family_office_engine.cli.main payroll import
```

Default input:

- `../family-office-workspace/documents/redditi/buste-paga`, se esiste;
- altrimenti `../family-office-workspace/inbox/bustepaga`.

L'output console riporta stato, numero record, numero documenti e gap. Lo snapshot contiene i valori estratti dal cedolino; il comando non calcola imposte o netto da lordo.

## `fo payroll diagnose`

Diagnostica i documenti payroll letti dal comando senza scrivere snapshot.

Uso:

```text
python -m family_office_engine.cli.main payroll diagnose
```

Output atteso:

```text
payroll diagnostics: extracted
input: ...
summary: 1 documents, 1 records, 0 gaps
document: ... status=extracted records=1 gaps=-
next: Payroll input is ready for import.
```

Per ottenere il contratto diagnostico completo:

```text
python -m family_office_engine.cli.main payroll diagnose --json
```

La diagnostica non stampa importi personali nell'output sintetico.

## `fo tax calculate`

Calcola un'imposta progressiva usando un rule pack JSON versionato.

Uso con rule pack IRPEF nazionale 2026:

```text
python -m family_office_engine.cli.main tax calculate --taxable-income 60000.00
```

Default:

- rule pack: `../family-office-rules/italy/2026/irpef-national.json`
- anno fiscale: `2026`
- giurisdizione: `IT`
- output: `../family-office-workspace/snapshots/tax-calculation.snapshot.json`

Il default calcola solo IRPEF nazionale lorda su imponibile gia' determinato. Non calcola detrazioni, trattamento integrativo, addizionali regionali o comunali, crediti, acconti o risultato dichiarativo completo.

Lo snapshot `tax-calculation/v1` include importo imponibile, imposta calcolata, tranche applicate, rule ID, periodo di validita', fonti e limitazioni del rule pack. Se anno o giurisdizione non sono coperti dal rule pack, lo stato e' `blocked_missing_rule`.

Uso con fixture sintetica di runtime:

```text
python -m family_office_engine.cli.main tax calculate --rule-pack ../family-office-rules/tests/fixtures/synthetic-progressive-tax.json --jurisdiction SYNTH --taxable-income 45000.00
```

La giurisdizione `SYNTH` e' solo una fixture tecnica per testare il runtime. Non rappresenta aliquote IRPEF, addizionali o regole fiscali reali.

## `fo rita optimize`

Costruisce uno snapshot `rita-options/v1` usando input espliciti e il rule pack RITA corrente.

Uso:

```text
python -m family_office_engine.cli.main rita optimize --age 62 --years-to-public-pension 4 --employment-status ceased --mandatory-contribution-years 32 --complementary-pension-years 8 --complementary-balance 120000.00 --duration-months 48 --monthly-need 3000.00
```

Default:

- rule pack: `../family-office-rules/italy/current/rita.yaml`
- output: `../family-office-workspace/snapshots/rita-options.snapshot.json`

Il comando verifica solo requisiti minimi deterministici e calcola un'opzione lorda lineare. Non calcola pensione pubblica, tassazione RITA, rendimenti, costi o vincoli del singolo fondo.

## `fo estate baseline`

Costruisce uno snapshot `estate-baseline/v1` da `net-worth.snapshot.json` e input familiari espliciti.

Uso:

```text
python -m family_office_engine.cli.main estate baseline --has-spouse --children-count 2 --prior-donations 0.00
```

Default:

- net worth: `../family-office-workspace/snapshots/net-worth.snapshot.json`
- rule pack: `../family-office-rules/succession/italy-current.json`
- output: `../family-office-workspace/snapshots/estate-baseline.snapshot.json`

Il comando calcola quote teoriche solo per casi semplici con coniuge e/o figli e solo su componenti con quota di titolarita' esplicita. Polizze, fondi pensione, asset esteri, testamento, debiti, imposte, donazioni non documentate e verifica notarile restano gap o limiti espliciti.

## `fo household validate`

Valida e normalizza un file privato `household-facts/v1`.

Uso:

```text
python -m family_office_engine.cli.main household validate
```

Default:

- input: `../family-office-workspace/household/household-facts.json`
- output: `../family-office-workspace/snapshots/household-facts.snapshot.json`

Per testare il contratto senza dati reali:

```text
python -m family_office_engine.cli.main household validate --input examples/household-facts-sample.json
```

Il comando controlla ID duplicati, riferimenti a persone inesistenti, date, periodi, residenze fiscali e ruoli economici. Non crea facts sintetici se il file reale manca.

## `fo household ownership validate`

Valida e normalizza un file privato `ownership-beneficiary-graph/v1`.

Uso:

```text
python -m family_office_engine.cli.main household ownership validate
```

Default:

- input: `../family-office-workspace/household/ownership-beneficiaries.json`
- household snapshot: `../family-office-workspace/snapshots/household-facts.snapshot.json`
- output: `../family-office-workspace/snapshots/ownership-beneficiary-graph.snapshot.json`

Per testare il contratto senza dati reali:

```text
python -m family_office_engine.cli.main household ownership validate --input examples/ownership-beneficiary-graph-sample.json
```

Il comando controlla asset, debiti, quote, beneficiari, periodi, provenance e riferimenti a persone quando lo snapshot household e' disponibile. Non classifica liquidita', tassazione o rischio degli asset e non calcola successioni.

## `fo household availability validate`

Valida e normalizza un file privato `asset-availability/v1`.

Uso:

```text
python -m family_office_engine.cli.main household availability validate
```

Default:

- input: `../family-office-workspace/household/asset-availability.json`
- ownership snapshot: `../family-office-workspace/snapshots/ownership-beneficiary-graph.snapshot.json`
- output: `../family-office-workspace/snapshots/asset-availability.snapshot.json`

Per testare il contratto senza dati reali:

```text
python -m family_office_engine.cli.main household availability validate --input examples/asset-availability-sample.json
```

Il comando controlla asset class, rischio, valuta, giurisdizione, liquidita', vincoli, trattamento fiscale dichiarativo, prima data di disponibilita', provenance e riferimenti ad asset quando lo snapshot ownership e' disponibile. Non calcola imposte, rendimenti o raccomandazioni.

## `fo household timeline validate`

Valida e normalizza un file privato `timeline-events/v1`.

Uso:

```text
python -m family_office_engine.cli.main household timeline validate
```

Default:

- input: `../family-office-workspace/household/timeline-events.json`
- policy: `../family-office-rules/timeline/default-overlap-policy.json`
- household snapshot: `../family-office-workspace/snapshots/household-facts.snapshot.json`
- asset availability snapshot: `../family-office-workspace/snapshots/asset-availability.snapshot.json`
- output: `../family-office-workspace/snapshots/timeline-events.snapshot.json`

Per testare il contratto senza dati reali:

```text
python -m family_office_engine.cli.main household timeline validate --input examples/timeline-events-sample.json
```

Il comando controlla eventi puntuali, periodi, ricorrenze, date, priorita', conflitti tecnici, provenance e riferimenti a persone o asset quando gli snapshot sono disponibili. Non calcola importi, imposte, diritti pensionistici o raccomandazioni.

## `fo pension import-spain`

Importa documenti previdenziali spagnoli classificati nel workspace privato e scrive:

```text
../family-office-workspace/snapshots/spanish-contribution-history.snapshot.json
```

Uso:

```text
python -m family_office_engine.cli.main pension import-spain
```

Default input:

- `../family-office-workspace/documents/pensione/spagna`, se esiste;
- altrimenti `../family-office-workspace/inbox/pensione/spagna`.

Il comando supporta PDF testuali, TXT e CSV semplici. Lo snapshot `spanish-contribution-history/v1` registra periodi da Vida Laboral, basi mensili da Informe de bases de cotizacion o CSV, e basi da nominas come fonte integrativa. Documenti duplicati, non leggibili e mesi senza base diventano gap espliciti. Non calcola pensione spagnola, diritti, base reguladora, coordinamento UE o fiscalita'.

## `fo pension reconcile-spain`

Riconcilia lo snapshot spagnolo importato e scrive:

```text
../family-office-workspace/snapshots/spanish-contribution-reconciliation.snapshot.json
```

Uso:

```text
python -m family_office_engine.cli.main pension reconcile-spain
```

Default:

- input: `../family-office-workspace/snapshots/spanish-contribution-history.snapshot.json`
- output: `../family-office-workspace/snapshots/spanish-contribution-reconciliation.snapshot.json`

Il comando produce una griglia mensile con copertura Vida Laboral, basi ufficiali, basi da nomina, fonte selezionata, gap e anomalie. Le basi ufficiali prevalgono sulle nominas; differenze e duplicati restano visibili. Non calcola pensione spagnola, base reguladora, diritto, coordinamento UE o fiscalita'.

## `fo pension estimate-spain`

Stima la pensione ordinaria pubblica spagnola lorda da basi contributive riconciliate e rule pack versionato:

```text
../family-office-workspace/snapshots/spanish-statutory-pension.snapshot.json
```

Uso:

```text
python -m family_office_engine.cli.main pension estimate-spain --retirement-year 2026
```

Default:

- input: `../family-office-workspace/snapshots/spanish-contribution-reconciliation.snapshot.json`
- rule pack: `../family-office-rules/spain/statutory-retirement-general.json`
- output: `../family-office-workspace/snapshots/spanish-statutory-pension.snapshot.json`

Il comando calcola solo lo scenario ordinario. Usa basi ufficiali selezionate dalla riconciliazione, parametri base reguladora, percentuale maturata e 14 paghe annue codificate nel rule pack. Se mancano basi sufficienti o requisiti minimi, scrive `blocked_missing_inputs` senza inventare importi. Non calcola anticipo, differimento, caps, fiscalita', supplementi, rivalutazione basi, integrazione lagune o coordinamento UE.

## `fo pension coordinate-it-es`

Costruisce un dossier di coordinamento pensionistico UE Italia-Spagna:

```text
../family-office-workspace/snapshots/eu-pension-coordination-it-es.snapshot.json
```

Uso:

```text
python -m family_office_engine.cli.main pension coordinate-it-es --italian-contribution-months 240
```

Default:

- INPS: `../family-office-workspace/snapshots/inps-pension.snapshot.json`
- Spagna: `../family-office-workspace/snapshots/spanish-statutory-pension.snapshot.json`
- rule pack: `../family-office-rules/cross-border/eu-pension-coordination-it-es.json`
- output: `../family-office-workspace/snapshots/eu-pension-coordination-it-es.snapshot.json`

Il comando mantiene separate le prestazioni nazionali e usa i periodi normalizzati solo per diagnostica di totalizzazione/pro-rata. Se i mesi italiani normalizzati non sono disponibili, produce un gap invece di convertire automaticamente settimane INPS in mesi. Non calcola P1 ufficiale, pensione INPS normativa, fiscalita', netto o trasferimenti di contributi.

## `fo pension compose-income`

Compone i flussi pensionistici disponibili in uno snapshot unico:

```text
../family-office-workspace/snapshots/pension-income.snapshot.json
```

Uso:

```text
python -m family_office_engine.cli.main pension compose-income
```

Default:

- INPS: `../family-office-workspace/snapshots/inps-pension.snapshot.json`
- Spagna: `../family-office-workspace/snapshots/spanish-statutory-pension.snapshot.json`
- RITA: `../family-office-workspace/snapshots/rita-options.snapshot.json`
- coordinamento UE: `../family-office-workspace/snapshots/eu-pension-coordination-it-es.snapshot.json`
- output: `../family-office-workspace/snapshots/pension-income.snapshot.json`

Il comando mantiene separati flussi documentali, stime interne e opzioni. Il riepilogo somma solo importi lordi annuali ricorrenti, espliciti e in EUR; non calcola netto, imposte, annualizzazioni mancanti o pensioni normative.

Per escludere le opzioni RITA:

```text
python -m family_office_engine.cli.main pension compose-income --no-rita
```

## `fo expenses build-lifecycle`

Costruisce un cashflow annuo di spese da un piano esplicito:

```text
../family-office-workspace/snapshots/lifecycle-expenses.snapshot.json
```

Uso:

```text
python -m family_office_engine.cli.main expenses build-lifecycle
```

Default:

- input: `../family-office-workspace/household/lifecycle-expenses.json`
- household snapshot: `../family-office-workspace/snapshots/household-facts.snapshot.json`
- timeline snapshot: `../family-office-workspace/snapshots/timeline-events.snapshot.json`
- output: `../family-office-workspace/snapshots/lifecycle-expenses.snapshot.json`

Il comando annualizza solo spese dichiarate nel piano, con importi EUR e inflazione esplicita. Non stima budget mancanti, fiscalita', costi sanitari, rendimenti o raccomandazioni.

## `fo scenarios compose-v2`

Compone un artefatto scenario V2 deterministico:

```text
../family-office-workspace/snapshots/decision-scenario-v2.snapshot.json
```

Uso:

```text
python -m family_office_engine.cli.main scenarios compose-v2
```

Default:

- input: `../family-office-workspace/scenarios/decision-scenario-v2.json`
- household: `../family-office-workspace/snapshots/household-facts.snapshot.json`
- ownership: `../family-office-workspace/snapshots/ownership-beneficiary-graph.snapshot.json`
- asset availability: `../family-office-workspace/snapshots/asset-availability.snapshot.json`
- timeline: `../family-office-workspace/snapshots/timeline-events.snapshot.json`
- pension income: `../family-office-workspace/snapshots/pension-income.snapshot.json`
- lifecycle expenses: `../family-office-workspace/snapshots/lifecycle-expenses.snapshot.json`
- output: `../family-office-workspace/snapshots/decision-scenario-v2.snapshot.json`

Il comando raccoglie riferimenti, summary, assunzioni esplicite, obiettivi e gap in `decision-scenario/v2`. Non esegue Monte Carlo, sensitivity, scoring, fiscalita', rendimenti o raccomandazioni.

## `fo scenarios evaluate`

Esegue il primo evaluator deterministico registrato e produce:

```text
../family-office-workspace/snapshots/decision-outcome.snapshot.json
```

Uso:

```text
python -m family_office_engine.cli.main scenarios evaluate
```

Default:

- decision scenario: `../family-office-workspace/snapshots/decision-scenario-v2.snapshot.json`
- configurazione outcome: `../family-office-workspace/scenarios/decision-outcome.json`
- output: `../family-office-workspace/snapshots/decision-outcome.snapshot.json`

`retirement-monte-carlo/v1` usa solo input espliciti gia' inclusi nelle assunzioni dello scenario e registra evaluator, versione, parametri, seed, hash e provenance per ogni metrica. Se gli input richiesti mancano, il comando scrive un outcome `blocked_missing_inputs`; non legge snapshot esterni implicitamente e non inventa metriche.

## `fo scenarios sensitivity`

Costruisce uno snapshot di sensitivities e stress matrix sopra uno scenario V2:

```text
../family-office-workspace/snapshots/sensitivity-analysis.snapshot.json
```

Uso:

```text
python -m family_office_engine.cli.main scenarios sensitivity
```

Default:

- decision scenario: `../family-office-workspace/snapshots/decision-scenario-v2.snapshot.json`
- input sensitivities: `../family-office-workspace/scenarios/sensitivity-analysis.json`
- output: `../family-office-workspace/snapshots/sensitivity-analysis.snapshot.json`

Il comando applica perturbazioni esplicite alle assunzioni di `decision-scenario/v2`. Quando `scenarios/sensitivity-analysis.json` contiene `outcome_evaluation`, riesegue `retirement-monte-carlo/v1` con gli stessi parametri e seed per baseline, casi isolati e stress combinati; produce outcome, delta metriche e tornado ordinato per la metrica di impatto dichiarata.

Senza `outcome_evaluation` mantiene il comportamento legacy basato sulla sola magnitudine della perturbazione. Evaluator bloccati diventano gap espliciti; il comando non inventa metriche e non calcola fiscalita', diritti pensionistici, scoring o raccomandazioni.

## `fo scenarios score`

Costruisce uno snapshot di scoring multi-obiettivo:

```text
../family-office-workspace/snapshots/decision-score.snapshot.json
```

Uso:

```text
python -m family_office_engine.cli.main scenarios score
```

Default:

- decision scenario: `../family-office-workspace/snapshots/decision-scenario-v2.snapshot.json`
- sensitivity analysis: `../family-office-workspace/snapshots/sensitivity-analysis.snapshot.json`
- input scoring: `../family-office-workspace/scenarios/decision-score.json`
- policy: `../family-office-rules/decision/score-policy-v1.json`
- output: `../family-office-workspace/snapshots/decision-score.snapshot.json`

Il comando produce `decision-score/v1` applicando pesi espliciti a metriche risolte da outcome deterministici presenti in `sensitivity-analysis/v1`. Ogni alternativa deve dichiarare `outcome_ref` e ogni metrica deve dichiarare `outcome_metric_id`; metriche manuali prive di lineage diventano gap bloccanti. Non calcola le metriche sottostanti, imposte, rendimenti, pensioni, ottimizzazioni o raccomandazioni.

## `fo scenarios dossier`

Costruisce uno snapshot dossier e un report Markdown:

```text
../family-office-workspace/snapshots/decision-dossier.snapshot.json
../family-office-workspace/reports/decision-dossier.md
```

Uso:

```text
python -m family_office_engine.cli.main scenarios dossier
```

Default:

- decision scenario: `../family-office-workspace/snapshots/decision-scenario-v2.snapshot.json`
- sensitivity analysis: `../family-office-workspace/snapshots/sensitivity-analysis.snapshot.json`
- decision score: `../family-office-workspace/snapshots/decision-score.snapshot.json`
- input dossier: `../family-office-workspace/scenarios/decision-dossier.json`
- output snapshot: `../family-office-workspace/snapshots/decision-dossier.snapshot.json`
- output Markdown: `../family-office-workspace/reports/decision-dossier.md`

Il comando produce `decision-dossier/v1` e blocca la raccomandazione se score, ranking, lineage delle metriche o gap bloccanti non consentono una revisione solida. Non calcola nuove metriche, imposte, rendimenti, pensioni, ottimizzazioni o raccomandazioni AI.

## `fo planning goals validate`

Valida e normalizza obiettivi e vincoli patrimoniali V4:

```text
../family-office-workspace/snapshots/planning-goals.snapshot.json
```

Uso:

```text
python -m family_office_engine.cli.main planning goals validate
```

Default:

- input: `../family-office-workspace/household/planning-goals.json`
- timeline: `../family-office-workspace/snapshots/timeline-events.snapshot.json`
- output: `../family-office-workspace/snapshots/planning-goals.snapshot.json`

Il comando produce `planning-goals/v1` con obiettivi, priorita', soglie, orizzonte, rischio, liquidita' e vincoli dichiarati. Valida riferimenti a obiettivi e, se la timeline e' disponibile, riferimenti a eventi. Non calcola rendimenti, imposte, ottimizzazioni, trade-off o raccomandazioni.

## `fo retirement simulate`

Esegue la simulazione pensionamento deterministica.

Uso con reddito pensionistico composto:

```text
python -m family_office_engine.cli.main retirement simulate --pension-income-snapshot ../family-office-workspace/snapshots/pension-income.snapshot.json
```

Quando `--pension-income-snapshot` e' passato, il simulatore usa solo `gross_annual_recurring_total` come offset lordo annuo dei prelievi post-pensionamento. Il comando non calcola netto, imposte o decorrenze mensili.

## `fo tax reconcile`

Riconcilia `payroll.snapshot.json` e `tax-documents.snapshot.json` senza calcolare imposte.

Uso:

```text
python -m family_office_engine.cli.main tax reconcile
```

Default:

- payroll: `../family-office-workspace/snapshots/payroll.snapshot.json`
- documenti fiscali: `../family-office-workspace/snapshots/tax-documents.snapshot.json`
- output: `../family-office-workspace/snapshots/tax-reconciliation.snapshot.json`

Lo snapshot `tax-reconciliation/v1` segnala anni coperti, anni non allineati, duplicati payroll esclusi e campi disponibili da CU/dichiarazione.

## `fo tax-documents diagnose`

Diagnostica CU e dichiarazioni dei redditi classificate senza scrivere snapshot.

Uso:

```text
python -m family_office_engine.cli.main tax-documents diagnose
```

Default input:

- CU: `../family-office-workspace/documents/redditi/cu`, se esiste; altrimenti `../family-office-workspace/inbox/cu`
- dichiarazioni: `../family-office-workspace/documents/dichiarazioni`, se esiste; altrimenti `../family-office-workspace/inbox/dichiarazioni`

L'output sintetico mostra solo path, conteggi, stati documento e gap, non importi personali.

## `fo tax-documents import`

Importa CU e dichiarazioni dei redditi PDF dal workspace privato e scrive:

```text
../family-office-workspace/snapshots/tax-documents.snapshot.json
```

Uso:

```text
python -m family_office_engine.cli.main tax-documents import
```

Lo snapshot `tax-documents/v1` registra document type, anno/modello e campi fiscali riconosciuti con provenance. Non calcola IRPEF, addizionali, detrazioni o conguagli.
