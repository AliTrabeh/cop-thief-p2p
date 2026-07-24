"""Unit tests for logging_setup.py — NFR-004."""

from __future__ import annotations

import logging

from police_thief.logging_setup import RedactionFilter, get_logger


def _filtered_message(raw_message: str) -> str:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=raw_message,
        args=(),
        exc_info=None,
    )
    RedactionFilter().filter(record)
    return record.getMessage()


def test_redacts_credentials_filename():
    assert "***REDACTED***" in _filtered_message("loaded secrets from credentials.json")
    assert "credentials.json" not in _filtered_message("loaded secrets from credentials.json")


def test_redacts_token_filename():
    assert "***REDACTED***" in _filtered_message("refreshed token.json successfully")


def test_redacts_nonce_field_in_json_like_message():
    msg = 'payload: {"nonce": "deadbeefcafebabe0011"}'
    filtered = _filtered_message(msg)
    assert "deadbeefcafebabe0011" not in filtered
    assert "***REDACTED***" in filtered


def test_does_not_touch_unrelated_messages():
    msg = "peer connected on port 8801"
    assert _filtered_message(msg) == msg


def test_get_logger_uses_the_police_thief_namespace():
    logger = get_logger("orchestrator")
    assert logger.name == "police_thief.orchestrator"
