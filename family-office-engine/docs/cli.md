# CLI

Guida generale e ordine d'uso: `docs/cli-workflow.md`.

Mappa degli input JSON compilabili: `docs/json-input-guides.md`.

Gate Work Transition e manifest sorgenti: `docs/work-transition-readiness.md`.

Scenario mensile Work Transition: `docs/work-transition-scenario.md`.

La CLI utente e' `fo`. Installarla una volta dal repository engine:

```powershell
cd family-office-engine
.\.venv\Scripts\python -m pip install -e .
```

Uso normale:

```powershell
fo validate
fo planning goals wizard
```

Dalla root del progetto sono disponibili anche wrapper locali, ad esempio `.\fo.ps1 validate`. I comandi `python -m family_office_engine.cli.main ...` sono fallback tecnici da checkout sorgente, non il percorso operativo preferito. Le procedure utente devono documentare prima il percorso `fo ...`, usando default del workspace, wizard e comandi senza path JSON.

PowerShell non esegue comandi dalla cartella corrente con il solo nome. Per usare `fo` senza prefisso `.\`, prepara la sessione dalla root:

```powershell
. .\use-family-office.ps1
fo validate
```

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

## `fo investments import`

Importa rendiconti investimento PDF classificati nel workspace privato e scrive:

```text
../family-office-workspace/snapshots/investments.snapshot.json
```

Uso:

```text
python -m family_office_engine.cli.main investments import
```

Default input:

- Italia: `../family-office-workspace/documents/investimenti/italia`
- Spagna: `../family-office-workspace/documents/investimenti/spagna`
- Directa: `../family-office-workspace/documents/investimenti/directa`

Il parser supporta formati deterministici per Amundi, Moneyfarm, Kutxabank, Consultinvest e Directa. Per PDF con testo custom-encoded, come alcuni rendiconti Consultinvest, usa un fallback sul content stream PDF e sulle mappe ToUnicode quando PyPDF2 non riesce a estrarre testo standard. Lo snapshot registra provider, tipo strumento, data rendiconto, valore, valuta e provenance; non stima valori mancanti e non calcola imposte, performance o raccomandazioni.

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
fo household availability validate
```

Wizard da net worth:

```text
fo household availability wizard
```

Rivedere classificazioni gia' inserite:

```text
fo household availability wizard --overwrite
```

Validare per il piano liquidita' quando gli asset arrivano dal net worth e non sono ancora allineati al grafo ownership:

```text
fo household availability validate --skip-ownership-check
```

Default:

- input: `../family-office-workspace/household/asset-availability.json`
- net worth per wizard: `../family-office-workspace/snapshots/net-worth.snapshot.json`
- ownership snapshot: `../family-office-workspace/snapshots/ownership-beneficiary-graph.snapshot.json`
- output: `../family-office-workspace/snapshots/asset-availability.snapshot.json`

Per testare il contratto senza dati reali:

```text
python -m family_office_engine.cli.main household availability validate --input examples/asset-availability-sample.json
```

Il comando controlla asset class, rischio, valuta, giurisdizione, liquidita', vincoli, trattamento fiscale dichiarativo, prima data di disponibilita', provenance e riferimenti ad asset quando lo snapshot ownership e' disponibile. Se stai classificando asset generati dal net worth prima di aggiornare ownership, usa `--skip-ownership-check`. Il wizard parte dagli asset nel net worth, propone default conservativi per classe asset, salva progressivamente dopo ogni asset e scrive l'input privato; con `--overwrite` permette di rivedere classificazioni gia' inserite. Valida subito paese e data, e per asset bloccati o incerti la prima data di disponibilita' puo' essere `unknown`, che resta un gap esplicito. Non calcola imposte, rendimenti o raccomandazioni.

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
fo pension import-spain
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
fo pension reconcile-spain
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
fo pension estimate-spain --retirement-year 2026
```

Per il caso misto Italia-Spagna in cui il diritto spagnolo nasce da totalizzazione UE e la pensione autonoma spagnola non e' calcolabile, non usare `estimate-spain` come percorso principale. Usa invece il flusso guidato `fo planning it-es-eu-pension wizard`, `fo planning spanish-eu-theoretical-pension build`, `fo planning it-es-eu-pension build`.

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
fo pension coordinate-it-es --italian-contribution-months 240
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
fo pension compose-income
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
fo pension compose-income --no-rita
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
fo planning goals status
fo planning goals validate
```

Se l'input privato non esiste ancora, preparalo dal draft del workspace:

```text
fo planning goals prepare
```

In alternativa puoi creare il JSON con domande guidate:

```text
fo planning goals wizard
```

`status` non modifica file e mostra il punto del workflow: input mancante, draft ancora da compilare, input pronto o snapshot gia' presente. Il draft contiene `draft_notes` e `draft_examples` per spiegare i campi e i valori ammessi; queste sezioni sono guida umana e possono restare nel file durante la compilazione.

