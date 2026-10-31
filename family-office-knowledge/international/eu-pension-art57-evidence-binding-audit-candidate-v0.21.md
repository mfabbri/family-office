# Art. 57 evidence-binding runtime — candidate v0.21

## Scope

This candidate is a bounded technical response to the exact-version NO-GO for v0.20. It does not add a legal conclusion, alter Article 57 semantics, or make Annex VIII executable.

The evidence registry is fail-closed. Registry `evidence_id` values and `resolved_source_refs` must each be unique, and every resolved reference must identify exactly one registry entry. Each entry carries `content_utf8`; `content_digest` must be exactly `sha256:` followed by 64 lowercase hexadecimal characters and equal SHA-256 over the UTF-8 bytes of that content. A digest proves byte integrity only; it does not establish source authenticity, legal sufficiency, or operator verification. Evidence content in real cases remains within `family-office-workspace/`; repository fixtures are synthetic.

The perimeter issuer must equal the coordination manifest issuer. For each resolved entry, the registry coverage must bind the same manifest, case, coordinated benefit, contingency/as-of dates, procedural scope and exact institution set, and its `temporal_coverage_from`/`temporal_coverage_to` must validly cover the full interval declared by the perimeter. Missing, duplicate, unresolved, malformed, incomplete or mismatched data remains `not_assessed + data_gaps`.

The deterministic Article 57(1) relief reconciliation and the c14n-v4 duration-segment grammar from v0.20 are unchanged. The runtime remains human-review-required, fail-closed for Annex VIII, and does not infer a competent or paying institution.

## Verification boundary

The registry and its content in tests and the sample are synthetic. They demonstrate only a technical integrity contract, not institutional evidence or a decision for a person. A possible GO would apply only to v0.21/c14n-v4 and the bounded checks above; V4.14 remains blocked for its other national, timeline and catalogue gaps.
