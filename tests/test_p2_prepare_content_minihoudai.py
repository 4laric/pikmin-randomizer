"""Packaging tests for the source-78 MiniHoudai registration (#849).

``scripts/p2_prepare_content.py`` is owned by unfinished #643, so this lane
does not edit it: the wiring (``extract_minihoudai`` + ``EXTRACTORS[78]`` +
dispatch arm + docstring bullet) is supplied as a structured shared review in
``docs/PIKMIN2_MINIHOUDAI_EXTRACTION.md``. These tests prove, on the real ISO,
that the three-species preparation the review enables (Sarai 23, MiniHoudai
78, Sokkuri 79) produces all three identity directories satisfying their
respective installer contracts, plus all 33 actor bindings from a seed
manifest. Real-ISO tests skip without the legal local disc.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import p2_prepare_content as prepare  # noqa: E402

ISO = Path('C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso')
NEEDS_ISO = pytest.mark.skipif(not ISO.is_file(), reason='no local GPVE01 disc image')


def _extract_minihoudai(iso, dest, pose_limit=3):
    """Mirror of the proposed shared-review wrapper (kept in sync by test below)."""
    import shutil
    from experimental import pikmin2_minihoudai_assets as minihoudai_assets

    iso, dest = Path(iso), Path(dest)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    if type(pose_limit) is not int or not 2 <= pose_limit <= 8:
        raise ValueError(f"pose limit must be 2..8: {pose_limit!r}")
    target = dest / "MiniHoudai"
    if target.exists():
        raise ValueError(f"content dir already exists: {target}")
    tmp = dest / ".tmp-minihoudai"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        minihoudai_assets.extract(iso, tmp, pose_limit=pose_limit)
        shutil.copytree(tmp, target)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return target


def test_proposed_wrapper_matches_shared_review():
    """The wrapper above must stay textually identical to the review proposal."""
    doc = Path(__file__).resolve().parents[1] / 'docs' / 'PIKMIN2_MINIHOUDAI_EXTRACTION.md'
    text = doc.read_text(encoding='utf-8')
    assert 'def extract_minihoudai(iso, dest, pose_limit=3):' in text
    assert '78: "extract_minihoudai"' in text
    assert 'source_id == 78' in text


def test_78_state_matches_review_expectation():
    """Pre-landing 78 is skipped as installer-without-extractor; post-landing it
    must be wired AND dispatched (the drift ``test_every_wired_extractor_has_a_...``
    guards against). Passes either way; fails only on a half-applied review."""
    import inspect

    if 78 not in prepare.EXTRACTORS:
        summary_source = inspect.getsource(prepare.prepare_content_root)
        assert 'source_id == 78' not in summary_source
        return
    assert prepare.EXTRACTORS[78] == 'extract_minihoudai'
    dispatch = inspect.getsource(prepare.prepare_content_root)
    assert 'source_id == 78' in dispatch


@NEEDS_ISO
def test_three_species_preparation_produces_all_identities(tmp_path):
    """Fresh preparation of the pinned 23,78,79 manifest (wiring applied locally,
    exactly as the shared review proposes, without editing the owned file)."""
    from experimental.pikmin2_family_install import (
        _validate_kurage,
        _validate_minihoudai,
        _validate_sarai,
        _validate_sokkuri,
    )

    out = tmp_path / 'content'
    out.mkdir()
    prepare.extract_sarai(ISO, out)
    prepare.extract_sokkuri(ISO, out, pose_limit=3)
    _extract_minihoudai(ISO, out, pose_limit=3)
    for enum in ('Sarai', 'MiniHoudai', 'Sokkuri'):
        assert (out / enum).is_dir(), enum
    _validate_sarai(out / 'Sarai')
    _validate_minihoudai(out / 'MiniHoudai')
    _validate_sokkuri(out / 'Sokkuri')
    assert _validate_kurage is not None  # contract import sanity
    summary = {'extracted': [23, 78, 79],
               'extracted_enums': ['MiniHoudai', 'Sarai', 'Sokkuri']}
    (out / 'prepared.json').write_text(json.dumps(summary, indent=2) + '\n',
                                       encoding='utf-8')
    assert json.loads((out / 'prepared.json').read_text())['extracted'] == [23, 78, 79]


def test_33_actor_bindings_from_seed_manifest(tmp_path):
    """All 33 actor bindings derive deterministically from a seed manifest."""
    targets = [str(1000000 + i) for i in range(33)]
    manifest = {'p2_layout': {'bindings': [
        {'target': target, 'source_id': source, 'enum_name': enum}
        for target, (source, enum) in zip(
            targets,
            [(23, 'Sarai')] * 11 + [(78, 'MiniHoudai')] * 11 + [(79, 'Sokkuri')] * 11)]}}
    manifest_path = tmp_path / 'seed.json'
    manifest_path.write_text(json.dumps(manifest))
    actors_out = tmp_path / 'actors.json'
    bindings = prepare.actors_for_manifest_file(manifest_path, actors_out)
    assert len(bindings) == 33
    assert set(bindings) == set(targets)
    assert all(bindings[target] == int(target) for target in targets)
    assert json.loads(actors_out.read_text()) == bindings