`wizard` pone domande deterministiche, scrive il JSON privato e lo valida a livello di contratto input. Se l'input esiste gia', non richiede di reinserire dati: suggerisce il comando successivo o `--overwrite` per rivederlo usando i valori esistenti come default. Durante la compilazione salva progressivamente le risposte, cosi' un'interruzione puo' essere ripresa con `fo planning goals wizard --overwrite`. Il fabbisogno pensionistico viene derivato da spesa netta mensile corrente e crescita annua dichiarata del costo della vita; se disponibile, la spesa mensile gia' inserita in `liquidity-plan-input/v1` viene proposta come default. Le risposte lasciate incerte restano tracciate in `data_gaps`; non calcola rendimenti, imposte, ottimizzazioni o raccomandazioni.

Da checkout sorgente:

```text
python -m family_office_engine.cli.main planning goals validate
```

Demo sintetica senza path JSON:

```text
fo planning goals demo
```

Da checkout sorgente:

```text
python -m family_office_engine.cli.main planning goals demo
```

Default:

- input: `../family-office-workspace/household/planning-goals.json`
- timeline: `../family-office-workspace/snapshots/timeline-events.snapshot.json`
- output: `../family-office-workspace/snapshots/planning-goals.snapshot.json`
- draft prepare: `../family-office-workspace/household/planning-goals.draft.json`

Default demo:

- timeline sintetica: `../family-office-workspace/snapshots/cli-check-timeline-events.synthetic.snapshot.json`
- output sintetico: `../family-office-workspace/snapshots/cli-check-planning-goals.synthetic.snapshot.json`

Il comando produce `planning-goals/v1` con obiettivi, priorita', soglie, orizzonte, rischio, liquidita' e vincoli dichiarati. Valida riferimenti a obiettivi e, se la timeline e' disponibile, riferimenti a eventi. Non calcola rendimenti, imposte, ottimizzazioni, trade-off o raccomandazioni.

## `fo planning liquidity build`

Costruisce il piano bucket di liquidita' V4:

```text
../family-office-workspace/snapshots/liquidity-plan.snapshot.json
```

Uso:

```text
fo planning liquidity build
```

Spiegazione dello snapshot gia' costruito:

```text
fo planning liquidity explain
```

Wizard interattivo input:

```text
fo planning liquidity wizard
```

Da checkout sorgente:

```text
python -m family_office_engine.cli.main planning liquidity build
```

Demo sintetica senza path JSON:

```text
fo planning liquidity demo
```

Da checkout sorgente:

```text
python -m family_office_engine.cli.main planning liquidity demo
```

Default:

- input: `../family-office-workspace/planning/liquidity-plan-input.json`
- net worth: `../family-office-workspace/snapshots/net-worth.snapshot.json`
- asset availability: `../family-office-workspace/snapshots/asset-availability.snapshot.json`
- planning goals: `../family-office-workspace/snapshots/planning-goals.snapshot.json`
- output: `../family-office-workspace/snapshots/liquidity-plan.snapshot.json`

Guida alla compilazione:

- `examples/liquidity-plan-input-guide.md`
- bozza privata: `../family-office-workspace/planning/liquidity-plan-input.draft.json`

Default demo:

- input sintetico: `examples/liquidity-plan-input-sample.json`
- net worth sintetico: `examples/liquidity-plan-net-worth-sample.json`
- asset availability sintetica: `examples/asset-availability-sample.json`
- output sintetico: `../family-office-workspace/snapshots/cli-check-liquidity-plan.synthetic.snapshot.json`

Il comando produce `liquidity-plan/v1` con riserva minima, bucket asset, asset bloccati per spese correnti, warning e data gaps. Non converte valute e non calcola rendimenti, imposte, ottimizzazioni, scoring o raccomandazioni.

L'output CLI mostra anche shortfall di riserva, numero di asset non usabili per spese correnti, bucket patrimoniali, primi gap e prossimo passo operativo.

`fo planning liquidity explain` legge lo snapshot esistente e traduce le assegnazioni asset per asset: quali sono utilizzabili, quali sono esclusi dalle spese correnti e quali vincoli o livelli di liquidabilita' hanno prodotto la classificazione.

`fo planning liquidity wizard` crea `liquidity-plan-input/v1` nel workspace e valida il JSON senza richiedere snapshot esterni. Se l'input esiste gia', non richiede di reinserire metadati tecnici come nucleo, data e valuta: li mostra come contesto e chiede solo spese mensili, mesi di riserva e soglia di concentrazione. Con `--overwrite` rimuove anche il placeholder `replace_with_known_gap_or_remove` se non viene sostituito da un gap reale.

## `fo planning decumulation build`

Confronta policy di decumulo pensionistico V4:

