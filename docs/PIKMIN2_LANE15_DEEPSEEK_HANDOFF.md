# Lane 15 — DeepSeek handoff: real Honeywisp carried-Egg reward (#166)

Implementation owner: Codex via shared account `4laric`. Executing
agent/session: DeepSeek (deepseek-v4-pro). This handoff records ONE slice and is
not full-lane or whole-family sign-off.

## Slice delivered

**Source ID owned: `EnemyID_Qurione` (16, Honeywisp).** One missing end-to-end
slice closed at the implementation/contract level: **real carried-Egg reward
ownership**. The integrated `pc_p2_qurione` module previously printed
`P2_QURIONE_EGG action=attach|drop` markers only, with the comment "the shared
Egg projectile is owned by lane 20" and no physical reward. This slice reuses the
integrated lane-20 `P2Egg` policy (`pc_p2_egg_hazard.*`) — a *consumer*, not a
reimplementation:
- bind: `P2Egg::birth(false)` + `onStartCapture()` → a real carried Egg;
- Drop (`damage` clip drop-fraction, recorded adaptation): `onEndCapture()`;
- released Egg falls under bounded host gravity, `bounce()` on floor contact
  (health 0), then `P2Egg::update()` builds the source drop table and births real
  P1 items: single/double nectar via `itemMgr->birth(OBJTYPE_Water)` (ItemHoney
  HONEY_Y), pellets via `pelletMgr->newNumberPellet(...)`, mitites downgrade to
  nectar (no P1 Mitite manager). Spicy/Bitter stay unsupported (first-spray demo
  flag). Disc Egg parms (fp01..fp05, health 50) are hardcoded from the source and
  never invented.

Source references: `Qurione.cpp` (attachItem/dropItem), `QurioneState.cpp`
(Drop KEYEVENT_2), `egg.cpp`/`eggState.cpp` (bounce/genItem); decomp revision
`632af93787b9c95b63f0c13be32b161375ce3a96`.

## Source IDs and files owned

- Native worktree `output/dsw/native-l15` (branch `deepseek/p2-l15-native`):
  - `pc_port/pc_p2_qurione.cpp` (only file changed). New markers emitted:
    `P2_QURIONE_EGG_REAL ... born=1 drop_group=0`, `... released=1`,
    `P2_QURIONE_EGG_BOUNCE`, `P2_QURIONE_EGG_BREAK`, `P2_QURIONE_EGG_ITEM`.
- Root worktree `output/dsw/l15-root` (branch `deepseek/p2-l15`):
  - `experimental/pikmin2_qurione_lifecycle.py` (REWARD real markers; validator
    `reward_real` sub-check; `transport_reward` gate updated to pass)
  - `experimental/pikmin2_qurione_arena.py`, `..._install.py`, `..._runtime.py`
    (metadata/evidence strings updated)
  - `tests/test_pikmin2_qurione_lifecycle.py` (2 new tests + REWARD assertions)

No shared-file edits (`teki.h`, `tekiinteraction.cpp`, `tekibteki.cpp`,
`tekimgr.cpp`, `gameCoreSection.cpp`, `navi.cpp`, `pc_p2_preview.cpp`, CMake) in
this slice. No hooks added or shared semantics changed.

## Ordered commits

