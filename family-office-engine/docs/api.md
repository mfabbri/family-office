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
