"""Lane 16 Frog/MaroFrog corpse-reward consumer tests (#167/#201)."""
import pytest

from experimental import pikmin2_frog_behavior as behavior
from experimental import pikmin2_frog_rewards as rewards
from experimental import pikmin2_receipts as receipts


def test_descriptors_use_the_shared_schema():
    descriptors = rewards.descriptors()
    by_identity = {d['identity']: d for d in descriptors}
    assert set(by_identity) == {'enemy:17', 'enemy:18'}
    assert by_identity['enemy:17'] == {
        'version': receipts.SCHEMA_VERSION, 'identity': 'enemy:17', 'family': 'frog',
        'drop': 'corpse', 'ledger': receipts.LEDGER_ONION, 'value': 5, 'count': 1}
    assert by_identity['enemy:18'] == {
        'version': receipts.SCHEMA_VERSION, 'identity': 'enemy:18', 'family': 'frog',
        'drop': 'corpse', 'ledger': receipts.LEDGER_ONION, 'value': 7, 'count': 1}
    assert rewards.FAMILY == 'frog' and rewards.SPECIES == {'Frog': 17, 'MaroFrog': 18}


def test_identity_maps_species_names_and_source_ids():
    assert rewards.identity('Frog') == 'enemy:17'
    assert rewards.identity('MaroFrog') == 'enemy:18'
    assert rewards.identity(17) == 'enemy:17' and rewards.identity(18) == 'enemy:18'
    with pytest.raises(ValueError, match='Unknown frog species'):
        rewards.identity('Toady')
    with pytest.raises(ValueError, match='Unknown frog source id'):
        rewards.identity(19)


def test_pickup_is_exactly_once_in_process():
    ledger = receipts.ReceiptLedger(receipts.InMemoryPersistence())
    assert rewards.grant_pickup(ledger, 'seed-a', 'enemy:17', '201001', 'floor1') is True
    assert rewards.grant_pickup(ledger, 'seed-a', 'enemy:17', '201001', 'floor1') is False
    assert len(ledger) == 1


def test_pickup_survives_restart_via_json_persistence(tmp_path):
    persistence = receipts.JsonReceiptPersistence(tmp_path / 'receipts.json')
    ledger = receipts.ReceiptLedger(persistence)
    assert rewards.grant_pickup(ledger, 'seed-a', 'enemy:18', '201002', 'floor2') is True
    # A fresh ledger reopened from the same file must not re-grant.
    reopened = receipts.ReceiptLedger(receipts.JsonReceiptPersistence(tmp_path / 'receipts.json'))
    assert rewards.grant_pickup(reopened, 'seed-a', 'enemy:18', '201002', 'floor2') is False
    assert len(reopened) == 1


def test_a_different_seed_grants_again():
    ledger = receipts.ReceiptLedger(receipts.InMemoryPersistence())
    assert rewards.grant_pickup(ledger, 'seed-a', 'enemy:17', '201001', 'floor1') is True
    assert rewards.grant_pickup(ledger, 'seed-b', 'enemy:17', '201001', 'floor1') is True
    assert len(ledger) == 2


def test_revisit_dedupes_the_pickup():
    ledger = receipts.ReceiptLedger(receipts.InMemoryPersistence())
    events = [('enemy:17', '201001', 'floor1'),
              ('enemy:18', '201002', 'floor1'),
              ('enemy:17', '201001', 'floor1')]  # revisit of the same actor/encounter
    assert rewards.resolve_pickups(ledger, 'seed-a', events) == ['enemy:17', 'enemy:18']


def test_unknown_identity_is_rejected():
    ledger = receipts.ReceiptLedger(receipts.InMemoryPersistence())
    for bad in ('enemy:19', 'alias:17', 'helper:17', 'Frog'):
        with pytest.raises(ValueError, match='Unknown frog reward identity'):
            rewards.grant_pickup(ledger, 'seed-a', bad, 'x', 'floor1')
    assert len(ledger) == 0


def test_carry_route_delegates_to_the_source_behavior_contract():
    route = rewards.carry_route('enemy:17')
    assert route['carry'] == (7, 14) and route['onion'] == (8, 8) and route['pokos'] == 5
    assert rewards.carry_route('enemy:18') == behavior.carry_route('MaroFrog')
    with pytest.raises(ValueError, match='Unknown frog reward identity'):
        rewards.carry_route('enemy:99')


def test_reconcile_covers_the_expected_frog_checks():
    result = rewards.reconcile_runs(['enemy:17', 'enemy:18'])
    assert result['ok'] and result['missing_sources'] == [] and result['pod_leaks'] == []


def test_reconcile_reports_a_missing_source():
    result = rewards.reconcile_runs(['enemy:17', 'enemy:18', 'enemy:103'])
    assert not result['ok'] and result['missing_sources'] == ['enemy:103']


def test_reconcile_refuses_a_pod_leak_for_an_ordinary_check():
    with pytest.raises(ValueError, match='Pod-only reward leaks'):
        receipts.reconcile(
            [{'version': receipts.SCHEMA_VERSION, 'identity': 'enemy:17',
              'family': 'frog', 'drop': 'treasure', 'ledger': receipts.LEDGER_POD,
              'value': 5, 'count': 1}],
            ['enemy:17'])
