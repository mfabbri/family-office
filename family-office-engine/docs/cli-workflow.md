# CLI workflow guide

Questa guida orienta l'uso della CLI senza dover leggere il codice. I dati reali restano sempre in `family-office-workspace/`; il repository engine contiene solo codice, documentazione ed esempi sintetici.

## Comandi base

Esegui i comandi da `family-office-engine`:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main validate
```

Se hai installato un wrapper locale `fo`, i comandi documentati in `docs/cli.md` possono essere letti come:

```text
fo <area> <azione>
```

## Ordine consigliato

1. `validate`: verifica layout dei repository.
2. `documents inventory` e `documents organize`: controlla e classifica i documenti nel workspace.
3. Import documentali: `payroll`, `investments`, `bank-insurance`, `tax-documents`, `fonte`, `pension import-spain`.
4. Normalizzazioni household: `household validate`, `household ownership validate`, `household availability validate`, `household timeline validate`.
5. Pensione e cashflow: `pension reconcile-spain`, `pension estimate-spain`, `pension coordinate-it-es`, `pension compose-income`, `expenses build-lifecycle`.
6. Patrimonio e pianificazione: `net-worth consolidate`, `planning goals`, `planning liquidity`, `planning decumulation`, `planning pension-contributions`.
7. Scenario decisionale: `scenarios compose-v2`, `scenarios evaluate`, `scenarios sensitivity`, `scenarios score`, `scenarios dossier`.
8. Report e dashboard: `dashboard build`, `report build`.

## Comandi demo

Quando disponibili, preferisci i demo sintetici per controllare che una capability funzioni senza preparare JSON reali:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning goals demo
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning liquidity demo
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning decumulation demo
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning pension-contributions demo
```

Gli output demo vanno in `family-office-workspace/snapshots/cli-check-*.synthetic.snapshot.json`.

## Wizard input

Per i principali input V4 puoi creare un primo JSON privato senza editarlo a mano:

```text
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning goals wizard
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning liquidity wizard
$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning decumulation wizard
```

I wizard fanno domande deterministiche, scrivono solo nel workspace o nel path passato con `--input`, rifiutano overwrite salvo `--overwrite` e validano il contratto input. Non deducono valori mancanti: le risposte lasciate incerte restano in `data_gaps` per revisione.

## Quando compilare JSON

Compila JSON privati solo quando la CLI non puo' derivare l'input da documenti o snapshot esistenti. Usa:

- `docs/json-input-guides.md` per la mappa di tutti gli input JSON attivi.
- `examples/*-sample.json` per esempi sintetici.
- `examples/liquidity-plan-input-guide.md` per `liquidity-plan-input/v1`.
- `examples/decumulation-policy-set-guide.md` per `decumulation-policy-set/v1`.

Non inserire nomi, codici fiscali, indirizzi, email o numeri documento nei file del repository engine. Se un campo richiede un identificativo, usa ID tecnici stabili come `household_main`, `person_self`, `asset_brokerage`.

## Lettura degli stati

La CLI usa stati riproducibili:

- `complete`: output costruito senza gap bloccanti.
- `partial`: output disponibile ma con gap o limiti espliciti.
- `blocked_missing_inputs`: dati essenziali mancanti; il comando non inventa valori.
- `blocked_missing_rule`: rule pack assente o non applicabile.

Un output `partial` puo' essere utile per audit e revisione, ma non va trattato come raccomandazione.
