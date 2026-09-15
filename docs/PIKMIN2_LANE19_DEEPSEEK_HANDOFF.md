# Lane 19 (Mamuta) DeepSeek handoff — #221 / #168

Implementation owner: Codex via shared account `4laric`. Executing agent: DeepSeek
(`deepseek-v4-pro`), lane 19, 2026-09-14. Root worktree `output/dsw/l19-root` on
`deepseek/p2-l19`; native worktree `output/dsw/native-l19` on
`deepseek/p2-l19-native`. No maintained checkout, shared build, native origin or
upstream GitHub was touched; nothing was pushed.

## Scope chosen (one source ID, one missing slice)

- **Source enemy ID:** Mamuta = `Miulin` (enemy ID 54); native actor is the P1
  proxy `TEKI_Miurin` (24) — the direct ancestor, unchanged P1 proxy behaviour.
- **Missing slice from the ledger:** "extend pinned natural evidence through
  actual transport/reward … and **revisit**" (next-wave goal), i.e. the combined
  head's natural kill/carry/receipt plus the revisit/re-entry gate.
- Outcome: the slice is **BLOCKED** at the natural-kill gate by a combined-head
  combat regression (details + evidence below). The revisit/re-entry + exactly-once
  reward infrastructure is **implemented, unit-tested and ready**; a root install
  regression that blocked Mamuta staging at the approved baseline was **fixed**.

## Source IDs and files owned

- `pc_p2_mamuta.{h,cpp}`, `pc_p2_mamuta_policy.h`, `pc_p2_mamuta_rules.{h,cpp}`
  (native; existing, unchanged this slice).
- Root: `experimental/pikmin2_mamuta_*.py`, `scripts/pikmin2_mamuta_*.{inc,py}`,
  `tests/test_pikmin2_mamuta_*.py` (Mamuta family lane 19).

## Ordered commits (root)

