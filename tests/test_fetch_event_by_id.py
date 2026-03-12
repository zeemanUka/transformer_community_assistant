"""
Manual test for fetch_event_by_id — fetch one id (CLI) or a list of ids (below).

Requires .env with FIREBASE_CONFIG_JSON.

Run from project root:
  uv run python tests/test_fetch_event_by_id.py              # uses EVENT_IDS below
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# --- Add Firestore document ids and/or internal UUIDs here ---
EVENT_IDS: list[str] = [
  "ja8btp6Ek4tGiVQ8dQdX",
  "XHeqdyHZoMgUECp0Iuhm",
  "TfcHEfgSbFBSInTlMs6t"
]


def _load_env() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env", override=True)
    except ImportError:
        pass


def _print_event(event_id: str, event: dict | None) -> None:
    from event_registration import format_event_details_for_message  # noqa: E402

    print(f"========== id={event_id!r} ==========")
    if event is None:
        print("  Result: NOT FOUND")
        print()
        return
    print("  Result: found")
    print(f"  _firestore_doc_id: {event.get('_firestore_doc_id')!r}")
    print(f"  id (field):        {event.get('id')!r}")
    print(f"  name:              {event.get('name')!r}")
    print(f"  projectType:       {event.get('projectType')!r}")
    print("  --- details ---")
    for line in format_event_details_for_message(event).splitlines():
        print(f"    {line}")
    print()


def main() -> None:
    _load_env()

    from event_registration import EVENTS_COLLECTION, fetch_event_by_id  # noqa: E402

   
    ids = [i.strip() for i in EVENT_IDS if str(i).strip()]

    if not ids:
        print("No ids to fetch.")
        print("  Either add ids to EVENT_IDS in this file, or run:")
        print("  uv run python tests/test_fetch_event_by_id.py <id> [id ...]")
        print(f"  Collection: {EVENTS_COLLECTION!r}")
        sys.exit(2)

    print(f"Collection: {EVENTS_COLLECTION!r}")
    print(f"Fetching {len(ids)} id(s)\n")

    found = 0
    for event_id in ids:
        event = fetch_event_by_id(event_id)
        if event is not None:
            found += 1
        _print_event(event_id, event)

    print(f"Summary: {found}/{len(ids)} found")
    sys.exit(0 if found == len(ids) else 1)


if __name__ == "__main__":
    main()
