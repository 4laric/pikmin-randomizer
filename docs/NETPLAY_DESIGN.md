# Online Co-op with Rollback Netcode: Feasibility and Architecture

> **Status (2026-09-27).** Tracking: [#876](https://github.com/4laric/pikmin-randomizer/issues/876). M0: [#877](https://github.com/4laric/pikmin-randomizer/issues/877). M1: [#878](https://github.com/4laric/pikmin-randomizer/issues/878).
>
> The owner answered open questions 1–3 (§5):
>
> 1. **Base line.** Netplay builds on the upstream 0.9 co-op merge line: native `claude/p2-final-v2-native` @ `20edccdc8`, which contains `6f3602445`.
> 2. **Staging.** Lockstep ships first (M0–M5). Rollback (M6–M8) is gated on the measurements from the M6a spike.
> 3. **View model.** Each peer sees its own captain, full screen. This requires the two-pass frame and sending camera yaw as input.
>
> Questions 4–11 are still open. This document is the feasibility study as delivered. Its `N/` line numbers refer to a95040b66, so re-find each site by symbol on the netplay branch.

**Path prefixes.** `N/` is `C:/Users/alari/pikmin-randomizer/native` at a95040b66 unless a commit is named. `U/` is `C:/Users/alari/pikmin-randomizer/output/netplay-upstream-main` (bb8ba817). `R/` is the repo root.

**Evidence tags.**
- **[V]**: verified in source by an investigator.
- **[V*]**: I re-checked it during this synthesis.
- **[M]**: measured, by a scratch microbenchmark or a toy harness, not in-game.
- **[I]**: inferred.

**What I re-checked myself:**
- The 6f3602445 merge: its parents, the branches that contain it, that no remote branch contains it, and that a95040b66 is not an ancestor of 20edccdc8.
- In `N/src/sysDolphin/system.cpp:314-468`: one `app->idle()` per loop iteration, the hold/freeze path, and the wall-clock `updateSysClock`.
- The world tick inside draw, at `N/src/plugPikiColin/newPikiGame.cpp:2251-2268`.
- `calcJointWorldPos` multiplying by `mInverseLookAtMtx` (`N/src/sysCommon/shapeBase.cpp:3543-3553`). Animation matrices are built from `gfx.mCamera->mLookAtMtx · mWorldMtx` (`viewPiki.cpp:601`, `navi.cpp:2404`, `tekibteki.cpp:2002`).
- Animation advancing in `updateAnim` during draw (`shapeBase.cpp:3332-3351`).
- The culling early-return (`creature.cpp:661`).
- `getRand → rand()` (`include/system.h:209`).
- The maintained build's CMakeCache: `PIKMIN_NATIVE_OPTIMIZE=OFF`, `PIKMIN_NATIVE_JAUDIO=ON`, Release.
- The sim's only camera reads in our fork (see §2b).
- `kPcTickWorldSim` exists upstream (`U/src/plugPikiColin/newPikiGame.cpp:2483`) but not in our fork.

---

## 1. Verdict

**Rollback is feasible. Nothing in the engine rules it out.** But the port has none of the properties rollback needs, and building them is a program of several months. The critical path runs through the simulation/render coupling, not the netcode library.

The right first product is **delay-based lockstep online co-op**. It needs every determinism fix but no snapshot/restore and no resimulation. Rollback is then an incremental upgrade on the same library (GekkoNet: `input_prediction_window = 0` is lockstep, raising it is rollback). Whether to do that upgrade should depend on two numbers nobody has measured yet: the cost of a headless sim tick, and the dirty-page set per tick.

### Hard blockers and their resolutions

| # | Blocker | Evidence | Resolution | Lockstep | Rollback |
|---|---|---|---|---|---|
| B1 | **The simulation runs inside render, and render writes simulation state based on the camera.** The world clock, `Node::update` and `updateAI` run after `BaseGameSection::draw` inside `NewPikiGameSection::draw`. Collision-part centres go through view-space animation matrices times the inverse lookAt. AI-culling flags come from a frustum built with the local window's aspect. Animation advances inside `updateAnim`. | [V*] `N/src/plugPikiColin/newPikiGame.cpp:2251-2268`; [V*] `N/src/sysCommon/shapeBase.cpp:3543-3553`; `N/src/plugPikiKando/collInfo.cpp:418-430`; `N/src/sysCommon/camera.cpp:314-328`; [V*] `N/src/plugPikiKando/creature.cpp:661` | A **two-pass frame** (§2b): an authoritative pass with a null GX backend and an identity "sim camera", plus a netplay culling policy; then a presentation pass with the local camera in the existing Presentation phase. The camera itself stops being sim state: each player's **control yaw is sent as input**. | Yes: each peer draws a different camera | Yes |
| B2 | **Time comes from the wall clock.** `mDeltaTime` is an OSGetTick delta capped at 1/30. The loop runs one idle per iteration. There are local freezes (foreground loss, randomizer staleness) and wall-clock sim timers. | [V*] `N/src/sysDolphin/system.cpp:315-325, 343-358, 456-468`; `N/src/plugPikiKando/naviState.cpp:1696`; `N/pc_port/pc_p2_purple_feedback.cpp:97`; `N/pc_port/pc_randomizer.cpp:348` | Fixed dt of 1/30 in netplay. The netplay driver owns ticks. Freezes become synchronized events. Timers count frames. | Yes | Yes |
| B3 | **The RNG is msvcrt `rand()`.** Its state is per-thread inside the DLL, so it cannot be snapshotted. It is never seeded, and menus and draw code consume it. | [V*] `N/include/system.h:209-210`; `N/include/BaseApp.h:36`; `N/src/plugPikiKando/itemAI.cpp:755`; objdump import (two investigators) | Put a PRNG inside the exe, seeded per day or stage from the session seed. Draw-only consumers get a cosmetic stream. | Yes: menu dwell time desyncs the stream | Yes |
| B4 | **Snapshot of a heap scattered across malloc.** Every `new` goes to msvcrt malloc: about 83k blocks, about 18 MB live. libstdc++ is a DLL, so `std::string` allocations bypass our allocator. P2 maps are keyed by pointer. | [V] `N/src/sysDolphin/sysNew.cpp:104-213`; exit dump (state-snapshot); 8.7M "unknown frees" | A fixed-address sim region with a deterministic allocator, a write-watch undo ring, the globals bracket, and a statically linked libstdc++ (§2c). | No | Yes |
| B5 | **Randomizer/AP I/O cannot be undone, and its inputs arrive asynchronously.** `state.txt` is polled by mtime at the top of the loop. Checks, deaths and Emperor are fsynced from inside ticks. A check reads back into the sim through `reconcileBbftParts` and kills the carried pellet. | [V] `N/pc_port/pc_randomizer.cpp:342-437, 534-616`; `N/src/plugPikiKando/playerState.cpp:302-357`; `N/src/plugPikiKando/pelletMgr.cpp:1171-1177` | The host is authoritative. External state travels as a stream inside the host's input. A confirmed-frame outbox that only the host flushes (§2g). | Yes (host-only, frame-stamped) | Yes (plus discard on rollback) |
| B6 | **Inputs bypass `PADStatus`**: mouse delta and virtual cursor, wheel, lock-on/charge edges, free-camera drag, F-keys, photo mode, the movie-skip latch. Upstream co-op triples these, including `mNaviID == keyboard_owner` checks in sim code. | [V] `N/src/plugPikiKando/navi.cpp:725, 1975-2092`; `U/src/plugPikiKando/navi.cpp:1028-1042, 2241-2265`; `N/pc_port/pc_bbft.cpp:32-41` | In v1, disable them all in netplay. The packet carries pad, yaw, flags and a host external-state chunk (§2d). | Yes | Yes |
| B7 | **Cross-CPU floating point.** The statically linked mingw libm uses x87 `fsin`/`fcos`/`fsincos`/`fpatan`/`f2xm1`/`fyl2x`. `tan` comes from msvcrt.dll. The FP environment is never pinned. The CMake default is `-march=native` with `-ffp-contract=fast`. | [V] disassembly of `N/build-randomizer/bin/nectar.exe`; `N/CMakeLists.txt:444-449`. Divergence between CPU vendors is [I], untested. | Identical exe, checked by hash. Software float libm. Pin MXCSR and the x87 control word. `-ffp-contract=off`. An objdump CI gate. | Yes (any cross-machine play) | Yes |
| B8 | **Co-op is not on the maintained line.** | [V*] 6f3602445 = merge of eb510ff4b and bb8ba817, on `claude/p2-final-integ-native-up` and `claude/p2-final-v2-native` (20edccdc8). No remote branch contains it. a95040b66 is not an ancestor. | Adopt that line and reconcile it (§2a). | Yes | Yes |

### Rollback vs lockstep, honestly

- **Shared work.** B1, B2, B3, B5 (host-only), B6, B7 and B8 are needed by both. Once they are done, lockstep is roughly transport plus handshake plus UI.
- **What rollback adds.** B4 (4–7 engineer-weeks), resimulation side-effect suppression (audio send gating and reconciliation, rumble latch, outbox discard, log gating: 3–5 weeks), lockstep barriers at transitions, time sync, and a CPU budget per presented frame:
  `T_present + T_restore + (d+1)·(T_sim_headless + T_save) ≤ 33.3 ms` for rollback depth `d`. GekkoNet saves on every advanced frame, resimulated ones included [M].
  With `T_save ≈ 1.5 ms`, `T_restore ≈ 3 ms` and `T_present ≈ 8 ms`, depth 4 needs `T_sim ≤ ~3.6 ms` [I: those inputs are microbenchmark numbers, and `T_sim` has not been measured].
- **How it feels.** At 30 Hz one frame is 33 ms, and lockstep delay is `ceil(one-way latency / 33) + a jitter margin`:
  - A same-region pair (about 60 ms RTT) gets 1–2 frames of delay (33–66 ms).
  - A 150 ms RTT pair gets 3–4 frames (100–133 ms).

  Pikmin is RTS-paced with an inertial captain, so I infer 1–2 frames is nearly unnoticeable and 3–4 is noticeable but playable (needs playtesting). Because the camera becomes local (camera yaw sent as input, §2b), camera rotation stays instant even in lockstep. That removes the most visible artifact of delay-based play.
- **Recommendation.** Ship lockstep as a real release (M0–M5). Build rollback (M6–M8) only if the M6a spike numbers fit the budget and playtests show lockstep delay is a problem for the pairs you care about.

---

## 2. Recommended architecture

### (a) Base: integrating upstream co-op

- **Do not re-merge.** Build on `6f3602445` / `20edccdc8` [V*]. The merge-probe investigator re-derived the three semantic traps independently and found this merge resolves them correctly:
  - `Teki::getMaxLife` must wrap `getParameterF(TPF_Life)` (6f3602445 `include/teki.h:483-490`).
  - D-pad throw colour must step once, not twice (6f3602445 `navi.cpp:823-825`).
  - The save root must compose correctly (6f3602445 `card_stubs.cpp:164`).

  Push both branches to native origin, which the `claude/**` policy allows. Reproduce the claims in the merge message (`pikmin_pc` builds clean, `ninja -n` has no work, ctest 160/163) in a private build dir before anything depends on them.
- **Close the known gaps on that line:**
  1. Port whistle pluck (#452) from a95040b66 into the tabbed F1 menu (`pc_settings_rows.h`). It is the only part of a95040b66's 55 unique commits that overlaps co-op.
  2. Neutralise upstream cheats under the randomizer: `PIKMIN_UNLOCK_ALL`, All Onions and Unlock Zones in `PlayerState::courseOpen` (6f3602445 `playerState.cpp:408-413`, `pc_settings.cpp:5173-5175`), plus no-day-advance and the carry/navi speed cheats.
  3. Extend the `pc_bbft_accept_input()` gate to `pad[1]` (6f3602445 `pc_window.cpp:1253-1258`).
  4. Add a co-op activation path for the randomizer's direct boot. `N/src/plugPikiColin/gameSetup.cpp:265-336` skips `U/src/plugPikiColin/cardSelect.cpp:87-110`. Use a bootstrap line or CLI flag that calls `pc_coop_set_pending(true)` before `GameCoreSection`. Do not add it to manifest `capabilities`, because `R/randomizer/runner.py:40-42` requires an exact hello.
  5. Make `R/scripts/export_native_source.py:22-26` filter out `android/`, `third_party/SDL2-android/`, `pc_port/android/`, `packaging/android/` and `pc_port/touch/assets/`, and either handle `nectar.ico` or guard `nectar.rc`. Today it raises on 55 binaries.
  6. Give the fork's single-captain code a co-op pass: `N/pc_port/pc_p2_cave.cpp:47-178`, `pc_p2_hardlanes.cpp:96,156`, `pc_p2_purple_feedback.cpp:94`.
- **Player mapping.** The remote player is simply "P2 on pad channel 1" on the host; on the guest the channels are swapped. That drives the remote Navi's Kontroller, the P2 camera manager, `DrawContainer(2)`, `mPlayer2Controller` and the Y menu unchanged, because all of them resolve to `sControllerPad[mPlayerNum-1]` [V] (`U/src/sysDolphin/controllerMgr.cpp:59-155`).
- **Adapting upstream co-op for online play:**
  - Remove the camera from the sim by sending camera yaw as input (§2b). This makes upstream's merged/dynamic camera (`U/src/plugPikiKando/gameCoreSection.cpp:2680-2780`) presentation-only: force it off in netplay, and each peer draws only its own captain, full screen.
  - Pause becomes a session event, outside rollback. F1 zeroes only the local outgoing input (`U/pc_port/pc_window.cpp:1254-1268`).
  - The Y map becomes local UI: while it is open, the local peer sends neutral input. That has the same effect as `mIsControllerFrozen` without the remote peer having to simulate a Movie-heap menu.
  - The Onion menu stays simulated from pad input, and its `DrawContainer` state lives in the snapshot.
  - Audio listener at the local Navi. Rumble only on the local channel.
  - VS is out of scope for v1. It has a `steady_clock` countdown (`U/pc_port/pc_vs.cpp:165-203`) and writes `mPauseAll` from the present path (`U/pc_port/dolphin_stubs/vi_stubs.cpp:41`, `pc_settings.cpp:4502-4532`).

### (b) Deterministic fixed-step simulation

1. **Clock.** When netplay is active, `System::updateSysClock` sets `mDeltaTime = f32(1/30)` (`N/src/sysDolphin/system.cpp:461`), and `fpsMode` is locked to 30 Hz (`N/src/plugPikiColin/newPikiGame.cpp:2926-2936`). The netplay driver replaces the tick body at `system.cpp:339-378`. GekkoNet events decide how many ticks run per loop iteration. The frames-ahead value drives time sync.
2. **Removing local freezes and wall-clock timers:**
   - `pc_bbft_hold`'s foreground condition (`N/pc_port/pc_bbft.cpp:97-104`) changes to "zero the local captured input". Randomizer not-ready becomes a synchronized HOLD/RESUME event.
   - The whistle double-tap (`N/src/plugPikiKando/naviState.cpp:1696-1706`, `N/pc_port/pc_whistle.h`) counts frames.
   - The purple camera-shake throttle (`N/pc_port/pc_p2_purple_feedback.cpp:97-104`) counts frames.
   - The 3 s staleness rule (`N/pc_port/pc_randomizer.cpp:348`) moves to the host's I/O side.
3. **RNG.** Replace `System::getRand`/`getHalfRand` (`N/include/system.h:209-210`), `BaseApp::rnd` (`N/include/BaseApp.h:36`) and the bare `rand()` at `N/src/plugPikiKando/itemAI.cpp:755` with an in-exe LCG compatible with MSL (`RAND_MAX 0x7fff`, returning values in [0,1)). Reseed from `hash(session seed, day, stage)` when each `GameCoreSection` is constructed, so replays and recovery can start from the day's start. Assert that it is only used from the main thread.

   **Particles stay on the sim stream.** Particle callbacks do hit checks and damage (`N/src/plugPikiYamashita/TAIeffectAttack.cpp:58-87, 224-260`). Only draw-time consumers move to a cosmetic stream: `viewPiki.cpp:453`, `drawWorldMap.cpp:2198`, UI, and camera shake (`pcammotionevents.cpp:122-130`, `navi.cpp:417-420`). Also fix the off-by-one at `N/src/plugPikiKando/aiAttack.cpp:235-236`.
4. **Camera yaw as input** (new; this is the key simplification).
   - In our fork the sim reads the camera in exactly three places [V*]: `navi.cpp:1925` (main-stick basis), `navi.cpp:2134` (C-stick basis) and `navi.cpp:1987-1990` (mouse cursor, disabled in v1). Every other coupling runs sim→camera: vibration at `KingAi.cpp:164/209/1467`, `SnakeAi.cpp:1045/1109`, `itemMgr.cpp:920-922`, and `startMotion`/`mControlsEnabled` at `naviState.cpp:2575-2578, 3206-3207`.
   - Therefore the packet carries each captain's control yaw (u16), and `makeVelocity`/`makeCStick` use it instead of `mNaviCamera`/`controlCamera()`. Each peer's `PcamCameraManager` becomes a purely local presentation object, and sim→camera calls act on the local camera only.
   - What this buys: no simulation of the remote camera, no camera state in snapshots, no merged-camera synchronisation, and an instant camera under lockstep. Stick and yaw are sampled together, so movement matches what the player saw.
   - Still to audit: upstream's `mControlCamera` paths (`U/src/plugPikiKando/navi.cpp:2188-2192, 2270-2280, 2421-2428`) and any other upstream sim reads of the camera. I checked the fork only.
5. **Two-pass frame.** This resolves B1 without first rewriting the order of the draw-embedded sim.
   - **Authoritative pass (every tick, and every resim tick):**
     - Run `renderall()` with a new pc_gfx null backend: no GL calls and no texture uploads. pc_gfx has no such mode today [V].
     - Set `gfx.mCamera` to a SimCamera whose `mLookAtMtx` and `mInverseLookAtMtx` are identity. The animation matrices (`lookAt · world · joint`) are then world-space, so `CollPart` centres are exact and independent of any camera.
     - Netplay culling policy: `enableAICulling`/`disableAICulling` (`N/include/Creature.h:275-289`) always report visible. `DualCreature::refresh` is pinned to one dynamics mode (`dualCreature.cpp:163-205`). `Plant::refresh` stops resetting off-camera plants (`plantMgr.cpp:123-126`).
     - Camera-distance LOD decisions that gate sim-affecting code (for example `ViewPiki::_528` → `updateLook`, `viewPiki.cpp:556-630`) use a fixed LOD.
     - The sim blocks run here, in their current order: `newPikiGame.cpp:2104, 2185-2196, 2251-2282`, the fades and `postUpdate` in `BaseGameSection::draw` (`newPikiGame.cpp:787-845`), `PlugPikiApp::draw` fades (`plugPiki.cpp:151-190`) and `parseMessages` (`plugPiki.cpp:276-278`).
   - **Presentation pass (once per presented frame, never during resim):**
     - Call `pc_render_begin_presentation` (`N/pc_port/timing/pc_render_phase.cpp:45-89`; no production caller today [V]) with the local camera and real GL.
     - The sim blocks above are skipped when the phase is not authoritative.
     - Add guards to the mutators that are currently unguarded [V]: `BaseShape::updateAnim`'s `animate` (`shapeBase.cpp:3350`), the DualCreature switch, ViewPiki's `mSRT`/matrix/look writes and the `demoDraw` position writes plus `rand` (`viewPiki.cpp:432-453, 556-630`), particle kill-on-draw and `mOrientedNormal` (`particleGenerator.cpp:1124-1147, 1204-1224`), the `MapMgr::postrefresh` fade (`mapMgr.cpp:1714-1735`) and the UfoItem spot rotation (`ufoItem.cpp:1040-1052`).
     - Move `SeSystem::update` and the listener (`N/src/plugPikiKando/gameCoreSection.cpp:2875-2891`) here.
   - **Risk (verified count):** `mAnimMatrices` comes from a per-frame pool (`Graphics::getMatrices`, `N/src/sysCommon/graphics.cpp:946`), and the presentation pass refills it in camera space. There are 101 `getAnimMatrix`/`calcJointWorldPos` references in about 20 sim-side files outside `shapeBase.cpp` [V*]. Each one must either be proven to run only inside the authoritative pass, or presentation must get its own matrix storage.
   - **Cost:** two scene traversals per frame, one of them without GL. Port upstream's `kPcTickWorldSim` profiler split (`U/src/plugPikiColin/newPikiGame.cpp:2483`, `U/src/plugPikiColin/plugPiki.cpp:167`) to measure it.
6. **Build policy for netplay binaries:**
   - `-DPIKMIN_NATIVE_OPTIMIZE=OFF`. The maintained `build-randomizer` already uses this [V*], but the lane recipe in AGENTS.md and the Windows packaging (`N/packaging/windows/package-standalone.sh:60-64`) leave `-march=native` on.
   - `-ffp-contract=off` and `-ftrivial-auto-var-init=zero`. Default constructors for `Vector2f`, `Quat` and `Matrix4f` leave members uninitialised (`N/include/Vector.h:246,309`, `Matrix4f.h:19`).
   - A software float libm, preferably correctly rounded (for example the CORE-MATH binary32 functions, which are MIT-licensed [I]; musl or fdlibm are fallbacks). It must provide `sinf/cosf/sincosf/tanf/atan2f/acosf/asinf/expf/logf/powf`. `sincosf` needs covering because GCC merges sin/cos pairs, giving 274 call sites.
   - Pin MXCSR to `0x1F80` and set a fixed x87 control word at the start of every tick.
   - A CI objdump gate that rejects `fsin|fcos|fsincos|fpatan|fptan|f2xm1|fyl2x|__imp_tan|vfmadd`.
   - The handshake refuses any exe SHA-256 mismatch.

### (c) State snapshot design (rollback only)

- **Rejected: a serializer per object.** `N/include` declares 2,315 classes and structs, including 130 TaiAction subclasses, 36 NaviState, 33 PikiState, and 46 P2 modules [V]. A missed field causes a silent desync. Hand-written serialization is kept only for the small bridges (audio facade, randomizer POD, input sampler).
- **Sim region:**
  - A fixed-VA `VirtualAlloc` reservation (for example 512 MB reserved, committed on demand) with `MEM_WRITE_WATCH`.
  - A deterministic allocator with its metadata inside the region (dlmalloc `create_mspace_with_base` or TLSF), zero-filling every block.
  - `operator new` (`N/src/sysDolphin/sysNew.cpp:185-213`) routes to the region only for main-thread allocations in the SIM domain. Other threads and port infrastructure go to malloc: the pc_gfx texture/TLUT maps (`N/pc_port/gl/pc_gfx.cpp:684, 741, 950-992`), `PcVisualSnapshotStore`, and the os_stubs thread and queue maps. Use the existing but unused `N/pc_port/PikiMallocAllocator.h` or an InfraScope.
  - Reset the region with `SYSHEAP_App` at `softReset` (`N/src/plugPikiColin/gameflow.cpp:705`). That restores the console's semantics and fixes the per-stage leak.
- **Asset region:** fixed base, deterministic load order, not snapshotted. It is needed so that pointer-valued sim state is identical across peers, which raw hashes and state transfer depend on. In debug, write-watch it and assert that no sim tick writes to it; this catches cases like `AnimFrameCacher` (`shapeBase.cpp:3261-3325`).
- **Globals:**
  - Snapshot `[__data_start__, __data_end__) ∪ [__bss_start__, __bss_end__)`, minus a no-snapshot section.
  - Move the 256 MB `sArenaMemory` (`N/pc_port/dolphin_stubs/os_stubs.cpp:388-393`) to `VirtualAlloc`.
  - Split the build into `pikmin_sim` (may use LTO), `pikmin_audio` (no LTO) and `pikmin_platform` (no LTO), so a linker script can route the non-sim `.data`/`.bss` outside the bracket.
  - Tag the OSThread and message-queue objects inside sim translation units (`N/src/sysDolphin/system.cpp:132-141, 1321-1324`) as no-snapshot.
  - Keep preserve-lists for mixed objects (`sys`: DVD error code, retrace counters, `mPrevTick`/FPS; `gameflow`: card and loading-banner fields).
  - Expected size: about 150–300 KB of real sim globals [I].
- **Link `-static-libstdc++ -static-libgcc`** so `std::string` growth uses our `operator new`. Acceptance: the unknown-frees counter at `sysNew.cpp:157-183` reads zero.
- **Mechanics:**
  - GekkoNet runs in **handle mode**: `state_size = 8` holds (slot index, frame), and the game keeps its own ring of 8–12 frames. This was tested at [M] (0 desyncs in a toy). Without it, `storage.cpp:11` would allocate `(window + 2) × state_size`.
  - Phase 1 is a write-watch shadow copy plus an undo log per tick. Phase 2 applies only if the segregated region stays under about 8 MB: a full `memcpy` ring.
- **Estimates [M, microbenchmark on this machine, not in-game]:**
  - Save: 1.1–2.2 ms per tick at 500–1000 dirty pages, including a first-write fault tax of about 0.7 µs per page.
  - Restore: about 1.3 µs per page.
  - `GetWriteWatch`: 0.14–0.8 ms.
  - `memcpy` of a compact 6–8 MB region: about 0.6 ms each way.
  - Memory: the shadow copy is about the used region (30–50 MB), plus 10–50 MB of ring.
  - Live objects today: about 18 MB in about 83k blocks.
  - Unknown: the dirty set in a real game tick (the M6a spike measures it).
- **After a restore:**
  - Invalidate the GL and resident-mesh caches for restored pages (upstream `DCFlushRange → pc_gfx_invalidate_cpu_range`).
  - Call `PcVisualSnapshotStore::synchronize()`.
  - Reconcile audio.

### (d) Input sync layer and library

- **Library: GekkoNet** (BSD-2), pinned at 3b21722 and vendored as `N/third_party/gekkonet`.
  - Build it as its own static library with `GEKKONET_NO_ASIO` and `-std=gnu++20`, outside `NATIVE_COMPILE_OPTIONS`. It compiles cleanly with MinGW g++ 16.2 [M].
  - Config: `max_spectators = 0` (handle mode is incompatible with portable saves), `desync_detection = true`, `check_distance ≥ 7`.
  - Lockstep: window 0 with an adaptive local delay. Rollback: window 6–8 with local delay 1–2.
  - Rejected: GGPO (no commits since 2019, IPv4-only, owns its socket, no network checksum), GGRS (needs Rust FFI), and GameNetworkingSockets (protobuf and OpenSSL, no MSYS2 package).
- **Injection point:** after `PADRead` in `ControllerMgr::update` (`N/src/sysDolphin/controllerMgr.cpp:24-37`), overwrite `sControllerPad[0..1]` with the inputs for the frame being simulated.
  - `pc_window_poll_events` keeps sampling locally and pumping SDL and audio. Whatever it wrote to `pad[1]` is discarded.
  - Controller and Kontroller edge state is heap state, so it lands in the snapshot.
- **Input record, fixed about 20 bytes per player:**

  | Field | Type |
  |---|---|
  | buttons | u16 |
  | stick X, stick Y, C-stick X, C-stick Y | 4 × s8, with deadzone and quantisation to reduce mispredictions |
  | L and R triggers | 2 × u8 |
  | control yaw | u16 |
  | flags | u8: local-menu-neutral, pause request, skip-cutscene edge |
  | external-state chunk (host only) | u8 sequence + 8 bytes payload |

  The chunk decoder is sim state. Chunks are tagged by frame, so a chunk that has been predicted by repetition decodes as a no-op, whatever the library's prediction rule. At 30 Hz a 60-byte randomizer state vector takes about 8 frames.
- **Movie skip** is derived from a confirmed Start edge in the inputs. It replaces `pc_bbft_start_button` (`N/pc_port/pc_window.cpp:892`), `pc_bbft.cpp:32-41` and `moviePlayer.cpp:645`.

### (e) Transport, NAT and lobby

- **Adapter 1: plain Winsock UDP** for direct IP:port. It comes first and is used for the M3 loopback, LAN, and Tailscale/ZeroTier.
- **Adapter 2: libjuice 1.7.4** (MPL-2.0; zero dependencies; builds with MinGW; loopback ICE completed in 17 ms [M]).
  - ICE with STUN at `stun.cloudflare.com:3478` and `stun.l.google.com:19302`.
  - TURN fallback, which 10–25% of consumer pairs need [I from published estimates]: self-hosted coturn or `juice_server`, or Cloudflare TURN.
  - A one-byte channel prefix (ping, handshake, bulk, gekko), in the style of RMG-K's LobbyIce (GPL, so design only).
  - A locked receive queue, because libjuice callbacks arrive on its own thread.
- **Signalling:** a room code through a tiny service (Python asyncio websockets, or a Worker) that relays SDP and candidates and issues short-lived TURN credentials. Copy-paste connection codes work with no server at all. For randomizer sessions, Archipelago `Bounce` is an optional signalling path [I, unverified].
- **Bulk channel:** chunked and acknowledged. Every declared length is bounded before allocation (the RetroArch PR #19614 lesson). It carries save and checkpoint transfer, and later state resync.
- **Handshake, refusing on any mismatch:**
  - exe SHA-256;
  - an assets digest (game data is never sent);
  - the session-config block: `fpsMode`, `chainActions`, `holdToPluck`, `whistlePluck`, `pikiLimit`, day length, mods and cheats, co-op settings, and the P2 profile `.txt` hashes;
  - the manifest fingerprint plus the bootstrap hash with the `SESSION` line removed;
  - the checkpoint generation and hash, and the save hash.

  Disable `PIKMIN_RANDOMIZER_TEST_*` and the debug keys.
- **Do not reuse the BBFT localhost TCP transport** (`N/pc_port/bbft/bbft_transport.c:595-605`, WIN32-only).
- **Licences:** add a `THIRD_PARTY_NOTICES` file (GekkoNet BSD-2, zpp_bits MIT, libjuice MPL-2.0 with a source link, xxhash BSD-2). Copy no code from Slippi, Dolphin, RMG-K, 3sx, RetroArch or sm64coopdx.

### (f) Suppressing side effects during resimulation

- **Flag:** `pc_netplay_resimulating()`, fed by GekkoNet's `rolling_back` flag on Advance events. A resim tick is the authoritative pass only: null GX, no presentation pass.
- **Audio:**
  - During resim, suppress `pc_audio_*` sends but report success. `Jac_PlayEventAction` records a slot only on a successful send (`N/pc_port/dolphin_stubs/audio_stubs.cpp:1055-1060`).
  - The facade bookkeeping goes into the snapshot: `sEvents[16]`, `sFreeEvents`, `sEventClock`, the pause latches, `sCountdownSounds`, demo state and `sVoiceRandom` (`audio_stubs.cpp:43-72, 105-108, 182-202, 437-485`).
  - Move `Jac_Gsync`'s frame timer (`system.cpp:326`) into the tick.
  - After a rollback, reconcile BGM, loops and pause state. One-shots play only the first time a frame is simulated.
  - **Conflict:** the maintained build uses the original jaudio engine (`PIKMIN_NATIVE_JAUDIO=ON` [V*]), which has an audio thread. The investigators analysed the facade, which is the CMake default (`N/CMakeLists.txt:92`). Netplay should pick one backend (see Q10).
- **Rumble:** `PADControlMotor` stores only the latest command per channel and applies it once per presented frame, local channel only, dropped during resim. Upstream's SDL rumble is at `U/pc_port/dolphin_stubs/pad_stubs.cpp:43-52`.
- **Particles:** fully simulated during resim, because they are gameplay. Only presentation-side mutations move.
- **Outbox (frame-tagged; entries at or after R are dropped on rollback to R; the host flushes up to the confirmed frame):**
  - `pc_randomizer_check` / `bbft_check`
  - `emperor_defeated`
  - `observe_pikmin_death`
  - the `consume_benefit` journal write
  - `save_campaign`, card saves, and the permadeath erase
  - `pc_bbft_milestone`, and the randomizer `printf` events
- **Logging:** `PRINT`/`_Print` (`N/include/DebugLog.h:12-29`) and the port's `printf` helpers are gated on the resim flag.
- **Barriers** (rollback disabled; wait until every input up to the triggering frame is confirmed; re-baseline the ring after `finalSetup`):
  - `softReset` and section change (`N/src/plugPikiColin/plugPiki.cpp:214-226`, `gameflow.cpp:625-792`);
  - day end and card saves (card worker thread, `cardutil.cpp:799-928`; `memoryCard.cpp:864-905`; no snapshot while `mIsCardSaving`);
  - cutscene start and end, plus Movie-heap loads of menu and tutorial windows (`newPikiGame.cpp:615-700`);
  - the permadeath erase (`newPikiGame.cpp:1159-1174`).

### (g) Randomizer and Archipelago integration

- **Host-authoritative, one shared AP slot.**
  - Only the host runs the runner. Start from **main's** `randomizer/runner.py`/`session.py`, which have DeathLink and the Sync/Retrieved readiness fix; this branch's copies are older [V].
  - The client runs a netplay-client runner mode: no AP connection, and a mirror directory `session/netplay/<fingerprint>/` so the overlay and F8 tracker work. It never writes the host's session.
- **Applying state:**
  - Split `pc_randomizer_update` into "read the file" (host I/O side) and "validate and apply" (sim side).
  - When the host's state vector changes, send it as the chunked external stream (§2d). Both peers apply it at the start of the frame where it completes, before `updateAI`.
- **Splitting `ready`:**
  - Link liveness turns into synchronized HOLD/RESUME events.
  - The sim-visible predicate means "initial sync done", and it drops the wall-clock gate from `pc_randomizer.cpp:442, 533, 551, 596`, `aiBoMake.cpp:135`, `aiBridge.cpp:587` and `aiBreakWall.cpp:203`.
- **Split `checks`** into a set owned by the sim (in the snapshot, read by `reconcileBbftParts`, `pc_bbft_checked` and `isBbftRestoredPart`) and a confirmed external set.
- **Gather the randomizer statics into one POD struct** that is snapshotted and hashed:
  - from `pc_randomizer.cpp:24-60`: `consumedBenefits`, `benefits`, `statUpgrades`/`colorStats`, repairs, unlocks, Flarlic, `deathLinksPending`/`Seen`/`Baseline`, `deathsReported`, `inducedDeaths`, `emperorDefeated`, `generatorIds` (keyed by stable id, not pointer);
  - the cooldowns at `gameCoreSection.cpp:1922, 1958, 2051`;
  - `bbftColorGranted`, `initialColorRegistered`, `bbftRedsQueued`/`Ready` and `bbftInitialField` at `gameCoreSection.cpp:2155-2239`;
  - `bbftReplayedParts` at `playerState.cpp:30`;
  - `BossMgr::mPrereleaseTrap`.
- **Day-end save barrier:** the host does the real card write and `pc_randomizer_save_campaign`, then sends `SAVE_RESULT(ok, generation, hash)` at a frame. The client forces the same `mDidSaveFail` and `gamePrefs` outcome and writes only to its mirror. A disconnect is treated like today's abandoned day (`R/README.md:140`). There is no host migration.
- **Co-op policy for hooks anchored to P1:**
  - `gameCoreSection.cpp:1918-2152`: the heal target, the Flower Shower, Bomb Ambush and Progg anchors, the landing check, and the `mNavi->mHealth > 0` gate at line 2092.
  - `KingAi.cpp` and `TAImar.cpp:214`: rumble and vibration using controller 0 only.

  This is owner policy (Q8).
- **Excluded in v1:** BBFT cross-game mode, the P2 cave/pod/preview modes (`pc_p2_cave_tick` calls `_Exit(42)` and opens modal boxes from `updateAI`, `gameCoreSection.cpp:2088`), photo mode, and the debug keys.

### (h) Desync detection and recovery

- **Checksum every frame.** A curated 64-bit hash, computed by walking the object managers in fixed order. It covers:
  - position and rotation bits, health and state ids;
  - Pikmin counts per colour and state, and Onion counts;
  - RNG state and the world clock;
  - the randomizer POD.

  It excludes audio, `SeContext` and render caches. It goes into GekkoNet's save checksum, which is compared for the confirmed frame (`game_session.cpp:372-390`).
- **Debug:** on mismatch, dump a vector of per-subsystem hashes, a full-region XXH3 (xxhash is already vendored upstream) and the input log, and diff them offline (3sx `compare_states` pattern). The determinism harness (M1) is the same code path.
- **Recovery v1:** stop the session, show a desync notice, and have both peers reload the host's last saved day, then reconnect. This reuses the existing abandoned-day semantics and needs no new state format.
- **Recovery v2 (M9):** full state transfer of the region plus the globals image over the bulk channel, zstd-compressed. It is only valid with an identical non-ASLR exe (`--disable-dynamicbase`), a fixed region base and a deterministic asset region. The client restores it and resumes at frame F. The same mechanism enables mid-session reconnect.
- **Barrier cross-check:** at every day start, compare save-file hashes.

---

## 3. Milestone plan

Every milestone starts with a GitHub issue in 4laric/pikmin-randomizer that states scope and acceptance criteria, assigned to 4laric, with Claude or Codex recorded as implementation owner (AGENTS.md). Builds go in private `output/native-<lane>-build` directories with `-DPIKMIN_NATIVE_OPTIMIZE=OFF`.

**M0: Base and tracking (1–2 weeks).**
- Scope:
  - Adopt the 6f3602445/20edccdc8 line, push it, and reproduce its build and ctest results.
  - Reconcile a95040b66's 55 commits, including whistle pluck.
  - Close the gaps in §2a: cheats, `pad[1]` gate, direct-boot co-op flag, export filter, single-captain audit.
- Acceptance:
  - Build evidence: pinned commit, executable SHA-256, `ninja -n` reports no work, ctest.
  - A headless randomizer boot with the co-op flag spawns two Navis, shown by a log line and a bot screenshot.
  - The export script completes on the line.
- Can run in parallel with M1, which touches files that barely conflict.

**M1: Determinism harness and deterministic mode, single process (2–3 weeks).** This comes first because it delivers the most verifiable value.
- Scope:
  - A `--netplay-deterministic` mode: fixed dt, in-exe PRNG seeded per day, frame-counted whistle and shake timers, no hold/foreground freeze, side channels disabled.
  - `--input-record` / `--input-replay`, capturing `sControllerPad[0..3]` per tick after `PADRead`.
  - A curated per-tick state hash written to a file.
  - Port the `kPcTickWorldSim` profiler split.
  - Build flags: `-ffp-contract=off`, MXCSR and control-word pinning.
- Acceptance (headless, hidden window through the existing test-background mode):
  - **A.** Record a scripted 5-minute day from a day-start save. Replay it in two fresh processes. The ≥9,000 per-tick hashes are identical.
  - **B.** Replay at 1280×720 and at 800×600. The harness reports the first divergent tick and subsystem. This is expected to fail until M2; the deliverable is the localisation.
  - **C.** Replay after 10 extra seconds on the title screen. Hashes are identical, which proves per-day seeding.
  - **D.** A ctest target runs a 2-minute replay twice.
  - **E.** A report of the world-sim tick cost (p50/p95) in a busy area.

**M2: View-independent co-op sim and FP hardening (4–7 weeks).** This is the largest milestone.
- Scope:
  - The two-pass frame (null GX, identity sim camera, netplay culling policy, presentation guards, `SeSystem` in the presentation pass).
  - Camera yaw as input.
  - The audit of the 101 animation-matrix readers.
  - Two-channel recording for upstream local co-op.
  - Software float libm and the objdump gate.
- Acceptance:
  - M1-B passes at different window sizes and aspect modes.
  - Replay with a debug-perturbed local camera gives identical hashes.
  - A local co-op recording (P2 on channel 1) replays identically.
  - The objdump gate is clean.
  - The same recording on an Intel and an AMD machine gives identical hashes (needs hardware, see Q5).
  - Non-netplay single-player bot evidence and ctest are unchanged.
  - Netplay mode frame p95 is under 33 ms in a busy area.

**M3: Two local instances in lockstep (2–3 weeks).**
- Scope:
  - Vendor GekkoNet with window 0.
  - Winsock UDP adapter, plus a test adapter that injects latency and loss.
  - The netplay driver in `System::run`.
  - Pad and yaw injection, handshake, host-to-client save transfer.
  - Session pause and neutral input for the local Y map and F1.
- Acceptance:
  - Two headless instances with scripted inputs on both, 100 ms one-way latency, 5% loss, a 30-minute session that crosses a day end.
  - Zero GekkoNet desync events. The host save bytes equal the client's mirror save. Hashes match at each day start.
  - Negative tests: a mismatched exe or settings block is refused.

**M4: Randomizer and AP in lockstep (3–5 weeks).**
- Scope:
  - Host-only runner (from main) and client mirror mode.
  - The chunked external-state stream, the `ready` split and synchronized HOLD.
  - Host-only outbox flush, the split `checks` set and the randomizer POD.
  - The day-end save barrier.
  - Owner decisions on co-op benefit policy.
- Acceptance, against a local Archipelago test server:
  - Items injected during active play apply on the same frame on both peers, shown by equal hashes.
  - `checks.txt` exists only on the host, with no duplicate LocationChecks.
  - The DeathLink count is exact.
  - Killing the AP connection makes both peers HOLD on the same frame, and both resume.
  - The next session resumes from the host checkpoint on both peers.

**M5: Internet play, the first release (3–5 weeks plus ops).**
- Scope:
  - libjuice ICE adapter and bulk channel.
  - Room-code signalling service and TURN.
  - Copy-paste codes.
  - Netplay menu and HUD: ping, jitter, delay, desync indicator.
  - Recovery v1 and adaptive delay.
- Acceptance:
  - Scripted tests: libjuice host-candidate loopback, forced TURN-only against a local coturn, copy-paste flow, and a room-code flow against a locally run signalling service.
  - Field test: a 1-hour session between two real networks with zero desyncs.

**M6: Snapshot and restore (5–8 weeks).**
- **M6a spike (3–5 days):** redirect `new` into a write-watch region, crashes tolerated. Measure dirty pages and allocation churn per tick over a real day. This decides between write-watch and `memcpy`, and whether rollback is worth pursuing.
- **M6b production:** the region allocator and routing, the infrastructure migration, the library split and linker script, static libstdc++, the preserve-lists, and handle-mode integration.
- Acceptance:
  - `--netplay-synctest 7`: every tick, save, advance, restore 7 frames and re-advance. Curated and full-region hashes match, with zero mismatches over scripted days in 3 or more stages including P2 enemies and a boss.
  - Save p95 ≤ 2 ms and restore p95 ≤ 4 ms on this machine.
  - unknown-frees is 0.

**M7: Suppressing side effects during resimulation (3–5 weeks).**
- Scope: the resim flag, audio gating and reconciliation, the rumble latch, outbox discard, log gating, barrier enforcement.
- Acceptance: a two-instance GekkoNet session with forced rollbacks every frame over the lossy adapter.
  - `checks.txt`, `deaths.txt` and `emperor.txt` are byte-identical to a reference run with the same inputs and no rollback.
  - The audio free-slot count returns to baseline.
  - A counter shows zero GL calls during resim.
  - An assert shows no rollback ever crosses a barrier.

**M8: Rollback online (2–3 weeks).**
- Scope: window 6–8, local delay 1–2, time sync, a rollback-depth histogram in the HUD.
- Acceptance, at 150 ms emulated RTT:
  - At least 99% of presented frames finish within 33.3 ms on a mid-range reference PC.
  - Zero desyncs over 1-hour sessions.
  - A subjective A/B test against lockstep.

**M9 (optional):** VS mode made deterministic; mouse-cursor mode, sending per-player cursor deltas in the packet in place of the keyboard-owner checks; state-transfer resync and reconnect; spectators.

**Totals [I]:**
- Lockstep release (M0–M5): about 15–25 engineer-weeks.
- Rollback on top (M6–M8): about 10–16 more.
- Overall: about 25–40 engineer-weeks.
- These totals remove overlap between the investigators' lane estimates. The largest uncertainty is M2.

---

## 4. Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Presentation-pass mutations get missed, so peers desync or single-player changes | High | High | Gate netplay behind a flag. Localise with the M1 harness. Start the audit from the 33 `pc_render_is_authoritative` sites plus the unguarded list in §2b. |
| R2 | The animation-matrix pool is refilled in camera space by the presentation pass while sim readers (101 references) consume it | Medium | High | Audit in M2. Give presentation its own matrix storage. Assert on phase. |
| R3 | Forcing AI unculled costs CPU and changes vanilla behaviour: off-screen enemies keep acting, the plant reset changes, and tutorial text-demo triggers (`pikiState.cpp:2491`, `aiTransport.cpp:955`) fire | Medium | Medium | Measure in M2. Alternative: a canonical frustum built from both captains' positions at a fixed aspect. |
| R4 | The headless sim tick is too slow for a useful rollback depth | Unknown | High (for rollback) | Measure in M1. Lockstep is already shippable. |
| R5 | The dirty set is over about 8 MB per tick | Unknown | Medium | M6a spike. Curate the region. Use `limited_saving` as a last resort (it disables desync detection). |
| R6 | x87 or msvcrt transcendentals diverge between CPU vendors [I] | Medium | High | Software libm plus the objdump gate. Test on Intel and AMD in M2. |
| R7 | Hidden state stays outside the snapshot: about 67–155 mutable statics, about 25 P2 maps keyed by pointer, libstdc++ DLL allocations | High | High | Region approach, static libstdc++, SyncTest in CI. |
| R8 | The line split (a95040b66 vs the co-op merge) and future upstream merges into heavily modified files | High | Medium | Decide the maintained line now (Q1). Merge upstream small and often. |
| R9 | AP false positives from predicted frames, including `reconcileBbftParts` killing a carried pellet | High without the outbox | High | Outbox plus the split `checks` set; M7 byte-identical journal test. |
| R10 | The audio bridge is designed for the wrong backend. jaudio's audio thread may read creature memory (SVector sound offsets) while a restore is running | Medium | Medium | Decide Q10. Test for the race in M6. |
| R11 | GekkoNet has a single maintainer | Low | Medium | Pinned and vendored. About 5.8k lines, forkable. |
| R12 | NAT failures without TURN (10–25% of pairs) | High | Medium | TURN, plus documented VPN fallbacks. |
| R13 | Security: exposed IPs, unencrypted traffic, a malicious peer sending oversized declared lengths | Medium | Medium | Bounded lengths, optional AEAD keyed from the room secret, a relay-only option. |
| R14 | Disabled v1 controls (cursor mode, lock-on, free camera, gyro) disappoint players | Medium | Low | Document it. M9 serialises them per player. |
| R15 | The card worker thread and saves interact badly with snapshots | Medium | Medium | Barriers. No snapshots while `mIsCardSaving`. |

---

## 5. Open questions for the project owner

1. **Base line.** Is a95040b66, the source of the engine/ export, still the maintained native line, or does the P2 final line with the upstream merge (6f3602445/20edccdc8) take over? Netplay has to be built on the co-op line. May those local-only branches be pushed now?
2. **Staging.** Ship lockstep online co-op first and gate rollback on the M6a measurements? (Recommended.)
3. **View model.** Each peer sees its own captain full screen (recommended; requires the two-pass frame), or both peers render identical split screens (a cheaper prototype, worse UX)?
4. **Behaviour changes only in netplay.** Are these acceptable?
   - No view-based AI culling.
   - A pinned DualCreature dynamics mode.
   - Movement driven by camera yaw sent as input.
   - Locked to 30 Hz.
   - In v1: mouse/cursor mode, lock-on/charge, free camera, first person, gyro and wheel controls disabled.
5. **Hardware.** Is an AMD machine, and an older Intel one, available for determinism tests across CPU vendors? Support across vendors should be mandatory; this decides when it can be verified.
6. **Infrastructure.** Will you run a signalling and TURN service (domain, cost, credentials, abuse handling)? Or should v1 ship with direct IP, VPN and copy-paste codes only?
7. **AP model.** One shared slot with only the host connected to AP (recommended)? When the host's AP connection drops, should both peers pause (today's behaviour) or keep playing offline, with checks journaled and sent later?
8. **Co-op randomizer policy.** Which captain receives heals and ambush and spawn anchors? Should benefits apply while P1 is down but P2 is alive (`gameCoreSection.cpp:2092`)? How does DeathLink count across two captains?
9. **Exclusions in v1.** VS, BBFT cross-game mode, the P2 experimental modes, permadeath, photo mode, mid-session join or reconnect, spectators. Confirm all of them.
10. **Audio backend for netplay builds.** The original jaudio engine (what the maintained build uses), or the port's mixer facade (the CMake default, main-thread only, easier to bridge)?
11. **Game traffic.** Should it be encrypted and authenticated in v1?