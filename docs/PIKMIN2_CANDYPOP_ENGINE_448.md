# P2 Candypop Bud real engine binding (lane 23, #448 / #171)

## Scope

This slice replaces the module-local injected Candypop actor for the three
P1-representable colour buds with the **real engine `Pom` Boss**
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
- Base `Pom` (82) is rejected and never bound.
- BlackPom/WhitePom remain with the existing violet/ivory providers
  (`pc_p2_purple.cpp` / `pc_p2_white.cpp`); the Queen (`RandPom`) colour cycle is
  **not** in this slice.

New files (native): `pc_port/pc_p2_candypop.{h,cpp}`. Additive hooks in
`src/plugPikiNishimura/PomAi.cpp` (`initAI` config + `createPikiHead` conversion),
`CMakeLists.txt`, `pc_port/pc_p2_preview.cpp`, `src/plugPikiKando/gameCoreSection.cpp`
and `pc_port/pc_p2_teki_lifetime.cpp`.

## Source anchors

| Behavior | Value | Anchor |
|---|---|---|
| Own-colour refund | same colour does not spend a slot | P2 `Pom.cpp:296-299` (`Obj::shotPikmin`) |
| Lifetime budget | `ip01` = 5 colour buds | disc `pom/enemyparm.txt` |
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
base `Pom` row is parsed, logged `P2_POM_BASE_REJECTED`, and skipped; non-RGB
colour buds are logged `P2_CANDYPOP_UNSUPPORTED`.

## Log contract

```text
P2_CANDYPOP_SIDECAR engine_buds=<n>
P2_POM_READY generator=<id> species=<name> source_id=<n> colour=<c> budget=<n> queen=<0|1> engine=1 x=.. y=.. z=..
P2_POM_INVULNERABLE generator=<id> invulnerable_after_landing=1
P2_CANDYPOP_WITNESS generator=<id> species=<name> input=<blue|red|yellow> refund=<0|1>
P2_CANDYPOP_CONVERT generator=<id> species=<name> converted=<n> used=<n> refunds=<n>
```

`refund=1` marks an own-colour input that consumed no slot; `used` is the
non-refunded slot count returned to `PomAi` (added to `mReleasedSeedCount`).

## Implemented

- Real engine actor bound and configured (`mMaxPikiPerCycle` = source budget,
  `mCloseWaitTime` = 1.0 s, any-colour entry, no same-colour kill).
- Real Pikmin throws via the ordinary `Navi::throwPiki` path; the engine
  swallow → close → discharge path performs the conversion.
- Source own-colour refund with population conservation.
- Base-Pom rejection and non-RGB explicit unsupported handling.
- Inert without the sidecar; reset clears bindings per stage.

## BLOCKED / remaining

- **RandPom Queen colour cycle.** The engine `Pom::setColor` accepts only P1
  colours; the source Blue/Red/Yellow cycle is not ported into this actor.
- **BlackPom/WhitePom** remain with the violet/ivory providers (no lane-23
  engine binding).
- **Natural generation/admission.** Placement, generated-session binding,
  rewards, save persistence and mixed-scene acceptance are unchanged and still
  belong to lanes 03/04/05/06/33.
- **Aim timing is scripted.** The fixture re-aims pending throws every 12 ticks;
  the throws, swallow, conversion and sprouts are engine behaviour, but the aim
  schedule is a labeled injection, not manual play.

## Approximations and labeled injections

- Boss generator rows are cloned from the challenge `ssob` template and stamped
  `GENBOSS_Pom`; the staged position is a fixture placement, not source routing.
- All staged boss generators carry a Red container colour so the engine birth
  gate passes; the module re-stamps the source colour. The fixture aim/timing is
  scripted (`P2_POM_ENGINE_PLAN`).

## Build and fixture provenance

- Native `opencode/p2-lane23-pom-native` @
  `7bb324d80ead443b88aa154556af8aec3b75d355` (base `b805d9c6`; never pushed).
  Private build `output/native-lane23-pom-build` (Ninja Release/MinGW, JAudio
  ON, IPO ON); `ninja -n pikmin_pc` -> no work to do; executable
  `bin/nectar.exe` SHA-256 `15DAC0D0E757D1FF38B4B0ECA3D307EA44206678AC5686FA013BEB771F08689E`.
- Root `opencode/p2-lane23-pom` @ `223138f` (based on
  `origin/codex/p2-main-review` `4fccf41`).
- Fixture `output/lane23-pom-fixture-2/build/fixture.exe` SHA-256
  `ded0be6237bdcba89063d34ec03c1e2894725377eda297727fc878fed10e6ff2`,
  `provenance.json` status `built`, expected/observed native head `7bb324d8`.

## Runtime evidence (960x540, live squad)

Run `output/lane23-pom-runtime-02/engine/4f955eec19a4410ba8e98905b734f767`,
validator all-true (`completion`, `ready_red`, `ready_blue`, `base_rejection`,
`convert_red`, `convert_blue`, `witnesses_refund`, `witnesses_used`,
`conservation`, `no_rewards`), exit 0, no leftover process:

```text
[PC Port] Experimental preview window set to 960x540 windowed and centered ...
P2_POM_BASE_REJECTED generator=240013 species=Pom source_id=82 reason=nonspawnable_base
P2_CANDYPOP_SIDECAR engine_buds=2
P2_POM_READY generator=240011 species=RedPom source_id=4 colour=1 budget=5 queen=0 engine=1 x=-25.00 y=30.00 z=1850.00
P2_POM_READY generator=240012 species=BluePom source_id=3 colour=0 budget=5 queen=0 engine=1 x=25.00 y=30.00 z=1850.00
P2_CANDYPOP_CONVERT generator=240011 species=RedPom converted=5 used=3 refunds=2
P2_CANDYPOP_CONVERT generator=240012 species=BluePom converted=5 used=3 refunds=2
P2_POM_ENGINE_STATE initial=12 sprouts=10 alive=2
PASS P2_POM_ENGINE real_conversion_refund_conservation
```

Each bud swallowed five real Pikmin (two own-colour refunds, three used) and
produced five sprouts; twelve field Pikmin became ten sprouts plus two
survivors, so `alive + sprouts == initial`.

## Validation

```text
py -3.12 -m pytest tests/ -q -k "pom or candypop"        # 34 passed
py -3.12 -m pytest tests/test_pikmin2_pom_engine_runtime.py -q
```

## Acceptance gates

| Gate | Result |
|---|---|
| A Identity/content | PASS — real `Pom` bound by generator id, `engine=1`, source colour/budget stamped; base Pom rejected |
| C Combat/receivers | PASS — real swallow/discharge conversion of thrown Pikmin; own-colour refund |
| D Death/drop/transport | PASS (bounded) — five sprouts per bud, population conserved; no reward path exercised |
| E Lifetime | PASS (bounded) — bound actor survives the cycle; full stage teardown is the existing `pc_p2_candypop_reset` |
| F Persistence | UNTESTED — no save/revisit in this fixture |
| B Declared behavior | PARTIAL — P1-representable colour buds; Queen cycle and Black/White providers unchanged |
| G Product/mixed scene | N/A — private fixture, no generated-session binding |
