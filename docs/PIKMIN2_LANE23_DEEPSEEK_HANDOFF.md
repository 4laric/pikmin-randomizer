# Lane 23 DeepSeek handoff — Candypop source FSM, budget-only death, conservation ledger (#448)

Session: lane 23 (Flora/Candypops). Implementation owner field remains Codex
through shared `4laric`; actual executing agent is a DeepSeek P2 fan-out worker.

## Source IDs and files owned

Concrete slice delivered: **Candypop Bud FSM completion** for the six buds
(`BluePom` 3, `RedPom` 4, `YellowPom` 5, `BlackPom` 6, `WhitePom` 7, `RandPom`
8) and the rejected base `Pom` (82), sourced from `enemy/Entities/Pom.h:153-161`
and the #171 audit (§"Candypop Buds").

Files owned by this slice:

- Native (family-local): `pc_port/pc_p2_pom_policy.h`, `pc_port/pc_p2_pom.cpp`.
- Root: `native-patches/pom/pc_p2_pom_policy.h` (kept byte-identical to the
  native header), `experimental/pikmin2_flora_behavior.py`,
  `experimental/pikmin2_pom_runtime.py`, `tests/pikmin2_pom_policy.cpp`,
  `tests/test_pikmin2_pom_runtime.py`, `docs/PIKMIN2_POM_NATIVE.md`.

No shared file (`teki.h`, `tekibteki.cpp`, `tekiinteraction.cpp`, `tekimgr.cpp`,
`gameCoreSection.cpp`, `navi.cpp`, `pc_p2_preview.cpp`, CMake) was modified by
this slice; all hooks the module uses were already integrated in the base.

## Ordered commits and dirty state

