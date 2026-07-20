# Guida a asset-availability.json

Questo file risponde alla domanda: "quanto e' davvero disponibile ogni asset per coprire spese correnti o riserva di emergenza?"

E' diverso da `net-worth.snapshot.json`: il net worth dice quanto vale un asset; asset availability dice se puoi usarlo, quando, con quali vincoli e con quale incertezza.

Il file reale va qui:

```text
family-office-workspace/household/asset-availability.json
```

## Prerequisito

Prima di compilare questo file, gli stessi `asset_id` devono esistere in:

```text
family-office-workspace/household/ownership-beneficiaries.json
```

Il validatore rifiuta asset availability per asset non presenti nell'ownership graph. Questo evita di classificare liquidita' di asset che non sono stati ancora attribuiti a un titolare.

## Campi principali

### `schema_version`

Versione del contratto. Non cambiarla.

```json
"schema_version": "asset-availability/v1"
```

### `record_type`

Tipo del documento. Non cambiarlo.

```json
"record_type": "AssetAvailability"
```

### `household_id`

Stessa etichetta tecnica usata negli altri file. Nel tuo input liquidita':

```json
"household_id": "my_household"
```

Usa lo stesso valore anche qui.

### `as_of_date`

Data della classificazione. Dovrebbe essere coerente con il piano liquidita' e con gli estratti usati.

```json
"as_of_date": "2026-07-15"
```

## `classifications`

Lista delle classificazioni di disponibilita', una per asset.

Ogni riga dice: "questo asset e' liquido/illiquido/vincolato in questo modo".

### `classification_id`

ID tecnico della riga. Deve essere unico.

Schema pratico:

```text
availability_<asset_id>
```

Esempio:

```json
"classification_id": "availability_investment_7"
```

### `asset_id`

ID dell'asset a cui si riferisce la classificazione.

Deve essere identico all'`asset_id` in `ownership-beneficiaries.json`.

Esempio:

```json
"asset_id": "investment_7"
```

### `asset_class`

Categoria di disponibilita' dell'asset. Non deve per forza coincidere parola per parola con la categoria vista nel net worth; deve usare la tassonomia accettata da questo file.

Valori ammessi:

```text
cash
deposit
brokerage
pension_fund
insurance_policy
real_estate
company_share
other
```

Come scegliere:

- liquidita' su conto corrente: `cash`;
- deposito o conto deposito: `deposit`;
- conto titoli, ETF, fondi, gestione patrimoniale: `brokerage`;
- fondo pensione o previdenza complementare: `pension_fund`;
- polizza vita, unit linked, gestione separata assicurativa: `insurance_policy`;
- immobile: `real_estate`;
- quote societarie: `company_share`;
- non classificabile: `other`, con gap.

### `currency`

Valuta dell'asset.

Esempi:

```json
"currency": "EUR"
```

```json
"currency": "USD"
```

Il liquidity plan non converte valuta. Un asset non in `base_currency` viene segnalato come gap e non finanzia la riserva in EUR.

### `jurisdiction`

Paese principale del rapporto o dell'asset, in formato ISO a due lettere.

Esempi:

```json
"jurisdiction": "IT"
```

```json
"jurisdiction": "ES"
```

Se non lo sai:

```json
"jurisdiction": null
```

Questo produce un gap, ma non un errore. Non usare `"unknown"` per la giurisdizione: non e' un codice Paese valido.

### `liquidity_tier`

Quanto rapidamente l'asset e' disponibile.

Valori ammessi:

```text
immediate
short_term
notice_required
locked_until_date
illiquid
unknown
```

Significato:

- `immediate`: spendibile subito o quasi, senza vendita complessa. Esempio: conto corrente libero.
- `short_term`: liquidabile in tempi brevi, ma non e' cassa immediata. Esempio: ETF vendibili, fondi rimborsabili, conto titoli.
- `notice_required`: serve preavviso o procedura. Esempio: deposito vincolato svincolabile con tempi/penali.
- `locked_until_date`: bloccato fino a una data o evento. Esempio: fondo pensione, polizza con vincoli, deposito vincolato.
- `illiquid`: non usabile per spese correnti. Esempio: immobile, quote societarie non facilmente vendibili.
- `unknown`: non sai ancora la disponibilita'. Il motore lo trattera' come gap.

### `first_available_date`

Prima data in cui l'asset puo' essere usato o liquidato, secondo le informazioni note.

Per asset immediati:

```json
"first_available_date": "2026-07-15"
```

Per asset liquidabile a breve:

```json
"first_available_date": "2026-07-22"
```

Per asset con data non nota:

```json
"first_available_date": null
```

Nota: per `immediate`, la data non puo' essere successiva a `availability_as_of_date`.

### `availability_as_of_date`

Data in cui hai valutato la disponibilita'. Di solito coincide con `as_of_date`.

```json
"availability_as_of_date": "2026-07-15"
```

### `constraints`

Vincoli che impediscono o limitano l'uso dell'asset.

Valori ammessi:

```text
none
pension_lock
policy_terms
mortgage_or_lien
co_ownership
foreign_reporting
sale_process
other
unknown
```

Come scegliere:

