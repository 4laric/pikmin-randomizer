"""Tests for the Chappy own-identity wiring (inst-chappy, #871).

Covers the family-installer registration (IDENTITY_FAMILY row, validator,
adapter), the ``p2_prepare_content`` extractor wiring, and the proxy-row
removal for Chappy (source 2): a proxy declaration and an identity row must
never coexist, and ``install_layout`` must stage the identity sidecars for
a Chappy binding.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experimental.pikmin2_staging import StagingError  # noqa: E402
import experimental.pikmin2_family_install as family  # noqa: E402
import scripts.p2_prepare_content as prepare  # noqa: E402
from test_p2_chappy_content import make_run, make_source  # noqa: E402


def test_identity_family_routes_chappy():
    assert family.resolve_family(2) == "chappy"
    assert family.resolve_family("Chappy") == "chappy"
    assert family.resolve_family("chappy") == "chappy"


def test_no_proxy_row_coexists_with_identity():
    from randomizer.p2_proxy import load_rows

    ids = {row["source_id"] for row in load_rows()}
    enums = {row["enum_name"] for row in load_rows()}
    assert 2 not in ids
    assert "Chappy" not in enums


def test_prepare_wiring_for_chappy():
    assert prepare.ENUM_FOR_SOURCE[2] == "Chappy"
    assert prepare.EXTRACTORS[2] == "extract_chappy"
    assert 2 not in prepare.PROXY_SOURCE_IDS


def test_extract_chappy_rejects_unknown_species(tmp_path):
    iso = tmp_path / "game.iso"
    iso.write_bytes(b"fake")
    with pytest.raises(ValueError, match="not a Chappy-family species"):
        prepare.extract_chappy(iso, tmp_path / "out", 99)


def make_retail(root):
    retail = root / "retail"
    (retail / "dataDir" / "stages").mkdir(parents=True)
    return retail


def test_install_layout_stages_chappy_identity(tmp_path):
    content = tmp_path / "content"
    make_source(content / "Chappy")
    run = tmp_path / "run"
    layout = {"bindings": [{"target": "219002", "source_id": 2, "enum_name": "Chappy"}]}
    receipt = family.install_layout(run, layout, content,
                                    actor_bindings={"219002": 219002},
                                    retail_assets=make_retail(tmp_path))
    assert "Chappy" in receipt["receipts"]["219002"]["species"]
    assert (run / "p2-chappy-actors.txt").read_text(encoding="ascii") == \
        "P2_CHAPPY_ACTORS_1\n1\n219002 Chappy\n"
    assert (run / "p2-chappy-bank.txt").read_text(encoding="ascii").splitlines()[0] == \
        "P2_CHAPPY_BANK_1"


def test_install_layout_rejects_chappy_enum_disagreement(tmp_path):
    content = tmp_path / "content"
    make_source(content / "Chappy")
    run = tmp_path / "run"
    layout = {"bindings": [{"target": "219002", "source_id": 33, "enum_name": "Chappy"}]}
    with pytest.raises(StagingError, match="disagrees"):
        family.install_layout(run, layout, content,
                              actor_bindings={"219002": 219002},
                              retail_assets=make_retail(tmp_path))
