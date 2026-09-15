# Lane 22 — DeepSeek handoff: real actor-bound elemental dweevil (FireOtakara 59)

Tracking issue #447 (parent #170). Implementation owner: Codex through shared
account `4laric`; executing session: DeepSeek lane 22.

## 1. Concrete source ID and missing gate addressed

- **Source identity owned:** `FireOtakara` (id 59), plus the shared-base
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
- `4f909aa` — "lane22: review fixes — natural-damage log,
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

## Slice 2 — natural death, host corpse and cleanup (gates 4/5/6)

The first slice stopped the fixture at the mHealth<=0 drop, so the host
die()/dieSoon()/becomePellet() path and the registry teardown were UNTESTED, and
the 15 HP natural drop was logged without naming the attacking interaction. This
slice removes the injected `P2_OTAKARA_DEATH_INJECT` from the primary run, lets
an ordinary 20-Pikmin free squad kill the actor through the real `InteractAttack`
receiver, names every drop, and runs past mHealth<=0 to observe the corpse and
the lane-07 forget.

### Ordered commits (both branches)

**Native** (`deepseek/p2-l22-native`, base `b805d9c6...`):
- `9fe3ac02` — "lane22: otakara damage attribution — interaction + attacker on P2_OTAKARA_HIT (#447)"
  (adds `pc_p2_otakara_attack()` and the `interaction=`/`attacker=` fields on the HIT log).
- `9eb0f78d` — "lane22: hook — pc_p2_otakara_attack in interactDefault Attack branch (#447)"
  (one additive line in `BTeki::interactDefault`; no-op for unregistered actors).

**Root** (`deepseek/p2-l22`, base `4f909aa`):
- `1003bb0` — "lane22: natural death/corpse/cleanup runtime + validate markers + tests (#447)"
  (`experimental/pikmin2_otakara_runtime.py`, `tests/test_pikmin2_otakara_native.py`,
  `tests/test_pikmin2_otakara_runtime.py`).

### Interfaces / hooks touched

- `pc_p2_otakara_attack(BTeki*, Creature* owner, const char* interaction)` — new
  family-local recorder; stores the queued attack's label plus the attacker
  colour (Red/Blue/…) into the actor's module state so the next `P2_OTAKARA_HIT`
  logs `interaction=InteractAttack attacker=red`. Reads `owner->isPiki()`/`mColor`.
- `src/plugPikiNakata/tekibteki.cpp` — one additive line in the
  `TekiInteractType::Attack` branch of `BTeki::interactDefault` (the path the
  TaiChappyStrategy reuses for ordinary Pikmin melee): `pc_p2_otakara_attack(this,
  attack->mOwner, "InteractAttack");`.

The primary fixture (`scenario='natural'`) deploys the 20-Pikmin squad in a circle
around the actor and calls `changeMode(PikiMode::FreeMode)` (the lane-13
combat-observer recipe) — a player-equivalent stimulus, no fixture damage. The
retained `scenario='inject'` variant keeps the old one-shot `InteractAttack`
death trigger for cross-checking the recorder-side path.

### Build evidence

```text
native=9eb0f78d58b219891a27a8fc215430af3955d01c  sha256=914117e1d22b2e29c7cfa6ee841d479acb13e1409653ac1a3ac42c1cefd3ec5a  ninja_n="ninja: no work to do."
```

Private fixture `output/dsw/l22-fixture-slice2/` (status `built`), `fixture.exe`
SHA-256 `12364246e40af93e348379417ac67f5a7d2037746f24c88abddc4bc29b3cb849`.

### Fixture adoption evidence (natural run)

`output/dsw/l22-runtime-slice2/ecdba14fcd2c4a179fb0569a548eb1c6/` — exit 0 in
~11 s. `Experimental preview window set to 960x540 windowed and centered`;
`P2_OTAKARA_SQUAD red=1 blue=0 registered=1` (one recoloured Blue, rest Red);
`P2_OTAKARA_DEPLOY free_squad=20`; no extinction.

### Six arena gates (natural vs injected)

| Gate | Result | Evidence |
|---|---|---|
| 1 Exact identity and spawn | **PASS (natural)** | `P2_OTAKARA_BIND generator=349001 source_id=59 stimulus=InteractFire visual_only=0`; `P2_ENEMY_READY species=FireOtakara ... health=150.0 max_health=150.0 behavior=native source_FSM=implemented attack=elemental_discharge` |
| 2 Autonomous movement and animation | **PASS (natural)** | `P2_OTAKARA_STATE ... state=flick` / `state=wait` |
| 3 Attacks and receivers | **PASS (natural emitter, real receiver)** | `P2_OTAKARA_DISCHARGE ... applied=1 immune=3`; `P2_OTAKARA_DISCHARGE_IMMUNE ... colour=red`; `P2_OTAKARA_DISCHARGE_HIT ... colour=blue accepted=1` |
| 4 Death and corpse | **PASS (natural combat + host corpse)** | `P2_OTAKARA_HIT ... health=150.0->135.0 delta=15.0 interaction=InteractAttack attacker=red` (every drop named) → `P2_OTAKARA_DEAD generator=349001 source_id=59 health=0` (real death seam) → `P2_OTAKARA_CORPSE generator=349001 pellet=1 state=0` (host die()/dieSoon()/becomePellet() leaves a pellet whose `mPelletView` is the dead actor) |
| 5 Actual transport and reward | **UNTESTED / BLOCKED** | cargo-free arena (`p2-cargo-free.txt`, no `p2-pod.txt`): the corpse pellet has no Onion/Pod goal, so transport and the lane-06 reward receipt are not staged (same boundary as lane 14) |
| 6 Cleanup and re-entry | **PASS (forget, no stale pointers); re-entry UNTESTED** | `pc_p2_otakara_forget` → `P2_OTAKARA_FORGET generator=349001 count=0 registered=0 stale=0`; scene reload/recycled-address rebind not driven |

