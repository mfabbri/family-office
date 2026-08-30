---
name: family-office-planner
description: Mantiene lo stato operativo persistente del micro-incremento senza sostituire roadmap, current-next-increment o stato verificabile del codice.
---

# Family Office AI persistent planner

## Autorita'

1. `roadmap-index.md`, roadmap attiva e decision log definiscono direzione e priorita';
2. `current-next-increment.md` conserva il piano narrativo dell'incremento corrente;
3. `planning/current-work.json` conserva lo stato operativo minimo e il routing;
4. codice e test mostrano lo stato implementativo reale.

## Start

1. Leggi `family-office-bootstrap/planning/current-work.json`.
2. Se `selected` o `in_progress`, verifica repository, roadmap audit e stop condition.
3. Se non e' piu' valido, marca `superseded` e ricalcola con l'algoritmo di `roadmap-index.md`.
4. Se `uninitialized`, `completed` o `superseded`, seleziona un solo micro-incremento valido.
5. Non inferire completion dal planner: verifica codice, test e documentazione.

## Selection record

Registra roadmap/section, obiettivo, scope/out-of-scope, file candidati, task envelope,
test mirati, stop condition e routing iniziale.

## Close

- incompleto e valido: `in_progress` + `resume`;
- bloccato: `blocked` + `review`/`recalculate`;
- stop condition raggiunta e test accettabili: `completed` + `recalculate`;
- invalidato: `superseded` + `recalculate`.

Non salvare dati personali, risultati finanziari sensibili, chain-of-thought o telemetria
provider nel planner.