```text
../family-office-workspace/snapshots/decumulation-strategy.snapshot.json
```

Uso:

```text
fo planning decumulation build
```

Wizard interattivo policy:

```text
fo planning decumulation wizard
```

Da checkout sorgente:

```text
python -m family_office_engine.cli.main planning decumulation build
```

Demo sintetica senza path JSON:

```text
fo planning decumulation demo
```

Da checkout sorgente:

```text
python -m family_office_engine.cli.main planning decumulation demo
```

Default:

- input: `../family-office-workspace/planning/decumulation-policy-set.json`
- net worth: `../family-office-workspace/snapshots/net-worth.snapshot.json`
- liquidity plan: `../family-office-workspace/snapshots/liquidity-plan.snapshot.json`
- pension income: `../family-office-workspace/snapshots/pension-income.snapshot.json`
- RITA options: `../family-office-workspace/snapshots/rita-options.snapshot.json`
- output: `../family-office-workspace/snapshots/decumulation-strategy.snapshot.json`

Guida alla compilazione:

- `examples/decumulation-policy-set-guide.md`
- bozza privata: `../family-office-workspace/planning/decumulation-policy-set.draft.json`

Default demo:

- input sintetico: `examples/decumulation-policy-set-sample.json`
- net worth sintetico: `examples/decumulation-net-worth-sample.json`
- liquidity plan sintetico: `examples/decumulation-liquidity-plan-sample.json`
- pension income sintetico: `examples/decumulation-pension-income-sample.json`
- RITA options sintetico: `examples/decumulation-rita-options-sample.json`
- output sintetico: `../family-office-workspace/snapshots/cli-check-decumulation-strategy.synthetic.snapshot.json`

Il comando produce `decumulation-strategy/v1` con cashflow annui per policy, ranking tecnico, metriche nette, warning e data gaps. I tassi netti sono solo quelli dichiarati nell'input; non calcola fiscalita' normativa, rendimenti attesi, cambi valuta, ottimizzazioni o raccomandazioni.

`fo planning decumulation wizard` crea una prima policy esplicita `decumulation-policy-set/v1`. Usa goals e piano liquidita' gia salvati come contesto per nucleo, data, valuta, fabbisogno annuo, cuscinetto di liquidita' e asset prelevabili; chiede solo eta', orizzonte, ordine di prelievo e assunzioni esplicite su rendimenti/aliquote. Se un'aliquota non e' nota, lascia `0.00`: il wizard la salva come gap da stimare, non come ipotesi fiscale definitiva. Se l'input esiste gia', non richiede di reinserire dati e usa `--overwrite` solo per revisione esplicita. Salva progressivamente le risposte, cosi' un'interruzione puo' essere ripresa con `fo planning decumulation wizard --overwrite`. Asset, rendimenti e tassi restano assunzioni dichiarate dall'utente e vanno revisionati prima del build.

## `fo planning investment-opportunity build`

Costruisce `investment-opportunity/v1` da scenari di opportunita' generica:

```text
fo planning investment-opportunity build
fo planning investment-opportunity demo
```

Il default legge `../family-office-workspace/planning/investment-opportunity.json`
e scrive `../family-office-workspace/snapshots/investment-opportunity.snapshot.json`.

## `fo planning real-estate-investment build`

Costruisce `real-estate-investment/v2` per immobili a reddito con driver dichiarati:

```text
fo planning real-estate-investment build
fo planning real-estate-investment demo
```

Il contratto separa ricavi locativi, NOI, cash flow, tax drag e valore di uscita. Le classificazioni fiscali prive di input/regola versionata restano `data_gaps`; il comando non deduce aliquote, occupazione o valore dell’immobile.
Il core calcola solo acquisition basis, ricavi/costi operativi, NOI, free cash
flow annuale, costo del tempo proprietario e valore residuo espliciti. Il
beneficio di uso personale e' separato dal cash flow; fiscalita', classificazione
dell'attivita', financing, utilizzo e valori non dichiarati sono data gap o
competenza degli adapter/rule pack successivi.

## `fo planning rentable-movable-asset build`

Costruisce `rentable-movable-asset/v1` (incluso il caso camper) da driver di disponibilita', noleggio e costi dichiarati:

```text
fo planning rentable-movable-asset build
fo planning rentable-movable-asset demo
```

Il default legge `../family-office-workspace/planning/rentable-movable-asset.json` e scrive `../family-office-workspace/snapshots/rentable-movable-asset.snapshot.json`. Uso personale, ricavi da noleggio e trattamento fiscale restano distinti; una classificazione `personal`, `occasional_rental`, `habitual_rental` o `business` richiede input con fonte o resta un data gap.

## `fo planning financing-plan build`

Costruisce `financing-plan/v1` riusabile per immobili e asset mobili:

```text
fo planning financing-plan build
fo planning financing-plan demo
```

