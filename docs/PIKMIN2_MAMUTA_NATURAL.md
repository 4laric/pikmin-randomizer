# Mamuta natural territory/flick/kill observation (lane 19, #221 / #168)

Implementation owner: Codex using shared account `4laric`. Executing agent:
opencode (deepseek-v4.1-flash), 2026-09-13. Extends
[PIKMIN2_MAMUTA_ARENA.md](PIKMIN2_MAMUTA_ARENA.md) and
[PIKMIN2_MAMUTA_DEATH.md](PIKMIN2_MAMUTA_DEATH.md). No production input, no
maintained checkout and no shared build was modified. Native origin was not
pushed.

## What this closes

The batch-4 rules fixture and the death/corpse fixture both **forced** their
inputs (`InteractBury::actPiki`, a lethal `InteractAttack`). This fixture forces
neither: it stages the same arena + rules marker + explicit 10-red squad, drives
the captain toward the bound P1 Miurin so the squad enters its territory, and
records what the proxy AI does by itself.

`scripts/pikmin2_mamuta_natural_fixture.inc` + `experimental/pikmin2_mamuta_natural_runtime.py`
+ `scripts/pikmin2_mamuta_natural_native.py`.

## Fixture baseline adoption

```text
Fixture baseline adoption
Child issue / lane / implementation owner: #221 / lane 19 natural territory-flick-kill observation / Codex via shared 4laric
Root commit + dirty state / overlay source: opencode/p2-mamuta-natural @ 8b80f0e, clean; base 643d2c9 (contains a51b301 ensure_pikmin_squad); overlay scripts/preview_pikmin2_room.py sha256 4abe0e950a1c7f137572d976ed62fd5a794c079683253a13bde8bfee47762a5a
Native commit + dirty state / worktree / private build directory: native da285dbf75e7c6fbb6d19f8c399dd8f9eb306696, clean; worktree output/native-mamuta-death; build output/native-mamuta-death-build
Squad change present / window change present (ancestry or source evidence): explicit 10-red lane squad staged through the overlay override so ensure_pikmin_squad preserves it (no 20-red top-up); P2_MAMUTA_NATURAL_BIRTH squad=10; 960x540 centered startup via native base 1d5a242b mirrored in tools/preview_p2_room.cpp, launched with PIKMIN_P2_ROOM_WINDOW=960x540
Fresh arena command / run directory / asset and config hashes: py -3.12 -m scripts.pikmin2_mamuta_natural_native --assets <GPIE01 assets> --imported output/mamuta-first/imported --exe output/mamuta-natural-fixture-06/fixture.exe --output output/mamuta-natural-run-06 --timeout 300; run dir output/mamuta-natural-run-06/5d0b37b69334438992266d2f4954153d; native.log sha256 78d86a23c5acae1d93671f4b0616c1d5067e1c323d79113f6891008e0589d96b; arena.json sha256 f2fc0a659694e571cf1b2266669138d8d7b7bd33e07899ecec88920f4052fb53
Executable SHA-256 / fixture provenance status if applicable: 1cbf0950de62ed88c84bba946bd774f9c72f3d52ecec17e5456adb326fe4426a; output/mamuta-natural-fixture-06/instrumentation.json status built (expected native head da285dbf)
Window setting / observed size and centring evidence: PIKMIN_P2_ROOM_WINDOW=960x540; log "[PC Port] Experimental preview window set to 960x540 windowed and centered (override with PIKMIN_P2_ROOM_WINDOW=WxH or =off)."; captures mamuta-natural-approach.ppm / mamuta-natural-final.ppm are 960x540
Live starting Pikmin / active gameplay / no immediate extinction evidence: P2_MAMUTA_NATURAL_BIRTH id=221001 type=24 squad=10 color=red; P2_MAMUTA_NATURAL_APPROACH; active natural combat; no extinction flow
PASS, FAIL, or BLOCKED; remaining work: PASS for this natural observation slice; transport/reward BLOCKED; proxy instability BLOCKER (below)
```

## Accepted run (run-06) and gate classification

Markers from run-06 (`native.log`):

