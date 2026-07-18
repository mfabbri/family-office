# Current Next Increment

## ID e titolo

V3.9 - Multi-objective scoring.

## Stato

`done`

## Roadmap

`docs/roadmap/roadmap-v3-decision-core.md`

## Motivazione e dipendenze

La roadmap V3 resta la prima roadmap non completata secondo `roadmap-index.md`. L'incremento corrente precedente V3.8 era `done`; dall'ultimo audit periodico V3.6a sono stati completati tre incrementi funzionali (`V3.7`, `V3.8`, `V3.9`), quindi non scatta ancora la cadenza audit. Il primo incremento `planned` con dipendenze soddisfatte era V3.9.

Dipendenze verificate:

- V3.7 `decision-scenario/v2` e' `done`.
- V3.8 `sensitivity-analysis/v1` e' `done`.
- V3.9 non richiede nuove fonti normative o dati personali reali.

## Repository coinvolti

- `family-office-engine`: contratto, scorer deterministico, CLI, test, fixture sintetica e documentazione.
- `family-office-rules`: rule pack tecnico `decision-score-policy/v1` con metriche ammesse, orientamento e limiti di normalizzazione.
- `family-office-workspace`: solo come destinazione degli snapshot privati quando la CLI viene eseguita su dati reali.

## Input attesi e classificazione dati

- `decision-scenario/v2`: snapshot privato o sintetico.
- `sensitivity-analysis/v1`: snapshot privato o sintetico, usato come fonte di contesto/gap.
- Specifica scoring in JSON: alternative, metriche esplicite, pesi dichiarati, soglie opzionali e metadati.
- Rule pack `decision-score-policy/v1`: metriche supportate, orientamento (`higher_is_better`/`lower_is_better`) e range di normalizzazione.
- Test solo con fixture sintetiche, senza dati personali.

## Output e contratti prodotti o modificati

- Nuovo snapshot `decision-score/v1`.
- Scorer deterministico che normalizza metriche esplicite, applica pesi dichiarati e produce punteggi separati per metrica e totale pesato.
- Ranking stabile con gestione di pareggi.
- Data gaps per metriche mancanti, pesi mancanti, metriche non consentite dal policy pack o input sorgenti parziali.
- Hash riproducibile del contenuto normalizzato.
- CLI `scenarios score`.

## File modificati

- `family-office-engine/src/family_office_engine/services/decision_score.py`
- `family-office-engine/src/family_office_engine/cli/main.py`
- `family-office-engine/tests/unit/test_decision_score.py`
- `family-office-engine/tests/unit/test_validate.py`
- `family-office-engine/examples/decision-score-input-sample.json`
- `family-office-rules/decision/score-policy-v1.json`
- `family-office-rules/decision/README.md`
- `family-office-rules/docs/changelog.md`
- `family-office-engine/docs/api.md`
- `family-office-engine/docs/cli.md`
- `family-office-engine/docs/testing.md`
- `family-office-engine/docs/roadmap/roadmap-v3-decision-core.md`
- `family-office-engine/docs/decision-log.md`
- `family-office-engine/docs/current-next-increment.md`

## Test e verifiche eseguite

- Due alternative complete producono `decision-score/v1`, punteggi normalizzati, totale pesato, ranking stabile e hash riproducibile.
- Cambiare pesi cambia il ranking quando le metriche lo giustificano.
- Pareggi producono stesso rank e ordinamento stabile.
- Metrica mancante genera gap esplicito e alternativa parziale esclusa dal ranking.
- Metrica non ammessa dal policy pack genera gap esplicito.
- Snapshot sorgente con schema errato viene rigettato.
- CLI `scenarios score` scrive snapshot e stampa stato, alternative, ranking e gap.
- Test mirati: `Ran 7 tests in 0.054s - OK`.
- Regression suite engine: `Ran 256 tests in 1.568s - OK`.

## Criteri di completamento

- `decision-score/v1` valuta alternative con metriche e pesi espliciti, mantenendo metriche separate dal totale.
- Il ranking non dipende da una singola percentuale di successo e resta riproducibile.
- Facts, assunzioni, metriche, pesi, limiti e data gaps restano separati.
- Lo scorer non calcola imposte, rendimenti, pensioni, metriche finanziarie non fornite o raccomandazioni.
- Test mirati e regression suite passano.
- Roadmap, current increment, decision log e documentazione sono aggiornati.

## Rischi, esclusioni e blocker

- Fuori perimetro: raccomandazione finale, dossier Markdown, ottimizzazione, calcolo delle metriche sottostanti, simulazioni, fiscalita', pensioni e consulenza di investimento.
- Lo scoring e' descrittivo e deterministicamente pesato; la revisione umana resta necessaria prima di interpretarlo come decisione.

## Risultati

Incremento completato.

- Implementato `decision-score/v1` con servizio `build_decision_score`.
- Aggiunta CLI `scenarios score`.
- Aggiunto rule pack tecnico `family-office-rules/decision/score-policy-v1.json`.
- Aggiunta fixture sintetica `examples/decision-score-input-sample.json`.
- Aggiunti test unitari e smoke CLI.
- Aggiornate API, CLI docs, testing docs, roadmap V3, decision log e changelog rules.

## Prossimo incremento deducibile

Dopo V3.9, il prossimo incremento deducibile secondo la roadmap V3 e' V3.10 - Explainable recommendation dossier.
