# P1 Challenge guarded boot fixture (prerequisite lane, #649)

Owner: Codex through shared account `4laric`. Lane
`p1-challenge-guarded-runtime-fixture` (tooling, generation 2). This is the
missing runtime-observation producer for the five vanilla P1 Challenge stages
(chal0..chal4: Impact, Forest, Navel, Spring, Trial): a real game-linked
replacement-main guarded boot fixture plus a machine-readable input package,
so the #52 campaign contract follow-on scope 1 becomes executable. No new
generator, save, scoring or combat semantics; no gameplay claims.

## Pin discovery (part of this job)

- Campaign contract: commit `9aa6faad2c76b3182b5ad3de3f564d5e5431ba90`
  (`codex/content-lanes-531`) holds
  `experimental/pikmin1_challenge_campaign_contract.py` (263 lines: stage
  table, check IDs, attempt/persistent boundary, per-stage audits).
- Canonical base `ecf5f53a` carries the guard but NOT the contract module.
- Decision: consume the contract read-only from its recorded commit (the
  inputs module imports it from a `git show` snapshot; exact pin recorded in
  every packet). NOT merged: the contract file is owned by the
  p1-challenge-campaign-contract lane, and merging would duplicate its scope
  into this tree.
- Captain guard: canonical `scripts/p2_fixture_captain_guard.h` sha256
  `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`,
  consumed read-only and vendored verbatim into the fixture.

## Owned files

- `native/tools/p2_challenge_guarded_boot_fixture.cpp`: replacement-main
  RoomApp fragment. Guard runs FIRST on every idle call (orimaDead/NaviDead/
  HP<=1 -> `P2_FIXTURE_CAPTAIN_DOWN` + exit 86 BLOCKED); requires
  `--experimental-challenge-level 0-4`; parks the captain once far outside
  attack reach (`P2_CHALLENGE_PARK`); logs `P2_CHALLENGE_BOOT level=N
  slot=chalN` + `P2_CHALLENGE_SQUAD`; exits `PASS
  P2_CHALLENGE_GUARDED_BOOT` after stable observation. PASS means boot
  observed, never gameplay.
- `scripts/build_p2_challenge_guarded_boot_fixture.py`: provenance-checked
  replacement-main build through the shared fixture builder (unmodified).
- `experimental/pikmin2_challenge_runtime_inputs.py`: input-package builder
  (per-stage slot/area/ini+hash, challenge-level argv, launch env,
  acceptance checklist) + fail-closed validator + run-log mapper (boot
  observed vs captain-down blocked).
- `tests/test_pikmin2_challenge_runtime_inputs.py`: 7 passed (contract load
  from pin, package round-trip, malformed rejection, boot acceptance,
  captain-down blocked mapping, empty-run rejection).
- This file.

## Per-stage consumption

```
py -3.12 -m experimental.pikmin2_challenge_runtime_inputs --root <root> --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets --output <out>
<exe> --experimental-challenge-level <0-4>
```

Environment: `PIKMIN_P2_ROOM_WINDOW=960x540`, `SDL_AUDIODRIVER=dummy`,
`PYTHONUTF8=1`. Each stage needs its `dataDir/stages/chalN.ini` present
(all five verified in the P1 asset tree).

## Remaining work (follow-on, not this slice)

- Per-area stage content boot validation (mapMgr course loading per chalN).
- Starting-squad/timer/scoring/ retry acceptance per the contract's
  explicitly-unverified list (consumer issues #563-#567, #52 stay OPEN).
- Full content issue #649 stays OPEN; no ADMIT.