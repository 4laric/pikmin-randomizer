# Demon escape bridge successor (#231)

Based on226 ce95fcc7. Preserve that delivered worktree. This successor wires
the tested input window into the P1 captain bridge and adds a distinct detached
fall phase. Native compile succeeds against frozenhost756515d5; pure escape
regression passes. It has not been linked into the game or exercised live.

Call pc_demon_escape_tick once per authoritative source update after supplying
current mouth pose and sampling a directional button-down edge. RNG callback
must be a pure source-compatible sampler returning [0,1), without mutating
bridge/game state. Paused/inactive simulation must not call it. It preserves
short-circuit draw consumption and sets source animation speed. On success,
the binding is revoked, FALL starts, and prior floor contact is cleared.

The detached fall record blocks ordinary AI/walk animation but does NOT block
Creature::update, allowing native gravity/terrain motion. Draw falls back to
ordinary upright captain transform. Fresh ground contact or bounce clears
the phase and resumes Walk. External Flick/Dead/stick/rope interruption clears
the phase without rewriting that state. forget clears both binding and exit
records before captain/scene destruction. Acquire refuses a pending exit.

Updated precise patch replaces bound with controls_blocked only for AI and
walk animation. Apply remains binding-only for physics, and full matrix draw
remains binding-only. It adds a Navi::isAtari false gate during falling and a
bounceCallback landing notification. The input sampling/RNG call is intentionally
not guessed into P1 controller code: integration must establish source edge
mapping and timing before installing that call. CMake/teardown remain root-owned.

P1 compatibility limits: this is an explicit bridge phase while native state
ID remains Walk, not a translated P2 SaraiExit state. Object collision false
must be tested independently from terrain collision/gravity. Capture remains
limited to Walk and a single captain. Explicit manual release and owner loss
retain226 fallback semantics; only successful escape enters this fall phase.
Source owner flick/drop behavior still needs receiver integration. No full
capture/escape acceptance follows from compilation or pure-window tests.

Required live gates: input consumed once, six-edge threshold/RNG behavior,
stable captured matrix, airborne control suppression with active gravity,
no stale-ground immediate landing, restored object collision/control after
actual floor bounce, interruption preservation and teardown/re-entry.

Source audit: Creature::moveNew (creatureMove.cpp:139-141) applies gravity independently of Navi AI; ordinary Creature::update must continue during exit. Flying, IgnoreGravity, and DisableMovement flags can still inhibit movement; integration must verify ordinary captain flags in the live fixture. The bridge does not overwrite external physics flags. Atari queries reconcile landing/interruption before suppressing collision, avoiding stale suppression after a state change.
