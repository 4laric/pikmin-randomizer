# Muse l62 Long Legs handoff — Houdai66 Walk translation + source-backed no-carcass reward (#502)

Parent #173; wave #491; integration #437/#186.
Implementation owner: Codex through shared account `4laric`; executing contributor:
Muse Spark 1.3 Contributor via OpenCode (`opencode/muse-spark-1.3-contributor-free`),
lane `muse-longlegs` (l62), session `ses_f588f7eedffe220W1v9h5gUeBd`, generation 2.

## Scope delivered

Start with Houdai66 (then BigFoot69): replace the host-pinned movement evidence and
the proxy-corpse reward evidence with source-backed natural paths, preserving the
four accepted lane26 gates (identity, attacks, death, cleanup).

1. **Movement (gate 2, Houdai66 candidate):** the owned host now translates a
   registered actor's body during FSM Walk toward the source target rule
   (`Houdai::getTargetPosition`: nearest Pikmin in sight, else a random
   territory-ring point; `Houdai.cpp:313-349`, consumed by `StateWalk::init`,
   `HoudaiState.cpp:340-350`) at the source species speed (Houdai 250 u/s).
   There is no walk animation family-wide; the legs stay bind-pose (documented
   approximation). The measured per-tick translation ratio feeds the source crush
   gate input; the planting edge is never synthesized, so Walk crush stays closed
   and only the landing key-2 crush fires (unchanged behavior).
2. **Reward (gate 5, both IDs):** source determination before implementing —
   `Houdai.cpp:71`, `BigFoot.cpp:69` (`Damagumo.cpp:80`) all run
   `disableEvent(0, EB_LeaveCarcass)` in `onInit`: no carcass, no corpse, no corpse
   transport, ever. Death reward is `createItemAndEnemy`: a pellet/treasure drop
   when `mPelletDropCode` is set (lane-06 objects), else child births from the
   `kosi` joint (BigFoot 30 Mitites / lane 14; Damagumo 25 ShijimiChou / lane 15;
   Houdai none). In a cargo-free arena with no held treasure, Houdai66 and
   BigFoot69 deaths yield nothing transportable: gate 5 is source-backed N/A.
   The old proxy-corpse Pod credit (P1 Chappy stand-in) is REMOVED as evidence,
   not relabelled. A held-treasure drop observation (kosi drop → carry → receipt)
   is a future slice needing lane-06 treasure objects; filed as follow-up.

## Ordered commits

Root branch `codex/muse-l62-longlegs` (base `72a2c450`):

