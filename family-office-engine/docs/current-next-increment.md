# Current Next Increment

## ID e titolo

V5.1 - Tool registry and invocation contract.

## Stato

`done`

## Roadmap

`docs/roadmap/roadmap-v5-ai-orchestration.md`

## Motivazione e dipendenze

V4 e' stata completata con V4.10, che ha introdotto `wealth-strategy/v1` e il piano operativo 90/180 giorni. Il gate V4 -> V5 richiede tool deterministici versionati, output con fonti/ipotesi/limiti/confidence, casi sintetici e nessun calcolo fiscale o finanziario affidato a LLM.

V5.1 e' il primo incremento della roadmap V5 e registra i tool disponibili con schema input/output, prerequisiti, livello di rischio e policy di autorizzazione. Prima di selezionare o implementare l'incremento funzionale eseguire sempre:

```text
python family-office-engine/src/family_office_engine/governance/roadmap_audit.py
```

## Stato implementazione

Completato.

V5.1 ha registrato:

- Contratto `tool-registry/v1`.
- Servizio deterministico `family_office_engine.services.tool_registry`.
- Adapter locale per invocare solo tool registrati, con versione richiesta e input validato.
- CLI `orchestration tool-registry build/list`.
- `orchestration tool-registry build` -> `complete 15 tools`.
- `orchestration tool-registry list` -> listing leggibile di 15 tool con schema output, rischio e policy.
- `$env:PYTHONPATH='family-office-engine/src'; python -m unittest family-office-engine.tests.unit.test_tool_registry family-office-engine.tests.unit.test_validate.ValidateCliTest.test_main_orchestration_tool_registry_build_returns_summary` -> 7 test OK.
- `$env:PYTHONPATH='family-office-engine/src'; python -m unittest discover -s family-office-engine\tests\unit` -> 464 test OK.
- `python family-office-engine/src/family_office_engine/governance/roadmap_audit.py` -> OK (`functional_since_audit=1`, `audit_due=false`).

## Piano operativo V5.1

1. Confermati pattern locali per contratti, servizi, CLI e test.
2. Definito perimetro minimo `tool-registry/v1`: identificativo tool, versioni I/O, prerequisiti, rischio, autorizzazione, data gaps, provenance.
3. Implementato adapter deterministico che non esegue funzioni interne non registrate.
4. Esposta CLI breve di build/list del registry.
5. Nessun LLM produce calcoli, valori fiscali, previdenziali o finanziari.

## Criteri di completamento V5.1

- `tool-registry/v1` elenca le principali capability decisionali V4 con contratti versionati e policy.
- Un adapter locale invoca solo tool registrati e rifiuta tool inesistenti o versioni incompatibili.
- Test mirati e regression pertinente verdi.
- Stato roadmap coerente e audit cadence verificata.
