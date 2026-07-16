import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "manual-assumptions/v1"
DRAFT_SCHEMA_VERSION = "manual-assumptions-draft/v1"


class AssumptionsImportError(ValueError):
    pass


@dataclass(frozen=True)
class FieldRule:
    path: tuple[str, ...]
    expected_type: type | tuple[type, ...]
    minimum: float | None = None
    maximum: float | None = None


FIELD_RULES = (
    FieldRule(("personal", "current_age"), int, minimum=0, maximum=120),
    FieldRule(("personal", "target_retirement_age"), int, minimum=0, maximum=120),
    FieldRule(("cashflow", "family_expenses_yearly"), (int, float), minimum=0),
    FieldRule(("cashflow", "net_salary_monthly"), (int, float), minimum=0),
    FieldRule(("cashflow", "salary_months"), int, minimum=1, maximum=15),
    FieldRule(("returns", "scenario"), str),
    FieldRule(("returns", "nominal_return"), (int, float), minimum=-1, maximum=1),
)

OPTIONAL_FIELD_RULES = (
    FieldRule(("cashflow", "retirement_income_yearly"), (int, float), minimum=0),
    FieldRule(("cashflow", "spouse_net_salary_monthly"), (int, float), minimum=0),
    FieldRule(("cashflow", "spouse_salary_months"), int, minimum=0, maximum=15),
    FieldRule(("cashflow", "rental_income_monthly_net"), (int, float), minimum=0),
    FieldRule(("returns", "nominal_volatility"), (int, float), minimum=0, maximum=1),
)


