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
P2_POM_SPROUT generator=<id> species=<name> count=<n> colour=<src> body=<p1> leaf=1
P2_POM_SPROUT_RETRY generator=<id> species=<name> owed_remaining=<n> requested=<n> born=<n> item_capacity=1 forced=<0|1>
P2_POM_SPROUT_SETTLED generator=<id> species=<name> requested=<n> born=<n> conservation=1
P2_POM_STATE generator=<id> species=<name> from=<s> to=<s>
P2_POM_DEAD generator=<id> species=<name> used=<n> refunds=<n> corpse=0 budget=<n>
P2_POM_CONSERVATION generator=<id> species=<name> used=<n> refunds=<n> requested=<n> born=<n> dead_pikis=<n> loss_counted=<0|1>

Review note: `loss_counted` is a delta on the global `GameStat::deadPikis`, so any unrelated Pikmin death in the scene flips it to 1 (false positive). The conservation ledger instruments the pre-existing erase-kill path (`pikidoKill.cpp` skips the increment when `mEraseOnKill`, which the base module already set); it is not a new mechanic.
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

## Approved-base rebase (maintained line)

Rebased onto the current maintained native (`codex/p2-main-review-native` head
`c223f442`) after lane 01's pass:

- Native `opencode/p2-lane23-approved` @ `5478384fbb9370a9b7f33a17caf15f167101cca5`
  (base `c223f442`; never pushed); private build `output/p2-lane23-approved-build`,
  550/550 link, `ninja -n pikmin_pc` no work.
- Fixture `output/p2-lane23-approved-fixture-pom/build/fixture.exe` SHA-256
  `7dead3c093730604175ab471f9b20161ca57c960db99dac82ac380d3a6dfa59e`, provenance
  status `built`, expected native head `5478384f`.
- GL run `output/p2-lane23-approved-runtime-pom/pom/167c105a9b8648f9ba41e08b546f10d1`
  PASS, carrying the #448 fix on the maintained base: Queen
  `P2_POM_SPROUT ... count=9 colour=0 body=0`, `P2_POM_SPROUT_RETRY ... item_capacity=1`,
  `P2_POM_SPROUT_SETTLED ... requested=9 born=9 conservation=1`, RedPom
  `requested=2 born=2`, `PASS P2_POM_NATIVE accept_refund_close_sprout`.

## DeepSeek #448 follow-on slice: source six-state FSM, budget-only death, conservation ledger

Lane 23 (DeepSeek session) adds the source state machine and the budget-only
death/cleanup path that the earlier module left implicit, plus a
population-conservation proof. New observables (native `pc_port/pc_p2_pom.cpp`,
mirrored policy `pc_port/pc_p2_pom_policy.h` and the root
`native-patches/pom` copy, `experimental/pikmin2_flora_behavior.py`,
`experimental/pikmin2_pom_runtime.py`, tests):

- **Six-state FSM.** The source state set (enemy/Entities/Pom.h:153-161)
  `wait/dead/open/close/shot/swing` is now tracked per bound bud and emitted as
  `P2_POM_STATE ... from=<s> to=<s>`. The Queen walks
  `wait -> open -> swing -> close -> shot -> dead`; a colour bud reopens
  (`shot -> wait`) while its lifetime budget (`ip01` = 5) remains.
- **Budget-only death.** `candypop_dead`/`p2pom::dead(budgetSpent, owed)` encode
  the audit's "death only from an exhausted budget": a bud reaches `dead` only
  when its budget is spent **and** sprout conservation has settled (`owed == 0`).
  The terminal log is `P2_POM_DEAD ... corpse=0 budget=<n>` (source-correct: no
  corpse). Conservation settlement still precedes death, so a consumed Pikmin's
  sprouts are never discarded by the death.
- **Population conservation ledger.** The module records `GameStat::deadPikis`
  once after binding (`deadPikisBaseline`) and again at death as
  `P2_POM_CONSERVATION ... used=<n> refunds=<n> requested=<n> born=<n>
  dead_pikis=<n> loss_counted=<0|1>`. Every consumed Pikmin is erase-killed
  (`Piki::setEraseKill()`), so `deadPikis` must not advance and `loss_counted`
  is `0`: conversion consumes Pikmin without counting them as deaths/losses.

The fixture validator now requires the state walk, `P2_POM_DEAD` and
`P2_POM_CONSERVATION` (with `loss_counted=0`) in addition to the prior
accept/refund/close/sprout/settled gates; a run that never dies, or that counts
a loss, fails closed. The module remains sidecar-gated, fail-closed, and inert
without `p2-pom.txt`.

## DeepSeek #448 slice 2: ordinary spawned, drawn Candypop bud (gate 1 spawn FAIL → PASS)

Lane 23 (DeepSeek session) makes the bud an ordinary spawned, drawn actor by
binding each sidecar generator to the live **batch-2 `flora` family Chappy
placement vehicle** and drawing the converted `enemy/data/Pom` bank through the
existing batch-2 display path, with the bud FSM driving the drawn pose.

- **Host bind** (`pc_p2_pom.cpp`): `pc_p2_pom_tick()` lazily resolves each
  sidecar generator to its live `TEKI_Chappy` host (same `mGenerator->_70`
  generator-id match the batch-2 `flora` family uses) and emits
  `P2_POM_BIND generator=<id> species=<name> source_id=<n> host=teki type=3 drawn=1`.
  A non-Chappy native type at that generator is a fail-closed abort.
- **FSM-driven pose** (`pc_p2_pom_clip`): a small clip hook (mirror of
  `pc_p2_hana_clip`) added to the batch-2 forced-clip chain maps the tracked
  `p2pom::State` to the source clip name — Wait→`wait`, Open→`type1`, Close→`type2`,
  Shot→`type3`, Swing→`type4`, Dead→`dead` (Pom::AnimID order) — and reports one
  `P2_POM_DRAW ... pose=<state> draws=<n>` per draw tick. Static/bind-pose phase
  (0.0); the clip alone distinguishes the state.
- **Forget on despawn** (`pc_p2_pom_forget`): wired into `pc_p2_forget_teki`;
  clears the host pointer while keeping the value-owned FSM/receipt state so a
  recycled Teki address cannot alias the bud.
- **Slot anchor stays planted**: the conversion mouth slot remains at the
  authored plant point (sidecar XYZ == arena spawn position); the Chappy host is
  the drawn vehicle only, so a wandering vehicle cannot move the receptor
  (source buds are stationary and dropped exactly on their point).

The arena is now `pikmin2_batch2_core.prepare(FAMILIES['flora'], …)`: generator
`353003` RedPom and `353007` RandPom (the flora-family bud slots) with the
converted `flora_<Species>_<clip>_*.mod` bank installed from
`experimental/pikmin2_flora_assets` (extracted from the US GPVE01 rev 0 disc),
plus one base-`Pom` rejection probe (`353099`, never bound). The runtime log now
shows the live host bind, batch-2 draw (`P2_BATCH2_DRAW key=flora|…`) and the
FSM pose walk (`pose=wait -> shot -> dead`) while the slice-1 death/conservation
chain still fires on the spawned host.

Conversion/material fidelity remain lane-09 scope; the drawn model is a static
bind pose, not skeletal playback. The Spectralid sentinel (lane 15) is untouched.
