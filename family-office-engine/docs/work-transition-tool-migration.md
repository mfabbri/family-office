# Work-transition tool migration

V4.19 registers the V4.16-V4.18 scenario tools alongside the existing `work-exit-feasibility/v1` tool. The registry contains both families; existing IDs and schema versions remain stable.

## Choose the contract

| Tool ID | Input/output schema | Use |
|---|---|---|
| `planning.work_exit_feasibility.build` | `work-exit-feasibility-input/v1` → `work-exit-feasibility/v1` | Existing evidence-based feasibility flow. Continue using this ID for existing clients; it is not the phased-work scenario optimizer. |
| `planning.work_transition_simulation.build` | `work-transition-simulation/v1` → same | Monthly projection from explicit assumptions, including optional seeded permutations of the declared return path. |
| `planning.work_transition_candidates.build` | `work-transition-candidate-set/v1` → same | Generate bounded, explained work-transition candidates; it does not rank or recommend. |
| `planning.work_transition_optimizer.build` | `work-transition-optimizer/v1` → same | Compare a V4.17 candidate set with explicit constraints and objective. |

No automatic conversion occurs between the legacy input and the new scenario contracts. Existing clients can continue to use the legacy tool and migrate only when they intend to submit explicit scenario assumptions and constraints.

## Invocation

Each new adapter accepts exactly `input_path` and `output_path` through `invoke_registered_tool`. The JSON input must be an object for the declared schema version; the output is written to the explicit destination and also returned in `tool-invocation/v1`. Input and output paths must differ. Unsupported tool IDs, output versions, malformed JSON, missing parameters and unknown parameters fail explicitly.

The scenario sequence is simulation → candidate generation → optimizer. Candidate generation consumes `work-transition-simulation/v1`; optimization consumes the returned `work-transition-candidate-set/v1`. Use the schema version declared by each registry entry.

## Meaning and boundaries

All future income, pension cash flows, return paths, costs and tax amounts remain declared scenario assumptions. These tools do not calculate tax or create pension rights. `pension_entitlement` remains `not_assessed` with verified fields null unless a separate source-bound record is supplied. A projection date is not a legally available pension date, administrative recognition, payment date or recommendation.

The legacy tool remains an independent contract. It must not be silently substituted for the scenario optimizer, and its historical schema and behavior must not be inferred from the new V4.18 outputs.
