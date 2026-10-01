"""Catfish (26) identity wiring (inst-misc lane, #871).

Proves the proxy->identity cutover for Water Dumple:
- ``IDENTITY_FAMILY`` maps 26/'catfish' to the shared aquatic installer;
- ``p2_prepare_content`` wires ``EXTRACTORS[26] == 'extract_catfish'`` and
  ``ENUM_FOR_SOURCE[26] == 'Catfish'``;
- the proxy declaration ``randomizer/p2_proxy/26_Catfish.json`` is gone, so
  ``load_rows()`` carries no 26 and the import-time collision guard
  (``_proxy_family_entries``) cannot fire for it.

Hermetic: no ISO reads, no retail assets.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_catfish_identity_family():
    from experimental.pikmin2_family_install import resolve_family

    assert resolve_family(26) == "aquatic"
    assert resolve_family("Catfish") == "aquatic"
    assert resolve_family("catfish") == "aquatic"


def test_catfish_extractor_wiring():
    from scripts import p2_prepare_content as prepare

    assert prepare.ENUM_FOR_SOURCE[26] == "Catfish"
    assert prepare.EXTRACTORS[26] == "extract_catfish"
    assert hasattr(prepare, "extract_catfish")


def test_catfish_proxy_removed():
    from randomizer.p2_proxy import load_rows

    assert not any(row["source_id"] == 26 for row in load_rows())
    assert not (ROOT / "randomizer" / "p2_proxy" / "26_Catfish.json").exists()
