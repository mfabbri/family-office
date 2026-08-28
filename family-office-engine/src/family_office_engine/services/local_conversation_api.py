"""Loopback-only local conversation API for V5.12.

The API owns transient session state only.  It accepts an already routed
``execution-plan-input/v1`` and calls the deterministic planner for a preview;
it deliberately has no executor, composer, or guardrail endpoint.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import threading
from copy import deepcopy
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from family_office_engine.services.execution_plan import ExecutionPlanError, plan_execution

API_SCHEMA_VERSION = "local-conversation-session/v1"
API_PREFIX = "/v1/local-conversation-sessions"


class LocalConversationApiError(ValueError):
    pass


class LocalConversationSessionStore:
    """Thread-safe, in-memory session state with append-only local audit."""

    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    def create(self, question_fingerprint: str) -> dict[str, Any]:
        if not _is_hash(question_fingerprint):
            raise LocalConversationApiError("question_fingerprint must be a SHA-256 hex digest")
        session_id = secrets.token_urlsafe(18)
        session = {
            "schema_version": API_SCHEMA_VERSION,
            "record_type": "LocalConversationSession",
            "session_id": session_id,
            "status": "active",
            "question_fingerprint": question_fingerprint,
            "route": None,
            "plan_preview": None,
            "approval": "not_requested",
            "audit": [],
        }
        with self._lock:
            self._sessions[session_id] = session
            self._append_audit(session, "session_created")
            return _public_session(session)

    def preview_plan(self, session_id: str, plan_input: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            session = self._session(session_id)
            if session["status"] != "active":
                raise LocalConversationApiError("plan preview is available only for an active session")
            try:
                preview = plan_execution(plan_input)
            except ExecutionPlanError as exc:
                self._append_audit(session, "plan_preview_rejected")
                raise LocalConversationApiError(str(exc)) from exc
            session["route"] = {
                "selected_intent_ids": preview["question_intent"]["selected_intent_ids"],
                "question_intent_hash": preview["question_intent"]["content_hash"],
            }
            session["plan_preview"] = {
                "schema_version": preview["schema_version"],
                "content_hash": preview["reproducibility"]["content_hash"],
                "node_count": len(preview["nodes"]),
                "execution_order": preview["execution_order"],
                "all_nodes_not_executed": all(node["execution_state"] == "not_executed" for node in preview["nodes"]),
            }
            session["status"] = "previewed"
            self._append_audit(session, "plan_previewed")
            return _public_session(session)

    def approve(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            session = self._session(session_id)
            if session["status"] != "previewed":
                raise LocalConversationApiError("only a previewed session can be approved")
            session["status"] = "approved"
            session["approval"] = "approved_preview_only"
            self._append_audit(session, "preview_approved")
            return _public_session(session)

    def cancel(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            session = self._session(session_id)
            if session["status"] == "cancelled":
                return _public_session(session)
            if session["status"] == "approved":
                raise LocalConversationApiError("an approved session cannot be cancelled")
            session["status"] = "cancelled"
            session["approval"] = "cancelled"
            self._append_audit(session, "session_cancelled")
            return _public_session(session)

    def get(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            return _public_session(self._session(session_id))

    def audit(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            session = self._session(session_id)
            return {"session_id": session_id, "audit": deepcopy(session["audit"])}

    def _session(self, session_id: str) -> dict[str, Any]:
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise LocalConversationApiError("unknown session") from exc

    @staticmethod
    def _append_audit(session: dict[str, Any], event: str) -> None:
        session["audit"].append({"sequence": len(session["audit"]) + 1, "event": event, "at": datetime.now(timezone.utc).isoformat()})


def create_local_conversation_server(token: str, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    """Create a server bound only to a loopback address."""
    if host not in {"127.0.0.1", "::1", "localhost"}:
        raise LocalConversationApiError("local conversation API must bind to a loopback host")
    if not isinstance(token, str) or len(token) < 16:
        raise LocalConversationApiError("bearer token must contain at least 16 characters")
    server = ThreadingHTTPServer((host, port), _handler_class(token, LocalConversationSessionStore()))
    server.daemon_threads = True
    return server


def serve_local_conversation_api(token: str, host: str = "127.0.0.1", port: int = 8765) -> None:
    server = create_local_conversation_server(token, host, port)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def _handler_class(token: str, store: LocalConversationSessionStore) -> type[BaseHTTPRequestHandler]:
    class LocalConversationHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/":
                self._send(HTTPStatus.OK, _client_html(), "text/html; charset=utf-8")
                return
            if not self._authenticated():
                return
            parts = _path_parts(self.path)
            try:
                if len(parts) == 2 and parts[0] == API_PREFIX:
                    self._send(HTTPStatus.OK, store.get(parts[1]))
                elif len(parts) == 3 and parts[0] == API_PREFIX and parts[2] == "audit":
                    self._send(HTTPStatus.OK, store.audit(parts[1]))
                else:
                    self._error(HTTPStatus.NOT_FOUND, "not_found")
            except LocalConversationApiError as exc:
                self._error(HTTPStatus.NOT_FOUND, str(exc))

        def do_POST(self) -> None:  # noqa: N802
            if not self._authenticated():
                return
            parts = _path_parts(self.path)
            try:
                body = self._json_body()
                if parts == [API_PREFIX]:
                    self._send(HTTPStatus.CREATED, store.create(body.get("question_fingerprint")))
                elif len(parts) == 3 and parts[0] == API_PREFIX and parts[2] == "plan-preview":
                    self._send(HTTPStatus.OK, store.preview_plan(parts[1], body))
                elif len(parts) == 3 and parts[0] == API_PREFIX and parts[2] == "approve":
                    self._send(HTTPStatus.OK, store.approve(parts[1]))
                elif len(parts) == 3 and parts[0] == API_PREFIX and parts[2] == "cancel":
                    self._send(HTTPStatus.OK, store.cancel(parts[1]))
                else:
                    self._error(HTTPStatus.NOT_FOUND, "not_found")
            except LocalConversationApiError as exc:
                self._error(HTTPStatus.BAD_REQUEST, str(exc))

        def _authenticated(self) -> bool:
            expected = f"Bearer {token}"
            if not hmac.compare_digest(self.headers.get("Authorization", ""), expected):
                self._error(HTTPStatus.UNAUTHORIZED, "bearer token required")
                return False
            return True

        def _json_body(self) -> dict[str, Any]:
            try:
                length = int(self.headers.get("Content-Length", "0"))
                value = json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
                raise LocalConversationApiError("request body must be a JSON object") from exc
            if not isinstance(value, dict):
                raise LocalConversationApiError("request body must be a JSON object")
            return value

        def _send(self, status: HTTPStatus, value: Any, content_type: str = "application/json; charset=utf-8") -> None:
            payload = value.encode("utf-8") if isinstance(value, str) else json.dumps(value, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

        def _error(self, status: HTTPStatus, message: str) -> None:
            self._send(status, {"error": message})

        def log_message(self, format: str, *args: Any) -> None:
            return

    return LocalConversationHandler


def _path_parts(path: str) -> list[str]:
    parsed = urlparse(path).path.rstrip("/")
    if not parsed.startswith(API_PREFIX):
        return []
    suffix = parsed[len(API_PREFIX) :].strip("/")
    return [API_PREFIX] + (suffix.split("/") if suffix else [])


def _public_session(session: dict[str, Any]) -> dict[str, Any]:
    return {key: deepcopy(value) for key, value in session.items() if key != "audit"} | {"audit_event_count": len(session["audit"])}


def _is_hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _client_html() -> str:
    return """<!doctype html><meta charset=\"utf-8\"><title>Family Office local conversation</title>
