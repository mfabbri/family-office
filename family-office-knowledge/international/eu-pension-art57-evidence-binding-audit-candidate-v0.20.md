# Art. 57 evidence-binding runtime — candidate v0.20

## Scope

This candidate is the bounded correction of the exact-version NO-GO for v0.19. It does not add a legal conclusion or make Annex VIII executable.

The technical contract now requires an `evidence_registry` for every `institution_scope_evidence.resolved_source_refs` entry. Each resolved entry must identify its issuer, a content digest, verified status, and coverage bound to the same coordination manifest, case, coordinated benefit, contingency/as-of dates, procedural scope and exact institution set. Missing, duplicate, unresolved or mismatched entries remain `not_assessed + data_gaps`.

The Article 57(1) relief result is reconciled deterministically from the source-bound duration/comparator and the institution-specific autonomous-right evidence. A declared boolean that disagrees with those predicates is rejected. Non-relief remains a valid evidenced outcome and never selects a payer.

The c14n-v4 duration segment keeps its one-parent/one-bound grammar; the sample digest is bound to the exact segment preimage. The runtime remains human-review-required, fail-closed for Annex VIII, and does not infer a competent or paying institution.

## Verification boundary

The registry used in tests and the sample is synthetic. It demonstrates the contract and does not constitute an institutional decision, legal proof for a person, or a positive Annex VIII match. A GO for this candidate would apply only to v0.20/c14n-v4 and the bounded technical checks above; V4.14 remains blocked for its other national, timeline and catalogue gaps.