Il default legge `../family-office-workspace/planning/financing-plan.json` e scrive `../family-office-workspace/snapshots/financing-plan.snapshot.json`. Il comando calcola solo il piano del debito da tassi, fee e rimborsi dichiarati; mantiene separati cash flow dell'asset, cash flow dell'equity, interessi e capitale. LTV richiede un valore di garanzia esplicito, DSCR richiede NOI esplicito e un piano senza debito lo segnala come non applicabile.

## `fo planning pension-contributions build`

Confronta opzioni esplicite di contribuzione a previdenza complementare:

```text
../family-office-workspace/snapshots/pension-contribution-options.snapshot.json
```

Uso:

```text
fo planning pension-contributions build
```

Wizard interattivo input:

```text
fo planning pension-contributions wizard
```

Demo sintetica senza path JSON:

```text
fo planning pension-contributions demo
```

Da checkout sorgente:

```text
python -m family_office_engine.cli.main planning pension-contributions demo
```

Default:

- input: `../family-office-workspace/planning/pension-contribution-input.json`
- rule pack: `../family-office-rules/italy/2026/pension-contribution-deduction.json`
- output: `../family-office-workspace/snapshots/pension-contribution-options.snapshot.json`

Default demo:

- input sintetico: `examples/pension-contribution-input-sample.json`
- output sintetico: `../family-office-workspace/snapshots/cli-check-pension-contribution-options.synthetic.snapshot.json`

Il comando produce `pension-contribution-options/v1` con deducibilita', beneficio fiscale stimato da aliquota marginale dichiarata, costo opportunita', liquidita' persa, vincoli e ranking tecnico. Non calcola IRPEF completa, rendimenti, matching contrattuale non dichiarato o raccomandazioni.

`fo planning pension-contributions wizard` crea `pension-contribution-input/v1` usando il piano liquidita' gia salvato come contesto per data, liquidita' disponibile e cuscinetto minimo da preservare. Se aliquota marginale, contributi gia dedotti, extra deducibilita o costo opportunita' non sono noti, lascia `0.00`: il wizard li salva come gap da stimare, non come ipotesi definitiva.

## `fo planning tax-aware-portfolio build`

Confronta opzioni esplicite di portafoglio al netto di costi e fiscalita' finanziaria:

```text
../family-office-workspace/snapshots/tax-aware-portfolio.snapshot.json
```

Uso:

```text
fo planning tax-aware-portfolio build
```

Demo sintetica senza path JSON:

```text
fo planning tax-aware-portfolio demo
```

Da checkout sorgente:

```text
python -m family_office_engine.cli.main planning tax-aware-portfolio demo
```

Default:

- input: `../family-office-workspace/planning/tax-aware-portfolio-input.json`
- rule pack: `../family-office-rules/italy/2026/tax-aware-investment.json`
- output: `../family-office-workspace/snapshots/tax-aware-portfolio.snapshot.json`

Default demo:

- input sintetico: `examples/tax-aware-portfolio-input-sample.json`
- output sintetico: `../family-office-workspace/snapshots/cli-check-tax-aware-portfolio.synthetic.snapshot.json`

Il comando produce `tax-aware-portfolio/v1` con rendimento lordo esplicito, costi, imponibile realizzato, uso minusvalenze dichiarate, imposte 26%/12,5% secondo categoria documentata, bollo/IVAFE, fiscal drag, fiscalita' differita stimata e ranking tecnico. Non calcola rendimenti attesi, fiscalita' estera completa, dichiarazione, PIR, cripto-attivita' o raccomandazioni.

## `fo planning it-es-pension-tax classify`

Classifica il trattamento convenzionale Italia-Spagna degli stream pensionistici:

```text
../family-office-workspace/snapshots/it-es-pension-tax-classification.snapshot.json
```

Uso:

```text
fo planning it-es-pension-tax classify
```

Demo sintetica senza path JSON:

```text
fo planning it-es-pension-tax demo
```

Da checkout sorgente:

```text
python -m family_office_engine.cli.main planning it-es-pension-tax demo
```

Default:

- input: `../family-office-workspace/planning/it-es-pension-tax-classification-input.json`
- pension income: `../family-office-workspace/snapshots/pension-income.snapshot.json`
- rule pack: `../family-office-rules/cross-border/it-es-pension-tax-classification.json`
- output: `../family-office-workspace/snapshots/it-es-pension-tax-classification.snapshot.json`

Default demo:

- input sintetico: `examples/it-es-pension-tax-classification-input-sample.json`
- pension income sintetico: `examples/it-es-pension-income-sample.json`
- output sintetico: `../family-office-workspace/snapshots/cli-check-it-es-pension-tax-classification.synthetic.snapshot.json`

