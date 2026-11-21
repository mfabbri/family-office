# ADR 2026-11-21: Separate pension entitlement from financial projections

- Status: accepted
- Decision owner: Family Office AI roadmap authorization, 2026-11-21
- Scope: V4B retirement bridge, decumulation, work-transition comparison and optimizer

## Context

The V4.14 integrated gate covers source-bound pension events and legally supportable conclusions. It must remain strict for eligibility, official recognition, effective dates, verified amounts and payments. At the same time, a family can compare financially explicit work-transition assumptions without asserting that a future pension event is legally established.

## Decision

Maintain two distinct data and computation tracks:

1. `pension_entitlement` contains source-bound facts, applicable rule/version and period, evidence provenance, and separately qualified screening, eligibility, recognition, effective-date, amount and payment states. Unsupported conclusions remain `null`/`not_assessed` with `data_gaps`.
2. `scenario_projection` contains declared future assumptions and deterministic financial calculations: work income, household cash flow, hypothetical pension cash flows, investment assumptions, inflation, parametrized tax inputs and available assets. Its outputs are projections, never verified entitlement.

The projection engine may accept verified entitlement streams as optional inputs. It may also accept explicitly hypothetical pension streams, tagged `scenario_assumption`; these must not be serialized into entitlement fields or used as evidence. Every result identifies its assumptions, provenance, gaps and projection period.

## Roadmap effect

- Re-scope V4.15 to implement a scenario-only monthly retirement bridge and compare 100%, 60% and 0% work-income assumptions. Its prerequisites are V4.2, V4.3 and V4.5. V4.14, RITA V2 and future pension certification are not prerequisites for this independent projection slice.
- Keep the V4.14 parent and every legal entitlement claim gated by its own integrated source, temporal, review and non-inference requirements. Optional verified pension facts can join projections only when available.
- V4.16 consumes V4.15 projections for deterministic decumulation and sequence-risk work. V4.17/V4.18 consume scenario candidates and compare them; any output described as a legally available retirement date still depends on verified entitlement evidence.
- V4.19 and V4.20 retain their integration and end-to-end gates. Their golden projection can run with synthetic assumptions and show pension entitlement as gaps; a verified timeline remains separately gated.
- This ADR changes dependency edges only for financial scenario capabilities. It does not close V4.14, activate Rules v6 for entitlement decisions, change legal rules, or grant a downstream legal conclusion.

## Initial projection contract

Input: synthetic or workspace-local household identifier; as-of month; projection month count; opening liquid assets; monthly household spending; explicit monthly full-time **net** earned-income assumption; annual inflation and return assumptions; and optional hypothetical pension monthly **net** amount/start month with explicit assumption label and provenance. Net income is supplied as an assumption; the projection does not compute tax. The 60% work case scales the declared net full-time amount linearly as a scenario assumption.

The engine deterministically emits 3 scenarios with fixed work factors `1.00`, `0.60`, and `0.00`, monthly net income, expenses, net cash flow, requested/actual asset withdrawals, shortfall and closing available assets, cumulative funding need for months where work income is zero, assumptions, `data_gaps`, and `scenario_projection` status. Pension entitlement fields remain `null` unless separately supplied as a verified, source-bound stream; hypothetical inputs are emitted only under scenario assumptions.

## Consequences and acceptance tests

- Financial comparisons can progress while V4.14 remains blocked.
- No pension right, eligibility, recognition, start date or verified amount is inferred from an assumption.
- Golden tests use synthetic values and exact Decimal arithmetic; test outputs are reproducible.
- A negative test proves hypothetical pension data cannot populate verified entitlement fields.
- Tax is a declared parameter in later scopes; this first slice does not calculate statutory tax.
- Roadmap dependencies and the current planner identify V4.15 as the active increment; no other increment is started in parallel.
