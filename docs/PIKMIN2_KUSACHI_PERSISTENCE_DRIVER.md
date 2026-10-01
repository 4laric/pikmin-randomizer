# Kusachi P2 persistence driver harness (#758)

Lane `kusachi-persistence-driver`, issue #758 (OPEN, 4laric-assigned; downstream
#533). Implementation owner: Codex through shared account `4laric`. This is a
**tooling** driver harness (not gameplay): it drives save/reload/retry/re-entry
sequences against the wired kusachi stage by generating the harness (commands,
keys, markers, hashed evidence) that downstream #533 executes. No
family/shared/native edits, no runtime run, no ADMIT. All six gates UNTESTED.

## Inputs consumed read-only (never re-derived, never duplicated)

- Integrated #708 persistence wiring (`p2-challenge-persistence-wiring-v1`):
  key shapes (`p2_challenge_<stage>_<field>`) and marker grammar mirrored, not
  re-implemented.
- Integrated #713 native hookup: save/load/clear/highscore/unlock semantics.
- Integrated #728 kusachi content wiring: `content_wired` + boot marker proving
  `ch_NARI_01kusachi` is wired (`content_wired=20 blue-bound boot`).
- Follows the accepted `dangomushi94-fixture-driver` (#667) precedent: a
  separable driver producer for a consumer residual gate set.

## Driver contract

`experimental/pikmin2_kusachi_persistence_driver.py --stage ch_NARI_01kusachi
--wiring <wiring.json> --out <dir>` validates the stage is wired (exact key +
`content_wired` + boot marker, else `DriverRejected` with no writes), generates
the four sequences (save/reload/retry/re-entry) with per-gate markers and
sha256 evidence, and emits `kusachi-persistence-packet.json` naming downstream
#533. Any unwired stage, missing wiring field, or existing packet is refused
fail-closed.

## Owned files (all new)

- `experimental/pikmin2_kusachi_persistence_driver.py`
- `tests/test_pikmin2_kusachi_persistence_driver.py` (10 focused tests, all pass)
- This file.

## Six-gate status (tooling; all UNTESTED, no runtime claim)

| Gate | Status | Evidence | Method |
|---|---|---|---|
| 1-6. all gates | UNTESTED | n/a (harness only) | unobserved |

## Captain safety (#632)

N/A (no runtime run; driver + tests only). Downstream #533 must adopt
`scripts/p2_fixture_captain_guard.h` with orimaDead/NaviDead/HP<=1 checks,
CAPTAIN_DOWN + BLOCKED exit, and a parked captain.