Root branch `deepseek/p2-l23` (base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`):

1. `6e92541` — `lane23: Candypop FSM/death/conservation model, harness, tests and policy mirror (#448)`
2. `43c9e4d` — `lane23: Candypop handoff and POM_NATIVE log-contract refresh (#448)` (this commit)

Native branch `deepseek/p2-l23-native` (base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`):

1. `8f6f1a8c` — `lane23: Candypop source six-state FSM, budget-only death and population-conservation ledger (#448)`
2. `179311ab` — `lane23: arm Open only on the cycle's first touch, keep each touch a Swing (#448)`

Both worktrees clean at handoff (`git status --short` empty) except the root
`docs/PIKMIN2_POM_NATIVE.md` edit staged into commit 2 above.

## Interfaces / hooks touched and why

`pc_p2_pom_policy.h` adds, in the existing `p2pom` namespace:

- `enum class State { Wait=0, Dead=1, Open=2, Close=3, Shot=4, Swing=5 }`
  mirroring `Pom.h:153-161`, plus `stateName(...)`.
- `bool dead(bool budgetSpent, int owed)` — budget-only death with conservation
  settlement (`owed == 0`), mirroring the audit's "death only from an exhausted
  budget" and the new `experimental.pikmin2_flora_behavior.candypop_dead`.

`pc_p2_pom.cpp` adds, without touching any existing marker:

- `Bound::state` + `setState(...)` emitting `P2_POM_STATE ... from=<s> to=<s>`.
- `finishDead(...)` emitting `P2_POM_DEAD ... corpse=0 budget=<n>` and
  `P2_POM_CONSERVATION ... used/refunds/requested/born/dead_pikis/loss_counted`.
- `GameStat::deadPikis` baseline captured in setup (after binding) and compared
  at death: every consumed Pikmin is `setEraseKill()`-killed, so `deadPikis`
  must not advance (consumption is not a loss). `dead_pikis` / `loss_counted`
  are logged once at termination.

The module remains sidecar-gated (`p2-pom.txt`), fail-closed and inert without
the sidecar.

## Build evidence (`output/dsw/l23-build-evidence.txt`)

```text
2026-09-14T19:37:15 lane=l23 target=pikmin_pc native=179311abfa967d1362d88c0c6d827072bc01baeb dirty=no
  build_dir=C:\Users\alari\pikmin-randomizer\output\dsw\native-l23-build
  exe=C:\Users\alari\pikmin-randomizer\output\dsw\native-l23-build\bin\nectar.exe
  sha256=81b59c966cd94f978687aae0a97e5b1223998020af2484348134985edbe7a081
  ninja_n="ninja: no work to do." seconds=122
```

- Native commit `179311abfa967d1362d88c0c6d827072bc01baeb`, clean.
- Main `nectar.exe` SHA-256 `81B59C966CD94F978687AAE0A97E5B1223998020AF2484348134985EDBE7A081`,
  `ninja -n pikmin_pc` reports "no work to do".
- Replacement-main fixture `pom-fixture-2/build/fixture.exe` SHA-256
  `F35A1038715CE7F3BEC272F00DEB16ACDD7F34AC6A5B7CA6E1100A6F56302BCD`,
  `provenance.json` status `built`, `expected_native_head` = `179311ab…`.

## Fixture adoption evidence

- `[PC Port] Experimental preview window set to 960x540 windowed and centered
  (override with PIKMIN_P2_ROOM_WINDOW=WxH or =off).` observed in `native.log`;
  `PIKMIN_P2_ROOM_WINDOW=960x540` set for the run.
- Starting squad: the Candypop runtime stages 10 injected red Pikmin
  (`experimental/pikmin2_pom_runtime.stage`) — a documented species-local
  override, not the default 20-red overlay. `p2-pom.txt`/`p2-pom-inject.txt` are
  strict sidecars; `P2_POM_FIXTURE_PLAN injected=3` and
  `P2_POM_FIXTURE_SPROUTS n=11` confirm live actors and births. No immediate
  extinction (the fixture's guard is a labeled injection).

Runtime result: `output/dsw/l23-out/pom-runtime-2/pom/9b0c5b412e7743d78f5e7211b10e04d7`,
`result.json` `passed=True`, `exit_code=0`, no leftover process, all 15 checks
green including the new `state_walk`, `dead`, `conservation`.

```text
P2_POM_STATE generator=240012 species=RandPom from=wait to=open
P2_POM_STATE generator=240012 species=RandPom from=open to=swing
P2_POM_STATE generator=240012 species=RandPom from=swing to=close
P2_POM_STATE generator=240012 species=RandPom from=close to=shot
P2_POM_STATE generator=240012 species=RandPom from=shot to=dead
P2_POM_DEAD generator=240012 species=RandPom used=1 refunds=0 corpse=0 budget=1
P2_POM_CONSERVATION generator=240012 species=RandPom used=1 refunds=0 requested=9 born=9 dead_pikis=0 loss_counted=0
P2_POM_STATE generator=240011 species=RedPom from=swing to=close
P2_POM_STATE generator=240011 species=RedPom from=close to=shot
P2_POM_STATE generator=240011 species=RedPom from=shot to=wait
PASS P2_POM_NATIVE accept_refund_close_sprout
```

## Six-gate table (honest, natural vs injected labeled)

| Gate | Result | Note |
|---|---|---|
| 1 Exact identity / spawn | identity PASS, spawn FAIL | IDs 4/8/82 correct (`P2_POM_BASE_REJECTED … source_id=82`); but the bud is a **module-local logic actor** anchored at sidecar positions, not an ordinary spawned/drawn actor. |
| 2 Movement / animation | movement source-backed N/A; animation UNTESTED | Buds do not move (source-correct). No bud model is drawn, so open/swing/shot clips are not rendered. FSM state walk is observed, not animated. |
| 3 Attacks / receivers | conversion receiver PASS (policy); physical slot press UNTESTED | accept/refund/close/shot routing is exercised; the receptor is a radius check on `PIKISTATE_Flying` Pikmin (fixture-injected), not a real collision-slot press. Invulnerable/immune source-correct. |
| 4 Death and corpse | **PASS** | `P2_POM_DEAD … corpse=0 budget=1` — budget-only death, source-correct no corpse. New in this slice. |
| 5 Transport / reward | sprout birth PASS; Onion seed receipt source-backed N/A | `born==requested` (`requested=9 born=9`, `P2_POM_FIXTURE_SPROUTS n=11`): real leaf-sprout births. Onion/AP seed accounting stays out of scope (lane 06). |
| 6 Cleanup / re-entry | partial | Dead buds are terminal (`done`), `pc_p2_pom_reset()` clears FSM/counter state; scene-teardown rebind of a living bud after a natural death is not exercised in this run. |

Population conservation (named lane goal) is now demonstrated: `dead_pikis=0
loss_counted=0` — converted Pikmin are erase-killed and never counted as losses,
and every consumed Pikmin's sprouts settle (`born == requested`).

## Tests run

```text
py -3.12 -m pytest tests/ -q -k "pom or flora or plant"          # 131 passed, 44 subtests
py -3.12 -m pytest tests/test_pikmin2_pom_runtime.py -q          # (included above; 7 protocol + consistency + native-policy cases)
g++ -std=c++17 -Wall -Wextra -Werror -I native-patches/pom tests/pikmin2_pom_policy.cpp
                                                                 # pikmin2_pom_policy PASS
```

## Assumptions made

- "Pom" naming: the P1 engine carries a `Pom` Boss (`src/plugPikiNishimura/Pom*.cpp`,
  `GENBOSS_Pom`) that is the **Pellet Posy** (`ポンガシ草` / "Pongashi" in
  `genBoss.cpp::doGenAge`), not the P2 Candypop Bud. The Candypop module therefore
  stays a logic actor; binding the engine Pom Boss as a *Candypop* would repeat the
  "proxy is not the source identity" mistake this lane is told to avoid. Binding
  that boss for the *Pelplant* remains an open, distinct slice.
- Own-colour "refund" retains the delivered module semantics (slot refunded; the
  Pikmin is still consume-erased) rather than relitigating the refund-vs-reject
  reading of `Pom.cpp:296-298`; changing that would need the P2 research source,
  which is a parallel checkout I do not edit.
- Per-cycle `mMaxPikiPerCycle` is not modeled in the module (budget `ip01`/`ip11`
  is the lifetime capacity), matching the audit's lifetime-budget reading.

## Remaining blockers (provider lane)

- **Ordinary spawn + draw for the Candypop bud** (visible `enemy/data/Pom` model,
  animation, slot collision): asset/conversion + an enemy-actor binding, not the
  P1 Pom Boss (see above). Converter/material side is lane 09 (#429), spawn
  binding is lane 03/05.
- **Onion/AP seed accounting** for the born sprouts / any Pellet Posy pellet:
  lane 06 (rewards/persistence).
- **Pellet Posy natural transport** (natural carry → Onion) remains blocked on
  the PC-port carry completion shared with lane 06/07; the Pelplant
  release/capture/exactly-once receipt slice is already integrated, delivery is
  still injected.
- **Plant Spectralid sentinel spawn** stays `P2_PLANT_SENTINEL_BLOCKED
  reason=no_qurione_seam` until lane 15 exposes a spawn seam or a shared spawn hook.

## One exact reproduction command

```powershell
$env:PATH='C:\msys64\mingw64\bin;'+$env:PATH
$env:PYTHONUTF8='1'
$env:PIKMIN_P2_ROOM_WINDOW='960x540'
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l23 -- py -3.12 -m experimental.pikmin2_pom_runtime run --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets --output C:/Users/alari/pikmin-randomizer/output/dsw/l23-out/pom-runtime-2 --exe C:/Users/alari/pikmin-randomizer/output/dsw/l23-out/pom-fixture-2/build/fixture.exe
```

## Slice 2

Slice 2 makes the Candypop bud an **ordinary spawned, drawn actor** (gate 1 spawn
FAIL → PASS) by binding each sidecar generator to the live batch-2 `flora`-family
Chappy placement vehicle and drawing the converted `enemy/data/Pom` bank through
the existing batch-2 display path, with the bud FSM driving the drawn pose.

### Source IDs and files owned

Candypop Buds (`BluePom` 3 .. `RandPom` 8, base `Pom` 82). New/changed files:

- Native: `pc_port/pc_p2_pom.h`, `pc_port/pc_p2_pom.cpp` (host bind + clip hook +
  forget); additive one-line hook `pc_port/pc_p2_batch2.cpp` (`pc_p2_pom_clip`
  in the forced-clip chain) + one `pc_p2_pom_forget` line in
  `pc_port/pc_p2_teki_lifetime.cpp`.
- Root: `experimental/pikmin2_pom_runtime.py` (stage now = flora-arena prepare +
  `p2-pom.txt` sidecars; validator gains `bind`/`drawn`), `tests/test_pikmin2_pom_runtime.py`,
  `docs/PIKMIN2_POM_NATIVE.md`.

### Ordered commits and dirty state

Root branch `deepseek/p2-l23` (base `ef1cace`, previous head `23fe0ec`):

1. `lane23: slice 2 — flora-arena Chappy-vehicle Candypop runtime, bind/draw validator and tests (#448)`

Native branch `deepseek/p2-l23-native` (base `b805d9c6`, previous head `df78cc06`):

1. `f313d5df` — `lane23: slice 2 — bind Candypop buds to the batch-2 Chappy host, drive clipped draw, forget on despawn (#448)`
2. `f41beb27` — `lane23: keep candypop conversion slot at the planted point, not the movable vehicle (#448)`

Both worktrees clean at handoff.

### Interfaces/hooks touched and why

- `pc_p2_pom` gains `pc_p2_pom_forget(BTeki*)`, `pc_p2_pom_clip(const BTeki*, const char*&, float&)`,
  `pc_p2_pom_bound()`; `pc_p2_pom_tick()` lazily `bindHosts()` by generator id
  + `TEKI_Chappy` assert and emits `P2_POM_BIND ... host=teki type=3 drawn=1`.
- `pc_p2_pom_clip` maps `p2pom::State` → clip (Wait→wait, Open→type1, Close→type2,
  Shot→type3, Swing→type4, Dead→dead) and emits `P2_POM_DRAW ... pose=<state> draws=<n>`.
- `pc_p2_batch2_draw` forced-clip chain gets `pc_p2_pom_clip` (mirror of `pc_p2_hana_clip`).
- `pc_p2_forget_teki` gains `pc_p2_pom_forget`. Conversion slot stays at the
  planted point (sidecar XYZ) so a moving vehicle cannot move the receptor.

### Build / fixture / runtime evidence

- Native `f41beb27df604df01c845fd577033406c94d912e`, clean. Main `nectar.exe`
  SHA-256 `41ED946D8752CFE51A6DDE07C3949C72D2E8525039EB300B790E26F79BB2E874`,
  `ninja -n pikmin_pc` "no work to do".
- Fixture `output/dsw/l23-out/pom-fixture-3/build/fixture.exe` SHA-256
  `E7DB285A0D667A32D90164A8EB6195E7FD973F4E93F127F5FF2D0C6A277AC506`,
  `provenance.json` status `built`, expected native head `f41beb27`.
- Converted bank: `output/dsw/l23-out/flora-bank` produced by
  `experimental/pikmin2_flora_assets` (`--pose-limit 3`); all six bud clips
  (`wait/dead/type1..type4`) convert 3/3 poses; HikariKinoko recorded unsupported.
- GL run `output/dsw/l23-out/pom-runtime-3/pom/591b53c59d2b4738844371d963a43abe`
  PASS (exit 0), 17/17 checks green, 960×540 centred window. New evidence:

```text
P2_POM_BIND generator=353003 species=RedPom source_id=4 host=teki type=3 drawn=1
P2_POM_BIND generator=353007 species=RandPom source_id=8 host=teki type=3 drawn=1
P2_BATCH2_DRAW corpse=0 key=flora|YellowPom clip=wait
P2_POM_DRAW generator=353007 species=RandPom pose=wait draws=1 ... draws=10
P2_POM_DRAW generator=353007 species=RandPom pose=shot draws=11
P2_POM_DEAD generator=353007 species=RandPom used=1 refunds=0 corpse=0 budget=1
P2_POM_CONSERVATION generator=353007 species=RandPom ... dead_pikis=0 loss_counted=0
P2_POM_DRAW generator=353007 species=RandPom pose=dead draws=13 ...
PASS P2_POM_NATIVE accept_refund_close_sprout
```

### Gates that changed

- Gate 1 (exact identity / spawn): **FAIL → PASS (spawn)**. The bud is now bound
  to a live generator-spawned `TEKI_Chappy` host and reports `P2_POM_BIND` with
  the correct source id (4 / 8) and base-Pom rejection. Identity is still the
  Chappy *vehicle*; the drawn visual is the converted Pom bank.
- Gate 2 (movement/animation): animation now **drawn** via batch-2 (static bind
  pose, clip per FSM state — `pose=wait -> shot -> dead`); no skeletal playback.
- Gate 4/5/6 (death/conservation/re-entry): unchanged PASS, now executing on the
  spawned host, plus `pc_p2_pom_forget` for despawn.

### Subagent usage

Three `task` subagents ran per the slice-2 instructions (experiment, per the wave
brief):

1. `explore` — batch-2/batch-4 proxy-vehicle host-bind + draw-path source audit.
   Result used **as-is**: confirmed `FAMILIES['flora']` maps buds → `TEKI_Chappy`,
   sidecar grammar `P2_FLORA_ACTORS_1`/`P2_FLORA_BANK_1`, draw chain
   `pc_p2_batch2_draw` at `tekibteki.cpp:170/2094`, and the `pc_p2_hana_clip`
   forced-clip hook to mirror. Saved a large amount of native-file reading.
2. `explore` — flora/pom/batch2 candidate + converted-bank inventory. Used **as-is**:
   established the bank did not yet exist and located the engine Pom Boss
   (P1 Pellet Posy, must-not-reuse), which drove the decision to convert via
   `pikmin2_flora_assets`. One finding (no `pc_p2_batch4` file; "batch 4" rides
   `pc_p2_batch2`) corrected my mental model.
3. `general` — wrote the `bind`/`drawn` validator checks + pytest scaffolding
   against my marker spec, ran pytest (7 passed). Used **as-is**; I later changed
   the synthetic validator test IDs from my provisional 240011/240012 to the
   real flora-arena generators 353003/353007/353099.

Net: the two explorers removed most of the read-heavy search from my context; the
general subagent saved a modest amount of test-scaffolding typing. Rough estimate
~20–30 minutes saved over doing everything inline; no result had to be discarded.

### Remaining blockers (provider lane)

- Drawn model is a static bind pose; skeletal playback/material fidelity → lane 09 (#429).
- Ordinary **generated-session** spawn binding (the flora arena is an engineered
  placement vehicle, not production placement) → lanes 03/04/05.
- Onion/AP seed accounting for sprouts/pellets → lane 06.
- Spectralid sentinel spawn → lane 15 (untouched).

### Reproduction

```powershell
$env:PATH='C:\msys64\mingw64\bin;'+$env:PATH
$env:PYTHONUTF8='1'
$env:PIKMIN_P2_ROOM_WINDOW='960x540'
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l23 -- py -3.12 -m experimental.pikmin2_pom_runtime run --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets --imported C:/Users/alari/pikmin-randomizer/output/dsw/l23-out/flora-bank --output C:/Users/alari/pikmin-randomizer/output/dsw/l23-out/pom-runtime-3 --exe C:/Users/alari/pikmin-randomizer/output/dsw/l23-out/pom-fixture-3/build/fixture.exe
```
