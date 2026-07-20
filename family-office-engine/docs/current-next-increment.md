# Current Next Increment

## ID e titolo

V4.3 - Retirement decumulation strategies.

## Stato

`done`

## Roadmap

`docs/roadmap/roadmap-v4-wealth-planning.md`

## Motivazione e dipendenze

`current-next-increment.md` precedente marcava V4.2a come `done` e indicava V4.3 come prossimo incremento deducibile. La roadmap V4 e' `in_progress`; non ci sono audit bloccanti prima di V4.3.

Dipendenze verificate:

- V4.2 `liquidity-plan/v1` e' `done`.
- V3.5e `pension-income/v1` e' `done`.
- La prima implementazione usa tassi espliciti nelle policy e non introduce interpretazione normativa o nuovi rule pack fiscali.

## Piano operativo

Piano salvato in `docs/plans/2026-07-20-v4.3-retirement-decumulation-strategies.md`.

## Perimetro previsto

- Servizio `services/decumulation_strategy.py`.
- CLI `planning decumulation build` e `planning decumulation demo`.
- Fixture sintetiche `examples/decumulation-*.json`.
- Test unitari e CLI smoke collegati.
- Documentazione API, CLI, testing e roadmap V4 solo se l'implementazione conferma il contratto.

## Esito implementazione

- Introdotto `decumulation-strategy/v1` con builder deterministico, hash stabile e note sui limiti.
- Le policy dichiarano eta' pensionamento, orizzonte, fabbisogno netto annuo, cash buffer, ordine prelievi, sequenza rendimenti, tassi espliciti e RITA si'/no.
- Il servizio compone `net-worth/v1`, `liquidity-plan/v1`, `pension-income/v1` e opzionalmente `rita-options/v1`, escludendo asset restricted/non classificati o in valuta non convertita.
- L'output contiene cashflow annui, metriche nette, shortfall, depletion age, uso pensione/RITA, warning, data gaps e ranking tecnico non prescrittivo.
- Nessuna modifica a rules o knowledge: non sono stati introdotti calcoli normativi o fiscali reali.

## File modificati

- `family-office-engine/src/family_office_engine/services/decumulation_strategy.py`
- `family-office-engine/tests/unit/test_decumulation_strategy.py`
- `family-office-engine/src/family_office_engine/cli/main.py`
- `family-office-engine/tests/unit/test_validate.py`
- `family-office-engine/examples/decumulation-policy-set-sample.json`
- `family-office-engine/examples/decumulation-net-worth-sample.json`
- `family-office-engine/examples/decumulation-liquidity-plan-sample.json`
- `family-office-engine/examples/decumulation-pension-income-sample.json`
- `family-office-engine/examples/decumulation-rita-options-sample.json`
- `family-office-engine/docs/api.md`
- `family-office-engine/docs/cli.md`
- `family-office-engine/docs/testing.md`
- `family-office-engine/docs/plans/2026-07-20-v4.3-retirement-decumulation-strategies.md`
- `family-office-engine/docs/current-next-increment.md`
- `family-office-engine/docs/roadmap/roadmap-index.md`
- `family-office-engine/docs/roadmap/roadmap-v4-wealth-planning.md`
- `family-office-engine/docs/decision-log.md`

## Test e verifiche

- Eseguito: `$env:PYTHONPATH='src'; python -m unittest tests.unit.test_decumulation_strategy tests.unit.test_validate` -> 64 test OK.
- Eseguito: `$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning decumulation demo` -> OK, `partial 2 policies`, `best=later_no_rita`, 1 gap.
- Eseguito: `$env:PYTHONPATH='src'; python -m unittest discover -s tests\unit` -> 309 test OK.
- Eseguito: `git diff --check` -> OK, con soli warning CRLF di Git.

## Criteri di completamento

- `decumulation-strategy/v1` disponibile da servizio e CLI.
- Almeno due policy confrontate con metriche nette, cashflow, warning e data gaps.
- Test mirati e regression pertinente verdi.
- V4.3 marcato `done`; V4 resta `in_progress`.

## Prossimo incremento deducibile

V4.3a - CLI and JSON input guides.

## Rischi, esclusioni e blocker

- Fuori perimetro: ottimizzazione contributi, fiscalita' normativa, investimenti tax-aware, AI, dati reali e raccomandazioni.
- Nessun blocker esplicito al momento dell'avvio.