def load_assumptions(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise AssumptionsImportError(f"Assumptions file not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AssumptionsImportError(f"Invalid JSON in assumptions file: {exc}") from exc

    if not isinstance(data, dict):
        raise AssumptionsImportError("Assumptions file must contain a JSON object")

    validate_assumptions(data)
    return data


def validate_assumptions(data: dict[str, Any]) -> None:
    errors: list[str] = []

    for rule in FIELD_RULES:
        value = _get_nested(data, rule.path)
        field_name = ".".join(rule.path)
        if value is None:
            errors.append(f"Missing required field: {field_name}")
            continue
        if not isinstance(value, rule.expected_type):
            errors.append(f"Invalid type for {field_name}")
            continue
        if isinstance(value, str) and not value.strip():
            errors.append(f"Invalid empty value for {field_name}")
            continue
        if rule.minimum is not None and value < rule.minimum:
            errors.append(f"Value below minimum for {field_name}")
        if rule.maximum is not None and value > rule.maximum:
            errors.append(f"Value above maximum for {field_name}")

    for rule in OPTIONAL_FIELD_RULES:
        value = _get_nested(data, rule.path)
        field_name = ".".join(rule.path)
        if value is None:
            continue
        if not isinstance(value, rule.expected_type):
            errors.append(f"Invalid type for {field_name}")
            continue
        if rule.minimum is not None and value < rule.minimum:
            errors.append(f"Value below minimum for {field_name}")
        if rule.maximum is not None and value > rule.maximum:
            errors.append(f"Value above maximum for {field_name}")

    current_age = _get_nested(data, ("personal", "current_age"))
    target_age = _get_nested(data, ("personal", "target_retirement_age"))
    if isinstance(current_age, int) and isinstance(target_age, int) and target_age < current_age:
        errors.append("target_retirement_age must be greater than or equal to current_age")

    if errors:
        raise AssumptionsImportError("; ".join(errors))


def normalize_assumptions(data: dict[str, Any], source_path: Path) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "ManualAssumptions",
        "source": {
            "type": "manual-json",
            "path": str(source_path),
        },
        "assumptions": data,
    }


def import_assumptions(input_path: Path, output_path: Path) -> dict[str, Any]:
    data = load_assumptions(input_path)
    normalized = normalize_assumptions(data, input_path)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(normalized, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise AssumptionsImportError(f"Cannot write output snapshot: {output_path}") from exc
    return normalized


def prepare_assumptions_input(
    template_path: Path,
    draft_path: Path,
    checklist_path: Path,
    overwrite: bool = False,
) -> dict[str, Any]:
    if not template_path.exists():
        raise AssumptionsImportError(f"Assumptions template not found: {template_path}")
    try:
        template = json.loads(template_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AssumptionsImportError(f"Invalid JSON in assumptions template: {exc}") from exc
    if not isinstance(template, dict):
        raise AssumptionsImportError("Assumptions template must contain a JSON object")

    _ensure_can_write(draft_path, overwrite)
    _ensure_can_write(checklist_path, overwrite)

    draft = {
        "schema_version": DRAFT_SCHEMA_VERSION,
        "record_type": "ManualAssumptionsDraft",
        "status": "requires_real_values",
        "instructions": [
            "Copy reviewed real values into base-assumptions.json before importing.",
            "Do not import this draft directly.",
        ],
        "assumptions": _empty_assumptions(),
        "source_template": str(template_path),
    }
    checklist = _checklist_text(draft_path, template_path)

    try:
        draft_path.parent.mkdir(parents=True, exist_ok=True)
        draft_path.write_text(
            json.dumps(draft, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        checklist_path.parent.mkdir(parents=True, exist_ok=True)
        checklist_path.write_text(checklist, encoding="utf-8")
    except OSError as exc:
        raise AssumptionsImportError("Cannot write assumptions preparation files") from exc

    return {
        "schema_version": "assumptions-preparation/v1",
        "record_type": "AssumptionsPreparation",
        "draft_path": str(draft_path),
        "checklist_path": str(checklist_path),
        "status": "prepared",
    }


def _ensure_can_write(path: Path, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise AssumptionsImportError(f"Refusing to overwrite existing file: {path}")


def _empty_assumptions() -> dict[str, Any]:
    return {
        "personal": {
            "current_age": None,
            "target_retirement_age": None,
        },
        "cashflow": {
            "family_expenses_yearly": None,
            "retirement_income_yearly": None,
            "net_salary_monthly": None,
            "salary_months": None,
            "spouse_net_salary_monthly": None,
            "spouse_salary_months": None,
            "rental_income_monthly_net": None,
        },
        "returns": {
            "scenario": None,
            "nominal_return": None,
            "nominal_volatility": None,
        },
        "notes": "Replace nulls with reviewed real assumptions in base-assumptions.json.",
    }


def _checklist_text(draft_path: Path, template_path: Path) -> str:
    return "\n".join(
        [
            "# Manual Assumptions Input Checklist",
            "",
            "## Files",
            "",
            f"- Draft: `{draft_path}`",
            f"- Template reference: `{template_path}`",
            "- Final private input to create: `base-assumptions.json`",
            "",
            "## Required Values",
            "",
            "- `personal.current_age`",
            "- `personal.target_retirement_age`",
            "- `cashflow.family_expenses_yearly`",
            "- `cashflow.retirement_income_yearly` (optional; use `0` if none)",
            "- `cashflow.net_salary_monthly`",
            "- `cashflow.salary_months`",
            "- `cashflow.spouse_net_salary_monthly` (optional; use `0` if none)",
            "- `cashflow.spouse_salary_months` (optional; use `0` if none)",
            "- `cashflow.rental_income_monthly_net` (optional; net monthly rent, use `0` if none)",
            "- `returns.scenario`",
            "- `returns.nominal_return`",
            "- `returns.nominal_volatility` (required by Monte Carlo)",
            "",
            "## Review Steps",
            "",
            "1. Copy the draft structure to `base-assumptions.json`.",
            "2. Replace every `null` with reviewed real assumptions.",
            "3. Run `fo assumptions import`.",
            "4. Run `fo assumptions check`.",
            "5. Re-run net worth, retirement simulation and report.",
            "",
        ]
    )


def _get_nested(data: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = data
    for part in path:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current
