# Lane 22 — DeepSeek handoff: real actor-bound elemental dweevil (FireOtakara 59)

Tracking issue #447 (parent #170). Implementation owner: Codex through shared
account `4laric`; executing session: DeepSeek lane 22.

## 1. Concrete source ID and missing gate addressed

- **Source ID owned:** `FireOtakara` (EnemyID 59), plus the shared-base
  elemental siblings WaterOtakara (60), GasOtakara (61), ElecOtakara (62) bound
  through the same FSM.
- **Missing gate addressed:** the ledger's open item — "Dweevil/BombOtakara
  sidecars still need real actor/payload ownership". Prior lane-22 modules
  (`pc_p2_dweevil`, `pc_p2_hiba`, `pc_p2_bombotakara`) were sidecar/policy
  simulations with **no real engine actor binding**, and the batch-3 result was
  "FireOtakara host accepts the attack but takes no damage". This slice binds a
  real `TEKI_Chappy` placement vehicle by generator ID, sets the source fp00
  life (150), drives the shared OtakaraBase Flick discharge through the actual
  `InteractFire` receiver, and proves the natural elemental-emitter →
  receiver-immunity chain and the queue-then-apply death path.

## 2. Ordered commits

**Root** (worktree `C:/Users/alari/pikmin-randomizer/output/dsw/l22-root`,
branch `deepseek/p2-l22`, base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`):
- (commit in this session) `experimental/pikmin2_otakara_runtime.py`,
  `tests/test_pikmin2_otakara_native.py`, and this doc.

**Native** (worktree `C:/Users/alari/pikmin-randomizer/output/dsw/native-l22`,
branch `deepseek/p2-l22-native`, base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`):
- `c423b5d44c1602da54beb8e9c9dcc2c87cb2bd1f` — "lane22: real actor-bound
  elemental dweevil FSM (pc_p2_otakara) with natural discharge receivers (#447)".

Both worktrees clean at handoff (root had only the two new files staged; native
clean).

## 3. Interfaces / hooks touched and why

New family-local module: `pc_port/pc_p2_otakara.{h,cpp}` (dweevil source FSM).
Shared-file hooks are narrow, additive, separately labelled:

- `src/plugPikiNakata/tekibteki.cpp` — `pc_p2_otakara_update(this);` in
  `BTeki::update()` (mirrors the existing family update hooks).
- `include/teki.h` — `#include "pc_p2_otakara.h"` and
  `pc_p2_otakara_param_f(...)` chained into `getParameterF` (life override:
  `TPF_Life` → source fp00, `TPF_LifeRecoverRate` → 0).
- `pc_port/pc_p2_batch2.cpp` — `pc_p2_otakara_clip(...)` added to the forced
  clip/phase chain so the FSM drives the source `wait1`/`attack1`/`dead` clips.
- `pc_port/pc_p2_teki_lifetime.cpp` — `pc_p2_otakara_forget(actor)` in the
  central forget seam; `pc_p2_otakara_reset()` in the central reset.
- `src/plugPikiNakata/tekimgr.cpp` — `pc_p2_otakara_reset()` in the three
  TekiMgr reset paths (matches the existing family pattern).
- `pc_port/pc_p2_preview.cpp` — `pc_p2_otakara_setup();` in the staged setup list.
- `CMakeLists.txt` — `PC_PORT_SOURCES += pc_port/pc_p2_otakara.cpp`.

Elemental immunity is **not** reimplemented: the emitter consults the lane-11
capability matrix (`p2_species_immune` / `p2_emitter_accepts`) and delivers the
real receivers (`InteractFire`/`InteractBubble`/`InteractGas`/`InteractDenki`).
BombOtakara (93) is deliberately left unbound — it consumes the lane-20 shared
Bomb blast contract; Gas/Denki use the receivers integrated in lane 10.

## 4. Build evidence

From `output/dsw/l22-build-evidence.txt`:

```text
native=c423b5d44c1602da54beb8e9c9dcc2c87cb2bd1f  target=pikmin_pc  dirty=no
exe=bin/nectar.exe
sha256=4EC808B25A18A0FDEEC814AE101987DA532A2630AB8A33EADA01B8577550D227
ninja_n="ninja: no work to do."
```

Configured via the lane private build
`output/dsw/native-l22-build` (Ninja + MinGW g++ Release, `PIKMIN_NATIVE_JAUDIO=ON`,
`CMAKE_MAKE_PROGRAM=<python-bundled ninja.exe>`). Full build `[604/604] Linking
CXX executable bin\nectar.exe` (exit 0). The shared `build_lane.py` wrapper was
broken by a concurrent peer edit (an escaped `'\'` literal), so configure/build
was run through the documented `slot.py run build l22 -- cmake ...` fallback
with the same flags; evidence recorded manually.

## 5. Fixture adoption evidence

- 960×540 centred window observed:
  `Experimental preview window set to 960x540 windowed and centered`.
- Live starting squad: `P2_OTAKARA_SQUAD red=1 blue=0 registered=1` (the fixture
  recolours the two starting Pikmin Red/Blue; the squad is live and no extinction).
- Fixture exe `output/dsw/l22-fixture/fixture.exe` SHA-256
  `F07529ED6BA0ABA1C45D9789B978933FE2B8206E6C7A97E4E9683EB2C846AB75`,
  `provenance.json` / `instrumentation.json` status `built`, expected native head
  `c423b5d4...`.
- GL run `output/dsw/l22-runtime/ee98ae5edee9433795a176880b33c235`, exit 0,
  `PASS P2_OTAKARA_RUNTIME`, no extinction.

## 6. Six arena gates (natural vs injected)

| Gate | Result | Evidence |
|---|---|---|
| 1 Exact identity and spawn | **PASS (natural)** | `P2_OTAKARA_BIND generator=349001 source_id=59 stimulus=InteractFire visual_only=0`; `P2_ENEMY_READY species=FireOtakara native_family=Chappy ... health=150.0 max_health=150.0 behavior=native source_FSM=implemented attack=elemental_discharge` |
| 2 Autonomous movement and animation | **PASS (natural)** | FSM drives source clips: `P2_OTAKARA_STATE ... state=flick`, `P2_BATCH2_DRAW corpse=0 key=dweevil\|FireOtakara clip=attack1`, sampled event clock `P2_BATCH2_EVENT ... attack1 frame=12 event=2 / frame=20 / frame=27 / frame=35 event=3` |
| 3 Attacks and receivers | **PASS (natural emitter, real receiver)** | `P2_OTAKARA_DISCHARGE ... stimulus=InteractFire applied=1 immune=3`; `P2_OTAKARA_DISCHARGE_IMMUNE ... colour=red` (fire-immune) vs `P2_OTAKARA_DISCHARGE_HIT ... colour=blue ... accepted=1` |
| 4 Death and corpse | **PASS death path (injected damage trigger), corpse UNTESTED** | `P2_OTAKARA_DEATH_INJECT before=135.0` (labeled `InteractAttack` injection) → queue-then-apply → `P2_OTAKARA_DEAD ... health=0`; host corpse-pellet teardown not asserted |
| 5 Actual transport and reward | **UNTESTED / BLOCKED** | corpse pellet transport to Onion not observed; dweevil reward is the recovered treasure (no treasure staged) |
| 6 Cleanup and re-entry | **Forget/reset wired + built; runtime UNTESTED** | `pc_p2_otakara_forget/reset` in the central lifetime seam and TekiMgr reset paths; scene-exit rebind not driven in the fixture |

Injected interventions (labelled): the fatal `InteractAttack` damage value and
the recolour/parking of the two starting Pikmin inside the discharge radius. The
FSM, the elemental emitter, the receiver immunity decision, the health value and
the death state are all native.

## 7. Tests

```
py -3.12 -m pytest tests/test_pikmin2_otakara_native.py -q                                   # 8 passed
py -3.12 -m pytest tests/test_pikmin2_otakara_native.py tests/test_pikmin2_elemental_behavior.py tests/test_pikmin2_dweevil_native.py -q   # 56 passed
```

`tests/test_pikmin2_otakara_native.py` pins the native source wiring (update /
param_f / clip / forget / reset / setup / CMake) and the disc parameter facts
(fp00 life 150/350, fp24 attack 10/0) against
`docs/PIKMIN2_DWEEVIL_ASSETS.md`.

## 8. Assumptions

- Dweevil own health = general fp00 life (Fire/Water/Elec 150, Gas 350); the
  proper-block fp01 "otakara life" 80 applies to a *captured treasure*, not the
  dweevil itself, so it is not the actor's max health.
- Only the normal OtakaraBase states are implemented; item-carry (5–10) and
  Bomb-carry (11–13) are source-backed N/A (no treasure/Bomb payload staged).
- `gun 0` hit angle on disc: the discharge uses a full-circle 60-unit radius
  (fp22), matching the source hit range.
- Fire immunity for the fixture is exercised via the P1 colour path
  (`setColor(Red)`), which `pc_p2_species` already maps to `P2SpeciesRed`
  (both enums align Blue=0/Red=1/Yellow=2).

## 9. Remaining blockers (provider lane named)

- **Corpse transport / reward**: reward semantics belong to lane 06; a real
  treasure capture + exactly-once drop + Onion receipt is the next slice
  (the sidecar policy already pins the drop contract).
- **BombOtakara real payload actor**: lane 20 (shared Bomb blast). The
  `pc_p2_bombotakara` blast consumer already routes the shared primitive; the
  detached `EnemyID_Bomb` actor + `mCarrier` linkage remain lane 20.
- **Scene re-entry / recycled-address rebind**: lane 07 lifetime harness;
  forget/reset are wired but not runtime-proven here.
- **Water/Gas/Elec discharge runtime**: lanes 10/11 receivers are wired; only
  the Fire/receiver was exercised in this fixture (Gas/Denki would transit
  `PIKISTATE_Panic`/`DenkiDying`).

## 10. Reproduction

```powershell
$env:PYTHONUTF8='1'
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l22 -- `
  py -3.12 -m experimental.pikmin2_otakara_runtime run `
    --assets "C:/Users/alari/bbft/dist/cohesion/pikmin/assets" `
    --imported "C:/Users/alari/pikmin-randomizer/output/dsw/l22-assets" `
    --output "C:/Users/alari/pikmin-randomizer/output/dsw/l22-runtime-repro" `
    --exe "C:/Users/alari/pikmin-randomizer/output/dsw/l22-fixture/fixture.exe" `
    --seconds 150
```
