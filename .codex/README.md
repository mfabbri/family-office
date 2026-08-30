# Codex model routing v3.1 — Family Office AI

## Runtime policy

Il parent è intenzionalmente economico e funge da router/controller:

- parent/controller: `gpt-5.6-luna` / `medium`;
- discovery: `fo_explorer` → Luna / `low`;
- docs review: `fo_docs_reviewer` → Luna / `medium`;
- docs/planner/agent-config edits: `fo_docs_editor` → Luna / `medium`;
- implementation planning: `fo_planner` → Terra / `medium`;
- implementation: `fo_implementer` → Terra / `medium`;
- quality review: `fo_reviewer` → Terra / `high`;
- architecture/migration: `fo_architect` → Sol / `high`;
- financial review: `fo_financial_reviewer` → Sol / `high`;
- normative/pension/compliance review: `fo_normative_reviewer` → Sol / `xhigh`.

Non usare `[profiles.*]` nel `.codex/config.toml` di progetto. Il routing runtime è realizzato tramite custom agent e planner persistente.

## Due livelli di tracciabilità

1. `family-office-bootstrap/planning/current-work.json` registra la route intenzionale.
2. `.codex/hooks.json` registra il modello effettivamente eseguito dal parent e dai subagent in `family-office-bootstrap/planning/.runtime/model-routing.ndjson`.

Il log runtime è locale e ignorato da Git. Non contiene chain-of-thought.

## Hook trust

Dopo una modifica agli hook project-local, usare `/hooks` in Codex per revisionarli e autorizzarli.

## Validazione

```powershell
python .\family-office-bootstrap\planning\validate-codex-model-routing.py
python -m json.tool .\family-office-bootstrap\planning\current-work.json
git diff --check
```

## Fallback

Se un modello non è disponibile nel client/account, il fallback deve essere esplicito nel planner. Non reintrodurre profili project-local solo per gestire il fallback.
