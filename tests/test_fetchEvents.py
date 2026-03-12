"""
Manual test to fetch events/projects from Firebase Firestore.

Requires .env with FIREBASE_CONFIG_JSON (service account JSON string).

Run from project root:
  uv run python tests/test_fetchEvents.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Project root on path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_env() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env", override=True)
    except ImportError:
        pass


def main() -> None:
    _load_env()

    from event_registration import (  # noqa: E402
        EVENTS_COLLECTION,
        fetch_event_by_id,
        fetch_events,
        format_event_details_for_message,
    )

    print(f"Fetching all documents from collection: {EVENTS_COLLECTION!r}")
    events = fetch_events()
    print(f"Count: {len(events)}")
    print()

    for i, ev in enumerate(events):
        doc_id = ev.get("_firestore_doc_id", "?")
        name = ev.get("name", "(no name)")
        internal_id = ev.get("id", "")
        ptype = ev.get("projectType", "")
        print(f"  [{i}] doc_id={doc_id}  name={name!r}  id={internal_id!r}  type={ptype!r}")

    if events:
        print()
        print("--- First event formatted ---")
        print(format_event_details_for_message(events[0]))


if __name__ == "__main__":
    main()
