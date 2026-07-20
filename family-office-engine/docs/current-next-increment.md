# Current Next Increment

## ID e titolo

V4.4 - Pension contribution optimizer.

## Stato

`done`

## Roadmap

`docs/roadmap/roadmap-v4-wealth-planning.md`

## Motivazione e dipendenze

`current-next-increment.md` precedente marcava V4.3b come `done` e indicava V4.4 come prossimo incremento deducibile. La roadmap V4 e' `in_progress`; V4.4 dipende da V3.5e `pension-income/v1` e dal rule engine fiscale, gia' disponibili.

L'incremento e' T4: tocca deducibilita' fiscale e previdenza complementare italiana. E' stato applicato il flusso `knowledge -> rules -> tests -> engine`.

## Piano operativo

Piano salvato in `docs/plans/2026-07-20-v4.4-pension-contribution-optimizer.md`.

## Perimetro previsto

- Knowledge note Italia su deducibilita' contributi previdenza complementare.
- Rule pack 2026 `pension-contribution-rule-pack/v1`.
- Contratto `pension-contribution-options/v1`.
- Servizio deterministico e CLI `planning pension-contributions build/demo`.
- Fixture sintetica e test su plafond, contributo datore, prima occupazione, liquidita' e anno non coperto.

## Esito implementazione

- Aggiunta knowledge note `previdenza-complementare-deducibilita-it.md` con fonti verificate il 2026-07-20.
- Aggiunto rule pack `family-office-rules/italy/2026/pension-contribution-deduction.json`.
- Aggiunto servizio `pension_contribution_options` per confrontare opzioni esplicite.
- Aggiunta fixture `examples/pension-contribution-input-sample.json`.
- Aggiunta CLI `fo planning pension-contributions build` e `demo`.
- Aggiornati API docs, CLI docs, testing docs, JSON input guide, decision log e roadmap.

## File modificati

- `family-office-knowledge/pensions/previdenza-complementare-deducibilita-it.md`
- `family-office-knowledge/pensions/README.md`
- `family-office-rules/italy/2026/pension-contribution-deduction.json`
- `family-office-rules/italy/2026/README.md`
- `family-office-engine/docs/plans/2026-07-20-v4.4-pension-contribution-optimizer.md`
- `family-office-engine/src/family_office_engine/services/pension_contribution_options.py`
- `family-office-engine/src/family_office_engine/cli/main.py`
- `family-office-engine/examples/pension-contribution-input-sample.json`
- `family-office-engine/tests/unit/test_pension_contribution_options.py`
- `family-office-engine/tests/unit/test_validate.py`
- `family-office-engine/docs/api.md`
- `family-office-engine/docs/cli.md`
- `family-office-engine/docs/testing.md`
- `family-office-engine/docs/json-input-guides.md`
- `family-office-engine/docs/decision-log.md`
- `family-office-engine/docs/current-next-increment.md`
- `family-office-engine/docs/roadmap/roadmap-index.md`
- `family-office-engine/docs/roadmap/roadmap-v4-wealth-planning.md`

## Test e verifiche

- Eseguito: `$env:PYTHONPATH='src'; python -m unittest tests.unit.test_pension_contribution_options tests.unit.test_validate.ValidateCliTest.test_main_planning_pension_contributions_demo_returns_success` -> 6 test OK.
- Eseguito: `$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning pension-contributions demo` -> OK, `complete 3 options`, `best=employee_plus_match`, 0 gap, 3 constraints sintetici.
- Eseguito: `$env:PYTHONPATH='src'; python -m unittest discover -s tests\unit` -> 320 test OK.
- Eseguito: `git diff --check` -> OK, con soli warning CRLF di Git.

## Criteri di completamento

- Ogni opzione espone deducibilita', beneficio fiscale stimato, costo opportunita', liquidita' persa, vincoli e data gaps.
- Nessun valore normativo e' hard-coded nell'engine.
- Aliquota marginale, contributi gia' dedotti, liquidita' e costo opportunita' sono input espliciti.
- Test pertinenti verdi.
- V4.4 marcato `done`; V4 resta `in_progress`.

## Prossimo incremento deducibile

V4.5 - Tax-aware investment planning.

## Rischi, esclusioni e blocker

- Fuori perimetro: IRPEF completa, detrazioni, addizionali, CU/dichiarazione, rendimenti, matching contrattuale non dichiarato, parser nuovi, dati reali e raccomandazioni.
- Le fonti normative sono state verificate il 2026-07-20; cambi successivi richiedono aggiornamento `knowledge -> rules -> tests -> engine`.
- Nessun blocker esplicito al momento della chiusura.
