"""
Manual test to fetch all event_registration documents from Firebase.

Requires .env with FIREBASE_CONFIG_JSON.

Run from project root:
  uv run python tests/test_fetch_event_registrations.py
"""

from __future__ import annotations

import sys
from pathlib import Path

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
        REGISTRATION_COLLECTION,
        fetch_event_registrations,
    )
    import event_registration as er

    print(f"Fetching all documents from collection: {REGISTRATION_COLLECTION!r}")
    rows = fetch_event_registrations()
    print(f"Count: {len(rows)}")
    print()

    for i, r in enumerate(rows):
        email = r.get("email", "")
        event_id = r.get("event_id", "")
        doc_id = r.get("_firestore_doc_id", "")
        event_name = r.get("event_name", "")
        registered_at = r.get("registered_at")
        at_str = er._firestore_datetime_to_str(registered_at) if registered_at else ""
        print(f"  [{i}] doc_id={doc_id!r}")
        print(f"       email={email!r}  event_id={event_id!r}")
        if event_name:
            print(f"       event_name={event_name!r}")
        if at_str:
            print(f"       registered_at={at_str}")
        print()

    if not rows:
        print("No registrations found.")
        sys.exit(0)
    sys.exit(0)


if __name__ == "__main__":
    main()
