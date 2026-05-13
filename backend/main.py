"""FastAPI server — HTTP layer only, no Gmail logic here."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import gmail_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    accounts = gmail_client.list_accounts()
    if not accounts:
        logger.info("No accounts found. POST /api/accounts to authenticate your first account.")
    else:
        logger.info("Loaded accounts: %s", accounts)
    yield


app = FastAPI(title="inbox-zera", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ClassifyBody(BaseModel):
    label_id: str
    account: str


def _raise(exc: Exception) -> None:
    raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/accounts")
async def list_accounts() -> list[str]:
    """All authenticated Gmail accounts."""
    return gmail_client.list_accounts()


@app.post("/api/accounts")
async def add_account() -> dict[str, str]:
    """Open a browser OAuth flow to authenticate a new Gmail account.
    Blocks until the user completes the flow.
    """
    try:
        email = await asyncio.to_thread(gmail_client.authenticate_new_account)
        return {"email": email}
    except Exception as exc:
        _raise(exc)


@app.get("/api/labels")
async def list_labels() -> list[dict[str, str]]:
    """All user-created labels across every authenticated account."""
    try:
        return gmail_client.fetch_all_labels()
    except Exception as exc:
        _raise(exc)


@app.get("/api/emails/next")
async def next_email() -> dict[str, Any] | None:
    """Next inbox email with no user labels. Returns null when all inboxes are clear."""
    try:
        return gmail_client.fetch_next_untagged_email()
    except Exception as exc:
        _raise(exc)


@app.post("/api/emails/{email_id}/classify")
async def classify_email(email_id: str, body: ClassifyBody) -> dict[str, str]:
    """Apply a label and archive the email, using the correct account's service."""
    try:
        gmail_client.apply_label_and_archive(email_id, body.label_id, body.account)
        return {"status": "ok"}
    except Exception as exc:
        _raise(exc)