<main><h1>Family Office local conversation</h1><p>This client stores the bearer token only in this browser tab.</p>
<label>Bearer token <input id=token type=password></label><label>Question <input id=question></label><button id=start>Start session</button><button id=cancel disabled>Cancel</button><pre id=status>Not connected.</pre></main>
<script>
let sessionId; const status=document.querySelector('#status');
async function fingerprint(text){const data=new TextEncoder().encode(text); const hash=await crypto.subtle.digest('SHA-256',data); return [...new Uint8Array(hash)].map(b=>b.toString(16).padStart(2,'0')).join('')}
async function request(path, body){const r=await fetch(path,{method:'POST',headers:{'Authorization':'Bearer '+token.value,'Content-Type':'application/json'},body:JSON.stringify(body||{})}); const value=await r.json(); if(!r.ok)throw new Error(value.error); return value}
start.onclick=async()=>{try{const value=await request('""" + API_PREFIX + """',{question_fingerprint:await fingerprint(question.value)}); sessionId=value.session_id; cancel.disabled=false; status.textContent=JSON.stringify(value,null,2)}catch(e){status.textContent=e.message}};
cancel.onclick=async()=>{try{const value=await request('""" + API_PREFIX + """/'+sessionId+'/cancel'); cancel.disabled=true; status.textContent=JSON.stringify(value,null,2)}catch(e){status.textContent=e.message}};
</script>"""
