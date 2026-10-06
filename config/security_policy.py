"""Shared location and fingerprint of the editable channel security policy."""

import hashlib
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

WEB_SITE = (os.getenv("WEB_SITE") or "").strip() or "http://127.0.0.1:2322"
SECURITY_POLICY_URL = WEB_SITE.rstrip("/") + "/security-policy"
SECURITY_POLICY_FILE = Path(__file__).resolve().parent.parent / "web" / "security-policy.txt"


def security_policy_text():
    return SECURITY_POLICY_FILE.read_text(encoding="utf-8")


def security_policy_fingerprint():
    return hashlib.sha256(SECURITY_POLICY_FILE.read_bytes()).hexdigest()
