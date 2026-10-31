# Art. 57 transition-source binding and deterministic arithmetic — candidate v0.26

## Scope and boundary

This candidate succeeds, without editing, v0.25. It adds technical source-registry metadata and fail-closed bindings for transition records used by the synthetic Art. 57 contract. It does not decide an individual entitlement, last Member State, competent institution, recognition, economic effective date, payer or payment.

All examples and tests are synthetic. A record digest is a technical integrity control for the local record only; it is not an official-content hash and is not proof of source authenticity or legal sufficiency.

## Official-source registry

| Registry identity/version | Document type, authority, territory/language | OJ / entry / application | Provision and limit |
| --- | --- | --- | --- |
| `reg-883-2004-original-oj`, CELEX 32004R0883 | Original OJ act; Parliament and Council; EU, EN/IT/ES | OJ 30-04-2004; entered into force 20-05-2004; applies from 01-05-2010 | Art. 87. EUR-Lex consolidated text as of 31-07-2019 is documentation, not a new act/effective date. |
| `reg-987-2009-original-oj`, CELEX 32009R0987 | Original OJ act; Parliament and Council; EU, EN/IT/ES | OJ 30-10-2009; applies from 01-05-2010 | Arts. 93–94 temporal provisions. |
| `reg-465-2012-original-oj`, CELEX 32012R0465 | Amending OJ act; Parliament and Council; EU, EN/IT/ES | OJ L149 08-06-2012; in force 28-06-2012 | Art. 87a is a Title-II unchanged-situation transition (maximum ten years, opt-out), not proof of automatic Art. 57 or pension applicability. |
| `reg-987-2009-corrigendum-2026-07-22`, CELEX 32009R0987R(04) | Corrigendum OJ 2026/90618; EU; HR/SV only | 22-07-2026 | HR: Arts. 28 heading/1–3, 31(2)–(3), 75(1), 87(4). SV: Arts. 78(2)(a), 83(1)(a). It is not Arts. 93–94, and no EN/IT/ES application is inferred. Full HR scope was not verified beyond this declared material. |

Official references reviewed 2026-10-31: [883/2004 original OJ](https://eur-lex.europa.eu/eli/reg/2004/883/oj/eng), [987/2009 original OJ](https://eur-lex.europa.eu/eli/reg/2009/987/oj/eng), [465/2012 original OJ](https://eur-lex.europa.eu/eli/reg/2012/465/oj/eng), [987 corrigendum HR PDF](https://eur-lex.europa.eu/legal-content/HR/TXT/PDF/?uri=CELEX%3A32009R0987R%2804%29), and [987 corrigendum SV text](https://eur-lex.europa.eu/legal-content/SV/TXT/?uri=CELEX%3A32009R0987R%2804%29).

## Executable boundary

Regulation 987/2009 Article 97 states entry into force on 01-05-2010. Article 93 applies basic Regulation Article 87 to situations covered by the implementing Regulation. Article 94 depends on the Member State territorial application date, contingency, pre/post periods and reassessment conditions; no universal Article 94 date is encoded.

The v5 profile declares Article 57 contract v0.26 with `fo-art57-c14n-v4`; loaders continue to accept coexisting v0.25. Transition references bind registry identity, immutable version, article, EU territory, Member State, language scope and assessment period. An Article 94 reference also binds the Member State and territorial application date to the reference period.

`integrity_digest_record` is `sha256:` plus lowercase SHA-256 over UTF-8 JSON for the registry record with that field omitted, sorted keys and compact `,`/`:` separators. It checks the local metadata record; it is not a digest of official legal content and proves neither authenticity nor sufficiency.

The v5 profile binds every transition reference to registry identity, immutable version, article, territory, language scope and assessment period. Missing, duplicate or mismatched bindings are `not_assessed` with `data_gaps`. The HR/SV corrigendum cannot bind the EN/IT/ES profile or Arts. 93–94.

Before every Art. 57 early return, any supplied Last-State attestation is technically validated. Malformed supplied material yields `not_assessed` and null pro-rata amounts, without an exception or legal inference. Ratio and money operations use declared bounded operands and an isolated deterministic Decimal context, preserving public scales and `ROUND_HALF_UP` independent of caller Decimal context.
