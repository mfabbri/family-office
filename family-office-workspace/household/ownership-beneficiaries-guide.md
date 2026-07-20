# Guida a ownership-beneficiaries.json

Questo file risponde a tre domande:

- quali asset e debiti esistono nel nucleo;
- chi ne e' titolare, e in che quota;
- chi sono eventuali beneficiari di polizze, fondi pensione o altri rapporti con beneficiario.

Serve come ponte tra patrimonio netto, successione, disponibilita' degli asset e pianificazione familiare. Non calcola imposte, successione o raccomandazioni: registra fatti dichiarati e gap.

Il file reale va qui:

```text
family-office-workspace/household/ownership-beneficiaries.json
```

## Regola importante

Gli `asset_id` devono essere gli stessi che userai poi in `asset-availability.json`.

Se hai gia' generato il patrimonio netto, gli asset da collegare si trovano nello snapshot privato:

```text
family-office-workspace/snapshots/net-worth.snapshot.json
```

Questo non e' un file del repository software `family-office-engine`: e' un output locale del workspace privato, generato dai tuoi documenti o dai tuoi input.

Nel tuo workspace, al momento della stesura di questa guida, quello snapshot conteneva asset con ID come:

```text
fonte_position
investment_1
investment_2
investment_4
investment_5
investment_6
investment_7
investment_8
```

Se vuoi che il liquidity plan li classifichi, questi asset devono comparire anche nella lista `assets` di `ownership-beneficiaries.json`.

## Campi principali

### `schema_version`

Versione del contratto. Non cambiarla.

```json
"schema_version": "ownership-beneficiary-graph/v1"
```

### `record_type`

Tipo del documento. Non cambiarlo.

```json
"record_type": "OwnershipBeneficiaryGraph"
```

### `household_id`

Etichetta tecnica del nucleo familiare. Usa lo stesso valore degli altri file del workspace.

Per il tuo file liquidita' hai usato:

```json
"household_id": "my_household"
```

Quindi usa lo stesso anche qui, salvo decidere di rinominare tutti i file in modo coerente.

### `as_of_date`

Data a cui sono vere le informazioni di ownership.

Usa una data vicina agli estratti o allo snapshot patrimoniale. Se stai lavorando sul piano liquidita' del 2026-07-15:

```json
"as_of_date": "2026-07-15"
```

Se alcune titolarita' sono note da documenti piu' vecchi, puoi comunque usare la data del piano e dichiarare il dubbio in `data_gaps`.

## `assets`

Lista degli asset che vuoi rendere riconoscibili al motore.

Ogni voce dice: "questo asset esiste, ha questo tipo, e questa informazione viene da questa fonte".

Campi:

- `asset_id`: ID stabile e tecnico dell'asset. Deve combaciare con net worth e asset availability.
- `asset_type`: categoria ammessa dal motore.
- `label`: nome leggibile, se vuoi usarlo. Evita dettagli sensibili inutili.
- `currency`: valuta principale, se nota.
- `provenance`: da dove arriva il dato.

Categorie ammesse per `asset_type`:

```text
financial_account
pension_fund
real_estate
insurance_policy
company_share
cash
other
```

Come scegliere `asset_type`:

- conto corrente o deposito: `financial_account` oppure `cash`;
- conto titoli, gestione patrimoniale, broker: `financial_account`;
- fondo pensione, previdenza complementare, posizione pensionistica: `pension_fund`;
- polizza vita o investimento assicurativo: `insurance_policy`;
- immobile: `real_estate`;
- quota societaria: `company_share`;
- dubbio non risolto: `other`, con gap.

Esempio:

```json
{
  "asset_id": "investment_7",
  "asset_type": "cash",
  "label": "Cash position from net worth snapshot",
  "currency": "EUR",
  "provenance": "net-worth.snapshot.json reviewed against bank/investment documents"
}
```

## `debts`

Lista dei debiti rilevanti: mutui, prestiti, finanziamenti, debiti fiscali, debiti verso terzi.

Puoi lasciarla vuota se non vuoi ancora modellare debiti:

```json
"debts": []
```

Campi tipici:

- `debt_id`: ID tecnico del debito.
- `linked_asset_id`: asset collegato, ad esempio immobile con mutuo. Lascia `null` se non collegato.
- `provenance`: fonte del dato.

Esempio:

