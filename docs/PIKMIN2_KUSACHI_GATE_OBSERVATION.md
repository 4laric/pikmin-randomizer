# Kusachi six-gate + P2 persistence observation (#818)

Lane `kusachi-gate-persistence-observation`: bounded runtime_check observation of
the EXISTING verified kusachi wiring (native pin `704bad6c`, accepted #728
wiring; callsites `pc_port/pc_p2_challenge_content.cpp:90` and
`tools/p2_kusachi_content_wiring_fixture.cpp:203`, read-only) for downstream
`p2-challenge-ch_nari_01kusachi-p1` (#533). Runtime check only: existing
callsites and membership identified without changing them; never an engine
unblock. No ADMIT.

## Method

Build the existing fixture via canonical leased private build dir, boot headed
(`--experimental-pikmin2-room --experimental-challenge-stage ch_nari_01kusachi`)
under guard #632, parse `P2_CHALLENGE_CONTENT_WIRED` /
`P2_KUSACHI_CONTENT_WIRING_STAGE` plus gate markers with
`experimental/pikmin2_kusachi_gate_observation.py`, and exercise
save/reload/retry/re-entry where the port emits markers. Per-gate verdicts are
observed only on evidence, otherwise honest UNTESTED/BLOCKED with the exact
blocker.

## Gates

`identity_spawn` is observed on wiring+stage+PASS; the other five gates stay
UNTESTED unless gate-specific combat/death/corpse/re-entry evidence appears in
the run log. Persistence is observed only when all four save markers appear.

## Evidence

- `tests/test_pikmin2_kusachi_gate_observation.py` (fail-closed parser tests).
- Leased build record (commit, exe SHA-256, ninja no-work) and headed run log
  with #632 adoption hashes.

## Captain safety (#632)

Mandatory: `orimaDead`, `NaviDead`, HP<=1 -> `CAPTAIN_DOWN`, exit BLOCKED
(`scripts/p2_fixture_captain_guard.h` sha256
`d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474` vendored
verbatim into the fixture). Park the captain outside attack reach. No blanket
invincibility; protected observation is labelled.
