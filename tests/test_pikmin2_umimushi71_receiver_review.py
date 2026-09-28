"""Focused fail-closed tests for the UmiMushi71 receiver review (#662).

Synthetic logs only: injected markers must never be credited, missing legs
must report the exact registration gap, and a fully-instrumented log must
pass. The retail research tree is referenced read-only by the report.
"""
from experimental import pikmin2_umimushi71_receiver_review as review

FULL_LOG = """\
P2_UMIMUSHI_BIND generator=41001 source_id=71
P2_ENEMY_READY species=UmiMushi generator=41001
P2_UMIMUSHI_EAT generator=41001 pikmin=1
P2_UMIMUSHI_DEAD generator=41001 source_id=71 health=0
P2_UMIMUSHI_CORPSE_READY generator=41001 source_id=71 receipt=corpse:umimushi:41001
"""

PARTIAL_LOG = """\
P2_UMIMUSHI_EAT generator=41001 pikmin=1
P2_UMIMUSHI_DEAD generator=41001 source_id=71 health=0
"""

BLIND_LOG = """\
P2_UMIMUSHI_DEAD generator=41002 source_id=101 health=0
P2_UMIMUSHI_CORPSE_READY generator=41002 source_id=101 receipt=corpse:umimushi:41002
"""

INJECTED_LOG = """\
P2_UMIMUSHI_DEAD generator=41001 source_id=71 health=0 INJECTED
P2_UMIMUSHI_CORPSE_READY generator=41001 source_id=71 receipt=corpse:umimushi:41001 FORCED
"""

WRONG_SOURCE_LOG = """\
P2_UMIMUSHI_DEAD generator=41001 source_id=30 health=0
"""


def test_full_log_registers_both_legs():
    result = review.review_log(FULL_LOG)
    assert result["registration_present"] is True
    assert result["gap"] is None
    assert result["sources"] == [71]
    assert result["deaths"] == {71: 1}
    assert result["eats"] == 1
    assert result["corpse_markers"] == 1
    assert result["receipt_tokens"] == 1


def test_partial_log_names_exact_gap():
    result = review.review_log(PARTIAL_LOG)
    assert result["registration_present"] is False
    assert result["corpse_markers"] == 0
    assert result["receipt_tokens"] == 0
    assert "P2_UMIMUSHI_CORPSE_READY" in result["gap"]
    assert "pc_p2_umimushi_forget" in result["gap"]
    assert "Family-owner review REQUIRED" in result["gap"]


def test_blind_identity_correlates():
    result = review.review_log(BLIND_LOG)
    assert result["registration_present"] is True
    assert result["sources"] == [101]
    assert result["deaths"] == {101: 1}


def test_injected_markers_never_credited():
    result = review.review_log(INJECTED_LOG)
    assert result["registration_present"] is False
    assert result["deaths"] == {}
    assert result["gap"] is not None


def test_wrong_source_ignored():
    result = review.review_log(WRONG_SOURCE_LOG)
    assert result["sources"] == []
    assert result["deaths"] == {}
    assert result["registration_present"] is False


def test_empty_log_fails_closed():
    result = review.review_log("")
    assert result["registration_present"] is False
    assert result["sources"] == []
    assert result["gap"] is not None
