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

## Audit best practices OpenAI — 2026-11-14

Il documento OpenAI dell'11 settembre 2026 raccomanda AGENTS concisi e contestuali, skill con trigger specifici e progressive disclosure, meno itinerari di istruzioni, e autonomia con criteri di done osservabili. La patch `dual-gate-v4.14` applica questi principi ai playbook e alle tre skill, senza cambiare `.codex/config.toml` né i TOML degli agent: il validator v3.1 e la compatibilità con il client installato hanno priorità. Verificare con `codex --version` e con il catalogo modelli effettivamente disponibile prima di una futura migrazione GPT-6/Astra.

Gli attuali `sandbox_mode = workspace-write`, `approval_policy = on-request` e `agents.max_concurrent_threads_per_session` risultano ancora opzioni riconosciute nella documentazione ufficiale Codex. Conservare i permessi restrittivi, i limiti di thread e gli hook revisionati; non impostare scorciatoie senza autorizzazione.

Controllare eventuali conflitti tra le nuove regole di `AGENTS.md` e i file più specifici dei sottorepository. Per la release del consumer pensionistico distinguere output `software_ready` da `normative_ready`.
