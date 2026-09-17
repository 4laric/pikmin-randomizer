# Forest P1 staged-asset re-run (#660, recovery 91743167)

The done #660 lane proved its fixture builds and guards green, but its headed boot
stalled pre-idle with all boundaries unobserved. The #717 diagnosis proved that stall
class data-dependent: a run root missing `assets/dataDir/SndData` blocks inside
`System::Initialise` (failed DVDOpen of `pikiseq.arc`/`pikibank.bx`, then a blocking OS
wait), while the same executable from a staged asset root reaches idle with a live room.
This slice re-runs the forest P1 fixture from a staged root to observe the boundaries.

## What this adds (three owned files only)

- `experimental/pikmin2_forest_p1_staged_rerun.py`: stages a private run root with the
  forest P1 layout (via the #660 runner read-only: `stage_run_layout`,
  `validate_run_layout`, `verify_run_log`) plus the hash-pinned JAudio asset set
  (`Seqs/pikiseq.arc`, `Banks/pikibank.bx` required; `Banks/*.aw` sibs pinned when
  present). Fail-closed on missing sources, missing members, hash drift and tampered
  layouts. Writes nothing but the run root.
- `tests/test_pikmin2_forest_p1_staged_rerun.py`: JAudio pinning, missing-member and
  missing-manifest refusal, tamper detection, clean validation, missing-runner refusal,
  verifier passthrough/negatives.
- This doc: contract + evidence. Downstream #149 stays OPEN.

## Captain safety #632

Guard `scripts/p2_fixture_captain_guard.h` (sha256 `d2f678c9...`) adopted first via the
#660 fixture (vendored verbatim): orimaDead/NaviDead/HP<=1, CAPTAIN_DOWN exits BLOCKED,
parked captain, no blanket invincibility. Guard self-test + negative re-verified on the
rebuilt exe before the headed run; hashes recorded in the handoff.

## Evidence

- Staged run root: forest P1 `manifest.json` + `session-seed.json` plus pinned
  `assets/dataDir/SndData/*`, validated clean before launch.
- Leased private rebuild of the #660 fixture at the pinned commits (executable hash +
  Ninja no-work recorded); headed run from the staged root, never the bare repo root.
- Per-boundary verdicts from observed markers only (boot, day transition, save/reload,
  receipt replay, exit/reentry); gates claimed solely on observation, UNTESTED otherwise;
  no playability overclaim, no ADMIT, no ledger writes.