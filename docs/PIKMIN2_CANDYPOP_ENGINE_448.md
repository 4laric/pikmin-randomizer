# P2 Candypop Bud real engine binding (lane 23, #448 / #171)

## Scope

This slice replaces the module-local injected Candypop actor for the four
engine-representable colour buds with the **real engine `Pom` Boss**
(`src/plugPikiNishimura/PomAi.cpp`). The previous `pc_p2_pom.cpp` slice drove a
sidecar-position logic actor that scanned `pikiMgr` for `PIKISTATE_Flying`
Pikmin and killed them itself (see [`PIKMIN2_POM_NATIVE.md`](PIKMIN2_POM_NATIVE.md));
this slice binds the genuine actor so the ordinary swallow/close/discharge path
performs the conversion.

- `BluePom` 3 / `RedPom` 4 / `YellowPom` 5 are bound by generator id from a new
  strict, opt-in sidecar `p2-pom-engine.txt` (reuses the lane-23 `P2_POM_1`
  parser from `pc_p2_pom_policy.h`, fail-closed, inert without the file).
- The module stamps the source identity (colour) and budget on the real actor
  and implements the **source own-colour refund** in `PomAi::createPikiHead`:
  a same-colour input births a replacement sprout and spends **no** budget
  slot, a different colour spends one. Population is conserved.
- `RandPom` 8 (Queen) is bound too: budget `ip11` = 1, the deterministic
  Blue/Red/Yellow cycle every `fp02` = 2.6 s (met-colour aware), no refund, and
  the source `ip13` = 9 leaf sprouts per swallowed Pikmin.
- Base `Pom` (82) is rejected and never bound.
- BlackPom/WhitePom remain with the existing violet/ivory providers
  (`pc_p2_purple.cpp` / `pc_p2_white.cpp`).

New files (native): `pc_port/pc_p2_candypop.{h,cpp}`. Additive hooks in
`src/plugPikiNishimura/PomAi.cpp` (`initAI` config + `createPikiHead` conversion),
`CMakeLists.txt`, `pc_port/pc_p2_preview.cpp`, `src/plugPikiKando/gameCoreSection.cpp`
and `pc_port/pc_p2_teki_lifetime.cpp`.

## Source anchors

| Behavior | Value | Anchor |
|---|---|---|
| Own-colour refund | same colour does not spend a slot | P2 `Pom.cpp:296-299` (`Obj::shotPikmin`) |
| Lifetime budget | `ip01` = 5 colour buds, `ip11` = 1 Queen | disc `pom/enemyparm.txt` |
| Queen colour cycle | Blue/Red/Yellow every `fp02` = 2.6 s | P2 `Pom.cpp:330-355` |
| Queen sprout multiplier | `ip13` = 9 per Pikmin | P2 `Pom.cpp:280-322` |
| Close on full/timeout | `mMaxPikiPerCycle` / `mCloseWaitTime` | `PomAi.cpp:482-501` |
| Swallow into slot | `InteractSwallow` on `slot` child | `PomAi.cpp:395-416`, `:609-627` |
| Sprout birth | `itemMgr->birth(OBJTYPE_Pikihead)` | `PomAi.cpp:325-362` |
| Boss identity | `GENBOSS_Pom` 5, `mItemColour` bits 6-7 | `genBoss.cpp:88-97`, `BossMgr.cpp:787-799` |

## Sidecar contract

`p2-pom-engine.txt` in the process working directory (strict `P2_POM_1`,
shared with `pc_p2_pom_policy.h::readPoms`):

```text
P2_POM_1 <count>
<generator-u32> <BluePom|RedPom|YellowPom|BlackPom|WhitePom|RandPom|Pom> <x> <y> <z>
```

Positions let the module match the actor during `Pom::init`, before the engine
links `mGenerator`. Malformed input aborts (`P2_CANDYPOP invalid sidecar`). A
base `Pom` row is parsed, logged `P2_POM_BASE_REJECTED`, and skipped;
BlackPom/WhitePom rows are logged `P2_CANDYPOP_UNSUPPORTED` (delegated).

