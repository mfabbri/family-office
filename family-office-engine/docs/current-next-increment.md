# Current Next Increment

## ID e titolo

V4.9 - Succession and donation planning V2.

## Stato

`planned`

## Roadmap

`docs/roadmap/roadmap-v4-wealth-planning.md`

## Motivazione e dipendenze

V4.8c e' stato completato e ha riallineato la roadmap all'obiettivo principale di trovare la prima data sostenibile di uscita dal lavoro. Il prossimo incremento pianificato nella roadmap V4 e' V4.9, che estende successione e donazioni V2 usando gli elementi patrimoniali e di protezione gia' modellati.

V4.9 dipende da V2.8, V3.2, V4.7, V4.8 e V4.8a. Prima di selezionare o implementare l'incremento funzionale eseguire sempre:

```text
python family-office-engine/src/family_office_engine/governance/roadmap_audit.py
```

## Stato implementazione

Pianificato.

V4.8c ha registrato:

- Knowledge note INPS verificata il 2026-07-29 e rule pack `it.inps-theoretical-pension.2026.v1`.
- Contratto `work-exit-feasibility/v1` e componente `inps-theoretical-pension/v1`.
- CLI `planning work-exit build/demo` con default del workspace e fixture sintetiche.
- `planning work-exit demo` -> `complete first=2039-01-01, 2 candidates, 0 gaps`.
- `$env:PYTHONPATH='src'; python -m unittest tests.unit.test_work_exit_feasibility` -> 5 test OK.
- `$env:PYTHONPATH='src'; python -m unittest tests.unit.test_validate.ValidateCliTest.test_main_planning_work_exit_demo_returns_first_sustainable_date` -> OK.
- `$env:PYTHONPATH='src'; python -m unittest discover -s tests\unit` -> 446 test OK.
- `python family-office-engine/src/family_office_engine/governance/roadmap_audit.py` -> OK.

## Piano operativo V4.9

1. Confermare i contratti e le fixture disponibili da V2.8, V3.2, V4.7, V4.8 e V4.8a.
2. Definire il perimetro minimo `estate-plan/v2`: quote, beneficiari, asset illiquidi, polizze, estero, donazioni pregresse, liquidita' e conflitti.
3. Applicare il playbook normativo se vengono codificate regole successorie o fiscali: `knowledge -> rules -> tests -> engine`.
4. Implementare il minimo servizio/CLI deterministico e testare casi sintetici prima di aggiornare lo stato.

## Criteri di completamento V4.9

- `estate-plan/v2` segnala conflitti civilistici e gap dati senza proporre schermi opachi.
- Beneficiari, quote, asset illiquidi, polizze, estero e donazioni pregresse sono tracciati con provenance.
- Test mirati e regression pertinente verdi.
- Stato roadmap coerente e audit cadence verificata.
