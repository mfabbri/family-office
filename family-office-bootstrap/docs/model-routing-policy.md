# Model routing policy v4.0 — 2026-11-21

- Parent: `gpt-6-luna/low`; nessuna delega se il task e' risolvibile localmente.
- Explorer/docs: `gpt-6-luna/low` o medium per editing effettivo.
- Planner: `gpt-6.1-terra/medium`.
- Implementazione + review tecnica: `gpt-6.2-sol/medium` con **agenti indipendenti**, mai reviewer che approva il proprio codice.
- Finanziario: `gpt-6.2-sol/high` per nuova semantica numerica.
- Normativo: `gpt-6.2-sol/high` solo su nuove fonti/condizioni/validita' materiale.
- Escalation: `gpt-6.2-astra/high` per controversia giuridica primaria delimitata e autorizzata; `fo_architect` Astra/medium per trade-off reali.

La matrice eseguibile e i trigger sono in `playbooks/02-model-routing.md`; il protocollo anti-loop in `playbooks/12-dual-gate-and-convergence.md`. Preservare l'identita' esatta di fonti/Rules/Knowledge. Il gate software non convalida il diritto previdenziale.

## Audit effettivo e usage

- `.codex/hooks/model-routing-audit.py` -> `.runtime/model-routing.ndjson`: **solo traccia della selezione**, non conteggio token.
- `planning/report-token-usage.py`: totale input/cached/output/reasoning da export Codex `--json`; nessun prezzo presunto e nessun prompt mostrato.
- UI Work/Codex Settings > Usage per reale quota piano. Prezzi API soltanto se si usa una API key.
- Pianificazione budget: massimo 2 deleghe sostanziali per task, un solo reviewer per finding, nessun polling infinito, controllo del diff prima di nuova review.
- Non salvare chain-of-thought, contenuti personali o trascrizioni sensibili nel repository.
