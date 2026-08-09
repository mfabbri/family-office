# Current Next Increment

## ID e titolo

V4.10 - Strategy optimizer and implementation plan.

## Stato

`done`

## Roadmap

`docs/roadmap/roadmap-v4-wealth-planning.md`

## Motivazione e dipendenze

V4.9 e' stato completato e ha introdotto `estate-plan/v2` con successione e donazioni V2. Il prossimo incremento pianificato nella roadmap V4 e' V4.10, che combina le opzioni V4 in pacchetti coerenti e piano operativo.

V4.10 dipende da V4.2-V4.5, V4.6a-V4.6d e V4.7-V4.9. Prima di selezionare o implementare l'incremento funzionale eseguire sempre:

```text
python family-office-engine/src/family_office_engine/governance/roadmap_audit.py
```

## Stato implementazione

Completato.

V4.10 ha registrato:

- Contratto `wealth-strategy/v1`.
- Servizio deterministico `family_office_engine.services.wealth_strategy`.
- Input sintetico `examples/wealth-strategy-input-sample.json` e input workspace default `family-office-workspace/planning/wealth-strategy-input.json`.
- CLI `planning wealth-strategy build/demo` con default del workspace e demo sintetica.
- `planning wealth-strategy demo` -> `partial 3 packages, 3 comparable, 20 gaps`.
- `planning wealth-strategy build` con default workspace -> `blocked_insufficient_comparable_packages` con gap recuperabili quando mancano snapshot personali standard.
- `$env:PYTHONPATH='family-office-engine/src'; python -m unittest family-office-engine.tests.unit.test_wealth_strategy family-office-engine.tests.unit.test_validate.ValidateCliTest.test_main_planning_wealth_strategy_demo_returns_summary` -> 5 test OK.
- `$env:PYTHONPATH='family-office-engine/src'; python -m unittest discover -s family-office-engine\tests\unit` -> 457 test OK.
- `python family-office-engine/src/family_office_engine/governance/roadmap_audit.py` -> OK (`functional_since_audit=3`, `audit_due=false`).

## Piano operativo V4.10

1. Confermati contratti e snapshot V4 disponibili per composizione.
2. Definito perimetro minimo `wealth-strategy/v1`: 2-4 pacchetti coerenti, costi/dipendenze/reversibilita', checklist 90/180 giorni, rischi e gap.
3. Nessuna nuova regola fiscale/finanziaria introdotta.
4. Implementata composizione deterministica sopra output gia' prodotti, senza ottimizzazione opaca o raccomandazioni non supportate.

## Criteri di completamento V4.10

- `wealth-strategy/v1` propone 2-4 alternative comparabili e motivate da evidenze deterministiche.
- Ogni pacchetto include piano 90/180 giorni, costi, dipendenze, reversibilita', controlli, rischi e gap.
- Test mirati e regression pertinente verdi.
- Stato roadmap coerente e audit cadence verificata.
