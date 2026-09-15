"""Ordinary delivery receiver: identity disjointness, exactly-once, reconcile."""
import pytest

from experimental.pikmin2_delivery import (DeliveryReceiver, p1_proxy_identity,
                                           p2_source_identity)
from experimental.pikmin2_receipts import (SCHEMA_VERSION, InMemoryPersistence,
                                           JsonReceiptPersistence, ReceiptLedger, reconcile)
from experimental.pikmin2_reward_lifecycle import validate


def receiver_for(ledger):
    return DeliveryReceiver(ledger)


def ordinary_descriptor(identity, family='lane-13-bulborbs', drop='corpse', ledger='onion'):
    return {'version': SCHEMA_VERSION, 'identity': identity, 'family': family,
            'drop': drop, 'ledger': ledger}


def test_p2_identity_never_collides_with_p1_proxy():
    assert p1_proxy_identity(3, 1).startswith('onion:p1:')
    assert p2_source_identity(45, 1).startswith('onion:p2:')
    assert p2_source_identity(45, 1) == 'onion:p2:45:1'
    assert p1_proxy_identity(3, 1) == 'onion:p1:3:1'
    assert p2_source_identity(45, 1) != p1_proxy_identity(3, 1)
    assert p2_source_identity(3, 1) != p1_proxy_identity(3, 1)
    for teki_type, source_id, stage in ((3, 45, 1), (0, 0, 1), (7, 7, 2)):
        p1 = p1_proxy_identity(teki_type, stage)
        p2 = p2_source_identity(source_id, stage)
        assert p1.startswith('onion:p1:')
        assert p2.startswith('onion:p2:')
        assert p1 != p2


def test_identity_and_slot_or_actor():
    receiver = receiver_for(ReceiptLedger(InMemoryPersistence()))
    assert receiver.identity(45, 3, 1, p1_proxy=False) == 'onion:p2:45:1'
    assert receiver.identity(0, 3, 1, p1_proxy=True) == 'onion:p1:3:1'
    assert receiver.slot_or_actor(77) == 'g77'


def test_p2_path_requires_bound_source_id():
    receiver = receiver_for(ReceiptLedger(InMemoryPersistence()))
    with pytest.raises(ValueError):
        receiver.identity(0, 3, 1, p1_proxy=False)
    with pytest.raises(ValueError):
        receiver.deliver('seed-a', 0, 3, 1, 77, 'tutorial_1:floor1', p1_proxy=False)


def test_exactly_once_grant_within_single_ledger():
    receiver = receiver_for(ReceiptLedger(InMemoryPersistence()))
    assert receiver.deliver('seed-a', 45, 3, 1, 77, 'tutorial_1:floor1', p1_proxy=False) is True
    assert receiver.deliver('seed-a', 45, 3, 1, 77, 'tutorial_1:floor1', p1_proxy=False) is False
    assert receiver.delivered('seed-a', 45, 3, 1, 77, 'tutorial_1:floor1', p1_proxy=False) is True
    assert receiver.deliver('seed-a', 45, 3, 1, 78, 'tutorial_1:floor1', p1_proxy=False) is True


def test_exactly_once_across_process_restart(tmp_path):
    path = tmp_path / 'receipts.json'
    ledger = ReceiptLedger(JsonReceiptPersistence(path))
    receiver = receiver_for(ledger)
    assert receiver.deliver('seed-a', 45, 3, 1, 77, 'tutorial_1:floor1', p1_proxy=False) is True

    restarted = ReceiptLedger(JsonReceiptPersistence(path))
    receiver2 = receiver_for(restarted)
    assert receiver2.deliver('seed-a', 45, 3, 1, 77, 'tutorial_1:floor1', p1_proxy=False) is False
    assert receiver2.delivered('seed-a', 45, 3, 1, 77, 'tutorial_1:floor1', p1_proxy=False) is True
    assert receiver2.deliver('seed-a', 45, 3, 1, 78, 'tutorial_1:floor1', p1_proxy=False) is True


def test_mixed_dump_pod_and_ordinary_count_correctly():
    text = '\n'.join([
        'P2_POD_RECEIPT id=corpse:385875968 value=2 new=1 pokos=2',
        'P2_POD_RECEIPT id=onion:p2:45:1 value=1 new=1 pokos=0',
        'P2_POD_RECEIPT id=onion:p1:3:1 value=1 new=1 pokos=0',
        'P2_POD_RECEIPT id=corpse:385875968 value=2 new=0 pokos=2',
    ])
    result = validate(text, 0)
    checks = result['checks']
    assert len(result['receipts']) == 4
    assert checks['corpse_receipts'] is True
    assert checks['first_new'] is True
    assert checks['second_duplicate'] is True
    assert checks['pokos_stable'] is True
    assert checks['value_is_2'] is True
    corpse = [r for r in result['receipts'] if r[0].startswith('corpse:')]
    assert len(corpse) == 2
    assert 'onion:p2:45:1' not in [r[0] for r in corpse]


def test_reconcile_integration_ok(tmp_path):
    desc44 = ordinary_descriptor(p2_source_identity(44, 1))
    desc45 = ordinary_descriptor(p2_source_identity(45, 1))
    report = reconcile([desc44, desc45],
                       [p2_source_identity(44, 1), p2_source_identity(45, 1)])
    assert report['ok'] is True
    assert report['missing_sources'] == []
    assert report['pod_leaks'] == []


def test_reconcile_refuses_pod_leak_covering_expected_check(tmp_path):
    desc44 = ordinary_descriptor(p2_source_identity(44, 1))
    pod45 = ordinary_descriptor(p2_source_identity(45, 1), ledger='pod')
    with pytest.raises(ValueError):
        reconcile([desc44, pod45],
                  [p2_source_identity(44, 1), p2_source_identity(45, 1)])
