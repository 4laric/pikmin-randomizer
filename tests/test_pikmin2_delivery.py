"""Ordinary delivery receiver: identity disjointness, exactly-once, reconcile."""
import pytest

from experimental.pikmin2_delivery import (DeliveryReceiver, p1_proxy_identity,
                                           p2_source_identity)
from experimental.pikmin2_receipts import (SCHEMA_VERSION, InMemoryPersistence,
                                           JsonReceiptPersistence, ReceiptLedger, reconcile)


def receiver_for(ledger):
    return DeliveryReceiver(ledger)


def ordinary_descriptor(identity, family='lane-13-bulborbs', drop='corpse', ledger='onion'):
    return {'version': SCHEMA_VERSION, 'identity': identity, 'family': family,
            'drop': drop, 'ledger': ledger}


def test_p2_identity_never_collides_with_p1_proxy():
    assert p2_source_identity(45, 1) != p1_proxy_identity(3, 1)
    assert p2_source_identity(3, 1) != p1_proxy_identity(3, 1)
    for teki_type, source_id, stage in ((3, 45, 1), (0, 0, 1), (7, 7, 2)):
        p1 = p1_proxy_identity(teki_type, stage)
        p2 = p2_source_identity(source_id, stage)
        assert p1.startswith('corpse:p1:')
        assert p2.startswith('corpse:p2:')
        assert p1 != p2


def test_identity_and_slot_or_actor():
    receiver = receiver_for(ReceiptLedger(InMemoryPersistence()))
    assert receiver.identity(45, 3, 1) == 'corpse:p2:45:1'
    assert receiver.identity(0, 3, 1) == 'corpse:p1:3:1'
    assert receiver.slot_or_actor(77) == 'g77'


def test_exactly_once_grant_within_single_ledger():
    receiver = receiver_for(ReceiptLedger(InMemoryPersistence()))
    assert receiver.deliver('seed-a', 45, 3, 1, 77, 'tutorial_1:floor1') is True
    assert receiver.deliver('seed-a', 45, 3, 1, 77, 'tutorial_1:floor1') is False
    assert receiver.delivered('seed-a', 45, 3, 1, 77, 'tutorial_1:floor1') is True
    assert receiver.deliver('seed-a', 45, 3, 1, 78, 'tutorial_1:floor1') is True


def test_exactly_once_across_process_restart(tmp_path):
    path = tmp_path / 'receipts.json'
    ledger = ReceiptLedger(JsonReceiptPersistence(path))
    receiver = receiver_for(ledger)
    assert receiver.deliver('seed-a', 45, 3, 1, 77, 'tutorial_1:floor1') is True

    restarted = ReceiptLedger(JsonReceiptPersistence(path))
    receiver2 = receiver_for(restarted)
    assert receiver2.deliver('seed-a', 45, 3, 1, 77, 'tutorial_1:floor1') is False
    assert receiver2.delivered('seed-a', 45, 3, 1, 77, 'tutorial_1:floor1') is True
    assert receiver2.deliver('seed-a', 45, 3, 1, 78, 'tutorial_1:floor1') is True


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
