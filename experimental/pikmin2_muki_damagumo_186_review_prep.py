"""#186 review-preparation packet for the muki-damagumo stage landings (#813).

Lane muki-damagumo-186-review-prep, consumer p2-challenge-ch-muki-damagumo-p1
(#740, blocked gen 5), classification
edbc7faab44d86e9cffdf0ae2386d52541a1e8eebef618ab1d2ff71f9ff41db4.

Bounded tooling-only diagnosis: verifies the pinned #742 damagumo-row and
#748 MUKI-rows producer diffs are purely additive and producer-owned (zero
shared-file edits), references the existing #777 MUKI decision packet instead
of duplicating it, renders the exact Damagumo row append for #186 review, and
records the missing shared registration as the remaining input. It performs
no engine change, grants no approval, and claims no gameplay acceptance.
All inputs are explicit pinned values; anything missing, malformed or
hash-drifted is refused fail-closed with no packet emitted.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

PACKET_SCHEMA = "p2-muki-damagumo-186-review-prep/1"
ISSUE = 813
CONSUMER_LANE = "p2-challenge-ch-muki-damagumo-p1"
CONSUMER_ISSUE = 740
CLASSIFICATION = "edbc7faab44d86e9cffdf0ae2386d52541a1e8eebef618ab1d2ff71f9ff41db4"
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"

PRODUCER_742 = {
    "lane": "damagumo-stage-table-row-native", "issue": 742,
    "root_base": "ecf5f53a601a3c563bb44339ec7abf4665795451",
    "root_head": "f0d2aec3af8dc597438402239c24cd2d64d40377",
    "native_base": "93603dc232f9c6ddc4fb2c1241bd590fe95d9b54",
    "native_head": "185c9d6715c3d7287abb2c7a8e503f283a575e4a",
    "root_files": ["docs/PIKMIN2_DAMAGUMO_STAGE_TABLE_ROW.md",
                   "experimental/pikmin2_damagumo_stage_table_row.py",
                   "scripts/build_p2_damagumo_stage_table.py",
                   "tests/test_pikmin2_damagumo_stage_table_row.py"],
    "native_files": ["native/pc_port/pc_p2_challenge_damagumo_stage.h",
                     "native/pc_port/pc_p2_challenge_damagumo_stage.cpp",
                     "native/tools/p2_damagumo_stage_table_fixture.cpp"],
}

PRODUCER_748 = {
    "lane": "muki-stage-table-rows-native", "issue": 748,
    "root_base": "ecf5f53a601a3c563bb44339ec7abf4665795451",
    "root_commits": ["e51a323c369837a2acd6fe5edd6d44da0ff4ebcb",
                     "98dc264ff6de4c4cb997a2e079d90d8cd4ac30ff",
                     "baf82085429160b6b8ce5a901a8af3ef36a50af8"],
    "root_head": "baf82085429160b6b8ce5a901a8af3ef36a50af8",
    "native_base": "93603dc232f9c6ddc4fb2c1241bd590fe95d9b54",
    "native_commits": ["cae86d4e46d22f6f579df38ac86ca5c62afde613",
                       "3c50ca44faad976d91cf790da8adbe6e3f508c4a"],
    "native_head": "3c50ca44faad976d91cf790da8adbe6e3f508c4a",
    "root_files": ["docs/PIKMIN2_MUKI_STAGE_TABLE_ROWS.md",
                   "experimental/pikmin2_muki_stage_table_rows.py",
                   "scripts/build_p2_muki_stage_table.py",
                   "tests/test_pikmin2_muki_stage_table_rows.py"],
    "native_files": ["native/pc_port/pc_p2_challenge_muki_stages.h",
                     "native/pc_port/pc_p2_challenge_muki_stages.cpp",
                     "native/tools/p2_muki_stage_table_fixture.cpp"],
}

# Existing #777 MUKI decision packet (read-only reference, never duplicated).
MUKI_PACKET_SHA256 = "5361c258a40d39856316663058b39d266897252f00b159e775c0879bd1bde527"
MUKI_PACKET_ISSUE = 777

# Destination pins (read-only refs).
DEST_NATIVE_HEAD = "f363d04d"
DEST_BOOT_TABLE_PIN = "db245877"
DEST_CMAKE_PIN = "38305eea"

# Shared files needing the #186 decision (no producer diff exists yet).
SHARED_FILES = ["native/pc_port/pc_bbft.cpp", "native/CMakeLists.txt"]

# Pinned Damagumo row (#742 spec, read-only).
DAMAGUMO_ROW = {
    "cave_id": "ch_MUKI_damagumo",
    "cave_path": "user/Mukki/mapunits/caveinfo/ch_MUKI_damagumo.txt",
    "source_sha256": "c6f2dede22acb37cb0d939b1ee9670b103dc9408d3c9fe100000482891fefa9e",
    "ui_index": 6, "table_order": 9, "floors": 1, "floor_seconds": [150.0],
    "roster": [[0, 0, 0], [0, 0, 0], [0, 0, 50], [0, 0, 0], [0, 0, 0],
               [0, 0, 0], [0, 0, 0]],
    "bitter_sprays": 0, "spicy_sprays": 1, "legacy_time": 0.0,
    "treasure_count_field": 0,
}

_FULL_SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
_SHORT_SHA_RE = re.compile(r"[0-9a-f]{7,40}\Z")


class PrepRejected(ValueError):
    """Fail-closed refusal: missing pin, malformed input or hash drift."""


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git(tree, *args):
    done = subprocess.run(["git", "-C", str(tree)] + list(args),
                          capture_output=True, text=True, timeout=60)
    if done.returncode != 0:
        raise PrepRejected("git failed in %s: %s" % (tree, done.stderr.strip()))
    return done.stdout.strip()


def check_worktree(tree, base, head, owned):
    """Confirm a worktree exists at the pinned head and lists only owned files."""
    tree = Path(tree)
    if not (tree / ".git").exists() and not tree.is_dir():
        raise PrepRejected("worktree missing: %s" % tree)
    observed = git(tree, "rev-parse", "HEAD")
    if observed != head:
        raise PrepRejected("worktree head changed: %s" % observed)
    names = git(tree, "diff", "--name-only", base, head).splitlines()
    names = [n for n in names if n.strip()]
    want = [o[7:] if o.startswith("native/") else o for o in owned]
    if sorted(names) != sorted(want):
        raise PrepRejected("diff files differ from owned scope: %s" % names)
    shared = [n for n in names if n in SHARED_FILES or n.startswith("native/pc_port/pc_bbft")]
    if shared:
        raise PrepRejected("unexpected shared-file edit: %s" % shared)
    return names


def verify_producer(spec, root_wt, native_wt):
    """Verify a producer's diffs are purely additive and producer-owned."""
    for key in ("root_base", "root_head", "native_base", "native_head"):
        if not _FULL_SHA_RE.match(spec[key]):
            raise PrepRejected("bad pin: " + key)
    root_files = check_worktree(root_wt, spec["root_base"], spec["root_head"], spec["root_files"])
    native_files = check_worktree(native_wt, spec["native_base"], spec["native_head"],
                                  spec["native_files"])
    return {"root_files": root_files, "native_files": native_files}


