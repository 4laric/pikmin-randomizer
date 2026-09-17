"""Focused tests for the overworld boot-flag review adapter (#738)."""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experimental import pikmin2_overworld_boot_flag_review as review  # noqa: E402

NATIVE = Path(os.environ.get("PIKMIN_OVERWORLD_NATIVE",
    "C:/Users/alari/pikmin-randomizer/output/workflow/autofill/planning-shards/overworld-tutorial/prepared/overworld-boot-flag-review-native"))


def base_sources():
    cpp = (NATIVE / "pc_port/pc_bbft.cpp").read_text(encoding="utf-8")
    h = (NATIVE / "pc_port/pc_bbft.h").read_text(encoding="utf-8")
    return cpp, h


def test_clean_apply_and_verify():
    cpp, h = base_sources()
    patched_cpp, patched_h = review.apply_proposal(cpp, h)
    findings = review.verify_proposal(patched_cpp, patched_h)
    assert findings["ok"] is True
    assert "P2_OVERWORLD_BOOT course=" in patched_cpp
    assert "--experimental-p2-overworld-course" in patched_cpp


def test_order_and_existing_intact():
    cpp, h = base_sources()
    patched_cpp, _ = review.apply_proposal(cpp, h)
    findings = review.verify_proposal(patched_cpp, h)
    assert findings["ordered"] is True
    assert findings["existing_intact"] is True


def test_double_apply_refused(tmp_path):
    cpp, h = base_sources()
    patched_cpp, patched_h = review.apply_proposal(cpp, h)
    with pytest.raises(review.ProposalRejected):
        review.apply_proposal(patched_cpp, patched_h)


def test_missing_room_anchor_refused():
    cpp, h = base_sources()
    with pytest.raises(review.ProposalRejected):
        review.apply_proposal(cpp.replace(review.ANCHOR_ROOM_FLAG, ""), h)


def test_missing_challenge_anchor_refused():
    cpp, h = base_sources()
    with pytest.raises(review.ProposalRejected):
        review.apply_proposal(cpp.replace(review.ANCHOR_CHALLENGE_FLAG, ""), h)


def test_missing_header_anchor_refused():
    cpp, h = base_sources()
    with pytest.raises(review.ProposalRejected):
        review.apply_proposal(cpp, h.replace(review.ANCHOR_H_ROOM, ""))


def test_empty_sources_refused():
    with pytest.raises(review.ProposalRejected):
        review.apply_proposal("", "")


def test_no_write_on_failure(tmp_path):
    cpp, h = base_sources()
    with pytest.raises(review.ProposalRejected):
        review.request_packet(cpp.replace(review.ANCHOR_ROOM_FLAG, ""), h, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_refusals_present():
    cpp, h = base_sources()
    patched_cpp, _ = review.apply_proposal(cpp, h)
    assert "requires a course name" in patched_cpp
    assert "Unknown P2 overworld course" in patched_cpp


def test_request_packet(tmp_path):
    cpp, h = base_sources()
    result = review.request_packet(cpp, h, tmp_path)
    assert Path(result["packet"]).is_file()
    assert Path(result["cpp"]).is_file()