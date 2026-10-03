from collections import Counter
from types import SimpleNamespace

import pytest

from randomizer.cave_campaign import CAPABILITY, LOCATION_NAMES, produce, location_ids
from randomizer.catalog import active_names, can_reach_manifest, FLARLIC, BLUE, YELLOW
from randomizer.runner import NativeRun, native_bootstrap
from randomizer.seed import generate, validate, fingerprint, solo_rewards, spheres
from randomizer.session import Session


def manifest(**options):
    return generate('production-cave-930', p2_enemies=True, p2_checks=True,
                    generated_cave=True, **options)


def test_opt_in_appends_stable_checks_without_renumbering():
    old = generate('production-cave-930', p2_enemies=True, p2_checks=True)
    new = manifest()
    assert active_names(new) == active_names(old) + LOCATION_NAMES
    assert {n: new['locations'][n] for n in old['locations']} == old['locations']
    assert new['generated_cave'] == produce(new['seed'], new['slot'])
    assert 'generated_cave' not in old and CAPABILITY not in old['capabilities']
    assert len(set(new['locations'].values())) == len(new['locations'])
    assert sum(map(len, spheres(solo_rewards(new), new))) == len(active_names(new))


@pytest.mark.parametrize('path,value', [
    (('native_seed',), 1), (('native_token',), '0' * 32),
    (('identity', 'retail_source'), 'tutorial_1'),
    (('checks', 0, 'host'), 'forest_1:f1:leaf:1'),
    (('entry_supply', 'minimum_live_bodies'), 0),
])
def test_contract_rejects_foreign_or_incomplete_data(path, value):
    m = manifest(); target = m['generated_cave']
    for key in path[:-1]: target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValueError): validate(m)


def test_capability_and_indices_are_seed_bound():
    m = manifest(); m['capabilities'].remove(CAPABILITY)
    with pytest.raises(ValueError): validate(m)
    m = manifest(); m['locations'][LOCATION_NAMES[0]] += 10
    with pytest.raises(ValueError): validate(m)
    with pytest.raises(ValueError): location_ids({LOCATION_NAMES[0]: 1})
    with pytest.raises(ValueError): generate('bad', generated_cave=True)


def test_capacity_does_not_supply_bodies_or_onion_access():
    m = manifest(); stock = Counter({FLARLIC: 100})
    assert not can_reach_manifest(LOCATION_NAMES[0], stock, m)
    stock.update({BLUE: 1, YELLOW: 1})
    assert can_reach_manifest(LOCATION_NAMES[0], stock, m)
    assert m['generated_cave']['entry_supply']['minimum_live_bodies'] == 2


def test_native_handshake_duplicate_journal_and_fresh_host_recovery(tmp_path):
    m = manifest(p2_second_captain=True)
    session = Session(m, tmp_path)
    run = NativeRun(session)
    body = run.bootstrap.read_text()
    assert body.index('CAPTAINS 2') < body.index('CAVE_CHECKS')
    assert body.endswith('\nEND\n')
    indices = [str(session.names.index(n)) for n in LOCATION_NAMES]
    (run.directory / 'checks.txt').write_text('\n'.join(indices + indices) + '\n')
    run.poll()
    assert not session.data['checked']
    (run.directory / 'hello.txt').write_text(' '.join([
        'PIKMIN_HELLO', str(m['schema']), run.token, session.fingerprint,
        *m['capabilities'], 'END']))
    run.poll()
    assert set(session.data['checked']) == set(LOCATION_NAMES)
    recovered = Session(m, tmp_path)
    assert recovered.data['checked'] == session.data['checked']
    run.bootstrap.write_text(body.replace(m['generated_cave']['native_token'], '0' * 32))
    with pytest.raises(ValueError, match='generated cave contract'):
        Session(m, tmp_path)


def test_old_bootstrap_stays_byte_identical_without_option():
    m = generate('production-cave-930', p2_enemies=True, p2_checks=True)
    session = SimpleNamespace(manifest=m, fingerprint=fingerprint(m), death_link_unit=0)
    assert 'CAVE_CHECKS' not in native_bootstrap(session, 'a' * 64)


def test_ap_manifest_has_identical_placement_identity_and_stable_ids():
    solo = manifest(); ap = manifest(mode='ap')
    assert ap['generated_cave'] == solo['generated_cave']
    assert ap['locations'] == solo['locations']
    validate(ap)