def _fmt_float(value):
    text = repr(float(value))
    return text if "." in text else text + ".0"


def render_damagumo_row():
    """Render the exact Damagumo row block in P2ChallengeStageRow field order."""
    r = DAMAGUMO_ROW
    seconds = ", ".join(_fmt_float(v) + "f" for v in list(r["floor_seconds"]) + [0.0] * 7)
    roster = ", ".join("{%d,%d,%d}" % tuple(cell) for cell in r["roster"])
    return (
        '    { "%s",\n'
        '      "%s",\n'
        '      "%s",\n'
        '      %d, %d, %d,\n'
        '      { %s },\n'
        '      { %s },\n'
        '      %d, %d, %sf, %d },\n'
    ) % (r["cave_id"], r["cave_path"], r["source_sha256"], r["ui_index"],
         r["table_order"], r["floors"], seconds, roster, r["bitter_sprays"],
         r["spicy_sprays"], _fmt_float(r["legacy_time"]), r["treasure_count_field"])


def render_damagumo_diff(anchor_tail="      1, 2, 350.0f, 0 },"):
    """Render the Damagumo append against the destination table shape."""
    rows = "".join("+" + line + "\n" for line in render_damagumo_row().splitlines())
    return (
        "--- a/native/pc_port/pc_bbft.cpp\n"
        "+++ b/native/pc_port/pc_bbft.cpp\n"
        "@@ kP2ChallengeStages: append Damagumo row (producer 185c9d67) @@\n"
        "  %s\n"
        "%s"
        "--- a/native/CMakeLists.txt\n"
        "+++ b/native/CMakeLists.txt\n"
        "@@ membership: add damagumo stage-table module to the owning target @@\n"
        "+pc_port/pc_p2_challenge_damagumo_stage.cpp\n"
    ) % (anchor_tail, rows)


