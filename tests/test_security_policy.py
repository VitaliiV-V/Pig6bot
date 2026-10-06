import tempfile
import unittest
import importlib.util
import os
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from config import security_policy as content
from web.policy import router


class SecurityPolicyTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_article_contains_policy_and_canonical_link(self):
        response = self.client.get("/security-policy")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn(content.SECURITY_POLICY_URL, response.text)
        self.assertIn("ПОДТВЕРЖДЕНИЯ ПОЛЬЗОВАТЕЛЯ", response.text)
        self.assertIn("административных прав", response.text)
        self.assertIn("Добровольный возврат платежей", response.text)
        self.assertEqual(response.headers["cache-control"], "no-cache")

    def test_config_uses_environment_for_local_and_public_policy_links(self):
        for base, expected in (
            ("http://127.0.0.1:2322", "http://127.0.0.1:2322/security-policy"),
            ("http://127.0.0.1:8080/", "http://127.0.0.1:8080/security-policy"),
            (" https://pig6bot.sos.al/ ", "https://pig6bot.sos.al/security-policy"),
            ("", "http://127.0.0.1:2322/security-policy"),
        ):
            with self.subTest(base=base):
                spec = importlib.util.spec_from_file_location("test_policy_config", content.__file__)
                module = importlib.util.module_from_spec(spec)
                with patch.dict(os.environ, {"WEB_SITE": base}), patch("dotenv.load_dotenv"):
                    spec.loader.exec_module(module)
                self.assertEqual(module.SECURITY_POLICY_URL, expected)

    def test_plain_text_edits_are_live_escaped_and_fingerprinted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.txt"
            path.write_text("Первая редакция\n\nПравила канала.", encoding="utf-8")
            with patch.object(content, "SECURITY_POLICY_FILE", path):
                previous_hash = content.security_policy_fingerprint()
                response = self.client.get("/security-policy")
                self.assertIn("Первая редакция\n\nПравила канала.", response.text)
                path.write_text("Новая редакция\n\n<script>alert('x')</script>", encoding="utf-8")
                response = self.client.get("/security-policy")
                self.assertIn("Новая редакция", response.text)
                self.assertNotIn("Первая редакция", response.text)
                self.assertNotIn("<script>", response.text)
                self.assertIn("&lt;script&gt;", response.text)
                self.assertNotEqual(content.security_policy_fingerprint(), previous_hash)


if __name__ == "__main__":
    unittest.main()
