"""Gmail API client — data layer only, no HTTP concerns."""

import base64
import logging
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
TOKEN_PATH = Path(__file__).parent / "token.json"
CREDENTIALS_PATH = Path(__file__).parent / "credentials.json"

logger = logging.getLogger(__name__)


def get_credentials() -> Credentials:
    """Load cached credentials or run OAuth flow to get new ones."""
    creds: Credentials | None = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_PATH.exists():
                raise FileNotFoundError(
                    f"credentials.json not found at {CREDENTIALS_PATH}. "
                    "Download it from Google Cloud Console → APIs & Services → Credentials."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)

        TOKEN_PATH.write_text(creds.to_json())
        logger.info("Saved OAuth token to %s", TOKEN_PATH)

    return creds


def _build_service():
    """Build and return an authenticated Gmail API service object."""
    return build("gmail", "v1", credentials=get_credentials())


# ---------------------------------------------------------------------------
# Label helpers
# ---------------------------------------------------------------------------

def fetch_labels() -> list[dict[str, str]]:
    """Return all user-created Gmail labels as [{id, name}]."""
    result = _build_service().users().labels().list(userId="me").execute()
    return [
        {"id": lbl["id"], "name": lbl["name"]}
        for lbl in result.get("labels", [])
        if lbl.get("type") == "user"
    ]


# ---------------------------------------------------------------------------
# Email helpers
# ---------------------------------------------------------------------------

def _decode_b64(data: str) -> str:
    """Decode a base64url-encoded Gmail body string."""
    # Gmail uses base64url without padding; add padding before decoding.
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

        # First pass — prefer plain text
        for part in parts:
            if part.get("mimeType") == "text/plain":
                raw = part.get("body", {}).get("data", "")
                if raw:
                    return _decode_b64(raw), False

        # Second pass — accept HTML, recurse into nested multipart
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
    """Pull From / Subject / Date from the raw header list."""
    return {
        h["name"].lower(): h["value"]
        for h in headers
        if h["name"].lower() in {"from", "subject", "date"}
    }


def fetch_next_untagged_email() -> dict[str, Any] | None:
    """Return the oldest unarchived inbox email with no user labels, or None."""
    service = _build_service()

    page = service.users().messages().list(
        userId="me",
        q="in:inbox -has:userlabels",
        maxResults=1,
    ).execute()

    messages = page.get("messages", [])
    if not messages:
        return None

    msg_id = messages[0]["id"]
    message = service.users().messages().get(
        userId="me",
        id=msg_id,
        format="full",
    ).execute()

    payload = message.get("payload", {})
    headers = _parse_headers(payload.get("headers", []))
    body, is_html = _extract_body(payload)

    return {
        "id": msg_id,
        "from": headers.get("from", ""),
        "subject": headers.get("subject", "(no subject)"),
        "date": headers.get("date", ""),
        "snippet": message.get("snippet", ""),
        "body": body or message.get("snippet", ""),
        "is_html": is_html,
    }


def apply_label_and_archive(email_id: str, label_id: str) -> None:
    """Add a user label to an email and remove it from the inbox."""
    _build_service().users().messages().modify(
        userId="me",
        id=email_id,
        body={
            "addLabelIds": [label_id],
            "removeLabelIds": ["INBOX"],
        },
    ).execute()
    logger.info("Email %s → label %s, archived", email_id, label_id)
