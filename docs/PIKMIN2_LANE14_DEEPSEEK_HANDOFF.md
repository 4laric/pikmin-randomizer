# Lane 14 (Ground invertebrates) — DeepSeek handoff

Tracking issue [#165](https://github.com/4laric/pikmin-randomizer/issues/165); parent [#407](https://github.com/4laric/pikmin-randomizer/issues/407).
Implementation owner: Codex through shared account `4laric`; executing agent/session: DeepSeek (lane 14, `dsw/l14-root`).

## Slice delivered

**Source IDs owned / inspected:** Sokkuri 79 (implemented), Armor 15, ElecBug 28,
Imomushi 65, TamagoMushi 68, Hana 84 (audited, unchanged).

**Concrete slice:** Sokkuri (EnemyID 79) — natural-combat **damage** observability
plus the injected death/corpse/cleanup/re-entry chain. Before this slice the
module could not distinguish a naturally-fought death from a fixture-injected
`mHealth=0`; both only logged `P2_SOKKURI_DEAD ... health=0`. The slice adds a
per-frame health tracker so real Pikmin attack damage and the injection signature
are separately observable and honestly labelled.

## Ordered commits

Root base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`; native base
`b805d9c626e4f4558c95aef7cac311a5d9a2068f`. Both clean at handoff.

| Branch | Commit | Subject |
|---|---|---|
| native `deepseek/p2-l14-native` | `3370950c` | Sokkuri death marker reports prior_health for combat-vs-inject distinction (#165) |
| native | `0ec890de` | Sokkuri natural-combat damage/death observability markers (#165) |
| root `deepseek/p2-l14` | `f66624b` | prior_health death marker + separate combat-damage gate (harness+tests+doc) (#165) |
| root | `ae0aca4` | Sokkuri natural-vs-injected death labelling (harness+tests+doc) (#165) |

Dirty state: none (both clean).

## Interfaces / hooks touched and why

Only the family-owned `pc_port/pc_p2_sokkuri.cpp` changed (16 inserts and a
9-line revision). No shared file (`teki.h`, `tekiinteraction.cpp`, `tekibteki.cpp`,
`tekimgr.cpp`, `gameCoreSection.cpp`, `navi.cpp`, `pc_p2_preview.cpp`, CMake) was
edited — the Sokkuri module is already registered and hooked. The change is
read-only observability:

- `P2_SOKKURI_DAMAGE generator=%u source_id=79 health=%.1f` — incremental,
  still-positive health decrease = natural Pikmin attack damage.
- `P2_SOKKURI_DEAD ... health=0 prior_health=%.1f` — health one update before
  death, so a single injection (large `prior_health`) is distinguishable from a
  combat-culminated death (small `prior_health`).

Root: `experimental/pikmin2_ground_lifecycle_behavior.py` (validator +
`combat_damage` gate), `tests/test_pikmin2_ground_lifecycle_behavior.py`
(new tests + native-worktree path resolution), `docs/PIKMIN2_SOKKURI_NATURAL_COMBAT.md`.

## Build evidence (`output/dsw/l14-build-evidence.txt`)

- Native head `3370950c54caf9995d8580af18c4d8c729d6cda9`, clean.
- `nectar.exe` SHA-256 `855e50aeba0ffab7a6cd8915364e24e9261a516aa4a551f7e56ba077325d671f`.
- `ninja -n` → `ninja: no work to do.` (fresh).
- Config: Ninja + MinGW g++ 16.2.0, Release, `PIKMIN_NATIVE_JAUDIO=ON`
  (the OFF default fails to link on `Jac_NoteDemoSkipped`; configured once with
  `-DCMAKE_MAKE_PROGRAM=<python ninja>` then built through `build_lane.py`).
- Private replacement-main fixture `fixture.exe` SHA-256
  `d2df8045d4d7c20b365bae0dc8a568de33ef2bf8fbfe25708281cfed99f9c0bf`
  (`instrumentation.json` status `built`).

## Fixture adoption evidence

- Window: native.log `Experimental preview window set to 960x540 windowed and centered`.
- Live squad: `P2_LIFECYCLE_READY squad=20 sokkuri_gen=346005 armor_gen=346001`.
- No extinction; run exit 0.
- Run dir: `output/dsw/l14-out/run2/2c10ec7097254c3e84f0a1ca957ac935`.

## Six arena gates (Sokkuri 79)

| Gate | Result | Evidence |
|---|---|---|
| 1. Identity + spawn | PASS | `P2_SOKKURI_BIND generator=346005 source_id=79 visual_only=0` |
| 2. Autonomous movement + animation | PASS (source-backed) | `P2_SOKKURI_STATE state=appear/flick`; prior sokkuri run evidence; not re-verified here |
| 3. Attacks / receivers | natural damage PASS; lethal injected | `P2_SOKKURI_DAMAGE health=105.0` (natural squad attack); `P2_LIFECYCLE_INJECT not_natural_combat=1` (lethal step injected) |
| 4. Death + corpse | PASS (injected lethal) | `P2_SOKKURI_DEAD prior_health=105.0`; `P2_LIFECYCLE_CORPSE species=Sokkuri pellet=1` |
| 5. Transport + reward | UNTESTED (deferred #397) | cargo-free arena, no Pod; source carry clip `type5` exists → not source-backed N/A |
| 6. Cleanup + re-entry | PASS (generator re-bind) | `P2_LIFECYCLE_FORGET count=0`; `P2_LIFECYCLE_REENTRY stale=0 fresh=1 count=1` |

Injected vs natural is labelled: injected lethal step is explicit
(`P2_LIFECYCLE_INJECT ... not_natural_combat=1`, `injected=1` completion marker);
natural combat **damage** is separately proven by `P2_SOKKURI_DAMAGE`. A natural
**lethal** death (health fully drained by combat, no injection) is still open.

## Tests

`py -3.12 -m pytest tests/test_pikmin2_{ground_lifecycle,sokkuri,armor,armor_receiver}_behavior.py -q`
→ 40 passed. Full family suite
(`test_pikmin2_{ground*,sokkuri*,armor*,elecbug*,imomushi*,hana*,tamago*}.py`)
→ 112 passed.

## Assumptions

- Incremental health decrease == natural combat damage (Pikmin throw/retaliation);
  a single jump to 0 == injected lethal step (signature: large `prior_health`).
- The cargo-free private arena has no Onion/Pod, so reward is untested (not N/A).
- The Skitter Leaf is harmless (attack params zeroed); its only receiver is Flick,
  so a natural *lethal* kill needs the squad to fully drain 120 HP without the
  fixture's injection — not achieved in this bounded run.

## Remaining blockers (named provider)

- Natural lethal death + true natural re-entry beyond generator `init`: needs lane
  33/07 (lifecycle, #397) and a non-injecting natural-combat fixture; the P1 proxy
  AI alone did not fully drain the enemy within the observation window.
- Actual transport/reward: lane 06 / #397 (Pod/Onion endpoint not present in the
  cargo-free arena).
- Pair discharge (ElecBug 28) and Mitite group births (TamagoMushi 68) remaining
  evidence are tracked separately in this family; ElecBug/Damago modules are
  implemented but not re-exercised here.

## Exact reproduction

```powershell
$env:PYTHONUTF8='1'
py -3.12 -m experimental.pikmin2_ground_lifecycle_behavior run `
  --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets `
  --imported C:/Users/alari/pikmin-randomizer/output/dsw/l14-out/ground `
  --output C:/Users/alari/pikmin-randomizer/output/dsw/l14-out/run-final `
  --exe C:/Users/alari/pikmin-randomizer/output/dsw/l14-out/fixture2/fixture.exe `
  --seconds 150
```

(Prerequisite, already done once: extract `ground` bank
`py -3.12 -m experimental.pikmin2_ground_inverts_assets --iso "<P2 disc>" --source "<pikmin2-research checkout>" --output ...`;
build `fixture.exe` via `... build --native .../native-l14 --build-dir .../native-l14-build --head 3370950c54caf9995d8580af18c4d8c729d6cda9`.)
