"""Gmail API client — data layer only, no HTTP concerns.

Supports multiple authenticated accounts. Each account's OAuth token is stored
as token_{email}.json in the same directory as this file.
"""

import base64
import logging
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
TOKEN_DIR = Path(__file__).parent
CREDENTIALS_PATH = TOKEN_DIR / "credentials.json"

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _token_path(email: str) -> Path:
    return TOKEN_DIR / f"token_{email}.json"


def _load_creds(email: str) -> Credentials:
    """Load and auto-refresh credentials for a given account."""
    path = _token_path(email)
    creds = Credentials.from_authorized_user_file(str(path), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        path.write_text(creds.to_json())
    return creds


def _service(email: str):
    """Return an authenticated Gmail API service for the given account."""
    return build("gmail", "v1", credentials=_load_creds(email))


def list_accounts() -> list[str]:
    """Return email addresses of all authenticated accounts (from token files)."""
    accounts = []
    for token_file in sorted(TOKEN_DIR.glob("token_*.json")):
        email = token_file.stem[len("token_"):]
        accounts.append(email)
    return accounts


def authenticate_new_account() -> str:
    """Run the OAuth browser flow for a new account and persist the token.

    Blocking — must be called from a thread, not the async event loop.
    Returns the authenticated email address.
    """
    if not CREDENTIALS_PATH.exists():
        raise FileNotFoundError(
            f"credentials.json not found at {CREDENTIALS_PATH}. "
            "Download it from Google Cloud Console → APIs & Services → Credentials."
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
    creds = flow.run_local_server(port=0)

    svc = build("gmail", "v1", credentials=creds)
    profile = svc.users().getProfile(userId="me").execute()
    email: str = profile["emailAddress"]

    _token_path(email).write_text(creds.to_json())
    logger.info("Authenticated new account: %s", email)
    return email


# ---------------------------------------------------------------------------
# Label helpers
# ---------------------------------------------------------------------------

def fetch_labels(account: str) -> list[dict[str, str]]:
    """Return all user-created labels for one account as [{id, name, account}]."""
    result = _service(account).users().labels().list(userId="me").execute()
    return [
        {"id": lbl["id"], "name": lbl["name"], "account": account}
        for lbl in result.get("labels", [])
        if lbl.get("type") == "user"
    ]


def fetch_all_labels() -> list[dict[str, str]]:
    """Merge labels from every authenticated account."""
    merged = []
    for account in list_accounts():
        merged.extend(fetch_labels(account))
    return merged


# ---------------------------------------------------------------------------
# Email helpers
# ---------------------------------------------------------------------------

def _decode_b64(data: str) -> str:
    """Decode a base64url-encoded Gmail body string."""
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")


def _extract_body(payload: dict[str, Any]) -> tuple[str, bool]:
    """Walk the MIME tree and return (content, is_html).

    Prefers text/plain. Falls back to text/html only if no plain part exists.
    """
    mime = payload.get("mimeType", "")
    data = payload.get("body", {}).get("data", "")

    if mime == "text/plain" and data:
        return _decode_b64(data), False

    if mime == "text/html" and data:
        return _decode_b64(data), True

    if mime.startswith("multipart/"):
        parts = payload.get("parts", [])

        for part in parts:
            if part.get("mimeType") == "text/plain":
                raw = part.get("body", {}).get("data", "")
                if raw:
                    return _decode_b64(raw), False

        for part in parts:
            if part.get("mimeType") == "text/html":
                raw = part.get("body", {}).get("data", "")
                if raw:
                    return _decode_b64(raw), True
            if part.get("mimeType", "").startswith("multipart/"):
                content, is_html = _extract_body(part)
                if content:
                    return content, is_html

    return "", False


def _parse_headers(headers: list[dict[str, str]]) -> dict[str, str]:
    return {
        h["name"].lower(): h["value"]
        for h in headers
        if h["name"].lower() in {"from", "subject", "date"}
    }


def _fetch_next_for_account(account: str) -> dict[str, Any] | None:
    """Return the next untagged inbox email for a single account, or None."""
    svc = _service(account)
    page = svc.users().messages().list(
        userId="me",
        q="in:inbox -has:userlabels",
        maxResults=1,
    ).execute()

    messages = page.get("messages", [])
    if not messages:
        return None

    msg_id = messages[0]["id"]
    message = svc.users().messages().get(userId="me", id=msg_id, format="full").execute()

    payload = message.get("payload", {})
    headers = _parse_headers(payload.get("headers", []))
    body, is_html = _extract_body(payload)

    return {
        "id": msg_id,
        "account": account,
        "from": headers.get("from", ""),
        "subject": headers.get("subject", "(no subject)"),
        "date": headers.get("date", ""),
        "snippet": message.get("snippet", ""),
        "body": body or message.get("snippet", ""),
        "is_html": is_html,
    }


def fetch_next_untagged_email() -> dict[str, Any] | None:
    """Return the next untagged inbox email across all authenticated accounts."""
    for account in list_accounts():
        email = _fetch_next_for_account(account)
        if email:
            return email
    return None


def apply_label_and_archive(email_id: str, label_id: str, account: str) -> None:
    """Add a user label to an email and remove it from the inbox."""
    _service(account).users().messages().modify(
        userId="me",
        id=email_id,
        body={
            "addLabelIds": [label_id],
            "removeLabelIds": ["INBOX"],
        },
    ).execute()
    logger.info("Email %s → label %s, archived (%s)", email_id, label_id, account)
