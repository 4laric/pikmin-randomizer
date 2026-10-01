"""Fuefuki natural-combat run-log reader verdict contract."""
import pytest

from experimental.pikmin2_fuefuki_combat_receipt import parse


def canonical_log():
    return '\n'.join([
        'P2_FUEFUKI_COMBAT_RT_WINDOW size=960x540 centered=1',
        'P2_FUEFUKI_COMBAT_RT_READY state=7 press_count=0',
        'P2_FUEFUKI_COMBAT_RT_STAGE frames=10 state=7 held=0',
        'P2_FUEFUKI_COMBAT_RT_PRESS injected=1 press_count=1 state=7 held=1',
        'P2_FUEFUKI_COMBAT_RT_STRUGGLE state=8 held=1',
        'P2_FUEFUKI_COMBAT_RT_DEATH injected=1 state=0 held=1',
        'P2_FUEFUKI_COMBAT_RT_RELEASE released=1 held=0 frames=120',
        'PASS FUEFUKI_COMBAT_RUNTIME',
    ]) + '\n'


def test_canonical_log_verdict():
    verdict = parse(canonical_log())
    assert verdict['window'] is True
    assert verdict['ready'] is True
    assert verdict['receiver_wired'] is True
    assert verdict['struggle'] is True
    assert verdict['death'] is True
    assert verdict['released'] == 1
    assert verdict['held_after'] == 0
    assert verdict['release_ok'] is True
    assert verdict['passed'] is True


def test_truncated_log_missing_press_and_release():
    text = '\n'.join([
        'P2_FUEFUKI_COMBAT_RT_WINDOW size=960x540 centered=1',
        'P2_FUEFUKI_COMBAT_RT_READY state=7 press_count=0',
        'P2_FUEFUKI_COMBAT_RT_STAGE frames=10 state=7 held=0',
        'P2_FUEFUKI_COMBAT_RT_STRUGGLE state=8 held=1',
        'P2_FUEFUKI_COMBAT_RT_DEATH injected=1 state=0 held=1',
    ]) + '\n'
    verdict = parse(text)
    assert verdict['window'] is True
    assert verdict['ready'] is True
    assert verdict['receiver_wired'] is False
    assert verdict['death'] is True
    assert verdict['released'] == -1
    assert verdict['held_after'] == -1
    assert verdict['release_ok'] is False
    assert verdict['passed'] is False


def test_release_held_positive_is_not_ok():
    text = '\n'.join([
        'P2_FUEFUKI_COMBAT_RT_WINDOW size=960x540 centered=1',
        'P2_FUEFUKI_COMBAT_RT_READY state=7 press_count=0',
        'P2_FUEFUKI_COMBAT_RT_PRESS injected=1 press_count=1 state=7 held=1',
        'P2_FUEFUKI_COMBAT_RT_STRUGGLE state=8 held=1',
        'P2_FUEFUKI_COMBAT_RT_DEATH injected=1 state=0 held=1',
        'P2_FUEFUKI_COMBAT_RT_RELEASE released=1 held=1 frames=120',
        'PASS FUEFUKI_COMBAT_RUNTIME',
    ]) + '\n'
    verdict = parse(text)
    assert verdict['death'] is True
    assert verdict['released'] == 1
    assert verdict['held_after'] == 1
    assert verdict['release_ok'] is False
    assert verdict['passed'] is True
