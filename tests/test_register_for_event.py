"""
Manual test for register_for_event (Firestore event_registration + MailerSend).

Uses the same email as test_mailersend_send and an event id from test_fetch_event_by_id.
This writes to Firestore collection `event_registration` and sends a real email.

Requires .env:
  FIREBASE_CONFIG_JSON
  MAILERSEND_API_TOKEN (or MAILERSEND_API_KEY) + MAILERSEND_FROM

Run from project root:
  uv run python tests/test_register_for_event.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


REGISTER_TEST_EMAIL = "talk2mm97@gmail.com"

REGISTER_TEST_EVENT_ID = "TfcHEfgSbFBSInTlMs6t"


def _load_env() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env", override=True)
    except ImportError:
        pass


def main() -> None:
    _load_env()

    from event_registration import register_for_event  

    email, event_id = REGISTER_TEST_EMAIL, REGISTER_TEST_EVENT_ID

    print("register_for_event test")
    print(f"  email:    {email!r}")
    print(f"  event_id: {event_id!r}")
    print()

    result = register_for_event(email, event_id)

    print("Result:")
    for k, v in result.items():
        if k == "event_summary" and v:
            print(f"  {k}:")
            for line in str(v).splitlines():
                print(f"    {line}")
        else:
            print(f"  {k}: {v!r}")

    if not result.get("success"):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
