import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "pension-income/v1"
CENT = Decimal("0.01")


class PensionIncomeError(ValueError):
    pass


def compose_pension_income(
    inps_snapshot_path: Path | None,
    spanish_pension_snapshot_path: Path | None,
    output_path: Path,
    *,
    rita_options_snapshot_path: Path | None = None,
    eu_coordination_snapshot_path: Path | None = None,
    include_rita: bool = True,
) -> dict[str, Any]:
    data_gaps: list[dict[str, Any]] = []
    sources: dict[str, str] = {}
    streams: list[dict[str, Any]] = []

    inps = _read_optional_snapshot(inps_snapshot_path, "inps", "inps-pension/v1", data_gaps, sources)
    spanish = _read_optional_snapshot(
        spanish_pension_snapshot_path,
        "spanish_statutory_pension",
        "spanish-statutory-pension/v1",
        data_gaps,
        sources,
    )
    rita = (
        _read_optional_snapshot(rita_options_snapshot_path, "rita_options", "rita-options/v1", data_gaps, sources)
        if include_rita
        else None
    )
    coordination = _read_optional_snapshot(
        eu_coordination_snapshot_path,
        "eu_pension_coordination",
        "eu-pension-coordination-it-es/v1",
        data_gaps,
        sources,
        missing_is_gap=False,
    )

    if inps is not None:
        streams.extend(_inps_streams(inps, data_gaps))
    if spanish is not None:
        streams.extend(_spanish_streams(spanish, data_gaps))
    if rita is not None and include_rita:
        streams.extend(_rita_streams(rita, data_gaps))

    if coordination is not None:
        data_gaps.extend(_coordination_gaps(coordination))

    summary = _summary(streams, data_gaps)
    status = "complete" if streams and summary["data_gap_count"] == 0 else "partial" if streams else "blocked_missing_inputs"
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "PensionIncomeSnapshot",
        "status": status,
        "sources": sources,
        "income_streams": streams,
        "summary": summary,
        "data_gaps": data_gaps,
        "notes": (
            "Pension income composer V1 keeps each pension source separate. It does not calculate tax, net income, "
            "currency conversion or statutory pension amounts. Annual totals include only explicit EUR recurring "
            "gross annual amounts."
        ),
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise PensionIncomeError(f"Cannot write pension income snapshot: {output_path}") from exc
    return snapshot


def _read_optional_snapshot(
    path: Path | None,
    source_key: str,
    expected_schema: str,
    data_gaps: list[dict[str, Any]],
    sources: dict[str, str],
    *,
    missing_is_gap: bool = True,
) -> dict[str, Any] | None:
    if path is None:
        return None
    if not path.exists():
        if missing_is_gap:
            data_gaps.append(
                {
                    "code": f"missing_{source_key}_snapshot",
                    "message": f"Missing {source_key} snapshot.",
                    "path": str(path),
                }
            )
        return None
    try:
        snapshot = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PensionIncomeError(f"Cannot read {source_key} snapshot: {path}") from exc
    if not isinstance(snapshot, dict):
        raise PensionIncomeError(f"{source_key} snapshot must be a JSON object: {path}")
    if snapshot.get("schema_version") != expected_schema:
        raise PensionIncomeError(
            f"Unsupported {source_key} schema: {snapshot.get('schema_version')}; expected {expected_schema}"
        )
    sources[source_key] = str(path)
    return snapshot


