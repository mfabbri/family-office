# Work-transition readiness

`work-transition-readiness/v1` e' il gate di lineage della pipeline Work Transition. Seleziona snapshot sorgente, registra esclusioni e conflitti e blocca i calcoli successivi quando manca un input materiale. Non calcola imposte, pensioni, RITA, rendimenti o date di uscita.

## Comandi

Con i default del workspace privato:

```text
fo planning work-transition readiness
```

Per collegare le snapshot gia' presenti senza modificare a mano il manifest:

```text
fo planning work-transition sources setup
```

Smoke sintetico riproducibile:

```text
fo planning work-transition readiness --demo
```

Il manifest predefinito e' `family-office-workspace/planning/work-transition-readiness.json`; lo snapshot viene scritto in `family-office-workspace/snapshots/work-transition-readiness.snapshot.json`.

## Setup guidato delle fonti

Il percorso parte dalla domanda: "quali dati posso usare per stimare quando smettere di lavorare?" Scansiona soltanto `family-office-workspace/snapshots/`, mostra per ciascuna fonte riconosciuta path locale, schema, data, categoria, membro, value basis e tipo, poi richiede una scelta esplicita per ogni input. Una fonte non viene mai selezionata automaticamente; piu' fonti compatibili restano un conflitto visibile, mentre una categoria senza snapshot compatibile resta un `data_gap`.

Ogni scelta mostra prima un riepilogo locale del candidato — numero documenti/record, periodi, datori e totale netto osservato quando disponibile — e spiega a quale membro (`primary`, `spouse` o `nucleo`) la fonte verrebbe associata. Il riepilogo serve solo a decidere e non viene persistito. La scelta `0` lascia il gap esplicito. Dopo una scelta, il setup salva subito un adapter workspace-local in `planning/work-transition-source-bindings/` e aggiorna il manifest. L'adapter non copia o modifica il contenuto della fonte: ne conserva path relativo, schema e hash nella provenance e dichiara il `binding_pointer` verificabile richiesto dal gate. Prima di salvare, il setup rilegge la fonte e blocca il binding se e' stata cancellata, sostituita o se il suo hash non corrisponde piu' alla rilevazione; va quindi rieseguito. A ogni readiness il gate ripete la verifica: una fonte originaria mancante e' esclusa come `missing_source_snapshot`, una fonte mutata come `source_snapshot_hash_mismatch`. Il path della fonte originaria viene sempre risolto e letto soltanto dentro il workspace configurato. Se un input ha gia' un binding, `--overwrite` e' necessario per sostituirlo; `k` lo mantiene. Al termine il comando riesegue automaticamente la readiness, che resta responsabile dei controlli di freshness, stream bounds, liquidita' e conflitti di coverage.

Quando la snapshot dichiara `period`, `stream_start_date`, `stream_end_date`, `liquidity_tier` o `coverage_keys`, il setup li copia senza reinterpretarli nella source entry. Se un requisito richiede bounds, periodo o liquidita' e la fonte non li dichiara, mostra un `data_gap` azionabile: rigenerare o documentare la fonte, senza usare valori inventati. Il manifest viene validato contro il contratto `work-transition-readiness-input/v1` prima di qualsiasi scrittura; un JSON malformato genera un errore CLI recuperabile.

Il setup riconosce soltanto snapshot con schema supportato per payroll, spese lifecycle, patrimonio, piano liquidita', RITA, INPS e coordinamento Spagna/UE. Uno schema non riconosciuto non viene interpretato come dato finanziario o previdenziale. `fo payroll import` produce i metadata temporali richiesti (`as_of_date`, `stream_start_date`, `stream_end_date`, `period`) soltanto quando mese e anno sono estratti in modo deterministico; dichiara inoltre `value_basis: net` solo quando tutti i record hanno un netto osservato. Il comando non assegna automaticamente `primary` o `spouse`: il binding della fonte rimane esplicito e verificabile. Se un periodo o il netto mancano, il payroll snapshot resta utilizzabile come diagnostica ma il setup mostra un gap bloccante per il requisito interessato. Il JSON diretto resta un fallback avanzato per integrazioni esterne, ma non e' il percorso operativo normale.

Se nessuna fonte e' disponibile, il comando stampa per ogni requisito lo schema atteso, il comando di import/build suggerito e i metadati minimi necessari. `--overwrite` sostituisce soltanto binding gia' presenti: non crea snapshot mancanti. Dopo avere prodotto una fonte, ripetere `fo planning work-transition sources setup --overwrite`, poi `fo planning work-transition readiness` e infine `fo planning work-exit build` quando non restano gap bloccanti.

## Manifest

Il contratto e' `schemas/work-transition-readiness-input.schema.json`. Il manifest dichiara:

- `household_members`: ID opachi degli adulti rilevanti;
- `required_inputs`: categorie necessarie, membro, basis ammessa, periodo richiesto ed eventuali vincoli di stream/liquidita';
- `sources`: path dello snapshot, schema atteso, tipo di fonte, provenance, basis, periodo, start/end, coverage key e `binding_pointer`;
- `freshness_policy`: eta' massima generale e override per categoria.

Le categorie disponibili inventariano reddito proprio e del coniuge, spese, patrimonio, liquidita', RITA/previdenza complementare, INPS, Spagna/UE e altri redditi. I path relativi sono risolti rispetto alla directory del manifest e accettano separatori `/` o `\`.

`binding_pointer` e' un JSON Pointer verso un oggetto dello snapshot sorgente che dichiara `category`, `member_id` e `value_basis`. Il gate confronta il binding letto dal file con il requisito: un manifest non puo' attribuire silenziosamente una busta paga alla persona sbagliata o dichiarare netto un valore marcato lordo. Le fonti legacy prive di binding restano escluse finche' non vengono rigenerate o accompagnate da un artefatto normalizzato verificabile.

## Policy deterministica

La precedence e' `documentary > normalized > derived > manual`. A parita' di classe viene selezionato lo snapshot con `as_of_date` piu' recente e, per un pareggio completo, il `source_id` lessicograficamente minore. Tutte le alternative restano nell'output con hash, provenance e motivo di esclusione; un conflitto non viene sovrascritto silenziosamente.

Una fonte viene esclusa se e' mancante o invalida, stale, ha schema inatteso, basis gross/net incompatibile, non copre il periodo richiesto, non dichiara start/end quando rappresenta uno stream oppure usa un asset non spendibile per il bridge. La stessa `coverage_key` selezionata da piu' input produce un blocker di doppio conteggio.

## Stati

- `ready`: tutti gli input richiesti sono selezionati senza gap;
- `partial`: gli input richiesti sono disponibili, ma esistono warning o conflitti espliciti;
- `blocked`: almeno un gap materiale impedisce i calcoli successivi e `optimization_allowed` e' `false`.

Il report `blocked` viene comunque scritto: e' l'artefatto diagnostico necessario per correggere onboarding o fonti nel workspace privato.

Tutti gli output, inclusi quelli sintetici, sono confinati a `family-office-workspace/`. `--demo` usa un output sintetico dedicato e non sovrascrive lo snapshot personale.