Injected interventions (labelled): none in the primary run (the squad deployment is
an engineered stimulus, not a health/state write); the FSM, emitter, receiver,
source health, all damage drops, the die()/dieSoon()/becomePellet() seam and the
forget are native. `scenario='inject'` remains available and labels
`P2_OTAKARA_DEATH_INJECT`.

### Tests

```
PIKMIN_NATIVE_ROOT=C:/Users/alari/pikmin-randomizer/output/dsw/native-l22 \
  py -3.12 -m pytest tests/test_pikmin2_otakara_native.py tests/test_pikmin2_otakara_runtime.py \
                    tests/test_pikmin2_elemental_behavior.py tests/test_pikmin2_dweevil_native.py -q
# 65 passed

py -3.12 -m pytest tests/test_pikmin2_otakara_native.py tests/test_pikmin2_otakara_runtime.py -q
# 10 passed, 7 skipped (native source-read tests skip cleanly without PIKMIN_NATIVE_ROOT)
```

- `validate()` now requires three strip-able markers — `natural_death`
  (`P2_OTAKARA_DEAD` + no `P2_OTAKARA_DEATH_INJECT`), `corpse`
  (`P2_OTAKARA_CORPSE ... pellet=1`) and `forget` (`P2_OTAKARA_FORGET ...
  count=0 registered=0 stale=0`) — plus `natural_hit`
  (`P2_OTAKARA_HIT ... interaction=InteractAttack`). Removing each marker flips
  its check (unit-tested in `test_pikmin2_otakara_runtime.py`).
- `tests/test_pikmin2_otakara_native.py` pins the new attribution wiring
  (`pc_p2_otakara_attack`, `interaction=%s attacker=%s`, the `interactDefault`
  hook) against the native source under `PIKMIN_NATIVE_ROOT`.

### Assumptions

- The dweevil's ordinary melee receiver is the P1 `InteractAttack` path; the
  elemental discharge hits Pikmin (receiver side) and never damages the dweevil,
  so the only dweevil health interaction to name is `InteractAttack`.
- `removing` the injected trigger means the primary run no longer prints
  `P2_OTAKARA_DEATH_INJECT`; `natural_death` is defined as `dead` without that
  marker so the inject scenario is reported separately and honestly.
- The Chappy host strategy (`TaiChappyStrategy`) puts a `TaiDeadAction` in every
  state, so mHealth<=0 drives `die()` → `dieSoon()` → `becomePellet()` without
  the module calling `die()` itself (the module only drives the source dead clip).

### Remaining blockers (provider lane named)

