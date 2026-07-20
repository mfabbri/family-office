# Decumulation policy set guide

Questa guida spiega come compilare `decumulation-policy-set/v1`. Il file reale va in:

```text
family-office-workspace/planning/decumulation-policy-set.json
```

Non copiare dati personali nel repository software. Usa `examples/decumulation-policy-set-sample.json` come esempio sintetico.

## Campo per campo

### `household_id`

ID tecnico dello stesso nucleo usato negli altri file del workspace.

Esempio:

```json
"household_id": "household_main"
```

### `as_of_date`

Data di riferimento della policy, idealmente vicina agli snapshot patrimoniali usati.

```json
"as_of_date": "2026-07-20"
```

### `base_currency`

Valuta di lettura del piano. V4.3 usa solo asset nella stessa valuta e non converte FX.

```json
"base_currency": "EUR"
```

### `current_age`

Eta' corrente della persona su cui modelli il decumulo. Deve essere un intero non negativo.

```json
"current_age": 60
```

### `policies`

Elenco di policy alternative da confrontare. Inserisci almeno due policy quando vuoi capire la sensibilita' a eta', ordine prelievi, cash buffer, RITA o sequenza rendimenti.

## Campi di ogni policy

### `policy_id`

ID tecnico univoco, senza spazi.

```json
"policy_id": "bridge_rita"
```

### `label`

Etichetta leggibile per report e CLI.

```json
"label": "Bridge with RITA and brokerage first"
```

### `retirement_age`

Eta' da cui la policy considera l'avvio del pensionamento o del bridge. Non puo' essere minore di `current_age`.

### `end_age`

Eta' finale dell'orizzonte. Deve essere maggiore o uguale a `retirement_age`. Usa orizzonti diversi per testare longevita' e depletion.

### `annual_spending_need`

Fabbisogno netto annuo che vuoi coprire in pensione, espresso come stringa decimale.

```json
"annual_spending_need": "36000.00"
```

Il motore non stima il budget: se il valore e' incompleto, dichiaralo in `data_gaps`.

### `cash_buffer_target`

Liquidita' minima desiderata durante il decumulo. Se il buffer scende sotto target, l'output produce warning.

### `withdrawal_order`

Ordine degli `asset_id` da usare per i prelievi. Gli ID devono esistere nel `net-worth.snapshot.json` e non essere restricted nel `liquidity-plan.snapshot.json`.

```json
"withdrawal_order": ["asset_brokerage", "asset_cash"]
```

### `annual_return_sequence`

Sequenza di rendimenti annui netti dichiarati. Il motore ripete l'ultimo valore se l'orizzonte e' piu' lungo della sequenza.

```json
"annual_return_sequence": ["-0.08", "0.02", "0.03"]
```

Questi sono input espliciti, non rendimenti attesi calcolati dal sistema.

### `withdrawal_tax_rate`

Aliquota tecnica da applicare ai prelievi per ottenere metriche nette. Deve essere tra `0` e `1`.

### `pension_tax_rate`

Aliquota tecnica per trasformare il pension income lordo ricorrente in importo netto usato dal confronto.

### `rita_tax_rate`

Aliquota tecnica per trasformare l'eventuale RITA lorda in importo netto usato dal confronto.

### `include_rita`

`true` se la policy usa le opzioni RITA disponibili nello snapshot, `false` se vuoi escluderle.

## `data_gaps`

Elenco di incertezze note.

Esempio:

```json
{
  "code": "spending_need_estimated",
  "message": "Annual spending need is estimated from partial expense history."
}
```

## Checklist prima di eseguire

- `current_age`, `retirement_age` ed `end_age` sono coerenti.
- Gli asset in `withdrawal_order` esistono nel patrimonio e sono decumulabili.
- I tassi sono espliciti e non rappresentano una regola fiscale normativa.
- I rendimenti sono scenari dichiarati, non previsioni generate dal modello.
- I gap noti sono in `data_gaps`.

## Comando

Da `family-office-engine`:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning decumulation build
```

Smoke sintetico:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning decumulation demo
```
