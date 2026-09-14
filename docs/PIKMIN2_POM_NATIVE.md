# P2 Candypop Bud native policy actor (lane 23, #171 / #448)

> Integration disposition: diagnostic tooling only in draft #432; the native actor described below is a worker candidate, not integrated gameplay. See [pre-wave review](PIKMIN2_PREWAVE_REVIEW_437.md) for blockers and validation limits.

## Scope

This is lane 23's **native Candypop Bud** slice on top of the delivered pure
Python behavior model (`experimental/pikmin2_flora_behavior.py`) and the
audit (`docs/PIKMIN2_FLORA_AUDIT.md`, #171). It implements a native, opt-in
(sidecar-gated, fail-closed, inert without the sidecar) source behavior for the
six buds `BluePom` 3, `RedPom` 4, `YellowPom` 5, `BlackPom` 6, `WhitePom` 7,
`RandPom` 8, and explicitly rejects the nonspawnable shared base `Pom` (82):

- any-colour press/throw-in acceptance while armed and under the **lifetime
  slot budget** `ip01` = 5 (colour buds) / `ip11` = 1 (Queen `RandPom`),
- an own-colour throw **refunds** the slot on colour buds only (the Queen never),
- **close** `fp01` = 1.0 s after the last swallow or when the budget is spent;
  a close with Pikmin inside **shoots** `ip13` = 9 leaf sprouts per swallowed
  Pikmin for the Queen, else 1 per Pikmin; a close with nothing inside reopens,
- the Queen cycles Blue/Red/Yellow deterministically every `fp02` = 2.6 s,
- invulnerable after landing,
- the nonspawnable **base Pom (82) is rejected** with an explicit marker and is
  never bound.

New files (native):

- `pc_port/pc_p2_pom_policy.h` - pure, engine-free policy and strict
  `P2_POM_1` parser (shared by the actor and the standalone strict test).
- `pc_port/pc_p2_pom.cpp` / `.h` - sidecar-gated module-local actor.

Registration (additive): `CMakeLists.txt` source list,
`pc_port/pc_p2_preview.cpp` setup, and `src/plugPikiKando/gameCoreSection.cpp`
per-frame `pc_p2_pom_tick()` after `pc_p2_flora_tick()`.

## Source anchors

| Behavior | Value | Anchor |
|---|---|---|
| Six buds 3-8, base 82 | `BluePom`..`RandPom`, `Pom` | `enemyInfo.h:62-67,141` |
| Entry | press on `slot` (radius 30), any colour | `Pom.cpp:154-201` |
| Lifetime budget | `ip01` 5 / `ip11` 1 | `Pom.h:100-105`, disc `pom/enemyparm.txt` |
| Own-colour refund | colour buds only | `Pom.cpp:296-298` |
| Close / reopen / shot | `fp01` 1.0 s; shot when inside | `PomState.cpp:101-235` |
| Leaf sprouts | `ip13` 9 per Pikmin (Queen), launch `(110,750,110)` | `Pom.cpp:280-322`, audit 66-73 |
| Queen colour cycle | `fp02` 2.6 s deterministic | `Pom.cpp:330-355` |
| Violet/Ivory gating | floor 1-2 / Emergence / White Flower Garden cap 20 | `PomMgr.cpp:38-89` |
| Invulnerable after landing | no damage path | audit 79-82 |

The `P2_POM_1` sidecar format is documented in `pc_p2_pom.cpp`. Malformed
input aborts (fail-closed); a base `Pom` row is parsed, then logged as
`P2_POM_BASE_REJECTED` and skipped.

## Log contract

```text
P2_POM_READY generator=<id> species=<name> source_id=<n> colour=<c> budget=<n> queen=<0|1> x=.. y=.. z=..
P2_POM_INVULNERABLE generator=<id> invulnerable_after_landing=1
P2_POM_BASE_REJECTED generator=<id> species=Pom source_id=82 reason=nonspawnable_base
P2_POM_ACCEPT generator=<id> species=<name> thrown_colour=<c> used=<n> budget=<n>
P2_POM_REFUND generator=<id> species=<name> thrown_colour=<c> used=<n> budget=<n> slot_refunded=1
P2_POM_QUEEN_COLOUR generator=<id> colour=<c>
P2_POM_CLOSE generator=<id> species=<name> outcome=<shot|reopen> used=<n> budget=<n> swallowed=<n>
P2_POM_SPROUT generator=<id> species=<name> count=<n> colour=<c> leaf=1
P2_POM_DONE generator=<id> species=<name> used=<n> refunds=<n>
```

The fixture self-terminates on a wall-clock ceiling (100 s) and prints
`P2_POM_RUNTIME_BLOCKED <gate> reason=<reason>` (`ready` / `accept` / `refund`
/ `close` / `sprout`) instead of hanging; `completion` requires the explicit
`PASS P2_POM_NATIVE accept_refund_close_sprout` line, so a blocked run can
never read as a pass.

## Implemented vs BLOCKED / remaining

**Implemented (native, this slice)**

- Six-species identity with per-species colour and budget, base `Pom` rejected.
- Acceptance (any colour), own-colour refund, budget exhaustion.
- `fp01` close with reopen/shot routing, `ip13` leaf sprout spawning.
- Queen deterministic colour cycle.
- Invulnerable-after-landing marker.

**BLOCKED / remaining**

- **Engine Pom FSM binding and visual proxy draw.** This slice is a
  module-local logic actor anchored at sidecar positions; it does not spawn or
  drive the engine `Pom` Boss (`src/plugPikiNishimura/Pom*.cpp`) and does not
  draw a bud model. Reusing the engine `Pom` (shape `bosses/pom/pom.mod`, prop
  `parms.bin`, `GENBOSS_Pom`) and its animations is the next step.
- **Onion / seed accounting** remains with the Pod/Onion lanes.
- **Violet/Ivory cutscene trigger** (`navi_demoCheck.cpp:42`) and the
  per-colour cave placement/roster work.
- The existing `pc_p2_purple.cpp` `pc_p2_violet` prototype is untouched and is
  not used by this module.

## Approximations and labeled injections

- The fixture injects Pikmin conversions by placing Pikmin in the
  `PIKISTATE_Flying` state at each bud's sidecar position; this is a labeled
  injection, not a source throw arc.
- Purple/White source colours map to a valid P1 body colour for the spawned
  sprout since P1 has no Purple/White Pikmin; the source colour is reported in
  the log.
- The bud actor is anchored at sidecar coordinates, not a stage generator; the
  `Generator::_70` little-endian-stamp convention is not exercised here
  (positions, not generator ids, are authoritative for this behavior slice).

## Build and fixture provenance

- Native branch `opencode/p2-lane23-native`, commit
  `a582a4c5b9bd04572af8ae0c2cb20f095f6e7463` (base `57bb1a4e`), clean.
- Private build `output/p2-lane23-native-build`, Ninja; dry run
  `ninja: no work to do.`
- Fixture `output/p2-lane23-pom-fixture-1/build/fixture.exe`
  SHA-256 `964b0e8b9d941f6c9d06c82f3719e090197c75d26ab44ef8c7b80d13ade9b42c`,
  `provenance.json` status `built`, expected native head matches.
- GL fixture runs are serialized and owned by the coordinator. This lane built
  only; no runtime/gameplay acceptance is claimed.

### Staged assets (`pikmin2_pom_runtime.stage`)

- `dataDir/stages/chal0.ini` = `dataDir/stages/practice.ini` (map
  `courses/practice/practice.mod`),
- `dataDir/stages/chal0/default.gen` = the practice `default.gen` records plus
  10 injected Red Pikmin (labeled squad injection),
- every pre-existing `dataDir/stages/chal0/*.gen` overridden to an empty stage,
- `p2-cargo-free.txt` (`P2_CARGO_FREE_1`) so the preview skips the missing
  `courses/pikmin2room/treasure.mod`,
- `p2-pom.txt` = one `RedPom` (240011), one `RandPom` Queen (240012) and one
  base `Pom` (240013, rejection probe).

`stage()` asserts each required file exists before launch.

Exact GL run command (from `output/p2-lane23-root`):

```powershell
$env:PIKMIN_P2_ROOM_WINDOW='960x540'
py -3.12 -m experimental.pikmin2_pom_runtime run --assets C:\Users\alari\bbft\dist\cohesion\pikmin\assets --output output/p2-lane23-pom-runtime-01 --exe C:\Users\alari\pikmin-randomizer\output\p2-lane23-pom-fixture-1\build\fixture.exe
```

## Validation

```text
py -3.12 -m pytest tests/ -q -k "pom or flora"   # 80 passed
g++ -std=c++17 -Wall -Wextra -Werror -I native-patches/pom tests/pikmin2_pom_policy.cpp
```

No runtime/native gameplay acceptance is claimed by this lane.
