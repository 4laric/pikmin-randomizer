"""Legal single-pr05 cave arena overlay / p2-cargo input provider (#654).

Root-only fixture-baseline input provider for the guarded cave boot (#642)
and its consumers (#161 yakushima4 P1, #154 forest1 P1). The guarded boot
reaches the 960x540 window then aborts at pc_p2_preview.cpp:128
("P2 preview: duplicate treasure") when the staged arena exposes more than
one pr05 treasure pellet with no p2-cargo.txt binding them.

This module decodes real arena treasure/cargo inputs with the REAL shared
parsers (read-only reuse, never edited), evaluates the EXACT native boot
predicate, and emits a LEGAL overlay: either a pruned single-pr05 arena gen
or a strict P2_CARGO_1 package binding every pr05 generator exactly once,
plus a machine-readable input package. No generator, save, scoring, combat
or receiver semantics. No invented values: caller supplies the arena bytes
and any cargo specs; malformed input fails closed.
"""
import hashlib
import struct

from scripts.preview_pikmin2_room import records
from experimental.pikmin2_cargo import read_cargo

POLICY = "P2_CAVE_ARENA_OVERLAY_1"
PACKAGE_SCHEMA = "p2-cave-arena-overlay-1"
# Little-endian bytes of the pr05 treasure scaffold model id, as observed in
# real staged chal0 arenas (24 rows, one preview treasure bolt).
PR05_MODEL = b"50rp"
PR05_LABEL = b"preview treasure bolt"
# Canonical #632 guard header, consumed read-only; hash pinned by the slice
# brief and re-verified here. Never reimplemented.
GUARD_PATH = "scripts/p2_fixture_captain_guard.h"
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"
DOWNSTREAM = ["#161", "#154", "#642"]


class ArenaOverlayError(ValueError):
    """Raised for malformed inputs and illegal boot configurations."""


def sha256_bytes(data):
    if not isinstance(data, (bytes, bytearray)) or not data:
        raise ArenaOverlayError("non-empty bytes required")
    return hashlib.sha256(bytes(data)).hexdigest()


def guard_record(root):
    """Hash the canonical guard header read-only; fail closed on drift."""
    from pathlib import Path
    path = Path(root) / GUARD_PATH
    if not path.is_file():
        raise ArenaOverlayError("guard header missing: " + GUARD_PATH)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != GUARD_SHA256:
        raise ArenaOverlayError("guard header drifted: " + digest)
    return {"path": GUARD_PATH, "sha256": digest}


def decode_arena_gen(gen_bytes):
    """Decode arena generator bytes into treasure inventory with real framing.

    Returns dict with row count, header count and the pr05 record list
    [{generator_id, label, position}]. generator_id is the little-endian
    u32 at offset 8, matching the roster/native generator convention.
    """
    if not isinstance(gen_bytes, (bytes, bytearray)):
        raise ArenaOverlayError("arena bytes required")
    import tempfile
    from pathlib import Path
    try:
        with tempfile.TemporaryDirectory() as tmp:
            probe = Path(tmp) / "default.gen"
            probe.write_bytes(bytes(gen_bytes))
            rows = records(probe)
    except ValueError as exc:
        raise ArenaOverlayError("invalid arena framing: %s" % exc)
    pr05 = []
    for row in rows:
        if row[80:84] == PR05_MODEL:
            pr05.append({
                "generator_id": struct.unpack_from("<I", row, 8)[0],
                "label": row[16:48].rstrip(b"\x00").decode("ascii", "replace"),
                "position": list(struct.unpack_from(">6f", row, 48)[:3]),
            })
    header_count = struct.unpack_from(">I", bytes(gen_bytes), 20)[0]
    return {"rows": len(rows), "header_count": header_count,
            "sha256": sha256_bytes(gen_bytes), "pr05": pr05}


def decode_run_inputs(run_dir):
    """Decode cargo inputs present in a staged run directory (read-only)."""
    from pathlib import Path
    run = Path(run_dir)
    if not run.is_dir():
        raise ArenaOverlayError("run directory missing")
    cargo_path = run / "p2-cargo.txt"
    free_path = run / "p2-cargo-free.txt"
    specs = read_cargo(cargo_path) if cargo_path.is_file() else None
    free = False
    if free_path.is_file():
        if free_path.read_bytes() != b"P2_CARGO_FREE_1\n":
            raise ArenaOverlayError("invalid p2-cargo-free.txt content")
        free = True
    if specs is not None and free:
        raise ArenaOverlayError("cargo and cargo-free configs conflict")
    return {"has_cargo": specs is not None,
            "has_cargo_free": free,
            "has_pod": (run / "p2-pod.txt").is_file(),
            "cargo_specs": specs}


