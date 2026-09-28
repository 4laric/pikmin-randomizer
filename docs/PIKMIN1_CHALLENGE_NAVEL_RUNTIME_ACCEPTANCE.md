# P1 Challenge Navel runtime acceptance (#563)

Lane p1-challenge-navel-runtime-acceptance. Consumes the landed #649 guarded
boot fixture read-only (fixture TU, harness build(), input package
validate_run_log, boot evidence) plus the #52 campaign contract. Owns only the
acceptance driver, its tests and this doc. No shared/maintained/native edits,
no harness duplication, no ADMIT.

## Pins

- Fixture source: #649 native worktree at pinned head
  `c549997e7bdf66fb09c0f0756c56e65fdad55861`
  (`output/workflow/autofill/planning-shards/p1-challenge/prepared/p1-challenge-guarded-runtime-native`,
  clean); fixture fragment `tools/p2_challenge_guarded_boot_fixture.cpp`
  sha256 `950c9222fae306ee3149ae7beb576d7ce525f95e6b00463e981cccee2aee6c1b`.
  Guard is vendored verbatim in the fixture and runs every idle call;
  canonical `scripts/p2_fixture_captain_guard.h` sha256
  `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`
  recorded at runtime by guard_record (fail-closed on drift).
- Harness: #649 `scripts/build_p2_challenge_guarded_boot_fixture.py` build()
  plus shared replacement-main `scripts/build_pikmin2_fixture.py`; the private
  leased build dir is
  `output/workflow/autofill/planning-shards/p1-challenge/prepared/p1-challenge-navel-runtime-acceptance-output/build`.
- Input package: `experimental/pikmin2_challenge_runtime_inputs.py`
  validate_run_log called for the observed/blocked verdict (fresh run:
  observed=true, blocked=false, levels=[2]).
- Contract: p1-challenge-campaign-contract lane (#52, done); module
  `experimental/pikmin1_challenge_campaign_contract.py` at pin
  `9aa6faad2c76b3182b5ad3de3f564d5e5431ba90` sha256
  `21e1caf02eda06acd9f686bf1b72bce2d6ea3bf366594bb2e8cb416c3aff1b87`
  (chal2 = Navel, area_id 2, ini `dataDir/stages/chal2.ini`).
- Assets: user-owned dataDir with `stages/chal2.ini` sha256
  `1a16d0e61c19c1e919a9f48459b8795f52980f448ffa8739a59a6255c51837ed` and
  `stages/chal2/default.gen` sha256
  `de45c8afcb6ae54d8c4b63b38e535e37e1e3b670eff6af97c0f44e50055914ba`;
  per-run fresh directory with assets junction.

## Consumption command

Run the driver phases from the lane root worktree:

    py scripts/p1_challenge_navel_runtime_acceptance.py --native <649-native>
      --build <private-build> --output <out> --expected-native-head c549997e...
      build run observe guard

The build phase configures the private dir, builds pikmin_pc, links the fixture
via the #649 harness build(), and records the ninja dry run. The run phase
launches the headed boot (`--experimental-challenge-level 2`) with a fresh
assets junction and stops the checklist once layout, generator output, squad,
window and frames are all observed. The observe phase maps the log to facts
plus gate verdicts and calls the #649 validate_run_log. The guard phase
compiles and runs a forced captain-down TU against the canonical header
(expect exit 86 + CAPTAIN_DOWN, no PASS).

## Observed vs not observed

Fresh run `acceptance/runs/c977a251af07423496550ae43a4a71d8` (exit 0, no
CAPTAIN_DOWN), native.log sha256
`700b3d4b45d8b2e2e69658dfc8926211c4241e44112f9f610ebc3b9e0424fbcf`:
CHALLENGE_LAYOUT_READY id=challenge-2 stage_index 18 file=stages/chal2.ini
story=1; 98 recognised generators with 122 spawned creatures (plus 38 plant
generators/creatures); 20-piki squad; 960x540 centred-window log lines; 3 FPS
frames; `P2_CHALLENGE_BOOT level=2 slot=chal2`;
`PASS P2_CHALLENGE_GUARDED_BOOT boot1 squad_alive`; captain parked
(`P2_CHALLENGE_PARK`); exit 0 with no CAPTAIN_DOWN. Gate identity_spawn PASS
(natural); gates 2-6 UNTESTED (boot-only observation; no movement, combat,
death, transport or reentry observed).

Private build: native commit c549997e (pinned, drift-refused); fixture.exe
sha256 `9726f014632c5c3c683c862a317493652b4c5e489de65c024b96437f1907d250`;
`ninja -n` dry run `ninja: no work to do.`; exclusive registry build lease
acquired before build/run and released after driver exit (self-release is
rejected while the holder is alive, so the caller releases post-exit).
Replacement-main note: the observed exe is the landed #649 replacement-main
fixture rebuilt privately from its pinned commit; this lane owns no native
files, so the handoff records replacement_main=false with the #649
provenance attached as supplementary build evidence rather than bound to the
lane tree.

## Captain safety #632

The fixture calls the canonical guard every idle before pause/movie/UI
returns; the driver fail-closes on guard hash drift and on any CAPTAIN_DOWN
(all gates BLOCKED, never PASS). Negative TU: exit 86,
`P2_FIXTURE_CAPTAIN_DOWN tick=7`, no PASS (`guard-negative.log`). Policy:
unprotected observation (no invincibility, no health edits; parking is the
fixture's prescribed non-combat placement, not protection). Guard/source/exe
hashes recorded above.

## Remaining scope

chal3 Spring and chal4 Trial runtime acceptance stay next scope (chal4 blocked
on the pre-existing PIKI BIRTH panic); #52 follow-on scope 1 (resource/timing
audit) stays open. No ADMIT, no gameplay acceptance beyond the observed boot.