## Log contract

```text
P2_CANDYPOP_SIDECAR engine_buds=<n>
P2_POM_READY generator=<id> species=<name> source_id=<n> colour=<c> budget=<n> queen=<0|1> engine=1 x=.. y=.. z=..
P2_POM_INVULNERABLE generator=<id> invulnerable_after_landing=1
P2_POM_QUEEN_COLOUR generator=<id> colour=<0|1|2> met=<mask>
P2_CANDYPOP_WITNESS generator=<id> species=<name> input=<blue|red|yellow> refund=<0|1>
P2_CANDYPOP_CONVERT generator=<id> species=<name> converted=<n> used=<n> refunds=<n>
P2_CANDYPOP_SPROUTS generator=<id> species=RandPom sprouts=<n> multiplier=9
```

`refund=1` marks an own-colour input that consumed no slot; `used` is the
non-refunded slot count returned to `PomAi` (added to `mReleasedSeedCount`).

## Implemented

- Real engine actor bound and configured (`mMaxPikiPerCycle` = source budget,
  `mCloseWaitTime` = 1.0 s, any-colour entry, no same-colour kill).
- Real Pikmin throws via the ordinary `Navi::throwPiki` path; the engine
  swallow → close → discharge path performs the conversion.
- Source own-colour refund with population conservation (colour buds).
- Queen: `ip11` = 1 budget, bounded 30 Hz Blue/Red/Yellow cycle, `ip13` = 9
  sprouts per swallowed Pikmin.
- Base-Pom rejection; inert without the sidecar; reset clears bindings per stage.

## BLOCKED / remaining

- **BlackPom/WhitePom** remain with the violet/ivory providers (no lane-23
  engine binding).
- **Natural generation/admission.** Placement, generated-session binding,
  rewards, save persistence and mixed-scene acceptance are unchanged and still
  belong to lanes 03/04/05/06/33.
- **Aim timing is scripted.** The fixtures re-aim pending throws every few ticks;
  the throws, swallow, conversion and sprouts are engine behaviour, but the aim
  schedule is a labeled injection, not manual play.

## Approximations and labeled injections

- Boss generator rows are cloned from the challenge `ssob` template and stamped
  `GENBOSS_Pom`; the staged position is a fixture placement, not source routing.
- All staged boss generators carry a Red container colour so the engine birth
  gate passes; the module re-stamps the source colour.
- Queen met-colour mask is the fixture's `0x7` (all three met); the source
  skips unmet colours, which the shared `p2pom::queenColour` policy still
  encodes.

## Build and fixture provenance

- Native `opencode/p2-lane23-pom-native` @
  `de476ea3e1ff7db4b8ce47b5bc15998a7e6d38b2` (base `b805d9c6`; never pushed);
  ordered commits `7bb324d8` (colour buds) then `de476ea3` (Queen). Private build
  `output/native-lane23-pom-build` (Ninja Release/MinGW, JAudio ON, IPO ON);
  `ninja -n pikmin_pc` -> no work to do; executable `bin/nectar.exe` SHA-256
  `F371E9916D8A5460AC59D3C1BAD44FDC18F366FB29AEFFBDC04DB7845953A357`.
- Root `opencode/p2-lane23-pom` (based on `origin/codex/p2-main-review`
  `4fccf41`): `223138f` (engine fixture), `c2061a3` (Queen fixture),
  `f2e6a43`/this docs commit.
- Fixtures at the `de476ea3` head:
  - engine `output/lane23-pom-fixture-3/build/fixture.exe` SHA-256
    `d3b83a866b41cef76596d5e61efb3ec8e641d4c3691a51c6ea974886e108ffe2`,
  - Queen `output/lane23-pom-queen-fixture-2/build/fixture.exe` SHA-256
    `cc912a189aed89e283a4edb70b79caf78885ef438e07fed0374d69c07062035f`,
  both `provenance.json` status `built`, observed head `de476ea3`.

