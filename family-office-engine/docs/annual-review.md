# Annual review

Per rispondere alla domanda “che cosa deve riesaminare la famiglia quest'anno?”, usare:

```text
fo review annual --year 2026 --as-of-date 2026-09-03
```

Il comando legge soltanto metadati degli snapshot JSON in `family-office-workspace/snapshots` e salva `annual-review.snapshot.json` nello stesso workspace. Verifica copertura delle fonti richieste, periodo dichiarato, freshness, gap già esposti e gli eventi dichiarati di cambio residenza o straordinari. Le fonti richieste possono essere sostituite ripetendo `--required-source`; la finestra predefinita è 365 giorni.

L'output `annual-review/v1` distingue fatti osservati, gap azionabili, rischi, priorità e azioni di contingenza. Non legge né ristampa note, importi o contenuti personali, non usa rete e non calcola valori fiscali, previdenziali o finanziari. `needs_review` ha exit code `2` e richiede revisione umana; `ready` ha exit code `0`.
