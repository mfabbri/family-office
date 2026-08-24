# Model routing

Use a hybrid strategy. The main agent remains on `gpt-5.5` for predictable everyday work, while specialist subagents use exact GPT-5.6 variants. Never configure the unsuffixed alias `gpt-5.6`.

| Tier | Model | Reasoning | Typical use |
|---|---|---:|---|
| economy | `gpt-5.6-luna` | low | bounded discovery, inventory, repetitive checks |
| standard | `gpt-5.5` | medium | ordinary implementation, bug fixes, documentation |
| advanced | `gpt-5.6-terra` | high | cross-module review, difficult debugging, design validation |
| critical | `gpt-5.6-sol` | high or xhigh | tax, pension, financial calculations, architecture, migrations |

## Routing rules

1. Start the main session with `gpt-5.5`.
2. Keep T0-T2 work in the main agent unless a bounded read-only exploration is cheaper to delegate to Luna.
3. Use Terra only for independent technical review of T3-T5 changes.
4. Use Sol only for normative, financial, pension, schema, or architecture-critical review.
5. Per incrementi V4B Work Transition usare `fo_retirement_transition_reviewer` come review Sol read-only quando cambiano timeline, netto da lavoro, contribuzione, diritto/decorrenza, RITA o optimizer.
6. Do not spawn more than one specialist unless their questions are independent.
7. Do not use a specialist merely to restate work already completed by the main agent.
8. Escalate reasoning before escalating model count.

## Compatibility

Valid GPT-5.6 identifiers are:

- `gpt-5.6-sol`
- `gpt-5.6-terra`
- `gpt-5.6-luna`

The alias `gpt-5.6` must not appear in executable Codex configuration.
