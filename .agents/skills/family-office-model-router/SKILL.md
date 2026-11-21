---
name: family-office-model-router
description: Usa per selezionare uno specialista Codex SOLO quando un task Family Office richiede delega; non usare per singolo edit locale o domande senza impatto sul repository. Output un routing motivato con budget, scope e done-when.
---

# Family Office model router v4.0

Leggi il solo `family-office-bootstrap/docs/playbooks/02-model-routing.md` se occorre delegare. Classifica **il diff**, non il dominio nominale. Nessun reviewer legale su documentazione previdenziale immutata.

- T0/T1 locale: parent `gpt-6-luna/low` e test mirato, senza agent.
- Discovery: `fo_explorer` Luna/low. Docs: `fo_docs_editor` Luna/medium.
- Pianificazione: `fo_planner` Terra/medium. Runtime: `fo_implementer` GPT-6.2 Sol/medium.
- Review indipendente di API e contratti: `fo_reviewer` GPT-6.2 Sol/medium.
- Nuova formula: `fo_financial_reviewer` Sol/high.
- Nuova interpretazione normativa: `fo_normative_reviewer` Sol/high, source/version/scope esatti.
- Solo conflitto sostanziale dimostrato: `fo_normative_escalation` Astra/high con budget esplicito; architettura irrisolta: `fo_architect` Astra/medium.

Non chiamare il router per una tabella testuale, un listing o un pack gia' validato che non cambia semantica. Restituisci agente, modello, effort, 1 frase di motivo, files/test e condizione di arresto. Un evento PENDING o timeout non autorizza un nuovo spawn. Misura uso reale con `report-token-usage.py` solo da JSONL Codex, mai inventare conteggi dai log hook.
