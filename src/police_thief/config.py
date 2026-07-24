"""Loads and validates ``config/game.json`` (shared, signed) and
``config/<role>/game.toml`` (private per peer) — docs/protocol.md §5-6.

This module does the file I/O the ``domain`` package deliberately avoids
(NFR-001); it hands validated, typed objects to the rest of the app. Every
failure raises :class:`ConfigError` with a clear message — never a bare
``KeyError``/``FileNotFoundError`` leaking to a CLI user (working
instructions, "Explicit validation").
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from police_thief.domain.crypto import hash_state
from police_thief.domain.models import GameConfig


class ConfigError(Exception):
    """Raised for any config file loading or validation failure."""


def _canonical_json_text(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def load_game_config(path: Path) -> GameConfig:
    """Load and validate the shared ``config/game.json`` file (NFR-005)."""
    if not path.exists():
        raise ConfigError(f"shared config file not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"shared config file is not valid JSON: {path}: {exc}") from exc
    try:
        return GameConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"shared config file failed validation: {path}: {exc}") from exc


def shared_config_hash(path: Path) -> str:
    """SHA-256 of the canonicalized shared config (NFR-008): both peers must
    compute the same hash from their own copy of ``config/game.json`` before
    a game starts, proving byte-identical rules without trusting each other.
    """
    if not path.exists():
        raise ConfigError(f"shared config file not found: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return hash_state(_canonical_json_text(raw))


class PeerGameIdentity(BaseModel):
    group_name: str
    group_id: str
    sub_game_number: int = 1
    members: list[str] = Field(default_factory=list)
    repos: dict[str, str] = Field(default_factory=dict)


class PeerNetworkConfig(BaseModel):
    my_port: int
    opponent_url: str
    turn_timeout_seconds: int = 180


class PeerTunnelConfig(BaseModel):
    """Not part of the book's own worked config example -- an extension this
    project adds for FR-006 (tunneling). Defaults to ``"none"`` (localhost
    only), so existing configs keep working unchanged.
    """

    provider: str = "none"  # "none" | "ngrok" | "manual"
    manual_public_url: str = ""  # only used when provider == "manual" (e.g. Localtonet)


class PeerStrategyConfig(BaseModel):
    thief_class: str | None = None
    police_class: str | None = None


class PeerTrashTalkConfig(BaseModel):
    provider: str = "template"


class PeerLLMConfig(BaseModel):
    model: str = "template"
    step_deadline_seconds: int = 30


class PeerEmailConfig(BaseModel):
    recipient: str
    mode: str = "draft"


class PeerConfig(BaseModel):
    """Mirrors ``config/<role>/game.toml`` exactly (docs/protocol.md §6)."""

    version: str
    game: PeerGameIdentity
    network: PeerNetworkConfig
    tunnel: PeerTunnelConfig = Field(default_factory=PeerTunnelConfig)
    strategy: PeerStrategyConfig = Field(default_factory=PeerStrategyConfig)
    trash_talk: PeerTrashTalkConfig = Field(default_factory=PeerTrashTalkConfig)
    llm: PeerLLMConfig = Field(default_factory=PeerLLMConfig)
    email: PeerEmailConfig


def load_peer_config(path: Path) -> PeerConfig:
    """Load and validate a peer's private ``game.toml`` file."""
    if not path.exists():
        raise ConfigError(f"private config file not found: {path}")
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"private config file is not valid TOML: {path}: {exc}") from exc
    try:
        return PeerConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"private config file failed validation: {path}: {exc}") from exc
