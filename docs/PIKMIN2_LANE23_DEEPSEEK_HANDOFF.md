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
