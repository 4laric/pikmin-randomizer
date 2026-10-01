"""inst-misc lane identity wiring for 26/27/66/97/84/93 (#871).

Proves the proxy->identity cutover for the misc family lane:
Catfish 26 + Tadpole 27 -> aquatic, Hana 84 -> ground_inverts,
BombOtakara 93 -> dweevil, Houdai 66 -> long_legs, FminiHoudai 97 ->
cannon_projectile. Each maps in IDENTITY_FAMILY (id + lowercase enum),
each wires an EXTRACTORS entry + ENUM_FOR_SOURCE entry, and none remains
in randomizer/p2_proxy (import fails closed on coexistence).

Hermetic: no ISO reads, no retail assets.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

EXPECTED = {
    26: ("Catfish", "aquatic", "extract_catfish"),
    27: ("Tadpole", "aquatic", "extract_tadpole"),
    84: ("Hana", "ground_inverts", "extract_hana"),
    93: ("BombOtakara", "dweevil", "extract_bombotakara"),
    66: ("Houdai", "long_legs", "extract_houdai"),
    97: ("FminiHoudai", "cannon_projectile", "extract_fminihoudai"),
}


def test_inst_misc_identity_families():
    from experimental.pikmin2_family_install import resolve_family

    for sid, (enum, family, _ext) in EXPECTED.items():
        assert resolve_family(sid) == family
        assert resolve_family(enum) == family
        assert resolve_family(enum.lower()) == family


def test_inst_misc_extractor_wiring():
    from scripts import p2_prepare_content as prepare

    for sid, (enum, _fam, ext) in EXPECTED.items():
        assert prepare.ENUM_FOR_SOURCE[sid] == enum
        assert prepare.EXTRACTORS[sid] == ext
        assert hasattr(prepare, ext)


def test_inst_misc_proxies_removed():
    from randomizer.p2_proxy import load_rows

    by_id = {row["source_id"] for row in load_rows()}
    for sid, (enum, _fam, _ext) in EXPECTED.items():
        assert sid not in by_id
        assert not (ROOT / "randomizer" / "p2_proxy" / f"{sid}_{enum}.json").exists()
