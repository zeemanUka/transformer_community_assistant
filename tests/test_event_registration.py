"""
Pytest coverage for event_registration module.

Mocks Firebase and MailerSend so tests run without credentials.
Run: uv run pytest tests/test_event_registration.py -v
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

# -----------------------------------------------------------------------------
# format_event_details_for_message (pure)
# -----------------------------------------------------------------------------
from event_registration import (  # noqa: E402
    REGISTRATION_COLLECTION,
    EVENT_REGISTRATION_TOOLS,
    bind_event_registration_tools,
    fetch_events_by_email_tool,
    format_event_details_for_message,
    get_event_registration_tools,
    get_register_for_event_tools,
    register_for_event_tool,
)


class TestFormatEventDetailsForMessage:
    def test_empty_dict_uses_default_name(self):
        out = format_event_details_for_message({})
        assert "Event: Event" in out
        assert out.count("\n") == 0 or "Event: Event" == out.split("\n")[0]

    def test_full_event_includes_fields(self):
        ev = {
            "name": "Meetup",
            "shortDescription": "Short",
            "description": "Long desc",
            "startDate": datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
            "endDate": datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc),
            "venue": "Hall A",
            "projectType": "CONFERENCE",
            "id": "uuid-123",
        }
        out = format_event_details_for_message(ev)
        assert "Meetup" in out
        assert "Short" in out
        assert "Long desc" in out
        assert "Start:" in out
        assert "End:" in out
        assert "Hall A" in out
        assert "CONFERENCE" in out
        assert "uuid-123" in out

    def test_uses_firestore_doc_id_when_no_id(self):
        ev = {"name": "X", "_firestore_doc_id": "doc-abc"}
        out = format_event_details_for_message(ev)
        assert "doc-abc" in out


# -----------------------------------------------------------------------------
# _validate_email and _parse_from_env (via module)
# -----------------------------------------------------------------------------
import event_registration as er


class TestValidateEmail:
    @pytest.mark.parametrize(
        "email,expected",
        [
            ("a@b.co", True),
            (" user@domain.com ", True),
            ("", False),
            ("not-an-email", False),
            ("@nodomain.com", False),
            (None, False),
        ],
    )
    def test_validate_email(self, email, expected):
        assert er._validate_email(email) is expected


class TestParseFromEnv:
    def test_plain_email(self):
        assert er._parse_from_env("noreply@test.com") == ("noreply@test.com", None)

    def test_name_angle_brackets(self):
        assert er._parse_from_env('Events <e@test.com>') == ("e@test.com", "Events")

    def test_empty(self):
        assert er._parse_from_env("") == ("", None)
        assert er._parse_from_env("   ") == ("", None)


# -----------------------------------------------------------------------------
# ensure_firebase_initialized
# -----------------------------------------------------------------------------
class TestEnsureFirebaseInitialized:
    def test_raises_when_config_missing(self):
        def getenv_side_effect(key, default=None):
            if key == "FIREBASE_CONFIG_JSON":
                return None
            return default

        with patch.object(er.firebase_admin, "_apps", {}):
            with patch("event_registration.os.getenv", side_effect=getenv_side_effect):
                with pytest.raises(RuntimeError, match="FIREBASE_CONFIG_JSON"):
                    er.ensure_firebase_initialized()

    def test_no_op_when_already_initialized(self):
        mock_app = MagicMock()
        with patch.object(er.firebase_admin, "_apps", {"default": mock_app}):
            er.ensure_firebase_initialized()  # should not raise


# -----------------------------------------------------------------------------
# fetch_event_by_id
# -----------------------------------------------------------------------------
class TestFetchEventById:
    def test_found_by_document_id(self):
        snap = MagicMock()
        snap.exists = True
        snap.id = "doc-id-1"
        snap.to_dict.return_value = {"name": "E1", "id": "internal-1"}

        doc_ref = MagicMock()
        doc_ref.get.return_value = snap

        col = MagicMock()
        col.document.return_value = doc_ref

        db = MagicMock()
        db.collection.return_value = col

        with patch.object(er, "ensure_firebase_initialized"):
            with patch.object(er.firestore, "client", return_value=db):
                result = er.fetch_event_by_id("doc-id-1")

        assert result is not None
        assert result["name"] == "E1"
        assert result["_firestore_doc_id"] == "doc-id-1"

    def test_found_by_query_when_doc_missing(self):
        snap_doc = MagicMock()
        snap_doc.exists = False
        doc_ref = MagicMock()
        doc_ref.get.return_value = snap_doc

        query_snap = MagicMock()
        query_snap.id = "q-doc"
        query_snap.to_dict.return_value = {"name": "E2", "id": "uuid-2"}

        query = MagicMock()
        query.limit.return_value = query
        query.stream.return_value = iter([query_snap])

        col = MagicMock()
        col.document.return_value = doc_ref
        col.where.return_value = query

        db = MagicMock()
        db.collection.return_value = col

        with patch.object(er, "ensure_firebase_initialized"):
            with patch.object(er.firestore, "client", return_value=db):
                result = er.fetch_event_by_id("uuid-2")

        assert result is not None
        assert result["name"] == "E2"
        assert result["_firestore_doc_id"] == "q-doc"

    def test_not_found(self):
        snap = MagicMock()
        snap.exists = False
        doc_ref = MagicMock()
        doc_ref.get.return_value = snap

        query = MagicMock()
        query.limit.return_value = query
        query.stream.return_value = iter([])

        col = MagicMock()
        col.document.return_value = doc_ref
        col.where.return_value = query

        db = MagicMock()
        db.collection.return_value = col

        with patch.object(er, "ensure_firebase_initialized"):
            with patch.object(er.firestore, "client", return_value=db):
                assert er.fetch_event_by_id("missing") is None


# -----------------------------------------------------------------------------
# fetch_events
# -----------------------------------------------------------------------------
class TestFetchEvents:
    def test_streams_all_with_doc_ids(self):
        s1 = MagicMock()
        s1.id = "d1"
        s1.to_dict.return_value = {"name": "A"}
        s2 = MagicMock()
        s2.id = "d2"
        s2.to_dict.return_value = None

        col = MagicMock()
        col.stream.return_value = iter([s1, s2])

        db = MagicMock()
        db.collection.return_value = col

        with patch.object(er, "ensure_firebase_initialized"):
            with patch.object(er.firestore, "client", return_value=db):
                out = er.fetch_events()

        assert len(out) == 2
        assert out[0]["name"] == "A"
        assert out[0]["_firestore_doc_id"] == "d1"
        assert out[1]["_firestore_doc_id"] == "d2"


# -----------------------------------------------------------------------------
# send_registration_confirmation_mailersend
# -----------------------------------------------------------------------------
class TestSendRegistrationConfirmationMailersend:
    def test_raises_without_token(self):
        # Avoid real .env / network: no API key and no from → fails before MailerSendClient
        def getenv_no_token(key, default=None):
            if key in ("MAILERSEND_API_TOKEN", "MAILERSEND_API_KEY"):
                return None
            if key == "MAILERSEND_FROM":
                return "a@b.com"
            return default

        with patch("event_registration.os.getenv", side_effect=getenv_no_token):
            with patch.object(er, "MAILERSEND_API_TOKEN", ""):
                with pytest.raises(RuntimeError, match="MAILERSEND_API_TOKEN"):
                    er.send_registration_confirmation_mailersend(
                        "to@test.com", {"name": "Ev"}
                    )

    def test_raises_without_from(self):
        def getenv_no_from(key, default=None):
            if key in ("MAILERSEND_API_TOKEN", "MAILERSEND_API_KEY"):
                return "token"
            if key == "MAILERSEND_FROM":
                return None
            return default

        with patch("event_registration.os.getenv", side_effect=getenv_no_from):
            with patch.object(er, "MAILERSEND_FROM", ""):
                with pytest.raises(RuntimeError, match="MAILERSEND_FROM"):
                    er.send_registration_confirmation_mailersend(
                        "to@test.com", {"name": "Ev"}
                    )

    def test_sends_via_client(self):
        def getenv_ok(key, default=None):
            if key in ("MAILERSEND_API_TOKEN", "MAILERSEND_API_KEY"):
                return "token"
            if key == "MAILERSEND_FROM":
                return "Sender <from@test.com>"
            return default

        with patch("event_registration.os.getenv", side_effect=getenv_ok):
            mock_client = MagicMock()
            with patch.object(er, "MailerSendClient", return_value=mock_client):
                er.send_registration_confirmation_mailersend(
                    "to@test.com", {"name": "My Event", "id": "1"}
                )
            mock_client.emails.send.assert_called_once()

    def test_wraps_send_failure(self):
        def getenv_ok(key, default=None):
            if key in ("MAILERSEND_API_TOKEN", "MAILERSEND_API_KEY"):
                return "token"
            if key == "MAILERSEND_FROM":
                return "from@test.com"
            return default

        with patch("event_registration.os.getenv", side_effect=getenv_ok):
            mock_client = MagicMock()
            mock_client.emails.send.side_effect = ValueError("api down")
            with patch.object(er, "MailerSendClient", return_value=mock_client):
                with pytest.raises(RuntimeError, match="MailerSend send failed"):
                    er.send_registration_confirmation_mailersend(
                        "to@test.com", {"name": "Ev"}
                    )


# -----------------------------------------------------------------------------
# register_for_event
# -----------------------------------------------------------------------------
class TestRegisterForEvent:
    def test_invalid_email(self):
        r = er.register_for_event("bad", "id1")
        assert r["success"] is False
        assert "Invalid email" in r["error"]

    def test_missing_event_id(self):
        r = er.register_for_event("ok@test.com", "")
        assert r["success"] is False
        assert "Event ID is required" in r["error"]

    def test_event_not_found(self):
        with patch.object(er, "fetch_event_by_id", return_value=None):
            r = er.register_for_event("ok@test.com", "missing-id")
        assert r["success"] is False
        assert "No event found" in r["error"]

    def test_success_writes_and_sends(self):
        event = {"name": "Conf", "id": "e1", "_firestore_doc_id": "fd1"}
        add_mock = MagicMock()
        col_mock = MagicMock()
        col_mock.add = add_mock
        db_mock = MagicMock()
        db_mock.collection.return_value = col_mock

        with patch.object(er, "fetch_event_by_id", return_value=event):
            with patch.object(er, "ensure_firebase_initialized"):
                with patch.object(er.firestore, "client", return_value=db_mock):
                    with patch.object(
                        er, "send_registration_confirmation_mailersend"
                    ) as send_mock:
                        r = er.register_for_event("user@test.com", "e1")

        assert r["success"] is True
        assert "confirmation email sent" in r["message"]
        send_mock.assert_called_once_with("user@test.com", event)
        db_mock.collection.assert_called_with(REGISTRATION_COLLECTION)
        add_mock.assert_called_once()
        call_kw = add_mock.call_args[0][0]
        assert call_kw["email"] == "user@test.com"
        assert call_kw["event_id"] == "e1"

    def test_success_with_email_failure_still_stores(self):
        event = {"name": "Conf", "id": "e1", "_firestore_doc_id": "fd1"}
        add_mock = MagicMock()
        col_mock = MagicMock()
        col_mock.add = add_mock
        db_mock = MagicMock()
        db_mock.collection.return_value = col_mock

        with patch.object(er, "fetch_event_by_id", return_value=event):
            with patch.object(er, "ensure_firebase_initialized"):
                with patch.object(er.firestore, "client", return_value=db_mock):
                    with patch.object(
                        er,
                        "send_registration_confirmation_mailersend",
                        side_effect=RuntimeError("send failed"),
                    ):
                        r = er.register_for_event("user@test.com", "e1")

        assert r["success"] is True
        assert "warning" in r
        assert "confirmation email failed" in r["warning"]
        add_mock.assert_called_once()


# -----------------------------------------------------------------------------
# register_for_event_tool & get_register_for_event_tools
# -----------------------------------------------------------------------------
class TestRegisterForEventTool:
    def test_failure_message(self):
        with patch.object(er, "register_for_event", return_value={"success": False, "error": "No event"}):
            out = register_for_event_tool.invoke({"email": "a@b.com", "event_id": "x"})
        assert "Registration failed" in out
        assert "No event" in out

    def test_success_message(self):
        with patch.object(
            er,
            "register_for_event",
            return_value={
                "success": True,
                "message": "Registration saved and confirmation email sent.",
                "event_summary": "Event: Foo",
            },
        ):
            out = register_for_event_tool.invoke({"email": "a@b.com", "event_id": "x"})
        assert "Registration saved" in out
        assert "Event: Foo" in out

    def test_success_with_warning(self):
        with patch.object(
            er,
            "register_for_event",
            return_value={
                "success": True,
                "message": "Done.",
                "warning": "email failed",
                "event_summary": "Event: Bar",
            },
        ):
            out = register_for_event_tool.invoke({"email": "a@b.com", "event_id": "x"})
        assert "email failed" in out
        assert "Event: Bar" in out


class TestFetchEventRegistrationsByEmail:
    def test_invalid_email_returns_empty(self):
        assert er.fetch_event_registrations_by_email("") == []
        assert er.fetch_event_registrations_by_email("not-email") == []

    def test_queries_by_email(self):
        snap = MagicMock()
        snap.id = "reg-doc-1"
        snap.to_dict.return_value = {
            "email": "u@test.com",
            "event_id": "e1",
            "event_name": "Conf",
        }
        query = MagicMock()
        query.stream.return_value = iter([snap])
        col = MagicMock()
        col.where.return_value = query
        db = MagicMock()
        db.collection.return_value = col

        with patch.object(er, "ensure_firebase_initialized"):
            with patch.object(er.firestore, "client", return_value=db):
                out = er.fetch_event_registrations_by_email("u@test.com")

        col.where.assert_called_once_with("email", "==", "u@test.com")
        assert len(out) == 1
        assert out[0]["event_id"] == "e1"
        assert out[0]["_firestore_doc_id"] == "reg-doc-1"


class TestFormatRegistrationsForMessage:
    def test_empty(self):
        assert "No event registrations" in er.format_registrations_for_message([])

    def test_lists_rows(self):
        rows = [
            {"event_id": "e1", "event_name": "A", "_firestore_doc_id": "d1"},
        ]
        out = er.format_registrations_for_message(rows)
        assert "1 registration" in out
        assert "A" in out and "e1" in out


class TestFetchEventsByEmailTool:
    def test_invalid_email(self):
        out = fetch_events_by_email_tool.invoke({"email": "bad"})
        assert "Invalid email" in out

    def test_uses_fetch_and_format(self):
        with patch.object(
            er,
            "fetch_event_registrations_by_email",
            return_value=[{"event_id": "x", "event_name": "Y"}],
        ):
            out = fetch_events_by_email_tool.invoke({"email": "a@b.com"})
        assert "1 registration" in out
        assert "Y" in out


class TestGetRegisterForEventTools:
    def test_returns_both_tools(self):
        for getter in (get_register_for_event_tools, get_event_registration_tools):
            tools = getter()
            names = {t.name for t in tools}
            assert "register_for_event_tool" in names
            assert "fetch_events_by_email_tool" in names

    def test_event_registration_tools_constant_matches(self):
        assert len(EVENT_REGISTRATION_TOOLS) == 2
        assert {t.name for t in EVENT_REGISTRATION_TOOLS} == {
            "register_for_event_tool",
            "fetch_events_by_email_tool",
        }

    def test_bind_event_registration_tools(self):
        llm = MagicMock()
        llm.bind_tools.return_value = "bound"
        out = bind_event_registration_tools(llm)
        llm.bind_tools.assert_called_once()
        call_args = llm.bind_tools.call_args[0][0]
        assert len(call_args) == 2
        assert out == "bound"
