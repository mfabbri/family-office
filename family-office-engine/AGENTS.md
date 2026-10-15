# Engine Agent Instructions

Leggere `../AGENTS.md`. Questo repository contiene software deterministico e non deve contenere dati personali reali.

## Contesto iniziale

Per bug o modifiche circoscritte leggere solo modulo, test e contratto coinvolti. Per lavoro di roadmap aggiungere `docs/current-next-increment.md`, `docs/roadmap/roadmap-index.md` e la sola roadmap attiva.

## Verifica

- Preferire test mirati prima della suite completa.
- Eseguire la suite completa del repository quando cambia un contratto condiviso, un calcolo, uno schema o prima di chiudere un incremento/release; il gate richiede esattamente 0 failure, 0 errori e 0 skipped.
- Un failure richiede una correzione nel codice o, con evidenza del contratto, nel test; non è mai un esito out-of-scope. Uno skip richiede un test equivalente eseguibile sulle piattaforme supportate; non è un pass.
- Se la suite non può essere eseguita o non passa integralmente, mantenere l'incremento `in_progress` o `blocked`, mai `done`.
- Non modificare rules o knowledge implicitamente dall'engine.
