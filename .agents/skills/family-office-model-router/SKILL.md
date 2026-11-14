---
name: family-office-model-router
description: Seleziona lo specialista in base alla semantica modificata; usa per routing e deleghe Codex Family Office AI.
---

# Model router

Leggi `family-office-bootstrap/docs/playbooks/02-model-routing.md` **solo se occorre delegare**. Riusa la configurazione Codex v3.1 esistente, verificata dalla CLI del progetto; non migrare a modelli non disponibili sulla sola base della documentazione.

- Change tecnico in loader, API o test, con pack immutati: `fo_implementer` Terra/medium, reviewer tecnico `fo_reviewer` se integrazione sensibile.
- Nuova semantica normativa, fonti, periodi o entitlement: `fo_normative_reviewer` Sol/xhigh; review esatta, non auto-approvazione.
- Nuove formule finanziarie: `fo_financial_reviewer` Sol/high.
- Design cross-module non deciso: `fo_architect` Sol/high.
- Fix documentale limitato: `fo_docs_editor` Luna/medium; discovery `fo_explorer` Luna/low.

Classifica il diff, non il dominio nominale del file. Registra routing intenzionale nel planner prima della delega. Bounded review, nessun polling o retry senza cambiamento materiale; vedi `12-dual-gate-and-convergence.md`. Non salvare chain-of-thought.
