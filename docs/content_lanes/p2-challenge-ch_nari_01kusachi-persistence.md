# ch_NARI_01kusachi P2 persistence observation (#781)

Lane `kusachi-persistence-obs`, issue #781, parent #533. Runtime slice; **not**
gameplay acceptance and no ADMIT. The #758 driver harness is driven against
two fresh-process guarded boots of the wired stage; receipts are
duplicate-resistant and kusachi-bound, but durable save payloads are
unobserved and the shared extinction blocker persists.

## Pins and guard

- root `36b868391e62cccf37d992aa2f796f3cc9c6dc31`,
  worktree `output/workflow/autofill/planning-shards/challenge-3/prepared/kusachi-persistence-root`
- native `68ac74966100b65b9353322257ad831ce1c0b615` (clean),
  worktree `output/workflow/autofill/planning-shards/challenge-3/prepared/kusachi-persistence-native`
- captain guard #632: `scripts/p2_fixture_captain_guard.h`
  sha256 `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`,
  vendored verbatim into the persistence observer; checked immediately after
  engine idle and before any movie return or observed tick. Guard self-test 7/7
  PASS; negative test exits 86 with `P2_FIXTURE_CAPTAIN_DOWN`. Unprotected
  policy; no health/state changes, no injection, no ADMIT, no native edits.

## What ran

A private replacement-main persistence observer (not a native repo edit) boots
the real engine with `--experimental-pikmin2-room
--experimental-challenge-stage ch_NARI_01kusachi` in a centred 960x540 window,
confirms the wired squad, and exits PASS. The engine's challenge-persistence
call site emits the 7 probe receipts once per boot; the lane adapter parses
them. Built with a leased private `pikmin_pc` build plus a private
response-file fixture link compiling the #728 content module and the observer.

- native build `output/kusachi-persistence-obs-build/bin/nectar.exe`
  sha256 `a780e13ec2a47e26…`; `ninja -n pikmin_pc` -> `ninja: no work to do.`
- observer fixture `output/kusachi-persistence-obs-fixture/fixture.exe`
  sha256 `f3d8154cfe754865…` (provenance recorded, native identity matched).
- pass1 `output/kusachi-persistence-obs-run-gen2-pass1` (18.7 s, exit 0),
  pass2 `output/kusachi-persistence-obs-run-gen2-pass2` (19.2 s, exit 0);
  no captain-down on either; wired 20-blue squad on both.

## Sequences (adapter-verified on the hashed logs)

| sequence | status | evidence |
| --- | --- | --- |
| save | OBSERVED | `P2_CHALLENGE_SAVE_KEY stage=ch_NARI_01kusachi` exactly once per pass, no refusal |
| reload | OBSERVED | `P2_CHALLENGE_LOAD_KEY stage=ch_NARI_01kusachi` exactly once per pass, no refusal |
| retry | OBSERVED | pass2 replays the identical single 7-receipt block (REPLAYED, never double-counted) |
| re-entry | OBSERVED | `P2_CHALLENGE_REENTRY stage=ch_NARI_01kusachi` on both fresh processes |
| duplicate resistance | SINGLE | each of the 7 receipts exactly once per boot; byte-identical blocks across passes |
| cross-content leakage | CLEAN | zero persistence markers for any other stage; zero refusals |

## Honest residual

- Durable save payloads are UNTESTED: both runs created fresh
  timestamp-scoped session roots whose card dirs are empty. The probes prove
  the save/load path fires with kusachi keys; no payload is written or
  restored in these short boots.
- The shared extinction blocker reproduces here: the challenge reports
  `end=extinction` and drops `naviMgr` after the boot, so no
  gameplay-sustained payload can form. Same fingerprint as the gameplay lane:
  `kusachi-wired-squad-extinction-after-boot`.
- Method caveat: each run's `save/` is a junction to the shared accepted
  baseline save; the runs wrote no payloads, so nothing was contaminated, but
  a payload-bearing run must stage a private save dir.

## Reproduction

```
py -3.12 scripts/workflow_native_build.py --root <root> --request <build-request>
py -3.12 output/.../kusachi-persistence-output/build_persistence_fixture.py \
    --build output/kusachi-persistence-obs-build \
    --source output/.../kusachi-persistence-native \
    --fixture output/.../kusachi-persistence-output/observer/p2_kusachi_persistence_observer.cpp \
    --output output/kusachi-persistence-obs-fixture \
    --expected-native-head 68ac74966100b65b9353322257ad831ce1c0b615
py -3.12 scripts/run_pikmin2_fixture.py --exe <fixture.exe> --run-dir <fresh staged dir> \
    --timeout 90 --arg=--experimental-pikmin2-room \
    --arg=--experimental-challenge-stage --arg=ch_NARI_01kusachi \
    --pass-marker='PASS KUSACHI_PERSIST'
```

## Remaining work

1. Sustained live squad on the wired stage (the extinction blocker).
2. Payload-bearing save/reload with a private save dir and a restore check.
3. Natural gameplay gates remain with `kusachi-gameplay-obs`.
