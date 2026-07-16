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
