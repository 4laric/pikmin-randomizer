# Lanes 07–09 integration handoff and native-line reconciliation

Engine/toolchain lanes 07–09, Codex through shared account `4laric`. Companion
to `PIKMIN2_TEKI_LIFETIME_SEAM.md`, `PIKMIN2_SAMPLED_CLOCK_ADOPTION.md` and
`PIKMIN2_UPSTREAM_SPECULAR_VALIDATION.md`.

## Rebased native candidate (current maintained tip)

The lane commits were rebased onto the current `codex/pikmin2-room-preview`
native tip `a95040b6` (they were originally on `f9e139d8`, an ancestor).

- Branch `opencode/p2-lanes789-native-r2`
  (`output/tracks/p2-lanes789/native-r2`), HEAD
  `72bed79a47b58332bb35afccc67d78cc41f0daac`, base `a95040b6`:
  - `758b2ad6` lifetime seam (`pc_p2_teki_lifetime`, `doKill` funnel)
  - `e05fc427` sampled-clock header (#431)
  - `beb359fe` `pc_p2_batch2` clock/event adoption (#431)
  - `bcd9a2e1` + `d69d9c8b` upstream GL specular
  - `f87ac502` + `af5fb09d` + `72bed79a` #397 rebind / queries / corpse rebind
- Cherry-pick range `f9e139d8..opencode/p2-lanes789-native` applied with **no
  conflicts**. Production build `output/tracks/p2-lanes789/native-r2-build`
  (`PIKMIN_NATIVE_JAUDIO=ON`), `bin\nectar.exe` SHA-256
  `3F0E2D9FC1701C513C917D69B99E61DF389DF4595A3B5AA1C6CEF8A99C404640`,
  `[522/522]`, `ninja -n` -> no work.
- Standalone probes: `PASS p2_sampled_clock: 46 checks`, `PASS p2_batch2_clock`.
- Fresh adopted arena
  `output/tracks/p2-lanes789/flora-arena-05/5f9a45ec8ecf42c9ad840201dafb044f`,
  rebuilt fixture, 960x540, exit 0:
  - `P2_BATCH2_EVENT key=flora|Pelplant clip=wait1 frame=0 event=0 cycle=0`
  - `P2_LIFECYCLE_CLEANUP id=353001 live=1 registered=1`
  - `P2_BATCH2_PRE_REBIND stale_registered=1`
  - `P2_LIFECYCLE_REENTRY id=353001 frame=384 reused=0`, `PASS P2_LIFECYCLE_RUNTIME`
  - marker probe: `before=1` -> `after_engine_dokill=0`, `PASS P2_FORGET_PROBE`
  - logs `native-lifecycle.log` / `native-forget-probe.log`.

## Two divergent native lines (needs lane 01)

`git merge-base` shows `f9e139d8` is an ancestor of `a95040b6`, but `0ab3ea12`
is **not** related to either (60 commits one way, 76 the other).

| Native line | Tip | Has P2 material/queen modules? |
|---|---|---|
| `codex/pikmin2-room-preview` (maintained) | `a95040b6` | **No** (`pc_port` has no `pc_p2_material_*`, `pc_p2_queen*`, `pc_p2_specular_layer*`) |
| `codex/p2-family-native-422` | `0ab3ea12` | **Yes** |

The root `codex/pikmin2-room-preview` `engine/` export **does** contain
`engine/pc_port/pc_p2_material_srt.h`, `pc_p2_queen.cpp` and
`pc_p2_specular_layer.cpp`, so that export came from the `0ab3ea12` family line,
not from the maintained `native/` branch. Consequences:

- The maintained native branch cannot currently reproduce the exported engine
  for the material/queen paths. Lane 01 should reconcile the two lines (merge
  `0ab3ea12` into `a95040b6` or re-adopt one as the maintained line) and then
  re-export.
- The lane 09 specular A/B necessarily ran on the `0ab3ea12`-based line
  (`opencode/p2-lanes789-queen-native` @ `d4bc8dbc`), because that is where the
  Queen two-stage material path exists. The GL commits themselves are
  `pc_gfx.cpp`-only and portable; they rebased cleanly onto `a95040b6` too.

## Recommended lane 01 actions

1. Adopt the two-line reconciliation so the maintained native branch matches the
   exported root engine.
2. Review the shared-semantics changes: the lifetime death-funnel seam and the
   upstream GL specular commits.
3. Export `opencode/p2-lanes789-native-r2` (line 1) and, separately, the
   specular commits on line 2 if line 2 remains the material line.
