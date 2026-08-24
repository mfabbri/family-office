# Codex configuration - Family Office AI

Questa configurazione applica routing esplicito per ridurre token e context churn senza abbassare l'affidabilita' dei task finanziari/normativi.

## Default

- main: `gpt-5.6-terra`, reasoning `medium`, verbosity `low`;
- fallback manuale: profilo `fallback55` -> `gpt-5.5`, reasoning `medium`;
- explorer: `gpt-5.6-luna`, low;
- planner/reviewer tecnico: `gpt-5.6-terra`, medium/high;
- reviewer finanziario/normativo: `gpt-5.6-sol`, high;
- `xhigh` solo tramite profilo `critical` o escalation esplicita.

## Profili

```text
codex --profile standard
codex --profile economy
codex --profile deep
codex --profile critical
codex --profile fallback55
```

Il repository usa solo ID GPT-5.6 completi (`-luna`, `-terra`, `-sol`) per evitare incompatibilita' osservate con l'alias non suffissato in sessioni Codex autenticate via ChatGPT.

## Multi-agent hygiene

- massimo due subagent concorrenti;
- `interrupt_message = false` per evitare messaggi di interruzione non necessari nel contesto;
- default subagent Luna/low;
- specialisti read-only e output concisi;
- il main agent resta proprietario di implementazione e test.

Vedi `family-office-bootstrap/docs/playbooks/02-model-routing.md` e `03-subagent-policy.md`.
