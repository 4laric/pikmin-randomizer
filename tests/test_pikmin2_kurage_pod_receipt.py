"""Tests for the lane-29 natural Kurage carcass -> Pod receipt validator (#243)."""
from experimental import pikmin2_kurage_pod_receipt as pod


def _sample():
    return pod.default_sample_log().splitlines()


def test_default_sample_log_validates_pass():
    result = pod.validate_pod_receipt(_sample())
    assert result["ok"] is True
    assert result["generator"] == 201001
    assert result["missing"] == []
    assert result["max_carriers"] >= 8
    assert result["max_moved"] > 400.0


def test_receipt_parsed():
    receipt = pod.parse_receipt(_sample())
    assert receipt == {"generator": 201001, "value": 2, "new": 1, "pokos": 2, "seeds": 0}


def test_strip_receipt_flips_fail():
    lines = [line for line in _sample() if "P2_POD_RECEIPT" not in line]
    result = pod.validate_pod_receipt(lines)
    assert result["ok"] is False
    assert result["receipt"] is None
    assert "[Pikipelago] P2_POD_RECEIPT id=corpse:kurage:" in result["missing"]


def test_injected_health_zero_flips_fail():
    lines = _sample() + ["P2_KURAGE_DEAD_CORPSE_RECEIPT_PASS generator=201001 injected=health_zero"]
    result = pod.validate_pod_receipt(lines)
    assert result["ok"] is False
    assert any("injected=health_zero" in item for item in result["missing"])


def test_no_movement_flips_fail():
    lines = [line for line in _sample()
             if not line.startswith("P2_KURAGE_TEKI_CORPSE tick=")]
    lines.append("P2_KURAGE_TEKI_CORPSE tick=30 x=1.0 z=1.0 moved=0.000 carriers=0")
    result = pod.validate_pod_receipt(lines)
    assert result["ok"] is False
    assert any("never moved" in item for item in result["missing"])
    assert any("no TransportMode carrier" in item for item in result["missing"])


def test_missing_dead_marker_flips_fail():
    lines = [line for line in _sample() if not line.startswith("P2_KURAGE_TEKI_DEAD")]
    result = pod.validate_pod_receipt(lines)
    assert result["ok"] is False
    assert "P2_KURAGE_TEKI_DEAD generator=" in result["missing"]


def test_native_helper_graceful_without_env(monkeypatch):
    monkeypatch.delenv("PIKMIN_NATIVE_ROOT", raising=False)
    assert pod.native_pod_chain_present() in (None, False)


def test_native_helper_graceful_with_fake_dir(monkeypatch, tmp_path):
    (tmp_path / "pc_port").mkdir(exist_ok=True)
    monkeypatch.setenv("PIKMIN_NATIVE_ROOT", str(tmp_path))
    assert pod.native_pod_chain_present() is False
