"""Guided workspace-local intake; all source meaning is explicitly attested."""

from __future__ import annotations

import hashlib
import json
import uuid
from copy import deepcopy
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


EVENT_LABELS = {
    "eligibility_date": "Data del solo diritto/percorso attestato",
    "requirements_met_date": "Data di soddisfacimento dei requisiti attestata",
    "official_recognition_date": "Data del riconoscimento amministrativo effettivo",
    "economic_effective_date": "Data di decorrenza economica attestata",
    "first_cash_payment_date": "Data del primo accredito effettivamente disponibile",
}
ROLES = {
    "eligibility_date": ("eligibility_legal_basis", "primary_legislation"),
    "requirements_met_date": ("requirements_evidence", "official_administrative_guidance"),
    "official_recognition_date": ("individual_decision", "individual_institutional_decision"),
    "economic_effective_date": ("economic_effective_basis", "individual_institutional_decision"),
    "first_cash_payment_date": ("cash_availability_confirmation", "individual_payment_evidence"),
}


class PensionTimelineWizardError(ValueError):
    pass


def _text(label: str, default: str = "") -> str:
    value = input(f"{label}" + (f" [{default}]" if default else "") + ": ").strip()
    return value or default


def _date_value(value: str) -> str:
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError
    except (TypeError, ValueError) as exc:
        raise PensionTimelineWizardError("Inserisci una data YYYY-MM-DD verificabile.") from exc
    return value


