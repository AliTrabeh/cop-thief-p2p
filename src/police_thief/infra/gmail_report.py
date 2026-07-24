"""Gmail API reporting automation (FR-080..082, Appendix A): OAuth2,
send-only scope, Gatekeeper-guarded (NFR-006).

In ``draft`` mode (this project's default per docs/assumptions.md, so no
test or local demo run ever touches a real mailbox or spends Gmail API
quota) the report is written to disk instead of sent. ``send`` mode is only
exercised manually against a real Google account.
"""

from __future__ import annotations

import base64
import json
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Protocol

from police_thief.infra.gatekeeper import Gatekeeper, GatekeeperVerdict

GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"


class GmailSendError(Exception):
    """Raised when a real send is attempted but rejected or fails."""


class GmailServiceLike(Protocol):
    """The narrow slice of a Gmail API service object this module needs, so
    tests can inject a fake without any real OAuth credentials.
    """

    def users(self) -> Any: ...


def build_mime_message(to_addr: str, subject: str, body: str) -> str:
    """Base64url-encoded raw MIME message, ready for ``users().messages().send``."""
    message = MIMEText(body)
    message["to"] = to_addr
    message["subject"] = subject
    return base64.urlsafe_b64encode(message.as_bytes()).decode()


def get_gmail_service(token_path: Path = Path("token.json")) -> Any:
    """Least-privilege (``gmail.send`` only) OAuth2 flow (Appendix A §2-3).

    Imports the Google client libraries lazily so the rest of the project
    never needs them importable just to run offline/draft-mode tests.
    """
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file(  # type: ignore[no-untyped-call]
        str(token_path), [GMAIL_SEND_SCOPE]
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("gmail", "v1", credentials=creds)


def send_report(service: GmailServiceLike, to_addr: str, subject: str, body: str) -> dict[str, Any]:
    raw = build_mime_message(to_addr, subject, body)
    result: dict[str, Any] = (
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
    )
    return result


def report_match_result(
    *,
    mode: str,
    recipient: str,
    result_json: dict[str, Any],
    gatekeeper: Gatekeeper,
    output_dir: Path,
    game_id: str,
    token_path: Path = Path("token.json"),
    service: GmailServiceLike | None = None,
) -> str:
    """Send (or draft) the end-of-match JSON report (FR-081).

    ``service`` may be injected (tests, or a pre-built client); otherwise a
    real one is constructed via :func:`get_gmail_service` only when
    ``mode == "send"``, so draft-mode callers never need Google credentials
    on disk at all.
    """
    body = json.dumps(result_json, indent=2, sort_keys=True)
    subject = f"[police-thief] match result: {game_id}"

    if mode != "send":
        output_dir.mkdir(parents=True, exist_ok=True)
        draft_path = output_dir / f"result_{game_id}.emaildraft.json"
        draft_path.write_text(body, encoding="utf-8")
        return f"draft written to {draft_path} (mode={mode!r}, no Gmail API call made)"

    verdict = gatekeeper.admit()
    if verdict is not GatekeeperVerdict.ALLOWED:
        raise GmailSendError(f"Gatekeeper blocked the send: {verdict.value}")

    svc = service if service is not None else get_gmail_service(token_path)
    send_report(svc, recipient, subject, body)
    return f"sent to {recipient}"
