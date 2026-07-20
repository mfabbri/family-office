# Liquidity plan input guide

Questa guida spiega come compilare `liquidity-plan-input/v1` partendo da dati reali nel workspace privato.

Non copiare dati personali nel repository software. Il file reale va in:

```text
family-office-workspace/planning/liquidity-plan-input.json
```

## Campo per campo

### `household_id`

Nome tecnico, non personale, con cui il progetto riconosce lo stesso nucleo familiare nei vari file.

In pratica: scegli una stringa breve e riusala uguale nei file del workspace che descrivono la stessa famiglia. Serve al motore per capire che `household-facts.json`, `planning-goals.json`, `asset-availability.json` e `liquidity-plan-input.json` parlano dello stesso caso.

Valore consigliato se stai compilando il caso reale principale:

```json
"household_id": "household_main"
```

Va bene anche un altro nome tecnico, ad esempio:

```json
"household_id": "household_real"
```

Non usare nomi, cognomi, codici fiscali, indirizzi o email. Questo campo non deve identificare una persona nel mondo reale: deve solo collegare tra loro i file locali.

Se hai gia' `family-office-workspace/household/household-facts.json`, copia lo stesso valore di `household_id` da li'. Se non esiste ancora o contiene un placeholder, usa `household_main` e poi mantieni quello negli altri file.

### `as_of_date`

Data a cui riferisci il piano di liquidita'. Usa la stessa data o una data vicina agli snapshot patrimoniali che stai usando.

Metodo consigliato:

- se stai usando estratti di fine mese, usa l'ultimo giorno del mese;
- se stai usando snapshot aggiornati oggi, usa la data di oggi;
- se alcuni documenti sono piu' vecchi, segnala il gap in `data_gaps`.

Formato:

```json
"as_of_date": "2026-07-19"
```

### `base_currency`

Valuta in cui vuoi leggere la riserva. Per una famiglia residente in Italia normalmente e':

```json
"base_currency": "EUR"
```

Il motore non converte valute. Asset in USD, GBP o altra valuta saranno segnalati come gap e non finanzieranno la riserva in EUR.

### `monthly_expenses`

Spesa mensile ordinaria usata per calcolare la riserva di emergenza.

Formula:

```text
monthly_expenses = spese annue ricorrenti / 12
```

Includi:

- casa, mutuo o affitto;
- utenze, condominio, manutenzione ordinaria;
- alimentari, trasporti, scuola, sanita' ricorrente;
- assicurazioni ricorrenti;
- rate debiti;
- imposte o spese annuali prevedibili divise per 12;
- margine prudenziale se le spese sono incomplete.

Escludi:

- trasferimenti verso investimenti o conti propri;
- acquisti patrimoniali una tantum;
- spese straordinarie gia' modellate come evento separato;
- tasse, rendimento o inflazione stimati dal modello.

Metodo rapido:

1. Prendi 6-12 mesi di movimenti bancari.
2. Elimina giroconti, investimenti, rimborsi e movimenti una tantum.
3. Somma le uscite ricorrenti.
4. Dividi per i mesi osservati.
5. Arrotonda per eccesso a 50 o 100 EUR.

Se hai solo una stima incompleta, usala ma aggiungi un gap:

```json
{
  "code": "estimated_monthly_expenses",
  "message": "Monthly expenses are estimated from partial bank data."
}
```

### `minimum_reserve_months`

Numero di mesi di spese da tenere in riserva.

Valori pratici:

- `3`: entrate stabili, basso rischio, rete familiare forte;
- `6`: default prudente per famiglia con spese ordinarie prevedibili;
- `9` o `12`: redditi variabili, figli, mutuo, rischio lavorativo o distanza dalla pensione;
- oltre `12`: solo se c'e' una ragione esplicita, perche' puo' immobilizzare liquidita'.

Nota: se passi anche `planning-goals.snapshot.json`, il valore in `planning_goals.liquidity_policy.minimum_reserve_months` prevale su questo campo. Mantieni i due valori allineati per evitare confusione.

### `concentration_threshold`

Soglia oltre la quale un singolo asset genera warning di concentrazione.

Esempi:

- `"0.30"`: warning se un asset supera il 30% del patrimonio osservato;
- `"0.50"`: soglia intermedia;
- `"0.60"`: soglia permissiva, utile quando casa o fondo pensione dominano il patrimonio.

Questo campo non produce raccomandazioni e non ottimizza il portafoglio: serve solo a rendere visibile la concentrazione.

### `data_gaps`

Elenco di incertezze note. Meglio dichiarare un gap che trasformare una stima in dato certo.

Esempi:

```json
{
  "code": "partial_bank_history",
  "message": "Monthly expenses are based on 4 months of bank movements, not a full year."
}
```

```json
{
  "code": "outdated_asset_value",
  "message": "Some investment values are based on statements older than the liquidity plan date."
}
```

```json
{
  "code": "unknown_policy_liquidity",
  "message": "Insurance policy surrender timing is not confirmed."
}
```

## Checklist prima di eseguire

- `monthly_expenses` rappresenta spese ricorrenti, non patrimonio o reddito.
- `minimum_reserve_months` e' coerente con `planning-goals.json`.
- La valuta base e' una sigla ISO maiuscola, ad esempio `EUR`.
- I valori incerti sono segnalati in `data_gaps`.
- I documenti reali restano sotto `family-office-workspace/`.

## Comando

Da `family-office-engine`:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning liquidity build
```
