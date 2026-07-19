# Engine Agent Instructions

Leggere `../AGENTS.md`. Questo repository contiene software deterministico e non deve contenere dati personali reali.

## Contesto iniziale

Per bug o modifiche circoscritte leggere solo modulo, test e contratto coinvolti. Per lavoro di roadmap aggiungere `docs/current-next-increment.md`, `docs/roadmap/roadmap-index.md` e la sola roadmap attiva.

## Verifica

- Preferire test mirati prima della suite completa.
- Eseguire la regression completa quando cambia un contratto condiviso, un calcolo, uno schema o prima di chiudere un incremento.
- Non modificare rules o knowledge implicitamente dall'engine.
