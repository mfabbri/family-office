# Current Next Increment

## ID e titolo

V3.5c-b - Spanish pension accrued percentage rules.

## Stato

`done`

## Roadmap

`docs/roadmap/roadmap-v3-decision-core.md`

## Motivazione e dipendenze

La roadmap V3 resta la prima roadmap non completata secondo `roadmap-index.md`. L'incremento corrente precedente, V3.5c-a, e' `done`; il prossimo incremento deducibile e' V3.5c - Spanish statutory pension estimator.

V3.5c pero' richiede ancora una regola previdenziale essenziale: la percentuale maturata oltre i primi 15 anni. Il baseline V3.5c-a codifica solo il 50% iniziale e dichiara la progressione successiva come deferred. Questo micro-incremento abilita V3.5c senza stimare ancora importi pensionistici.

Dipendenze verificate:

- V3.5b `spanish-contribution-reconciliation/v1` e' completato.
- V3.5c-a `spanish-statutory-pension-rule-pack/v1` e' completato.
- Il BOE, Real Decreto Legislativo 8/2015, testo consolidato aggiornato al 2026-02-04, espone Articolo 210 e Disposizione transitoria nona per la progressione percentuale.

## Repository coinvolti

- `family-office-knowledge`: aggiornamento della nota spagnola con progressione percentuale e fonte.
- `family-office-rules`: estensione del rule pack spagnolo con schedule percentuale transitoria.
- `family-office-engine`: validazione e lookup/calcolo deterministico della percentuale maturata.

## Input attesi e classificazione dati

- Fonti normative pubbliche ufficiali: BOE, testo consolidato della Ley General de la Seguridad Social.
- Nessun documento personale e nessun dato del workspace.

## Output e contratti

- Rule pack `spanish-statutory-pension-rule-pack/v1` esteso con `additional_month_schedule`.
- Servizio engine capace di:
  - validare la schedule percentuale;
  - rifiutare rule pack che dichiarano la progressione come deferred;
  - calcolare la percentuale maturata da mesi contributivi e anno di pensionamento.

## File previsti

- `family-office-knowledge/international/spain-pension.md`
- `family-office-rules/spain/statutory-retirement-general.json`
- `family-office-rules/spain/README.md`
- `family-office-engine/src/family_office_engine/services/spanish_pension_rules.py`
- `family-office-engine/tests/unit/test_spanish_pension_rules.py`
- `family-office-engine/docs/api.md`
- `family-office-engine/docs/testing.md`
- `family-office-engine/docs/roadmap/roadmap-v3-decision-core.md`
- `family-office-engine/docs/decision-log.md`

## Test e verifiche

- Done: unit test rule pack valido con schedule percentuale caricato con successo.
- Done: unit test rule pack con progressione percentuale deferred rigettato.
- Done: unit test percentuale 2026 con 15 anni = 50%.
- Done: unit test percentuale 2026 con 25 anni = 73.78%.
- Done: unit test percentuale 2027 con mesi oltre soglia e cap al 100%.
- Done: `$env:PYTHONPATH='src'; python -m unittest tests.unit.test_spanish_pension_rules`
- Done: `$env:PYTHONPATH='src'; python -m unittest discover -s tests/unit`

## Criteri di completamento

- La progressione percentuale ordinaria e transitoria e' versionata nel rule pack, con fonte BOE esplicita.
- Il loader rifiuta regole percentuali incomplete o non coperte da fonte.
- Il calcolo della percentuale maturata e' deterministico, capped al 100% e non produce importi pensionistici.
- La roadmap registra V3.5c-b come incremento abilitante tra V3.5c-a e V3.5c.

## Rischi, esclusioni e blocker

- Fuori perimetro: base reguladora, rivalutazione basi, integrazione lagune, massimali/minimi, anticipo, differimento, supplementi, fiscalita', coordinamento UE, importi mensili o annuali.
- Il rule pack non e' consulenza legale o previdenziale e non sostituisce calcoli ufficiali Seguridad Social.
- La fonte BOE consolidata e' informativa; per uso legale va verificata la pubblicazione ufficiale applicabile.

## Risultati

Incremento completato.

- Esteso `spanish-statutory-pension-rule-pack/v1` con schedule percentuale ordinaria 2023-2026 e dal 2027.
- Aggiornata knowledge note spagnola con Articolo 210, Disposizione transitoria nona e limiti operativi.
- Implementato `accrued_pension_percentage` nel loader/validatore spagnolo.
- Roadmap V3 aggiornata con micro-incremento V3.5c-b `done`.
- Decision log aggiornato.
- Test mirato: `Ran 9 tests in 0.015s - OK`.
- Regression suite engine: `Ran 214 tests in 2.150s - OK`.

## Prossimo incremento deducibile

Dopo V3.5c-b, il successivo incremento deducibile e' V3.5c - Spanish statutory pension estimator. Il primo passo di V3.5c potra' combinare basi riconciliate, parametri base reguladora e percentuale maturata, bloccando il risultato quando mancano basi o regole ancora fuori perimetro.
