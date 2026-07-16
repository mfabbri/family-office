# Workflow

## Data and calculation flow

1. Depositare documenti personali appena scaricati nel workspace `inbox/`.
2. Inventariare e organizzare i documenti in `documents/<fonte>` mantenendo provenance.
3. Importare e normalizzare solo documenti classificati.
4. Aggiornare household graph, ownership, asset availability e timeline.
5. Applicare rule pack versionati per giurisdizione e periodo.
6. Generare cashflow, simulazioni, stress test e confronti.
7. Produrre evidence bundle, report e decision dossier.
8. Registrare snapshot, lineage, data gaps e decision log.

## Development flow

```text
roadmap-index
  → current-next-increment
  → contract/fixture
  → implementation
  → tests
  → documentation and decision log
  → roadmap status
  → next increment
```

L'agente seleziona un solo micro-incremento per sessione, salvo richiesta esplicita. Un incremento bloccato genera un passo abilitante; non viene saltato.

## Normative flow

```text
authoritative source
  → family-office-knowledge
  → versioned rule pack
  → synthetic tests
  → engine integration
  → regression scenarios
```

## AI flow

```text
question
  → intent
  → inspectable execution plan
  → deterministic tools
  → evidence bundle
  → cited explanation
```

L'LLM non modifica facts o assunzioni approvate e non esegue direttamente calcoli fiscali, previdenziali o finanziari.
