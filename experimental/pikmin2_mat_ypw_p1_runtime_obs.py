"""ch_MAT_yellow_purple_white P1 runtime observation helpers (issue #552).

Lane p2-challenge-ch-mat-ypw-p1-runtime-obs. Reuses the done P1 content
lane read-only (its adapter, manifest validation and run-layout staging are
never forked or re-owned) and the accepted content-loading binder contract
read-only. This module only: stages a fresh run dir (P1 run layout +
P2_CHALLENGE_CONTENT_1 sidecar + generator manifest from real decoded
tokens), parses a runtime marker log with a strict verdict, and records the
#632 guard hash. No engine/family/shared edits, no ADMIT, no ledger writes,
no invented values: spawn intents mirror the real decoded TekiInfo rows.
"""
import hashlib
import importlib.util
import json
import re
from pathlib import Path

CAVE_ID = "ch_MAT_yellow_purple_white"
ISSUE = 552
SIDECAR_MAGIC = "P2_CHALLENGE_CONTENT_1"
GUARD_PATH = "scripts/p2_fixture_captain_guard.h"
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"

# Real decoded TekiInfo rows (hash-verified disc bytes; token + row count).
# Counts are definition-row counts, never observed spawn instances.
REAL_SPAWNS = (("FminiHoudai_key", 1), ("ElecBug_wadou_kaichin", 2),
               ("GasHiba", 1))
REAL_POOL = "1_MAT_tower2_toy.txt"
ANCHOR = "hole"

REQUIRED_MARKERS = ("P2_CHALLENGE_CONTENT_SELECTED",
                    "P2_CHALLENGE_CONTENT_SPAWN_COVERED",
                    "P2_CHALLENGE_CONTENT_READY",
                    "P2_CHALLENGE_CONTENT_LIVE",
                    "PASS P2_CHALLENGE_CONTENT_RUN")
FAIL_TOKENS = ("P2_FIXTURE_CAPTAIN_DOWN", "duplicate treasure",
               "P2_CHALLENGE_CONTENT_REFUSED", "P2 preview: duplicate")
INJECTED_TOKENS = ("P2_MAT_YPW_INJECT", "mat-ypw-inject", "injection=1")


class ObsError(ValueError):
    """Malformed input or illegal run configuration."""


def workspace_root():
    return Path(__file__).resolve().parents[2]


def p1_adapter(root=None):
    """Load the done P1 content adapter by path (reuse, never fork)."""
    base = Path(root) if root is not None else workspace_root()
    path = base / "experimental" / "content_lanes" / "ch_mat_yellow_purple_white.py"
    if not path.is_file():
        raise ObsError("P1 adapter missing: %s" % path)
    spec = importlib.util.spec_from_file_location("mat_ypw_p1_content", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_file(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def render_sidecar(cave_id=CAVE_ID, floor=1, pool=REAL_POOL,
                   spawns=REAL_SPAWNS, anchor=ANCHOR):
    """Render P2_CHALLENGE_CONTENT_1 text from real decoded tokens."""
    if cave_id != CAVE_ID:
        raise ObsError("sidecar stage mismatch")
    if type(floor) is not int or floor != 1:
        raise ObsError("sidecar floor must be 1")
    if not pool or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", pool):
        raise ObsError("sidecar pool refused")
    if not spawns:
        raise ObsError("sidecar roster is empty")
    lines = [SIDECAR_MAGIC, "stage %s %d" % (cave_id, floor), "pool %s" % pool]
    seen = set()
    for token, count in spawns:
        if (not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", token or "")
                or type(count) is not int or not 1 <= count <= 10000
                or token in seen):
            raise ObsError("sidecar spawn refused: %r" % (token,))
        seen.add(token)
        lines.append("spawn %s %d" % (token, count))
    if anchor not in ("hole", "geyser"):
        raise ObsError("sidecar anchor refused")
    lines.append("anchor %s" % anchor)
    return "\n".join(lines) + "\n"


def render_generate_manifest(spawns=REAL_SPAWNS):
    """Minimal generator manifest: spawn intents the binder scans."""
    if not spawns:
        raise ObsError("generate manifest needs spawns")
    return "".join("spawn %s %d\n" % (token, count) for token, count in spawns)


def stage_fresh_run(output, root=None, native_root=None):
    """Stage a fresh run dir: P1 layout + sidecar + manifest + run config.

    Reuses the done P1 adapter's manifest validation and run-layout staging
    verbatim. Returns {files: {name: sha256}} for the evidence record.
    """
    adapter = p1_adapter(root)
    manifest = adapter.default_manifest(root)
    staging = adapter.validate_p1_manifest(manifest, root=root)
    output = Path(output)
    if output.exists():
        raise ObsError("run dir must be fresh")
    adapter.stage_run_layout(manifest, output, root=root, native_root=native_root)
    sidecar = render_sidecar()
    generate = render_generate_manifest()
    (output / "p2-challenge-content.txt").write_text(sidecar, encoding="ascii")
    (output / "p2-cave-generate.txt").write_text(generate, encoding="ascii")
    (output / "run-config-obs.json").write_text(json.dumps({
        "cave_id": CAVE_ID, "issue": ISSUE, "floor": 1,
        "window": "960x540", "captain_guard": GUARD_PATH,
        "guard_sha256": GUARD_SHA256, "staging": staging,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    files = {}
    for child in sorted(output.iterdir()):
        if child.is_file():
            files[child.name] = sha256_file(child)
    return {"run_dir": str(output), "files": files,
            "squad_total": staging["squad_total"]}


def guard_record(root=None):
    """Hash the canonical #632 guard header read-only; fail closed on drift."""
    base = Path(root) if root is not None else workspace_root()
    path = base / Path(*GUARD_PATH.split("/"))
    if not path.is_file():
        raise ObsError("guard header missing: %s" % GUARD_PATH)
    digest = sha256_file(path)
    if digest != GUARD_SHA256:
        raise ObsError("guard header drifted: %s" % digest)
    return {"path": GUARD_PATH, "sha256": digest}


def read_run_log(text):
    """Parse a runtime marker log into observations with a strict verdict.

    Returns (observations, passed). passed requires every REQUIRED_MARKERS
    prefix present, no FAIL_TOKENS, no INJECTED_TOKENS. Nothing is inferred:
    counts come only from marker lines actually present.
    """
    if not isinstance(text, str) or not text.strip():
        raise ObsError("empty marker log")
    if any(token in text for token in INJECTED_TOKENS):
        return {"injected": True}, False
    found = {marker: (marker in text) for marker in REQUIRED_MARKERS}
    # Bare FAIL matches only as a standalone verdict token (not the benign
    # engine "FAILED to open <optional asset>" probe noise seen on good runs).
    failed_fail = re.search(r"(?:^|\s)FAIL(?:\s|$)", text) is not None
    failed = failed_fail or any(token in text for token in FAIL_TOKENS)
    squad = None
    match = re.search(r"squad=(\d+)", text)
    if match:
        squad = int(match.group(1))
    actors = None
    match = re.search(r"actors=(\d+)", text)
    if match:
        actors = int(match.group(1))
    # The content fixture inherits centred-window setup from the production
    # room entrypoint and logs "(960x540)" at init; it emits no size= marker,
    # so resolution presence (not a size= token) is the honest signal here.
    window = "960x540" in text
    observations = {"markers": found, "failed_tokens": failed,
                    "squad": squad, "actors": actors, "window_960": window}
    passed = all(found.values()) and not failed
    return observations, passed
