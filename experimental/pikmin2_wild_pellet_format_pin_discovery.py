"""Bounded pin-discovery: wild-pellet (pb01) tlep record format + corpse-registry binding.

Tooling-only, read-only. Issue #825 (downstream consumer #561, recovery
request 1282ac9d1a5bce83b7a826f8a9fce7870411e14b3df7507f331770529daf13cb).

This module pins the exact generator-record layout of wild arena pellets
(``tlep`` rows in ``default.gen``) and the exact engine receipt binding that
decides their Pod delivery fate. It performs no staging, no builds, no
launches and no gameplay acceptance. Every path that touches the engine
fails closed: unknown bytes, missing inputs or drifted citations raise
instead of guessing.

Pinned against root worktree commit 3a33cbdefd5e4057eef9fb0d824cce4510ddab05.
All ``engine/...``, ``scripts/...`` and ``experimental/...`` citations below
are worktree-relative file:line references at that pin unless noted.
"""

import argparse
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Pinned citations (worktree-relative, root pin 3a33cbde).
# ---------------------------------------------------------------------------
CITATIONS = {
    # Generator framing shared parser.
    "records": "scripts/preview_pikmin2_room.py:12-18",
    "room_templates": "scripts/preview_pikmin2_room.py:25",
    "room_generator": "scripts/preview_pikmin2_room.py:35-52",
    # Generator pose convention (position + offset at 48:72, never Euler).
    "write_position": "experimental/pikmin2_generator_pose.py:6-10",
    # Only in-tree tlep row consumer (repositions, never decodes the model).
    "tlep_row_use": "experimental/pikmin2_uji_bite_fixture.py:52-60",
    # Enemy audit covers teki/boss only; tlep/ikip rows are out of scope.
    "enemy_audit_gap": "scripts/audit_enemy_slots.py:70-76",
    # Engine receipt binding (preview harness).
    "corpses_decl": "engine/pc_port/pc_p2_preview.cpp:102",
    "corpses_rebind": "engine/pc_port/pc_p2_preview.cpp:114-124",
    "chappy_fill": "engine/pc_port/pc_p2_preview.cpp:120-121",
    "pr05_scan": "engine/pc_port/pc_p2_preview.cpp:178-202",
    "pr05_tally": "engine/pc_port/pc_p2_preview.cpp:203",
    "pod_parse": "engine/pc_port/pc_p2_preview.cpp:230-236",
    "pod_ready": "engine/pc_port/pc_p2_preview.cpp:248",
    "room_ready": "engine/pc_port/pc_p2_preview.cpp:333",
    "deliver_chain": "engine/pc_port/pc_p2_preview.cpp:360-411",
    "unregistered_abort": "engine/pc_port/pc_p2_preview.cpp:409",
    "draw_pr05_gate": "engine/pc_port/pc_p2_preview.cpp:340",
    # Cargo registry + preview policy.
    "cargo_format": "engine/pc_port/pc_p2_cargo.h:23-36",
    "cargo_free_abort": "engine/pc_port/pc_p2_preview.cpp:359",
    "preview_policy": "engine/pc_port/pc_p2_preview_policy.h:12-16",
    # Sheargrub (Uji) corpse sidecar registry: Teki-keyed, pellet-blind.
    "sheargrub_receipt": "engine/pc_port/pc_p2_sheargrub.cpp:72",
    "sheargrub_setup": "engine/pc_port/pc_p2_sheargrub.cpp:73-89",
    # Retail pellet model table: pb01 is Blue 1-pellet.
    "pellet_table": "engine/src/plugPikiKando/pelletMgr.cpp:1490",
}

# ---------------------------------------------------------------------------
# Pinned tlep record layout.
#
# Byte offsets are record-relative. Observed on the real #561 staged arena
# ``run-rover-23/assets/dataDir/stages/chal0/default.gen``
# (sha256 8a5f18539202ca8939a36b095a93061cca756ecdf2c355fb8147522ffdd38a3d):
# 137 records, 53 tlep rows, each 164 bytes, kind ``tlep`` at 72:76 and
# version ``0.0v`` at 76:80. Model FourCC bytes live at 80:84 in stored
# (reversed-ascii) order: b"10bp" decodes to "pb01", b"50rp" to "pr05".
# This stored-order convention matches the #654 provider corroboration
# (PR05_MODEL = b"50rp", little-endian generator id at offset 8).
# ---------------------------------------------------------------------------
FRAME_MAGIC = b"    0.0v"
FILE_MAGIC = b"1.0v"
OFF_ID = 8
OFF_NAME_END = 48
OFF_POS_END = 72
OFF_KIND = 72
OFF_VERSION = 76
OFF_MODEL = 80
TLEP_KIND = b"tlep"
TLEP_VERSION = b"0.0v"
TLEP_RECORD_LEN = 164

