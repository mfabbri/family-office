# Current Next Increment

## ID e titolo

V4.10 - Strategy optimizer and implementation plan.

## Stato

`planned`

## Roadmap

`docs/roadmap/roadmap-v4-wealth-planning.md`

## Motivazione e dipendenze

V4.9 e' stato completato e ha introdotto `estate-plan/v2` con successione e donazioni V2. Il prossimo incremento pianificato nella roadmap V4 e' V4.10, che combina le opzioni V4 in pacchetti coerenti e piano operativo.

V4.10 dipende da V4.2-V4.5, V4.6a-V4.6d e V4.7-V4.9. Prima di selezionare o implementare l'incremento funzionale eseguire sempre:

```text
python family-office-engine/src/family_office_engine/governance/roadmap_audit.py
```

## Stato implementazione

Pianificato.

V4.9 ha registrato:

- Knowledge note successoria verificata il 2026-07-29 e rule pack `it.estate-plan.2026.v2`.
- Contratto `estate-plan/v2`.
- CLI `planning estate build/demo` con default del workspace e fixture sintetica.
- `planning estate demo` -> `partial 2 scenarios, 3 conflicts, 4 gaps`.
- `$env:PYTHONPATH='src'; python -m unittest tests.unit.test_estate_plan` -> 5 test OK.
- `$env:PYTHONPATH='src'; python -m unittest tests.unit.test_validate.ValidateCliTest.test_main_estate_baseline_returns_success tests.unit.test_validate.ValidateCliTest.test_main_planning_estate_demo_returns_summary` -> 2 test OK.
- `$env:PYTHONPATH='src'; python -m unittest discover -s tests\unit` -> 452 test OK.
- `python family-office-engine/src/family_office_engine/governance/roadmap_audit.py` -> OK.

## Piano operativo V4.10

1. Confermare contratti e snapshot V4 disponibili: goals, liquidity, decumulation, contribution, tax-aware portfolio, cross-border IT-ES, real estate, protection, estate plan e work-exit.
2. Definire il perimetro minimo `wealth-strategy/v1`: 2-4 pacchetti coerenti, costi/dipendenze/reversibilita', checklist 90/180 giorni, rischi e gap.
3. Evitare nuove regole fiscali/finanziarie se non strettamente necessarie; in caso contrario applicare `knowledge -> rules -> tests -> engine`.
4. Implementare solo composizione deterministica sopra output gia' prodotti, senza ottimizzazione opaca o raccomandazioni non supportate.

## Criteri di completamento V4.10

- `wealth-strategy/v1` propone 2-4 alternative comparabili e motivate da evidenze deterministiche.
- Ogni pacchetto include piano 90/180 giorni, costi, dipendenze, reversibilita', controlli, rischi e gap.
- Test mirati e regression pertinente verdi.
- Stato roadmap coerente e audit cadence verificata.
