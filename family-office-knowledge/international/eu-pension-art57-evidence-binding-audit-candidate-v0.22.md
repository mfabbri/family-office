# Art. 57 evidence-binding runtime — candidate v0.22

## Scope

This is a bounded technical response to the exact-version NO-GO for v0.21/c14n-v4. It does not introduce a new interpretation of Regulation 883/2004 or 987/2009, determine a national entitlement, or make Annex VIII executable.

The v0.21 evidence-integrity checks are preconditions for every Article 57 assessment result. Validate the coordination manifest, full-perimeter record and evidence registry before returning any result, including `excluded_by_57_4` and `does_not_apply`. A missing, duplicate, unresolved, malformed or mismatched registry item must yield `not_assessed + data_gaps`; no early branch may bypass these controls. A positive Annex VIII evidence result may not be emitted from an assessment whose registry is invalid.

The root assessment and the institutional record identified as the root institution must reconcile the same Article 57(1) predicates. Compare the source-bound duration and unit, one-year comparator and unit, applicable legislation identity/version/validity, autonomous-right determination and the resulting relief predicate. Any contradiction in either direction yields `not_assessed + data_gaps`, not a selected outcome. The institutional evidence remains source-bound and human-reviewed; technical equality checks do not decide the meaning or sufficiency of national law.

The checks preserve c14n-v4, v0.21 content-bound SHA-256, issuer/manifest equality and full temporal coverage. Hashing proves byte integrity only. Annex VIII remains fail-closed without a complete applicable machine-readable catalogue; the engine does not infer a competent or paying institution.

## Verification boundary

All regressions and samples are synthetic. No personal evidence leaves `family-office-workspace/`. A possible GO applies only to the exact v0.22/c14n-v4 runtime and the bounded technical controls in this candidate. V4.14w/V4.14 remain blocked for their other national, temporal and catalogue gaps.