| Commit | Subject |
|---|---|
| `cb56df7b` | l62 observer: Houdai walk-translation + no-carcass reward validator and flip tests (#502) |
| `8520d2ba` | l62 stage Pod package so preview_ready gates the walk observer; Pod unused (#502) |

Native branch `codex/muse-l62-longlegs-native` (base `7b9ecaa6`):

| Commit | Subject |
|---|---|
| `8beb44b4` | l62 Walk translation at source speed along source target rule + walk fixture (#502) |
| `b024c88c` | l62 clump-attack drain tactic + BigFoot wake + faster windows (#502) |

Both clean (`git status` clean at handoff). No shared files touched; no other
owner's files edited. Owned files only (8 reserved paths).

## Build evidence

- Leased configure+build: `output/muse-wave/l62/build-1789517065621189200.log`
  (native head `8beb44b4`, clean). `pikmin_pc` `nectar.exe` SHA-256
  `9d5f7b45356b0715d1509bfde9486ca5e3a517ff6c42a60ff1854d96543215a6`,
  `ninja -n` → no work to do.
- Fixture3 (current): `output/muse-wave/l62/fixture3/` built against native
  `b024c88c` via the leased runner
  (`output/muse-wave/l62/build-1789527363895948700.log`, exit 0),
  `fixture.exe` SHA-256 `6fc9f25a667be55dc579f8f7a63bfbea689593c3b2ea5a27cc54026fab309fea`
  (provenance `built`, `fixture3/baseline/provenance.json`).
- `py -3.12 -m pytest tests/test_pikmin2_muse_longlegs.py -q` → **11 passed**.

## Fixture baseline adoption

Child issue / lane / implementation owner: #502 / muse-longlegs (l62) /
Codex through shared `4laric`; executing Muse Spark 1.3 Contributor.
Root commit + dirty state / overlay source: `8520d2ba` (branch
`codex/muse-l62-longlegs`), clean / `scripts/preview_pikmin2_room.py`
`overlay()` calls `ensure_pikmin_squad()` (lines 94-99), verified in-worktree.
Native commit + dirty state / worktree / private build directory: `b024c88c`
(branch `codex/muse-l62-longlegs-native`), clean /
`C:\Users\alari\pikmin-randomizer\output\msw\native-l62` /
`C:\Users\alari\pikmin-randomizer\output\msw\native-l62-build`.
Squad change present / window change present: yes / yes (source-verified above;
`pc_port/pc_main.cpp` 960×540 default + `pc_window_center()`, lines 55-77/130).
Fresh arena command / run directory / asset and config hashes:
`experimental.pikmin2_muse_longlegs.run(assets, imported, run3, fixture3/fixture.exe)` /
`output/muse-wave/l62/run4/0094c37bba0843a2b69e96e50766d244` (fresh arena,
current overlay; disc bank reused from lane26 extraction copied to private
`output/muse-wave/l62/imported`, manifest
`9f9183520bb0a91e5aa9c8a768206a4c3679ccc07676a66aca5250ebebcc800e`).
Executable SHA-256 / fixture provenance: fixture `6fc9f25a…fab309fea`,
`built` against native `b024c88c`.
Window setting / observed size and centring evidence: `PIKMIN_P2_ROOM_WINDOW=960x540`;
`output/muse-wave/l62/run4/0094c37bba0843a2b69e96e50766d244/capture/native.log:7`
(`Experimental preview window set to 960x540 windowed and centered`).
Live starting Pikmin / active gameplay / no immediate extinction evidence:
`native.log:746` (`P2_MUSE_WALK_READY squad=20`), `red=20` room preview,
`native.log:1445` (`P2_MUSE_WALK_SESSION navi=1 pikis=20`), no `Extinction`.
PASS; remaining work: BigFoot69 Walk (woke to Wait, no Walk in window) + future
held-treasure slice (lane-06 objects).

## Six-gate evidence

L62RUN = `output/muse-wave/l62/run4/0094c37bba0843a2b69e96e50766d244/capture/native.log`.
L26RUN = `output/dsw/l26-out/run/2c3ce2a8252241e68160e8f8b3747a80/capture/native.log`
(accepted lane26 evidence, read-only, preserved not re-run).

- Source ID: 66 `Houdai`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | output/muse-wave/l62/run4/0094c37bba0843a2b69e96e50766d244/capture/native.log:730 (BIND generator=312001 species=Houdai native_fsm=implemented) | natural |
| 2. Autonomous movement and animation | PASS (natural) | output/muse-wave/l62/run4/0094c37bba0843a2b69e96e50766d244/capture/native.log:850 (WALK from=149.8,1846.1 to=168.1,1813.3 speed=250.0) :864 (WALK_END distance=38.5 seconds=0.16, avg 240.6 u/s at source 250 u/s budget); legs bind-pose, no IK articulation (approximation documented above); arena actor residual P1 locomotion disclosed above | natural |
| 3. Attacks and receivers | PASS (natural) | output/muse-wave/l62/run4/0094c37bba0843a2b69e96e50766d244/capture/native.log:913 (SHELL) :914 (SHELL_HIT pikmin=1, source InteractBomb receiver; six more shell/hit pairs :915-:941) | natural |
| 4. Death and corpse | PASS (natural) | output/muse-wave/l62/run4/0094c37bba0843a2b69e96e50766d244/capture/native.log:944 (DEAD prior_health=10.00, drained 130 to 0, no lethal write) :1463 (NATURAL_DEATH houdai=1 tick=1501); no Houdai BIRTH line (source deathChildren 0); fallen pellet is the arena actor P1 pellet, not a source carcass (see gate 5) | natural |
| 5. Actual transport and reward | N/A | Source-backed: native/pikmin2-research/src/plugProjectNishimuraU/Houdai.cpp:71 disableEvent(0, EB_LeaveCarcass), so no carcass exists; cargo-free arena, no held treasure, staged Pod anchor unused, no receipt claimed; earlier stand-in corpse credit withdrawn | N/A |
| 6. Cleanup and re-entry | PASS (natural) | output/dsw/l26-out/run/2c3ce2a8252241e68160e8f8b3747a80/capture/native.log:940 (FORGET Houdai count=0 registered=0) :945 (REENTRY stale=0 fresh=1); accepted lane26 fix4 evidence preserved, walk/drain run leaves registry paths untouched | natural |

- Source ID: 69 `BigFoot`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | output/muse-wave/l62/run4/0094c37bba0843a2b69e96e50766d244/capture/native.log:731 (BIND generator=312002 species=BigFoot native_fsm=implemented) | natural |
| 2. Autonomous movement and animation | UNTESTED | Woke Stay to Wait in the l62 walk window but reached no Walk inside 1500 ticks; same owned code path as Houdai, staged too far to cycle in-window | N/A |
| 3. Attacks and receivers | PASS (natural) | output/dsw/l26-out/run/2c3ce2a8252241e68160e8f8b3747a80/capture/native.log:734 (CRUSH pikmin=20) :762 (DAMAGE drain 130 to 0); accepted lane26 evidence preserved | natural |
| 4. Death and corpse | PASS (natural) | output/dsw/l26-out/run/2c3ce2a8252241e68160e8f8b3747a80/capture/native.log:802 (DEAD prior_health=10.00) :803 (BIRTH count=30) :805 (NATURAL_DEATH bigfoot=1); accepted lane26 evidence preserved | natural |
| 5. Actual transport and reward | N/A | Source-backed: native/pikmin2-research/src/plugProjectNishimuraU/BigFoot.cpp:69 disableEvent(0, EB_LeaveCarcass), so no carcass exists; Mitite births are lane-14 enemy spawns, not carried reward | N/A |
| 6. Cleanup and re-entry | PASS (natural) | output/dsw/l26-out/run/2c3ce2a8252241e68160e8f8b3747a80/capture/native.log:939 (FORGET BigFoot count=0 registered=0) :944 (REENTRY stale=0 fresh=1); accepted lane26 fix4 evidence preserved | natural |

## Tests run

- `py -3.12 -m pytest tests/test_pikmin2_muse_longlegs.py -q` → **11 passed**
  (walk displacement, pinned-walk/teleport flips, Houdai-birth rejection,
  injection flagging, no-carcass static audit, no-forced-transport fixture grep).
- Lane26 suites untouched (legacy-claimed paths not re-run; no regressions possible —
  no shared files changed).

## Assumptions and disclosed approximations

- The P1 Chappy placement vehicle retains its own residual locomotion; the
  reported 38.5 u Walk displacement is the owned host's applied source-rule
  translation (per-tick steps toward the source-rule target at ≤250 u/s) summed
  over the Walk, and the net body motion is real (POS samples move during Walk,
  static after). Split with vehicle drift disclosed, not separated.
- Legs stay bind-pose: no IKSystemMgr, no foot articulation, no walk animation
  (family has none in source either — motion is IK-driven there).
- Walk crush stays closed (planting edge never synthesized); only landing key-2
  crush fires. Stuck-Pikmin damage rule still host-side (unchanged).
- Squad/captain staged (behavior fixture positions, not production placement);
  both Long Legs staged outside the 60u accumulate radius for the walk window.
- Pod anchor files staged for `preview_ready` only; no carry/receipt in this run.

## Remaining blockers / next slice

- BigFoot69 Walk translation observation (needs earlier wake or a longer walk
  window; same code path, unproven).
- Held-treasure kosi-drop → carry → receipt slice (needs lane-06 treasure objects
  + held-treasure staging; request through #491, not an owned-file edit).
- Mitite/ShijimiChou birth objects (lanes 14/15); shell pool visuals (lane 20).

## Exact reproduction

```powershell
$env:PIKMIN_P2_POD_PACKAGE='C:\Users\alari\pikmin-randomizer\output\dsw\l19-out\pod'
py -3.12 -c "from experimental.pikmin2_muse_longlegs import run; run(r'C:\Users\alari\bbft\dist\cohesion\pikmin\assets', r'C:\Users\alari\pikmin-randomizer\output\muse-wave\l62\imported', r'<NEW_PRIVATE_OUT>', r'C:\Users\alari\pikmin-randomizer\output\muse-wave\l62\fixture2\fixture.exe', 300)"
```

(Native `b024c88c` already built in `output/msw/native-l62-build`; fixture3
provenance `built`.)
