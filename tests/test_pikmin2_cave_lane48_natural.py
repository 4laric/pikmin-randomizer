"""Focused tests for the lane-48 cave natural-acquisition validator.

These tests use synthetic marker text only. They never touch the native engine,
a real cave run, a Candypop bud or a GL fixture.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from experimental.pikmin2_cave_lane48_natural import (
    MISSING,
    MOCKED,
    NATURAL,
    STAGED,
    evaluate,
    main,
)

BUD_YELLOW = (
    "P2_CAVE_BUD_ACTOR slot=forest_1:f1:bud:0 colour=yellow segment=0 count=5 "
    "x=120.0 y=0.0 z=48.0 spawned=1"
)
ACCEPT_YELLOW = (
    "P2_CAVE_BUD_ACCEPT slot=forest_1:f1:bud:0 colour=yellow thrown_colour=1 used=1 budget=5"
)
SPROUT_YELLOW = (
    "P2_CAVE_BUD_SPROUT slot=forest_1:f1:bud:0 colour=yellow colour_index=2 plucked=1 natural=1"
)
DONE_YELLOW = (
    "P2_CAVE_BUD_DONE slot=forest_1:f1:bud:0 colour=yellow used=1 refunds=0 conversions=1"
)
# Lane 23's actor markers remain valid aliases.
POM_ACCEPT_YELLOW = (
    "P2_POM_ACCEPT generator=100 species=YellowPom thrown_colour=2 used=1 budget=5"
)
POM_SPROUT_YELLOW = (
    "P2_POM_SPROUT generator=100 species=YellowPom count=5 colour=2 body=1 leaf=1"
)
GRANT_YELLOW_NATURAL = (
    "P2_CAVE_ROOMS_GRANT species=yellow natural_acquire=1 staged=0"
)
GRANT_YELLOW_STAGED = "P2_CAVE_ROOMS_GRANT species=yellow natural_acquire=0 staged=1"
TIMELINE_ELEC = (
    "P2_CAVE_ROOMS_TIMELINE tag=come_back_with_yellow hole=0 "
    "treasure_elec=1 treasure_water=0 untagged=0"
)

NATURAL_YELLOW = "\n".join([
    BUD_YELLOW,
    ACCEPT_YELLOW,
    SPROUT_YELLOW,
    DONE_YELLOW,
    GRANT_YELLOW_NATURAL,
])


def test_genuine_natural_yellow_is_natural():
    result = evaluate(NATURAL_YELLOW)
    assert result["classification"] == NATURAL
    assert result["pass"] is True
    assert result["reasons"] == []
    assert result["species"] == "yellow"
    assert result["colour"] == "yellow"
    assert result["natural_grant"] is True
    assert result["staged_grant"] is False
    assert result["bud_actor"]["segment"] == 0
    assert result["conversion"]["colour_index"] == 2


def test_staged_grant_taints_an_otherwise_natural_run():
    text = NATURAL_YELLOW + "\n" + GRANT_YELLOW_STAGED
    result = evaluate(text)
    assert result["classification"] == STAGED
    assert result["pass"] is False
    assert result["staged_grant"] is True
    assert "staged_grant" in result["reasons"]


def test_staged_only_is_staged_and_fails():
    result = evaluate(GRANT_YELLOW_STAGED)
    assert result["classification"] == STAGED
    assert result["pass"] is False


def test_accept_and_sprout_without_a_bud_actor_is_mocked():
    text = "\n".join([ACCEPT_YELLOW, SPROUT_YELLOW])
    result = evaluate(text)
    assert result["classification"] == MOCKED
    assert result["pass"] is False
    assert "no_bud_actor" in result["reasons"]


def test_bud_actor_with_wrong_colour_is_an_explicit_failure():
    text = "\n".join([
        BUD_YELLOW.replace("colour=yellow", "colour=blue"),
        ACCEPT_YELLOW,
        SPROUT_YELLOW,
        GRANT_YELLOW_NATURAL,
    ])
    result = evaluate(text)
    assert result["pass"] is False
    assert result["classification"] != NATURAL
    assert "bud_colour_mismatch" in result["reasons"]


def test_missing_accept_and_conversion_are_named_reasons():
    no_accept = "\n".join([BUD_YELLOW, SPROUT_YELLOW, GRANT_YELLOW_NATURAL])
    result = evaluate(no_accept)
    assert result["pass"] is False
    assert "no_accept" in result["reasons"]

    no_conversion = "\n".join([BUD_YELLOW, ACCEPT_YELLOW, GRANT_YELLOW_NATURAL])
    result = evaluate(no_conversion)
    assert result["pass"] is False
    assert "no_conversion" in result["reasons"]


def test_empty_or_garbage_input_is_missing():
    for text in ("", "   \n\n", "garbage line\nmore unrelated noise\n"):
        result = evaluate(text)
        assert result["classification"] == MISSING
        assert result["pass"] is False


def test_elec_timeline_flag_is_reported_but_not_required():
    without_timeline = evaluate(NATURAL_YELLOW)
    assert without_timeline["pass"] is True
    assert without_timeline["elec_opened_after_grant"] is False

    after = evaluate(NATURAL_YELLOW + "\n" + TIMELINE_ELEC)
    assert after["pass"] is True
    assert after["elec_opened_after_grant"] is True
    assert after["elec_timeline_index"] > after["elec_grant_index"]

    before = evaluate(TIMELINE_ELEC + "\n" + NATURAL_YELLOW)
    assert before["pass"] is True
    assert before["elec_opened_after_grant"] is False


def test_lane23_pom_markers_remain_valid_aliases():
    text = "\n".join([
        BUD_YELLOW,
        POM_ACCEPT_YELLOW,
        POM_SPROUT_YELLOW,
        GRANT_YELLOW_NATURAL,
    ])
    result = evaluate(text)
    assert result["classification"] == NATURAL
    assert result["pass"] is True


def test_evaluate_accepts_a_list_of_lines():
    result = evaluate(NATURAL_YELLOW.splitlines())
    assert result["classification"] == NATURAL
    assert result["pass"] is True


def test_main_prints_json_and_returns_exit_code(tmp_path, capsys):
    good = tmp_path / "run.log"
    good.write_text(NATURAL_YELLOW, encoding="utf-8")
    code = main(str(good))
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["pass"] is True
    assert out["classification"] == NATURAL

    bad = tmp_path / "bad.log"
    bad.write_text(GRANT_YELLOW_STAGED, encoding="utf-8")
    assert main(bad) == 1
