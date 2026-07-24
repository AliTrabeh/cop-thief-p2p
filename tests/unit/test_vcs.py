"""Unit tests for infra/vcs.py — FR-087 (real commit hash in the declaration
JSON). ``subprocess.run`` is monkeypatched throughout; no real git process
dependency is required for correctness here (the real one is exercised
implicitly whenever the test suite itself runs inside this git checkout).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from police_thief.infra import vcs


class _FakeCompleted:
    def __init__(self, returncode: int, stdout: str) -> None:
        self.returncode = returncode
        self.stdout = stdout


def test_current_commit_hash_returns_git_output(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args: object, **kwargs: object) -> _FakeCompleted:
        return _FakeCompleted(returncode=0, stdout="abc123deadbeef\n")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert vcs.current_commit_hash() == "abc123deadbeef"


def test_current_commit_hash_falls_back_when_git_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args: object, **kwargs: object) -> _FakeCompleted:
        raise FileNotFoundError("git not on PATH")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert vcs.current_commit_hash() == vcs.UNKNOWN_COMMIT


def test_current_commit_hash_falls_back_on_nonzero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args: object, **kwargs: object) -> _FakeCompleted:
        return _FakeCompleted(returncode=128, stdout="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert vcs.current_commit_hash() == vcs.UNKNOWN_COMMIT


def test_current_commit_hash_falls_back_on_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args: object, **kwargs: object) -> _FakeCompleted:
        raise subprocess.TimeoutExpired(cmd="git", timeout=5.0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert vcs.current_commit_hash() == vcs.UNKNOWN_COMMIT


def test_current_commit_hash_falls_back_on_blank_output(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args: object, **kwargs: object) -> _FakeCompleted:
        return _FakeCompleted(returncode=0, stdout="   \n")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert vcs.current_commit_hash() == vcs.UNKNOWN_COMMIT


def test_current_commit_hash_against_real_repo() -> None:
    """This test file lives inside the real project checkout, so a real,
    un-mocked call must succeed and return a 40-character hex SHA-1.
    """
    result = vcs.current_commit_hash(Path(__file__).resolve().parents[2])
    assert result != vcs.UNKNOWN_COMMIT
    assert len(result) == 40
    assert all(c in "0123456789abcdef" for c in result)
