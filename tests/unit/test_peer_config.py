"""Unit tests for config.py — NFR-005, TEST-001 (peer game.toml half, split
out of test_config.py to keep each file under 150 lines).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from _config_fixtures import VALID_PEER_TOML

from police_thief.config import ConfigError, load_peer_config


def test_load_peer_config_round_trips_the_books_own_example(tmp_path: Path):
    path = tmp_path / "game.toml"
    path.write_text(VALID_PEER_TOML, encoding="utf-8")
    cfg = load_peer_config(path)
    assert cfg.game.group_name == "My-Team"
    assert cfg.network.my_port == 8802
    assert cfg.llm.model == "template"
    assert cfg.email.mode == "draft"


def test_load_peer_config_missing_file_raises_config_error(tmp_path: Path):
    with pytest.raises(ConfigError, match="not found"):
        load_peer_config(tmp_path / "nope.toml")


def test_load_peer_config_invalid_toml_raises_config_error(tmp_path: Path):
    path = tmp_path / "game.toml"
    path.write_text("not = [valid toml", encoding="utf-8")
    with pytest.raises(ConfigError, match="not valid TOML"):
        load_peer_config(path)


def test_load_peer_config_missing_required_field_raises_config_error(tmp_path: Path):
    path = tmp_path / "game.toml"
    path.write_text(
        'version = "1.0"\n[network]\nmy_port = 1\nopponent_url = "x"\n', encoding="utf-8"
    )
    with pytest.raises(ConfigError, match="failed validation"):
        load_peer_config(path)


def test_load_peer_config_rejects_unknown_field(tmp_path: Path):
    path = tmp_path / "game.toml"
    path.write_text(VALID_PEER_TOML + "\nnot_a_real_field = 1\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="failed validation"):
        load_peer_config(path)


def test_load_peer_config_rejects_unknown_nested_field(tmp_path: Path):
    tampered = VALID_PEER_TOML.replace("my_port = 8802", "my_port = 8802\nmyport_typo = 1")
    path = tmp_path / "game.toml"
    path.write_text(tampered, encoding="utf-8")
    with pytest.raises(ConfigError, match="failed validation"):
        load_peer_config(path)