Il comando produce `it-es-pension-tax-classification/v1` con articolo convenzionale candidato, Stato con potesta' impositiva, ritenuta attesa qualitativa, documenti richiesti, warning e confidence. Non calcola netto, IRPEF, IRPF spagnola, credito per imposte estere, rimborsi o dichiarazione completa.

## `fo planning spanish-pension-net build`

Calcola un ponte lordo-netto per pensioni spagnole di residente fiscale italiano:

```text
../family-office-workspace/snapshots/spanish-pension-net-it-resident.snapshot.json
```

Uso:

```text
fo planning spanish-pension-net build
```

Demo sintetica senza path JSON:

```text
fo planning spanish-pension-net demo
```

Da checkout sorgente:

```text
python -m family_office_engine.cli.main planning spanish-pension-net demo
```

Default:

- input: `../family-office-workspace/planning/spanish-pension-net-it-resident-input.json`
- pension income: `../family-office-workspace/snapshots/pension-income.snapshot.json`
- classificazione: `../family-office-workspace/snapshots/it-es-pension-tax-classification.snapshot.json`
- rule pack netto: `../family-office-rules/cross-border/spanish-pension-net-it-resident.json`
- rule pack IRPEF: `../family-office-rules/italy/2026/irpef-national.json`
- output: `../family-office-workspace/snapshots/spanish-pension-net-it-resident.snapshot.json`

Default demo:

- input sintetico: `examples/spanish-pension-net-it-resident-input-sample.json`
- pension income sintetico: `examples/it-es-pension-income-sample.json`
- classificazione sintetica: `examples/spanish-pension-net-it-es-classification-sample.json`
- output sintetico: `../family-office-workspace/snapshots/cli-check-spanish-pension-net-it-resident.synthetic.snapshot.json`

Il comando produce `spanish-pension-net-it-resident/v1` con lordo, ritenuta spagnola dichiarata, IRPEF nazionale incrementale, credito art. 165 quando applicabile, netto, warning e confidence. Non calcola detrazioni, addizionali, acconti, rimborsi, imposte spagnole o dichiarazione completa.

## `fo planning it-es-foreign-assets build`

Classifica attivita' spagnole di residente fiscale italiano ai fini RW, IVAFE e IVIE:

```text
../family-office-workspace/snapshots/it-es-foreign-assets.snapshot.json
```

Uso:

```text
fo planning it-es-foreign-assets build
```

Demo sintetica senza path JSON:

```text
fo planning it-es-foreign-assets demo
```

Da checkout sorgente:

```text
python -m family_office_engine.cli.main planning it-es-foreign-assets demo
```

Default:

- input: `../family-office-workspace/planning/it-es-foreign-assets-input.json`
- rule pack: `../family-office-rules/cross-border/it-es-foreign-asset-monitoring-v2.json`
- output: `../family-office-workspace/snapshots/it-es-foreign-assets.snapshot.json`

Default demo:

- input sintetico: `examples/it-es-foreign-assets-input-sample.json`
- output sintetico: `../family-office-workspace/snapshots/cli-check-it-es-foreign-assets.synthetic.snapshot.json`

Il comando produce `it-es-foreign-assets/v1` con obbligo RW, categoria monitoraggio, documenti richiesti, IVAFE/IVIE calcolate da valori espliciti, tax events dichiarati, warning e data gaps. Non prepara la dichiarazione, non calcola imposte estere o redditi finanziari, non copre cripto-attivita' e non deduce esenzioni non documentate.

## `fo planning cross-border-it-es build`

Compone pensione, tassazione e monitoraggio patrimoniale Italia-Spagna:

```text
../family-office-workspace/snapshots/cross-border-it-es.snapshot.json
```

Uso:

```text
fo planning cross-border-it-es build
```

Demo sintetica senza path JSON:

```text
fo planning cross-border-it-es demo
```

Da checkout sorgente:

```text
python -m family_office_engine.cli.main planning cross-border-it-es demo
```

Default:

- scenario pensionistico: `../family-office-workspace/snapshots/pension-scenario.snapshot.json`
- pension income: `../family-office-workspace/snapshots/pension-income.snapshot.json`
- classificazione pensione: `../family-office-workspace/snapshots/it-es-pension-tax-classification.snapshot.json`
- netto pensione spagnola: `../family-office-workspace/snapshots/spanish-pension-net-it-resident.snapshot.json`
- quota pro-rata UE: `../family-office-workspace/snapshots/it-es-eu-pension-pro-rata.snapshot.json`
- asset esteri: `../family-office-workspace/snapshots/it-es-foreign-assets.snapshot.json`
- output: `../family-office-workspace/snapshots/cross-border-it-es.snapshot.json`

Default demo:

