# Current Next Increment

## ID e titolo

V3.6 - Lifecycle expense model.

## Stato

`done`

## Roadmap

`docs/roadmap/roadmap-v3-decision-core.md`

## Motivazione e dipendenze

La roadmap V3 resta la prima roadmap non completata secondo `roadmap-index.md`. L'incremento corrente precedente V3.5e e' `done`; il primo incremento `planned` con dipendenze soddisfatte e' V3.6.

Dipendenze verificate:

- V3.1 `household-facts/v1` e' `done` e fornisce il contesto familiare/personale a cui collegare spese per persona o nucleo.
- V3.4 `timeline-events/v1` e' `done` e fornisce eventi puntuali, periodici e date di scenario.
- V3.5e `pension-income/v1` e' `done` e non blocca il modello spese.
- Ultimo audit: V3.5c-c. Dopo V3.5c, V3.5d e V3.5e ci sono tre incrementi funzionali completati; V3.6 e' il quarto, quindi l'audit e' necessario prima di procedere a V3.7.

## Repository coinvolti

- `family-office-engine`: contratto, servizio deterministico, CLI, test e documentazione.
- `family-office-workspace`: solo come destinazione degli snapshot privati quando la CLI viene eseguita su dati reali.

## Input attesi e classificazione dati

- `household-facts/v1`: snapshot privato o sintetico per collegare persone e nucleo.
- `timeline-events/v1`: snapshot privato o sintetico per applicare eventi una tantum o periodici.
- Piano spese esplicito fornito come JSON privato nel workspace o fixture sintetica nei test.
- Nessun dato personale reale nei repository software.

## Output e contratti prodotti o modificati

- Nuovo snapshot `lifecycle-expenses/v1`.
- Servizio che produce cashflow annuo di spesa per categoria, fase di vita, periodo, inflazione opzionale, persona/nucleo e provenance.
- CLI `expenses build-lifecycle`.
- Totali prudenti: il servizio usa solo importi espliciti in EUR, non stima spese mancanti, non calcola fiscalita', rendimenti, bisogni sanitari o inflazione implicita.

## File modificati

- `family-office-engine/src/family_office_engine/services/lifecycle_expenses.py`
- `family-office-engine/src/family_office_engine/cli/main.py`
- `family-office-engine/tests/unit/test_lifecycle_expenses.py`
- `family-office-engine/tests/unit/test_validate.py`
- `family-office-engine/docs/api.md`
- `family-office-engine/docs/cli.md`
- `family-office-engine/docs/testing.md`
- `family-office-engine/docs/roadmap/roadmap-v3-decision-core.md`
- `family-office-engine/docs/decision-log.md`
- `family-office-engine/docs/current-next-increment.md`

## Test e verifiche eseguite

- Spesa ricorrente con inflazione annua esplicita e importi annuali riproducibili.
- Periodo limitato con start/end year e nessuna spesa fuori finestra.
- Spesa una tantum agganciata a un anno evento.
- Categorie mancanti o importi non validi generano gap/errori senza inventare valori.
- CLI `expenses build-lifecycle` scrive snapshot e stampa stato, anni, totale e gap.
- Test mirati: `Ran 7 tests in 0.034s - OK`.
- Regression suite engine: `Ran 237 tests in 1.309s - OK`.

## Criteri di completamento

- Il sistema produce `lifecycle-expenses/v1` da input espliciti senza duplicare spese manuali nel simulatore.
- Le spese sono annualizzate e separate per categoria/fase/persona o nucleo, con provenance e data gaps.
- L'inflazione e' applicata solo quando dichiarata nel piano spese.
- Test mirati e regression suite passano.
- Roadmap, current increment, decision log e documentazione sono aggiornati.

## Rischi, esclusioni e blocker

- Fuori perimetro: stima automatica delle spese familiari, fiscalita', costo sanitario attuariale, cambio valuta, ottimizzazione, scoring e raccomandazioni.
- Gli importi sono input di scenario interni, non budget certificati o consulenza finanziaria.

## Risultati

Incremento completato.

- Implementato `lifecycle-expenses/v1` con servizio `build_lifecycle_expenses`.
- Aggiunta CLI `expenses build-lifecycle`.
- Aggiunti test unitari e smoke CLI con fixture sintetiche.
- Aggiornate API, CLI docs, testing docs, roadmap V3 e decision log.

## Prossimo incremento deducibile

Dopo V3.6, la cadenza audit richiede `V3.6a - Code audit cadence 3 before scenario contract V2` prima di procedere a V3.7.
