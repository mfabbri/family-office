# Current Next Increment

## ID e titolo

V5.2 - Knowledge corpus and citation index.

## Stato

`done`

## Roadmap

`docs/roadmap/roadmap-v5-ai-orchestration.md`

## Motivazione e dipendenze

V5.1 e' completata e fornisce `tool-registry/v1` con 15 tool deterministici e adapter locale validato. V5.2 e' il primo incremento selezionabile e deve rendere le fonti knowledge recuperabili con citazioni identificabili, validita' temporale e livello di autorita'.

Non sono necessari dati personali per procedere: il corpus pubblico gia' presente in `family-office-knowledge` e' sufficiente come base iniziale. I gap di formati o fonti reali ancora aperti in V1 sono non bloccanti finche' V5.2 non dichiara il corpus esaustivo per quei perimetri.

Prima dell'implementazione eseguire sempre:

```text
python family-office-engine/src/family_office_engine/governance/roadmap_audit.py
```

## Readiness e gap osservati

- Le note knowledge piu' recenti riportano gia' parte dei metadati richiesti: giurisdizione, periodo applicabile, data di verifica e fonti ufficiali.
- La copertura non e' uniforme tra tutte le note; alcuni documenti non espongono ancora gli stessi campi in forma strutturata.
- `family-office-knowledge/sources/source-template.md` e' ancora minimale e andra' allineato al citation contract definito dall'incremento.
- Una fonte priva di metadati obbligatori deve produrre un gap esplicito: non va esclusa silenziosamente e non va promossa per deduzione a fonte autorevole.
- Eventuali verifiche o integrazioni normative devono seguire `knowledge -> rules -> tests -> engine`; V5.2 indicizza e qualifica le fonti, non introduce nuovi calcoli.

## Piano operativo V5.2

1. Inventariare note knowledge, contratti e riferimenti normativi nel perimetro iniziale.
2. Definire un citation contract versionato con identificativo, tema, giurisdizione, autorita', validita', stato temporale e provenance.
3. Normalizzare il template delle fonti senza inventare metadati mancanti.
4. Costruire un indice locale deterministico, riproducibile e deduplicato.
5. Implementare retrieval temporale e gestione esplicita di fonti mancanti, scadute, abrogate o duplicate.
6. Aggiungere test, CLI/documentazione impattata e verificare regression e roadmap audit.

## Criteri di completamento V5.2

- Il corpus iniziale e' indicizzato con contratto versionato e hash riproducibile.
- Ogni affermazione normativa supportata puo' rinviare a una fonte identificabile.
- Metadati mancanti, fonti abrogate e conflitti temporali restano visibili come gap.
- Retrieval temporale, citazione mancante e deduplica sono coperti da test.
- Nessun dato personale entra nei repository software o knowledge.

## Stato implementazione

Completato.

- Catalogo `knowledge-citation-catalog/v1` nel repository knowledge con citation ID, autorita', giurisdizione, temi, validita' e stato.
- Servizio deterministico `family_office_engine.services.citation_index` con output `citation-index/v1` e `citation-search/v1`.
- Corpus iniziale: 11 citazioni, 13 documenti knowledge e 28 contratti input/output derivati dal tool registry.
- 7 gap espliciti: cinque documenti senza citation ID strutturato e fonte RITA senza validita'/data di verifica documentate.
- Deduplica per locator canonico, hash dei documenti, protezione path traversal e filtro temporale per fonti future, scadute, abrogate o ritirate.
- Tool read-only `knowledge.citations.search` aggiunto al registry.
- CLI `fo orchestration citations build/search` con default repository/workspace ed errore recuperabile.
- 13 test mirati/integration OK.
- Regression unit engine: 471 test OK.
- Smoke CLI: build `complete_with_gaps 11 citations, 13 documents, 28 contracts, 7 gaps`; ricerca IT/taxation `complete 8 citations`.
- `roadmap_audit.py`: OK (`functional_since_audit=2`, `audit_due=false`).

## Cadenza audit

Il contatore verificato dopo V5.2 e' `functional_since_audit=2`. Completate V5.3 e V5.4, l'incremento di audit V5.4a deve essere eseguito prima di V5.5.
