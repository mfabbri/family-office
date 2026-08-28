import hashlib
import json
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from family_office_engine.cli.main import main
from family_office_engine.services.execution_plan import demo_execution_plan_input
from family_office_engine.services.local_conversation_api import API_PREFIX, create_local_conversation_server


class LocalConversationApiTest(unittest.TestCase):
    token = "synthetic-local-api-token"

    def setUp(self):
        self.server = create_local_conversation_server(self.token, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()

    def test_authentication_and_loopback_only_binding(self):
        with self.assertRaises(HTTPError) as caught:
            self._request("POST", API_PREFIX, {"question_fingerprint": self._fingerprint("question")}, token=None)
        self.assertEqual(401, caught.exception.code)

        stdout = StringIO()
        with redirect_stdout(stdout):
            exit_code = main(["orchestration", "local-api", "serve", "--token", self.token, "--host", "0.0.0.0"])
        self.assertEqual(1, exit_code)
        self.assertIn("loopback host", stdout.getvalue())

    def test_sessions_are_isolated_and_preview_never_executes(self):
        with ThreadPoolExecutor(max_workers=2) as workers:
            sessions = list(workers.map(lambda number: self._create(f"question {number}"), range(2)))
        self.assertNotEqual(sessions[0]["session_id"], sessions[1]["session_id"])
        self.assertEqual("active", sessions[0]["status"])

        preview = self._request("POST", f"{API_PREFIX}/{sessions[0]['session_id']}/plan-preview", demo_execution_plan_input())
        self.assertEqual("previewed", preview["status"])
        self.assertTrue(preview["plan_preview"]["all_nodes_not_executed"])
        self.assertEqual(["retirement_and_work_exit"], preview["route"]["selected_intent_ids"])

        other = self._request("GET", f"{API_PREFIX}/{sessions[1]['session_id']}")
        self.assertEqual("active", other["status"])
        self.assertIsNone(other["plan_preview"])

        approved = self._request("POST", f"{API_PREFIX}/{sessions[0]['session_id']}/approve", {})
        self.assertEqual("approved_preview_only", approved["approval"])
        self.assertEqual("approved", approved["status"])
        audit = self._request("GET", f"{API_PREFIX}/{sessions[0]['session_id']}/audit")
        self.assertEqual(["session_created", "plan_previewed", "preview_approved"], [item["event"] for item in audit["audit"]])

    def test_cancel_is_reproducible_and_client_does_not_receive_server_token(self):
        session = self._create("cancel question")
        cancelled = self._request("POST", f"{API_PREFIX}/{session['session_id']}/cancel", {})
        self.assertEqual("cancelled", cancelled["status"])
        repeat = self._request("POST", f"{API_PREFIX}/{session['session_id']}/cancel", {})
        self.assertEqual(cancelled, repeat)
        with self.assertRaises(HTTPError) as caught:
            self._request("POST", f"{API_PREFIX}/{session['session_id']}/plan-preview", demo_execution_plan_input())
        self.assertEqual(400, caught.exception.code)

        client = urlopen(f"{self.base_url}/").read().decode("utf-8")
        self.assertIn("crypto.subtle.digest", client)
        self.assertNotIn(self.token, client)
        self.assertNotIn("localStorage", client)

    def _create(self, question: str):
        return self._request("POST", API_PREFIX, {"question_fingerprint": self._fingerprint(question)})

    def _request(self, method: str, path: str, value=None, token: str | None = token):
        data = None if value is None else json.dumps(value).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        request = Request(f"{self.base_url}{path}", data=data, headers=headers, method=method)
        with urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _fingerprint(question: str) -> str:
        return hashlib.sha256(question.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    unittest.main()