def build_packet(root742, native742, root748, native748,
                 muki_packet_path=None, dest_native_head=DEST_NATIVE_HEAD):
    """Assemble the machine-readable #186 review-prep packet (fail-closed)."""
    v742 = verify_producer(PRODUCER_742, root742, native742)
    v748 = verify_producer(PRODUCER_748, root748, native748)
    if not _SHORT_SHA_RE.match(dest_native_head):
        raise PrepRejected("bad destination pin")
    muki_ref = {"issue": MUKI_PACKET_ISSUE, "sha256": MUKI_PACKET_SHA256,
                "note": "MUKI rows diff lives there; not duplicated here"}
    if muki_packet_path is not None:
        actual = sha256_file(muki_packet_path)
        if actual != MUKI_PACKET_SHA256:
            raise PrepRejected("MUKI packet hash drift: " + actual)
        muki_ref["path"] = str(muki_packet_path)
    files_742 = v742["root_files"] + v742["native_files"]
    files_748 = v748["root_files"] + v748["native_files"]
    recommendations = {}
    for path in files_742 + files_748:
        recommendations[path] = {
            "recommendation": "no-186-review-required",
            "reason": "lane-owned additive file, not a shared hook; outside #186 scope",
        }
    for path in SHARED_FILES:
        recommendations[path] = {
            "recommendation": "decision-pending-missing-diff",
            "reason": "shared hook with no producer diff yet; the integration owner "
                      "must supply the registration diff before #186 can decide",
        }
    return {
        "schema": PACKET_SCHEMA,
        "issue": ISSUE,
        "consumer": {"lane": CONSUMER_LANE, "issue": CONSUMER_ISSUE},
        "classification": CLASSIFICATION,
        "producers": {
            "742": {"lane": PRODUCER_742["lane"], "issue": 742,
                    "root_head": PRODUCER_742["root_head"],
                    "native_head": PRODUCER_742["native_head"],
                    "files": files_742},
            "748": {"lane": PRODUCER_748["lane"], "issue": 748,
                    "root_head": PRODUCER_748["root_head"],
                    "native_head": PRODUCER_748["native_head"],
                    "files": files_748},
        },
        "muki_packet_reference": muki_ref,
        "destination": {"native_head": dest_native_head,
                        "boot_table_pin": DEST_BOOT_TABLE_PIN,
                        "cmake_pin": DEST_CMAKE_PIN},
        "damagumo_diff": render_damagumo_diff(),
        "shared_files": list(SHARED_FILES),
        "recommendations": recommendations,
        "missing_input": ("No shared-file diff exists for either landing; #186 cannot "
                          "approve or reject unproposed edits. The integration owner "
                          "must supply the kP2ChallengeStages registration + CMakeLists "
                          "membership diff (Damagumo row rendered above; MUKI rows in "
                          "the #777 packet) before a #186 decision is possible."),
        "guard_sha256": GUARD_SHA256,
        "runtime_claim": False,
    }


def validate_packet(packet):
    """Fail-closed packet self-check; True only when complete and honest."""
    if not isinstance(packet, dict) or packet.get("schema") != PACKET_SCHEMA:
        return False
    if packet.get("issue") != ISSUE or packet.get("consumer", {}).get("issue") != CONSUMER_ISSUE:
        return False
    if packet.get("classification") != CLASSIFICATION:
        return False
    try:
        rebuilt = render_damagumo_diff()
    except (ValueError, TypeError, AttributeError):
        return False
    if rebuilt != packet.get("damagumo_diff"):
        return False
    recs = packet.get("recommendations", {})
    for path in SHARED_FILES:
        if recs.get(path, {}).get("recommendation") != "decision-pending-missing-diff":
            return False
    return bool(packet.get("missing_input"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("packet", "diff", "verify"))
    parser.add_argument("--root742", type=Path, default=None)
    parser.add_argument("--native742", type=Path, default=None)
    parser.add_argument("--root748", type=Path, default=None)
    parser.add_argument("--native748", type=Path, default=None)
    parser.add_argument("--muki-packet", type=Path, default=None)
    args = parser.parse_args(argv)
    if args.command == "diff":
        print(render_damagumo_diff())
        return 0
    if args.command == "verify":
        for label, wt in (("root742", args.root742), ("native742", args.native742),
                          ("root748", args.root748), ("native748", args.native748)):
            if wt is None:
                raise SystemExit("missing --%s" % label.replace("742", "742").replace("748", "748"))
        verify_producer(PRODUCER_742, args.root742, args.native742)
        verify_producer(PRODUCER_748, args.root748, args.native748)
        print(json.dumps({"verified": True}))
        return 0
    for label in ("root742", "native742", "root748", "native748"):
        if getattr(args, label) is None:
            raise SystemExit("missing --" + label)
    print(json.dumps(build_packet(args.root742, args.native742, args.root748,
                                  args.native748, args.muki_packet),
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    main()
