---
name: family-office-session
description: Riprende un incremento Family Office AI dalla roadmap e chiude il lavoro con test, evidenze e gestione di blocker.
---

# Sessione Family Office AI

Se il task è sulla roadmap, leggi planner, indice roadmap, `current-next-increment.md` e la sola roadmap attiva. Se è un fix locale, leggi invece solo i file utili. Per selezionare incrementi esegui `roadmap_audit.py` e non saltare predecessori.

Registra un task envelope minimale (`objective`, `scope`, `write_set`, `test_command`, `stop_conditions`) nel planner; chiama `$family-office-model-router` **solo quando serve una delega**.

Implementa la minima modifica autorizzata, prova prima i test pertinenti, quindi la suite completa al gate di incremento. Conserva `null+data_gaps` per contenuti giuridicamente non valutabili. Distingui software readiness e normative readiness in base a `12-dual-gate-and-convergence.md`. Un reviewer in timeout non va rieseguito sul medesimo hash senza evidenza nuova.

Aggiorna roadmap, planner e decision log solo quando cambia la loro semantica; al gate esegui `validate-execution-guardrails.py`. Riporta done/blocked e prossima azione concreta. Non autoaprire l'incremento successivo prima di rispettare le dipendenze.