def evaluate_boot_predicate(decoded, run_inputs):
    """Mirror the pc_p2_preview_setup treasure/cargo abort logic.

    Returns a verdict dict. `abort-*` verdicts name the exact native abort
    the configuration would hit; `legal-*` verdicts are bootable.
    Live-actor/generator count agreement is runtime-checked and recorded
    as a limitation, not decided here.
    """
    pr05 = decoded["pr05"]
    ids = [r["generator_id"] for r in pr05]
    if len(set(ids)) != len(ids):
        return {"verdict": "abort-duplicate-generator",
                "detail": "arena carries duplicate pr05 generator ids"}
    if run_inputs["has_cargo_free"]:
        if pr05:
            return {"verdict": "abort-duplicate-treasure",
                    "detail": "cargo-free arena must carry zero pr05 rows"}
        return {"verdict": "legal-cargo-free", "detail": "no pr05 rows"}
    if run_inputs["has_cargo"]:
        spec_ids = [s["generator"] for s in run_inputs["cargo_specs"]]
        unbound = sorted(set(ids) - set(spec_ids))
        missing = sorted(set(spec_ids) - set(ids))
        if unbound or missing:
            return {"verdict": "abort-cargo-binding",
                    "detail": "unbound=%s missing=%s" % (unbound, missing)}
        return {"verdict": "legal-cargo",
                "detail": "every pr05 generator bound exactly once"}
    if len(pr05) > 1:
        return {"verdict": "abort-duplicate-treasure",
                "detail": "%d pr05 rows and no p2-cargo.txt" % len(pr05)}
    if not pr05:
        return {"verdict": "no-treasure",
                "detail": "no pr05 row; treasure boot never becomes ready"}
    return {"verdict": "legal-single-treasure",
            "detail": "exactly one pr05 row"}


def emit_single_pr05_overlay(gen_bytes, keep_generator_id=None):
    """Prune an arena gen to exactly one pr05 row (deterministic).

    Keeps every non-pr05 row untouched and retains one pr05 row: the
    lowest generator id, or keep_generator_id (which must exist). The
    header count is repacked. Returns (overlay_bytes, sha256).
    """
    decoded = decode_arena_gen(gen_bytes)
    if not decoded["pr05"]:
        raise ArenaOverlayError("no pr05 row to keep")
    keep = keep_generator_id
    if keep is None:
        keep = min(r["generator_id"] for r in decoded["pr05"])
    if keep not in [r["generator_id"] for r in decoded["pr05"]]:
        raise ArenaOverlayError("keep id is not a pr05 generator")
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "default.gen"
        probe.write_bytes(bytes(gen_bytes))
        rows = records(probe)
    kept = [r for r in rows
            if r[80:84] != PR05_MODEL
            or struct.unpack_from("<I", r, 8)[0] == keep]
    if sum(1 for r in kept if r[80:84] == PR05_MODEL) != 1:
        raise ArenaOverlayError("overlay must carry exactly one pr05 row")
    header = bytearray(bytes(gen_bytes)[:24])
    struct.pack_into(">I", header, 20, len(kept))
    overlay = bytes(header) + b"".join(kept)
    check = decode_arena_gen(overlay)
    if check["rows"] != len(kept) or len(check["pr05"]) != 1:
        raise ArenaOverlayError("overlay reparse mismatch")
    return overlay, sha256_bytes(overlay)


def emit_cargo_package(decoded, specs):
    """Render a strict P2_CARGO_1 text binding every pr05 generator once.

    specs is caller-supplied [{generator, instance, model, value, weight,
    slots}] (roster/content facts); nothing is invented. The generator set
    must equal the arena pr05 set exactly. Returns (cargo_text, package).
    """
    if not isinstance(specs, list) or not specs:
        raise ArenaOverlayError("caller cargo specs required")
    arena_ids = sorted(r["generator_id"] for r in decoded["pr05"])
    if not arena_ids:
        raise ArenaOverlayError("no pr05 rows to bind")
    lines = ["P2_CARGO_1", str(len(specs))]
    for spec in specs:
        try:
            row = "%d %s %s %d %d %d" % (
                spec["generator"], spec["instance"], spec["model"],
                spec["value"], spec["weight"], spec["slots"])
        except (KeyError, TypeError) as exc:
            raise ArenaOverlayError("malformed cargo spec: %s" % exc)
        lines.append(row)
    text = "\n".join(lines) + "\n"
    from pathlib import Path
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "p2-cargo.txt"
        probe.write_text(text, encoding="ascii")
        try:
            parsed = read_cargo(probe)
        except ValueError as exc:
            raise ArenaOverlayError("invalid cargo text: %s" % exc)
    if sorted(s["generator"] for s in parsed) != arena_ids:
        raise ArenaOverlayError("cargo generators must equal arena pr05 set")
    package = {"schema": PACKAGE_SCHEMA, "policy": POLICY,
               "arena_sha256": decoded["sha256"],
               "pr05_generators": arena_ids,
               "cargo_sha256": hashlib.sha256(text.encode("ascii")).hexdigest(),
               "downstream": list(DOWNSTREAM)}
    return text, package


def input_package(decoded, run_inputs, guard, emitted_sha256=None):
    """Machine-readable input package for the guarded boot consumer."""
    verdict = evaluate_boot_predicate(decoded, run_inputs)
    return {"schema": PACKAGE_SCHEMA, "policy": POLICY,
            "arena_sha256": decoded["sha256"],
            "pr05_generators": sorted(r["generator_id"]
                                      for r in decoded["pr05"]),
            "cargo_present": run_inputs["has_cargo"],
            "cargo_free": run_inputs["has_cargo_free"],
            "pod_present": run_inputs["has_pod"],
            "guard": dict(guard),
            "verdict": verdict["verdict"],
            "emitted_sha256": emitted_sha256,
            "downstream": list(DOWNSTREAM),
            "limitations": ["Live-actor/generator count agreement is "
                            "runtime-checked by the boot fixture, not here."]}
