# Honeywisp visual proxy handoff (#203)

Codex via assigned4laric. Source assets #196; umbrella #166. Native runtime pending.

The P1 counterpart is TEKI_Qurione=6 (`include/teki.h`), implemented by
`src/plugPikiNakata/taimizinko.cpp` and `include/TAI/Mizinko.h`. P2 source identity
Qurione16 stays distinct. The proposed proxy changes visuals only: health,
collision, movement, hit receivers, state sequencing and rewards remain P1.

## Explicit reward boundary

P1 `TaiMizinkoDropWaterAction::act` observes ACTION_0 and births
OBJTYPE_FallWater directly below the actor, storing creature pointer2. P2
`Qurione::attachItem` births a separate Egg captured by the water joint;
Drop state's damage animation key2 at frame5 releases it. These are different
ownership/lifecycle/reward mechanisms. The isolated module labels the actor
“Honeywisp (P1 nectar proxy)”; it does not create an Egg, execute source events,
add P2 receipts, or claim reward parity. No carryable-corpse port is implied.

## Install and arena

`experimental/pikmin2_qurione_install.py` requires an explicit expected SHA256 of
qurione.json, verifies source model/motion and every pose hash, validates exact
motion registration/events/frame endpoints and fixed safe model names, requires
identical material/texture resources across poses, enforces 512KiB/clip and 2MiB
bank budgets. Config bytes are LF-exact. Conflicting files/IDs are refused before
writes, and target model directory ancestors must be private, not junctions.

`experimental/pikmin2_qurione_arena.py` uses original Impact Site stage/map/routes
in private chal0 overlay. IDs203001/203002 represent proxy/control, respectively.
Full XYZ: (-150,30,1850) and (150,30,1550), offsets zero; no source yaw applied.
The template byte80 selects native family6. A documented private circle radius
50->0 override gives deterministic birth requests. Actual physics coordinates,
AI and rendering have not been checked. Empty-Pikmin tutorial behavior requires
the established legitimate fixture UI dismissal during runtime acceptance.

Actual source-ID audit:198 supported generator files checked, no collisions;
28 files do not match the existing records parser and remain unaudited globally.
The actual selected practice roster is checked again and rejects ID collisions.
Evidence: output/p2-qurione203/id-audit.json.

Staged original-map bundle:
output/p2-qurione203/arena/43ba780daa414a3d89d49b3a7266e4a7.
21 models /410592bytes. Source-bound install and preserved map hashes recorded
in arena.json; output/p2-qurione203/staging.json identifies the profile hash.

## Isolated native patch and root-owned hooks

output/p2-qurione203/native/qurione.patch adds pc_port/pc_p2_qurione.cpp,
pc_p2_qurione.h and pc_p2_qurione_policy.h. It is not applied to shared native.
The module preflights registrations and resource equality, reuses shared materials
within its bank, retains source-backed sampling bounds and registers only selected
TEKI_Qurione actors. Ordinary control actors return false from draw/name queries.
Absent bank+bindings returns before registration. Partial configs fail closed.

Root integration requests:

- Add pc_p2_qurione.cpp to PC CMake source list.
- Call setup after stage enemy births, alongside other family setup delegates.
- Call draw in the existing BTeki visual delegate chain; false falls through.
- Expose name in the existing identity delegate chain.
- Call reset at actual manager/stage reset, and forget after successful birth
  before initialization (slot reuse), alongside existing family hooks.
- Include the family in central conflict checks if new same-host registries arise.

Current registration type6 differs from Snow/Red/Sheargrub/Breadbug host types;
installer rejects explicit overlap with existing p2-*-actors configs, and native
also rejects existing Snow/Sheargrub names. No new gameplay/reward hooks requested.
Reset clears all registry and bank references; forget removes the one actor.
Actual same-address reuse/manager teardown are pending integrated runtime tests.

Native counter mapping (TAI/Mizinko state IDs): Going0/Coming2 +Wait1 ->waitl;
DropWater4 +Damage ->damage; FlyingAway5 +Dead ->run. HidingDest1,
HidingStart3 and Dead6 suppress model draw. Unexpected motion/state falls back to
ordinary native rendering. Source appear1/hide1 remain installed but unmapped;
there is no exact host motion equivalent. Phase follows native animator counter
and frame count, selecting nearest source sample; it does not retime host hits,
execute key events or provide continuous skeletal animation.

## Validation and limits

Seven Python tests pass (four installer +three importer). Standalone native policy
compile/run passes: state/motion/fallback/hidden mapping, malformed IDs, counter
clamp/NaN. Isolated full pc_p2_qurione.cpp translation-unit compile exits0 using
existing recipe defines/includes; compile.json/log preserve the command. No shared
build, link, source export, live player binary or save was modified.

Native display, natural AI/combat, nectar behavior, reset/reentry and mixed-scene
performance remain UNTESTED. Compilation and successful staging do not establish
those gates. Materials are approximate and native safety needs fresh integrated
render/lifecycle acceptance. Root owns integration and source-only commits.