def _inps_streams(snapshot: dict[str, Any], data_gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    projection = snapshot.get("projection") if isinstance(snapshot.get("projection"), dict) else {}
    monthly = projection.get("monthly_gross_pension")
    start_date = projection.get("retirement_date")
    if monthly in (None, ""):
        data_gaps.append({"code": "missing_inps_monthly_gross_pension", "message": "INPS projection has no monthly gross pension."})
        return []
    stream_gaps = [{"code": "missing_inps_annual_gross_pension", "message": "INPS snapshot does not expose an annual gross amount."}]
    if start_date in (None, ""):
        stream_gaps.append({"code": "missing_inps_start_date", "message": "INPS projection has no retirement date."})
    return [
        _stream(
            stream_id="inps_public_pension",
            country="IT",
            payer="INPS",
            benefit_type="public_statutory_pension",
            source_type="documentary_projection",
            status=snapshot.get("extraction_status", "available"),
            start_date=start_date,
            periodicity="monthly_recurring",
            confidence="medium",
            gross={"monthly_amount": _money(monthly), "annual_amount": None, "currency": "EUR"},
            data_gaps=stream_gaps,
        )
    ]


def _spanish_streams(snapshot: dict[str, Any], data_gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gross = snapshot.get("gross_pension") if isinstance(snapshot.get("gross_pension"), dict) else None
    if snapshot.get("status") != "complete" or gross is None:
        data_gaps.append(
            {
                "code": "spanish_pension_not_calculable",
                "message": "Spanish statutory pension snapshot has no calculable gross pension.",
                "source_status": snapshot.get("status"),
            }
        )
        data_gaps.extend(snapshot.get("data_gaps", []))
        return []
    return [
        _stream(
            stream_id="spanish_public_pension",
            country="ES",
            payer="Seguridad Social",
            benefit_type="public_statutory_pension",
            source_type=snapshot.get("result_type", "internal_estimate"),
            status="estimated",
            start_date=snapshot.get("retirement_date"),
            periodicity="annualized_recurring",
            confidence=snapshot.get("confidence", "medium"),
            gross={
                "monthly_amount": _money(gross.get("monthly_amount")),
                "annual_amount": _money(gross.get("annual_amount")),
                "currency": gross.get("currency", "EUR"),
                "payments_per_year": gross.get("payments_per_year"),
            },
            data_gaps=[],
        )
    ]


def _rita_streams(snapshot: dict[str, Any], data_gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if snapshot.get("status") != "complete":
        data_gaps.append(
            {
                "code": "rita_options_not_available",
                "message": "RITA options snapshot is not complete.",
                "source_status": snapshot.get("status"),
            }
        )
        return []
    streams: list[dict[str, Any]] = []
    for option in snapshot.get("options", []):
        if not isinstance(option, dict):
            continue
        monthly = option.get("gross_monthly_amount")
        total = option.get("gross_total_amount")
        if monthly in (None, ""):
            continue
        streams.append(
            _stream(
                stream_id=f"rita_{option.get('option_id', 'option')}",
                country="IT",
                payer="Complementary pension fund",
                benefit_type="rita_bridge_income",
                source_type="option_estimate",
                status="optional",
                start_date=None,
                periodicity="monthly_for_duration",
                confidence="medium",
                gross={
                    "monthly_amount": _money(monthly),
                    "annual_amount": None,
                    "total_amount": _money(total),
                    "currency": option.get("currency", "EUR"),
                    "duration_months": option.get("duration_months"),
                },
                data_gaps=[
                    {"code": "missing_rita_start_date", "message": "RITA option has no selected start date."},
                    {"code": "rita_not_annual_recurring", "message": "RITA is a finite bridge option and is excluded from recurring annual totals."},
                ],
            )
        )
    return streams


def _coordination_gaps(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for gap in snapshot.get("data_gaps", []):
        if isinstance(gap, dict):
            copied = dict(gap)
            copied["source"] = "eu_pension_coordination"
            gaps.append(copied)
    return gaps


def _stream(
    *,
    stream_id: str,
    country: str,
    payer: str,
    benefit_type: str,
    source_type: str,
    status: str,
    start_date: str | None,
    periodicity: str,
    confidence: str,
    gross: dict[str, Any],
    data_gaps: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "stream_id": stream_id,
        "country": country,
        "payer": payer,
        "benefit_type": benefit_type,
        "source_type": source_type,
        "status": status,
        "start_date": start_date,
        "periodicity": periodicity,
        "gross": gross,
        "net": {
            "status": "not_calculated",
            "data_gap_code": "net_tax_not_implemented",
        },
        "confidence": confidence,
        "data_gaps": data_gaps,
    }


def _summary(streams: list[dict[str, Any]], data_gaps: list[dict[str, Any]]) -> dict[str, Any]:
    total = Decimal("0.00")
    included_stream_ids: list[str] = []
    excluded_stream_ids: list[str] = []
    for stream in streams:
        gross = stream.get("gross", {})
        annual = gross.get("annual_amount") if isinstance(gross, dict) else None
        currency = gross.get("currency") if isinstance(gross, dict) else None
        if stream.get("periodicity") == "annualized_recurring" and annual not in (None, "") and currency == "EUR":
            total += _decimal(annual, "annual_amount")
            included_stream_ids.append(stream["stream_id"])
        else:
            excluded_stream_ids.append(stream["stream_id"])
    stream_gap_count = sum(len(stream.get("data_gaps", [])) for stream in streams)
    return {
        "stream_count": len(streams),
        "gross_annual_recurring_total": _format_money(total) if included_stream_ids else None,
        "gross_annual_recurring_total_currency": "EUR" if included_stream_ids else None,
        "gross_annual_recurring_total_included_stream_ids": included_stream_ids,
        "gross_annual_recurring_total_excluded_stream_ids": excluded_stream_ids,
        "data_gap_count": len(data_gaps) + stream_gap_count,
    }


def _money(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return _format_money(_decimal(value, "money"))


def _decimal(value: Any, field_name: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise PensionIncomeError(f"Invalid decimal for {field_name}: {value}") from exc


def _format_money(value: Decimal) -> str:
    return str(value.quantize(CENT))
