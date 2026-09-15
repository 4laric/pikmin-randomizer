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


def test_carried_treasure_standin_overrides_only_the_first_flip():
    # The native host has no P2 treasure item, so a configured number-pellet value
    # stands in for the cave first-flip treasure (createTreasureItem).
    assert rewards.flip_drop(9, 1, carried_treasure=5) == 5
    assert rewards.flip_drop(10, 1, carried_treasure=1) == 1
    assert rewards.flip_drop(9, 2, carried_treasure=5) == rewards.flip_drop(9, 2)
    assert rewards.flip_drop(11, 3, carried_treasure=1) == rewards.flip_drop(11, 3)


def test_register_carried_treasure_suppresses_the_table_on_the_first_flip():
    account = rewards.BeetleFlips(ledger())
    first = account.register('seed-a', 9, '219001', 1, carried_treasure=5)
    assert first['granted'] is True and first['drop'] == 5
    second = account.register('seed-a', 9, '219001', 2, carried_treasure=5)
    assert second['granted'] is True and second['drop'] == rewards.flip_drop(9, 2)


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


# Native sidecar -> lane-06 ledger bridge (#168/#219/#441).
SIDECAR = 'P2_KOGANE_RECEIPTS_1\n219001 3\n219002 1\n'


def test_reconcile_native_grants_each_sidecar_flip_once():
    account = ledger()
    result = rewards.reconcile_native(SIDECAR, account, 'seed-a')
    assert set(result['granted']) == {
        ('seed-a', 'enemy:9', '219001', 'flip1'),
        ('seed-a', 'enemy:9', '219001', 'flip2'),
        ('seed-a', 'enemy:9', '219001', 'flip3'),
        ('seed-a', 'enemy:10', '219002', 'flip1')}
    assert result['summary'] == {'rows': 2, 'generators': ['219001', '219002'],
                                 'receipts': 4, 'granted': 4, 'already_present': 0}
    assert len(account) == 4


def test_reconcile_native_reopen_does_not_double_grant(tmp_path):
    path = tmp_path / 'kogane-receipts.json'
    first = receipts.ReceiptLedger(receipts.JsonReceiptPersistence(path))
    assert rewards.reconcile_native(SIDECAR, first, 'seed-a')['summary']['granted'] == 4
    reopened = receipts.ReceiptLedger(receipts.JsonReceiptPersistence(path))
    again = rewards.reconcile_native(SIDECAR, reopened, 'seed-a')
    assert again['granted'] == ()
    assert again['summary']['already_present'] == 4
    assert len(reopened) == 4


def test_reconcile_native_a_different_seed_grants_again():
    account = ledger()
    rewards.reconcile_native(SIDECAR, account, 'seed-a')
    again = rewards.reconcile_native(SIDECAR, account, 'seed-b')
    assert again['summary']['granted'] == 4
    assert len(account) == 8


def test_reconcile_native_rejects_a_malformed_sidecar(tmp_path):
    for text in ('P2_KOGANE_RECEIPTS_2\n219001 3\n',
                 'P2_KOGANE_RECEIPTS_1\n219001 9\n',
                 'P2_KOGANE_RECEIPTS_1\n219001 2\n219001 1\n'):
        with pytest.raises(ValueError):
            rewards.reconcile_native(text, ledger(), 'seed-a')
    malformed = tmp_path / 'bad.txt'
    malformed.write_text('219001 3\n')
    with pytest.raises(ValueError, match='header'):
        rewards.reconcile_native(malformed, ledger(), 'seed-a')


def test_reconcile_native_missing_file_grants_nothing(tmp_path):
    result = rewards.reconcile_native(tmp_path / 'absent.txt', ledger(), 'seed-a')
    assert result == {'granted': (), 'summary': {'rows': 0, 'generators': [],
                                                 'receipts': 0, 'granted': 0,
                                                 'already_present': 0}}


def test_reconcile_native_handles_an_unknown_generator_explicitly():
    text = 'P2_KOGANE_RECEIPTS_1\n219099 2\n'
    with pytest.raises(ValueError, match='Unknown reward beetle generator: 219099'):
        rewards.reconcile_native(text, ledger(), 'seed-a')
    account = ledger()
    mapped = rewards.reconcile_native(text, account, 'seed-a', generator_to_enemy={219099: 9})
    assert mapped['summary']['granted'] == 2
    with pytest.raises(ValueError, match='Unknown reward beetle id'):
        rewards.reconcile_native(text, ledger(), 'seed-a', generator_to_enemy={219099: 12})


def test_sync_receipts_round_trips_without_regranting(tmp_path):
    path = tmp_path / rewards.RECEIPTS_FILENAME
    account = ledger()
    rewards.reconcile_native(SIDECAR, account, 'seed-a')
    assert rewards.sync_receipts(path, account, 'seed-a') == {219001: 3, 219002: 1}
    assert rewards.read_receipts(path) == {219001: 3, 219002: 1}
    again = rewards.reconcile_native(path, account, 'seed-a')
    assert again['granted'] == ()
    assert again['summary']['already_present'] == 4


def test_write_receipts_matches_the_native_format_and_validates_rows(tmp_path):
    path = tmp_path / 'out.txt'
    text = rewards.write_receipts(path, {219002: 1, 219001: 3})
    assert text == 'P2_KOGANE_RECEIPTS_1\n219001 3\n219002 1\n'
    assert path.read_text() == text
    with pytest.raises(ValueError, match='flip count'):
        rewards.write_receipts(path, {219001: MAX_FLIPS + 1})
    with pytest.raises(ValueError, match='generator id'):
        rewards.write_receipts(path, {0: 1})