- scenario pensionistico sintetico: `examples/pension-scenario-snapshot-sample.json`
- pension income sintetico: `examples/it-es-pension-income-sample.json`
- classificazione sintetica: `examples/spanish-pension-net-it-es-classification-sample.json`
- netto sintetico: `examples/cross-border-spanish-pension-net-sample.json`
- pro-rata sintetico: `examples/cross-border-it-es-eu-pension-pro-rata-sample.json`
- asset sintetici: `examples/cross-border-it-es-foreign-assets-sample.json`
- output sintetico: `../family-office-workspace/snapshots/cli-check-cross-border-it-es.synthetic.snapshot.json`

Il comando produce `cross-border-it-es/v1` con scenario pensionistico selezionato, diritti previdenziali, tassazione pensionistica, monitoraggio asset, tax events, documenti richiesti, rischi e azioni operative. Non ricalcola pensioni, imposte, crediti, valori patrimoniali, dichiarazioni o raccomandazioni.

## `fo planning pension-scenario build`

Registra assunzioni pensionistiche Italia-Spagna esplicite:

```text
../family-office-workspace/snapshots/pension-scenario.snapshot.json
```

Uso:

```text
fo planning pension-scenario build
```

Demo sintetica senza path JSON:

```text
fo planning pension-scenario demo
```

Da checkout sorgente:

```text
python -m family_office_engine.cli.main planning pension-scenario demo
```

Default:

- input: `../family-office-workspace/planning/pension-scenario.json`
- output: `../family-office-workspace/snapshots/pension-scenario.snapshot.json`

Default demo:

- input sintetico: `examples/pension-scenario-sample.json`
- output sintetico: `../family-office-workspace/snapshots/cli-check-pension-scenario.synthetic.snapshot.json`

Il comando produce `pension-scenario/v1` con scenario selezionato, alternative, pensionamento, residenza iniziale, trasferimenti post-pensionamento, contributi futuri IT/ES, provenance e gap. Non calcola pensioni, basi contributive, imposte, netto, diritto UE, pro-rata o raccomandazioni.

## `fo planning real-estate build`

Confronta alternative immobiliari dichiarative:

```text
../family-office-workspace/snapshots/real-estate-plan.snapshot.json
```

Uso:

```text
fo planning real-estate build
```

Demo sintetica senza path JSON:

```text
fo planning real-estate demo
```

Da checkout sorgente:

```text
python -m family_office_engine.cli.main planning real-estate demo
```

Default:

- input: `../family-office-workspace/planning/real-estate-plan.json`
- output: `../family-office-workspace/snapshots/real-estate-plan.snapshot.json`

Default demo:

- input sintetico: `examples/real-estate-plan-sample.json`
- output sintetico: `../family-office-workspace/snapshots/cli-check-real-estate-plan.synthetic.snapshot.json`

Il comando produce `real-estate-plan/v1` con immobili, quote di titolarita', costi, imposte dichiarate, vacancy, locazione, vendita, alternative `hold`/`rent`/`sell`, liquidita', provenance e gap. Non calcola imposte normative, successione, perizie, finanziamenti, FX, dichiarazioni o raccomandazioni.

## `fo planning protection build`

Confronta fabbisogni familiari e polizze assicurative dichiarative:

```text
../family-office-workspace/snapshots/protection-gap.snapshot.json
```

Uso:

```text
fo planning protection build
```

Demo sintetica senza path JSON:

```text
fo planning protection demo
```

Da checkout sorgente:

```text
python -m family_office_engine.cli.main planning protection demo
```

Default:

- input: `../family-office-workspace/planning/protection-gap.json`
- output: `../family-office-workspace/snapshots/protection-gap.snapshot.json`

Default demo:

- input sintetico: `examples/protection-gap-sample.json`
- output sintetico: `../family-office-workspace/snapshots/cli-check-protection-gap.synthetic.snapshot.json`

Il comando produce `protection-gap/v1` con fabbisogni familiari, polizze rischio/inabilita'/miste/investimento, beneficiari, capitali assicurati, premi, riscatti, gap di protezione, provenance e data gap. Non calcola consulenza assicurativa, sanitaria, attuariale, legale, fiscale, underwriting, successione o raccomandazioni.

## `fo planning it-es-eu-pension build`

Stima diritto pensionistico spagnolo in coordinamento UE e quota pro-rata:

```text
../family-office-workspace/snapshots/it-es-eu-pension-pro-rata.snapshot.json
```

Uso ordinario per caso personale misto Italia-Spagna:

```text
fo planning it-es-eu-pension wizard
fo planning spanish-eu-theoretical-pension build
fo planning it-es-eu-pension build
```

Il build pro-rata usa automaticamente lo snapshot teorico di default se `fo planning spanish-eu-theoretical-pension build` lo ha prodotto. Non serve passare path JSON.

Demo sintetiche senza path JSON:

```text
fo planning spanish-eu-theoretical-pension demo
fo planning it-es-eu-pension demo
```

Prepara una bozza sintetica nel workspace privato:

