# Work-transition readiness

`work-transition-readiness/v1` e' il gate di lineage della pipeline Work Transition. Seleziona snapshot sorgente, registra esclusioni e conflitti e blocca i calcoli successivi quando manca un input materiale. Non calcola imposte, pensioni, RITA, rendimenti o date di uscita.

## Comandi

Con i default del workspace privato:

```text
fo planning work-transition readiness
```

Smoke sintetico riproducibile:

```text
fo planning work-transition readiness --demo
```

Il manifest predefinito e' `family-office-workspace/planning/work-transition-readiness.json`; lo snapshot viene scritto in `family-office-workspace/snapshots/work-transition-readiness.snapshot.json`.

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
