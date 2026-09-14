"""Lane 18 reward-receipt consumer tests against the lane-06 shared schema."""
import pytest

from experimental import pikmin2_breadbug_rewards as rewards
from experimental import pikmin2_breadbug_contest as contest
from experimental import pikmin2_receipts as receipts


def test_descriptors_use_the_shared_schema_and_exclude_helpers():
    descriptors = rewards.descriptors()
    by_identity = {d['identity']: d for d in descriptors}
    assert set(by_identity) == {rewards.SMALL, rewards.GIANT}
    assert by_identity[rewards.SMALL] == {
        'version': receipts.SCHEMA_VERSION, 'identity': rewards.SMALL, 'family': 'breadbug',
        'drop': 'pellet', 'ledger': receipts.LEDGER_ONION, 'value': 1, 'count': 1}
    assert by_identity[rewards.GIANT]['ledger'] == receipts.LEDGER_AP
    for helper in rewards.HELPERS:
        assert helper not in by_identity


def test_defeat_is_exactly_once_in_process():
    ledger = receipts.ReceiptLedger(receipts.InMemoryPersistence())
    assert rewards.grant_defeat(ledger, 'seed-a', rewards.GIANT, '187001', 'floor1') is True
    assert rewards.grant_defeat(ledger, 'seed-a', rewards.GIANT, '187001', 'floor1') is False
    assert len(ledger) == 1


def test_defeat_survives_restart_via_json_persistence(tmp_path):
    persistence = receipts.JsonReceiptPersistence(tmp_path / 'receipts.json')
    ledger = receipts.ReceiptLedger(persistence)
    assert rewards.grant_defeat(ledger, 'seed-a', rewards.SMALL, '186081', 'floor2') is True
    # A fresh ledger reopened from the same file must not re-grant.
    reopened = receipts.ReceiptLedger(receipts.JsonReceiptPersistence(tmp_path / 'receipts.json'))
    assert rewards.grant_defeat(reopened, 'seed-a', rewards.SMALL, '186081', 'floor2') is False
    assert len(reopened) == 1


def test_a_different_seed_grants_again():
    ledger = receipts.ReceiptLedger(receipts.InMemoryPersistence())
    assert rewards.grant_defeat(ledger, 'seed-a', rewards.GIANT, '187001', 'floor1') is True
    assert rewards.grant_defeat(ledger, 'seed-b', rewards.GIANT, '187001', 'floor1') is True
    assert len(ledger) == 2


def test_revisit_releases_cargo_once_with_no_duplicate_reward():
    ledger = receipts.ReceiptLedger(receipts.InMemoryPersistence())
    encounters = [(rewards.SMALL, '186081', 'floor2'),
                  (rewards.GIANT, '187001', 'floor2'),
                  (rewards.SMALL, '186081', 'floor2')]  # revisit of the same actor/encounter
    assert rewards.resolve_encounters(ledger, 'seed-a', encounters) == [rewards.SMALL, rewards.GIANT]


def test_helpers_and_aliases_never_earn_rewards():
    ledger = receipts.ReceiptLedger(receipts.InMemoryPersistence())
    for helper in rewards.HELPERS:
        with pytest.raises(ValueError, match='never earn'):
            rewards.grant_defeat(ledger, 'seed-a', helper, '187002', 'floor2')


def test_unknown_identity_is_rejected():
    ledger = receipts.ReceiptLedger(receipts.InMemoryPersistence())
    with pytest.raises(ValueError, match='Unknown breadbug reward identity'):
        rewards.grant_defeat(ledger, 'seed-a', 'enemy:99', 'x', 'floor1')


def test_reconcile_covers_the_expected_breadbug_checks():
    result = rewards.reconcile_runs([rewards.SMALL, rewards.GIANT])
    assert result['ok'] and result['missing_sources'] == [] and result['pod_leaks'] == []


def test_reconcile_reports_missing_source():
    result = rewards.reconcile_runs([rewards.SMALL, rewards.GIANT, 'enemy:103'])
    assert not result['ok'] and result['missing_sources'] == ['enemy:103']


def test_reconcile_refuses_a_pod_leak_for_an_ordinary_check():
    with pytest.raises(ValueError, match='Pod-only reward leaks'):
        receipts.reconcile(
            [{'version': receipts.SCHEMA_VERSION, 'identity': rewards.GIANT,
              'family': 'breadbug', 'drop': 'treasure', 'ledger': receipts.LEDGER_POD,
              'value': 1, 'count': 1}],
            [rewards.GIANT])


def test_interruption_and_digest_never_grant_a_reward():
    ledger = receipts.ReceiptLedger(receipts.InMemoryPersistence())
    for reason in (contest.DROP, contest.RECOVER, contest.DIGEST, contest.EAT):
        result = rewards.resolve_contest(ledger, 'seed-a', rewards.GIANT, '187001',
                                         'floor1', reason, held_slots=1)
        assert result['granted'] is False and result['returned'] == 0
    assert len(ledger) == 0


def test_death_recovery_grants_once_and_returns_held_treasure():
    ledger = receipts.ReceiptLedger(receipts.InMemoryPersistence())
    first = rewards.resolve_contest(ledger, 'seed-a', rewards.GIANT, '187001',
                                    'floor1', rewards.DEATH, held_slots=3)
    assert first['granted'] is True and first['returned'] == 3
    assert first['held'] == 3
    second = rewards.resolve_contest(ledger, 'seed-a', rewards.GIANT, '187001',
                                     'floor1', rewards.DEATH, held_slots=3)
    assert second['granted'] is False
    assert len(ledger) == 1


def test_unknown_cargo_outcome_is_rejected():
    ledger = receipts.ReceiptLedger(receipts.InMemoryPersistence())
    with pytest.raises(ValueError, match='Unknown cargo outcome'):
        rewards.resolve_contest(ledger, 'seed-a', rewards.GIANT, '187001', 'floor1', 'explode')


def test_helpers_never_earn_a_reward_on_death():
    ledger = receipts.ReceiptLedger(receipts.InMemoryPersistence())
    with pytest.raises(ValueError, match='never earn'):
        rewards.resolve_contest(ledger, 'seed-a', rewards.PANHOUSE, '187002',
                                'floor1', rewards.DEATH)