## Runtime evidence (960x540, live squad)

### Colour buds — own-colour refund + conservation

Run `output/lane23-pom-runtime-03/engine/0413f42ed6d14c35bcd489a5844f01d3`,
validator all-true (`completion`, `ready_red`, `ready_blue`, `base_rejection`,
`convert_red`, `convert_blue`, `witnesses_refund`, `witnesses_used`,
`conservation`, `no_rewards`), exit 0, no leftover process:

```text
[PC Port] Experimental preview window set to 960x540 windowed and centered ...
P2_POM_BASE_REJECTED generator=240013 species=Pom source_id=82 reason=nonspawnable_base
P2_POM_READY generator=240011 species=RedPom source_id=4 colour=1 budget=5 queen=0 engine=1 x=-25.00 y=30.00 z=1850.00
P2_POM_READY generator=240012 species=BluePom source_id=3 colour=0 budget=5 queen=0 engine=1 x=25.00 y=30.00 z=1850.00
P2_CANDYPOP_CONVERT generator=240011 species=RedPom converted=5 used=3 refunds=2
P2_CANDYPOP_CONVERT generator=240012 species=BluePom converted=5 used=3 refunds=2
P2_POM_ENGINE_STATE initial=12 sprouts=10 alive=2
PASS P2_POM_ENGINE real_conversion_refund_conservation
```

Each bud swallowed five real Pikmin (two own-colour refunds, three used) and
produced five sprouts; twelve field Pikmin became ten sprouts plus two
survivors, so `alive + sprouts == initial`. (The base-Pom probe generator id is
`240013`; the Queen fixture reuses that id in a separate run.)

### Queen — colour cycle + `ip13` multiplier

Run `output/lane23-pom-queen-runtime-03/queen/45874c8365de4368b408d6b358e5ff3a`
(note: the base-Pom rejection probe is not part of this fixture):

```text
P2_POM_READY generator=240013 species=RandPom source_id=8 colour=0 budget=1 queen=1 engine=1 x=-25.00 y=30.00 z=1790.00
P2_POM_QUEEN_COLOUR generator=240013 colour=1 met=7
P2_POM_QUEEN_COLOUR generator=240013 colour=2 met=7
P2_POM_QUEEN_COLOUR generator=240013 colour=0 met=7
P2_POM_QUEEN_COLOUR generator=240013 colour=1 met=7
P2_CANDYPOP_WITNESS generator=240013 species=RandPom input=red refund=0
P2_CANDYPOP_CONVERT generator=240013 species=RandPom converted=1 used=1 refunds=0
P2_CANDYPOP_SPROUTS generator=240013 species=RandPom sprouts=9 multiplier=9
P2_POM_QUEEN_STATE initial=2 sprouts=9 alive=1
PASS P2_POM_QUEEN cycle_and_multiplier
```

Four cycle changes observed (1→2→0→1); one real throw converted for `ip11` = 1
and shot `ip13` = 9 sprouts — the Queen multiplies the population by design, so
conservation is not asserted for it.

## Validation

```text
py -3.12 -m pytest tests/ -q -k "pom or candypop or queen"   # 71 passed
```

## Acceptance gates

| Gate | Result |
|---|---|
| A Identity/content | PASS — real `Pom` bound by generator id, `engine=1`, source colour/budget stamped; base Pom rejected |
| C Combat/receivers | PASS — real swallow/discharge conversion of thrown Pikmin; own-colour refund; Queen multiplier |
| D Death/drop/transport | PASS (bounded) — sprouts born as expected; no reward path exercised |
| E Lifetime | PASS (bounded) — bound actor survives the cycle; teardown via `pc_p2_candypop_reset` |
| F Persistence | UNTESTED — no save/revisit in these fixtures |
| B Declared behavior | PARTIAL — engine colour buds + Queen cycle; BlackPom/WhitePom providers unchanged |
| G Product/mixed scene | N/A — private fixtures, no generated-session binding |
