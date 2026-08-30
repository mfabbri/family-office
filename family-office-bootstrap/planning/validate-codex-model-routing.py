from __future__ import annotations

import json
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

EXPECTED = {
    "fo-explorer": ("gpt-5.6-luna", "low"),
    "fo-docs-reviewer": ("gpt-5.6-luna", "medium"),
    "fo-docs-editor": ("gpt-5.6-luna", "medium"),
    "fo-planner": ("gpt-5.6-terra", "medium"),
    "fo-implementer": ("gpt-5.6-terra", "medium"),
    "fo-reviewer": ("gpt-5.6-terra", "high"),
    "fo-architect": ("gpt-5.6-sol", "high"),
    "fo-financial-reviewer": ("gpt-5.6-sol", "high"),
    "fo-normative-reviewer": ("gpt-5.6-sol", "xhigh"),
}

ROUTES = {
    "low": {
        ("fo_explorer", "gpt-5.6-luna", "low"),
        ("fo_docs_reviewer", "gpt-5.6-luna", "medium"),
        ("fo_docs_editor", "gpt-5.6-luna", "medium"),
    },
    "medium": {
        ("fo_planner", "gpt-5.6-terra", "medium"),
        ("fo_implementer", "gpt-5.6-terra", "medium"),
    },
    "review": {("fo_reviewer", "gpt-5.6-terra", "high")},
    "high": {
        ("fo_architect", "gpt-5.6-sol", "high"),
        ("fo_financial_reviewer", "gpt-5.6-sol", "high"),
    },
    "critical": {("fo_normative_reviewer", "gpt-5.6-sol", "xhigh")},
}


def fail(msg: str) -> None:
    print("FAIL:", msg)
    raise SystemExit(1)


def main() -> int:
    cfg = tomllib.loads((ROOT / ".codex/config.toml").read_text(encoding="utf-8"))
    if "profiles" in cfg:
        fail("project-local profiles present")
    if (cfg.get("model"), cfg.get("model_reasoning_effort")) != ("gpt-5.6-luna", "medium"):
        fail("parent must be Luna/medium router")

    ag = cfg.get("agents", {})
    if ag.get("max_concurrent_threads_per_session") != 3:
        fail("max_concurrent_threads_per_session != 3")
    if "max_threads" in ag:
        fail("legacy max_threads still present")

    for filename, expected in EXPECTED.items():
        p = ROOT / ".codex/agents" / f"{filename}.toml"
        if not p.is_file():
            fail(f"missing agent config: {filename}")
        data = tomllib.loads(p.read_text(encoding="utf-8"))
        if (data.get("model"), data.get("model_reasoning_effort")) != expected:
            fail(f"{filename} model/effort mismatch")
        if data.get("model") == "gpt-5.6":
            fail(f"{filename} uses forbidden unsuffixed gpt-5.6 alias")

    planner_path = ROOT / "family-office-bootstrap/planning/current-work.json"
    planner = json.loads(planner_path.read_text(encoding="utf-8"))
    active = planner.get("status") in {"selected", "in_progress", "blocked"}
    route = planner.get("routing")
    if active and not route:
        fail("active planner has no routing block")
    if route:
        if route.get("policy_version") != "3.1":
            fail(f"planner routing policy_version != 3.1: {route.get('policy_version')}")
        tup = (route.get("agent"), route.get("model"), route.get("reasoning_effort"))
        if tup not in ROUTES.get(route.get("tier"), set()):
            fail(f"unsupported planner route: {route.get('tier')} {tup}")

    try:
        import jsonschema
    except ImportError:
        print("WARN: jsonschema not installed; schema validation skipped")
    else:
        schema = json.loads((ROOT / "family-office-bootstrap/planning/current-work.schema.json").read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(planner)

    for rel in [
        ".agents/skills/family-office-model-router/SKILL.md",
        ".agents/skills/family-office-session/SKILL.md",
        ".agents/skills/family-office-planner/SKILL.md",
        "family-office-bootstrap/planning/validate-codex-model-routing.py",
    ]:
        try:
            r = subprocess.run(["git", "check-ignore", "-q", rel], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if r.returncode == 0:
                fail(f"required routing asset is ignored by git: {rel}")
        except FileNotFoundError:
            print("WARN: git not found; ignore validation skipped")

    json.loads((ROOT / ".codex/hooks.json").read_text(encoding="utf-8"))
    if not (ROOT / ".codex/hooks/model-routing-audit.py").is_file():
        fail("runtime audit hook script missing")

    # Domain-specific playbooks/guardrails must survive the routing migration.
    root_agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    bootstrap_agents = (ROOT / "family-office-bootstrap/AGENTS.md").read_text(encoding="utf-8")
    router = (ROOT / "family-office-bootstrap/docs/playbooks/00-task-router.md").read_text(encoding="utf-8")
    playbooks = (ROOT / "family-office-bootstrap/docs/playbooks/README.md").read_text(encoding="utf-8")
    for needle in ["modifica manuale di JSON", "domanda o decisione familiare", "11-investment-opportunity.md"]:
        if needle not in root_agents:
            fail(f"root AGENTS guardrail missing: {needle}")
    if "11-work-transition-retirement-bridge.md" not in bootstrap_agents:
        fail("work-transition playbook reference missing from bootstrap AGENTS")
    if "## Investment opportunity routing" not in router:
        fail("investment opportunity routing section missing")
    for needle in ["11-investment-opportunity.md", "11-work-transition-retirement-bridge.md"]:
        if needle not in playbooks:
            fail(f"playbook index missing: {needle}")
    for rel in [
        "family-office-bootstrap/docs/playbooks/11-investment-opportunity.md",
        "family-office-bootstrap/docs/playbooks/11-work-transition-retirement-bridge.md",
    ]:
        if not (ROOT / rel).is_file():
            fail(f"domain playbook missing from repository: {rel}")

    print("OK: Family Office AI Codex model routing v3.1 is structurally coherent")
    print("parent: tier=router agent=parent model=gpt-5.6-luna effort=medium")
    if route:
        print(f"planner: tier={route['tier']} agent={route['agent']} model={route['model']} effort={route['reasoning_effort']}")
    else:
        print(f"planner: status={planner.get('status')} (route will be selected with the next active increment)")

    runtime = ROOT / "family-office-bootstrap/planning/.runtime/model-routing.ndjson"
    if runtime.exists():
        lines = runtime.read_text(encoding="utf-8", errors="replace").splitlines()[-5:]
        print("runtime audit (last events):")
        for line in lines:
            try:
                e = json.loads(line)
                print(f"  {e.get('event')}: agent={e.get('agent_type')} model={e.get('model')}")
            except Exception:
                pass
    else:
        print("runtime audit: no events yet (trust hooks with /hooks, then run a session)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