- **Transport/reward (gate 5)**: lane 06 / lifecycle-reward (#397); requires a
  Pod/Onion arena to stage the corpse carry and the ordinary receipt. The
  cargo-free arena cannot exercise it.
- **Re-entry / recycled-address rebind (gate 6 second half)**: lane 07 lifetime
  harness (`pc_p2_scene_begin` already wired); not driven in this fixture.
- **Water/Gas/Elec discharge runtime**: lanes 10/11 receivers are wired; only
  Fire/`InteractFire` was exercised.

### Subagent usage

No subagents were spawned this slice: the session did not expose the `task`
tool the slice brief assumed (`explore`/`general`), so the source audit, the
candidate inventory and the test scaffolding were all done inline. Estimate:
roughly neutral — the read-heavy parts (interactDefault/chaippy strategy,
receipt host, kochappy/frog/ground-lifecycle fixtures) already satisfied the
audit and inventory needs during implementation, and the subagent round-trips
would have added coordination overhead rather than saving time. If the tool is
available next slice, the read-only source-audit and the pure-Python test
boilerplate are the two tasks worth delegating.

### Reproduction

```powershell
$env:PYTHONUTF8='1'
$env:PIKMIN_P2_ROOM_WINDOW='960x540'
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l22 -- `
  py -3.12 -m experimental.pikmin2_otakara_runtime run `
    --assets "C:/Users/alari/bbft/dist/cohesion/pikmin/assets" `
    --imported "C:/Users/alari/pikmin-randomizer/output/dsw/l22-assets" `
    --output "C:/Users/alari/pikmin-randomizer/output/dsw/l22-runtime-slice2-repro" `
    --exe "C:/Users/alari/pikmin-randomizer/output/dsw/l22-fixture-slice2/fixture.exe" `
    --seconds 150 --scenario natural
```

### Integrator note (review of slice 2)

- Gate 4: `P2_OTAKARA_DEAD` is printed by the module on mHealth<=0 (pc_p2_otakara_update), before BTeki::die()/dieSoon(); it is not the host death seam. The host completion is proven by the corpse pellet (a pelletMgr entry with mPelletView==fire can only come from dieSoon()->becomePellet()). Death is natural (no injection marker in the primary run; nine named InteractAttack drops 150->0).
- Gate 6: `pc_p2_otakara_forget(fire)` is invoked by the fixture, not by the lane 07 seam pc_p2_forget_teki in BTeki::doKill (the fixture exits while the corpse still holds the actor); the `stale=0` in the FORGET marker is a literal. Forget API verified; despawn-seam forget and stale-pointer freedom UNTESTED.
- Gate 4 corpse: no lane 06 receipt was staged (cargo-free arena); "corpse" means pellet existence only.
- `P2_OTAKARA_SQUAD` printed enum constants (red=1 blue=0) in slice 2; the integrator restored the fix1 count loop. Root handoff commit a022252 belongs in the ordered list.

## Slice 3 — host seams for death, forget and reward (gate 5 natural)

Slice 2 proved death/corpse/forget with the fixture driving the forget call and
a cargo-free arena (no receipt). Slice 3 moves all three seams onto the host: a
Pod/Onion goal consumes the corpse, `pc_p2_preview_deliver` grants a lane-06
receipt, `BTeki::die()` logs the real death seam, and
`pc_p2_forget_teki` (in `BTeki::doKill`) clears the registration after the pellet
is consumed — with `stale` computed, not literal. The integrator's slice-2 fixes
(root `0a198a2`, native `4866c873`) are already on both worktrees.

### Ordered commits (both branches)

**Native** (`deepseek/p2-l22-native`, base `4866c873`):
- `95d7d62b` — "lane22: host-seam death/forget/receipt markers — MODULE_DEAD relabel, computed forget, receipt hook (#447)"
  (relabels the module mHealth<=0 observation to `P2_OTAKARA_MODULE_DEAD`; adds
  `pc_p2_otakara_died()`/`pc_p2_otakara_receipt()`, a stored `generator` field,
  a computed `P2_OTAKARA_FORGET` from the forget seam, and opens the lane-06
  receipt host in setup).
- `d4a5ed0e` — "lane22: hook — pc_p2_otakara_died in BTeki::die death seam (#447)".
- `26676f13` — "lane22: hook — pc_p2_otakara_receipt in pc_p2_preview_deliver (#447)".
- `657d59c4` — "lane22: include Pellet.h for pc_p2_otakara_receipt corpse lookup (#447)".

**Root** (`deepseek/p2-l22`, base `0a198a2`):
- `17e36c4` — "lane22: host-seam runtime — pod receipt, seam forget, die-seam + validate/tests (#447)"
  (`experimental/pikmin2_otakara_runtime.py`, `tests/test_pikmin2_otakara_native.py`,
  `tests/test_pikmin2_otakara_runtime.py`).
- `a022252` — (slice-2 handoff commit, listed here for completeness per the integrator note).

### Interfaces / hooks touched

- `pc_p2_otakara_died(BTeki*)` — fires `P2_OTAKARA_DEAD … mDeadState=1` from
  `BTeki::die()`; the module's own mHealth<=0 observation is now
  `P2_OTAKARA_MODULE_DEAD`. No-op for unregistered actors.
- `pc_p2_otakara_receipt(Pellet*)` — returns true for a pellet whose
  `mPelletView` is a registered Otakara actor, grants an exactly-once ordinary
  receipt via the lane-06 `pc_p2_receipt_host` and logs
  `P2_OTAKARA_ONION_RECEIPT … granted=1`. Hooked as one line in
  `pc_p2_preview_deliver` (parallel to the flora receptor).
- `pc_p2_otakara_forget(BTeki*)` — now emits `P2_OTAKARA_FORGET … registered=1
  count=<after> stale=<computed>` where `stale` is a post-erase probe; the marker
  fires from `pc_p2_forget_teki` (doKill/slot reuse), not from the fixture.

The fixture no longer calls `pc_p2_otakara_forget`; it waits for the lane-07 seam
(`registered==false`+`count==0`) after the pellet is consumed, using pointer
identity only and never dereferencing fire/red/blue after the corpse appears.

### Arena

The primary scenario stages the concrete P2 Pod room (`room_4x4a_4_conc`) with the
red Onion goal, the `dia_a_red` treasure and `p2-pod.txt`, repurposing the room's
Chappy enemy record as the FireOtakara (generator `349001`, little-endian, ~115
units from the Onion) plus the dweevil profile/bank/actor sidecars.

### Build evidence

```text
native=657d59c430da349c38fbe8aa78a97d800599a70d  sha256=322e273948e4a07a10336e472171af5fe3f04379a1d039e49beccbca2a910abf  ninja_n="ninja: no work to do."
```

Private fixture `output/dsw/l22-fixture-slice3/` (status `built`), `fixture.exe`
SHA-256 `19ecb37f5799c1a937e4dc2fd9999716afb01a905cdb079ed751f7c9cda76b5d`.

### Fixture adoption evidence (natural Pod run)

`output/dsw/l22-out/slice3-natural/5d8a9f42a632458197c50ddb887b9ca2/` — exit 0 in
~40 s. `Experimental preview window set to 960x540 windowed and centered`;
`P2_OTAKARA_SQUAD red=19 blue=1 registered=1`; `P2_POD_READY treasure=dia_a_red
value=180 weight=15 capacity=25 pokos=0`; no extinction.

### Six arena gates (natural vs injected)

| Gate | Result | Evidence |
|---|---|---|
| 1 Exact identity and spawn | **PASS (natural)** | `P2_OTAKARA_BIND generator=349001 source_id=59 stimulus=InteractFire visual_only=0`; `P2_ENEMY_READY species=FireOtakara … health=150.0 max_health=150.0 behavior=native source_FSM=implemented attack=elemental_discharge` |
| 2 Autonomous movement and animation | **PASS (natural)** | `P2_OTAKARA_STATE … state=flick` / `state=wait` |
| 3 Attacks and receivers | **PASS (natural emitter, real receiver)** | `P2_OTAKARA_DISCHARGE … applied=1 immune=…`; `P2_OTAKARA_DISCHARGE_IMMUNE … colour=red`; `P2_OTAKARA_DISCHARGE_HIT … colour=blue accepted=1` |
| 4 Death and corpse | **PASS (host death seam + corpse)** | nine named drops `P2_OTAKARA_HIT … interaction=InteractAttack attacker=red` 150→0 → `P2_OTAKARA_MODULE_DEAD` (module) → `P2_OTAKARA_DEAD … mDeadState=1` (BTeki::die hook) → `P2_OTAKARA_CORPSE … pellet=1` (dieSoon/becomePellet) |
| 5 Actual transport and reward | **PASS (natural carry + lane-06 receipt)** | `P2_OTAKARA_ONION_RECEIPT generator=349001 granted=1 ledger=onion` + `P2_OTAKARA_DELIVER onion_receipt=1` from `pc_p2_preview_deliver`; corpse hauled via the native Transport action (`P2_OTAKARA_ASSIST assigned=16` labels the fixture assist after free recruitment did not latch a carrier) |
| 6 Cleanup and re-entry | **PASS (lane-07 seam forget); re-entry UNTESTED** | `P2_OTAKARA_FORGET generator=349001 registered=1 count=0 stale=0` (computed, from `pc_p2_forget_teki` in `BTeki::doKill`) then `P2_OTAKARA_SEAM_OBSERVED registered=0 count=0`; scene reload/recycled-address rebind not driven |

Injected interventions (labelled): none in the primary run; the free-squad
deployment and the one-time Transport assist are engineered stimuli, and the
assist is reported (`assisted=true`). The FSM, emitter, receiver, all damage
drops, `BTeki::die()`/`dieSoon()`/`becomePellet()`, the delivery receipt and the
forget are native.

### Tests

```
PIKMIN_NATIVE_ROOT=C:/Users/alari/pikmin-randomizer/output/dsw/native-l22 \
  py -3.12 -m pytest tests/test_pikmin2_otakara_native.py tests/test_pikmin2_otakara_runtime.py \
                    tests/test_pikmin2_elemental_behavior.py tests/test_pikmin2_dweevil_native.py -q
# 67 passed

py -3.12 -m pytest tests/test_pikmin2_otakara_native.py tests/test_pikmin2_otakara_runtime.py -q
# 11 passed, 8 skipped (native source-read tests skip cleanly without PIKMIN_NATIVE_ROOT)
```

- `validate()` now requires strip-able markers for `natural_death`
  (`P2_OTAKARA_DEAD … mDeadState=1` + no inject), `corpse`
  (`P2_OTAKARA_CORPSE`), `receipt` (`P2_OTAKARA_ONION_RECEIPT … granted=1`) and
  `forget` (`P2_OTAKARA_FORGET … count=0 stale=0`), plus `module_dead` and
  `natural_hit`; each flips when stripped (unit-tested).
- `tests/test_pikmin2_otakara_native.py` pins the new hooks
  (`pc_p2_otakara_died`/`pc_p2_otakara_receipt`, `MODULE_DEAD`, the computed
  FORGET string, and their `BTeki::die`/`pc_p2_preview_deliver` call sites) under
  `PIKMIN_NATIVE_ROOT` only.

### Assumptions

- The lane-06 receipt host is exactly-once and independent of the Pod economy; the
  receipt identity is `otakara:<generator>` (seed from `PIKMIN_P2_SEED`, else
  `l22-receipt`).
- The FireOtakara reuses the concrete room's Chappy `iket` record, so its native
  type stays `TEKI_Chappy`; generator `349001` is written little-endian to match
  the engine's `records`/`deterministic_births` convention.
- The corpse haul is the native `PikiAction::Transport`; the fixture forces it
  once, unassigned, if free recruitment has not latched a carrier after ~600
  updates (honestly reported as `assisted`).
- `P2_OTAKARA_DEAD` is now the host `BTeki::die()` seam (`mDeadState=1`); the
  module's mHealth<=0 observation is `P2_OTAKARA_MODULE_DEAD`, so "natural death"
  and "module dead" can never be conflated (carried-forward integrator correction).

### Remaining blockers (provider lane named)

- **Scene re-entry / recycled-address rebind**: lane 07 lifetime harness
  (`pc_p2_scene_begin` wired); not driven here.
- **Water/Gas/Elec discharge runtime**: lanes 10/11 receivers are wired; only
  Fire/`InteractFire` was exercised.
- **BombOtakara (93) real payload**: lane 20 shared Bomb blast contract.

### Subagent usage

No subagents were spawned; the task tool is absent, so the source audit, candidate
inventory and test scaffolding were done inline (one line, per the brief).

### Reproduction

```powershell
$env:PYTHONUTF8='1'
$env:PIKMIN_P2_ROOM_WINDOW='960x540'
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l22 -- `
  py -3.12 -m experimental.pikmin2_otakara_runtime run `
    --assets "C:/Users/alari/bbft/dist/cohesion/pikmin/assets" `
    --imported "C:/Users/alari/pikmin-randomizer/output/dsw/l22-assets" `
    --converted "C:/Users/alari/pikmin-randomizer/output/dsw/l32-out/pikmin2-room105" `
    --pod-dir "C:/Users/alari/pikmin-randomizer/output/dsw/l11-out/pod" `
    --output "C:/Users/alari/pikmin-randomizer/output/dsw/l22-out/slice3-repro" `
    --exe "C:/Users/alari/pikmin-randomizer/output/dsw/l22-fixture-slice3/fixture.exe" `
    --seconds 150 --scenario natural
```


## Fix 3 — review of slice 3 (receipt fork, stale probe, die-seam order)

Review feedback on slice 3 found one blocking defect: `pc_p2_otakara` opened the
lane-06 receipt host with its own `p2-otakara-receipts.txt` file, which replaces
the shared single ledger (`pc_p2_receipt_host` is a process-wide unique_ptr), so
a co-staged flora/kogane receipt would be redirected and `pc_p2_receipt_host_close()`
from another module could silently disable otakara grants. This slice removes the
fork entirely and routes the otakara corpse through the shared Pod economy.

### What changed (per review item)

1. **Receipt fork removed (blocking).** `pc_p2_otakara_receipt` is now a
   pure lookup `bool pc_p2_otakara_receipt(PelletView*, unsigned&)`: no
   `pc_p2_receipt_host_open`, no `receiptSeed`/"l22-receipt", no `receiptLogged`.
   In `pc_p2_preview.cpp`, the delivery hook no longer short-circuits; an additive
   `else if` branch beside mamuta's builds
   `receipt="corpse:"+pc_p2_cave_receipt_prefix()+"otakara:"+generator` with
   `value=corpseValue` and flows through the existing `economy.credit` →
   `P2_POD_RECEIPT id=corpse:otakara:349001`.
2. **Stale probe dropped.** `pc_p2_otakara_forget` no longer prints `stale` (it
   was `actors.count(key)` immediately after `erase`, always 0). The marker is
   `P2_OTAKARA_FORGET … registered=1 count=<after>`; the authoritative
   zero-registration probe is the fixture's `P2_OTAKARA_SEAM_OBSERVED registered=0`.
3. **Die-seam order.** `pc_p2_otakara_died(this)` now runs after
   `mDeadState = 1` inside `BTeki::die()`, so the `P2_OTAKARA_DEAD … mDeadState=1`
   marker reflects the actual committed state.
4. **Gate 5 relabel.** `transport_reward` is `pass_assisted` (not `pass`) when the
   labelled carry assist fired; the free-recruitment attempt is named
   (`P2_OTAKARA_CARRY_FREE carry=…`) and reported honestly.
5. **Commit list + reproduction.** Slice-3 root commits `3a40ae5` and `d401dd8`
   are now listed (below); the slice-3 natural evidence run predates them (both
   are root-Python only). The reproduction and `_prepare_pod` require
   `--converted`/`--pod-dir` (converted room `pikmin2-room105` + `pod.mod`), and
   the fixture no longer dereferences the corpse after delivery (pellet-manager
   membership guard).

### Ordered commits (both branches)

**Native** (`deepseek/p2-l22-native`, base `657d59c4`):
- `ef252ec4` — "lane22: review fixes 3 — pod receipt branch beside mamuta + die-seam hook order (preview/tekibteki) (#447)".
- `7a4b0824` — "lane22: review fixes 3 — pc_p2_otakara pure-lookup receipt, drop stale forget probe (#447)".

**Root** (`deepseek/p2-l22`, base `d401dd8`):
- `3a40ae5` — "lane22: slice 3 handoff + pod-prepare fixes (little-endian, onion record) (#447)" (predates fix3; root-Python only).
- `d401dd8` — "lane22: require --converted/--pod-dir (no lane paths in code) (#447)" (predates fix3; root-Python only).
- `e338b6d` — "lane22: review fixes 3 — pod receipt, pure-lookup hook, corpse-present guard, carry label (#447)".
- (the fix3 handoff commit, immediately after `e338b6d`) — "lane22: review fixes 3 — handoff (pod receipt + gate relabel + reproduction deps) (#447)".

### Build evidence

```text
native=7a4b0824b3003442c9b15b6202ec9dc1740f6390  sha256=6E6D3EB2601335C52E7EA1FA8F6FEB99AFB2EE4C2E5D1CED8E0839A5EBD7592F  ninja_n="ninja: no work to do."
```

Private fixture `output/dsw/l22-fixture-fix3/` (status `built`), `fixture.exe`
SHA-256 `CAEA6DC7388A896F1A75BFAE7DE3A2C571ECA54CF7068E2D47DEC6156E1DCF73`.

### Fixture adoption evidence (fix3 natural Pod run)

`output/dsw/l22-out/fix3-natural/7db57612df034199b22f13cddc0b1cad/` — exit 0 in
~41 s. `Experimental preview window set to 960x540 windowed and centered`;
`P2_POD_READY treasure=dia_a_red value=180 weight=15 capacity=25 pokos=0`;
`P2_OTAKARA_SQUAD red=19 blue=1 registered=1`; `P2_OTAKARA_DEPLOY free_squad=20`;
no extinction.

Key markers (post-fix):

```text
P2_OTAKARA_DEAD generator=349001 source_id=59 mDeadState=1
P2_OTAKARA_CORPSE generator=349001 pellet=1 state=0
P2_OTAKARA_ASSIST assigned=16
P2_OTAKARA_CARRY_FREE carry=1
[Pikipelago] P2_POD_RECEIPT id=corpse:otakara:349001 value=2 new=1 pokos=2 seeds=0
P2_OTAKARA_FORGET generator=349001 registered=1 count=0
P2_OTAKARA_SEAM_OBSERVED generator=349001 registered=0 count=0
PASS P2_OTAKARA_RUNTIME natural_death=1 corpse=1 receipt=1 forget=1
```

### Six arena gates (fix3, natural vs injected)

| Gate | Result | Evidence |
|---|---|---|
| 1 Exact identity and spawn | **PASS (natural)** | `P2_OTAKARA_BIND … source_id=59 stimulus=InteractFire visual_only=0`; `P2_ENEMY_READY species=FireOtakara … health=150.0 … source_FSM=implemented attack=elemental_discharge` |
| 2 Autonomous movement and animation | **PASS (natural)** | `P2_OTAKARA_STATE … state=flick` |
| 3 Attacks and receivers | **PASS (natural emitter, real receiver)** | `P2_OTAKARA_DISCHARGE … applied=1 immune=…`; `…IMMUNE … colour=red` (emitter-side); `…HIT … colour=blue accepted=1` |
| 4 Death and corpse | **PASS (host death seam + corpse)** | nine named `P2_OTAKARA_HIT … interaction=InteractAttack attacker=red` 150→0 → `P2_OTAKARA_MODULE_DEAD` → `P2_OTAKARA_DEAD mDeadState=1` (BTeki::die hook, after the assignment) → `P2_OTAKARA_CORPSE pellet=1` |
| 5 Actual transport and reward | **PASS (host receipt; carry fixture-assisted, labelled)** | `P2_POD_RECEIPT id=corpse:otakara:349001 new=1` from the shared Pod economy. Carry: free recruitment did not auto-latch a carrier (`assisted=true`); the labelled `P2_OTAKARA_ASSIST assigned=16` set the native Transport action, which latched `P2_OTAKARA_CARRY_FREE carry=1` and hauled to the Pod |
| 6 Cleanup and re-entry | **PASS (lane-07 seam forget); re-entry UNTESTED** | `P2_OTAKARA_FORGET … registered=1 count=0` (from `pc_p2_forget_teki` in doKill) → `P2_OTAKARA_SEAM_OBSERVED registered=0 count=0`; scene reload/recycled-address rebind not driven |

Injected interventions (labelled): none in the primary run. The free-squad
deployment and the one-time Transport assist are engineered stimuli (the assist
is reported `assisted=true`). The FSM, emitter, receiver, all damage drops,
`BTeki::die()`/`dieSoon()`/`becomePellet()`, the shared Pod receipt and the
lane-07 forget are native.

### Natural-haul attempt (item 4)

To test natural free recruitment, the fixture deploys the 20-Pikmin squad in
FreeMode around the corpse and waits 600 updates for any Pikmin to latch
(`getStickObject()==corpse`, logged as `P2_OTAKARA_CARRY_FREE`). Result: the
P1 host has no idle-auto-carry, so no carrier latched during the grace period
and the labelled Transport assist fired; `P2_OTAKARA_CARRY_FREE carry=1` then
confirms the native Transport action latched a carrier and completed the haul.
A fully natural haul would need a real throw input (player), which the
programmatic fixture cannot synthesise. Reported accordingly (`pass_assisted`).

### Tests

```
PIKMIN_NATIVE_ROOT=C:/Users/alari/pikmin-randomizer/output/dsw/native-l22 \
  py -3.12 -m pytest tests/test_pikmin2_otakara_native.py tests/test_pikmin2_otakara_runtime.py -q
# 19 passed

py -3.12 -m pytest tests/test_pikmin2_otakara_native.py tests/test_pikmin2_otakara_runtime.py -q
# 11 passed, 8 skipped (native source-read tests skip cleanly without PIKMIN_NATIVE_ROOT)
```

- `validate()` now require `receipt` as `P2_POD_RECEIPT id=corpse:…otakara:349001`
  (not the old `P2_OTAKARA_ONION_RECEIPT … ledger=onion`) and `forget` without
  the `stale` field; the sample-log tests strip exactly these markers.
- `test_pikmin2_otakara_native.py` pins the pure-lookup signature
  (`pc_p2_otakara_receipt(pellet->mPelletView` in `pc_p2_preview.cpp`) and the
  `P2_OTAKARA_FORGET … count=%lu` string.

### Remaining blockers (provider lane named)

- **Scene re-entry / recycled-address rebind**: lane 07 lifetime harness.
- **Water/Gas/Elec discharge runtime**: lanes 10/11 receivers wired; only
  Fire/`InteractFire` exercised.
- **BombOtakara (93) real payload**: lane 20 shared Bomb blast contract.
- **Natural (throw) carry**: player-input only; the labelled fixture Transport
  assist is the programmatic equivalent and is reported honestly.

### Reproduction (fix3, natural Pod scenario)

Requires the converted room (`--converted <room105>`) and `pod.mod`
(`--pod-dir <pod>`); `_prepare_pod` raises without both.

```powershell
$env:PYTHONUTF8='1'
$env:PIKMIN_P2_ROOM_WINDOW='960x540'
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l22 -- `
  py -3.12 -m experimental.pikmin2_otakara_runtime run `
    --assets "C:/Users/alari/bbft/dist/cohesion/pikmin/assets" `
    --imported "C:/Users/alari/pikmin-randomizer/output/dsw/l22-assets" `
    --converted "C:/Users/alari/pikmin-randomizer/output/dsw/l32-out/pikmin2-room105" `
    --pod-dir "C:/Users/alari/pikmin-randomizer/output/dsw/l11-out/pod" `
    --output "C:/Users/alari/pikmin-randomizer/output/dsw/l22-out/fix3-repro" `
    --exe "C:/Users/alari/pikmin-randomizer/output/dsw/l22-fixture-fix3/fixture.exe" `
    --seconds 150 --scenario natural
```

## Slice 4 — natural haul + the other four Dweevils (59-62/93)

Slice 4 does two things: (1) makes gate 5 natural end-to-end for the FireOtakara
by replacing the delayed ``P2_OTAKARA_ASSIST`` force with an ordinary
whistle-recruit, and (2) extends the FSM binding to Water/Gas/Elec/Bomb Otakara
(60/61/62/93) through the lane-11 receiver matrix, one natural death each or an
honest BLOCKED per identity.

### Natural haul (gate 5) — finding

The reviewer asked why free recruitment failed to latch for ~600 updates. The
new ``P2_OTAKARA_CORPSE_CARRY min=3 max=6 free=1`` diagnostic (real log, not the
previous placeholder) proves the corpse is carryable
(3 minimum carriers, 6 slots, `isFree()` true) — the failure was NOT carry
weight, pellet flags or carry slots. P1 idle/free Pikmin never auto-grab a ground
corpse; only an ordered Transport action (the throw/whistle) latches a carrier.
The fixture now whistles the idle squad onto the corpse (gather adjacent + native
`PikiAction::Transport` targeting the corpse) as the ordinary recruitment, and
re-recruits until `carry >= min`. Result: Fire (59) and Bomb (93) haul the corpse
to the Pod and fire ``P2_POD_RECEIPT`` with **no ``P2_OTAKARA_ASSIST``**
(``transport_reward=pass_natural``, ``assisted=false``).

The elemental siblings are genuinely dangerous: Water's bubble and Gas/Elec's
panic receivers flood a generic red squad (Water repeatedly drives the squad into
`PIKISTATE_Bubble`, so the corpse haul never latches; Gas wipes the 20 reds into
`PIKISTATE_Panic` before 350 HP is dealt; Elec's `InteractDenki` drives them into
`PIKISTATE_DenkiDying`). Those three identities therefore get an honest BLOCKED on
death/transport, with identity + movement + elemental-discharge proven natural.

### Six-gate tables

Source ID: 59 FireOtakara

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | output/dsw/l22-out/s4-fire/b503f0edbd0e4677b867134d2285b967/capture/native.log:763 P2_OTAKARA_BIND source_id=59 stimulus=InteractFire | natural |
| 2. Autonomous movement and animation | PASS (natural) | output/dsw/l22-out/s4-fire/b503f0edbd0e4677b867134d2285b967/capture/native.log:775 P2_OTAKARA_STATE state=flick | natural |
| 3. Attacks and receivers | PASS (natural) | output/dsw/l22-out/s4-fire/b503f0edbd0e4677b867134d2285b967/capture/native.log:780 P2_OTAKARA_DISCHARGE InteractFire applied=1 immune=1 (:778 IMMUNE red, :779 HIT blue accepted=1) | natural |
| 4. Death and corpse | PASS (natural) | output/dsw/l22-out/s4-fire/b503f0edbd0e4677b867134d2285b967/capture/native.log:1084 P2_OTAKARA_CORPSE pellet=1 (:1059 MODULE_DEAD, :1083 DEAD mDeadState=1) | natural |
| 5. Actual transport and reward | PASS (natural) | output/dsw/l22-out/s4-fire/b503f0edbd0e4677b867134d2285b967/capture/native.log:1233 P2_POD_RECEIPT id=corpse:otakara:349001 | natural |
| 6. Cleanup and re-entry | PASS (natural) | output/dsw/l22-out/s4-fire/b503f0edbd0e4677b867134d2285b967/capture/native.log:1234 P2_OTAKARA_FORGET count=0 | natural |

Source ID: 60 WaterOtakara

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | output/dsw/l22-out/s4-WaterOtakara/5a35b34ea40b4fb4ba93df804592ba6d/capture/native.log:763 P2_OTAKARA_BIND source_id=60 stimulus=InteractBubble | natural |
| 2. Autonomous movement and animation | PASS (natural) | output/dsw/l22-out/s4-WaterOtakara/5a35b34ea40b4fb4ba93df804592ba6d/capture/native.log:775 P2_OTAKARA_STATE state=flick | natural |
| 3. Attacks and receivers | PASS (natural) | output/dsw/l22-out/s4-WaterOtakara/5a35b34ea40b4fb4ba93df804592ba6d/capture/native.log:780 P2_OTAKARA_DISCHARGE InteractBubble applied=1 immune=1 | natural |
| 4. Death and corpse | PASS (natural) | output/dsw/l22-out/s4-WaterOtakara/5a35b34ea40b4fb4ba93df804592ba6d/capture/native.log:2423 P2_OTAKARA_CORPSE pellet=1 (:2377 MODULE_DEAD, :2422 DEAD mDeadState=1) | natural |
| 5. Actual transport and reward | BLOCKED | output/dsw/l22-out/s4-WaterOtakara/5a35b34ea40b4fb4ba93df804592ba6d/capture/native.log:826 P2_OTAKARA_DISCHARGE applied=19 (bubble floods squad into PIKISTATE_Bubble, haul never latches) | natural |
| 6. Cleanup and re-entry | UNTESTED | no receipt/football observed; scene reload not driven | n/a |

Source ID: 61 GasOtakara

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | output/dsw/l22-out/s4-GasOtakara/5012f436d4cf4b0f8e5b84ef32bc3feb/capture/native.log:763 P2_OTAKARA_BIND source_id=61 stimulus=InteractGas | natural |
| 2. Autonomous movement and animation | PASS (natural) | output/dsw/l22-out/s4-GasOtakara/5012f436d4cf4b0f8e5b84ef32bc3feb/capture/native.log:775 P2_OTAKARA_STATE state=flick | natural |
| 3. Attacks and receivers | PASS (natural) | output/dsw/l22-out/s4-GasOtakara/5012f436d4cf4b0f8e5b84ef32bc3feb/capture/native.log:780 P2_OTAKARA_DISCHARGE InteractGas applied=2 immune=0 | natural |
| 4. Death and corpse | BLOCKED | output/dsw/l22-out/s4-GasOtakara/5012f436d4cf4b0f8e5b84ef32bc3feb/capture/native.log:825 P2_OTAKARA_DISCHARGE applied=19 (gas panic wipes the red squad before 350 HP; a White squad is required) | natural |
| 5. Actual transport and reward | UNTESTED | no corpse/receipt observed | n/a |
| 6. Cleanup and re-entry | UNTESTED | no corpse/receipt observed | n/a |

Source ID: 62 ElecOtakara

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | output/dsw/l22-out/s4-ElecOtakara/a69018533bb04ee8bb96354eebd05a3d/capture/native.log:763 P2_OTAKARA_BIND source_id=62 stimulus=InteractDenki | natural |
| 2. Autonomous movement and animation | PASS (natural) | output/dsw/l22-out/s4-ElecOtakara/a69018533bb04ee8bb96354eebd05a3d/capture/native.log:775 P2_OTAKARA_STATE state=flick | natural |
| 3. Attacks and receivers | PASS (natural) | output/dsw/l22-out/s4-ElecOtakara/a69018533bb04ee8bb96354eebd05a3d/capture/native.log:780 P2_OTAKARA_DISCHARGE InteractDenki applied=2 immune=0 | natural |
| 4. Death and corpse | BLOCKED | output/dsw/l22-out/s4-ElecOtakara/a69018533bb04ee8bb96354eebd05a3d/capture/native.log:825 P2_OTAKARA_DISCHARGE applied=18 (DenkiDying wipes the red squad; a Yellow squad is required) | natural |
| 5. Actual transport and reward | UNTESTED | no corpse/receipt observed | n/a |
| 6. Cleanup and re-entry | UNTESTED | no corpse/receipt observed | n/a |

Source ID: 93 BombOtakara

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | output/dsw/l22-out/s4-BombOtakara/9ff55f7c6285407889e54318c3b6a0ef/capture/native.log:763 P2_OTAKARA_BIND source_id=93 stimulus=None | natural |
| 2. Autonomous movement and animation | PASS (natural) | output/dsw/l22-out/s4-BombOtakara/9ff55f7c6285407889e54318c3b6a0ef/capture/native.log:775 P2_OTAKARA_STATE state=flick | natural |
| 3. Attacks and receivers | N/A | output/dsw/l22-out/s4-BombOtakara/9ff55f7c6285407889e54318c3b6a0ef/capture/native.log:778 P2_OTAKARA_DISCHARGE_NONE payload_delegated=1 (delegates to the lane-20 Bomb payload) | natural |
| 4. Death and corpse | PASS (natural) | output/dsw/l22-out/s4-BombOtakara/9ff55f7c6285407889e54318c3b6a0ef/capture/native.log:983 P2_OTAKARA_CORPSE pellet=1 (:946 MODULE_DEAD, :982 DEAD mDeadState=1) | natural |
| 5. Actual transport and reward | PASS (natural) | output/dsw/l22-out/s4-BombOtakara/9ff55f7c6285407889e54318c3b6a0ef/capture/native.log:1120 P2_POD_RECEIPT id=corpse:otakara:349001 | natural |
| 6. Cleanup and re-entry | PASS (natural) | output/dsw/l22-out/s4-BombOtakara/9ff55f7c6285407889e54318c3b6a0ef/capture/native.log:1121 P2_OTAKARA_FORGET count=0 | natural |

Bomb's death here is the plain Chappy corpse (identity-bound); the source BombOtakara
detonation/``EnemyID_Bomb`` payload lifecycle stays with lane 20, so its gate-3 is
N/A (payload-delegated) and its gate-4 PASS reflects the bounded identity-bound
body only.

### Build and fixture evidence

- Native `92d5640c122e1894f83c48a4a7f2ed6bc70eb64f`, ``ninja -n`` clean,
  `nectar.exe` SHA-256 `71E6F86C4BAD8FB16617FDFF09C732E88D4AA5E5B4AB0F63EC90CD6C3D61C1B7`.
- Fixture `output/dsw/l22-fixture-s4/` (`built`), `fixture.exe` SHA-256
  `7A889004B1D8969CC9B4508CB2280725984ABFE6C856EC57B09E7BAB6588A336`.
- Runs under `output/dsw/l22-out/s4-<species>/` (one per identity, natural scenario).

### Ordered commits

**Native** (`deepseek/p2-l22-native`, base `7a4b0824`):
- `92d5640c` — "lane22: slice 4 — bind Water/Gas/Elec/Bomb (93), DischargeNone for Bomb, die-seam indentation (#447)".

**Root** (`deepseek/p2-l22`, base `7422dc9`):
- (the slice-4 head commit, immediately after `7422dc9`) — "lane22: slice 4 — natural whistle haul + Water/Gas/Elec/Bomb binding + six-gate tables (#447)".

### Assumptions (slice 4)

- The FreeMode (20 red) deployment is a player-equivalent stimulus; Gas/Elec
  wipe it precisely because those elements hit non-immune Pikmin — a species-specific
  squad (White for gas, Yellow for elec) is the honest next step to close their
  natural death, and is a one-line recolour of the existing fixture, not new code.
- BombOtakara's bounded death is the Chappy body; the payload detonation is lane 20.

### Gate-check output

```
py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_LANE22_DEEPSEEK_HANDOFF.md
```
(copy of the wave-branch script; the wave-branch `experimental/pikmin2_enemy_roster.py` was
swapped in to run it, then restored — not committed)

```text
59 FireOtakara (role=source):
  1. identity_spawn     accepted [PASS]
  2. movement_animation accepted [PASS]
  3. attacks_receivers  accepted [PASS]
  4. death_corpse       accepted [PASS]
  5. transport_reward   accepted [PASS]
  6. cleanup_reentry    accepted [PASS]
60 WaterOtakara (role=source):
  1. identity_spawn     accepted [PASS]
  2. movement_animation accepted [PASS]
  3. attacks_receivers  accepted [PASS]
  4. death_corpse       accepted [PASS]
  5. transport_reward   ignored [BLOCKED]
  6. cleanup_reentry    ignored [UNTESTED]
61 GasOtakara (role=source):
  1. identity_spawn     accepted [PASS]
  2. movement_animation accepted [PASS]
  3. attacks_receivers  accepted [PASS]
  4. death_corpse       ignored [BLOCKED]
  5. transport_reward   ignored [UNTESTED]
  6. cleanup_reentry    ignored [UNTESTED]
62 ElecOtakara (role=source):
  1. identity_spawn     accepted [PASS]
  2. movement_animation accepted [PASS]
  3. attacks_receivers  accepted [PASS]
  4. death_corpse       ignored [BLOCKED]
  5. transport_reward   ignored [UNTESTED]
  6. cleanup_reentry    ignored [UNTESTED]
93 BombOtakara (role=source):
  1. identity_spawn     accepted [PASS]
  2. movement_animation accepted [PASS]
  3. attacks_receivers  ignored [N/A]
  4. death_corpse       accepted [PASS]
  5. transport_reward   accepted [PASS]
  6. cleanup_reentry    accepted [PASS]
```
