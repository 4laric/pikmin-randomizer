"""BigFoot-only sessions need Mitite resources without extra placements."""
import hashlib
import json
import shutil

import pytest

from experimental import pikmin2_family_install as fi
from experimental import pikmin2_tamago_content as tamago
from scripts import p2_smoke_seed as smoke
from scripts import p2_prepare_content as prepare
from tests.test_p2_tamago_content import make_source, make_run


LAYOUT = {'bindings': [{'target': 'boss', 'source_id': 69, 'enum_name': 'BigFoot'}]}


def setup_content(tmp_path, monkeypatch, *, child=True):
    content = tmp_path / 'content'
    (content / 'BigFoot').mkdir(parents=True)
    if child:
        make_source(content / 'TamagoMushi')
    def install(source, run, actors):
        make_run(run)
        (run / 'boss.txt').write_text(str(actors))
        return {'actors': actors}
    monkeypatch.setitem(fi._OVERRIDES, 'long_legs', install)
    return content


def test_bigfoot_only_stages_child_resources_and_replays_cache(tmp_path, monkeypatch):
    content = setup_content(tmp_path, monkeypatch)
    cache = tmp_path / 'cache'
    run = tmp_path / 'run'
    result = fi.install_layout(run, LAYOUT, content, {'boss': 123}, cache_dir=cache)
    assert result['bindings'] == LAYOUT['bindings']
    assert set(result['receipts']) == {'boss'}
    child = result['resource_dependencies']['BigFoot:TamagoMushi']
    assert child['generators'] == []
    assert not (run / 'p2-ground-actors.txt').exists()
    assert 'species TamagoMushi 68' in (run / 'p2-ground-bank.txt').read_text()
    poses = list((run / tamago.ROOM).glob('ginv_TamagoMushi_*.mod'))
    assert poses and all(p.read_bytes() for p in poses)
    canonical = {'bindings': LAYOUT['bindings'], 'actor_bindings': {'boss': 123}}
    old_digest = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    assert result['plan_digest'] != old_digest
    shutil.rmtree(content)
    replay = fi.install_layout(tmp_path / 'replay', LAYOUT, content, {'boss': 123}, cache_dir=cache)
    assert replay['cached']
    for relative, digest in result['files'].items():
        assert hashlib.sha256((tmp_path / 'replay' / relative).read_bytes()).hexdigest() == digest


@pytest.mark.parametrize('bad', ['missing', 'hash'])
def test_child_content_failure_precedes_run_mutation(tmp_path, monkeypatch, bad):
    content = setup_content(tmp_path, monkeypatch, child=bad != 'missing')
    if bad == 'hash':
        next((content / 'TamagoMushi').glob('*.mod')).write_bytes(b'wrong')
    run = tmp_path / 'run'
    with pytest.raises(fi.StagingError):
        fi.install_layout(run, LAYOUT, content, {'boss': 123})
    assert not run.exists()


def test_resource_staging_preserves_real_mitite_actor_rows(tmp_path):
    source = make_source(tmp_path / 'source')
    run = make_run(tmp_path / 'run')
    tamago.stage_tamago_ground(source, run, [(456, 'TamagoMushi')])
    before = {p.name: p.read_bytes() for p in run.iterdir() if p.is_file()}
    receipt = tamago.stage_bigfoot_children(source, run)
    assert receipt['generators'] == []
    assert before == {p.name: p.read_bytes() for p in run.iterdir() if p.is_file()}


def test_smoke_content_prepares_child_without_editing_layout(tmp_path):
    manifest = {'p2_layout': LAYOUT}
    seen = []
    def prepare(iso, out, wanted):
        seen.extend(wanted)
        for enum in ('BigFoot', 'TamagoMushi'):
            (out / enum).mkdir()
            (out / enum / 'content.bin').write_bytes(b'private fixture')
        return {'extracted_enums': ['BigFoot', 'TamagoMushi']}
    result = smoke.stage_content(manifest, tmp_path / 'content', None, 'test.iso', prepare_fn=prepare)
    assert seen == [68, 69]
    assert result['needed'] == {'68': 'TamagoMushi', '69': 'BigFoot'}
    assert manifest == {'p2_layout': LAYOUT}


def test_extract_bigfoot_includes_child_once(tmp_path, monkeypatch):
    iso = tmp_path / 'test.iso'
    iso.write_bytes(b'fixture')
    calls = []
    def extract(enum):
        def run(iso, dest, **kwargs):
            calls.append(enum)
            (dest / enum).mkdir()
        return run
    monkeypatch.setattr(prepare, 'extract_bigfoot', extract('BigFoot'))
    monkeypatch.setattr(prepare, 'extract_tamago', extract('TamagoMushi'))
    prepare.prepare_content_root(iso, tmp_path / 'out', wanted=[69])
    assert sorted(calls) == ['BigFoot', 'TamagoMushi']
    calls.clear()
    prepare.prepare_content_root(iso, tmp_path / 'out2', wanted=[69, 68])
    assert sorted(calls) == ['BigFoot', 'TamagoMushi']
