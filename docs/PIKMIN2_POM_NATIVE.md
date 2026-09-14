# P2 Candypop Bud native policy actor (lane 23, #171 / #448)

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
P2_POM_SPROUT generator=<id> species=<name> count=<n> colour=<src> body=<p1> leaf=1
P2_POM_SPROUT_RETRY generator=<id> species=<name> owed_remaining=<n> requested=<n> born=<n> item_capacity=1 forced=<0|1>
P2_POM_SPROUT_SETTLED generator=<id> species=<name> requested=<n> born=<n> conservation=1
P2_POM_DONE generator=<id> species=<name> used=<n> refunds=<n>
```

`colour` is the source-selected colour (the Queen's cycling colour, no longer the
`-1` "cycles" sentinel); `body` is the P1 sprout body actually applied. The
fixture self-terminates on a wall-clock ceiling (100 s) and prints
`P2_POM_RUNTIME_BLOCKED <gate> reason=<reason>` (`ready` / `accept` / `refund` /
`close` / `sprout`) instead of hanging; `completion` requires the explicit
`PASS P2_POM_NATIVE accept_refund_close_sprout` line, so a blocked run can never
read as a pass.

## Integration-review follow-up (#448, PIKMIN2_PREWAVE_REVIEW_437.md §1)

- **Queen colour-correct output.** `spawnSprouts` previously used
  `bound.colour`, which is `-1` for the Queen and fell back to Blue. It now uses
  the source-selected cycling colour (`queenColour`), so the born sprouts match
  the visible bud colour; colour buds keep their own colour (Black/White still
  fall back to a valid P1 body and report the source colour separately).
- **Exhausted-capacity conservation.** Item birth demand is tracked per bud
  (`requested`/`born`/`owed`) and retried every simulation tick until every
  consumed Pikmin has produced its source-count sprouts. Nothing is silently
  discarded: a bud emits `P2_POM_SPROUT_RETRY ... item_capacity=1` while demand
  is outstanding and `P2_POM_SPROUT_SETTLED ... conservation=1` once
  `born == requested`; the budget-spent bud only finishes after settlement.
- **Simulation clock.** Timers now advance on a bounded 30 Hz behavior clock
  (same pattern as `pc_p2_king.cpp`) instead of raw frame pacing; `reset()`
  clears the clock, injection and conservation state on scene teardown.
- **Labeled capacity probe.** The fixture writes `p2-pom-inject.txt`
  (`P2_POM_INJECT_1 <generator> <forcedBirthFailures>`) to force the Queen's
  first two sprout births to fail. This is a labeled injection, never present in
  a normal run, and is what exercises the retry path deterministically.

## Implemented vs BLOCKED / remaining

**Implemented (native, this slice)**

- Six-species identity with per-species colour and budget, base `Pom` rejected.
- Acceptance (any colour), own-colour refund, budget exhaustion.
- `fp01` close with reopen/shot routing, `ip13` leaf sprout spawning.
- Queen deterministic colour cycle **and colour-correct sprout output**.
- Capacity-conservation retry: no consumed Pikmin's sprouts are silently lost
  under exhausted item capacity (`requested == born` at settlement).
- Bounded 30 Hz simulation clock; reset clears clock/injection state.
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
  `d17efee5c3a73ae3f1808acbe2a1527c16486d3f` (colour/conservation/clock fix on
  top of `fc24c9e9`; clean).
- Private build `output/p2-lane23-native-build`, Ninja Release,
  `PIKMIN_NATIVE_JAUDIO=ON`; dry run `ninja: no work to do.`
- Fixture `output/p2-lane23-root/output/p2-lane23-pom-fixture-2/build/fixture.exe`
  SHA-256 `0a403362f3363d11a813f6fab692dc501221d807e2c15a95b741b97d7ae376a9`,
  `provenance.json` status `built`, expected native head matches
  `d17efee5`.
- GL run `output/p2-lane23-root/output/p2-lane23-pom-runtime-02/pom/15723793344c4f4980f2737986344496`
  (this run is the serialized GL acceptance for the fix; the earlier
  `p2-lane23-pom-runtime-01` operator run remains historical).

### Staged assets (`pikmin2_pom_runtime.stage`)

- `dataDir/stages/chal0.ini` = `dataDir/stages/practice.ini` (map
  `courses/practice/practice.mod`),
- `dataDir/stages/chal0/default.gen` = the practice `default.gen` records plus
  10 injected Red Pikmin (labeled squad injection),
- every pre-existing `dataDir/stages/chal0/*.gen` overridden to an empty stage,
- `p2-cargo-free.txt` (`P2_CARGO_FREE_1`) so the preview skips the missing
  `courses/pikmin2room/treasure.mod`,
- `p2-pom.txt` = one `RedPom` (240011), one `RandPom` Queen (240012) and one
  base `Pom` (240013, rejection probe),
- `p2-pom-inject.txt` = `P2_POM_INJECT_1 1` / `240012 2` (labeled capacity probe
  forcing the Queen's first two sprout births to fail).

`stage()` asserts each required file exists before launch.

Exact GL run command (from `output/p2-lane23-root`):

```powershell
$env:PIKMIN_P2_ROOM_WINDOW='960x540'
py -3.12 -m experimental.pikmin2_pom_runtime run --assets C:\Users\alari\bbft\dist\cohesion\pikmin\assets --output output/p2-lane23-pom-runtime-02 --exe C:\Users\alari\pikmin-randomizer\output\p2-lane23-root\output\p2-lane23-pom-fixture-2\build\fixture.exe
```

## Runtime evidence (bounded, labeled injections)

Run `output/p2-lane23-root/output/p2-lane23-pom-runtime-02/pom/15723793344c4f4980f2737986344496`,
validator all-true (`ready`, `base_rejection`, `accept`, `refund`, `close`,
`sprout`, `sprout_colour`, `sprout_retry`, `sprout_settled`, `invulnerable`,
`no_rewards`).

```text
P2_POM_QUEEN_COLOUR generator=240012 colour=0
P2_POM_SPROUT generator=240012 species=RandPom count=9 colour=0 body=0 leaf=1
P2_POM_SPROUT_RETRY generator=240012 species=RandPom owed_remaining=9 requested=9 born=0 item_capacity=1 forced=1
P2_POM_SPROUT_RETRY generator=240012 species=RandPom owed_remaining=9 requested=9 born=0 item_capacity=1 forced=0
P2_POM_SPROUT_SETTLED generator=240012 species=RandPom requested=9 born=9 conservation=1
P2_POM_SPROUT generator=240011 species=RedPom count=2 colour=1 body=1 leaf=1
P2_POM_SPROUT_SETTLED generator=240011 species=RedPom requested=2 born=2 conservation=1
PASS P2_POM_NATIVE accept_refund_close_sprout
```

The first `RETRY` (`forced=1`) is the injected capacity probe; the second
(`forced=0`) is the module re-attempting under the same outstanding demand. This
run is still a module-local, sidecar-anchored policy fixture with labeled
injected conversions, not natural Candypop gameplay.

## Validation

```text
py -3.12 -m pytest tests/test_pikmin2_pom_runtime.py -q   # 7 passed
py -3.12 -m pytest tests/ -q -k "pom or flora"             # 81 passed
g++ -std=c++17 -Wall -Wextra -Werror -I native-patches/pom tests/pikmin2_pom_policy.cpp
```

The bounded injected GL gate passes; natural engine-Pom-FSM gameplay, bud
visuals, Onion seed receipt, plant placement/Spectralid and Hikari #429 remain
open.
