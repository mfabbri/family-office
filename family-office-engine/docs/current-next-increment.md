# Current Next Increment

## ID e titolo

V6.14 - Efficient bank expense categorization review.

## Stato

`done`

## Roadmap

`docs/roadmap/roadmap-v6-operations-compliance.md`

## Motivazione e dipendenze

V6.13 è completato e l'export reale contiene gruppi numerosi, ad esempio `food` con 87 movimenti. V6.14 è stato il primo incremento planned successivo e non cambia il contratto di importazione: migliora soltanto l'efficienza e la leggibilità della revisione.

## Obiettivo e criteri di accettazione

L'operatore deve poter confermare un gruppo omogeneo con una sola decisione, vedere un campione e aprire il dettaglio completo solo quando serve, correggere gruppi in blocco e riutilizzare le correzioni come regole locali. Le descrizioni originali devono restare disponibili e i gruppi ambigui o anomali devono rimanere esplicitamente revisionabili.

## Piano concreto

1. Definire un normalizzatore deterministico di merchant con fingerprint stabile e descrizione raw preservata.
2. Estendere il contratto di review con gruppi, campioni, periodo, totale calcolato, confidenza/provenance e motivi di eccezione.
3. Aggiornare `review-bank` con conferma/esclusione/correzione in blocco, drill-down e ordinamento per priorità di revisione.
4. Aggiungere il percorso CLI per salvare e applicare regole locali versionate, senza rendere il JSON un passaggio operativo.
5. Coprire casi limite, privacy/path, test CLI/integrativi, regressione e validazione architetturale.

Implementazione avviata: il contratto di import resta `bank-expense-transactions/v1`; il nuovo output di review
sarà `bank-expense-review/v2`, con regole workspace-local versionate e applicate solo in modo deterministico.

Esito: completato. L'import conserva merchant normalizzato/fingerprint e applica regole locali opzionali; `review-bank` usa gruppi, campioni, periodo, totale, priorità ed eccezioni, con conferma/esclusione/correzione per gruppo e drill-down raw. Verifiche: 7 test bank-expenses, 2 CLI wrapper, 6 lifecycle, regression engine 692 test (2 skip Windows), py_compile, smoke help CLI, `roadmap_audit.py`, validator planner, privacy/import scan e `git diff --check` OK.

## Blocker di selezione successiva

V6.14 è completato e la roadmap V6 non contiene incrementi `planned`, `in_progress` o `blocked` selezionabili: l'unica voce successiva nel file è V6.9a, già `done`. Impatto: non è possibile completare un nuovo incremento senza inventare scope o aprire una nuova roadmap. Prerequisito: il maintainer deve aggiungere un incremento pianificato compatibile nella roadmap V6 oppure aprire formalmente la roadmap successiva e il relativo gate nell'indice.

## Comandi operativi previsti

```text
fo expenses review-bank
```

Export stabile: `family-office-workspace/documents/banca/spese/`. `family-office-workspace/inbox/` resta deposito temporaneo.

## Stop condition

Fermarsi se la normalizzazione fonde esercenti distinti senza evidenza, se una regola non conserva provenance o se la conferma in blocco impedisce di ispezionare le eccezioni. Non introdurre LLM obbligatorio, connessioni online o calcoli finanziari.
