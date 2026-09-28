# Lane 30 (Snitchbugs/Demon) — reconcile candidate onto approved native baseline

Workstream F: replay the lane-30 candidate (`opencode/p2-lane30-final`, `ebba8495`) onto the
approved native baseline (`f14c6851`) and prove the combined tree builds and its standalone
gates pass.

## Provenance

- Approved native baseline: `f14c6851473ac1161be56c8b98f4f905232f3635`
  ("Keep Jellyfloat receiver collparts in stable registry storage (#456)"), a descendant of the
  pair root `origin/codex/p2-main-review` @ `3851d4b`.
- Candidate branch: `opencode/p2-lane30-final` @ `ebba8495f64a28f488d8e4267da39b8fb08ea7aa`,
  67 linear commits from base `2c08d6b8d6d085318f239c07297be0bb5c33dbdf`.
- Reconciled branch: `opencode/p2-lane30-rebase`, worktree `output/native-lane30-rebase`.
  Replayed with `git cherry-pick 2c08d6b8..ebba8495`.
- Reconciled implementation head (parent of this doc commit): `930744746918d3bc440ca7c211573eef2f03ed36`.
  66 lane-30 commits replayed; one (`3173a59a`) was already in the baseline and was skipped.

## Replayed commits (oldest → newest, rebased SHAs)

