"""
Event registration tool for LLM tool-calling.

- Registers email + event_id in Firestore collection `event_registration`.
- Sends confirmation email via MailerSend with event details loaded from Firebase.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any

import firebase_admin
from firebase_admin import credentials, firestore
from mailersend import EmailBuilder, MailerSendClient
from langchain_core.tools import tool

load_dotenv = None
try:
    from dotenv import load_dotenv as _load_dotenv

    load_dotenv = _load_dotenv
except ImportError:
    pass

# Firestore collection where event/project documents live (Audiatur uses `projects`)
EVENTS_COLLECTION = os.getenv("EVENTS_COLLECTION", "projects")
REGISTRATION_COLLECTION = "event_registration"

# MailerSend Python SDK v2 — MailerSendClient + EmailBuilder (reads MAILERSEND_API_KEY if api_key omitted)
MAILERSEND_API_TOKEN = os.getenv("MAILERSEND_API_TOKEN", os.getenv("MAILERSEND_API_KEY", ""))
MAILERSEND_FROM = os.getenv("MAILERSEND_FROM", "")  # e.g. "Events <noreply@yourdomain.com>" or just email


def _ensure_dotenv() -> None:
    if load_dotenv:
        load_dotenv(override=True)


def ensure_firebase_initialized() -> None:
    """Initialize Firebase app once using FIREBASE_CONFIG_JSON (same as notebook)."""
    if firebase_admin._apps:
        return
    _ensure_dotenv()
    config_raw = os.getenv("FIREBASE_CONFIG_JSON")
    if not config_raw:
        raise RuntimeError("FIREBASE_CONFIG_JSON is not set")
    config = json.loads(config_raw)
    cred = credentials.Certificate(config)
    firebase_admin.initialize_app(cred)

def fetch_events() -> list[dict[str, Any]]:
    """Fetch all events/projects from Firestore collection EVENTS_COLLECTION (default: projects)."""
    ensure_firebase_initialized()
    db = firestore.client()
    col = db.collection(EVENTS_COLLECTION)
    out: list[dict[str, Any]] = []
    for snap in col.stream():
        data = snap.to_dict() or {}
        data["_firestore_doc_id"] = snap.id
        out.append(data)
    return out

def fetch_event_registrations() -> list[dict[str, Any]]:
    """
    Fetch all documents from the event_registration collection.
    Each dict includes the stored fields (email, event_id, registered_at, etc.)
    plus _firestore_doc_id for the auto-generated document id.
    """
    ensure_firebase_initialized()
    db = firestore.client()
    col = db.collection(REGISTRATION_COLLECTION)
    out: list[dict[str, Any]] = []
    for snap in col.stream():
        data = snap.to_dict() or {}
        data["_firestore_doc_id"] = snap.id
        out.append(data)
    return out


def _firestore_datetime_to_str(value: Any) -> str:
    """Convert Firestore DatetimeWithNanoseconds or datetime to ISO string."""
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    return str(value)


def _sanitize_for_email(text: str, max_len: int = 2000) -> str:
    if not text:
        return ""
    text = str(text).strip()
    if len(text) > max_len:
        text = text[: max_len - 3] + "..."
    return text


def fetch_event_by_id(event_id: str) -> dict[str, Any] | None:
    """
    Load event/project from Firestore by ID.
    Tries document ID first, then queries by field `id` (Audiatur stores UUID in doc).
    """
    ensure_firebase_initialized()
    db = firestore.client()
    col = db.collection(EVENTS_COLLECTION)

    # 1) Direct document lookup (event_id as Firestore document ID)
    doc_ref = col.document(event_id)
    snap = doc_ref.get()
    if snap.exists:
        data = snap.to_dict() or {}
        data["_firestore_doc_id"] = snap.id
        return data

    # 2) Query by internal id field
    query = col.where("id", "==", event_id).limit(1)
    for d in query.stream():
        data = d.to_dict() or {}
        data["_firestore_doc_id"] = d.id
        return data

    return None


def format_event_details_for_message(event: dict[str, Any]) -> str:
    """Build a human-readable block from Firestore event/project dict for email body."""
    lines = []
    name = event.get("name") or "Event"
    lines.append(f"Event: {name}")

    if event.get("shortDescription"):
        lines.append(f"Summary: {_sanitize_for_email(event['shortDescription'], 500)}")
    if event.get("description"):
        lines.append(f"Description: {_sanitize_for_email(event['description'], 1000)}")

    start = _firestore_datetime_to_str(event.get("startDate"))
    end = _firestore_datetime_to_str(event.get("endDate"))
    if start:
        lines.append(f"Start: {start}")
    if end:
        lines.append(f"End: {end}")
    if event.get("venue"):
        lines.append(f"Venue: {event['venue']}")
    if event.get("projectType"):
        lines.append(f"Type: {event['projectType']}")

    internal_id = event.get("id") or event.get("_firestore_doc_id", "")
    if internal_id:
        lines.append(f"Event ID: {internal_id}")

    return "\n".join(lines)


def _validate_email(email: str) -> bool:
    if not email or not isinstance(email, str):
        return False
    email = email.strip()
    # Practical RFC-like check
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))


def fetch_event_registrations_by_email(email: str) -> list[dict[str, Any]]:
    """
    Fetch event_registration documents for a given attendee email.

    Returns list of dicts with email, event_id, registered_at, event_name, etc.
    plus _firestore_doc_id. Empty list if none or invalid email.
    """
    email = (email or "").strip()
    if not _validate_email(email):
        return []

    ensure_firebase_initialized()
    db = firestore.client()
    col = db.collection(REGISTRATION_COLLECTION)
    query = col.where("email", "==", email)
    out: list[dict[str, Any]] = []
    for snap in query.stream():
        data = snap.to_dict() or {}
        data["_firestore_doc_id"] = snap.id
        out.append(data)
    return out


def format_registrations_for_message(registrations: list[dict[str, Any]]) -> str:
    """Build a human-readable summary of registration records for the LLM/user."""
    if not registrations:
        return "No event registrations found for this email."
    lines = [f"Found {len(registrations)} registration(s):\n"]
    for i, r in enumerate(registrations, 1):
        event_id = r.get("event_id", "")
        event_name = r.get("event_name") or "(name not stored)"
        at = _firestore_datetime_to_str(r.get("registered_at"))
        doc_id = r.get("_firestore_doc_id", "")
        lines.append(f"{i}. Event: {event_name}")
        lines.append(f"   event_id: {event_id}")
        if at:
            lines.append(f"   registered_at: {at}")
        if doc_id:
            lines.append(f"   registration_doc_id: {doc_id}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _parse_from_env(from_value: str) -> tuple[str, str | None]:
    """
    Parse 'Name <email@domain.com>' or 'email@domain.com' into (email, name).
    """
    from_value = (from_value or "").strip()
    if not from_value:
        return "", None
    if "<" in from_value and ">" in from_value:
        start = from_value.index("<") + 1
        end = from_value.index(">")
        email = from_value[start:end].strip()
        name = from_value[: from_value.index("<")].strip().strip('"') or None
        return email, name
    return from_value, None


def send_registration_confirmation_mailersend(
    to_email: str,
    event: dict[str, Any],
    subject_prefix: str = "Registration confirmed",
) -> None:
    """Send HTML + text confirmation via MailerSend Python SDK."""
    _ensure_dotenv()
    token = os.getenv("MAILERSEND_API_TOKEN", os.getenv("MAILERSEND_API_KEY", MAILERSEND_API_TOKEN))
    from_raw = os.getenv("MAILERSEND_FROM", MAILERSEND_FROM)

    if not token:
        raise RuntimeError("MAILERSEND_API_TOKEN (or MAILERSEND_API_KEY) is not set")
    if not from_raw:
        raise RuntimeError(
            "MAILERSEND_FROM is not set (e.g. 'Events <noreply@yourdomain.com>' or verified sender email)"
        )

    from_email, from_name = _parse_from_env(from_raw)
    if not from_email or not _validate_email(from_email):
        raise RuntimeError("MAILERSEND_FROM must be a valid sender email (verified in MailerSend)")

    details = format_event_details_for_message(event)
    event_name = event.get("name") or "the event"
    subject = f"{subject_prefix}: {event_name}"

    text_body = (
        f"You are successfully registered for {event_name}.\n\n"
        f"{details}\n\n"
        "If you did not register for this event, you can ignore this email.\n"
    )

    html_body = f"""<html><body>
