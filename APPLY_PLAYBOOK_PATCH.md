# Apply the token-efficient agent playbook patch

Extract this archive over the root of `family-office-ai-project`, allowing replacement of existing files.

## Added

- root `AGENTS.md` as a short repository map;
- `family-office-bootstrap/docs/playbooks/`;
- project-scoped `.codex/config.toml`;
- three optional custom Codex agents.

## Replaced

- bootstrap, engine, rules and knowledge `AGENTS.md`;
- bootstrap `developer-playbook.md` and `workflow.md`.

## Behavior change

Agents no longer read every roadmap and governance file at session start. They classify the task, apply an exploration budget, select model/reasoning effort, and expand context only when concrete triggers require it.

## Recommended verification

```bash
codex --strict-config
```

Inside Codex:

```text
/debug-config
/status
```

No application code, rule pack, schema, workspace data or roadmap status is modified by this patch.
