# Model Catalog Review

Verificare almeno trimestralmente o quando Codex segnala deprecazioni:

- modello principale raccomandato da OpenAI;
- modello rapido/economico disponibile;
- livelli di `model_reasoning_effort` supportati;
- modelli deprecati presenti in `.codex/` o nella CI;
- comportamento dei subagent e limiti di concorrenza.

Aggiornare soltanto:

- `.codex/config.toml`;
- `.codex/agents/*.toml`;
- tabella in `02-model-routing.md`.

Non disseminare nomi modello in altri documenti.
