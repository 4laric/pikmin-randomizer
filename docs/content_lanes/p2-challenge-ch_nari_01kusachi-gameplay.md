# ch_NARI_01kusachi natural gameplay observation (#780)

Lane `kusachi-gameplay-obs`, issue #780, parent #533. Runtime slice; **not**
gameplay acceptance and no ADMIT. Conclusion: **blocked** on a reproducible
content blocker after the guarded boot produced only two of six gates.

## Pins and guard

- root `36b868391e62cccf37d992aa2f796f3cc9c6dc31`,
  worktree `output/workflow/autofill/planning-shards/challenge-3/prepared/kusachi-gameplay-root`
- native `68ac74966100b65b9353322257ad831ce1c0b615` (clean),
  worktree `output/workflow/autofill/planning-shards/challenge-3/prepared/kusachi-gameplay-native`
- captain guard #632: `scripts/p2_fixture_captain_guard.h`
  sha256 `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`,
  vendored verbatim into the observer. Guard self-test 7/7 rows PASS; negative
  test exits 86 and prints `P2_FIXTURE_CAPTAIN_DOWN`. The guard runs
  immediately after engine idle and before any movie/pause/overlay return or
  observed tick. Unprotected policy: the captain is never health-modified.

## What ran

A private replacement-main observer (not a native repo edit) boots the real
engine with `--experimental-pikmin2-room --experimental-challenge-stage
ch_NARI_01kusachi`, stages a centred 960x540 window, and reads only engine
state. Built with a leased private `pikmin_pc` build (`workflow_native_build`)
plus a private response-file fixture link that compiles the #728 content module
and the observer TU.

- native build executable `output/kusachi-gameplay-obs-build/bin/nectar.exe`
  sha256 `1b13fb70354e0f324f20fc00002c7a994ab13b823eaabdac6486489425c1ff25`;
  `ninja -n pikmin_pc` -> `ninja: no work to do.`
- observer fixture sha256 `da8e38edb315e79a9b864c35e67c7f8d67675139dde1f7c0199c3888ab8b3028`
  (provenance `16967f25...`), 18.9 s headed run, exit 0, no captain-down.
- run log sha256 `bc2a4afc2f7b1ac0fb3a54108a9d33f13aa29db6b135217719a69775f143554b`.

## Six arena gates

| gate | status | method | evidence |
| --- | --- | --- | --- |
| identity_spawn | PASS | natural | `P2_KUSACHI_IDENTITY tick=1 total=20 blue=20 wired=20 pass=1` |
| movement_animation | PASS | natural | `P2_KUSACHI_MOVEMENT ... peak=1626.970 pass=1` |
| attacks_receivers | UNTESTED | unobserved | one live teki present; no natural engagement before extinction |
| death_corpse | UNTESTED | unobserved | no natural event before extinction |
| transport_reward | UNTESTED | unobserved | source `treasure_count_field=0`; no verified source loot |
| cleanup_reentry | UNTESTED | unobserved | no natural event before extinction |

`P2_KUSACHI_IDENTITY` confirms the #728 content module binds the kusachi roster
(blue, native color 0) into a live 20-Pikmin squad on the real stage, and the
window is centred 960x540.

## Blocker (reproducible)

The wired squad is not sustained naturally. The challenge runtime records
`squad_alive=20` then, ~12.5 s after boot, `squad_alive=0` and
`P2_CHALLENGE_MODE_DONE ... end=extinction`; `naviMgr` is then dropped and the
process idles. With no live captain/squad, attacks, death, transport and
cleanup cannot be observed and fixture adoption cannot honestly assert
`no_immediate_extinction`. Diagnostic fingerprint:
`kusachi-wired-squad-extinction-after-boot` (`P2_CHALLENGE_MODE_DONE
end=extinction` within ~13 s of `P2_CHALLENGE_MODE_BOOT population=50`).

The observation is honest and fail-closed: the adapter
(`experimental/content_lanes/p2-challenge-ch_nari_01kusachi_gameplay.py`)
reports UNTESTED rather than inferring PASS, and no gate is claimed from an
uninstructed run. `attacks_receivers` cannot be PASS under any protected
observation per the fanout contract.

## Reproduction

```
py -3.12 scripts/workflow_native_build.py --root <root> --request <build-request>
py -3.12 output/.../kusachi-gameplay-output/build_gameplay_fixture.py \
    --build output/kusachi-gameplay-obs-build \
    --source output/.../kusachi-gameplay-native \
    --fixture output/.../kusachi-gameplay-output/observer/p2_kusachi_gameplay_observer.cpp \
    --output output/kusachi-gameplay-obs-fixture-v2 \
    --expected-native-head 68ac74966100b65b9353322257ad831ce1c0b615
py -3.12 scripts/run_pikmin2_fixture.py --exe <fixture.exe> --run-dir <fresh staged dir> \
    --timeout 120 --arg=--experimental-pikmin2-room \
    --arg=--experimental-challenge-stage --arg=ch_NARI_01kusachi \
    --pass-marker='PASS KUSACHI_GAMEPLAY'
```

## Remaining work

1. Diagnose why the wired kusachi squad goes extinct ~12.5 s after boot with a
   live captain; restore a sustained live squad.
2. Re-run the observer and capture natural attacks/death/transport/cleanup, or
   a re-entry pass for cleanup.
3. P2 persistence (save/reload/retry/re-entry) remains the parallel
   `kusachi-persistence-obs` slice.