- nessun vincolo rilevante: `["none"]`;
- fondo pensione non liberamente riscattabile: `["pension_lock"]`;
- polizza con condizioni contrattuali di riscatto: `["policy_terms"]`;
- immobile con mutuo, pegno o lien: `["mortgage_or_lien"]`;
- cointestazione o asset di minore/terzo: `["co_ownership"]`;
- asset estero con monitoraggio o attenzione fiscale: `["foreign_reporting"]`;
- immobile o asset vendibile solo con processo lungo: `["sale_process"]`;
- non sai ancora: `["unknown"]`.

Importante: se metti `pension_lock`, `policy_terms`, `mortgage_or_lien`, `co_ownership`, `sale_process` o `unknown`, il liquidity plan non usera' quell'asset per spese correnti.

### `risk_level`

Rischio/volatilita' dell'asset ai fini della riserva.

Valori ammessi:

```text
low
medium
high
illiquid
unknown
```

Come scegliere:

- conto corrente o deposito garantito: `low`;
- fondo monetario, obbligazionario prudente, portafoglio moderato: `medium`;
- azionario o crypto/strumenti molto volatili: `high`;
- immobile o asset non vendibile rapidamente: `illiquid`;
- non verificato: `unknown`.

Nota: per entrare in `emergency_reserve`, l'asset deve essere `immediate`, in valuta base, senza vincoli bloccanti e con rischio `low` o `medium`.

### `tax_treatment`

Etichetta descrittiva del trattamento fiscale o contenitore. Non calcola imposte.

Valori ammessi:

```text
ordinary_taxable
tax_deferred
pension_taxation
insurance_wrapper
real_estate_taxation
foreign_asset_reporting
unknown
```

Come scegliere:

- conto titoli/fondi ordinari: `ordinary_taxable`;
- contenitore con differimento fiscale: `tax_deferred`;
- fondo pensione: `pension_taxation`;
- polizza assicurativa: `insurance_wrapper`;
- immobile: `real_estate_taxation`;
- asset estero da monitorare: `foreign_asset_reporting`;
- dubbio: `unknown`.

### `provenance`

Fonte della classificazione. Deve far capire da dove arriva il dato.

Esempi:

```json
"provenance": "bank statement reviewed manually"
```

```json
"provenance": "policy terms reviewed manually"
```

```json
"provenance": "manual classification pending document review"
```

### `notes`

Campo libero per spiegare dubbi o assunzioni operative.

Esempi:

```json
"notes": "Settlement expected within a few business days; tax impact not calculated here."
```

```json
"notes": "Pension product; access rules must be reviewed before decumulation planning."
```

## Esempi pronti

### Cassa libera

```json
{
  "classification_id": "availability_investment_7",
  "asset_id": "investment_7",
  "asset_class": "cash",
  "currency": "EUR",
  "jurisdiction": "IT",
  "liquidity_tier": "immediate",
  "first_available_date": "2026-07-15",
  "availability_as_of_date": "2026-07-15",
  "constraints": ["none"],
  "risk_level": "low",
  "tax_treatment": "ordinary_taxable",
  "provenance": "account statement reviewed manually",
  "notes": "Free cash available for household spending."
}
```

### Investimento liquidabile ma non riserva immediata

```json
{
  "classification_id": "availability_investment_4",
  "asset_id": "investment_4",
  "asset_class": "brokerage",
  "currency": "EUR",
  "jurisdiction": "IT",
  "liquidity_tier": "short_term",
  "first_available_date": "2026-07-22",
  "availability_as_of_date": "2026-07-15",
  "constraints": ["none"],
  "risk_level": "medium",
  "tax_treatment": "ordinary_taxable",
  "provenance": "investment statement reviewed manually",
  "notes": "Liquidation may require market sale; not treated as immediate cash."
}
```

### Fondo pensione

```json
{
  "classification_id": "availability_fonte_position",
  "asset_id": "fonte_position",
  "asset_class": "pension_fund",
  "currency": "EUR",
  "jurisdiction": "IT",
  "liquidity_tier": "locked_until_date",
  "first_available_date": null,
  "availability_as_of_date": "2026-07-15",
  "constraints": ["pension_lock"],
  "risk_level": "medium",
  "tax_treatment": "pension_taxation",
  "provenance": "pension fund statement reviewed manually",
  "notes": "Not available for current spending without checking pension access rules."
}
```

## `data_gaps`

Usalo quando non vuoi forzare una certezza.

Esempi:

```json
{
  "code": "unknown_policy_terms",
  "message": "Insurance policy liquidity and surrender terms are not verified."
}
```

```json
{
  "code": "missing_asset_jurisdiction",
  "message": "Some investment jurisdictions are not yet verified from account documents."
}
```

## Effetto sul liquidity plan

Il liquidity plan usa queste regole pratiche:

- `immediate`, valuta base, rischio `low` o `medium`, nessun vincolo bloccante: puo' entrare in `emergency_reserve`;
- `short_term` o `notice_required`: entra in `short_term`;
- `locked_until_date`: entra in short/medium/long term in base alla data, ma resta bloccato per spese correnti;
- `illiquid`, `unknown` o asset con vincoli bloccanti: entra in `restricted`;
- valuta diversa dalla base: gap e niente funding della riserva.

Comando:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main household availability validate
```