```text
fo planning it-es-eu-pension prepare
```

Wizard per caso personale misto Italia-Spagna:

```text
fo planning it-es-eu-pension wizard
```

Demo sintetica senza path JSON:

```text
fo planning it-es-eu-pension demo
```

Default:

- input: `../family-office-workspace/planning/it-es-eu-pension-pro-rata-input.json`
- draft prepare: `../family-office-workspace/planning/it-es-eu-pension-pro-rata-input.draft.json`
- rule pack: `../family-office-rules/cross-border/eu-pension-coordination-it-es.json`
- output: `../family-office-workspace/snapshots/it-es-eu-pension-pro-rata.snapshot.json`
- importo teorico calcolato: `../family-office-workspace/snapshots/spanish-eu-theoretical-pension.snapshot.json`

Default demo:

- input sintetico: `examples/it-es-eu-pension-pro-rata-input-sample.json`
- input teorico sintetico: `examples/spanish-eu-theoretical-pension-pro-rata-input-sample.json`
- riconciliazione ES sintetica: `examples/spanish-eu-theoretical-pension-reconciliation-sample.json`
- output sintetico: `../family-office-workspace/snapshots/cli-check-it-es-eu-pension-pro-rata.synthetic.snapshot.json`

Il comando produce `it-es-eu-pension-pro-rata/v1` con data nascita, scenario pensionamento, anchor del requisito recente, periodi IT/ES datati, mesi non sovrapposti, diritto spagnolo autonomo e totalizzato, importo teorico spagnolo esplicito o calcolato con provenance solo spagnola, quota pro-rata, warning e data gaps. Non calcola pensione INPS normativa, fiscalita', netto, P1 ufficiale, basi spagnole da periodi italiani o contribuzione futura non dichiarata.

`fo planning spanish-eu-theoretical-pension build` produce `spanish-eu-theoretical-pension/v1` da input pro-rata, riconciliazione contributiva spagnola e rule pack `spanish-eu-theoretical-pension`. Per anni futuri non osservabili, come il 2039, usa solo assunzioni proiettive dichiarate nel rule pack e marca lo snapshot come `planning_projection_not_official_future_law`: e' una stima di pianificazione, non una regola ufficiale futura. Per mesi UE non spagnoli nella finestra di base usa solo la base spagnola reale piu' vicina nel tempo aggiornata con IPC ufficiale o proiettato; se IPC, basi ES o copertura mensile non sono disponibili, scrive data gaps. `fo planning it-es-eu-pension wizard` crea l'input personale guidato senza fixture sintetiche: propone i mesi spagnoli dalla riconciliazione disponibile, chiede mesi italiani normalizzati, mese di pensionamento, conferma esplicita di nessun contributo spagnolo futuro e importo teorico spagnolo da sole basi ES. Se l'importo teorico non e' noto, lo registra come data gap invece di inventarlo.

## `fo planning work-exit build` planned

Capability pianificata in V4.8c, non ancora disponibile nella CLI.

Obiettivo: trovare la prima data sostenibile per smettere di lavorare partendo da oggi, non valutare soltanto una data target statica.

Uso previsto:

```text
fo planning work-exit build
```

Default previsti:

- INPS: `../family-office-workspace/snapshots/inps-pension.snapshot.json`
- Spagna teorica/pro-rata: `../family-office-workspace/snapshots/spanish-eu-theoretical-pension.snapshot.json` e `../family-office-workspace/snapshots/it-es-eu-pension-pro-rata.snapshot.json`
- pension income: `../family-office-workspace/snapshots/pension-income.snapshot.json`
- patrimonio/liquidita'/spese: snapshot del workspace gia' prodotti dai comandi dedicati
- output: `../family-office-workspace/snapshots/work-exit-feasibility.snapshot.json`

Il comando dovra' produrre `work-exit-feasibility/v1` con date candidate, prima data sostenibile oppure blocco spiegato, motivi delle date scartate, stima INPS interna per candidato/persona, quota spagnola pro-rata, pensione del coniuge, totale lordo separato per persona e fonte, eventuali bridge e data gaps. Date esplicite come `2037` sono candidate diagnostiche o filtri della ricerca, non l'obiettivo primario. Se la pensione del coniuge non e' disponibile o stimabile, il comando dovra' produrre un gap esplicito per evitare una data household incompleta. Per anni futuri non osservabili usera' solo assunzioni proiettive dichiarate nei rule pack; non calcolera' certificazioni ufficiali INPS, P1 ufficiale, netto fiscale non gia' disponibile o raccomandazioni.

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

## `fo planning work-exit build`

Trova la prima data sostenibile di uscita dal lavoro del nucleo componendo stima INPS interna, benchmark INPS documentale, quota spagnola pro-rata, pensione del coniuge, patrimonio ponte e spese dichiarate.

Uso:

```text
fo planning work-exit build
```

