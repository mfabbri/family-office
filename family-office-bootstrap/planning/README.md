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
- ogni incremento attivo registra il routing prima della delega;
- deleghe, escalation e fallback aggiornano la routing trace;
- il budget ordinario è due eventi sostanziali; un'estensione fino a diciotto richiede autorizzazione utente esplicita, scope/versione e blocker registrati in `routing.delegation_budget`;
- `routing.trace` è circoscritta all'incremento attivo; gli esiti storici si conservano in `verification`/decision log, non accumulando deleghe concluse nel budget della sessione corrente;
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
