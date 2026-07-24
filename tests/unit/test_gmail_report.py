"""Unit tests for infra/gmail_report.py — FR-080..082.

Never touches a real Gmail account: draft mode writes to disk, and "send"
mode is tested with an injected fake service object.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import pytest

from police_thief.infra.gatekeeper import Gatekeeper
from police_thief.infra.gmail_report import (
    GmailSendError,
    build_mime_message,
    report_match_result,
    send_report,
)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class _FakeMessages:
    def __init__(self, sink: list[dict[str, Any]]) -> None:
        self._sink = sink

    def send(self, userId: str, body: dict[str, Any]) -> _FakeExecutable:  # noqa: N803 - matches Gmail API's own param name
        self._sink.append({"userId": userId, "body": body})
        return _FakeExecutable({"id": "fake-message-id"})


class _FakeExecutable:
    def __init__(self, result: dict[str, Any]) -> None:
        self._result = result

    def execute(self) -> dict[str, Any]:
        return self._result


class _FakeUsers:
    def __init__(self, sink: list[dict[str, Any]]) -> None:
        self._sink = sink

    def messages(self) -> _FakeMessages:
        return _FakeMessages(self._sink)


class FakeGmailService:
    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    def users(self) -> _FakeUsers:
        return _FakeUsers(self.sent)


def test_build_mime_message_is_valid_base64():
    raw = build_mime_message("grader@example.com", "subject", "body text")
    decoded = base64.urlsafe_b64decode(raw.encode()).decode()
    assert "grader@example.com" in decoded
    assert "subject" in decoded
    assert "body text" in decoded


def test_send_report_calls_the_service_and_returns_its_result():
    service = FakeGmailService()
    result = send_report(service, "grader@example.com", "subj", "body")
    assert result == {"id": "fake-message-id"}
    assert len(service.sent) == 1
    assert service.sent[0]["userId"] == "me"


def test_report_match_result_draft_mode_never_touches_a_service(tmp_path: Path):
    status = report_match_result(
        mode="draft",
        recipient="grader@example.com",
        result_json={"outcome": "capture"},
        gatekeeper=Gatekeeper(_rate_limiter_config(), clock=FakeClock()),
        output_dir=tmp_path,
        game_id="g1",
    )
    assert "draft written" in status
    draft_files = list(tmp_path.glob("*.emaildraft.json"))
    assert len(draft_files) == 1
    assert json.loads(draft_files[0].read_text(encoding="utf-8")) == {"outcome": "capture"}


def test_report_match_result_send_mode_uses_injected_service(tmp_path: Path):
    service = FakeGmailService()
    status = report_match_result(
        mode="send",
        recipient="grader@example.com",
        result_json={"outcome": "capture"},
        gatekeeper=Gatekeeper(_rate_limiter_config(), clock=FakeClock()),
        output_dir=tmp_path,
        game_id="g1",
        service=service,
    )
    assert status == "sent to grader@example.com"
    assert len(service.sent) == 1


def test_report_match_result_send_mode_blocked_by_gatekeeper(tmp_path: Path):
    clock = FakeClock()
    config = _rate_limiter_config()
    gk = Gatekeeper(config, clock=clock)
    for _ in range(config.concurrent_requests):
        assert gk.admit().value == "allowed"  # drain the token bucket first
    with pytest.raises(GmailSendError, match="Gatekeeper blocked"):
        report_match_result(
            mode="send",
            recipient="grader@example.com",
            result_json={"outcome": "capture"},
            gatekeeper=gk,
            output_dir=tmp_path,
            game_id="g1",
            service=FakeGmailService(),
        )


def _rate_limiter_config(**overrides: object):
    from police_thief.domain.models import RateLimiterGatekeeperConfig

    base: dict[str, object] = {
        "requests_per_minute": 30,
        "concurrent_requests": 2,
        "retry_backoff_sec": 5,
        "max_retries": 3,
        "queue_depth": 100,
    }
    base.update(overrides)
    return RateLimiterGatekeeperConfig(**base)  # type: ignore[arg-type]
