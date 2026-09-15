# Lane 07 (Lifetime/fixtures) — DeepSeek handoff

Tracking issue: [#397](https://github.com/4laric/pikmin-randomizer/issues/397); coordination [#186](https://github.com/4laric/pikmin-randomizer/issues/186).
Implementation owner: Codex through shared account `4laric`; executing agent/session: DeepSeek (lane 07, `dsw/l07-root`).

## Slice delivered

**Consumer (one live family):** Dwarf Orange Bulborb — species `BlueKochappy`,
source_id `44`, native module `pc_p2_dwarf_orange` (generator id `211001`), with an
ordinary P1 Chappy control (`211002`).

**Concrete slice:** reconcile the centralized forget/rebind ownership with this
live family through the *engine-driven* seam, closing the "broader family
lifetime/re-entry coverage" leg that remained after the Snow new-scene gate. It
proves on a live actor, with **no** fixture `_forget` call and **no** manager
swap (the narrower lane-13 `pikmin2_dwarf_orange_reentry` reset):

1. **Engine-driven forget** — `target->kill(false)` enters `BTeki::doKill`, which
   calls `pc_p2_forget_teki` -> `pc_p2_dwarf_orange_forget`; `P2_FORGET_PROBE
   after_engine_dokill=0`.
2. **Late birth + clean rebind** — the staged generator re-initializes
   (`targetGen->init()`), the newborn actor is observed clean (`P2_REUSE_PROBE
   registered_before_rebind=0`) and re-registers cleanly (`rebound_registered=1
   alive=1`).
3. **Control unaffected** — `P2_DO_CONTROL_ALIVE alive=1`.

The kill *trigger* is an explicit fixture injection (`kill(false)`); everything
downstream is the real engine death funnel. Address reuse is reported, not
gated: in this arena the engine handed a *different* pool slot back
(`same_address_observed=0`) because the killed `TEKI_Chappy` is non-removable
until the generator's `informDeath` bookkeeping, so `getEmptyIndex()` allocated
a lower free slot. The seam's staleness guarantee (`TekiMgr::newTeki ->
pc_p2_forget_teki`, `tekimgr.cpp:313`) is what makes `registered_before_rebind=0`
hold regardless of which address the pool returns (deterministic `same_address=1`
was already proven at flora level in `docs/PIKMIN2_TEKI_LIFETIME_SEAM.md`).

## Ordered commits

Root base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`; native base
`b805d9c626e4f4558c95aef7cac311a5d9a2068f`.

| Branch | Commit | Subject |
|---|---|---|
| root `deepseek/p2-l07` | `16d4599` | lane07: Dwarf Orange engine-driven lifetime/re-entry probe (forget/rebind/late-birth) (#397) |

Native `deepseek/p2-l07-native`: **no commits** — the shared seam
(`pc_p2_teki_lifetime.*`, `BTeki::doKill`, `TekiMgr::newTeki`,
`GameCoreSection::exitStage/finalSetup`) is already integrated at the pinned base;
this slice needed no native source change. Both worktrees clean at handoff.

## Interfaces / hooks touched

None new. The slice consumes the already-integrated shared seam and the
`pc_p2_dwarf_orange` family API (`registered`, `forget` via seam, `setup` re-read),
plus a replacement-main `preview_p2_room.cpp` fixture. No shared file
(`teki.h`, `tekiinteraction.cpp`, `tekibteki.cpp`, `tekimgr.cpp`, `gameCoreSection.cpp`,
`navi.cpp`, `pc_p2_preview.cpp`, CMake) was edited.

## Build evidence (`output/dsw/l07-build-evidence.txt`)

```
2026-09-14T19:44:59 lane=l07 target=pikmin_pc native=b805d9c626e4f4558c95aef7cac311a5d9a2068f dirty=no
  build_dir=.../native-l07-build exe=.../bin/nectar.exe
  sha256=2d507c6cf0a827ce4bbf4e3beb22aac1998b1bf310f90bf4005048388921accc ninja_n="ninja: no work to do." seconds=147
```

- Native head `b805d9c6` (clean), Ninja + MinGW g++ 16.2.0, Release, `PIKMIN_NATIVE_JAUDIO=ON`, LTO.
- Replacement-main fixture `fixture.exe` SHA-256 `b13e13214ff9d2d6b1bc4724f85837d9aea1f0ca9b1a9fb0c0ce92f6c83b3cee`
  (`provenance.json` status `built`).
- `nectar.exe` SHA-256 `2d507c6cf0a827ce4bbf4e3beb22aac1998b1bf310f90bf4005048388921accc`.

## Fixture adoption evidence

- Window: `Experimental preview window set to 960x540 windowed and centered` (and `SDL2 Window & OpenGL Context initialized successfully (960x540)`).
- Live squad: `P2_DO_LIFETIME_SQUAD alive=20`.
- No extinction; run exit 0, elapsed 1.31 s.
- Run dir: `output/dsw/l07-out/run3` (native.log SHA-256 `0f416331734768ea604e091e95354231fcc7ffe3ea974e303907b38c50ca3408`).

## Six arena gates (Dwarf Orange 44)

| Gate | Result | Evidence (natural vs injected) |
|---|---|---|
| 1. Identity + spawn | PASS (natural) | `P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy generator=211001 x=-150 y=30 z=1850 health=250.0 max_health=250.0` |
| 2. Autonomous movement + animation | UNTESTED here | bank loads (`P2_DWARF_ORANGE_BANK poses=64 mod_bytes=1024000`); no draw frame observed — probe kills on frame 2. Family lane 13. |
| 3. Attacks + receivers | UNTESTED (injected death trigger) | `kill(false)` is explicit; no Pikmin attack/receiver. Family lanes 13/10. |
| 4. Death + corpse | death injected / corpse N/A | `kill(false)` -> `BTeki::doKill` directly (no `becomePellet` corpse path). Family lanes 13/06. |
| 5. Transport + reward | N/A | cargo-free arena, no Onion/Pod; lane 06. |
| 6. Cleanup + re-entry | **PASS** (engine-driven, labelled injected trigger) | `P2_FORGET_PROBE after_engine_dokill=0`; `P2_REUSE_PROBE registered_before_rebind=0 same_address=0`; `rebound_registered=1 alive=1`; `P2_DO_CONTROL_ALIVE alive=1` |

Completion marker `PASS P2_DWARF_ORANGE_LIFETIME` (exit 0).

## Tests

`py -3.12 -m pytest tests/test_pikmin2_dwarf_orange_lifetime.py -q` -> **28 passed**.
Focused battery (`test_pikmin2_dwarf_orange_{lifetime,chain,runtime}.py` +
`test_pikmin2_lifecycle_runtime.py`) -> **45 passed**.

## Assumptions

- `kill(false)` = the real death funnel (`Creature::kill -> doKill`); documented in
  `BTeki::doKill` and confirmed by the prior seam evidence in
  `docs/PIKMIN2_TEKI_LIFETIME_SEAM.md`.
- `same_address` is allocator-dependent, hence reported (`same_address_observed`)
  rather than gated; the seam invariant `registered_before_rebind=0` is the gate.
- The prebuilt `output/p2-dwarf-orange-bank` + `output/p2-dwarf-orange-ref` were reused
  read-only (they match `pc_p2_dwarf_orange`'s file contract).

## Remaining blockers (named provider lane)

- Natural combat death + real corpse/pellet + transport/reward: family lane **13** and
  reward lane **06**; not part of the lifetime seam.
- Deterministic same-address allocator reuse for *this* family: allocator behavior;
  the reclaim seam is in place but the arena's corpse-typed `TEKI_Chappy` keeps the
  killed actor non-removable. No lane dependency — the guard is already integrated.
- Whole scene-exit teardown (`pc_p2_reset_all_teki`) for Dwarf Orange specifically:
  not re-run (already proven at Snow/flora level); lane **01** owns the combined build.

## Subagent usage

- **explore #1 — source audit** (death funnel, `pc_p2_dwarf_orange` keying, seam wiring,
  `kill`/`doKill` signatures, `PelletView` inheritance): used as-is; its finding that a
  corpse-typed `TEKI_Chappy` reaches `doKill` only via corpse disposal (not `kill(false)`)
  directly shaped the probe choice (`kill(false)` for a deterministic synchronous funnel).
- **explore #2 — existing-candidate inventory**: used as-is; confirmed the dedicated
  `P2_FORGET/REUSE/TEARDOWN_PROBE` fixtures were never committed and that
  `pikmin2_kochappy_fixture.py`/`pikmin2_dwarf_orange_reentry.py` were the closest
  committed candidates to model. Chose a new Dwarf-Orange engine-driven probe instead of
  the manager-reset re-entry fixture.
- **general #3 — tests + harness scaffolding**: returned the pytest skeleton with a
  `same_address=1` gate I later corrected to observed-not-gated after the first runtime
  showed `same_address=0`; the module interface and marker contract were otherwise used
  as delivered. Estimated time saved: roughly the full pytest-authoring pass; cost was
  one semantics correction.
- Net: these parallelized the read-heavy audit/inventory/tests so core context stayed on
  the probe C++, the build, and the runtime evidence.

## Exact reproduction

```powershell
$env:PYTHONUTF8 = '1'
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l07 -- `
  py -3.12 -m experimental.pikmin2_dwarf_orange_lifetime run `
    --stage C:/Users/alari/pikmin-randomizer/output/dsw/l07-out/arena/0722b240c86349be853c9bb120f26729 `
    --exe C:/Users/alari/pikmin-randomizer/output/dsw/l07-out/fixture2/baseline/fixture.exe `
    --output C:/Users/alari/pikmin-randomizer/output/dsw/l07-out/run-final `
    --seconds 120
```

Prerequisites (already done once): build `nectar.exe` via
`py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/build_lane.py l07`,
then build the fixture via
`py -3.12 -m experimental.pikmin2_dwarf_orange_lifetime build --native .../native-l07 --build-dir .../native-l07-build --output .../fixture2 --head b805d9c626e4f4558c95aef7cac311a5d9a2068f`.
The arena was staged with
`py -3.12 -m experimental.pikmin2_dwarf_orange_arena --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets --bank C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-bank --profile C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-ref --output .../arena`.
