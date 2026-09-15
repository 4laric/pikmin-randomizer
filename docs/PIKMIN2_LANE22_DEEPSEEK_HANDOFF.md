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
  receiver-immunity chain, the natural pre-injection damage receipt, and the
  queue-then-apply death path.

## 2. Ordered commits

**Root** (worktree `C:/Users/alari/pikmin-randomizer/output/dsw/l22-root`,
branch `deepseek/p2-l22`, base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`):
- `ff83c3c` — "lane22: real FireOtakara actor FSM runtime + tests + handoff (#447)"
  (adds `experimental/pikmin2_otakara_runtime.py`, `tests/test_pikmin2_otakara_native.py`,
  `docs/PIKMIN2_LANE22_DEEPSEEK_HANDOFF.md`).
- (fix1 commit, this session) — "lane22: review fixes — natural-damage log,
  squad counts, WAIT timer fix, validate test + path discovery (#447)".

**Native** (worktree `C:/Users/alari/pikmin-randomizer/output/dsw/native-l22`,
branch `deepseek/p2-l22-native`, base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`),
rewritten from the earlier single `c423b5d` into two commits:
- `fce546af` — "lane22: hooks — additive Otakara registration in teki.h/tekibteki/tekimgr/preview/lifetime/batch2/CMake (#447)".
- `784d157c` — "lane22: pc_p2_otakara module (#447)" (module + review fixes:
  natural-damage `P2_OTAKARA_HIT` log, `prevHealth` tracking, and the
  post-flick WAIT timer reset).

Both worktrees clean at handoff.

## 3. Interfaces / hooks touched and why

New family-local module: `pc_port/pc_p2_otakara.{h,cpp}` (dweevil source FSM).
Shared-file hooks are narrow, additive, and isolated in the `fce546af` hook
commit:

- `src/plugPikiNakata/tekibteki.cpp` — `pc_p2_otakara_update(this);` in
  `BTeki::update()`.
- `include/teki.h` — `#include "pc_p2_otakara.h"`; `pc_p2_otakara_param_f(...)`
  chained into `getParameterF` (`TPF_Life` → source fp00, `TPF_LifeRecoverRate`
  → 0).
- `pc_port/pc_p2_batch2.cpp` — `pc_p2_otakara_clip(...)` in the forced
  clip/phase chain (drives `wait1`/`attack1`/`dead`).
- `pc_port/pc_p2_teki_lifetime.cpp` — `pc_p2_otakara_forget(actor)` in the
  central forget seam; `pc_p2_otakara_reset()` in the central reset.
- `src/plugPikiNakata/tekimgr.cpp` — `pc_p2_otakara_reset()` in the three
  TekiMgr reset paths.
- `pc_port/pc_p2_preview.cpp` — `pc_p2_otakara_setup();` in the staged setup list.
- `CMakeLists.txt` — `PC_PORT_SOURCES += pc_port/pc_p2_otakara.cpp`.

Elemental immunity is **not** reimplemented: the emitter consults the lane-11
capability matrix (`p2_species_immune` / `p2_emitter_accepts`) and delivers the
real receivers (`InteractFire`/`InteractBubble`/`InteractGas`/`InteractDenki`).
BombOtakara (93) is deliberately left unbound — it consumes the lane-20 shared
Bomb blast contract; Gas/Denki use the receivers integrated in lane 10.

## Evidence (artifacts on disk)

- Native private build dir: `C:/Users/alari/pikmin-randomizer/output/dsw/native-l22-build`.
- Fixture: `C:/Users/alari/pikmin-randomizer/output/dsw/l22-fixture-fix1/`
  (`fixture.exe` + `baseline/provenance.json` + `instrumentation.json`, status `built`).
- GL run: `C:/Users/alari/pikmin-randomizer/output/dsw/l22-runtime-fix1/5ae1eeb7e72a4e929e4b45677909ed74/`
  (`capture/native.log`, `otakara-validation.json`).
- Assets: `C:/Users/alari/pikmin-randomizer/output/dsw/l22-assets/` (`dweevils.json`).
- Build evidence log: `C:/Users/alari/pikmin-randomizer/output/dsw/l22-build-evidence.txt`.

## 4. Build evidence

From `output/dsw/l22-build-evidence.txt` (latest two lines):

```text
native=c423b5d4...  sha256=4EC808B25A18A0FDEEC814AE101987DA532A2630AB8A33EADA01B8577550D227   (first slice)
native=784d157c...  sha256=5AAD21798B838F1480E19AA97CC4ECBBBCB2686B043CFE1A0766A29259AA790B   (fix1)
```