Root (base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`):
1. `a89996b` lane15: grade real carried-Egg reward in Qurione lifecycle contract (#166)

Native (base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`):
1. `d1a579f3` lane15: Qurione carries real Egg reward via lane-20 P2Egg policy (#166)

Both worktrees clean at handoff (no dirty state).

## Interfaces / hooks touched

None new. The slice consumes the already-integrated lane-20 `P2Egg` primitive and
the P1 `itemMgr`/`pelletMgr` birth interfaces. Existing Qurione hooks
(`pc_p2_qurione_update`/`suppress_ai`/`draw`/`param_f`/`reset`/`forget`) were
already integrated and are unchanged.

## Build evidence (`output/dsw/l15-build-evidence.txt`)

- Configured with Ninja + MinGW g++ 16.2.0, Release, `-DPIKMIN_NATIVE_JAUDIO=ON`
  (the OFF default fails to link on `Jac_NoteDemoSkipped`; see
  docs/PIKMIN2_IMPLEMENTATION_FANOUT.md §Private builds).
- Native head `d1a579f34a08f15ce3a870708ba4ff25e45c3319`, dirty=no.
- `nectar.exe` SHA-256 `ef0ac8b97c5832ad539bea1c059157585cc2442d584a5a5787c6f724913ce9eb`.
- `cmake --build ... --target pikmin_pc -- -n` → `ninja: no work to do.`

## Fixture adoption evidence

- Fresh Qurione arena regenerated into `output/dsw/l15-out/arena-runs/504bde766a2d46ecbda0f6f754217a49`
  (bank from `output/dsw/l15-out/qurione-bank`, `qurione.json` SHA-256
  `86ac5aa8f1d2a110badc15e01e2f7264a972fc1d35f0159277628c5d93903934`).
- Log witnesses:
  - `[PC Port] Experimental preview window set to 960x540 windowed and centered`
  - `[Pikipelago] P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1`
  - `[BBFT] Direct boot: Forest of Hope day 2, 20 reds`
  - `P2_QURIONE_BIND generator=203001 source_id=16 visual_only=0`
  - `P2_ENEMY_READY species=Qurione ... health=9999.0 ... reward=P2_Egg`
  - `P2_QURIONE_EGG generator=203001 action=attach`
  - `P2_QURIONE_EGG_REAL generator=203001 born=1 drop_group=0`  ← new
- No `Extinction`; 20 live reds confirmed.

## Six-gate table (natural vs injected)

| Gate | Result | Evidence / note |
|---|---|---|
| 1 identity/spawn | **PASS** (natural) | `source_id=16`, birth XYZ matched, validated assets, no P1 fallback |
| 2 movement/animation | **BLOCKED** | wisp `mSRT.t` → NaN within ~1 s at base `b805d9c6`; it never leaves STAY. Pre-existing shared traceMove regression, not this slice. |
| 3 attacks/receivers | source-backed N/A | Honeywisp has no attack; contact trigger is `flyCollisionCallBack`. |
| 4 death/corpse | **UNTESTED** | drop->dead fly-away cannot be reached while movement is blocked (#2). |
| 5 transport/reward | **PARTIAL** | Egg **attach + real born** observed live (`born=1`). Release/fall/break/item-birth code is complete and contract-tested but the natural `drop` cannot fire while #2 blocks contact. |
| 6 cleanup/re-entry | **UNTESTED** | requires a death path (#2/#4); shared #397 lifecycle seam. |

Injected state: none. All observations are natural engine execution; no health,
animation or event was forced.

## Tests

`py -3.12 -m pytest tests/test_pikmin2_qurione_lifecycle.py -q` → **17 passed**
(was 15; added real-Egg reward detection + proxy-log negative test).

Full flying-family suite:
`py -3.12 -m pytest tests/test_pikmin2_{qurione_lifecycle,qurione_assets,qurione_install,qurione_runtime,flying_assets,flying_install,mar_behavior,shijimi_behavior,shijimi_install}.py -q`
→ **79 passed, 14 subtests**.

## Assumptions

- Reusing lane-20 `P2Egg` as a policy object is a legitimate consumer (the module
  header itself states "a future host integration owns capture/fall physics, the
  item/pellet births" — this slice is that host integration for the Honeywisp).
- Because the P1 engine has no physical Egg creature, the released Egg is a
  policy object whose break births real items; there is no "haul Egg to nest"
  step (correct: P2 Eggs break on floor impact, they are not hauled).
- Host gravity/terminal fall are bounded approximations (documented constants).

## Remaining blockers (provider lane)

1. **Natural drop→break→birth runtime** is blocked by a flying-teki position NaN
   in the shared movement/collision path at base `b805d9c6`. Diagnostic evidence
   from a temporary instrumented build: `colrad=16.00 vy=0.0000 flying=1` yet
   `mSRT.t=nan` after ~1 s, i.e. `MapMgr::traceMove` returns NaN for a valid
   airborne teki. This is a regression versus the previously-validated Qurione
   runtime (`docs/pikmin2-qurione-runtime.md`, base `b602d8c4`); provider is the
   shared engine/collision owner (lane 01 integration; the `Fix P2 hauling
   against internal coplanar floor seams` / Jellyfloat-flight work sits in the
   lineage). Lane 15's module position/movement code is byte-identical to the
   previously-working version (`git blame`: last changed `9077eb33`).
2. Cleanup/re-entry: #397 shared lifecycle seam.

## Exact reproduction command

```powershell
# native worktree already configured (JAUDIO ON) and built at d1a579f3
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/build_lane.py l15

# regenerate bank + arena (root worktree)
$env:PYTHONUTF8='1'
py -3.12 -m experimental.pikmin2_qurione_assets --iso "C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso" --output "C:/Users/alari/pikmin-randomizer/output/dsw/l15-out/qurione-bank" --pose-limit 4
py -3.12 -m experimental.pikmin2_qurione_arena --assets "C:/Users/alari/bbft/dist/cohesion/pikmin/assets" --bank "C:/Users/alari/pikmin-randomizer/output/dsw/l15-out/qurione-bank" --output "C:/Users/alari/pikmin-randomizer/output/dsw/l15-out/arena-runs" --source-sha256 "86ac5aa8f1d2a110badc15e01e2f7264a972fc1d35f0159277628c5d93903934"

# runtime (GL slot, 30 s)
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l15 -- py -3.12 run_fixture.py "C:/Users/alari/pikmin-randomizer/output/dsw/native-l15-build/bin/nectar.exe" "<arena-run-dir>" "<arena-run-dir>/qurione-run.log" 30
```

Notes: `run_fixture.py` (in `output/dsw/l15-out/`) sets `PIKMIN_P2_ROOM_WINDOW=960x540`,
`PYTHONUTF8=1`, and prepends the MinGW bin to PATH. The private output dir links a
read-only junction `native/pikmin2-research` → the shared decomp checkout so the
asset extractor can hash its source files.
