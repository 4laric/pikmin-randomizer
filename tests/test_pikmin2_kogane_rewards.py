"""Lane 17 finite flip-drop and restart-dedupe tests (#168/#219/#441)."""
import pytest

from experimental import pikmin2_kogane_rewards as rewards
from experimental import pikmin2_receipts as receipts
from experimental.pikmin2_kogane_assets import MAX_FLIPS


def ledger(persistence=None):
    return receipts.ReceiptLedger(persistence or receipts.InMemoryPersistence())


def test_source_drop_table_matches_the_audited_flip_rows():
    assert rewards.flip_drop(9, 1) == ('pellet', 'PELLET_NUMBER_ONE', 1)
    assert rewards.flip_drop(9, 2) == ('doping', 'HONEY_Y', 2)
    assert rewards.flip_drop(9, 3, demo_flag=True) == ('doping', 'HONEY_R', 1)
    assert rewards.flip_drop(9, 3, demo_flag=False) == ('doping', 'HONEY_Y', 3)
    assert rewards.flip_drop(9, 1, in_cave=True) == ('doping', 'HONEY_Y', 1)
    assert rewards.flip_drop(10, 1) == ('pellet', 'PELLET_NUMBER_FIVE', 3)
    assert rewards.flip_drop(11, 1) == ('doping', 'HONEY_Y', 3)
    assert rewards.flip_drop(11, 3, demo_flag=True) == ('doping', 'HONEY_B', 1)
    assert rewards.flip_drop(11, 3, demo_flag=False) == ('doping', 'HONEY_Y', 3)


def test_unknown_ids_and_out_of_range_flips_are_rejected():
    with pytest.raises(ValueError, match='Unknown reward beetle id'):
        rewards.flip_drop(12, 1)
    with pytest.raises(ValueError, match='Flip out of range'):
        rewards.flip_drop(9, 0)
    with pytest.raises(ValueError, match='Flip out of range'):
        rewards.flip_drop(9, MAX_FLIPS + 1)
    with pytest.raises(ValueError, match='Unknown reward beetle id'):
        rewards.identity(99)


def test_three_flips_then_escape_with_finite_counts():
    flips = rewards.BeetleFlips(ledger())
    for flip in (1, 2, 3):
        result = flips.register('seed-a', 9, '219001', flip)
        assert result['granted'] and not result['escaped'] and result['drop'] is not None
    escaped = flips.register('seed-a', 9, '219001', MAX_FLIPS + 1)
    assert escaped == {'flip': 4, 'granted': False, 'escaped': True, 'drop': None}
    assert flips.flips('seed-a', 9, '219001') == MAX_FLIPS
    assert flips.escaped('seed-a', 9, '219001')


def test_replayed_flip_never_drops_twice():
    account = rewards.BeetleFlips(ledger())
    assert account.register('seed-a', 10, '219002', 1)['granted'] is True
    replay = account.register('seed-a', 10, '219002', 1)
    assert replay['granted'] is False and replay['drop'] is None
    assert account.flips('seed-a', 10, '219002') == 1


def test_restart_dedupe_survives_process_reopen(tmp_path):
    path = tmp_path / 'kogane-receipts.json'
    first = rewards.BeetleFlips(ledger(receipts.JsonReceiptPersistence(path)))
    assert first.register('seed-a', 11, '219003', 1)['granted'] is True
    reopened = rewards.BeetleFlips(
        receipts.ReceiptLedger(receipts.JsonReceiptPersistence(path)))
    repeated = reopened.register('seed-a', 11, '219003', 1)
    assert repeated['granted'] is False and repeated['drop'] is None
    assert reopened.flips('seed-a', 11, '219003') == 1
    assert reopened.register('seed-a', 11, '219003', 2)['granted'] is True


def test_collection_is_exactly_once_and_requires_a_registered_flip():
    account = rewards.BeetleFlips(ledger())
    with pytest.raises(ValueError, match='unregistered flip'):
        account.collect('seed-a', 9, '219001', 1)
    account.register('seed-a', 9, '219001', 1)
    assert account.collect('seed-a', 9, '219001', 1) is True
    assert account.collect('seed-a', 9, '219001', 1) is False
    with pytest.raises(ValueError, match='unregistered flip'):
        account.collect('seed-a', 9, '219001', 2)


def test_a_different_seed_grants_again():
    account = rewards.BeetleFlips(ledger())
    assert account.register('seed-a', 9, '219001', 1)['granted'] is True
    assert account.register('seed-b', 9, '219001', 1)['granted'] is True


def test_no_alias_or_helper_identities_are_accepted():
    assert rewards.FAMILY == 'kogane'
    assert set(rewards.ENEMY_IDS) == {9, 10, 11}
    assert rewards.identity(9) == 'enemy:9'


def test_receipts_sidecar_parses_the_native_format():
    assert rewards.RECEIPTS_HEADER == 'P2_KOGANE_RECEIPTS_1'
    text = 'P2_KOGANE_RECEIPTS_1\n219001 3\n219002 1\n'
    assert rewards.parse_receipts(text) == {219001: 3, 219002: 1}
    assert rewards.parse_receipts('P2_KOGANE_RECEIPTS_1\n') == {}
    # the native loader skips blank lines between rows
    assert rewards.parse_receipts('P2_KOGANE_RECEIPTS_1\n\n219003 2\n\n') == {219003: 2}


def test_receipts_sidecar_rejects_drift():
    with pytest.raises(ValueError, match='header'):
        rewards.parse_receipts('P2_KOGANE_RECEIPTS_2\n219001 3\n')
    with pytest.raises(ValueError, match='header'):
        rewards.parse_receipts('219001 3\n')
    for bad in ('219001\n', '219001 3 4\n', '219001 three\n', 'x 1\n'):
        with pytest.raises(ValueError, match='row'):
            rewards.parse_receipts('P2_KOGANE_RECEIPTS_1\n' + bad)
    for bad in ('0 1\n', '219001 0\n', '219001 %d\n' % (MAX_FLIPS + 1)):
        with pytest.raises(ValueError, match='range'):
            rewards.parse_receipts('P2_KOGANE_RECEIPTS_1\n' + bad)
    with pytest.raises(ValueError, match='Duplicate'):
        rewards.parse_receipts('P2_KOGANE_RECEIPTS_1\n219001 2\n219001 1\n')


def test_read_receipts_fails_safe_on_missing_or_malformed_files(tmp_path):
    assert rewards.read_receipts(tmp_path / 'absent.txt') == {}
    (tmp_path / 'bad.txt').write_text('not a receipt ledger\n')
    assert rewards.read_receipts(tmp_path / 'bad.txt') == {}
    good = tmp_path / rewards.RECEIPTS_FILENAME
    good.write_text('P2_KOGANE_RECEIPTS_1\n219002 1\n219001 3\n')
    assert rewards.read_receipts(good) == {219001: 3, 219002: 1}
