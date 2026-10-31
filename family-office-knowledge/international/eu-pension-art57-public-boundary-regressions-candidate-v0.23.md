# Art. 57 public-boundary regression contract — candidate v0.23

## Scope and version

This candidate is a technical, regression-test-only response to the exact-version NO-GO for runtime candidate v0.22 / `fo-art57-c14n-v4`. Jurisdiction and legal context remain the EU coordination of statutory old-age pensions under Regulation (EC) No 883/2004, Article 57, and Regulation (EC) No 987/2009; this candidate adds no legal interpretation and no new effective-period claim. It does not approve runtime use.

## Required public-boundary regressions

Tests must invoke the public `build_it_es_eu_pension_pro_rata` service and assert the returned snapshot, not only call private assessment helpers.

1. For Article 57(4) Annex-matched and non-relief outcomes, mutate the synthetic evidence registry so it is invalid. The public snapshot must expose Article 57 `not_assessed`, non-empty `data_gaps`, no calculable pro-rata amount, and no inferred competent/paying institution.
2. Reconcile root and root-institution Article 57(1) evidence in both directions using synthetic fixtures. Cover mismatched duration/unit, comparator/unit, legislation identity/version, autonomous-right result and relief predicate as applicable to each fixture. Each contradiction must fail closed in the public snapshot with `not_assessed` and non-empty `data_gaps`; the output must not contain a calculable pro-rata amount or payer inference.
3. Retain the v0.21 evidence-registry integrity regressions and v0.22 private-level tests; public-boundary tests supplement rather than replace them.
4. The citation-index test must assert the exact document identifier for this v0.23 candidate. Keep assertions for earlier versions, including v0.22.

## Limits

All test data is synthetic. The tests prove service-boundary behavior only; they do not establish an individual entitlement, institutional finding, payer, or national-law sufficiency. Annex VIII remains fail-closed without a complete applicable machine-readable catalogue. c14n-v4 and the v0.22 evidence rules are unchanged. Runtime code changes are permitted only if these public regressions reproduce a concrete defect, and must preserve all existing fail-closed behavior.

## Review boundary

Any GO applies only to the exact v0.23/c14n-v4 artifacts reviewed, the synthetic service-output regressions above, and citation coverage. No GO transfers to v0.22 or approves V4.14w/V4.14, whose other national, temporal, and catalogue gaps remain.
