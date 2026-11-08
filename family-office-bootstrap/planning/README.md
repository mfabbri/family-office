# Persistent session planner

`current-work.json` conserva lo stato operativo minimo tra una sessione e la successiva.
Non sostituisce roadmap, `current-next-increment.md` o decision log.

## Autorita'

1. roadmap e decision log definiscono direzione e priorita';
2. `current-next-increment.md` descrive l'incremento corrente;
3. `current-work.json` registra stato operativo, task envelope e routing;
4. codice e test mostrano lo stato implementativo reale.

In caso di conflitto prevalgono roadmap, decisioni e stato verificabile del repository.
Il planner viene marcato `superseded` e ricalcolato.

## Ciclo

- `uninitialized`, `completed` o `superseded`: ricalcolare dalle roadmap;
- `selected` o `in_progress`: verificare che sia ancora valido e riprenderlo;
- `blocked`: non aggirare il blocco; seguire la policy roadmap e registrare la decisione;
- a fine sessione aggiornare test, risultato, note, route e `next_action`.

## Regole

- un solo incremento attivo;
- prima di selezionare **o chiudere** un incremento, verificare tutti i predecessori nell'ordine della roadmap attiva e tutte le dipendenze dichiarate. Se un predecessore resta `planned`, `in_progress` o `blocked`, non proseguire con un incremento funzionale/audit a valle: riprendere il predecessore più antico oppure selezionare il minimo micro-incremento per sbloccarlo. Un GO limitato a un figlio non completa il parent;
- `roadmap_audit.py` verifica la cadenza, non l'eleggibilita' in sequenza: confrontare manualmente ciascun predecessore/dipendenza con la roadmap attiva e riallineare `current-next-increment.md` e `current-work.json` se puntano a valle;
- un GO locale chiude solo lo scope esaminato. Prima di marcare un parent `done`, ottenere la sua verifica richiesta sul candidato corrente; non inferire la chiusura da una review successiva che cita i suoi finding come PASS;
- i valori `mode` del task envelope e di `next_action` hanno enum distinti in `current-work.schema.json`; validare il planner con lo schema usando il venv Engine, non affidarsi al solo validator di routing che puo' saltare JSON Schema se il Python di sistema non ha `jsonschema`;
- ogni incremento attivo registra il routing prima della delega;
- deleghe, escalation e fallback aggiornano la routing trace;
- il budget ordinario è due eventi sostanziali; un'estensione fino a diciotto richiede autorizzazione utente esplicita, scope/versione e blocker registrati in `routing.delegation_budget`;
- `routing.trace` è circoscritta all'incremento attivo; gli esiti storici si conservano in `verification`/decision log, non accumulando deleghe concluse nel budget della sessione corrente;
- una review `done` con verdetto NO-GO chiude solo l'attività di audit: l'incremento revisionato e i suoi parent restano `blocked`/`in_progress`; suite, hash e governance verdi non annullano finding normativi, semantici o di contratto;
- registrare gli hash esaminati e riportare il verdetto sullo stesso set di artefatti. Se l'hash cambia, la review non copre più il candidato; hash identici provano solo l'identità, non la correttezza;
- esaurito il numero/scope di incrementi o deleghe autorizzati, fermarsi, aggiornare `blockers` e `next_action` e attendere nuova autorizzazione prima di un altro corrective loop;
- i test di branch/early-return devono dimostrare con controlli validi che ogni ramo dichiarato è raggiungibile; non contare un preflight comune che interrompe tutti i casi come copertura dei singoli rami;
- chiudere una sessione non significa chiudere l'incremento: un gate o un'autorizzazione ancora pendenti mantengono lo stato `in_progress`/`blocked` e una `next_action` concreta;
- nessun dato personale o risultato sensibile nel planner;
- niente chain-of-thought;
- percorsi relativi al repository;
- date ISO 8601 UTC;
- aggiornamenti piccoli e leggibili in diff.

Prima di dichiarare completata una sessione eseguire `python planning/validate-execution-guardrails.py`. Il gate verifica che gli stati attivi abbiano una prossima azione concreta e che gli stati completati abbiano test, review quando richiesta, nessun blocker e non più del budget sostanziale registrato (due di default, fino a diciotto con eccezione esplicita).

Se `jsonschema` e' installato:

```powershell
python -m jsonschema -i family-office-bootstrap/planning/current-work.json family-office-bootstrap/planning/current-work.schema.json
```