# Deliver-chain receipt families that exist in the pinned engine. None of
# them is keyed on a wild pellet model or pellet generator id.
RECEIPT_BRANCHES = (
    "p2-cargo.txt spec (generator-bound pr05)",
    "previewTreasure (staged pr05 treasure)",
    "sheargrub (Uji Teki sidecar)",
    "mamuta/mar/bombsarai/kurage/sarai/otakara/waterwraith/king/queen/groink/fuefuki/longlegs sidecars",
    "corpses map (TEKI_Chappy only)",
)


def decode_model(stored):
    """Decode the 4 stored model bytes to the retail FourCC string."""
    if not isinstance(stored, (bytes, bytearray)) or len(stored) != 4:
        raise ValueError("model field must be exactly 4 bytes")
    return bytes(stored)[::-1].decode("ascii")


def frame_records(data):
    """Split raw ``default.gen`` bytes into generator records (read-only).

    Same framing contract as scripts/preview_pikmin2_room.records: ``1.0v``
    header, records opened by ``    0.0v`` at byte 24, record count as a
    big-endian u32 at byte 20. Fails closed on any framing drift.
    """
    if not isinstance(data, (bytes, bytearray)) or len(data) < 24:
        raise ValueError("generator blob too short for 1.0v framing")
    data = bytes(data)
    if data[:4] != FILE_MAGIC:
        raise ValueError("expected 1.0v generator fixture source")
    starts = [m.start() for m in re.finditer(re.escape(FRAME_MAGIC), data)]
    count = struct.unpack_from(">I", data, 20)[0]
    if not starts or starts[0] != 24 or len(starts) != count:
        raise ValueError("unsupported template record framing")
    return [data[s:(starts[i + 1] if i + 1 < len(starts) else len(data))]
            for i, s in enumerate(starts)]


def parse_tlep(row):
    """Decode one ``tlep`` (pellet generator) record with pinned offsets.

    Returns generator_id (LE u32 at 8), label, position (3 BE floats at 48),
    stored model bytes (80:84) and decoded model FourCC. Fails closed on
    short rows, wrong kind/version or non-ascii model bytes.
    """
    if len(row) < OFF_MODEL + 4:
        raise ValueError("truncated tlep record")
    if row[OFF_KIND:OFF_KIND + 4] != TLEP_KIND:
        raise ValueError("not a tlep record")
    if row[OFF_VERSION:OFF_VERSION + 4] != TLEP_VERSION:
        raise ValueError("unsupported tlep version")
    stored = bytes(row[OFF_MODEL:OFF_MODEL + 4])
    try:
        model = decode_model(stored)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError("non-ascii tlep model field") from exc
    generator_id = struct.unpack_from("<I", row, OFF_ID)[0]
    label = bytes(row[16:OFF_NAME_END]).split(b"\x00")[0].decode(
        "ascii", "replace")
    position = list(struct.unpack_from(">3f", row, 48))
    if any(not (abs(v) != float("inf") and v == v) for v in position):
        raise ValueError("non-finite tlep position")
    return {"generator_id": generator_id, "label": label,
            "position": position, "stored_model": stored.hex(),
            "model": model}


def classify_delivery(model):
    """Name the exact pinned-engine fate of a delivered pellet model.

    ``pr05`` is the only pellet model with a bound receipt path (staged
    cargo spec or previewTreasure). Every other pellet model reaches the
    fail-closed abort. Returns (binding, abort_bool).
    """
    if model == "pr05":
        return ("treasure: staged p2-cargo.txt spec or previewTreasure "
                "(engine/pc_port/pc_p2_preview.cpp:360-362)", False)
    return ("unregistered: no receipt branch binds wild pellet model "
            "%r; deliver() aborts at "
            "engine/pc_port/pc_p2_preview.cpp:409" % model, True)


def audit_arena(gen_path):
    """Audit a staged ``default.gen`` file read-only; fail closed on inputs.

    Returns row/tlep counts, the stored-order model histogram (decoded to
    retail FourCC), the unregistered-model list and the file sha256. Raises
    FileNotFoundError/ValueError instead of inventing a result.
    """
    path = Path(gen_path)
    if not path.is_file():
        raise FileNotFoundError("staged arena generator missing: %s" % path)
    data = path.read_bytes()
    rows = frame_records(data)
    tlep = []
    for row in rows:
        if len(row) >= OFF_KIND + 4 and row[OFF_KIND:OFF_KIND + 4] == TLEP_KIND:
            tlep.append(parse_tlep(row))
    histogram = {}
    for entry in tlep:
        histogram[entry["model"]] = histogram.get(entry["model"], 0) + 1
    unregistered = sorted(m for m in histogram if classify_delivery(m)[1])
    return {"gen_sha256": hashlib.sha256(data).hexdigest(),
            "gen_bytes": len(data), "rows": len(rows),
            "tlep_records": len(tlep), "tlep_len_ok": all(
                len(r) == TLEP_RECORD_LEN for r in rows
                if r[OFF_KIND:OFF_KIND + 4] == TLEP_KIND),
            "model_histogram": histogram,
            "unregistered_models": unregistered,
            "tlep": tlep}


