# Model routing v4.0 — 21 novembre 2026

## Goal

Minimizzare consumo di contesto, reasoning e deleghe **per risultato osservabile**. Evitare il falso risparmio che genera dieci review su uno stesso difetto. La selezione parte dal diff e dalla domanda decisionale, non dalle parole `pensione`, `fisco` o dalla dimensione del repository.

## Modelli disponibili e uso proposto

| Tier | Custom agent | Modello Codex | Reasoning | Quando |
|---|---|---|---|---|
| controller | parent | `gpt-6-luna` | low | Smista, esegue step locali minimi, produce evidenze e riepilogo |
| low | `fo_explorer` | `gpt-6-luna` | low | Discovery read-only mirata, solo se evita lavoro duplicato |
| low | `fo_docs_reviewer` | `gpt-6-luna` | low | Coerenza documentale circoscritta |
| low | `fo_docs_editor` | `gpt-6-luna` | medium | Correzione docs/testo/asset di governance |
| medium | `fo_planner` | `gpt-6.1-terra` | medium | Piano di implementazione entro architettura definita |
| medium | `fo_implementer` | `gpt-6.2-sol` | medium | Implementazione code/test deterministica |
| review | `fo_reviewer` | `gpt-6.2-sol` | medium | Review tecnica indipendente, rischio e regressioni |
| high | `fo_architect` | `gpt-6.2-astra` | medium | Solo trade-off architetturali non risolti |
| high | `fo_financial_reviewer` | `gpt-6.2-sol` | high | Nuova formula, semantica cash flow, rischio economico |
| critical | `fo_normative_reviewer` | `gpt-6.2-sol` | high | Nuova interpretazione legale *materiale*, esatta e delimitata |
| critical escalation | `fo_normative_escalation` | `gpt-6.2-astra` | high | Una sola controversia primaria irrisolta con motivazione, budget e autorizzazione |

Lo specialista storico `fo_retirement_transition_reviewer`, se utilizzato direttamente, impiega `gpt-6.2-sol/high` ed e' soggetto allo stesso gate indipendente. Non e' una delega obbligatoria in aggiunta ai reviewer sopra.

**GPT-6.2 Sol/Astra** sono stati annunciati il 17 novembre 2026. Il menu dell'utente dimostra disponibilita' nel suo ambiente Work/Codex; **non garantisce** disponibilita' dello stesso slug nel suo CLI locale e non indica il costo reale. Verificare `codex --version` e il model picker del client prima del primo run. Nessun fallback silenzioso; registrare la scelta nel planner. I prezzi API e i limiti Work/Codex sono sistemi differenti.

## Routing in 7 passaggi

1. Identificare una modifica, un risultato verificabile, massimo 3 file/aree iniziali e un test di entrata. Se basta un edit locale, **nessuna delega**.
2. Leggere soltanto file, schema e test connessi, usando `01-context-budget.md`.
3. Classificare la fase reale: T0 editoriale, T1–T3 software, T4 finanziario o normativo **solo se cambia la semantica**, T5 trade-off.
4. Preferire una sola route attiva, il minimo effort utile e un output bounded (finding + riferimenti + esito).
5. Richiedere reviewer normativo solo per legge/periodo/eligibility/claim nuove o cambiate; binding del pack immutato => review tecnica.
6. Elevare a Astra solo se **un punto sostanziale** non puo' essere risolto con fonte primaria e test mirati; una review indipendente non puo' essere sostituita da auto-approvazione.
7. Registrare `routing` (`policy_version: 4.0`) e gli eventi reali. La trace storica v3.1 del planner bloccato non va riscritta retroattivamente.

## Budget anti-loop e gestione uso

- Budget default: 0 subagent per T0/T1 locale; al massimo 1 implementer + 1 reviewer dove necessario; 3 thread possibili, ma **mai lanciare tutti per default**.
- PIANO: <= 12 righe, RISULTATO reviewer: <= 12 righe / 5 finding, salvo evidenza critica. Nessuna chain-of-thought, dump file, log completo.
- All'inizio confrontare candidati, diff e hash esistenti. No nuove consultazioni se `(hash, scope, finding, period)` non cambia.
- Primo NO-GO: una remediation circoscritta + test di regressione. Secondo finding diverso: **analizzare il modello di gate e la granularita'** prima di creare un suffisso. Niente loop automatici fino a GO.
- Timebox e budget in planner su versione/esatto hash. Senza verdetto: PENDING, non auto-riprovare.
- Rivedere budget ogni 2 turni di ricerca/decisione o quando non cambia il diff. A budget esaurito: checkpoint e blocker, non un altro agente.
- Ridurre **contesto prima di modello**: `rg`, range selettivi, output `--quiet`, registrare summary verificabile, compaction prima di saturazione. Non condensare né modificare le evidenze legali immutabili.
- Report token da `codex exec --json` tramite `python family-office-bootstrap/planning/report-token-usage.py <run.ndjson>`: conta solo `turn.completed.usage` senza stampare prompt. Il log hook `model-routing.ndjson` traccia modelli/ruoli ma **non** spesa token.
- Per Work/Desktop non inferire token da messaggi o numero di chiamate: verificare il consumo dall'interfaccia **Settings → Usage**. Per API, prezzi e cache vanno valutati sulla fatturazione reale, non su stime fisse nel router.

## Fallback e schema

Il validator `planning/validate-codex-model-routing.py` verifica `.codex/config.toml`, TOML agent, schema e piano. Accetta route `3.1` **soltanto** se l'incremento storico e' `blocked`, per non falsificare review gia' attestate. Alla prima nuova selezione, aprire route `4.0` con una nuova trace e mantenere lo storico nel decision log. Mai cambiare il modello del reviewer di una review conclusa; mai invocare Astra normativo senza autorizzazione esplicita per `versione/hash/scope/budget`.

## Fonti di policy (accesso pubblico al 2026-11-21)

- OpenAI, 2026-11-17: https://developers.openai.com/api/docs/changelog (GPT-6.2 Sol/Astra)
- OpenAI, Work/Codex: https://help.openai.com/en/articles/20001275-chatgpt-work-and-codex
- OpenAI, usage/reasoning: https://help.openai.com/en/articles/20001516-managing-usage-with-gpt-6-astra-in-work-and-codex
- OpenAI, skill routing/compaction: https://developers.openai.com/blog/skills-shell-tips
- OpenAI, Codex non-interactive JSONL: https://learn.chatgpt.com/docs/non-interactive-mode
