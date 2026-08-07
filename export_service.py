"""
Google Docs export service.

Uses OAuth 2.0 user credentials (client_secrets.json) to create a new
Google Doc by uploading HTML content via the Drive API.  The first run
opens a browser window for consent; the token is then cached in a secure
hidden folder outside the project workspace.
"""

import io
import logging
import os
import re
import stat

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
CLIENT_SECRETS_FILE = "client_secrets.json"

# Store the token in a hidden folder in the user's home directory
SECURE_DIR = os.path.expanduser("~/.research_assistant_keys")
os.makedirs(SECURE_DIR, exist_ok=True)
TOKEN_FILE = os.path.join(SECURE_DIR, "token.json")


def _get_credentials() -> Credentials:
    """Return valid user credentials, prompting for login if necessary."""
    creds = None

    # Load cached token if it exists
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # If no valid credentials, run the OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired token…")
            creds.refresh(Request())
        else:
            logger.info("Starting OAuth login flow…")
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Cache for next time
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

        # Restrict file permissions: owner read/write only (chmod 600)
        os.chmod(TOKEN_FILE, stat.S_IRUSR | stat.S_IWUSR)

        logger.info("Token securely saved to %s", TOKEN_FILE)

    return creds


def _markdown_to_html(md: str) -> str:
    """Minimal markdown → HTML conversion (headings, bold, italic, lists, paragraphs)."""
    lines = md.split("\n")
    html_lines: list[str] = []
    in_ul = False
    in_ol = False

    for line in lines:
        stripped = line.strip()

        # Close open lists if current line is not a list item
        if in_ul and not re.match(r"^[-*]\s", stripped):
            html_lines.append("</ul>")
            in_ul = False
        if in_ol and not re.match(r"^\d+\.\s", stripped):
            html_lines.append("</ol>")
            in_ol = False

        # Headings
        if m := re.match(r"^(#{1,6})\s+(.*)", stripped):
            level = len(m.group(1))
            html_lines.append(f"<h{level}>{m.group(2)}</h{level}>")
        # Unordered list
        elif m := re.match(r"^[-*]\s+(.*)", stripped):
            if not in_ul:
                html_lines.append("<ul>")
                in_ul = True
            html_lines.append(f"<li>{m.group(1)}</li>")
        # Ordered list
        elif m := re.match(r"^\d+\.\s+(.*)", stripped):
            if not in_ol:
                html_lines.append("<ol>")
                in_ol = True
            html_lines.append(f"<li>{m.group(1)}</li>")
        # Empty line
        elif stripped == "":
            html_lines.append("")
        # Paragraph
        else:
            html_lines.append(f"<p>{stripped}</p>")

    if in_ul:
        html_lines.append("</ul>")
    if in_ol:
        html_lines.append("</ol>")

    html = "\n".join(html_lines)
    # Inline formatting
    html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html)
    html = re.sub(r"\*(.+?)\*", r"<i>\1</i>", html)
    html = re.sub(r"`(.+?)`", r"<code>\1</code>", html)
    return html


def export_to_docs(markdown_text: str, title: str) -> str:
    """Create a Google Doc with *title* containing *markdown_text*.

    Uses Drive API to upload HTML and convert to Google Docs format.
    Returns the URL of the newly created document.
    """
    creds = _get_credentials()
    drive_service = build("drive", "v3", credentials=creds)

    # Convert markdown to HTML for better formatting in the Doc
    html_content = _markdown_to_html(markdown_text)
    html_body = f"<html><body>{html_content}</body></html>"

    # Upload HTML and convert to Google Doc in one step
    file_metadata = {
        "name": title,
        "mimeType": "application/vnd.google-apps.document",
    }
    media = MediaIoBaseUpload(
        io.BytesIO(html_body.encode("utf-8")),
        mimetype="text/html",
        resumable=False,
    )

    logger.info("Creating Google Doc via Drive API: %s", title)
    doc = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id",
    ).execute()
    document_id = doc["id"]
    logger.info("Created document: %s", document_id)

    return f"https://docs.google.com/document/d/{document_id}/edit"


