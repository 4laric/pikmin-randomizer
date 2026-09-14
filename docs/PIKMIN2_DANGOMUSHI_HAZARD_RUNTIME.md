# DangoMushi Turn window + Rock/Egg hazard runtime evidence (#174 / #376)

Lane 25 third slice: wire the `pc_p2_dangomushi_hazard` policy into the #407
source Crawbster FSM and observe the two previously-unmeasured Turn behaviors at
runtime.

Implementation owner: Codex via shared account `4laric`. Executing session:
opencode (deepseek-v4.1-flash), 2026-09-13.

- Native branch `opencode/p2-crawbster-hazard-native` @ `0140fb56`, base
  `8ae1e5b4` (`opencode/p2-species-snagret`, never pushed to native origin),
  worktree `output/native-lane25-crawbster`, build
  `output/native-lane25-crawbster-build`.
- Patch bundle: `native-candidates/dangomushi-hazard-host/`.

## What changed

- `pc_port/pc_p2_dangomushi.cpp`: includes and drives
  `P2DangoMushiHazardPolicy` in the `DANGO_TURN` state. On Turn entry it emits
  the Rock/Egg decisions; it tracks/announces the stickable window; on Turn exit
  it notifies the policy. The captain share is
  `GameStat::formationPikis / GameStat::allPikis`.
- `pc_port/pc_p2_dangomushi_hazard.{h,cpp}`: copied from the reviewed
  maintained-line module (unchanged).
- `CMakeLists.txt`: add the hazard source.
- `experimental/pikmin2_dangomushi_behavior.py` + its test now parse and require
  the new markers (`turn_window`, `hazard_rain`); `hazard_egg` is informational.

## Fixture baseline adoption

| Field | Value |
|---|---|
| Root / child revision | `kimi/p2-bulblax-import` @ `6e1094a` (harness/validator); native @ `0140fb56`, base `8ae1e5b4` |
| Private build | `output/native-lane25-crawbster-build`, `[525/525]` link, exit 0 |
| Executable SHA-256 | `282BAD9B000E8B1D8E4359EC3176B9DBCD9A38A8A550C08EFD5A706716C966D3` |
| Window | `PIKMIN_P2_ROOM_WINDOW=960x540`; `window: true`, log line "Experimental preview window set to 960x540 windowed and centered" |
| Squad | DangoMushi fixture's explicit 20-red squad (custom runner; documented equivalent starting squad, not the shared overlay) |
| Run directory | `output/p2-lane25-crawbster-run3/e1ce0fff75fd48a38398aacca51e7830` |
| `native.log` SHA-256 | `5B6FFEF67B9C71EFC492CF5ABD9F3B9291AEEC3073E7170833AC62D1E8EC93FD` |
| Result | `dangomushi-validation.json` `passed=true`; `turn_window=true`, `hazard_rain=true` |

## Observed markers

```
P2_DANGOMUSHI_TURN_WINDOW generator=376003 frame=32.0 stickable=1 invulnerable=0
P2_DANGOMUSHI_TURN_WINDOW generator=376003 frame=108.5 stickable=0 invulnerable=1
P2_DANGOMUSHI_HAZARD generator=376003 rocks=10 lifetime=30.0 egg=0
```

The window opens at the turn clip loop-start key (32) and closes at key 3 (108),
matching the source audit. The Rock rain requests 10 Rocks with a 30 s lifetime
per Turn; the Egg decision is a probability and was 0 this run (`hazard_egg` is
informational for that reason).

## Six-gate status

| Gate | Status | Note |
|---|---|---|
| 1. Exact identity and spawn | PASS | existing fixture markers |
| 2. Autonomous movement and animation | PASS | existing FSM states |
| 3. Attacks and receivers | PARTIAL | roll contact as before; window now applied by the follow-up damage gate ([vuln-apply slice](PIKMIN2_DANGOMUSHI_VULN_APPLY.md)) |
| 4. Death and corpse | UNTESTED | unchanged |
| 5. Actual transport and reward | source-backed generic | unchanged |
| 6. Cleanup and re-entry | UNTESTED | unchanged |

This is a decision-observer slice, not a damage/flag application or a real
Rock/Egg birth.

## Remaining

1. The P1 proxy host had no `EB_Invulnerable` path; the follow-up slice applies
   the stickable window through `pc_p2_dangomushi_invulnerable`
   ([vuln-apply slice](PIKMIN2_DANGOMUSHI_VULN_APPLY.md)), pending a real-GL run.
2. Real Rock/Egg births need lane 20 primitives.
3. True `InteractPress` roll crush, `wallCallback` crash trigger and
   `dangomushi.brk` remain.
4. Death/corpse/cleanup (#397).