Root base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`; native base/head
`b805d9c626e4f4558c95aef7cac311a5d9a2068f` (clean — **no native commits** this slice).

1. `lane19: restore single-pose static anchors alongside time-sampled pose banks (#221)`
   — `experimental/pikmin2_mamuta_install.py` + `tests/test_pikmin2_mamuta_install.py`.
2. `lane19: Mamuta revisit/re-entry fixture, runner and validator (#221)`
   — `scripts/pikmin2_mamuta_revisit_fixture.inc`,
   `scripts/pikmin2_mamuta_revisit_native.py`, `tests/test_pikmin2_mamuta_revisit.py`.

Dirty state at handoff: clean (both commits applied, nothing staged beyond these).

## What changed and why

### 1. Install regression fix (unblocks staging on the approved baseline)

The approved native baseline `b805d9c6` still loads **three single static anchors**
`miulin_{wait,dead,attack1}.mod` (`pc_p2_mamuta.cpp` + `pc_p2_mamuta_policy.h`
"Static source anchors"), but `pikmin2_mamuta_install.py` had been advanced to a
**time-sampled bank** (`miulin_wait_00.mod`, …) whose native consumer
(`opencode/p2-mamuta-anim` @ `dad4c920`) is **not** integrated. Result: `pc_p2_mamuta_setup`
aborted `P2_MAMUTA invalid profile` (no single `.mod` on disk) — Mamuta could not
stage at all on the current pair. Fix: `plan()` now emits the three single-pose
anchors (`wait` pose 0, last `dead` pose, `attack1` pose 0 — the exact pre-bank
selection from `ce92557`) **in addition to** the banks, so both the static path and
the pending bank path can coexist.

### 2. Revisit/re-entry slice (gate F persistence + gate E re-entry)

- `scripts/pikmin2_mamuta_revisit_fixture.inc` re-enters the SAME Pod-arena stage
  directory after process 1 credited `corpse:mamuta:221001` (`p2-economy.txt`
  persisted, `pokos=2`). A fresh process re-births the Mamuta from the staged
  `default.gen`, re-runs the natural approach/observation, and hard-requires
  `pc_p2_preview_pokos()==initialPokos`, proving the re-delivery is deduped
  (`new=0`) and the reward is neither duplicated nor lost.
- `scripts/pikmin2_mamuta_revisit_native.py` re-runs the exe in an existing staged
  directory and classifies the markers honestly (re-entry identity, natural
  re-kill/corpse/carry, `receipt_deduped`, `reward_not_duplicated`).
- `tests/test_pikmin2_mamuta_revisit.py` covers dedup/duplication/re-entry
  classification and fixture instrumentation.

The revisit runtime is **gated behind the natural kill** (process 1 must actually
credit `corpse:mamuta:221001`), so its runtime evidence is `UNTESTED` here.

## Build evidence (`output/dsw/l19-build-evidence.txt`)

```
2026-09-14T19:08:17 lane=l19 target=pikmin_pc native=b805d9c626e4f4558c95aef7cac311a5d9a2068f dirty=no build_dir=C:\Users\alari\pikmin-randomizer\output\dsw\native-l19-build exe=C:\Users\alari\pikmin-randomizer\output\dsw\native-l19-build\bin\nectar.exe sha256=61fb1c850bd551c8c7c9d07a38e30dbb3ded5faf85ff866cdad7b1108c0b8fa8 ninja_n="ninja: no work to do." seconds=137
```

Release / MinGW g++ 16.2.0 / Ninja / `PIKMIN_NATIVE_JAUDIO=ON`. Fixture builds
(provenance `built`, against native `b805d9c6`):
| fixture | `fixture.exe` SHA-256 |
| --- | --- |
| `mamuta-pod-natural-fixture` (pristine) | `e00e7a26730cddbfc9ce2b51c9fe29029cefc08bb1b4a84f068d99a537a36d74` |
| `mamuta-revisit-fixture` (pristine) | link-validated at `d10a54f171224d712f592f6ebb45e7eaee652e11285e45954f8751908cfde307` (identical committed source); final on-disk relink was starved by build-slot contention and is not needed for the BLOCKED slice (the revisit runtime is gated on gate 4) |

Note: the fixture link is **not bit-reproducible** across identical-source rebuilds
(observed `cc8c2257…` → `e00e7a26…` for the same pristine source under LTO with 85
serial LTRANS jobs), so the committed fixture source + native head are the
authoritative provenance; the recorded SHA is the on-disk built artifact.

## Fixture baseline adoption

```text
Child issue / lane / implementation owner: #221 / lane 19 / Codex via shared 4laric
Root commit + dirty state / overlay source: ef1cace (after lane19 commits) / scripts/preview_pikmin2_room.py ensure_pikmin_squad
Native commit + dirty state / worktree / build: b805d9c6 clean / output/dsw/native-l19 / output/dsw/native-l19-build
Squad change present / window change present: explicit 10-red lane squad staged through overlay override (ensure_pikmin_squad preserves it); 960x540 centred startup via native base 1d5a242b
Fresh arena command / run dir / hashes: py -3.12 -m scripts.pikmin2_mamuta_pod_native --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets --imported output/dsw/l19-out/imported --exe <fixture.exe> --output output/dsw/l19-out/mamuta-pod-accept-natural-02 --pod-package output/dsw/l19-out/pod ; run dir output/dsw/l19-out/mamuta-pod-accept-natural-02/4e903d6a18a94bde80ec60400982a080
Executable SHA-256 / status: pod fixture e00e7a26... ; nectar.exe 61fb1c85... (native head b805d9c6)
Window setting / observed size and centring: PIKMIN_P2_ROOM_WINDOW=960x540; captures are 960x540; "Experimental preview window set to 960x540 windowed and centered" log
Live starting Pikmin / active gameplay / no immediate extinction: P2_MAMUTA_POD_BIRTH id=221001 type=24 squad=10 color=red ; approached=1 ; no extinction flow
PASS / FAIL / BLOCKED: PASS for identity/movement/attacks; BLOCKED for natural kill (see below)
```

## Six arena gates (natural vs injected)

| Gate | Result | Evidence (current head `b805d9c6`) |
| --- | --- | --- |
| 1. Exact identity and spawn | **PASS** (proxy) | `P2_MAMUTA_READY generator=221001 native_type=24`, `P2_MAMUTA_POD_BIRTH id=221001 type=24 squad=10 color=red` |
| 2. Autonomous movement and animation | **PASS** | `approached=1 min=19.9 states=00001ea8`, `P2_MAMUTA_DRAW anchor=attack1` |
| 3. Attacks and receivers | **PASS** (proxy, natural) | natural `P2_MAMUTA_PLANT kind=1 happa=2` (flower-stage), `P2_MAMUTA_NAVI damage=5.0`; no forced `InteractBury` |
| 4. Death and corpse | **BLOCKED** / UNPROVEN | natural kill stalls: health ~2485 → ~70 then frozen; captain buried to 0 health; squad 10→5–8. No `died`. |
| 5. Actual transport and reward | **BLOCKED** | no death → no corpse → no receipt (`pokos=0`) |
| 6. Cleanup and re-entry | **partial PASS** | `P2_MAMUTA_POD_RESET` + `control_alive=1` (reset/forget + control unaffected); revisit infrastructure built+tested but **UNTESTED** at runtime (gated on gate 4) |

Injected state: none. All gate 1–3 observations are natural (no forced health,
bury, or lethal hit). The squad/captain start is the documented fixture placement
(the pod fixture pins the captain to the south approach with `resetPosition`, as in
the accepted prior evidence).

## The blocker (natural-kill regression on the combined head)

Reproduced 3/3 runs on `b805d9c6`: the Mamuta proxy is engaged and damaged
naturally but is never killed. Health drops ~2485→~70, then **freezes**; the
captain is buried to 0 health and 2–5 of the 10 Pikmin are planted, collapsing DPS.

Contrast with the worker build (native `a54f4af2`, `output/mamuta-pod-accept-natural-04/…`):
health drops through ~105→0 and `P2_MAMUTA_POD_DIED tick=466` with only 1 plant
(`squad=9`) — a natural kill. The Mamuta FSM and the P2 bury rules are **unchanged**
(same `pc_p2_mamuta_rules.cpp`, same P1 Miurin proxy), so this is a **shared
behaviour regression**, not a lane-19 family change. Likely providers: lane 01
(integration of the ~272-commit #437 range), lane 08 (sampled animation/clock
changes altering attack/bury cadence), lane 10/13 (shared Piki receiver/attack
hooks added for many #407 source FSMs and the Dwarf-Orange/Purple/White work),
and lane 07 (`a3bec43e` centralizes Teki family forget on death). A 20-red overlay
squad would likely tip the balance, but the lane's 10-red squad is the documented
design, and masking a shared regression with a lane-local squad bump is deferred to
integration.

## Tests

- `py -3.12 -m pytest tests/test_pikmin2_mamuta_*.py -q` → **81 passed, 1 skipped,
  33 subtests** (includes the new `test_pikmin2_mamuta_revisit.py` and the updated
  `test_pikmin2_mamuta_install.py`).

## Assumptions

- The `Miulin` visual is a P1-proxy static anchor (per the approved native
  baseline); the time-sampled bank consumer (`opencode/p2-mamuta-anim`) is out of
  this slice's scope and left for a separate animation-candidate slice.
- `corpse:mamuta:221001` value is 2 (Kochappy `corpseValue` in `p2-pod.txt`),
  matching the prior integrated receipt.
- The natural-kill regression is a shared/combined-head issue; lane 19 is not
  the owner of the shared Piki-receiver/animation-clock code.

## Remaining blockers (named provider)

- Natural kill/carry/receipt on `b805d9c6` → lane **01** (integration) to bisect the
  #437 range with lane **08** (clock) / **10** (receivers) / **13** (Piki combat) / **07** (lifetime).
- Generated/mixed-scene acceptance → lanes **03/05/06/33** (unchanged).
- Day/floor reset, save-load, Piklopedia → shared-semantic, unchanged (flagged since PIKMIN2_MAMUTA_DEATH.md).

## Reproduction

```powershell
cd C:/Users/alari/pikmin-randomizer/output/dsw/l19-root
$env:PYTHONUTF8='1'
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l19 -- `
  py -3.12 -m scripts.pikmin2_mamuta_pod_native `
    --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets `
    --imported C:/Users/alari/pikmin-randomizer/output/dsw/l19-out/imported `
    --exe C:/Users/alari/pikmin-randomizer/output/dsw/l19-out/mamuta-pod-natural-fixture/fixture.exe `
    --output C:/Users/alari/pikmin-randomizer/output/dsw/l19-out/mamuta-pod-accept-natural-04 `
    --pod-package C:/Users/alari/pikmin-randomizer/output/dsw/l19-out/pod `
    --timeout 300
# expect: approached=1, native bury/plant + navi damage, but died=0 (health floor ~70)
#         => natural kill/carry/receipt BLOCKED on combined head b805d9c6
```
