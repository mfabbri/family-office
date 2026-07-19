# Codex model routing

This project intentionally combines GPT-5.5 and GPT-5.6.

- Main session: `gpt-5.5`, medium reasoning.
- `fo_explorer`: `gpt-5.6-luna`, low reasoning.
- `fo_reviewer`: `gpt-5.6-terra`, high reasoning.
- `fo_normative_reviewer`: `gpt-5.6-sol`, extra-high reasoning.

The generic alias `gpt-5.6` is deliberately forbidden because ChatGPT-authenticated Codex may reject it. Always use the complete IDs `gpt-5.6-sol`, `gpt-5.6-terra`, or `gpt-5.6-luna`.

Optional launch profiles are available:

```powershell
codex --profile standard
codex --profile luna
codex --profile terra
codex --profile sol
```

GPT-5.6 requires a current Codex client and account availability. The installer checks the local CLI version and rewrites only the exact obsolete alias `gpt-5.6` to `gpt-5.6-sol`; suffixed GPT-5.6 IDs are preserved.
