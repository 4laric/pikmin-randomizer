"""Lane 29 Jellyfloat reward consumer tests (#243)."""
import pytest

from experimental import pikmin2_kurage_rewards as rewards
from experimental import pikmin2_receipts as receipts


def test_descriptors_use_the_shared_schema():
    descriptors = rewards.descriptors()
    by_identity = {d['identity']: d for d in descriptors}
    assert set(by_identity) == {'enemy:57', 'enemy:72'}
    assert by_identity['enemy:57'] == {
        'version': receipts.SCHEMA_VERSION, 'identity': 'enemy:57', 'family': 'jellyfloat',
        'drop': 'pellet', 'ledger': receipts.LEDGER_ONION, 'value': None, 'count': 1}
    assert by_identity['enemy:72'] == {
        'version': receipts.SCHEMA_VERSION, 'identity': 'enemy:72', 'family': 'jellyfloat',
        'drop': 'pellet', 'ledger': receipts.LEDGER_ONION, 'value': None, 'count': 1}
    assert rewards.FAMILY == 'jellyfloat'
    assert rewards.SPECIES == {'Kurage': 57, 'OniKurage': 72}
    assert rewards.DROP_TYPE == {'Kurage': 'BDT_Normal', 'OniKurage': 'BDT_Strong'}


def test_identity_maps_species_names_and_source_ids():
    assert rewards.identity('Kurage') == 'enemy:57'
    assert rewards.identity('OniKurage') == 'enemy:72'
    assert rewards.identity(57) == 'enemy:57' and rewards.identity(72) == 'enemy:72'
    with pytest.raises(ValueError, match='Unknown Jellyfloat species'):
        rewards.identity('Demon')
    with pytest.raises(ValueError, match='Unknown Jellyfloat source id'):
        rewards.identity(73)


def test_pickup_is_exactly_once_in_process():
    ledger = receipts.ReceiptLedger(receipts.InMemoryPersistence())
    assert rewards.grant_pickup(ledger, 'seed-a', 'enemy:57', '201001', 'floor1') is True
    assert rewards.grant_pickup(ledger, 'seed-a', 'enemy:57', '201001', 'floor1') is False
    assert len(ledger) == 1


def test_pickup_survives_restart_via_json_persistence(tmp_path):
    persistence = receipts.JsonReceiptPersistence(tmp_path / 'receipts.json')
    ledger = receipts.ReceiptLedger(persistence)
    assert rewards.grant_pickup(ledger, 'seed-a', 'enemy:72', '201002', 'floor2') is True
    reopened = receipts.ReceiptLedger(receipts.JsonReceiptPersistence(tmp_path / 'receipts.json'))
    assert rewards.grant_pickup(reopened, 'seed-a', 'enemy:72', '201002', 'floor2') is False
    assert len(reopened) == 1


def test_a_different_seed_grants_again():
    ledger = receipts.ReceiptLedger(receipts.InMemoryPersistence())
    assert rewards.grant_pickup(ledger, 'seed-a', 'enemy:57', '201001', 'floor1') is True
    assert rewards.grant_pickup(ledger, 'seed-b', 'enemy:57', '201001', 'floor1') is True
    assert len(ledger) == 2


def test_revisit_dedupes_the_pickup():
    ledger = receipts.ReceiptLedger(receipts.InMemoryPersistence())
    events = [('enemy:57', '201001', 'floor1'),
              ('enemy:72', '201002', 'floor1'),
              ('enemy:57', '201001', 'floor1')]
    assert rewards.resolve_pickups(ledger, 'seed-a', events) == ['enemy:57', 'enemy:72']


def test_unknown_identity_is_rejected():
    ledger = receipts.ReceiptLedger(receipts.InMemoryPersistence())
    for bad in ('enemy:73', 'alias:57', 'helper:57', 'Kurage', 'enemy:16'):
        with pytest.raises(ValueError, match='Unknown Jellyfloat reward identity'):
            rewards.grant_pickup(ledger, 'seed-a', bad, 'x', 'floor1')
    assert len(ledger) == 0


def test_reconcile_covers_the_expected_jellyfloat_checks():
    result = rewards.reconcile_runs(['enemy:57', 'enemy:72'])
    assert result['ok'] and result['missing_sources'] == [] and result['pod_leaks'] == []


def test_reconcile_reports_a_missing_source():
    result = rewards.reconcile_runs(['enemy:57', 'enemy:72', 'enemy:103'])
    assert not result['ok'] and result['missing_sources'] == ['enemy:103']


def test_reconcile_refuses_a_pod_leak_for_an_ordinary_check():
    with pytest.raises(ValueError, match='Pod-only reward leaks'):
        receipts.reconcile(
            [{'version': receipts.SCHEMA_VERSION, 'identity': 'enemy:57',
              'family': 'jellyfloat', 'drop': 'treasure', 'ledger': receipts.LEDGER_POD,
              'value': 5, 'count': 1}],
            ['enemy:57'])
