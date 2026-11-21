from __future__ import annotations

import json
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY = "4.0"
EXPECTED = {
    "fo-explorer": ("gpt-6-luna", "low"),
    "fo-docs-reviewer": ("gpt-6-luna", "low"),
    "fo-docs-editor": ("gpt-6-luna", "medium"),
    "fo-planner": ("gpt-6.1-terra", "medium"),
    "fo-implementer": ("gpt-6.2-sol", "medium"),
    "fo-reviewer": ("gpt-6.2-sol", "medium"),
    "fo-architect": ("gpt-6.2-astra", "medium"),
    "fo-financial-reviewer": ("gpt-6.2-sol", "high"),
    "fo-normative-reviewer": ("gpt-6.2-sol", "high"),
    "fo-normative-escalation": ("gpt-6.2-astra", "high"),
    "fo-retirement-transition-reviewer": ("gpt-6.2-sol", "high"),
}
TIERS = {
    "low": {"fo_explorer", "fo_docs_reviewer", "fo_docs_editor"},
    "medium": {"fo_planner", "fo_implementer"},
    "review": {"fo_reviewer"},
    "high": {"fo_architect", "fo_financial_reviewer"},
    "critical": {"fo_normative_reviewer", "fo_normative_escalation"},
}
LEGACY_ROUTES = {
    ("low", "fo_explorer", "gpt-5.6-luna", "low"),
    ("low", "fo_docs_reviewer", "gpt-5.6-luna", "medium"),
    ("low", "fo_docs_editor", "gpt-5.6-luna", "medium"),
    ("medium", "fo_planner", "gpt-5.6-terra", "medium"),
    ("medium", "fo_implementer", "gpt-5.6-terra", "medium"),
    ("review", "fo_reviewer", "gpt-5.6-terra", "high"),
    ("high", "fo_architect", "gpt-5.6-sol", "high"),
    ("high", "fo_financial_reviewer", "gpt-5.6-sol", "high"),
    ("critical", "fo_normative_reviewer", "gpt-5.6-sol", "xhigh"),
}


def fail(message: str) -> None:
    raise SystemExit("FAIL: " + message)


def validate_route(route: dict, status: str) -> str:
    version = route.get("policy_version")
    value = (route.get("tier"), route.get("agent"), route.get("model"), route.get("reasoning_effort"))
    if version == "3.1":
        if status != "blocked":
            fail("legacy planner route may only be retained in BLOCKED historical work; migrate on next activation")
        if value not in LEGACY_ROUTES:
            fail("historical 3.1 route invalid")
        return "legacy-blocked; preserve previous independent reviewer provenance"
    if version != POLICY:
        fail(f"planner route version {version!r} unsupported")
    if route.get("agent") not in TIERS.get(route.get("tier"), set()):
        fail("agent/tier mismatch")
    key = route["agent"].replace("_", "-")
    if (route.get("model"), route.get("reasoning_effort")) != EXPECTED[key]:
        fail("agent/model/reasoning mismatch")
    if key == "fo-normative-escalation" and not route.get("delegation_budget"):
        fail("Astra normative escalation needs explicit authorized delegation budget")
    return "4.0"


def main() -> int:
    cfg = tomllib.loads((ROOT / ".codex/config.toml").read_text(encoding="utf-8"))
    if "profiles" in cfg:
        fail("project-local profiles must remain absent")
    if (cfg.get("model"), cfg.get("model_reasoning_effort")) != ("gpt-6-luna", "low"):
        fail("parent must be GPT-6 Luna/low")
    agents = cfg.get("agents", {})
    if agents.get("max_concurrent_threads_per_session") != 3 or "max_threads" in agents:
        fail("max_concurrent_threads_per_session must remain 3")
    if agents.get("default_subagent_model") != "gpt-6.1-terra":
        fail("default subagent model differs from v4.0")
    declared = {key for key in agents if key.startswith("fo_")}
    expected_names = {key.replace("-", "_") for key in EXPECTED if key != "fo-retirement-transition-reviewer"}
    if not expected_names.issubset(declared):
        fail("missing custom agent binding(s): " + str(expected_names - declared))
    for filename, expected in EXPECTED.items():
        agent_file = ROOT / ".codex/agents" / f"{filename}.toml"
        if not agent_file.is_file():
            fail("missing agent config: " + filename)
        data = tomllib.loads(agent_file.read_text(encoding="utf-8"))
        if (data.get("model"), data.get("model_reasoning_effort")) != expected:
            fail("agent model mismatch: " + filename)
        if filename != "fo-retirement-transition-reviewer":  # legacy manual specialist; not auto-routed
            binding = agents[filename.replace("-", "_")]
            if binding.get("config_file") != "agents/" + filename + ".toml":
                fail("bad agent config_file: " + filename)
    plan = json.loads((ROOT / "family-office-bootstrap/planning/current-work.json").read_text(encoding="utf-8"))
    route = plan.get("routing")
    if plan.get("status") in {"selected", "in_progress", "blocked"} and not route:
        fail("active planner is missing route")
    route_msg = validate_route(route, plan.get("status")) if route else "none"
    try:
        import jsonschema
    except ImportError:
        print("WARN: jsonschema missing; JSON schema not validated (install for full checks)")
    else:
        spec = json.loads((ROOT / "family-office-bootstrap/planning/current-work.schema.json").read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(spec, format_checker=jsonschema.FormatChecker()).validate(plan)
    for rel in [
        ".agents/skills/family-office-model-router/SKILL.md",
        ".agents/skills/family-office-session/SKILL.md",
        ".agents/skills/family-office-planner/SKILL.md",
        "family-office-bootstrap/planning/validate-codex-model-routing.py",
    ]:
        try:
            result = subprocess.run(["git", "check-ignore", "-q", rel], cwd=ROOT,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if result.returncode == 0: fail("required routing asset ignored: " + rel)
        except FileNotFoundError:
            print("WARN: git unavailable; ignore check omitted")
    json.loads((ROOT / ".codex/hooks.json").read_text(encoding="utf-8"))
    if not (ROOT / ".codex/hooks/model-routing-audit.py").is_file(): fail("routing audit hook missing")
    root = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    boot = (ROOT / "family-office-bootstrap/AGENTS.md").read_text(encoding="utf-8")
    router = (ROOT / "family-office-bootstrap/docs/playbooks/00-task-router.md").read_text(encoding="utf-8")
    playbook_index = (ROOT / "family-office-bootstrap/docs/playbooks/README.md").read_text(encoding="utf-8")
    for needle in ("modifica manuale di JSON", "domanda o decisione familiare", "11-investment-opportunity.md"):
        if needle not in root: fail("root AGENTS guardrail missing: " + needle)
    if "11-work-transition-retirement-bridge.md" not in boot: fail("work-transition bootstrap reference missing")
    if "## Investment opportunity routing" not in router: fail("investment router missing")
    for needle in ("11-investment-opportunity.md", "11-work-transition-retirement-bridge.md"):
        if needle not in playbook_index: fail("domain playbook index missing " + needle)
    print("OK: Family Office AI Codex routing 4.0 validated")
    print("Parent: gpt-6-luna/low. Planner route:", route_msg)
    print("Note: structural checks cannot certify local Codex runtime/entitlement; check actual model picker before using")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
