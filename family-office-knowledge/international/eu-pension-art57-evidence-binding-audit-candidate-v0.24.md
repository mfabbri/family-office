# Art. 57 Last-State evidence registry binding — candidate v0.24

## Scope and legal boundary

This candidate is a technical provenance and fail-closed correction for EU statutory old-age coordination. It does not add a legal interpretation, decide a legally relevant last Member State, determine a competent or paying institution, or determine payment.

The legal predicates remain Regulation (EC) No 883/2004, Article 57(3). Regulation (EC) No 987/2009, Article 47(4)–(7), remains the cited procedural context for inter-institutional exchange and information. Registry identifiers, UTF-8 SHA-256 digests, issuer reconciliation, coverage records, verified/comparable status and operator-selected-last-state status are internal provenance controls. They are not statutory forms, legal presumptions, or proof of legal sufficiency.

Primary-source context (checked 2026-10-30; cited for the legal boundary only, not as authority for the technical registry schema): [Regulation 883/2004, Article 57](https://eur-lex.europa.eu/eli/reg/2004/883/oj/eng) and [Regulation 987/2009, Article 47](https://eur-lex.europa.eu/eli/reg/2009/987/oj/eng).

## Technical contract

`v0.24` retains `fo-art57-c14n-v4`, mandatory human review, all v0.22 controls, Annex VIII Part 2 unavailable/fail-closed, and no payer inference.

Before any mapping access, `last_state_attestation` must be a canonical object. A malformed scalar, list, null, wrong shape, or invalid binding returns `not_assessed` with `data_gaps` through the public builder.

The selection, conditions, comparability, event, applicable-legislation and institutional-record reference categories must each resolve to distinct verified registry entries. Every referenced entry must have a strict lowercase `sha256:` digest of its UTF-8 content, the manifest issuer, and coverage matching the coordination manifest/case/coordinated benefit/institution set. Its temporal coverage must include the contingency, conditions event and assessment/as-of dates; its explicit legislation coverage must match the attested applicable-legislation validity dates.

Missing or unresolved references use `missing_article_57_3_registry_evidence`; malformed attestation uses `invalid_article_57_3_last_state_attestation`; duplicate, digest, issuer, verification, coverage, case, benefit or date inconsistency uses `inconsistent_article_57_3_registry_binding`. These technical results do not establish legal sufficiency.

## Output boundary

Any failed v0.24 check emits Article 57 `not_assessed`, national payment obligation `not_assessed`, and non-calculable Spanish pro-rata amounts (`null`). Valid registry evidence is also technical provenance only: the output never emits `article_57_3_last_state` or another legal-looking Last-State conclusion. No output may infer a payer or institution.

All fixtures and regressions are synthetic. A review of this candidate is limited to its exact technical contract; it does not unblock V4.14w or V4.14.
