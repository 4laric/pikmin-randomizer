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

## Slice 3

Slice 3 closes the slice-2 draw gaps: **both buds drawn in every FSM pose, from
a confirmed draw.** RedPom had been camera-culled at x=-120 and only wait/shot/
dead, not open/swing/close, were observable on the single Queen that did draw.
The DRAW print also fired before the batch-2 clip-selection, so a pose could be
claimed without the forced clip being found in the bank.

### Source IDs and files owned

Candypop Buds (`BluePom` 3 .. `RandPom` 8, base `Pom` 82), unchanged identity
set from slice 1/2. New/changed files:

- Native: `pc_port/pc_p2_pom.h`, `pc_port/pc_p2_pom.cpp` (source-timed six-state
  walk, confirmed-draw report, per-pose draw logging, host anchor at the planted
  point, dropped the unused `pc_p2_pom_bound`); one shared-file hook
  `pc_port/pc_p2_batch2.cpp` (`pc_p2_pom_report_draw` after the bank-clip check,
  committed separately).
- Root: `experimental/pikmin2_pom_runtime.py` (validator now requires a
  confirmed `P2_POM_DRAW` for BOTH generators in all six poses; both buds moved
  in-frame; REDPOM exhausts its budget so it too reaches `dead`;
  `tests/test_pikmin2_pom_runtime.py` (per-pose flip tests), this doc.

### Ordered commits and dirty state

Root branch `deepseek/p2-l23` (base `ef1cace`, previous head `6aec967`):

1. `6b71122` — `lane23: slice 3 — both buds draw every FSM pose from a confirmed draw; validator + per-pose flip tests (#448)`
2. (this handoff commit)

Native branch `deepseek/p2-l23-native` (base `b805d9c6`, previous head `7d1c6854`):

1. `89d5cc22` — `lane23: slice 3 — observable source-timed FSM pose walk and confirmed-draw report (#448)`
2. `4f0ee053` — `lane23: batch2 hook — report a Pom draw only after the forced clip is found in the bank (#448)` (separate hook commit)
3. `d94a6854` — `lane23: per-pose draw logging so later FSM poses are not capped out of the log (#448)`
4. `b82dc0a9` — `lane23: anchor the bound Chappy host at the bud's planted point so both buds stay in-frame (#448)`

Both worktrees clean at handoff.

### Interfaces / hooks touched and why

- `pc_p2_pom_clip` no longer prints; it only feeds the FSM clip/phase. New
  `pc_p2_pom_report_draw(const BTeki*)` records the "confirmed" draw; the
  batch-2 chain calls it only after `bank.clips.count(forced)` succeeds (i.e.
  the selected clip really exists), so a `P2_POM_DRAW` line claims a rendered
  pose. `pc_p2_pom_bound()` (uncalled) removed.
- `stepBuds` reworked into an explicit source-timed walk (Pom.h:120): `Wait`
  arms to `Open` once the Wait clip is drawn; every touch is a transient `Swing`
  that returns to `Open`; `Open` closes after the remain-open window or a spent
  budget; `Close` routes to `Shot` (or reopen); `Shot` settles its owed sprouts
  then reopens, or dies once the budget is spent. Each state spans at least one
  behavior step, so open/swing/close are now observable instead of collapsing
  into one tick.
- `bindHosts` re-anchors each bound Chappy host at its sidecar point
  (`teki->mSRT.t.set(...)`), matching the source "dropped buds land exactly on
  their point". The conversion slot is already `slotPosition()`, so host and
  receptor coincide.
- Per-pose draw logging: the first 8 draws of each pose are logged (`draws`
  stays monotonic), so a long open wait can no longer exhaust a global draw cap
  and starve the later poses.

### Build / fixture / runtime evidence

- Native `b82dc0a9d94c93782eaacaab5b20c72afb7f8e0f`, clean. Main `nectar.exe`
  SHA-256 `E60F11C120456EB18DDB1FFC4E40C2400CAFE4D7F73469783073F1125CA51AB6`,
  `ninja -n pikmin_pc` "no work to do".
- Fixture `output/dsw/l23-out/pom-fixture-7/build/fixture.exe` SHA-256
  `F85318FD57E0FD2AB56510A910D8627893CA762B972F1CFB9EBCF3AF56A202F1`,
  `provenance.json` status `built`, expected native head `b82dc0a9`.
- GL run `output/dsw/l23-out/pom-runtime-7/pom/c66e6016f6fd4d98813400f4a26ad1a2`
  PASS (exit 0), no leftover process, 960×540 centred window observed. Both buds
  now draw all six poses:

```text
P2_POM_BIND generator=353003 species=RedPom source_id=4 host=teki type=3
P2_POM_BIND generator=353007 species=RandPom source_id=8 host=teki type=3
P2_POM_STATE generator=353003 species=RedPom from=wait to=open
P2_POM_STATE generator=353003 species=RedPom from=open to=swing   (.. swing->open -> close -> shot -> dead)
P2_POM_STATE generator=353007 species=RandPom from=wait to=open
P2_POM_STATE generator=353007 species=RandPom from=open to=swing  (.. swing->open -> close -> shot -> dead)
P2_POM_SPROUT generator=353003 species=RedPom count=6 colour=1 body=1 leaf=1
P2_POM_DEAD generator=353003 species=RedPom used=5 refunds=1 corpse=0 budget=5
P2_POM_CONSERVATION generator=353003 species=RedPom used=5 refunds=1 requested=6 born=6 dead_pikis=0 loss_counted=0
P2_POM_DEAD generator=353007 species=RandPom used=1 refunds=0 corpse=0 budget=1
P2_POM_CONSERVATION generator=353007 species=RandPom used=1 refunds=0 requested=9 born=9 dead_pikis=0 loss_counted=0
PASS P2_POM_NATIVE bind_draw_fsm_walk
```

Both buds emit `P2_POM_DRAW` for `wait/open/swing/close/shot/dead` (RedPom 21
lines, RandPom 19 lines). RedPom's sprout count changed from 2 (slice 2) to 6
because it now accepts five Pikmin to exhaust `ip01=5` (plus one refund).

### Gates that changed

- Gate 2 (movement/animation): the drawn walk is now the full six-pose FSM on
  **both** buds, from a confirmed draw. (Still static/bind pose, no skeletal
  playback — lane 09.)
- Gate 1 / 4 / 5 / 6: unchanged — exact identity/bind, budget-only death,
  conservation `loss_counted=0`, `forget` on despawn — now also evidenced for
  RedPom (it dies with `used=5 refunds=1`).

### Subagent usage

The wave brief required spawning three `task` subagents (2 explore + 1 general)
for source audit, candidate inventory, and test scaffolding, but **no `task`
tool is available in this session's toolset**, so nothing was delegated. All
lane-23 slice-3 work — native FSM rework, host anchor, confirmed-draw hook,
validator/tests, build, GL run and this handoff — was done inline. Net: this was
a dependency-of-the-brief miss, not a choice; the read-heavy audit and test
scaffolding that subagents would have absorbed were instead done directly, and
the slice still completed end-to-end.

### Remaining blockers (provider lane)

- Drawn model is a static bind pose; skeletal playback/material fidelity → lane 09 (#429).
- Ordinary generated-session spawn binding (flora arena is an engineered
  placement vehicle) → lanes 03/04/05.
- Onion/AP seed accounting for sprouts → lane 06.
- Spectralid sentinel spawn → lane 15 (untouched).

### Fixture adoption (fan-out baseline)

- 960×540 centred window observed (`Experimental preview window set to 960x540
  windowed and centered`), `PIKMIN_P2_ROOM_WINDOW=960x540` and `PYTHONUTF8=1`.
- Live starting squad: the batch-2 flora arena overlay supplies 20 red Pikmin;
  the fixture colors seven (1 red refund + 5 blue accepts + 1 yellow) and the
  guard injection is labeled. `P2_POM_FIXTURE_PLAN injected=7` and
  `P2_POM_FIXTURE_SPROUTS n=15` confirm live actors and births.

### Tests run

```text
py -3.12 -m pytest tests/test_pikmin2_pom_runtime.py -q          # 7 passed
py -3.12 -m pytest tests/ -q -k "pom or flora or plant"          # 131 passed, 44 subtests
```

The `drawn` check now requires both generators × six poses; `test_validate_pass_and_fail`
carries a flip test per pose (removing either bud's draw for a pose fails).

### Reproduction

```powershell
$env:PATH='C:\msys64\mingw64\bin;'+$env:PATH
$env:PYTHONUTF8='1'
$env:PIKMIN_P2_ROOM_WINDOW='960x540'
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l23 -- py -3.12 -m experimental.pikmin2_pom_runtime run --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets --imported C:/Users/alari/pikmin-randomizer/output/dsw/l23-out/flora-bank --output C:/Users/alari/pikmin-randomizer/output/dsw/l23-out/pom-runtime-7 --exe C:/Users/alari/pikmin-randomizer/output/dsw/l23-out/pom-fixture-7/build/fixture.exe
```

## Six-gate handoff table (ingest contract)

Candypop Buds. The two runtime-tested identities are `RedPom` (4) and `RandPom`
(8); the other four colour buds (BluePom 3, YellowPom 5, BlackPom 6, WhitePom 7)
share the same converted Pom bank and FSM but are only drawn in the arena, not
driven through death/conversion yet. The animal-facing base `Pom` (82) is
nonspawnable and rejected. Every status below is `injected`: the drawn actor is
the batch-2 Chappy placement vehicle (proxy) and the conversions are driven by
fixture-placed Pikmin, so no gate is claimed as a natural PASS.

### RedPom (Crimson Candypop Bud, source id 4)

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PARTIAL (injected) | output/dsw/l23-out/pom-runtime-10/pom/7f8a5ba0c883425b8c38ffaca436276b/native.log:979 | injected |
| 2. Autonomous movement and animation | PARTIAL (injected) | output/dsw/l23-out/pom-runtime-10/pom/7f8a5ba0c883425b8c38ffaca436276b/native.log:986 | injected |
| 3. Attacks and receivers | PARTIAL (injected) | output/dsw/l23-out/pom-runtime-10/pom/7f8a5ba0c883425b8c38ffaca436276b/native.log:1007 | injected |
| 4. Death and corpse | PARTIAL (injected) | output/dsw/l23-out/pom-runtime-10/pom/7f8a5ba0c883425b8c38ffaca436276b/native.log:1066 | injected |
| 5. Actual transport and reward | UNTESTED (injected) | output/dsw/l23-out/pom-runtime-10/pom/7f8a5ba0c883425b8c38ffaca436276b/native.log:1067 | injected |
| 6. Cleanup and re-entry | UNTESTED (injected) | output/dsw/l23-out/pom-runtime-10/pom/7f8a5ba0c883425b8c38ffaca436276b/native.log:1094 | injected |

### RandPom (Queen Candypop Bud, source id 8)

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PARTIAL (injected) | output/dsw/l23-out/pom-runtime-10/pom/7f8a5ba0c883425b8c38ffaca436276b/native.log:980 | injected |
| 2. Autonomous movement and animation | PARTIAL (injected) | output/dsw/l23-out/pom-runtime-10/pom/7f8a5ba0c883425b8c38ffaca436276b/native.log:987 | injected |
| 3. Attacks and receivers | PARTIAL (injected) | output/dsw/l23-out/pom-runtime-10/pom/7f8a5ba0c883425b8c38ffaca436276b/native.log:1014 | injected |
| 4. Death and corpse | PARTIAL (injected) | output/dsw/l23-out/pom-runtime-10/pom/7f8a5ba0c883425b8c38ffaca436276b/native.log:1074 | injected |
| 5. Actual transport and reward | UNTESTED (injected) | output/dsw/l23-out/pom-runtime-10/pom/7f8a5ba0c883425b8c38ffaca436276b/native.log:1075 | injected |
| 6. Cleanup and re-entry | UNTESTED (injected) | output/dsw/l23-out/pom-runtime-10/pom/7f8a5ba0c883425b8c38ffaca436276b/native.log:1094 | injected |

## Review fixes 3

The slice-3 handoff was reviewed **NOT merged**: noted a blocking native
regression (Wait gated the arm on `draws`, so an off-camera/culled bud never
armed) plus one-shot Swing/Close timing, a draw-report placement gap, a one-shot
host anchor, and validator/test/doc gaps. Fixed on this branch.

### Native fixes (`deepseek/p2-l23-native`, base `b82dc0a9`)

1. `103d15c2` — **source-timed Walk/Swing/Close/Shot holds**: `Wait` arms after
   one SimTick (not a confirmed draw); `Swing`/`Close`/`Shot` hold their source
   clip lengths (type4=20, type2=30, type3=40 behavior steps) so transient poses
   are drawn across frames, not a single catch-up step. `bindHosts` re-anchors
   the bound Chappy host every tick. `pc_p2_pom_report_draw` moved to just before
   `shape->drawshape`, gated on `name == forcedClip` (the clip actually about to
   render).
2. `71163d6a` — increment `stateTicks` after the switch, so a newly-entered state
   keeps its clip observable for the frame's draw (Wait is drawn once).
3. `8eb03c49` — prime the sim clock on the first tick, so the setup-pause (movie
   skip / preview) does not accrue as catch-up steps that collapse the one-tick
   Wait arm into the bind frame.

### Root fixes (`deepseek/p2-l23`, base `ce18398`)

- `bb1fd20` — validator now requires **RedPom's** `P2_POM_DEAD` (`used=5
  refunds=1 corpse=0 budget=5`) and `P2_POM_CONSERVATION` (`requested=6 born=6`)
  in addition to the Queen's; `test_validate_pass_and_fail` flips each bud's
  `P2_POM_DRAW` line separately per pose; `docs/PIKMIN2_POM_NATIVE.md` drops the
  stale `drawn=1`, documents the per-pose draw cap and `pc_p2_pom_report_draw`,
  and records the full six-pose walk.

### Build / fixture / runtime evidence

- Native `8eb03c490fdb76e310834add9e732d3739659e50`, clean. `nectar.exe`
  SHA-256 `5BC7E473BF8C03EF79AB55EA11A54A43AA8A8CF1EA8157D4E5997A41EBD596DE`,
  `ninja -n pikmin_pc` "no work to do".
- Fixture `output/dsw/l23-out/pom-fixture-10/build/fixture.exe` SHA-256
  `B7AFA0DBED174F5DEBBE1AA130095C7F157F181A9BAEEAE0585546323B65AD69`,
  `provenance.json` status `built`, expected native head `8eb03c49`.
- GL run `output/dsw/l23-out/pom-runtime-10/pom/7f8a5ba0c883425b8c38ffaca436276b`
  PASS (exit 0), 17/17 checks, no leftover process, 960×540 centred window. The
  Wait pose is now drawn (lines 986/987) before the arm; RedPom and Queen each
  reach `DEAD`/`CONSERVATION` (`loss_counted=0`).

### Six-gate table checker

`py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_LANE23_DEEPSEEK_HANDOFF.md`
(exit 0):

```text
3 BluePom (role=plant): ignored (role)
4 RedPom (role=plant): ignored (role)
5 YellowPom (role=plant): ignored (role)
6 BlackPom (role=plant): ignored (role)
7 WhitePom (role=plant): ignored (role)
8 RandPom (role=plant): ignored (role)
```

The checker ran against the wave-branch `experimental/pikmin2_enemy_roster.py`
(the local copy was older and lacked `NONNATURAL_MARKERS`/`admission_requirements`).
It reports no refusals; the six Candypop identities are classified `role=plant`
in the roster, so the deny-by-default ingest does not treat them as seedable
enemy identities and neither advances nor refuses any gate. The six-gate tables
above are retained for traceability.