- `P2_MAMUTA_RULES enabled cap=99 navi_damage=5.0 vertical_band=20`
- `P2_MAMUTA_READY generator=221001 native_type=24 xyz=-150,30,1850`
- `P2_MAMUTA_NATURAL_BIRTH id=221001 type=24 squad=10 color=red`
- `P2_MAMUTA_NATURAL_APPROACH_RESULT approached=1 min=55.3 states=00017fa8`
- three natural `P2_MAMUTA_PLANT kind=1 happa=2 planted=0/1/1` lines (no forced bury)
- `P2_MAMUTA_NATURAL_PLANTED planted=3 bury_states=3`
- `P2_MAMUTA_NATURAL_DIED tick=957` and `P2_MAMUTA_NATURAL_CORPSE` (no lethal hit injected)
- `P2_MAMUTA_NATURAL_RESULT died=1 died_tick=957 corpse=1 carried=0 goal=0 control_alive=1 squad=7`
- `P2_MAMUTA_NATURAL_RESET` then `PASS P2_MAMUTA_NATURAL_RUNTIME observe approach reset`

| Gate | Result |
|---|---|
| native_identity | PASS (P1 Miurin proxy) |
| natural_AI / approach | PASS: captain reached the territory, actor covered natural states `a8`→`102a8`→`17fa8`, closest approach 55.3 |
| territory_watchdog | PASS (proxy level): the Miurin autonomously engaged the following squad |
| bury_attack / flick collateral | PASS (proxy level): three natural `P2_MAMUTA_PLANT` events, flower-stage (`happa=2`), same-kind, no forced `InteractBury` |
| natural kill | PASS: the squad killed the actor naturally at tick 957 (no injected damage) |
| death_corpse | PASS: native carryable `tkmu` carcass follows the natural death |
| carry/transport/reward | BLOCKED / UNPROVEN: no natural pickup; the assisted-transport variant could not be completed because of the instability below |
| reset / re-entry (rules) | PASS: `pc_p2_mamuta_forget` + `pc_p2_mamuta_reset` disable the rules; control Chappy unaffected |
| day/floor reset, save-load, Piklopedia | UNTESTED |

## New blocker: intermittent proxy abort during repeated natural attacks

The natural sequence is **not yet stable**. Repeated attack/plant cycles
intermittently abort the proxy with exit `-1` and no diagnostic line, in most
observed failures immediately after the actor reaches the imported `attack1`
anchor (`P2_MAMUTA_DRAW ... anchor=attack1`). The batch-4/5 forced fixtures never
drove the proxy through repeated natural `attack1` draws, so this is newly
exposed by natural observation.

| Run | Fixture | Outcome |
|---|---|---|
| 01 | natural-fixture-01 (approach threshold 45) | completed, approach not counted (min 49.1) |
| 02 | natural-fixture-02 (same source as committed) | **completed** (plants 5, died tick 968) |
| 03 | natural-fixture-03 (+ inactive transport) | aborted ~tick 270, last line `P2_MAMUTA_DRAW anchor=attack1` |
| 04 | natural-fixture-03 | aborted ~tick 600, actor still alive |
| 05 | natural-fixture-02 | aborted before death |
| 06 | natural-fixture-06 (committed source rebuild) | **completed** (plants 3, died tick 957) |

2 of 5 extended natural runs completed. This is tracked as a lane blocker, not a
PASS: a stable acceptance run needs either a diagnosed fix to the `attack1`
anchor draw/anim path (`pc_p2_mamuta_draw` / `Shape::updateAnim` /
`Shape::drawshape` in `pc_port/pc_p2_mamuta.cpp`), or a bounded natural window
that reliably avoids the abort. The completing runs remain valid evidence for
the observed natural bury/kill/corpse behavior; they do not establish stability.

## Tests

`py -3.12 -m pytest tests/test_pikmin2_mamuta_natural.py -q` -> 4 passed.
Validators cover identity/approach/result parsing, honest UNPROVEN
classification when the proxy does not reproduce a behaviour, and rejection of
missing approach/reset and GX desync. Full lane suite
`tests/test_pikmin2_mamuta_{natural,rules,install,binding,assets}.py` remains
green (asset tests skip when the local user-owned assets are absent).

## Remaining (not claimed here)

- Diagnose and fix the intermittent `attack1` abort, then re-run natural
  observation for a stable, repeatable acceptance.
- Natural corpse pickup and Onion/Pod transport (gate 5) once stable.
- Full day/floor reset, save-load, Piklopedia.
- Shared-semantic flags unchanged: ShijimiChou owner-death cleanup,
  material/TEV fidelity.
