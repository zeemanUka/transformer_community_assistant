"""
Manual test for fetch_event_registrations_by_email — one email (CLI) or a list (below).

Requires .env with FIREBASE_CONFIG_JSON.

Run from project root:
  uv run python tests/test_fetch_event_registrations_by_email.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# --- Add attendee emails to look up in event_registration ---
EMAILS: list[str] = [
    "talk2mm97@gmail.com",
    # "another@example.com",
]


def _load_env() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env", override=True)
    except ImportError:
        pass


def _print_registrations(email: str, rows: list) -> None:
    from event_registration import format_registrations_for_message  # noqa: E402

    print(f"========== email={email!r} ==========")
    if not rows:
        print("  Result: no registrations found")
        print()
        return
    print(f"  Result: {len(rows)} registration(s)")
    print("  --- details ---")
    for line in format_registrations_for_message(rows).splitlines():
        print(f"    {line}")
    print()


def main() -> None:
    _load_env()

    from event_registration import (  # noqa: E402
        REGISTRATION_COLLECTION,
        fetch_event_registrations_by_email,
    )

    emails = [e.strip() for e in EMAILS if str(e).strip()]

    if not emails:
        print("No emails to look up.")
        print("  Either add emails to EMAILS in this file, or run:")
        print("  uv run python tests/test_fetch_event_registrations_by_email.py <email> [email ...]")
        print(f"  Collection: {REGISTRATION_COLLECTION!r}")
        sys.exit(2)

    print(f"Collection: {REGISTRATION_COLLECTION!r}")
    print(f"Looking up {len(emails)} email(s)\n")

    with_registrations = 0
    for email in emails:
        rows = fetch_event_registrations_by_email(email)
        if rows:
            with_registrations += 1
        _print_registrations(email, rows)

    print(f"Summary: {with_registrations}/{len(emails)} email(s) have at least one registration")
    sys.exit(0)


if __name__ == "__main__":
    main()
