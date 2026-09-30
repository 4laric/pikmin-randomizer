"""The native Proom table matches the retail skeleton (#960)."""
from pathlib import Path

import pytest

from scripts import kurage_proom_offsets as proom

CACHE = Path(__file__).resolve().parents[1] / "output" / "p2-content-dense"


def test_header_row_parser():
    text = '{"attack", {0.0f, 6.1f, 0.0f},   {0.0f, 9.2f, 0.0f}},\n{"flick2", {-0.3f, 31.9f, -0.6f}, {-0.4f, 48.3f, -0.9f}},'
    path = Path(__file__).with_name("_proom_tmp.h")
    path.write_text(text)
    try:
        rows = proom.header_rows(path)
    finally:
        path.unlink()
    assert rows["attack"] == ((0.0, 6.1, 0.0), (0.0, 9.2, 0.0))
    assert rows["flick2"][0] == (-0.3, 31.9, -0.6)


@pytest.mark.skipif(not (CACHE / "Kurage" / "enemy.bmd").exists(), reason="no staged Jellyfloat content")
def test_attack_pose_stomach_is_inside_the_squashed_bell():
    lesser = proom.proom_offsets(CACHE, "Kurage")
    greater = proom.proom_offsets(CACHE, "OniKurage")
    assert lesser["attack"][1] == pytest.approx(6.1, abs=0.05)
    assert greater["attack"][1] == pytest.approx(9.2, abs=0.05)
    assert all(v[1] > 0 for v in list(lesser.values()) + list(greater.values()))
