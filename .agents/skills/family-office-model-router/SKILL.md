---
name: family-office-model-router
description: Classifica il task Family Office AI, seleziona custom agent/modello e registra routing intenzionale, deleghe ed escalation nel planner.
---

# Family Office AI model router

## Principio

Usa il modello meno costoso compatibile con rischio, fase e tipo di lavoro. La dimensione del repository non determina il tier. Mantieni le specializzazioni finanziaria e normativa separate.

| tier | tipo | agent | model | effort | write |
|---|---|---|---|---|---|
| low | discovery | fo_explorer | gpt-5.6-luna | low | no |
| low | document review | fo_docs_reviewer | gpt-5.6-luna | medium | no |
| low | docs/planner/agent config edit | fo_docs_editor | gpt-5.6-luna | medium | sì, solo confini indicati |
| medium | implementation planning | fo_planner | gpt-5.6-terra | medium | no |
| medium | code/config runtime entro contratti esistenti | fo_implementer | gpt-5.6-terra | medium | sì |
| review | regressioni, edge case, privacy, provenance, quality gate | fo_reviewer | gpt-5.6-terra | high | no |
| high | architettura, migrazione, trade-off cross-repository | fo_architect | gpt-5.6-sol | high | no |
| high | matematica finanziaria, leverage, cash-flow, opportunity cost | fo_financial_reviewer | gpt-5.6-sol | high | no |
| critical | fiscalità, pensioni, monitoraggio fiscale, compliance | fo_normative_reviewer | gpt-5.6-sol | xhigh | no |

## Decisione deterministica

1. Se il task introduce/interpreta fiscalità, pensioni, RW/IVAFE/IVIE, successione, AML/CRS/DAC o altra compliance → `critical/fo_normative_reviewer` per la fase normativa/review.
2. Altrimenti, se introduce o verifica IRR/NPV/DSCR, leverage, cash-flow, scenario assumptions, opportunity cost o ranking finanziario → `high/fo_financial_reviewer` per la fase finanziaria/review.
3. Altrimenti, se ci sono architettura, migrazione, ownership o trade-off non deciso → `high/fo_architect`.
4. Altrimenti, se è quality/audit/regressione indipendente → `review/fo_reviewer`.
5. Altrimenti, se serve un piano cross-module ma architettura, contratti e regole sono già decisi → `medium/fo_planner`.
6. Altrimenti, se `write_set` contiene codice runtime o configurazione applicativa → `medium/fo_implementer`.
7. Altrimenti, se `write_set` contiene solo docs, planner, AGENTS, `.codex` o `.agents` → `low/fo_docs_editor`.
8. Altrimenti, se è read-only documentale → `low/fo_docs_reviewer`.
9. Altrimenti → `low/fo_explorer` per discovery o `medium/fo_implementer` come default prudente.

Per T4, Sol non deve sostituire i calcoli deterministici. Il reviewer finanziario/normativo definisce o verifica formule, fonti, regole, assunzioni e scenari; l'implementazione viene delegata a Terra e torna allo specialista per il gate quando il playbook lo richiede.

Registra il blocco `routing` nel planner prima della prima delega. Aggiungi eventi `delegated`, `escalated` o `fallback` prima di cambiare agent/modello. Non salvare chain-of-thought.

La traccia runtime effettiva viene prodotta dagli hook e non va copiata nel planner:
`family-office-bootstrap/planning/.runtime/model-routing.ndjson`.
