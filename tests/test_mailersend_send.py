"""
Manual test for MailerSend registration confirmation email.

Requires .env with MAILERSEND_API_TOKEN (or MAILERSEND_API_KEY) and MAILERSEND_FROM.

Run from project root:
  uv run python tests/test_mailersend_send.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

# Project root on path so `event_registration` imports
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from event_registration import (  # noqa: E402
    format_event_details_for_message,
    send_registration_confirmation_mailersend,
)

# Sample event shaped like Firestore `projects` docs (see community_assistant notebook)
SAMPLE_EVENT = {
    "id": "sample-event-001-test",
    "name": "Community Tech Meetup 2026",
    "shortDescription": "Quarterly meetup for builders and community managers.",
    "description": (
        "Join us for an evening of lightning talks, networking, and pizza. "
        "We will cover Firebase, LLM tool-calling, and event registration flows."
    ),
    "startDate": datetime(2026, 4, 15, 18, 0, tzinfo=timezone.utc),
    "endDate": datetime(2026, 4, 15, 21, 0, tzinfo=timezone.utc),
    "venue": "Andela Learning Hub, Lagos",
    "projectType": "CONFERENCE",
    "_firestore_doc_id": "doc-sample-001",
}

TEST_RECIPIENT = "talk2mm97@gmail.com"


def main() -> None:
    # Load .env from project root even if cwd is elsewhere
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env", override=True)
    except ImportError:
        pass

    print("Sample event details preview:")
    print(format_event_details_for_message(SAMPLE_EVENT))
    print()
    print(f"Sending test email to {TEST_RECIPIENT} ...")
    send_registration_confirmation_mailersend(TEST_RECIPIENT, SAMPLE_EVENT)
    print("Done. Check inbox (and spam).")


if __name__ == "__main__":
    main()
