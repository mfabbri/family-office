# Art. 57 institutional evidence registry binding — candidate v0.25

## Scope and legal boundary

This successor preserves v0.24 byte-for-byte and adds only a technical provenance control for EU statutory old-age coordination. It does not add a legal interpretation, decide a legally relevant last Member State, determine a competent or paying institution, determine entitlement, or determine payment.

The legal boundary remains Regulation (EC) No 883/2004, Article 57(3), with Regulation (EC) No 987/2009, Article 47(4)–(7) as cited procedural context. These are not authority for the technical registry schema. Primary-source context was checked 2026-10-31: [Regulation 883/2004, Article 57](https://eur-lex.europa.eu/eli/reg/2004/883/oj/eng) and [Regulation 987/2009, Article 47](https://eur-lex.europa.eu/eli/reg/2009/987/oj/eng).

## Technical contract

`v0.25` retains `fo-art57-c14n-v4`, mandatory human review, all v0.24 controls, Annex VIII Part 2 unavailable/fail-closed, and no payer inference.

For every concerned institution, both `article_57_1_evidence.source_evidence_refs` and record `evidence_refs` must be nonempty canonical string lists with no duplicate within either list. Every reference must resolve to a unique registry entry with a strict lowercase UTF-8 SHA-256 content digest, `verified: true`, issuer equal to the coordination-manifest issuer, manifest/case/coordinated-benefit/institution-set coverage, temporal coverage including the institutional contingency, risk-materialization and assessment dates, and matching applicable-legislation validity coverage.

An absent registry or unresolved reference yields `missing_article_57_3_registry_evidence`. Duplicate identifiers or references, digest, issuer, verification, manifest, coverage, legislation, case, benefit or date mismatch yields `inconsistent_article_57_3_registry_binding`. These are internal technical provenance controls, not statutory forms, legal presumptions, or proof of legal sufficiency.

## Output boundary

Any failed v0.25 check emits Article 57 `not_assessed`, national payment obligation `not_assessed`, and non-calculable Spanish pro-rata amounts (`null`). Valid registry evidence remains technical provenance only. No output emits a legal-looking Last-State conclusion, payer, competent-institution, entitlement, or payment conclusion.

All fixtures and regressions are synthetic. A review of this exact candidate is limited to this technical contract and does not unblock V4.14w or V4.14.
