"""Focused tests for the last daylight/receipt/cache discovery (#151)."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experimental import pikmin2_last_daylight_receipt_cache_discovery as disc  # noqa: E402

RESEARCH = Path("C:/Users/alari/pikmin-randomizer/native/pikmin2-research")


def test_research_pins_verified():
    findings = disc.verify_research(RESEARCH)
    assert set(findings) == {"sunset_day_driver", "receipt_ledger_endpoint", "generator_cache_restore"}
    assert all(f["ok"] for f in findings.values())


def test_missing_research_root_refused(tmp_path):
    with pytest.raises(disc.DiscoveryRejected):
        disc.verify_research(tmp_path / "nope")


def test_missing_port_tree_refused(tmp_path):
    with pytest.raises(disc.DiscoveryRejected):
        disc.check_port(tmp_path)


def test_absent_port_tree_reports_absent(tmp_path):
    port = tmp_path / "pc_port"
    port.mkdir()
    (port / "empty.cpp").write_text("int main(){return 0;}\n")
    results = disc.check_port(tmp_path)
    assert all(v["present"] is False for v in results.values())


def test_present_marker_detected(tmp_path):
    port = tmp_path / "pc_port"
    port.mkdir()
    (port / "x.cpp").write_text("void SunsetDriver(){}\n")
    results = disc.check_port(tmp_path)
    assert results["sunset_day_driver"]["present"] is True
    assert results["receipt_ledger_endpoint"]["present"] is False


def test_registry_has_three_items_and_no_save_serializer():
    reg = disc.build_registry(RESEARCH, Path("C:/Users/alari/pikmin-randomizer/output/native-mar29-repair631"))
    assert set(reg["items"]) == {"sunset_day_driver", "receipt_ledger_endpoint", "generator_cache_restore"}
    assert "736" in reg["save_serializer"] and "not re-derived" in reg["save_serializer"]
    assert "save_serializer" not in reg["items"]


def test_registry_contracts_present():
    reg = disc.build_registry(RESEARCH, Path("C:/Users/alari/pikmin-randomizer/output/native-mar29-repair631"))
    assert "186" in reg["items"]["sunset_day_driver"]["contract"]
    assert "606" in reg["items"]["receipt_ledger_endpoint"]["contract"]
    assert "607" in reg["items"]["generator_cache_restore"]["contract"]


def test_consumer_command_and_behavior():
    reg = disc.build_registry(RESEARCH, Path("C:/Users/alari/pikmin-randomizer/output/native-mar29-repair631"))
    cmd = reg["items"]["sunset_day_driver"]["consumer"]["command"]
    assert "run_pikmin2_fixture" in cmd
    assert set(reg["items"]["sunset_day_driver"]["consumer"]["expected"]) == {"boot", "day", "save", "receipt", "exit"}


def test_emit_registry(tmp_path):
    result = disc.emit_registry(RESEARCH, Path("C:/Users/alari/pikmin-randomizer/output/native-mar29-repair631"), tmp_path)
    assert Path(result["registry"]).is_file()
    assert json.loads(Path(result["registry"]).read_text())["schema"] == disc.SCHEMA


def test_no_overwrite(tmp_path):
    disc.emit_registry(RESEARCH, Path("C:/Users/alari/pikmin-randomizer/output/native-mar29-repair631"), tmp_path)
    with pytest.raises(disc.DiscoveryRejected):
        disc.emit_registry(RESEARCH, Path("C:/Users/alari/pikmin-randomizer/output/native-mar29-repair631"), tmp_path)


def test_gates_untested():
    reg = disc.build_registry(RESEARCH, Path("C:/Users/alari/pikmin-randomizer/output/native-mar29-repair631"))
    assert "UNTESTED" in reg["gates"]


def test_module_is_stdlib_only():
    src = (ROOT / "experimental" / "pikmin2_last_daylight_receipt_cache_discovery.py").read_text()
    assert "import numpy" not in src and "import requests" not in src

def test_cargo_ledger_does_not_count_as_surface_endpoint(tmp_path):
    port = tmp_path / "pc_port"
    port.mkdir()
    (port / "cargo.h").write_text("enum class Ledger { Onion, Ap, Pod };\nstruct ReceiptLedger {};\n")
    results = disc.check_port(tmp_path)
    assert results["receipt_ledger_endpoint"]["present"] is False
