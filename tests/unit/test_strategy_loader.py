"""Unit tests for strategy/base.py::load_brain_class — FR-060 (pluggable
strategy loading half, split out of test_strategy.py to keep each file
under 150 lines).
"""

from __future__ import annotations

import pytest

from police_thief.strategy.base import load_brain_class
from police_thief.strategy.heuristic import HeuristicPoliceBrain


def test_load_brain_class_resolves_a_valid_spec():
    cls = load_brain_class("police_thief.strategy.heuristic:HeuristicPoliceBrain")
    assert cls is HeuristicPoliceBrain


def test_load_brain_class_rejects_malformed_spec():
    with pytest.raises(ValueError, match="package.module:Class"):
        load_brain_class("not-a-valid-spec")


def test_load_brain_class_rejects_non_brainbase_class():
    with pytest.raises(TypeError, match="does not subclass BrainBase"):
        load_brain_class("pathlib:Path")


def test_load_brain_class_rejects_unknown_attribute():
    with pytest.raises(ValueError, match="no attribute"):
        load_brain_class("police_thief.strategy.heuristic:NoSuchBrain")