- `7b93ca59` Prototype dedicated PC Demon drop state and scoped native hooks
- `4c24a522` Document prototype limits and diagnose captain admission
- `8cec4830` Arrange Walk admission and test retained listener exhaustion
- `3857eaf1` Record registered state runtime gates and remaining ownership limits
- `1f6dc345` Reject unadmitted direct transitions into Demon drop state
- `fe2fe584` Record final nine-mode registered receiver validation
- `893891aa` Handle Demon drop state handoffs and revoke at production stage exit
- `da767958` Record fifteen-mode Demon lifecycle candidate validation
- `9e75a95b` Add private Demon live capture bridge
- `789f3f30` Add private rendered Demon capture host
- `a559cf68` Preserve full Demon mouth transforms in private host
- `4291816b` Load sampled Demon mouth bases from exported pose bank
- `f021c801` Exercise Demon pose-bank attachment in native fixture
- `ea7b86c6` Synchronize Demon captive with its exact live mouth joint
- `06259d4d` Record verified Demon full-pose runtime and remaining gates
- `cb389817` Select Demon mesh and mouth bases from one sampled pose bank
- `e5551fbd` Drive Demon attack poses and event decisions with retail player
- `babcac64` Exercise source-timed Demon attack events in runtime fixture
- `ad32f863` Drive Demon CatchFly and FallMeck host clock
- `475ae4aa` Move Demon clock transitions into host
- `bf64bc5d` Correct Demon transition clock and exercise timed capture cycle
- `20f01e81` Reconcile live capture ownership during Demon flight
- `066622ed` Guard failed Demon release and expose CatchFly ordering
- `f9e579bb` Wire CatchFly movement policy into host clock
- `3e3666ce` Use semantic CatchFly height outcomes and ownership
- `0859faeb` Expose semantic Demon height transition
- `5c70505c` Verify sustained Demon pursuit drive
- `ae7efcb9` Update Demon host motion on game frames
- `d66cf1a4` Feed evolving Demon position into pursuit
- `9f4c835e` Verify Demon pursuit heading over game frames
- `4e008a11` Add bounded CatchFly turning to host movement
- `4b32d39d` Correct Demon turn fixture inputs
- `edfdc48e` Exercise capped Demon turn convergence
- `039dc836` Add deterministic Demon CatchFly target selection
- `13ea11b5` Document deterministic Demon target scope
- `4bc7184a` Add deterministic CatchFly random target seam
- `dcb619dc` Add identity checked Demon actor binding seam
- `e8ea6a65` Harden Demon actor binding lifecycle
- `8383d531` Exercise Demon actor binding lifecycle
- `378a5a84` Make Demon binding fixture self-contained
- `eabf352c` Add opt-in Demon manager binding skeleton
- `03e3d1ca` Dispatch bound Demon hosts through manager seam
- `a7564f53` Clear Demon bindings with Teki manager lifecycle
- `56204bb6` Dispatch opt-in Demon hosts from game core
- `66337853` Dispatch bound Demon hosts per Teki actor
- `5809d30d` Add opt-in automatic Demon host setup
- `d45bb808` Run opt-in Demon setup after stage finalization
- `8c7c2768` Add automatic Demon binding fixture mode
- `282546b8` Add generated Demon identity discovery fixture
- `e2763f36` Assert automatic Demon host rendering
- `a1969971` Initialize and restore Demon render state
- `95e28f6d` Adopt centered 960x540 Demon fixture
- `6eaad4d0` Log Demon host fixture window geometry on the adopted baseline (#242)
- `20908d17` pc_port: live owner-mouth capture fixture for Demon host (#242)
- `82ba8e65` pc_port: natural Demon captor target/approach/admission policy (#242)
- `e4f142b0` pc_port: opt-in natural captor on the Demon host (#242)
- `2de313ff` tools: natural captor fixture mode and evidence doc (#242)
- `dd76f625` tools: pin natural captor evidence to committed head (#242)
- `7f255440` tools: natural captor escape/interrupt/teardown gates (#242)
- `b01167ec` tools: record natural captor escape/interrupt/teardown evidence (#242)
- `65cc438b` pc_port: ordinary spawned natural captor binding on the Demon manager (#242)
- `a658aae1` tools: ordinary spawned captor fixture mode (#242)
- `13bd1e15` tools: record ordinary spawned captor evidence (#242)
- `1b8612d8` species: Swooping Snitchbug (Sarai id 23) isolated source policy + audit (#166, lane 30)
- `752f8b10` species: Sarai flight FSM bridge composing the source policy (#166, lane 30)
- `93074474` species: Sarai getAttackableTarget geometry contract (#166, lane 30)

Skipped: original `3173a59a` "pc_port: open experimental-room windows small and centered by
default" — an empty pick because the baseline already carries the identical change
(`587ab6ae`, `9f179c88`). Work is preserved in the baseline, not lost.

## Resolved conflicts

The baseline already integrated lane-30's drop-state prototype through `#387` (`ae4747d4`); the
candidate's earlier commits therefore replayed as add/add or content conflicts. All conflicts were
resolved by keeping **both** baseline work and lane-30 work. Net effect of the whole replay versus
the baseline: 37 files changed, +3903/−3; no baseline file was deleted.

| Pick | File | Conflict | Resolution |
|---|---|---|---|
| `98049f45` | `CMakeLists.txt` | content | Baseline `PC_PORT_SOURCES` entries kept; lane-30 `pc_p2_demon_drop_state.cpp` already present. Later picks added `pc_p2_demon_escape_state.cpp`, `pc_p2_demon_bridge.cpp`, `pc_p2_demon_host.cpp` cleanly. |
| `98049f45` | `pc_port/pc_p2_demon_drop_state.h/.cpp` | add/add | Took lane-30 chain (baseline blob equals lane-30 final blob `1e2e12d4`/`9be5f6f8`); `beea4615` re-added the handoff/scene-exit hooks so the final tree matches the baseline. |
| `98049f45` | `src/plugPikiKando/navi.cpp` | content | Kept baseline (`pc_p2_mamuta_rules.h` include plus lane-30's demon include, `pc_demon_drop_reset`/`pc_demon_drop_post_physics` calls already present). |
| `98049f45` | `include/NaviState.h`, `src/plugPikiKando/naviState.cpp` | auto-merged | Clean union; final `NaviState.h` is the lane-30 superset (`DemonDrop=36`, `DemonEscape=37`, `Count` 38). |
| `98049f45` | `tools/p2_demon_registered_run.py`, `tools/p2_demon_registered_runtime.cpp` | add/add | Took lane-30 chain; baseline blob equals lane-30 final blob (`2c6ce032`/`dc2c50f1`). |
| `0507d0fc` | `tools/P2_DEMON_REGISTERED_STATE.md` | add/add | Took lane-30 chain; baseline blob equals lane-30 final blob (`8cb0208a`). |
| `beea4615` | `src/plugPikiKando/gameCoreSection.cpp` | content | Kept baseline (`pc_p2_kurage_teki.h`/`pc_p2_onikurage_teki.h` includes; `pc_demon_drop_scene_exit()` already present). |
| `1d6478b6` | `pc_port/pc_p2_motion_events.h`, `pc_port/pc_p2_retail_player.h` | add/add | Kept baseline; the only difference is baseline provenance comments (functional content identical). |
| `48023b42` | `src/plugPikiNakata/tekimgr.cpp` | content (4 hunks) | Manual union: baseline's full per-lane reset/forget lists retained and lane-30's `pc_p2_demon_manager_reset()`/`pc_p2_demon_manager_forget()` hooks added (include, `initTekiMgr`, `TekiMgr()`, `newTeki`, `reset`). |
| `56eb023a` | `src/plugPikiKando/gameCoreSection.cpp` | content | Union include: kept baseline `pc_p2_enemy.h` + lane-30 `pc_p2_demon_host.h`. |
| `e33bad0e` | `src/plugPikiKando/gameCoreSection.cpp` | content | Union include (same as above). |
| `e33bad0e` | `src/plugPikiNakata/tekibteki.cpp` | content (3 hunks) | Union: lane-30 `pc_p2_demon_manager_draw_actor`/`update_actor` prepended to the baseline draw/update chains (all baseline draws plus batch2/batch3/long_legs/kurage/onikurage/giant retained). |
| `dfa047b1` | `pc_port/pc_p2_preview.cpp` | content (2 hunks) | Union include and setup list (baseline `pc_p2_kurage_teki.h` + lane-30 `pc_p2_demon_host.h`; baseline setup calls + `pc_p2_demon_manager_setup()`). |
| `800b88c1` | `pc_port/pc_p2_preview.cpp` | content (2 hunks) | Followed lane-30: removed the preview-level demon include/setup (moved to game core) while retaining baseline's list. |
| `800b88c1` | `src/plugPikiKando/gameCoreSection.cpp` | content (2 hunks) | Union include; kept baseline `pc_p2_kurage_teki_setup()`/`pc_p2_onikurage_teki_setup()` and added `pc_p2_demon_manager_setup()` in `finalSetup()`. |

No unresolved conflict remains; `git grep` finds no conflict markers in tracked files.

## Private build evidence

- Build directory: `output/native-lane30-rebase-build` (private, ignored; `native/build-randomizer` untouched).
- Toolchain: MinGW-w64 GCC 16.2.0 (`C:/msys64/mingw64/bin`), Ninja 1.13.2 (Python-bundled).
- Configure: `cmake -S output/native-lane30-rebase -B output/native-lane30-rebase-build -G Ninja
  -DCMAKE_C_COMPILER=gcc -DCMAKE_CXX_COMPILER=g++ -DCMAKE_BUILD_TYPE=Release
  -DPIKMIN_NATIVE_JAUDIO=ON`.
- Build: `cmake --build output/native-lane30-rebase-build --target pikmin_pc -j 4` → PASS,
  `[547/547] Linking CXX executable bin\nectar.exe`.
- `bin\nectar.exe` SHA-256: `7DAA4FE0FB565969211E04E917A95B1B01A70A56D4014F2F472EA6A26ABC1BDF`
  (7,381,889 bytes).
- `ninja -n -C output/native-lane30-rebase-build pikmin_pc` → `ninja: no work to do.`

## Standalone gate tests (warning-clean)

Compiled with `g++ -std=gnu++17 -Wall -Wextra -Werror -I <worktree>/pc_port` and run; executables
deleted afterwards.

- `p2_demon_captor_test PASS`
- `p2_demon_escape_test PASS`
- `p2_demon_drop_policy_test PASS`
- `p2_demon_host_clock_test PASS`
- `p2_sarai_policy_test PASS checks=49`
- `p2_sarai_fsm_test PASS checks=37`

## Remaining gates / risks

- These are standalone policy/unit gates on the reconciled tree. No real-GL / input acceptance run
  was performed (another workstream holds the single GL slot); the natural captor, escape/interrupt/
  teardown and Sarai runtime evidence remain pinned to the worker executables, not this combined
  binary.
- Natural admission of Sarai/Demon through ordinary spawn, generated-session staging, revisit and
  process restart is not re-established here. Gates A–G from `PIKMIN2_NEXT_WAVE.md` remain open.
- The Demon drop state was reconstructed through the candidate chain and converges to the baseline
  blob; only the combined `pikmin_pc` link and the six standalone tests were verified.
- No native origin push, no main/upstream mutation, no other worktree change, and no edit to
  `native/build-randomizer`.
