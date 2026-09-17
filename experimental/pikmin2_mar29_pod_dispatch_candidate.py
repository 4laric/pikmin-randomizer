"""Private scoped candidate for the Mar29 Pod dispatch arm (#665).

Reuses the already-filed #650 dispatch patch verbatim: a 5-line additive arm
wiring the lane-owned `pc_p2_mar_receipt` hook into the shared
`pc_port/pc_p2_preview.cpp` corpse chain. This module never edits shared
files; it applies the patch onto a PRIVATE copy, verifies hook registration
grammar, and emits a hashed integration-ready packet for the single-writer
integrator after the #186 owner decision. Downstream consumer: #375.

Fail-closed: anchors must match exactly once; any drift, reorder, or missing
anchor raises ValueError and writes nothing. No ADMIT, no runtime, no ledger.
Stdlib only.
"""
import argparse
import hashlib
import json
from pathlib import Path

BASE_PREVIEW_SHA256 = "1460767425018a06"
BASE_NATIVE_COMMIT = "7b9ecaa668fd55332073446cdbdaf6424b209ea7"
ADAPTER_HEADER_SHA256 = "51502c3e75415b81"
ADAPTER_IMPL_SHA256 = "0cd70df739825066"
FIXTURE_SHA256 = "0b3437662a9ee53b"

ANCHOR_INCLUDE = '#include "pc_p2_kurage_teki.h"'
ADD_INCLUDE = '#include "pc_p2_mar_receipt.h"'
ANCHOR_ARM_BEFORE = "pc_p2_long_legs_receipt(pellet,generator)"
ANCHOR_ARM_AFTER = "corpses.find(pellet->mPelletView)"
ARM_LINES = (
    "        // Mar29 corpse receipt (corpse:mar:<gen>), keyed on the delivered\n"
    "        // PelletView via pc_p2_mar_receipt (#650, downstream #375).\n"
    "        else if(unsigned generator=0;pc_p2_mar_receipt(pellet->mPelletView,generator)) {\n"
    '            receipt="corpse:"+pc_p2_cave_receipt_prefix()+"mar:"+std::to_string(generator);value=corpseValue;\n'
    "        }\n"
)
EXPECTED_ARM_RECEIPT = 'receipt="corpse:"+pc_p2_cave_receipt_prefix()+"mar:"'


class CandidateRejected(ValueError):
    pass


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def apply_patch(preview_text):
    """Return the patched preview text; raise CandidateRejected on any drift."""
    if not isinstance(preview_text, str) or not preview_text:
        raise CandidateRejected("Empty preview source")
    if preview_text.count(ANCHOR_INCLUDE) != 1:
        raise CandidateRejected("Include anchor must occur exactly once")
    if ADD_INCLUDE in preview_text:
        raise CandidateRejected("Patch already applied or foreign include present")
    if ARM_LINES.strip() in preview_text:
        raise CandidateRejected("Dispatch arm already present")
    if preview_text.count(ANCHOR_ARM_BEFORE) != 1:
        raise CandidateRejected("Long-legs arm anchor must occur exactly once")
    if preview_text.count(ANCHOR_ARM_AFTER) < 1:
        raise CandidateRejected("Corpse-fallback anchor missing")
    text = preview_text.replace(
        ANCHOR_INCLUDE, ANCHOR_INCLUDE + "\n" + ADD_INCLUDE, 1)
    marker = "        }\n"
    pos = text.find(ANCHOR_ARM_BEFORE)
    close = text.find(marker, pos)
    if close < 0:
        raise CandidateRejected("Long-legs arm block end not found")
    insert_at = close + len(marker)
    text = text[:insert_at] + ARM_LINES + text[insert_at:]
    return text


def verify_hook(patched_text):
    """Verify the wired hook registration grammar; return a findings dict."""
    findings = {"include": ADD_INCLUDE in patched_text,
                "arm": ARM_LINES.strip() in patched_text,
                "receipt": EXPECTED_ARM_RECEIPT in patched_text,
                "call": "pc_p2_mar_receipt(pellet->mPelletView,generator)" in patched_text,
                "ordered": False, "existing_intact": False}
    longlegs = patched_text.find(ANCHOR_ARM_BEFORE)
    arm = patched_text.find(ARM_LINES.strip())
    fallback = patched_text.find(ANCHOR_ARM_AFTER)
    findings["ordered"] = 0 <= longlegs < arm < fallback
    findings["existing_intact"] = (
        "pc_p2_long_legs_receipt(pellet,generator)" in patched_text
        and "auto found=corpses.find(pellet->mPelletView)" in patched_text)
    findings["ok"] = all((findings["include"], findings["arm"],
                          findings["receipt"], findings["call"],
                          findings["ordered"], findings["existing_intact"]))
    return findings


def candidate_packet(preview_text, adapter_hashes, out_dir):
    """Apply + verify onto private copies; write patched file + packet JSON."""
    patched = apply_patch(preview_text)
    findings = verify_hook(patched)
    if not findings["ok"]:
        raise CandidateRejected("Hook verification failed: %s" % findings)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    patched_path = out_dir / "pc_p2_preview.cpp.candidate"
    if patched_path.exists():
        raise CandidateRejected("Refusing to overwrite existing candidate")
    patched_path.write_text(patched, encoding="utf-8", newline="")
    packet = {
        "schema": 1,
        "issue": 665,
        "producer_issue": 650,
        "downstream_consumer": 375,
        "base_native_commit": BASE_NATIVE_COMMIT,
        "base_preview_sha256_prefix": BASE_PREVIEW_SHA256,
        "adapter_hashes": dict(adapter_hashes),
        "patched_sha256": sha256_bytes(patched.encode("utf-8")),
        "hook_findings": findings,
        "owner_decision_needed": "#186 existing-owner approval to land the 5 added lines verbatim on pc_port/pc_p2_preview.cpp",
        "gates": "all six runtime gates UNTESTED; no build, no runtime, no ADMIT",
    }
    packet_path = out_dir / "mar29-pod-dispatch-packet.json"
    if packet_path.exists():
        raise CandidateRejected("Refusing to overwrite existing packet")
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    return {"patched": str(patched_path), "packet": str(packet_path),
            "patched_sha256": packet["patched_sha256"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--adapter-header-sha256", default=ADAPTER_HEADER_SHA256)
    parser.add_argument("--adapter-impl-sha256", default=ADAPTER_IMPL_SHA256)
    parser.add_argument("--fixture-sha256", default=FIXTURE_SHA256)
    args = parser.parse_args(argv)
    preview_text = args.preview.read_text(encoding="utf-8")
    result = candidate_packet(
        preview_text,
        {"pc_p2_mar_receipt.h": args.adapter_header_sha256,
         "pc_p2_mar_receipt.cpp": args.adapter_impl_sha256,
         "p2_muse_mar_receipt_fixture.cpp": args.fixture_sha256},
        args.out)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