<p>You are successfully registered for <strong>{_sanitize_for_email(event_name, 200)}</strong>.</p>
<pre style="white-space:pre-wrap;font-family:sans-serif;">{_sanitize_for_email(details, 3000)}</pre>
<p>If you did not register for this event, you can ignore this email.</p>
</body></html>"""

    # mailersend 2.x: EmailBuilder → EmailRequest → client.emails.send(...)
    email_request = (
        EmailBuilder()
        .from_email(from_email, from_name)
        .to_many([{"email": to_email.strip()}])
        .subject(subject)
        .html(html_body)
        .text(text_body)
        .build()
    )

    client = MailerSendClient(api_key=token)
    try:
        client.emails.send(email_request)
    except Exception as e:
        raise RuntimeError(f"MailerSend send failed: {e}") from e


def register_for_event(email: str, event_id: str) -> dict[str, Any]:
    """
    Register an email for an event: write to Firestore then send MailerSend confirmation.

    Returns a dict with success flag and message for the LLM.
    """
    _ensure_dotenv()
    email = (email or "").strip()
    event_id = (event_id or "").strip()

    if not _validate_email(email):
        return {"success": False, "error": "Invalid email address."}
    if not event_id:
        return {"success": False, "error": "Event ID is required."}

    event = fetch_event_by_id(event_id)
    if not event:
        return {
            "success": False,
            "error": f"No event found for ID '{event_id}'. Check the ID and try again.",
        }

    ensure_firebase_initialized()
    db = firestore.client()
    now = datetime.now(timezone.utc)
    reg_doc = {
        "email": email,
        "event_id": event_id,
        "registered_at": now,
        # Optional denormalized fields for admin views
        "event_name": event.get("name"),
        "firestore_event_doc_id": event.get("_firestore_doc_id"),
    }
    db.collection(REGISTRATION_COLLECTION).add(reg_doc)

    try:
        send_registration_confirmation_mailersend(email, event)
    except Exception as e:
        # Registration is already stored; surface email failure clearly
        return {
            "success": True,
            "warning": f"Registered in database but confirmation email failed: {e}",
            "event_summary": format_event_details_for_message(event),
        }

    return {
        "success": True,
        "message": "Registration saved and confirmation email sent.",
        "event_summary": format_event_details_for_message(event),
    }


@tool
def fetch_events_by_email_tool(email: str) -> str:
    """
    Look up which events an email is registered for.
    Use when the user asks what they are signed up for, their registrations, or events for their email.
    Args:
        email: The attendee's email address to look up.
    """
    email = (email or "").strip()
    if not _validate_email(email):
        return "Invalid email address; cannot look up registrations."
    rows = fetch_event_registrations_by_email(email)
    return format_registrations_for_message(rows)


@tool
def register_for_event_tool(email: str, event_id: str) -> str:
    """
    Register the user for an event by email and event ID.
    Use when the user wants to sign up or register for a specific event.
    After success, the user receives a confirmation email with event details.
    Args:
        email: The attendee's email address.
        event_id: The event's ID (UUID or Firestore document id as used in the system).
    """
    result = register_for_event(email, event_id)
    if result.get("success"):
        parts = [result.get("message") or "Registration completed."]
        if result.get("warning"):
            parts.append(result["warning"])
        if result.get("event_summary"):
            parts.append("Event details:\n" + result["event_summary"])
        return "\n\n".join(parts)
    return f"Registration failed: {result.get('error', 'Unknown error')}"


def get_register_for_event_tools():
    """Return list of tools to bind to an LLM (e.g. llm.bind_tools(get_register_for_event_tools()))."""
    return [register_for_event_tool, fetch_events_by_email_tool]