```json
{
  "debt_id": "debt_main_mortgage",
  "linked_asset_id": "asset_family_home",
  "provenance": "mortgage statement reviewed manually"
}
```

## `ownership_interests`

Questa e' la parte piu' importante: dice chi possiede cosa.

Ogni voce collega una persona a un asset o debito.

Campi:

- `ownership_id`: ID tecnico della riga.
- `subject_type`: `asset` o `debt`.
- `subject_id`: ID dell'asset o debito.
- `owner_person_id`: persona titolare. Deve esistere in `household-facts.json`, se validi contro quello snapshot.
- `interest_type`: tipo di diritto.
- `share`: quota posseduta, da `"0.00"` a `"1.00"`.
- `start_date`: da quando e' valida la titolarita', se noto.
- `end_date`: fine titolarita', di solito `null`.
- `provenance`: fonte.

Valori ammessi per `interest_type`:

```text
full_ownership
co_ownership
bare_ownership
usufruct
debtor
guarantor
unknown
```

Come scegliere:

- asset intestato a una sola persona: `full_ownership`, `share: "1.00"`;
- asset cointestato: una riga per ogni titolare con `co_ownership`, quote che sommano a `1.00`;
- nuda proprieta': `bare_ownership`;
- usufrutto: `usufruct`;
- debito intestato a una persona: `debtor`;
- garanzia senza debito diretto: `guarantor`;
- non sai chi sia titolare: `unknown`, e aggiungi un gap.

Esempio asset singolo:

```json
{
  "ownership_id": "own_investment_7_self",
  "subject_type": "asset",
  "subject_id": "investment_7",
  "owner_person_id": "person_self",
  "interest_type": "full_ownership",
  "share": "1.00",
  "start_date": null,
  "end_date": null,
  "provenance": "account statement reviewed manually"
}
```

Esempio cointestazione 50/50:

```json
{
  "ownership_id": "own_joint_account_self",
  "subject_type": "asset",
  "subject_id": "asset_joint_account",
  "owner_person_id": "person_self",
  "interest_type": "co_ownership",
  "share": "0.50",
  "start_date": null,
  "end_date": null,
  "provenance": "bank statement reviewed manually"
}
```

Per lo stesso asset servirebbe una seconda riga con l'altro titolare e `share: "0.50"`.

## `beneficiaries`

Beneficiari espliciti di polizze, fondi pensione, conti o altri rapporti. Non e' la stessa cosa della titolarita'.

Puoi lasciare vuoto se non hai ancora verificato:

```json
"beneficiaries": []
```

Ma per polizze e fondi pensione e' meglio indicare almeno un gap se il beneficiario non e' noto.

Campi:

- `beneficiary_id`: ID tecnico della riga.
- `subject_type`: `asset` o `debt`.
- `subject_id`: asset/debito a cui si riferisce.
- `beneficiary_person_id`: persona beneficiaria, se interna al nucleo e nota.
- `beneficiary_type`: tipo di beneficiario.
- `share`: quota beneficiaria, se nota.
- `provenance`: fonte.

Valori ammessi per `beneficiary_type`:

```text
primary
contingent
legal_heir
other
unknown
```

Esempio:

```json
{
  "beneficiary_id": "beneficiary_policy_primary",
  "subject_type": "asset",
  "subject_id": "asset_life_policy",
  "beneficiary_person_id": "person_spouse",
  "beneficiary_type": "primary",
  "share": "1.00",
  "provenance": "policy document reviewed manually"
}
```

## `data_gaps`

Qui dichiari cio' che non sai ancora. Meglio un gap esplicito che un dato inventato.

Esempi:

```json
{
  "code": "unknown_beneficiaries",
  "message": "Beneficiaries for pension funds and insurance policies are not yet verified."
}
```

```json
{
  "code": "ownership_share_to_confirm",
  "message": "Some account ownership shares are inferred from statements and must be confirmed."
}
```

## Sequenza consigliata per il liquidity plan

1. Copia gli asset reali da `family-office-workspace/snapshots/net-worth.snapshot.json` nella lista `assets`.
2. Per ogni asset aggiungi almeno una riga in `ownership_interests`.
3. Se non sai il titolare, usa `interest_type: "unknown"` e registra un gap.
4. Valida ownership.
5. Solo dopo compila `asset-availability.json`.

Comando:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main household ownership validate
```
