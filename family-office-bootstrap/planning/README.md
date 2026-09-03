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
- ogni incremento attivo registra il routing prima della delega;
- deleghe, escalation e fallback aggiornano la routing trace;
- nessun dato personale o risultato sensibile nel planner;
- niente chain-of-thought;
- percorsi relativi al repository;
- date ISO 8601 UTC;
- aggiornamenti piccoli e leggibili in diff.

Prima di dichiarare completata una sessione eseguire `python planning/validate-execution-guardrails.py`. Il gate verifica che gli stati attivi abbiano una prossima azione concreta e che gli stati completati abbiano test, review quando richiesta, nessun blocker e non più di due eventi sostanziali di delega/escalation.

Se `jsonschema` e' installato:

```powershell
python -m jsonschema -i family-office-bootstrap/planning/current-work.json family-office-bootstrap/planning/current-work.schema.json
```
