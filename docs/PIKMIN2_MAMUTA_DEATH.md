# Mamuta death/corpse runtime gate (existing-mechanics completion, #221)

Lane: existing mechanics completion — one outstanding runtime gate in an
existing P2-mechanics lane. Owner: Codex using the shared `4laric` account.
Parent family: #168 (Reward beetles, Breadbugs, nests and Mamuta); lane issue
#221 (Mamuta P2 bury). This closes the **death_corpse** gate that the batch-4
bury pass left UNTESTED. No new P2 FSM/species behavior is claimed.

## Source contract

- P2 `Miulin` (`native/pikmin2-research`) enters `StateDead`, calls
  `enemy->deathProcedure()` and `kill(nullptr)` after the death keyframe
  (`miulinState.cpp:531-556`).
- `EnemyBase::onInit` enables `EB_LeaveCarcass` (`enemyBase.cpp:1076`); no
  `Miulin` unit disables it (grep of `EB_LeaveCarcass` disables excludes
  `miulin.cpp`), so the source creature leaves a carcass on death.
- The P1 host mirrors this: `TEKI_Miurin` (index 24, type id `tkmu`) has
  `TPI_CorpseType = TEKICORPSE_LeaveCorpse`, a `pelletConfig` entry for
  `tkmu`, and `TAIAdying` spawns the carcass via `PelletView::becomePellet`
  when the death animation finishes. The legacy proxy therefore satisfies the
  gate without a native behavior change.

## Implementation

- The existing opt-in rules fixture (`scripts/pikmin2_mamuta_rules_fixture.inc`)
  gains a death/corpse phase: it verifies the bound actor is not invincible,
  applies one legal lethal `InteractAttack(navi, nullptr, 100000, false)`,
  waits out the death animation, and requires a native alive `Pellet` whose
  `mPelletView` is the bound actor.
- `scripts/pikmin2_mamuta_rules_native.py` validates the death markers and the
  final `PASS ... death corpse ...` line.
- `experimental/pikmin2_mamuta_rules.py`/`arena.py`: the lane's explicit
  10-red starting squad is now staged through the overlay override before
  `overlay()` runs, so the mandatory `ensure_pikmin_squad()` helper sees the
  existing `ikip` record and preserves it instead of adding the default
  20-red squad (fixture baseline adoption).
- Native `tools/preview_p2_room.cpp` main now mirrors `pc_main.cpp`'s
  mandatory small centred preview window (default 960x540, overridable with
  `PIKMIN_P2_ROOM_WINDOW=WxH`) instead of the old hardcoded 960x720. This is
  the custom-fixture entrypoint requirement from
  [PIKMIN2_IMPLEMENTATION_FANOUT.md](PIKMIN2_IMPLEMENTATION_FANOUT.md).

## Fixture baseline adoption

- Root overlay source: contains `preview_pikmin2_room.ensure_pikmin_squad`
  (root `a51b301`).
- Native source: private worktree `output/native-mamuta-death` on
  `opencode/p2-mamuta-death-native` @ `4e58bd2d` (base maintained native
  `1fb98b32`), which contains the experimental-room 960x540 centred startup
  (native `1d5a242b`). Dirty: `M tools/preview_p2_room.cpp` (window parity).
- Private build: `output/native-mamuta-death-build`, `pikmin_pc` 517/517,
  `cmake --build ... -- -n` → `ninja: no work to do.`
- Squad: explicit 10 red (generator 221003) preserved; the helper does not top
  up. Equivalent starting squad documented, not the default 20.

## Run

```powershell
py -3.12 -m scripts.pikmin2_mamuta_rules_native `
  --assets <P1 GPIE01 assets> --imported output/mamuta-first/imported `
  --exe output/mamuta-death-fixture-05/fixture.exe `
  --output output/mamuta-death-run-final2 --timeout 180
```

Environment: `PIKMIN_P2_ROOM_WINDOW=960x540`, `SDL_AUDIODRIVER=dummy`, MinGW64
on `PATH`. Fixture built with
`experimental.pikmin2_mamuta_rules_runtime.build` against `native 4e58bd2d`;
`provenance.json` status `built`.

## Evidence

- Fixture executable SHA-256:
  `aec0d56a630ec1387771e7be99158d6217a1b4b8ccc9577d5171dd569e6da639`
- Run directory:
  `output/mamuta-death-run-final2/ea8518c993374405b6a5e2ad28555eb5`
- `native.log` SHA-256
  `206354ea87ec60cecd965670fd38a99fb56ce8e1770d9d5d546e92eac78700c8`;
  `arena.json` SHA-256
  `f2fc0a659694e571cf1b2266669138d8d7b7bd33e07899ecec88920f4052fb53`.
- Window: `[PC Port] Experimental preview window set to 960x540 windowed and
  centered`.
- Key log lines:
  - `P2_MAMUTA_CARCASS_CONFIG tkmu=1`
  - `P2_MAMUTA_DEATH_CORPSETYPE corpse_type=1`
  - `P2_MAMUTA_DEATH_HIT accepted=1 invincible=0 health_before=2424.8 stored=100000.0`
  - `P2_MAMUTA_DEATH_DIED tick=151 health=0.0`
  - `P2_MAMUTA_DEATH_TRACE tick=270 deadstate=2 pellet=... corpse=1`
  - `P2_MAMUTA_DEATH_PELLETS total=2 withview=1`
  - `P2_MAMUTA_DEATH_RESULT died_tick=151 corpse=1`
  - `PASS P2_MAMUTA_RULES_RUNTIME bury flower_stage cap99 navi_damage5 death corpse reset`
- Screenshots: `mamuta-death-hit.ppm`, `mamuta-corpse.ppm`,
  `mamuta-rules-live.ppm`.

## Gate result (Mamuta arena, gate 4)

| Gate | Result |
|---|---|
| death_corpse | **PASS** — legal non-invincible lethal hit accepted; actor dies (health 0, `mDeadState` 1→2); native carryable carcass pellet appears with `mPelletView == actor`; control survives |
| native_identity | PASS (unchanged) |
| bury_attack (P2 semantics) | PASS (unchanged, opt-in) |
| planted_cap_99 / captain_damage_only / rules_reset | PASS (unchanged) |
| flick_collateral / territory_watchdog | observed-only (not adversarially forced) |
| day_floor_reset / save_load / piklopedia_observation | shared-semantic, still flagged |

## Tests

`py -3.12 -m pytest tests/test_pikmin2_mamuta_rules.py -q` → 11 passed
(covers the preserved-overlay squad staging and the death/corpse validator,
including rejection when the corpse or corpse type is missing).

## Remaining work

- Natural (Pikmin swarm) kill rather than an injected lethal interaction, and
  corpse transport/delivery, remain separate from this gate.
- Flick collateral and territory watchdog still need adversarial probes.
- ShijimiChou owner-death cleanup hazard, day/floor reset and save-load remain
  shared-semantic flags.
- Material fidelity unchanged (partial TEV).