Configured via the lane private build `output/dsw/native-l22-build` (Ninja +
MinGW g++ Release, `PIKMIN_NATIVE_JAUDIO=ON`, `CMAKE_MAKE_PROGRAM=<python-bundled
ninja.exe>`). Full link `[604/604] Linking CXX executable bin\nectar.exe`,
`ninja -n pikmin_pc` → `ninja: no work to do.`. The shared `build_lane.py`
wrapper was broken by a concurrent peer edit (`'\'` string literal), so
configure/build used the documented `slot.py run build l22 -- cmake ...`
fallback with the same flags; evidence recorded manually.

## 5. Fixture adoption evidence (fix1 run)

- 960×540 centred window:
  `Experimental preview window set to 960x540 windowed and centered`.
- Live starting squad (actual counts, not enum constants):
  `P2_OTAKARA_SQUAD red=19 blue=1 registered=1` (20-red overlay, one recoloured
  Blue); no extinction.
- Fixture exe `output/dsw/l22-fixture-fix1/fixture.exe` SHA-256
  `81D80858253860DAB1F242E33426703EB8A07FD7F638CA228ECFB7E912924103`.
- GL run exit 0, `PASS P2_OTAKARA_RUNTIME`.

## 6. Six arena gates (natural vs injected)

| Gate | Result | Evidence |
|---|---|---|
| 1 Exact identity and spawn | **PASS (natural)** | `P2_OTAKARA_BIND generator=349001 source_id=59 stimulus=InteractFire visual_only=0`; `P2_ENEMY_READY species=FireOtakara ... health=150.0 max_health=150.0 behavior=native source_FSM=implemented attack=elemental_discharge` |
| 2 Autonomous movement and animation | **PASS (natural)** | `P2_OTAKARA_STATE ... state=flick`, `P2_BATCH2_DRAW corpse=0 key=dweevil\|FireOtakara clip=attack1`, sampled event clock `P2_BATCH2_EVENT ... attack1 frame=12 event=2 / frame=20 / frame=27 / frame=35 event=3` |
| 3 Attacks and receivers | **PASS (natural emitter, real receiver)** | `P2_OTAKARA_DISCHARGE ... stimulus=InteractFire applied=1 immune=3`. The emitter honours the lane-11 matrix and simply does not deliver to a fire-immune Pikmin (`P2_OTAKARA_DISCHARGE_IMMUNE ... colour=red`, emitter-side); a Blue Pikmin reaches the real `InteractFire` receiver (`P2_OTAKARA_DISCHARGE_HIT ... colour=blue accepted=1`, later `PIKISTATE_Fired`) |
| 4 Death and corpse | **Injected damage applied 135→0; host die()/dieSoon()/becomePellet() UNTESTED** | Natural `P2_OTAKARA_HIT ... health=150.0->135.0 delta=15.0` (pre-injection, unlabelled combat) → labelled `P2_OTAKARA_DEATH_INJECT before=135.0` → `P2_OTAKARA_HIT ... 135.0->0.0` → `P2_OTAKARA_DEAD health=0`. The fixture exits at the health drop, so host corpse teardown is not observed |
| 5 Actual transport and reward | **UNTESTED / BLOCKED** | corpse pellet transport to Onion not observed; dweevil reward is the recovered treasure (no treasure staged) |
| 6 Cleanup and re-entry | **Forget/reset wired + built; runtime UNTESTED** | `pc_p2_otakara_forget/reset` in the central lifetime seam and TekiMgr reset paths; scene-exit rebind not driven in the fixture |

Injected interventions (labelled): the fatal `InteractAttack` damage value and
the recolour/parking of the two starting Pikmin inside the discharge radius. The
FSM, the elemental emitter, the receiver immunity decision, the source health
value, the natural 150→135 damage receipt and the health→0 death drop are all
native. The 15 HP lost before injection is the strongest evidence against the
ledger's "takes no damage" blocker: it is now logged explicitly as
`P2_OTAKARA_HIT health=150.0->135.0 delta=15.0` rather than inferred.

## 7. Tests

