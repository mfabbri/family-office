# Art. 57 evidence-binding runtime — candidate v0.19

**Stato:** candidata tecnica non ancora approvata per Rules/Engine; gate normativo exact-version pendente.
**Giurisdizione:** coordinamento UE, implementazioni IT/ES.
**Verifica delle fonti:** 2026-10-18. Le fonti normative elencate sono quelle già documentate nel candidato v0.18; il passaggio v0.19 materializza requisiti tecnici del contratto documentale v0.2.2 e non modifica l'interpretazione della legge.

## Fonti e perimetro

- Reg. (CE) 883/2004, artt. 52 e 57 e Annex VIII: https://eur-lex.europa.eu/eli/reg/2004/883/2019-07-31/eng
- Reg. (CE) 987/2009, artt. 45–48, in particolare 47(4)–(7): https://eur-lex.europa.eu/eli/reg/2009/987/oj/eng
- Reg. (CE) 988/2009, art. 1(16), che introduce l'art. 57(4): https://eur-lex.europa.eu/eli/reg/2009/988/oj/eng
- Contratto tecnico documentale Art. 57 v0.2.2, con GO limitato documentale registrato in `family-office-engine/docs/current-next-increment.md`.

Il diritto UE non prescrive le chiavi software, le etichette di verifica o il formato delle evidenze qui elencate. Sono controlli prudenziali del software; non sostituiscono una decisione dell'istituzione e non attestano da soli l'esistenza di un diritto.

## Contratto tecnico runtime v0.19 / fo-art57-c14n-v4

La root, il `coordination_manifest` e ogni record istituzionale restano vincolati allo stesso riferimento di caso, oggetto coordinato, rischio/data e data di valutazione. I riferimenti nazionali locali mantengono namespace e issuer distinti; non si richiede uguaglianza fra identificativi nazionali.

### Perimetro istituzionale

`institution_scope_evidence` non è soddisfatto da una lista, da risposte ricevute o da `attested_complete`. Deve contenere i binding al manifest/caso/beneficio/data, issuer, data `as_of`, intervallo di copertura temporale che includa l'evento e la valutazione, copertura procedurale, elenco esatto degli istituti e riferimenti a fonti risolvibili. `full_perimeter_status=source_bound_full_perimeter` e `operator_verification_status=verified` rappresentano una verifica umana registrata, non una conclusione automatica del software. La fonte deve dichiarare il perimetro completo del caso e l'operatore deve verificare che lo sostenga. Campo assente, fonte irrisolta, discordanza, copertura insufficiente o verifica mancante → `not_assessed + data_gaps`.

### Prova per istituzione ex art. 57(1)

Ogni record contiene `article_57_1_evidence` separata dal booleano di esito: riferimenti ai periodi pertinenti; durata complessiva e comparatore di un anno con unità e basi legali; legislazione/versione nazionale applicabile alla data del rischio e relative fonti; determinazione distinta del diritto autonomo basata sui soli periodi dell'istituzione, con rule-pack/versione/data/evidenze; riferimenti probatori istituzionali. Durata non strettamente inferiore al comparatore o diritto autonomo acquisito non autorizzano il sollievo. Un booleano isolato, prova generica o uno qualsiasi dei componenti mancanti/conflittuali impedisce di concludere che tutte le istituzioni siano sollevate e mantiene l'esito prudenziale non valutato con gap.

### Stato membro le cui condizioni sono soddisfatte per ultime ex art. 57(3)

`last_state_attestation` lega istituzione e Stato selezionati al medesimo manifest, caso, oggetto e data, include legislazione/versione applicabile, condizioni nazionali, evento e data in cui risultano soddisfatte, riferimenti istituzionali e prove separate per selezione, condizioni e comparabilità. L'insieme dei candidati deve corrispondere ai record considerati; `candidate_conditions_comparability_status=verified_comparable` e `last_state_selection_status=operator_verified_unique_last_state` sono attestazioni source-bound verificate da un operatore, non risultati dedotti dal motore. Il motore non ordina date per decidere autonomamente quale Stato sia legalmente ultimo. Candidato mancante, parità, incomparabilità, legislazione/condizioni ignote o prova non risolta → `not_assessed + data_gaps`.

### Traceability e controlli conservati

- Il Rule Pack rende tracciabili gli artt. 46–48 del Reg. 987/2009, incluso l'art. 47(4)–(7), coerentemente con il flusso procedurale descritto in Knowledge.
- Il profilo c14n-v4 resta limitato a un parent e un bound; schema, riferimenti, cardinalità e digest sono controllati deterministicamente. Non si attribuisce valore normativo alla canonicalizzazione.
- Il catalogo machine-readable Annex VIII Part 2 resta non disponibile. Non produrre match né non-match senza catalogo completo, versionato e applicabile; mantenere `not_assessed + data_gaps`.
- Non inferire l'istituzione competente o il soggetto pagatore. Anche un ramo Art. 57(3) tecnicamente supportato non costituisce, da solo, determinazione dell'obbligo nazionale di pagamento.
- `human_review_required` resta obbligatorio; gli esiti sono evidenze software sintetiche e non decisioni ufficiali.

## Gate e regressioni

Questa candidata richiede review normativa indipendente exact-version prima di considerare GO il runtime. I test sintetici devono coprire prove di perimetro auto-attestate/non verificate o discordanti; istituti mancanti/extra; periodi, durata/comparatore, legislazione o prova di diritto autonomo mancanti; evento last-State con candidati non comparabili, parità o binding errato; traceability Art. 47; fail-closed Annex VIII; invarianti d'ordine; e mutazioni c14n-v4. Un GO riguarda esclusivamente questa versione runtime e non sblocca V4.14 complessiva.