Smoke sintetico:

```text
fo planning work-exit demo
```

Default principali:

- input: `../family-office-workspace/planning/work-exit-feasibility.json`
- rule pack: `../family-office-rules/italy/2026/inps-theoretical-pension.json`
- INPS documentale: `../family-office-workspace/snapshots/inps-pension.snapshot.json`
- Spagna pro-rata: `../family-office-workspace/snapshots/it-es-eu-pension-pro-rata.snapshot.json`
- output: `../family-office-workspace/snapshots/work-exit-feasibility.snapshot.json`
- input sintetico: `examples/work-exit-feasibility-sample.json`
- output sintetico: `../family-office-workspace/snapshots/cli-check-work-exit.synthetic.snapshot.json`

Il comando produce `work-exit-feasibility/v1`: elenca candidate valutate, prima data sostenibile o blocco, motivi delle date scartate, `inps-theoretical-pension/v1` per candidato/persona, stream lordi separati per persona e fonte e data gaps. La stima INPS interna e' contributiva e proiettiva per pianificazione; non sostituisce INPS, non calcola netto fiscale, P1, ricongiunzioni, riscatti, decorrenze amministrative o raccomandazioni.

## `fo planning estate build`

Confronta attribuzioni successorie e donazioni pregresse con quote di riserva, beneficiari, polizze, estero e liquidita' fiscale dichiarata.

Uso:

```text
fo planning estate build
```

Smoke sintetico:

```text
fo planning estate demo
```

Default principali:

- input: `../family-office-workspace/planning/estate-plan.json`
- rule pack: `../family-office-rules/succession/italy-2026-v2.json`
- output: `../family-office-workspace/snapshots/estate-plan.snapshot.json`
- input sintetico: `examples/estate-plan-sample.json`
- output sintetico: `../family-office-workspace/snapshots/cli-check-estate-plan.synthetic.snapshot.json`

Il comando produce `estate-plan/v2` con massa nota, massa fittizia dichiarata, quote di riserva, scenari comparati, conflitti, stime fiscali coperte dal rule pack e gap dati. Non calcola collazione, riduzione, base catastale, successione estera, trust, contenzioso o raccomandazioni.

## `fo planning wealth-strategy build`

Compone gli snapshot V4 in pacchetti strategici comparabili con piano operativo 90/180 giorni.

Uso:

```text
fo planning wealth-strategy build
```

Smoke sintetico:

```text
fo planning wealth-strategy demo
```

Default principali:

- input: `../family-office-workspace/planning/wealth-strategy-input.json`
- output: `../family-office-workspace/snapshots/wealth-strategy.snapshot.json`
- input sintetico: `examples/wealth-strategy-input-sample.json`
- output sintetico: `../family-office-workspace/snapshots/cli-check-wealth-strategy.synthetic.snapshot.json`
- sorgenti default: liquidity, tax-aware portfolio, cross-border IT-ES, real estate, protection, estate plan e work-exit nel workspace snapshots

Il comando produce `wealth-strategy/v1` con 2-4 pacchetti, componenti collegati agli snapshot sorgente, ranking ponderato, checklist 90/180 giorni, costi, dipendenze, reversibilita', controlli, rischi, scenari avversi e gap. Non calcola nuove imposte, pensioni, rendimenti, effetti legali o raccomandazioni.

## `fo orchestration tool-registry build`

Costruisce il registry dei tool deterministici invocabili dai futuri componenti AI.

Uso:

```text
fo orchestration tool-registry build
```

Listing leggibile:

```text
fo orchestration tool-registry list
```

Default principali:

- output: `../family-office-workspace/snapshots/tool-registry.snapshot.json`

Il comando produce `tool-registry/v1` con tool id, schema input/output, prerequisiti, rischio, policy di autorizzazione e note di perimetro. Non esegue tool di pianificazione e non abilita calcoli LLM.

## `fo orchestration citations build`

Costruisce l'indice locale delle fonti pubbliche, dei documenti knowledge e dei contratti registrati.

Uso:

```text
fo orchestration citations build
```

Ricerca per testo, giurisdizione, tema e data:

```text
fo orchestration citations search --jurisdiction IT --topic taxation --as-of-date 2026-08-09
fo orchestration citations search --query "pension coordination" --jurisdiction EU
```

Default principali:

- catalogo: `../family-office-knowledge/sources/citation-catalog.json`
- knowledge root: `../family-office-knowledge`
- output: `../family-office-workspace/snapshots/citation-index.snapshot.json`

`build` produce `citation-index/v1` con riepilogo di citazioni, documenti, contratti e gap. `search` esclude per default fonti future, scadute, abrogate o ritirate; `--include-inactive` le mostra con stato temporale esplicito. Se l'indice manca o non e' valido, l'errore indica di eseguire prima `fo orchestration citations build`.
