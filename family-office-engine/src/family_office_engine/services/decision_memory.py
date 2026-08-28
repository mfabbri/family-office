"""Private, append-only V5.10 decision memory with validated lineage only."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any

INPUT_SCHEMA_VERSION="decision-memory-input/v1"; SCHEMA_VERSION="decision-memory/v1"
class DecisionMemoryError(ValueError): pass

def update_decision_memory(input_path: Path, memory_path: Path) -> dict[str, Any]:
    try: data=json.loads(input_path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc: raise DecisionMemoryError("Cannot read decision memory input") from exc
    existing=_read_memory(memory_path)
    snapshot=apply_decision_memory(data, existing)
    try:
        memory_path.parent.mkdir(parents=True,exist_ok=True); memory_path.write_text(json.dumps(snapshot,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    except OSError as exc: raise DecisionMemoryError(f"Cannot write decision memory: {memory_path}") from exc
    return snapshot

def apply_decision_memory(data: dict[str,Any], existing: dict[str,Any]|None=None)->dict[str,Any]:
    if not isinstance(data,dict) or data.get("schema_version")!=INPUT_SCHEMA_VERSION or data.get("record_type")!="DecisionMemoryInput": raise DecisionMemoryError(f"input must be {INPUT_SCHEMA_VERSION}")
    if {"conversation_text","facts","raw_request"}&set(data): raise DecisionMemoryError("conversation text and raw facts are not allowed in decision memory")
    key=_text(data,"decision_key"); action=_text(data,"action")
    if action not in {"record","revoke"}: raise DecisionMemoryError("action must be record or revoke")
    previous=(existing or {}).get("entries",[]); active=[e for e in previous if e["decision_key"]==key and e["state"]=="active"]
    expected=data.get("expected_current_version")
    current=max(active,key=lambda e:e["version"],default=None)
    if expected is not None and (not isinstance(expected,int) or (current or {}).get("version")!=expected):
        return _snapshot(previous,"conflict",{"code":"version_conflict","decision_key":key,"expected":expected,"actual":None if current is None else current["version"]})
    entries=[dict(e) for e in previous]
    if action=="record":
        lineage=_lineage(data.get("validated_lineage")); version=1+max((e["version"] for e in entries if e["decision_key"]==key),default=0)
        if current: current_entry=next(e for e in entries if e["entry_id"]==current["entry_id"]); current_entry["state"]="superseded"; current_entry["superseded_by"]=version
        entries.append({"entry_id":f"{key}:v{version}","decision_key":key,"version":version,"state":"active","validated_lineage":lineage,"note":"validated_reference_only"})
    else:
        if not current: return _snapshot(entries,"conflict",{"code":"no_active_decision","decision_key":key})
        next(e for e in entries if e["entry_id"]==current["entry_id"])["state"]="revoked"
    return _snapshot(entries,"complete",None)

def _lineage(value:Any)->dict[str,dict[str,str]]:
    required={"scenario","evidence_bundle","advisory_response","answer_confidence"}
    if not isinstance(value,dict) or set(value)!=required: raise DecisionMemoryError("validated_lineage must contain exactly scenario, evidence_bundle, advisory_response and answer_confidence")
    result={}
    for name,item in value.items():
        if not isinstance(item,dict) or not isinstance(item.get("schema_version"),str) or not _hash_ok(item.get("content_hash")): raise DecisionMemoryError(f"validated_lineage.{name} requires schema_version and content_hash")
        result[name]={"schema_version":item["schema_version"],"content_hash":item["content_hash"]}
    return result

def _read_memory(path:Path)->dict[str,Any]|None:
    if not path.exists(): return None
    try: data=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc: raise DecisionMemoryError("Cannot read existing decision memory") from exc
    if data.get("schema_version")!=SCHEMA_VERSION or not isinstance(data.get("entries"),list): raise DecisionMemoryError("existing memory is not decision-memory/v1")
    return data

def _snapshot(entries:list[dict[str,Any]],status:str,conflict:dict[str,Any]|None)->dict[str,Any]:
    core={"entries":entries,"conflicts":[] if conflict is None else [conflict],"policy":{"workspace_private_only":True,"conversation_text_persisted":False,"raw_facts_persisted":False,"validated_lineage_required":True}}
    return {"schema_version":SCHEMA_VERSION,"record_type":"DecisionMemory","status":status,**core,"reproducibility":{"hash_algorithm":"sha256","content_hash":_hash(core)}}
def _text(data:dict[str,Any],field:str)->str:
    v=data.get(field)
    if not isinstance(v,str) or not v.strip(): raise DecisionMemoryError(f"{field} must be a non-empty string")
    return v.strip()
def _hash_ok(v:Any)->bool:return isinstance(v,str) and len(v)==64 and all(c in "0123456789abcdef" for c in v)
def _hash(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()
