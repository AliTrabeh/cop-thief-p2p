"""One-time OAuth2 bootstrap for Gmail sending (Appendix A, Step 5: First
Authorization Flow). Run this once, manually, after downloading
``credentials.json`` from Google Cloud Console into the project root.

Opens a real browser for interactive Google login/consent, then writes
``token.json`` (access + refresh token) next to it. Every later real send
(``infra/gmail_report.py::get_gmail_service``) reuses ``token.json`` and
never needs this script again unless the refresh token is revoked.

Usage:
    uv run python scripts/setup_gmail_oauth.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

from police_thief.infra.gmail_report import GMAIL_SEND_SCOPE

CREDENTIALS_PATH = Path("credentials.json")
TOKEN_PATH = Path("token.json")


def main() -> int:
    if not CREDENTIALS_PATH.exists():
        print(
            f"error: {CREDENTIALS_PATH} not found. Download it from Google Cloud Console "
            "(APIs & Services -> Credentials -> your Desktop-app OAuth Client ID) and place "
            "it in the project root first.",
            file=sys.stderr,
        )
        return 1
    if TOKEN_PATH.exists():
        print(f"note: {TOKEN_PATH} already exists; re-running will overwrite it.")

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), [GMAIL_SEND_SCOPE])
    creds = flow.run_local_server(port=0)
    TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    print(f"success: wrote {TOKEN_PATH}. Real Gmail sends will now work via get_gmail_service().")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
