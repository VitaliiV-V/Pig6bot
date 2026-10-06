"""Public policy page; editors change only security-policy.txt."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from config.security_policy import SECURITY_POLICY_URL, security_policy_text

router = APIRouter()
templates = Environment(
    loader=FileSystemLoader(Path(__file__).resolve().parent),
    autoescape=select_autoescape(["html"]),
)


@router.get("/security-policy", response_class=HTMLResponse)
def security_policy():
    return HTMLResponse(
        templates.get_template("security-policy.html").render(
            policy_text=security_policy_text(), canonical_url=SECURITY_POLICY_URL,
        ),
        headers={"Cache-Control": "no-cache"},
    )
