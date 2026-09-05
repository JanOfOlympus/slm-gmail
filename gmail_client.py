"""
Minimal Gmail client: OAuth login + fetch today's messages (subject, sender, snippet/body).

Setup (one-time):
1. Go to https://console.cloud.google.com/ -> create a project (or use existing)
2. Enable the "Gmail API"
3. Create OAuth 2.0 credentials -> Application type: "Desktop app"
4. Download the JSON, save it as credentials.json in this same folder
5. First run will open a browser to authorize; a token.json is cached after that
"""

import base64
import os
from datetime import date

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
TOKEN_PATH = "token.json"
CREDENTIALS_PATH = "credentials.json"


def get_gmail_service():
    """Handles OAuth login, caching the token so you don't re-auth every run."""
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                raise FileNotFoundError(
                    f"Missing {CREDENTIALS_PATH}. See setup instructions at the top of this file."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def _extract_plain_text(payload) -> str:
    """Walks the MIME payload to find and decode a plain-text body."""
    if payload.get("mimeType") == "text/plain" and "data" in payload.get("body", {}):
        data = payload["body"]["data"]
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        text = _extract_plain_text(part)
        if text:
            return text
    return ""


def fetch_todays_emails(service, max_results: int = 20):
    """Returns a list of dicts: {id, subject, sender, snippet, body} for today's inbox emails."""
    today_str = date.today().strftime("%Y/%m/%d")
    query = f"in:inbox after:{today_str}"

    results = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )
    message_stubs = results.get("messages", [])

    emails = []
    for stub in message_stubs:
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=stub["id"], format="full")
            .execute()
        )
        headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
        body = _extract_plain_text(msg["payload"])[:2000]  # cap length for the SLM prompt

        emails.append(
            {
                "id": msg["id"],
                "subject": headers.get("Subject", "(no subject)"),
                "sender": headers.get("From", "(unknown sender)"),
                "snippet": msg.get("snippet", ""),
                "body": body or msg.get("snippet", ""),
            }
        )
    return emails