def _within(root: Path, path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise PensionTimelineWizardError("Il percorso deve restare nel workspace privato.")
    return resolved


def _ref(root: Path, raw: str) -> str:
    relative = raw.removeprefix("workspace-ref:")
    path = _within(root, root / relative)
    if not path.is_file():
        raise PensionTimelineWizardError("La fonte selezionata deve essere un file del workspace.")
    return "workspace-ref:" + path.relative_to(root.resolve()).as_posix()


def _write(root: Path, path: Path, value: dict[str, Any]) -> None:
    target = _within(root, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + "." + uuid.uuid4().hex + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)


def _proof(root: Path, *, event: str, event_date: str, as_of: str,
           jurisdiction: str, role: str, authority: str) -> dict[str, Any] | None:
    print(f"Fonte per {role}; ruolo dichiarato: {authority}. Se non verificabile, lascia vuoto: restera' un gap.")
    raw = _text("Percorso relativo della fonte")
    if not raw:
        return None
    ref = _ref(root, raw)
    payload = _within(root, root / ref.removeprefix("workspace-ref:")).read_bytes()
    act = _text("Identificativo dell'atto/documento")
    article = _text("Articolo o riferimento puntuale alla prova")
    version = _text("Versione esatta della fonte")
    retrieved = _text("Data di acquisizione YYYY-MM-DD")
    reviewed = _text("Data di verifica esterna YYYY-MM-DD")
    start = _text("Inizio applicabilita' YYYY-MM-DD")
    end = _text("Fine ESCLUSA YYYY-MM-DD, oppure APERTA se esplicitamente senza termine")
    if not all((act, article, version, retrieved, reviewed, start, end)):
        return None
    for value in (retrieved, reviewed, start):
        _date_value(value)
    until = None if end.upper() == "APERTA" else _date_value(end)
    if _text("Fonte, ruolo e copertura di evento e data del rapporto sono stati verificati esternamente? Scrivi CONFERMO").upper() != "CONFERMO":
        return None
    return {
        "evidence_ref": event + ":" + hashlib.sha256(payload).hexdigest()[:16],
        "evidence_role": role,
        "source_provenance": {
            "source_ref": ref, "digest_sha256": hashlib.sha256(payload).hexdigest(),
            "source_authority": authority, "jurisdiction": jurisdiction,
            "act_identifier": act, "article_identifier": article, "source_version": version,
            "legal_applicability": {"valid_from": start, "valid_to": until, "validity_status": "bounded"},
            "coverage_assessment": {"coverage_status": "covered", "event_date": event_date,
                "event_date_coverage_status": "covered", "as_of_date": as_of,
                "as_of_date_coverage_status": "covered", "assessed_on": reviewed, "data_gaps": []},
            "retrieved_on": retrieved, "reviewed_on": reviewed,
        },
    }


def _observed_binding(root: Path, request: dict[str, Any], stream: dict[str, Any], event: str) -> str | None:
    raw_date = _text(EVENT_LABELS[event] + " YYYY-MM-DD (vuoto se sconosciuta)")
    if not raw_date:
        return None
    observed = _date_value(raw_date)
    if observed > request["as_of_date"]:
        raise PensionTimelineWizardError("Una data futura resta proiezione, non fatto amministrativo osservato.")
    role, authority = ROLES[event]
    proof = _proof(root, event=event, event_date=observed, as_of=request["as_of_date"],
                   jurisdiction=stream["jurisdiction"], role=role, authority=authority)
    if proof is None:
        return None
    transition_status = _text(
        f"Stato transitorio accertato esternamente per {stream['member_id']}/{stream['jurisdiction']}/{stream['stream_id']}/{event}: applicable / not_applicable / unknown",
        "unknown",
    ).lower()
    if transition_status not in {"applicable", "not_applicable", "unknown"}:
        raise PensionTimelineWizardError("Lo stato transitorio deve essere applicable, not_applicable o unknown.")
    if transition_status == "unknown":
        proof["transition_scope"] = {"status": "unknown", "scope_evidence": [], "data_gaps": [
            {"code": "transitional_branch_unknown", "message": "Applicabilita' transitoria non accertata esternamente per la persona/prestazione/evento.", "severity": "blocking"}]}
    else:
        print("La copertura transitoria richiede una propria fonte primaria o atto attuativo verificato.")
        scope = _proof(root, event=event, event_date=observed, as_of=request["as_of_date"],
                       jurisdiction=stream["jurisdiction"], role="transition_scope", authority="primary_legislation")
        if scope is None:
            return None
        proof["transition_scope"] = {
            "status": transition_status, "scope_evidence": [{"source_provenance": scope["source_provenance"],
            "scope": {"scope_status": "resolved", "applies_to_event": event, "transition_status": transition_status}}],
        }
    proofs = [proof]
    individual = proof
    if event in {"eligibility_date", "requirements_met_date"}:
        print("La fonte generale non prova la situazione individuale: serve anche la decisione attestata per questa persona/prestazione.")
        individual = _proof(root, event=event, event_date=observed, as_of=request["as_of_date"],
                            jurisdiction=stream["jurisdiction"], role="individual_decision", authority="individual_institutional_decision")
        if individual is None:
            return None
        individual["transition_scope"] = deepcopy(proof["transition_scope"])
        proofs.append(individual)
    verifier = _text("Riferimento alla verifica esterna di persona, prestazione, evento e fonte")
    if not verifier or _text("La verifica esterna lega questa prova ESATTAMENTE alla persona/prestazione selezionata? Scrivi CONFERMO").upper() != "CONFERMO":
        return None
    binding = {
        "household_id": request["household_id"], "member_id": stream["member_id"],
        "jurisdiction": stream["jurisdiction"], "stream_id": stream["stream_id"],
        "event_kind": event, "date": observed,
        "verification": {"status": "externally_verified", "verified_on": individual["source_provenance"]["reviewed_on"],
            "verifier_ref": verifier, "source_ref": individual["source_provenance"]["source_ref"],
            "digest_sha256": individual["source_provenance"]["digest_sha256"]},
        "evidence": proofs,
    }
    if event == "economic_effective_date":
        retroactivity = _text("Retroattivita' verificata: not_retroactive / unknown", "unknown")
        if retroactivity != "not_retroactive":
            print("Retroattivita' da verificare: evento lasciato sconosciuto; nessuna base inventata.")
            return None
        binding["retroactivity_status"] = "not_retroactive"
    destination = root / "planning/pension-event-bindings" / (uuid.uuid4().hex + ".json")
    _write(root, destination, binding)
    return "workspace-ref:" + destination.relative_to(root).as_posix()


def prepare_pension_timeline_request(input_path: Path, *, workspace_root: Path, revise: bool = False) -> dict[str, Any]:
    root = workspace_root.resolve()
    target = _within(root, input_path)
    existing = None
    if target.exists() and not revise:
        value = json.loads(target.read_text(encoding="utf-8"))
        print("Riprendo gli input locali salvati; usa --revise per integrare nuove evidenze.")
        return value
    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(existing, dict) or existing.get("schema_version") != "pension-timeline-integration-input/v1":
            raise PensionTimelineWizardError("Il file esistente non e' un input di integrazione: non verra' sovrascritto.")
    print("Domanda familiare: quali pensioni sono documentate e quali restano ipotesi negli scenari di lavoro?")
    print("Le attestazioni sono dichiarazioni esterne: il motore verifica legami, byte e copertura, non autentica un ente.")
    if existing is not None:
        request = deepcopy(existing)
        household, as_of, members = request["household_id"], request["as_of_date"], request["household_members"]
        print("Conservo nucleo, data e prestazioni esistenti; le nuove evidenze vengono aggiunte senza cancellare quelle salvate.")
    else:
        household = _text("Etichetta locale del nucleo", "household_private")
        as_of = _date_value(_text("Data del rapporto YYYY-MM-DD", date.today().isoformat()))
        members = [part.strip() for part in _text("Etichette dei membri separate da virgola", "primary,spouse").split(",") if part.strip()]
        if not members or len(set(members)) != len(members):
            raise PensionTimelineWizardError("Occorrono etichette uniche per i membri.")
        request = {"schema_version": "pension-timeline-integration-input/v1", "household_id": household,
                   "as_of_date": as_of, "household_members": members, "streams": []}
        _write(root, target, request)
    while _text("Aggiungere una prestazione? s/n", "n").lower() == "s":
        member = _text("Membro cui appartiene la prestazione", members[0])
        country = _text("Paese della prestazione IT/ES", "IT").upper()
        stream_id = _text("Identificativo locale della prestazione", "pension_" + country.lower())
        if member not in members or country not in {"IT", "ES"} or not stream_id:
            raise PensionTimelineWizardError("Persona o Paese non corrispondono al nucleo dichiarato.")
        matching = [index for index, item in enumerate(request["streams"]) if
                    (item["member_id"], item["jurisdiction"], item["stream_id"]) == (member, country, stream_id)]
        stream = (deepcopy(request["streams"][matching[0]]) if matching else
                  {"member_id": member, "jurisdiction": country, "stream_id": stream_id, "observed_event_refs": []})
        if country == "IT":
            source = _text("Input di scenario INPS gia' preparato (percorso relativo; vuoto se manca)")
            if source:
                candidate = _date_value(_text("Giorno candidato dello SCENARIO YYYY-MM-DD; non e' una data di diritto"))
                stream["inps"] = {**stream.get("inps", {}), "rule_pack": "inps-theoretical-pension.json", "work_exit_input_ref": _ref(root, source), "candidate_date": candidate}
                if _text("Dichiarare basi imponibili annue diverse per le fasi di lavoro? s/n", "n").lower() == "s":
                    source_path = _within(root, root / stream["inps"]["work_exit_input_ref"].removeprefix("workspace-ref:"))
                    scenario = json.loads(source_path.read_text(encoding="utf-8"))
                    adults = [adult for adult in scenario.get("adults", []) if adult.get("person_id") == member]
                    if scenario.get("household_id") != household or len(adults) != 1:
                        raise PensionTimelineWizardError("Lo scenario deve corrispondere al nucleo e a una sola persona selezionata.")
                    schedule = {}
                    print("Le basi sono ipotesi lorde dichiarate: il motore non le ricava dall'FTE. Copri ogni anno fino al giorno candidato.")
                    while True:
                        year = _text("Anno YYYY (vuoto per terminare)")
                        if not year:
                            break
                        if len(year) != 4 or not year.isdigit() or year in schedule:
                            raise PensionTimelineWizardError("Gli anni della proiezione devono essere unici, nel formato YYYY.")
                        amount = _text("Base imponibile annua dichiarata EUR, anche 0 per cessazione")
                        try:
                            number = Decimal(amount)
                            if not number.is_finite() or number < 0:
                                raise InvalidOperation
                        except InvalidOperation as exc:
                            raise PensionTimelineWizardError("Occorre un importo finito non negativo.") from exc
                        schedule[year] = str(number)
                    estimate = adults[0].get("inps_contributory_estimate")
                    if not isinstance(estimate, dict):
                        raise PensionTimelineWizardError("Manca il contratto di stima contributiva nello scenario.")
                    future = estimate.setdefault("future_contributions", {})
                    future.pop("annual_taxable_income", None)
                    future.pop("through_year", None)
                    future["annual_taxable_income_by_year"] = schedule
                    prepared = root / "planning/pension-scenario-inputs" / (uuid.uuid4().hex + ".json")
                    _write(root, prepared, scenario)
                    stream["inps"]["work_exit_input_ref"] = "workspace-ref:" + prepared.relative_to(root).as_posix()
                benchmark = _text("Benchmark documentale INPS importato (percorso relativo; vuoto se manca)")
                if benchmark:
                    stream["inps"]["documentary_ref"] = _ref(root, benchmark)
        else:
            source = _text("Input spagnolo/UE gia' preparato (percorso relativo; vuoto se manca)")
            if source:
                reconciliation = _text("Riconciliazione contributiva spagnola importata (percorso relativo)")
                if reconciliation:
                    stream["spanish"] = {"theoretical_rule_pack": "spanish-eu-theoretical-pension.json",
                        "pro_rata_rule_pack": "eu-pension-coordination-it-es-v8.json",
                        "pro_rata_input_ref": _ref(root, source), "reconciliation_ref": _ref(root, reconciliation)}
                    if _text("Le due fonti di scenario appartengono a questa persona/prestazione? Scrivi CONFERMO; altrimenti gli importi resteranno sconosciuti").upper() == "CONFERMO":
                        identity = {"household_id": household, "member_id": member, "jurisdiction": country, "stream_id": stream_id}
                        for field in ("pro_rata_input_ref", "reconciliation_ref"):
                            original_ref = stream["spanish"][field]
                            original_path = _within(root, root / original_ref.removeprefix("workspace-ref:"))
                            payload = original_path.read_bytes()
                            bound = json.loads(payload.decode("utf-8"))
                            if not isinstance(bound, dict) or any(key in bound and bound[key] != value for key, value in identity.items()):
                                raise PensionTimelineWizardError("La fonte dichiara una persona/prestazione differente: non verra' riassegnata.")
                            bound.update(identity)
                            bound["source_binding"] = {"status": "operator_confirmed_scenario_subject", "source_ref": original_ref, "digest_sha256": hashlib.sha256(payload).hexdigest()}
                            prepared = root / "planning/pension-scenario-inputs" / (uuid.uuid4().hex + ".json")
                            _write(root, prepared, bound)
                            stream["spanish"][field] = "workspace-ref:" + prepared.relative_to(root).as_posix()
        if _text("Importare eventi amministrativi gia' verificati esternamente? s/n", "n").lower() == "s":
            for event in EVENT_LABELS:
                ref = _observed_binding(root, request, stream, event)
                if ref:
                    stream["observed_event_refs"].append(ref)
        if matching:
            request["streams"][matching[0]] = stream
        else:
            request["streams"].append(stream)
        _write(root, target, request)
    return request


def render_pension_timeline_report(report: dict[str, Any]) -> None:
    print("Domanda familiare: quali eventi pensionistici sono documentati e quali restano ipotesi?")
    print("Fatti: le date supportate conservano l'attestazione esterna e le fonti della singola persona/prestazione; il motore non autentica un ente.")
    for stream in report.get("streams", []):
        print(f"Prestazione {stream['member_id']}/{stream['jurisdiction']}/{stream['stream_id']}:")
        for name, event in stream.get("timeline_v2", {}).get("events", {}).items():
            print(f"  {EVENT_LABELS.get(name, name)}: {event['date'] if event.get('date') else 'sconosciuta'} ({event['status']})")
        projection = stream.get("scenario_projection", {})
        for name in ("inps", "spanish_theoretical", "spanish_pro_rata"):
            item = projection.get(name)
            if item is not None:
                print(f"  Scenario {name}: {item.get('status', 'partial')}; scenario_projection, mai diritto verificato.")
        if stream.get("documentary_benchmark") is not None:
            print("  Benchmark documentale INPS: separato dalla stima di scenario; non ricalcolato.")
    gaps = report.get("data_gaps", [])
    codes = sorted({str(gap.get("code", "unknown")) for gap in gaps})
    print("Assunzioni: basi contributive e giorni candidati sono dichiarati; nessuna data di diritto e' ricavata da cessazione o FTE.")
    print("Data gaps: " + (", ".join(codes) if codes else "nessuno dichiarato nel perimetro eseguito."))
    print("Limiti: copertura delle versioni e delle fonti esplicita; importi e date non supportati restano nulli. Revisione umana richiesta.")
    print("Prossima azione: completa le prove mancanti della singola prestazione e verifica separatamente le ipotesi di scenario.")
