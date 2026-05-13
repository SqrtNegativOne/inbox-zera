"""FastAPI server — HTTP layer only, no Gmail logic here."""

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
    """Trigger OAuth on startup so the browser flow happens before the UI opens."""
    logger.info("Authenticating with Gmail…")
    try:
        gmail_client.get_credentials()
        logger.info("Gmail auth OK.")
    except FileNotFoundError as exc:
        logger.error(str(exc))
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


def _raise(exc: Exception) -> None:
    raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/labels")
async def list_labels() -> list[dict[str, str]]:
    """All user-created Gmail labels."""
    try:
        return gmail_client.fetch_labels()
    except Exception as exc:
        _raise(exc)


@app.get("/api/emails/next")
async def next_email() -> dict[str, Any] | None:
    """Next inbox email with no user labels. Returns null when inbox is clear."""
    try:
        return gmail_client.fetch_next_untagged_email()
    except Exception as exc:
        _raise(exc)


@app.post("/api/emails/{email_id}/classify")
async def classify_email(email_id: str, body: ClassifyBody) -> dict[str, str]:
    """Apply a label and archive the email."""
    try:
        gmail_client.apply_label_and_archive(email_id, body.label_id)
        return {"status": "ok"}
    except Exception as exc:
        _raise(exc)