def check_pod_config(pod_path):
    """Validate a staged ``p2-pod.txt`` against the pinned pod contract."""
    path = Path(pod_path)
    if not path.is_file():
        raise FileNotFoundError("p2-pod.txt missing: %s" % path)
    parts = path.read_text(encoding="utf-8").split()
    if len(parts) != 7 or parts[0] != "P2_POD_1" or parts[5] != "Kochappy":
        raise ValueError("invalid P2 pod config")
    return {"treasure": parts[1], "value": int(parts[2]),
            "weight": int(parts[3]), "capacity": int(parts[4]),
            "corpse_id": parts[5], "corpse_value": int(parts[6])}


FINDING = (
    "needs-engine-change-or-staging-suppression: wild arena pellets "
    "(tlep rows, e.g. model pb01) are spawned by the engine from staged "
    "generator bytes but no receipt branch binds them. The corpses map is "
    "TEKI_Chappy-only (engine/pc_port/pc_p2_preview.cpp:120-121), the "
    "pr05 scan ignores non-pr05 models (:178-202), the draw gate admits "
    "only pr05 (:340), and the aborting pellet carries a null PelletView, "
    "so even the PelletView-keyed corpses map could never match it. "
    "Delivery aborts at engine/pc_port/pc_p2_preview.cpp:409 with "
    "id=0x70623031 ('pb01'). Legitimization needs either staging-side "
    "suppression of non-pr05 tlep rows or an engine-side model/generator-"
    "keyed pellet receipt branch plus shared (#186) review."
)

NEXT_SLICE = {
    "title": "Suppress non-pr05 wild-pellet tlep rows for ch_MAT_route_rover staging",
    "owned_files": [
        "experimental/pikmin2_challenge_wild_pellet_prune.py",
        "tests/test_pikmin2_challenge_wild_pellet_prune.py",
        "docs/PIKMIN2_CHALLENGE_WILD_PELLET_PRUNE.md",
    ],
    "base_pins": {
        # Root pin is this lane's worktree head. The native pin is the #561
        # gen-20 observed short pin; the follow-on slice must resolve the
        # full 40-hex head from the #561 lane record first, else fail closed.
        "root": "3a33cbdefd5e4057eef9fb0d824cce4510ddab05",
        "native_short": "899634a3515c",
        "native_full": "UNRESOLVED-fail-closed",
    },
    "consumer": "p2-challenge-ch_mat_route_rover-p1 (#561)",
    "command": ("run_stageworld_g20.py consumer check against a re-staged "
                "run dir: P2_POD_READY + 7/7 P2_CHALLENGE_* markers + "
                "exit 0 (today exit 3 on unregistered-cargo)"),
    "expected": ("exit 0 with P2_POD_RECEIPT for the staged treasure and no "
                 "Unregistered P2 pod cargo abort; pr05 room-bolt treasure "
                 "path unchanged"),
    "fail_closed": ("abort the prune if the arena holds zero pr05 rows, if "
                    "any kept row fails tlep framing validation, or if the "
                    "output sha256 is not recorded in the slice evidence"),
    # producer_contract kind=diagnosis envelope for the follow-on proposal:
    # concrete pin/ownership deliverables, never an engine unblock claim.
    "producer_contract": {
        "kind": "diagnosis",
        "deliverable": ("audited prune tool + re-staged arena inventory "
                        "proving which tlep rows were dropped/kept"),
        "consumers": [{
            "lane": "p2-challenge-ch_mat_route_rover-p1",
            "command": "run_stageworld_g20.py consumer check (re-staged run)",
            "expected": "exit 0, P2_POD_READY, no unregistered-cargo abort",
        }],
    },
}


def diagnose(gen_path, pod_path=None):
    """Run the full pin-discovery audit; fail closed on missing inputs."""
    audit = audit_arena(gen_path)
    pod = check_pod_config(pod_path) if pod_path is not None else None
    bindings = {m: classify_delivery(m)[0] for m in audit["model_histogram"]}
    return {"citations": CITATIONS, "audit": audit, "pod": pod,
            "bindings": bindings, "finding": FINDING,
            "next_slice": NEXT_SLICE,
            "downstream_consumer": "p2-challenge-ch_mat_route_rover-p1 (#561)",
            "recovery_request": "1282ac9d1a5bce83b7a826f8a9fce7870411e14b3df7507f331770529daf13cb"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gen", required=True,
                        help="staged default.gen path (read-only)")
    parser.add_argument("--pod", default=None,
                        help="staged p2-pod.txt path (read-only, optional)")
    args = parser.parse_args(argv)
    try:
        result = diagnose(args.gen, args.pod)
    except (FileNotFoundError, ValueError) as exc:
        print("wild-pellet pin-discovery refused: %s" % exc, file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
