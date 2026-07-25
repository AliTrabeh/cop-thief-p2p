"""Unit tests for infra/hardware_declaration.py — book §5.5 "Step-0 and
Computational Fairness", Appendix E item 24.
"""

from __future__ import annotations

from police_thief.infra.hardware_declaration import collect_hardware_spec


def test_collect_hardware_spec_returns_all_expected_keys():
    spec = collect_hardware_spec()
    assert set(spec) == {"os", "cpu_cores", "ram_mb", "gpu"}


def test_collect_hardware_spec_never_raises_and_has_a_real_os_string():
    spec = collect_hardware_spec()
    assert isinstance(spec["os"], str) and spec["os"]


def test_collect_hardware_spec_cpu_cores_is_a_positive_int_on_this_machine():
    spec = collect_hardware_spec()
    assert isinstance(spec["cpu_cores"], int)
    assert spec["cpu_cores"] >= 1


def test_collect_hardware_spec_gpu_is_explicitly_not_applicable():
    spec = collect_hardware_spec()
    assert spec["gpu"] == "not applicable (no GPU compute used)"


def test_collect_hardware_spec_ram_is_an_int_or_gracefully_none():
    spec = collect_hardware_spec()
    assert spec["ram_mb"] is None or isinstance(spec["ram_mb"], int)
