# Art. 57 transition-source binding and deterministic arithmetic — candidate v0.26

## Scope and boundary

This candidate succeeds, without editing, v0.25. It adds technical source-registry metadata and fail-closed bindings for transition records used by the synthetic Art. 57 contract. It does not decide an individual entitlement, last Member State, competent institution, recognition, economic effective date, payer or payment.

All examples and tests are synthetic. A record digest is a technical integrity control for the local record only; it is not an official-content hash and is not proof of source authenticity or legal sufficiency.

## Official-source registry

| Registry identity/version | Document type, authority, territory/language | OJ / entry / application | Provision and limit |
| --- | --- | --- | --- |
| `reg-883-2004-original-oj`, CELEX 32004R0883 | Original OJ act; Parliament and Council; EU, EN/IT/ES | OJ 30-04-2004; entered into force 20-05-2004; applies from 01-05-2010 | Art. 87. EUR-Lex consolidated text as of 31-07-2019 is documentation, not a new act/effective date. |
| `reg-987-2009-original-oj`, CELEX 32009R0987 | Original OJ act; Parliament and Council; EU, EN/IT/ES | OJ 30-10-2009; applies from 01-05-2010 | Arts. 93–94 temporal provisions. |
| `reg-465-2012-original-oj`, CELEX 32012R0465 | Amending OJ act; Parliament and Council; EU, EN/IT/ES | OJ L149 08-06-2012; in force 28-06-2012 | Art. 1(11) inserts Regulation 883/2004 Art. 87a: a Title-II unchanged-situation transition (maximum ten years, opt-out), not proof of automatic Art. 57 or pension applicability. |
| `reg-987-2009-corrigendum-2026-07-22`, CELEX 32009R0987R(04) | Corrigendum OJ 2026/90618; EU; HR/SV only | 22-07-2026 | HR: Arts. 28 heading/1–3, 31(2)–(3), 75(1), 87(4). SV: Arts. 78(2)(a), 83(1)(a). It is not Arts. 93–94, and no EN/IT/ES application is inferred. Full HR scope was not verified beyond this declared material. |

Official references reviewed 2026-10-31: [883/2004 original OJ](https://eur-lex.europa.eu/eli/reg/2004/883/oj/eng), [987/2009 original OJ](https://eur-lex.europa.eu/eli/reg/2009/987/oj/eng), [465/2012 original OJ](https://eur-lex.europa.eu/eli/reg/2012/465/oj/eng), [987 corrigendum HR PDF](https://eur-lex.europa.eu/legal-content/HR/TXT/PDF/?uri=CELEX%3A32009R0987R%2804%29), and [987 corrigendum SV text](https://eur-lex.europa.eu/legal-content/SV/TXT/?uri=CELEX%3A32009R0987R%2804%29).

## Executable boundary

Regulation 987/2009 Article 97 states entry into force on 01-05-2010. Article 93 applies basic Regulation Article 87 to situations covered by the implementing Regulation. Article 94 depends on the Member State territorial application date, contingency, pre/post periods and reassessment conditions; no universal Article 94 date is encoded.

The v5 profile declares Article 57 contract v0.26 with `fo-art57-c14n-v4`; loaders continue to accept coexisting v0.25. Transition references bind registry identity, immutable version, article, EU territory, Member State, language scope and assessment period. An Article 94 reference also binds the Member State and territorial application date to the reference period.

`integrity_digest_record` is `sha256:` plus lowercase SHA-256 over UTF-8 JSON for the registry record with that field omitted, sorted keys and compact `,`/`:` separators. It checks the local metadata record; it is not a digest of official legal content and proves neither authenticity nor sufficiency.

The v5 profile binds every transition branch to its exact source identity, immutable version, target article, territory, language scope and assessment period: `basic_regulation_883_87` to Regulation 883/2004 Art. 87; `implementing_regulation_987_93` to Regulation 987/2009 Art. 93; `regulation_465_2012_883_87a` to Regulation 883/2004 Art. 87a with Regulation 465/2012 Art. 1(11) amendment provenance; and `pension_transitional_987_94_1` to Regulation 987/2009 Art. 94(1). Each branch preserves its own pre-application semantics and does not borrow another branch's article. Missing, duplicate, cross-branch or mismatched bindings are `not_assessed` with `data_gaps`. The HR/SV corrigendum cannot bind the EN/IT/ES profile or Arts. 93–94.

For the v5 IT/ES Art. 94(1) branch only, each member-state binding declares `B = 2010-05-01` separately and source-binds it to Regulation 987/2009 Articles 94(1) and 97. The contingency must be strictly before `B`, the claim must not have been awarded before `B`, and benefits must be due for the preceding period. When all three predicates hold, the two amount legs are distinct contiguous intervals: the prior-leg period is `[prior.start, B)` with `prior.start < B` and `prior.end_exclusive = B`; the basic-Regulation-leg period is `[B, basic.end_exclusive)` with `basic.start = B` and `basic.end_exclusive > B`. Exact equality is required at the shared boundary (`prior.end_exclusive = basic.start = B`); neither an overlap nor a gap is normalized. The prior leg is retained only when `prior.amount > basic.amount`; `prior.amount <= basic.amount`, including equality, selects the basic-Regulation leg. A false predicate is `not_applicable`; an unknown, null, non-ISO or malformed predicate, endpoint, leg, or comparison is `not_assessed` with `data_gaps`. These controls do not alter the coexisting v0.25 branch.

Before every Art. 57 early return, any supplied Last-State attestation is technically validated. Its absence is distinct from a supplied `null` or any malformed value. Supplied null or malformed material yields `not_assessed`, `data_gaps` and null pro-rata amounts, without an exception or legal inference. A v4 pack accepts only the historical v0.25 shape; the v5 profile accepts only the v0.26 transition-registry shape, and either cross-pair fails closed while output gaps identify the selected contract. Ratio and money operations use declared bounded operands and an isolated deterministic Decimal context, preserving public scales and `ROUND_HALF_UP` independent of caller Decimal context.
