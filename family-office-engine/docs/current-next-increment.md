# Current Next Increment

## ID e titolo

V4.1 - Goals and constraints model.

## Stato

`done`

## Roadmap

`docs/roadmap/roadmap-v4-wealth-planning.md`

## Motivazione e dipendenze

`current-next-increment.md` precedente e `roadmap-index.md` marcano V3 come `done` e il gate V3 -> V4 come superato. La prima roadmap non completata e' V4; il primo incremento `planned` con dipendenze soddisfatte e' V4.1.

V4.1 formalizza obiettivi, priorita', soglie minime, orizzonte, rischio, liquidita', eventi familiari e vincoli legali in un contratto deterministico. Gli incrementi successivi V4.2-V4.10 potranno usare questi vincoli dichiarati invece di preferenze implicite.

Dipendenze verificate:

- Gate V3 -> V4 `passed`.
- `decision-scenario/v2`, `decision-score/v1` e `decision-dossier/v1` sono disponibili e tracciabili.
- Non serve nuova normativa o rule pack fiscale per V4.1.
- Non scatta code audit: dall'ultimo audit V3.10a sono stati completati tre incrementi funzionali (`V3.10b`, `V3.10c`, `V3.10d`), quindi V4.1 puo' procedere.

## Repository coinvolti

- `family-office-engine`: contratto `planning-goals/v1`, validatore, snapshot builder, CLI, fixture sintetica, test e documentazione.
- `family-office-workspace`: destinazione privata attesa per input e snapshot reali; nessun dato reale viene copiato nel repository software.
- `family-office-rules`, `family-office-knowledge`, `family-office-bootstrap`: nessuna modifica prevista.

## Input attesi e classificazione dati

- Input JSON `planning-goals/v1` con obiettivi, vincoli, preferenze di rischio/liquidita', orizzonte e riferimenti opzionali a eventi di `timeline-events/v1`.
- Snapshot opzionale `timeline-events/v1` per validare riferimenti a eventi familiari.
- Fixture sintetiche nell'engine; dati reali solo nel workspace privato.

## Output e contratti prodotti o modificati

- Contratto e snapshot `planning-goals/v1`.
- Validatore deterministico con data gaps per campi mancanti, riferimenti timeline mancanti e vincoli incompleti.
- Errori bloccanti per ID duplicati, priorita' non positive, soglie incoerenti, orizzonti invalidi e riferimenti a vincoli/obiettivi inesistenti.
- CLI per validare input goals e scrivere snapshot nel workspace.

## File modificati

- `family-office-engine/src/family_office_engine/services/planning_goals.py`
- `family-office-engine/src/family_office_engine/cli/main.py`
- `family-office-engine/tests/unit/test_planning_goals.py`
- `family-office-engine/tests/unit/test_validate.py`
- `family-office-engine/examples/planning-goals-sample.json`
- `family-office-workspace/household/planning-goals.draft.json`
- `family-office-workspace/household/household-input-guide.md`
- `family-office-engine/docs/api.md`
- `family-office-engine/docs/cli.md`
- `family-office-engine/docs/testing.md`
- `family-office-engine/docs/current-next-increment.md`
- `family-office-engine/docs/roadmap/roadmap-v4-wealth-planning.md`
- `family-office-engine/docs/decision-log.md`

## Test e verifiche

- Input completo produce snapshot `complete`, hash stabile e nessun gap.
- Obiettivi incompatibili o soglie min/max incoerenti vengono rigettati.
- Priorita' duplicate o non positive vengono rigettate.
- Riferimento timeline mancante produce gap esplicito.
- Campi opzionali mancanti o `unknown` producono data gaps, non valori inventati.
- CLI smoke `planning goals validate`.
- Eseguito: `$env:PYTHONPATH='src'; python -m unittest tests.unit.test_planning_goals tests.unit.test_validate` -> 55 test OK.
- Eseguito: `$env:PYTHONPATH='src'; python -m unittest discover -s tests\unit` -> 281 test OK.
- Eseguito: `git diff --check` -> OK.

## Documentazione aggiornata

- API e CLI per `planning-goals/v1`.
- Testing docs con comandi di verifica.
- Roadmap V4 con stato V4.1.
- Decision log con confini e limiti del contratto.
- Questo file con risultati e prossimo incremento deducibile.
- Guida workspace con il nuovo draft privato `planning-goals.draft.json`.

## Criteri di completamento

- Gli obiettivi e i vincoli sono rappresentati in modo versionato, validabile e riproducibile.
- L'output mantiene separati obiettivi, vincoli, preferenze, timeline refs, data gaps e limiti.
- Non vengono calcolati rendimenti, imposte, ottimizzazioni, raccomandazioni o strategie.
- Test mirati, CLI smoke e regression suite passano.
- V4.1 e' marcato `done`; V4 e' `in_progress`; il prossimo incremento deducibile resta V4.2.

## Prossimo incremento deducibile

V4.2 - Liquidity buckets and emergency reserve.

## Rischi, esclusioni e blocker

- Fuori perimetro: liquidity buckets, emergency reserve, ottimizzazione, scoring V4, fiscalita', investimenti tax-aware, AI e uso di dati reali.
- Il contratto non decide trade-off tra obiettivi: registra priorita' e soglie dichiarate.
- Se emergono obiettivi incompatibili non risolvibili deterministicamente, vengono registrati come errori o data gaps, non mediati dal servizio.
