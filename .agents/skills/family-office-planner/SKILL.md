---
name: family-office-planner
description: Seleziona o riprende il micro-incremento Family Office AI e mantiene una sola fonte di stato operativo verificabile.
---

# Planner persistente

Fonti: `family-office-engine/docs/roadmap/roadmap-index.md` e roadmap attiva per ordine/stati; `family-office-engine/docs/current-next-increment.md` per piano corrente; `family-office-bootstrap/planning/current-work.json` per esecuzione/routing; codice+test per realtà implementativa.

Se planner è `selected`/`in_progress`, validalo contro codice e roadmap e riprendi; altrimenti ricalcola il predecessore più antico non completato. Non inferire `done` da un GO parziale o dai test verdi; `roadmap_audit.py` e i gate dell'incremento restano necessari.

Per V4.14 distinguere blocker giuridico, implementazione tecnica fail-closed e simulazione di scenario secondo `12-dual-gate-and-convergence.md`. Dopo due review inconcludenti dello stesso pacchetto fermare i retry, registrare richiesta umana mirata, non aprire suffissi ciclici. Aggiorna solo i documenti di stato impattati; non registrare dati personali o chain-of-thought.
