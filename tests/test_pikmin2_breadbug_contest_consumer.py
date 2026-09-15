"""Lane 18 small-Breadbug P2 cargo-contest consumer tests (#220)."""
import pytest

from experimental import pikmin2_breadbug_contest as contest


GOOD_LOG = (
    'P2_BREADBUG_CONTEST_BEGIN generator=186081 identity=onion:p2:38:0 max=2\n'
    'P2_BREADBUG_CONTEST_UPDATE generator=186081 carriers=1 outcome=held\n'
    'P2_BREADBUG_CONTEST_UPDATE generator=186081 carriers=2 outcome=stolen\n'
    'P2_BREADBUG_CONTEST_STOLEN generator=186081 carriers=2 released=1\n'
    'P2_BREADBUG_CONTEST_GRANT generator=186081 identity=onion:p2:38:0 granted=1\n'
    'P2_BREADBUG_REVISIT generator=186081 rearmed=1\n'
    'P2_BREADBUG_CONTEST_BEGIN generator=186081 identity=onion:p2:38:0 max=2\n'
    'P2_BREADBUG_CONTEST_UPDATE generator=186081 carriers=2 outcome=stolen\n'
    'P2_BREADBUG_CONTEST_STOLEN generator=186081 carriers=2 released=1\n'
    'P2_BREADBUG_CONTEST_GRANT generator=186081 identity=onion:p2:38:0 granted=0 duplicate=1\n'
    'P2_BREADBUG_OWNER_DIED generator=186081 released=1 reason=OwnerDied\n'
    'PASS P2_BREADBUG_CONTEST\n'
)


def test_small_contest_config_matches_the_consumer_spec():
    config = contest.small_contest_config(186081)
    assert config['identity'] == 'onion:p2:38:0'
    assert config['source_token'] == 'nest:186081'
    assert config['min_threshold'] == 1
    assert config['max_threshold'] == 2
    assert config['freeze_seconds'] == 0.5
    assert config['required_carriers'] == 1
    assert config['max_carriers'] == 0
    # A copy is returned so callers cannot mutate the shared table.
    config['min_threshold'] = 99
    assert contest.SMALL_CONTEST_CONFIG['min_threshold'] == 1
    with pytest.raises(ValueError, match='must be an int'):
        contest.small_contest_config('186081')
    with pytest.raises(ValueError, match='out of range'):
        contest.small_contest_config(-1)
    with pytest.raises(ValueError, match='out of range'):
        contest.small_contest_config(contest.MAX_GENERATOR_ID + 1)


def test_mirror_one_carrier_holds_and_two_carriers_steal():
    mirror = contest.SmallContestMirror(186081)
    assert mirror.begin() == contest.OUTCOME_HELD
    assert mirror.outcome == 'held'
    assert mirror.update(0.0, ['a']) == 'held'
    assert mirror.update(0.1, ['a']) == 'held'
    assert mirror.update(0.2, ['a', 'b']) == 'stolen'
    assert mirror.outcome == 'stolen'


def test_mirror_zero_carriers_times_out_after_the_freeze():
    mirror = contest.SmallContestMirror(1)
    mirror.begin()
    assert mirror.update(0.0, []) == 'held'
    assert mirror.update(0.4, []) == 'held'
    assert mirror.update(0.5, []) == 'released'
    assert mirror.reason == 'timeout'


def test_mirror_interrupt_and_owner_died_release_but_stolen_is_sticky():
    interrupted = contest.SmallContestMirror(1)
    interrupted.begin()
    assert interrupted.interrupt() == 'released'
    assert interrupted.reason == 'interrupted'

    dead = contest.SmallContestMirror(1)
    dead.begin()
    assert dead.on_owner_died() == 'released'
    assert dead.reason == 'owner_died'

    revisited = contest.SmallContestMirror(1)
    revisited.begin()
    assert revisited.on_revisit() == 'released'
    assert revisited.reason == 'revisit'

    sticky = contest.SmallContestMirror(1)
    sticky.begin()
    sticky.update(0.0, ['a', 'b'])
    assert sticky.outcome == 'stolen'
    assert sticky.interrupt() == 'stolen'
    assert sticky.on_owner_died() == 'stolen'
    assert sticky.on_revisit() == 'stolen'
    assert sticky.reset() == 'stolen'
    assert sticky.outcome == 'stolen'


