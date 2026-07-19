# Current Next Increment

## ID e titolo

V4.2 - Liquidity buckets and emergency reserve.

## Stato

`done`

## Roadmap

`docs/roadmap/roadmap-v4-wealth-planning.md`

## Motivazione e dipendenze

`current-next-increment.md` precedente marcava V4.1 come `done` e indicava V4.2 come prossimo incremento deducibile. La roadmap V4 e' `in_progress`; V4.2 era il primo incremento `planned` con dipendenze soddisfatte.

V4.2 divide gli asset valorizzati in riserva, breve, medio, lungo termine e vincolati usando classificazioni esplicite di disponibilita' asset, net worth e obiettivi dichiarati. Il servizio impedisce che le spese correnti dipendano da asset non liquidabili e segnala riserva insufficiente, valuta estera, concentrazione e dati mancanti.

Dipendenze verificate:

- V4.1 `planning-goals/v1` e' `done`.
- V3.3 asset availability e net worth sono disponibili come contratti engine.
- Non serve nuova normativa o rule pack fiscale: V4.2 classifica liquidita' da input espliciti senza tassazione, rendimenti o raccomandazioni.
- Dopo V4.2 la cadenza audit richiede V4.2a prima di V4.3.

## Repository coinvolti

- `family-office-engine`: contratto `liquidity-plan/v1`, snapshot builder, CLI, fixture sintetica, test e documentazione.
- `family-office-workspace`: destinazione privata attesa per input e snapshot reali; nessun dato reale viene copiato nel repository software.
- `family-office-rules`, `family-office-knowledge`, `family-office-bootstrap`: nessuna modifica.

## Input attesi e classificazione dati

- Input JSON `liquidity-plan-input/v1` con spese mensili, valuta base e soglie di concentrazione opzionali.
- Snapshot `net-worth/v1`, `asset-availability/v1` e `planning-goals/v1`.
- Fixture sintetiche nell'engine; dati reali solo nel workspace privato.

## Output e contratti prodotti o modificati

- Contratto e snapshot `liquidity-plan/v1`.
- Emergency reserve target, funded amount e shortfall.
- Bucket `emergency_reserve`, `short_term`, `medium_term`, `long_term` e `restricted` con asset assegnati.
- Data gaps e warning per riserva insufficiente, valuta estera, asset vincolati, dati mancanti e concentrazione.
- CLI `planning liquidity build` e `planning liquidity demo`.

## File modificati

- `family-office-engine/src/family_office_engine/services/liquidity_plan.py`
- `family-office-engine/src/family_office_engine/cli/main.py`
- `family-office-engine/tests/unit/test_liquidity_plan.py`
- `family-office-engine/tests/unit/test_validate.py`
- `family-office-engine/examples/liquidity-plan-input-sample.json`
- `family-office-engine/examples/liquidity-plan-net-worth-sample.json`
- `family-office-engine/docs/plans/2026-07-19-v4.2-liquidity-plan.md`
- `family-office-engine/docs/api.md`
- `family-office-engine/docs/cli.md`
- `family-office-engine/docs/testing.md`
- `family-office-engine/docs/current-next-increment.md`
- `family-office-engine/docs/roadmap/roadmap-v4-wealth-planning.md`
- `family-office-engine/docs/roadmap/roadmap-index.md`
- `family-office-engine/docs/decision-log.md`

## Test e verifiche

- Input completo produce snapshot con hash stabile.
- Riserva insufficiente produce shortfall esplicito.
- Asset illiquidi, locked o vincolati sono esclusi dal funding delle spese correnti.
- Valuta estera produce data gap senza conversione inventata.
- Concentrazione sopra soglia produce warning.
- CLI smoke `planning liquidity build` e `planning liquidity demo`.
- Eseguito: `$env:PYTHONPATH='src'; python -m unittest tests.unit.test_liquidity_plan tests.unit.test_validate` -> 61 test OK.
- Eseguito: `$env:PYTHONPATH='src'; python -m family_office_engine.cli.main planning liquidity demo` -> OK.
- Eseguito: `$env:PYTHONPATH='src'; python -m unittest discover -s tests\unit` -> 294 test OK.
- Eseguito: `git diff --check` -> OK, con soli warning CRLF di Git.

## Documentazione aggiornata

- API e CLI per `liquidity-plan/v1`.
- Testing docs con comandi di verifica.
- Roadmap V4 con stato V4.2 e audit V4.2a.
- Roadmap index con prossimo incremento audit.
- Decision log con confini e limiti del contratto.
- Questo file con risultati e prossimo incremento deducibile.

## Criteri di completamento

- Gli asset sono assegnati a bucket di liquidita' versionati, riproducibili e tracciabili.
- La riserva minima usa mesi dichiarati e spese mensili esplicite.
- Il piano non usa per spese correnti asset non liquidabili.
- Non vengono calcolati rendimenti, imposte, FX, ottimizzazioni, scoring o raccomandazioni.
- Test mirati, CLI smoke e regression suite passano.
- V4.2 e' marcato `done`; V4 resta `in_progress`; il prossimo incremento deducibile e' V4.2a.

## Prossimo incremento deducibile

V4.2a - Code audit after liquidity plan.

## Rischi, esclusioni e blocker

- Fuori perimetro: decumulo, ottimizzazione, scoring V4, fiscalita', investimenti tax-aware, AI e uso di dati reali.
- Il piano non converte valute e non valuta rischi di mercato: segnala gap e warning.
- Asset con classificazione mancante, unknown o vincoli bloccanti non vengono promossi a riserva disponibile.