```
PIKMIN_NATIVE_ROOT=C:/Users/alari/pikmin-randomizer/output/dsw/native-l22 \
  py -3.12 -m pytest tests/test_pikmin2_otakara_native.py tests/test_pikmin2_otakara_runtime.py \
                    tests/test_pikmin2_elemental_behavior.py tests/test_pikmin2_dweevil_native.py -q
# 60 passed

py -3.12 -m pytest tests/test_pikmin2_otakara_native.py tests/test_pikmin2_otakara_runtime.py -q
# 6 passed, 6 skipped (native source-read tests skip cleanly without PIKMIN_NATIVE_ROOT)
```

- `tests/test_pikmin2_otakara_native.py` pins the native source wiring and disc
  parameter facts; native-path discovery now honours
  `PIKMIN_NATIVE_ROOT` / `P2_NATIVE_PC_PORT` / `ROOT/native` (no hardcoded
  absolute path, no lane-specific env var).
- `tests/test_pikmin2_otakara_runtime.py` (new) exercises
  `experimental/pikmin2_otakara_runtime.validate` on a sample log: a good log
  passes; removing `P2_OTAKARA_DEAD` flips `checks['dead']`; removing
  `P2_OTAKARA_DISCHARGE_HIT` flips `checks['hit_blue']`; a nonzero exit fails.

## 8. Assumptions

- Dweevil own health = general fp00 life (Fire/Water/Elec 150, Gas 350); the
  proper-block fp01 "otakara life" 80 applies to a *captured treasure*, not the
  dweevil itself, so it is not the actor's max health.
- Only the normal OtakaraBase states are implemented; item-carry (5–10) and
  Bomb-carry (11–13) are source-backed N/A (no treasure/Bomb payload staged).
- fp23 hit angle 0 on disc means a full-circle discharge (radius fp22 = 60),
  matching the source.
- Fire immunity for the fixture is exercised via the P1 colour path
  (`setColor(Red)`), which `pc_p2_species` already maps to `P2SpeciesRed`
  (both enums align Blue=0/Red=1/Yellow=2).

## 9. Remaining blockers (provider lane named)

- **Host death/corpse teardown + transport/reward**: lane 06; a real treasure
  capture + exactly-once drop + Onion receipt is the next slice (the sidecar
  policy already pins the drop contract).
- **BombOtakara real payload actor**: lane 20 (shared Bomb blast); the
  `pc_p2_bombotakara` blast consumer already routes the shared primitive.
- **Scene re-entry / recycled-address rebind**: lane 07 lifetime harness.
- **Water/Gas/Elec discharge runtime**: lanes 10/11 receivers are wired; only
  Fire/receiver was exercised in this fixture.

## Subagent usage

Three subagents were run in parallel (per the slice's work instructions):

1. **explore — Otakara source audit.** Confirmed the 14-state FSM, the
   flick(2)/discharge(3)/end(1000) event semantics, per-species stimulus map,
   retail fp00/fp06/fp12/fp22/fp24 parameters, and the four receiver immunity
   rows with file:line citations. Used as-is; no contradictions with the pinned
   docs (only a header-vs-disc note: fp22 header 70 vs disc 60).
2. **explore — candidate inventory.** Enumerated every lane-22 module/hook/
   harness/test/doc and the exact `pc_p2_otakara` hook sites and markers. Used
   as-is; surfaced the (expected) BombOtakara-93 overlap across the sidecar
   modules and the root/native `engine/` divergence.
3. **general — test/harness scaffolding.** Fixed `tests/test_pikmin2_otakara_native.py`
   native-path discovery (PIKMIN_NATIVE_ROOT / P2_NATIVE_PC_PORT / ROOT/native,
   removed the hardcoded path) and added `tests/test_pikmin2_otakara_runtime.py`
   validate tests. Used nearly as-is; I then added a `natural_damage` check to
   `validate()` (the subagent's GOOD log already contained the matching line, so
   its tests still pass). Net: saved roughly the read/grep and boilerplate work
   while I focused on the native FSM, build and runtime evidence.

## 10. Reproduction

```powershell
$env:PYTHONUTF8='1'
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l22 -- `
  py -3.12 -m experimental.pikmin2_otakara_runtime run `
    --assets "C:/Users/alari/bbft/dist/cohesion/pikmin/assets" `
    --imported "C:/Users/alari/pikmin-randomizer/output/dsw/l22-assets" `
    --output "C:/Users/alari/pikmin-randomizer/output/dsw/l22-runtime-repro" `
    --exe "C:/Users/alari/pikmin-randomizer/output/dsw/l22-fixture-fix1/fixture.exe" `
    --seconds 150
```
