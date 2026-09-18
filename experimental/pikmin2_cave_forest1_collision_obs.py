"""Forest_1 P1 criterion-3 observation reader + validator (#773, downstream #154).

Parses a guarded fixture run log for P2_FOREST1_COLLISION_* receipt markers
(actor births, collision contact, route traversal) emitted by
native/tools/p2_forest1_collision_obs_fixture.cpp over the gen-13 staged arena
(P0-derived sidecar, staged geometry, 960x540, starting squad of 20 reds).

Criterion 3 passes ONLY when the log shows, in order, ENTRY_READY then at
least one BIRTH, one CONTACT and one TRAVERSE, then COLLISION_PASS plus
PASS FOREST1_COLLISION_OBS with process exit 0 and no P2_FIXTURE_CAPTAIN_DOWN
anywhere. Anything else is UNTESTED (never PASS by default). Fail-closed on
malformed/missing input. Dependency-free (stdlib only) so the reader runs
anywhere the log is present.
"""

# Receipt-parseable marker contract (native fixture emits these).
MARKERS = (
    "P2_FOREST1_COLLISION_WINDOW",
    "P2_FOREST1_COLLISION_WAIT",
    "P2_FOREST1_COLLISION_ENTRY_READY",
    "P2_FOREST1_BIRTH",
    "P2_FOREST1_CONTACT",
    "P2_FOREST1_TRAVERSE",
    "P2_FOREST1_COLLISION_OBSERVE",
    "P2_FOREST1_COLLISION_PASS",
    "PASS FOREST1_COLLISION_OBS",
    "P2_FIXTURE_CAPTAIN_DOWN",
)

REQUIRED_ORDER = (
    "P2_FOREST1_COLLISION_ENTRY_READY",
    "P2_FOREST1_BIRTH",
    "P2_FOREST1_CONTACT",
    "P2_FOREST1_TRAVERSE",
    "P2_FOREST1_COLLISION_PASS",
    "PASS FOREST1_COLLISION_OBS",
)


class LogError(ValueError):
    pass


def parse_markers(text):
    """Return the ordered marker heads found in a run log. Fail-closed on bad input."""
    if not isinstance(text, str) or not text:
        raise LogError("run log text missing or empty")
    kinds = []
    for line in text.splitlines():
        stripped = line.strip()
        for marker in MARKERS:
            if stripped.startswith(marker):
                kinds.append(marker)
                break
    return kinds


def check_chain(kinds, exit_code):
    """Validate the criterion-3 marker chain. Returns (passed, detail)."""
    if not isinstance(kinds, list):
        return False, "marker list missing"
    if "P2_FIXTURE_CAPTAIN_DOWN" in kinds:
        return False, "captain-down interruption present"
    positions = {}
    for want in REQUIRED_ORDER:
        try:
            positions[want] = kinds.index(want)
        except ValueError:
            return False, "missing marker: " + want
    ordered = [positions[w] for w in REQUIRED_ORDER]
    if ordered != sorted(ordered):
        return False, "markers out of order"
    if kinds.count("P2_FOREST1_BIRTH") < 1:
        return False, "no actor birth observed"
    if kinds.count("P2_FOREST1_CONTACT") < 1:
        return False, "no collision contact observed"
    if kinds.count("P2_FOREST1_TRAVERSE") < 1:
        return False, "no route traversal observed"
    if exit_code != 0:
        return False, "fixture exit was %r, not 0" % (exit_code,)
    return True, "criterion 3 observed: births + contact + traversal with live squad"


def evaluate_run_log(text, exit_code):
    """Full evaluation: parse then check. Returns dict with passed/detail."""
    kinds = parse_markers(text)
    passed, detail = check_chain(kinds, exit_code)
    return {"passed": passed, "detail": detail, "markers": kinds,
            "births": kinds.count("P2_FOREST1_BIRTH"),
            "contacts": kinds.count("P2_FOREST1_CONTACT"),
            "traverses": kinds.count("P2_FOREST1_TRAVERSE")}