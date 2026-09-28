"""Root-only producer: land the reviewed #509 @rsp fix on the canonical line (#659).

Verifies the canonical integration pin still rejects Ninja `@rsp` link lines while the
reviewed fix commits exist off-line, re-derives the exact landable rebased change from
the reviewed bytes (delivered as a patch; the shared files stay owned by published
`provider-rsp-builder-509-v1`, issue #509), re-verifies the #616 pinned evidence hashes,
and emits a landable packet for the integrator. Downstream: #616 handoff validation,
then #573. Planning/tooling only: no builds, no runtime, all gates UNTESTED, no ADMIT.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ISSUE = 659
CANONICAL_PIN = "36b868391e62cccf37d992aa2f796f3cc9c6dc31"
FIX_COMMIT = "0cab1fa111216250ce57e02600f697ab850ae592"
FIX_PARENT = "2fb2040e8f74501ebc96be90c68c22b7acb6861b"
CONTENT_COMMIT = "70d308277ee46cc5327ef087f252369b136a40f5"
SHARED_FILES = ("scripts/build_pikmin2_fixture.py",
                "tests/test_pikmin2_fixture_build.py")
REJECTION_LINE = 'raise BuildRejected('
RSP_PROBE = "startswith('@')"
CANONICAL_ROOT = Path("C:/Users/alari/pikmin-randomizer")
H616_HANDOFF = ("output/workflow/autofill/planning-shards/"
                "provider-actor-birth-projectiles/prepared/bomb-mgr-birth/out/handoff.json")


class LandingGapError(ValueError):
    """A prerequisite pin cannot be supplied or verified; nothing is invented."""


def _git(*args):
    try:
        proc = subprocess.run(["git", "-C", str(CANONICAL_ROOT), *args],
                              capture_output=True)
    except (OSError, ValueError) as exc:
        raise LandingGapError("git unavailable: %s" % exc)
    if proc.returncode != 0:
        raise LandingGapError("git %s failed: %s" % (" ".join(args), proc.stderr.decode()[:200]))
    return proc.stdout


def _is_ancestor(commit, pin):
    proc = subprocess.run(["git", "-C", str(CANONICAL_ROOT), "merge-base",
                           "--is-ancestor", commit, pin], capture_output=True)
    if proc.returncode not in (0, 1):
        raise LandingGapError("ancestry check failed for %s" % commit)
    return proc.returncode == 0


def sha256_bytes(data):
    if not isinstance(data, (bytes, bytearray)):
        raise LandingGapError("bytes required for hashing")
    return hashlib.sha256(bytes(data)).hexdigest()


def canonical_gap():
    """Prove the canonical pin rejects @rsp and lacks the reviewed fix."""
    builder = _git("show", "%s:%s" % (CANONICAL_PIN, SHARED_FILES[0])).decode("utf-8")
    rejects = REJECTION_LINE in builder and RSP_PROBE in builder
    if not rejects:
        raise LandingGapError("canonical pin no longer rejects @rsp; gap record stale")
    ancestry = {name: _is_ancestor(commit, CANONICAL_PIN)
                for name, commit in (("fix", FIX_COMMIT), ("parent", FIX_PARENT),
                                     ("content", CONTENT_COMMIT))}
    if any(ancestry.values()):
        raise LandingGapError("reviewed fix already on canonical pin: %s" % ancestry)
    return {"pin": CANONICAL_PIN, "rejects_rsp": True,
            "rejection": "Empty command or unsupported response file",
            "fix_absent": ancestry, "shared_files": list(SHARED_FILES)}


def reviewed_fix():
    """Identify the reviewed bytes and both endpoint hashes per file."""
    entries = {}
    for path in SHARED_FILES:
        pin_bytes = _git("show", "%s:%s" % (CANONICAL_PIN, path))
        fix_bytes = _git("show", "%s:%s" % (FIX_COMMIT, path))
        if pin_bytes == fix_bytes:
            raise LandingGapError("no change between pin and fix for %s" % path)
        entries[path] = {"pin_sha256": sha256_bytes(pin_bytes),
                         "fix_sha256": sha256_bytes(fix_bytes),
                         "pin_bytes": len(pin_bytes), "fix_bytes": len(fix_bytes)}
    return {"fix_commit": FIX_COMMIT, "fix_parent": FIX_PARENT,
            "content_commit": CONTENT_COMMIT, "files": entries}


def derive_landable_patch():
    """Re-derive the exact patch (pin -> reviewed fix) and prove it applies."""
    diff = _git("diff", CANONICAL_PIN, FIX_COMMIT, "--", *SHARED_FILES)
    if not diff:
        raise LandingGapError("empty landable diff")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "scripts").mkdir()
        (root / "tests").mkdir()
        for path in SHARED_FILES:
            target = root / path
            target.write_bytes(_git("show", "%s:%s" % (CANONICAL_PIN, path)))
        patch = root / "landable.patch"
        patch.write_bytes(diff)
        proc = subprocess.run(["git", "apply", "--check", str(patch)],
                              capture_output=True, cwd=str(root))
        if proc.returncode != 0:
            raise LandingGapError("landable patch does not apply: %s"
                                  % proc.stderr.decode()[:200])
    return {"patch_sha256": sha256_bytes(diff), "patch_bytes": len(diff),
            "patch": diff.decode("utf-8")}


def verify_616_evidence():
    """Re-verify every #616 handoff evidence hash still matches on disk."""
    handoff_path = CANONICAL_ROOT / H616_HANDOFF
    try:
        record = json.loads(handoff_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LandingGapError("#616 handoff unreadable: %s" % exc)
    checked = {}
    for key, item in record.get("evidence", {}).items():
        target = CANONICAL_ROOT / item["path"]
        if not target.is_file():
            raise LandingGapError("#616 evidence missing: %s" % key)
        digest = sha256_bytes(target.read_bytes())
        if digest != item["sha256"]:
            raise LandingGapError("#616 evidence drifted: %s" % key)
        checked[key] = digest
    return {"matches": checked,
            "handoff_root": record["root"]["head"],
            "handoff_native": record["native"]["head"]}


def emit_packet(out_dir=None):
    """Emit the landable packet dict (and optionally write it)."""
    gap = canonical_gap()
    fix = reviewed_fix()
    patch = derive_landable_patch()
    evidence = verify_616_evidence()
    packet = {
        "schema": 1, "kind": "landable-patch", "issue": ISSUE,
        "gap": gap, "fix": fix,
        "patch_sha256": patch["patch_sha256"], "patch_bytes": patch["patch_bytes"],
        "patch": patch["patch"], "evidence_616": evidence,
        "downstream": ["provider-bomb-mgr-birth (#616) handoff validation",
                       "enemy-bombotakara93-payload (#573) consumption"],
        "shared_files_owned_by": "provider-rsp-builder-509-v1 (issue #509); "
                                 "integrator lands the patch, this lane claims nothing shared",
        "gates": "all six UNTESTED",
    }
    if out_dir is not None:
        target = Path(out_dir) / "rsp-canonical-landing-packet.json"
        target.write_text(json.dumps(packet, indent=1) + "\n", encoding="utf-8")
        packet["packet_path"] = str(target)
    return packet


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        packet = emit_packet(args.out)
    except LandingGapError as exc:
        print("LANDING_GAP %s" % exc)
        return 4
    print("patch=%s gap=%s evidence_616=%d downstream=%s"
          % (packet["patch_sha256"][:16], packet["gap"]["pin"][:8],
             len(packet["evidence_616"]["matches"]),
             ",".join(s.split(" ")[0] for s in packet["downstream"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())