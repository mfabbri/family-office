# Model routing policy v3.1

Data: 2026-08-30

## Obiettivo

Routing Codex multi-model reale, proporzionato al rischio e verificabile, con due livelli:

- decisione intenzionale versionata nel planner;
- modello effettivamente eseguito registrato localmente dagli hook.

| Tier | Agent | Modello | Reasoning | Responsabilità |
|---|---|---|---|---|
| router | parent | Luna | medium | classificare, delegare, sintetizzare |
| low | fo_explorer | Luna | low | discovery read-only |
| low | fo_docs_reviewer | Luna | medium | review documentale read-only |
| low | fo_docs_editor | Luna | medium | docs/planner/config agent |
| medium | fo_planner | Terra | medium | planning cross-module delimitato |
| medium | fo_implementer | Terra | medium | codice e micro-feature deterministiche |
| review | fo_reviewer | Terra | high | quality/regressioni/privacy/provenance |
| high | fo_architect | Sol | high | architettura/migrazioni/trade-off |
| high | fo_financial_reviewer | Sol | high | matematica finanziaria/leverage/cash-flow |
| critical | fo_normative_reviewer | Sol | xhigh | fiscalità/pensioni/compliance |

## Regola T4

Separare il gate finanziario dal gate normativo:

- `fo_financial_reviewer` verifica formule, tempi dei flussi, leverage, scenari e opportunity cost;
- `fo_normative_reviewer` verifica fonti, giurisdizione, validità temporale, fiscalità/previdenza/compliance;
- i calcoli numerici restano deterministici e versionati;
- l'implementazione avviene con Terra dopo che contratti e regole sono chiari.

## Audit runtime

Gli hook `SessionStart`, `SubagentStart` e `SubagentStop` registrano sessione, evento, model slug, agent type/id e permission mode in:

```text
family-office-bootstrap/planning/.runtime/model-routing.ndjson
```

Il file non viene versionato e non contiene chain-of-thought.

## Guardrail

- nessun `[profiles.*]` project-local;
- mai usare l'alias eseguibile non suffissato `gpt-5.6`;
- nessuna escalation dovuta alla sola dimensione del repository;
- ogni fallback/escalation è esplicito nel planner;
- i playbook funzionali esistenti, inclusi investment opportunity e work-transition, restano autoritativi;
- nessun modello sostituisce rule pack e test per risultati fiscali, pensionistici o finanziari.