def test_mirror_reset_releases_with_the_revisit_reason():
    mirror = contest.SmallContestMirror(1)
    mirror.begin()
    assert mirror.reset() == 'released'
    assert mirror.reason == 'revisit'


def test_mirror_grant_receipt_is_exactly_once_and_requires_a_steal():
    stolen = contest.SmallContestMirror(1)
    stolen.begin()
    stolen.update(0.0, ['a', 'b'])
    assert stolen.grant_receipt() is True
    assert stolen.grant_receipt() is False
    # A distinct receipt key deduplicates independently.
    assert stolen.grant_receipt('other-encounter') is True

    held = contest.SmallContestMirror(1)
    held.begin()
    held.update(0.0, ['a'])
    with pytest.raises(ValueError, match='stolen'):
        held.grant_receipt()


def test_mirror_rejects_malformed_carriers():
    mirror = contest.SmallContestMirror(1)
    mirror.begin()
    with pytest.raises(ValueError, match='list or tuple'):
        mirror.update(0.0, 'abc')
    with pytest.raises(ValueError, match='must be a string'):
        mirror.update(0.0, [1, 2])


def test_parser_records_the_observed_consumer_events():
    events = contest.parse_contest_consumer(GOOD_LOG, 186081)
    assert events['began'] is True
    assert events['held'] is True
    assert events['stolen'] is True
    assert events['released'] is True
    assert events['granted'] is True
    assert events['grants'] == 1
    assert events['grant_duplicate'] is True
    assert events['owner_died'] is True
    assert events['owner_died_released'] is True
    assert events['revisit'] is True
    assert events['update_outcomes'] == ['held', 'stolen', 'stolen']
    assert events['pass_marker'] is True


def test_parser_ignores_markers_for_other_generators():
    events = contest.parse_contest_consumer(GOOD_LOG, 999999)
    assert events['began'] is False
    assert events['held'] is False
    assert events['stolen'] is False


def test_validator_passes_a_complete_consumer_run():
    events = contest.parse_contest_consumer(GOOD_LOG, 186081)
    result = contest.validate_contest_consumer(events)
    assert result['passed'] is True
    assert result['checks']['gate_began'] is True
    assert result['checks']['gate_held_then_stolen_released_granted'] is True
    assert result['checks']['gate_owner_died_released'] is True
    assert result['checks']['gate_grant_exactly_once'] is True


def test_validator_fails_on_a_missing_gate():
    missing_owner = GOOD_LOG.replace(
        'P2_BREADBUG_OWNER_DIED generator=186081 released=1 reason=OwnerDied\n', '')
    events = contest.parse_contest_consumer(missing_owner, 186081)
    result = contest.validate_contest_consumer(events)
    assert result['passed'] is False
    assert result['checks']['gate_owner_died_released'] is False
    assert result['checks']['gate_began'] is True


def test_validator_requires_the_revisit_duplicate_for_exactly_once():
    # Exactly-once is proven by exactly one grant AND one refused re-grant
    # (the revisit duplicate). Without the duplicate marker, gate_grant fails.
    events = contest.parse_contest_consumer(GOOD_LOG, 186081)
    assert events['grants'] == 1
    assert events['grant_duplicate'] is True
    result = contest.validate_contest_consumer(events)
    assert result['checks']['gate_grant_exactly_once'] is True

    no_revisit_duplicate = GOOD_LOG.replace(
        'P2_BREADBUG_CONTEST_GRANT generator=186081 identity=onion:p2:38:0 granted=0 duplicate=1\n', '')
    events = contest.parse_contest_consumer(no_revisit_duplicate, 186081)
    result = contest.validate_contest_consumer(events)
    assert result['passed'] is False
    assert result['checks']['gate_grant_exactly_once'] is False


def test_validator_rejects_an_empty_observation():
    assert contest.validate_contest_consumer({})['passed'] is False
