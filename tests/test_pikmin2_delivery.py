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


def test_two_ledgers_on_distinct_paths_do_not_interfere(tmp_path):
    delivery_path = tmp_path / 'p2-delivery-receipts.json'
    flora_path = tmp_path / 'p2-flora-receipts.json'

    delivery = receiver_for(ReceiptLedger(JsonReceiptPersistence(delivery_path)))
    flora = receiver_for(ReceiptLedger(JsonReceiptPersistence(flora_path)))

    assert delivery.identity(3, 3, 1, p1_proxy=False) != flora.identity(4, 3, 1, p1_proxy=False)

    delivery_event = ('seed', 3, 3, 1, 7, 'corpse')
    flora_event = ('seed', 4, 3, 1, 7, 'onion')

    assert delivery.deliver(*delivery_event, p1_proxy=False) is True
    assert flora.deliver(*flora_event, p1_proxy=False) is True

    assert len(delivery.ledger) == 1
    assert len(flora.ledger) == 1

    assert delivery.delivered(*delivery_event, p1_proxy=False) is True
    assert delivery.delivered(*flora_event, p1_proxy=False) is False
    assert flora.delivered(*flora_event, p1_proxy=False) is True
    assert flora.delivered(*delivery_event, p1_proxy=False) is False

    delivery_reopened = receiver_for(ReceiptLedger(JsonReceiptPersistence(delivery_path)))
    flora_reopened = receiver_for(ReceiptLedger(JsonReceiptPersistence(flora_path)))

    assert len(delivery_reopened.ledger) == 1
    assert len(flora_reopened.ledger) == 1
    assert delivery_reopened.delivered(*delivery_event, p1_proxy=False) is True
    assert delivery_reopened.delivered(*flora_event, p1_proxy=False) is False
    assert flora_reopened.delivered(*flora_event, p1_proxy=False) is True
    assert flora_reopened.delivered(*delivery_event, p1_proxy=False) is False


def test_reopen_same_path_reuses_same_ledger_state(tmp_path):
    path = tmp_path / 'receipts.json'
    first = ReceiptLedger(JsonReceiptPersistence(path))
    event = ('seed', 'corpse:5000', 7, 'tutorial_1:floor1')
    assert first.grant(*event) is True

    second = ReceiptLedger(JsonReceiptPersistence(path))
    assert second.has(*event) is True
    assert second.grant(*event) is False
    assert len(second) == 1


def test_ledger_count_accessor_and_independence(tmp_path):
    first_path = tmp_path / 'first-receipts.json'
    second_path = tmp_path / 'second-receipts.json'

    first = receiver_for(ReceiptLedger(JsonReceiptPersistence(first_path)))
    second = receiver_for(ReceiptLedger(JsonReceiptPersistence(second_path)))

    assert first.deliver('seed-a', 45, 3, 1, 77, 'tutorial_1:floor1', p1_proxy=False) is True
    assert first.deliver('seed-a', 46, 3, 1, 78, 'tutorial_1:floor1', p1_proxy=False) is True
    assert second.deliver('seed-b', 45, 3, 1, 77, 'tutorial_1:floor1', p1_proxy=False) is True

    assert len(first.ledger) == 2
    assert len(second.ledger) == 1

    first_reopened = receiver_for(ReceiptLedger(JsonReceiptPersistence(first_path)))
    second_reopened = receiver_for(ReceiptLedger(JsonReceiptPersistence(second_path)))
    assert len(first_reopened.ledger) == 2
    assert len(second_reopened.ledger) == 1


def test_two_paths_pod_vs_onion_vocabulary_do_not_collide():
    pod_identity = 'corpse:385875968'
    for source_id, teki_type, stage in ((45, 3, 1), (385875968, 3, 1), (0, 0, 2), (7, 7, 3)):
        p1 = p1_proxy_identity(teki_type, stage)
        p2 = p2_source_identity(source_id, stage)
        for ident in (p1, p2):
            assert ident != f'corpse:{source_id}'
            assert ident != f'corpse:{teki_type}'
            assert ident != pod_identity
            assert not ident.startswith('corpse:')

    lines = [
        f'P2_POD_RECEIPT id={pod_identity} value=2 new=1 pokos=2',
        f'P2_POD_RECEIPT id={p2_source_identity(45, 1)} value=1 new=1 pokos=0',
        f'P2_POD_RECEIPT id={p1_proxy_identity(3, 1)} value=1 new=1 pokos=0',
        f'P2_POD_RECEIPT id={p2_source_identity(385875968, 1)} value=1 new=1 pokos=0',
    ]
    corpse = [r[0] for r in validate('\n'.join(lines), 0)['receipts']
              if r[0].startswith('corpse:')]
    assert corpse == [pod_identity]


def test_mamuta_pod_receipt_vocabulary_shape_disjoint_from_onion():
    """Vocabulary-shape contract only (no provider/GL/native claim).

    A Mamuta Pod receipt key uses the ``corpse:`` namespace, so it must be
    disjoint from the Onion P1/P2 identity vocabularies produced by
    ``p1_proxy_identity``/``p2_source_identity`` and must be counted as a Pod
    ``corpse:`` row by the real ``validate`` parser. This test only exercises
    those pure helpers; it does not drive a provider, GL, or reference run.
    """
    pod_identity = 'corpse:mamuta:221001'
    assert pod_identity.startswith('corpse:')
    assert not pod_identity.startswith('onion:')
    for source_id, teki_type, stage in ((45, 3, 1), (221001, 24, 1), (0, 0, 2), (7, 7, 3)):
        p1 = p1_proxy_identity(teki_type, stage)
        p2 = p2_source_identity(source_id, stage)
        assert p1.startswith('onion:p1:')
        assert p2.startswith('onion:p2:')
        assert pod_identity != p1
        assert pod_identity != p2
        assert not p1.startswith('corpse:')
        assert not p2.startswith('corpse:')
    result = validate(f'P2_POD_RECEIPT id={pod_identity} value=2 new=1 pokos=2', 0)
    corpse = [r[0] for r in result['receipts'] if r[0].startswith('corpse:')]
    assert corpse == [pod_identity]
