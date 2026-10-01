# Mamuta install + arena (batch 2, issue #221; follows #214)

Implementation owner: Codex using shared account 4laric. Continues
[PIKMIN2_MAMUTA_AUDIT.md](PIKMIN2_MAMUTA_AUDIT.md) and
[PIKMIN2_MAMUTA_BEHAVIOR.md](PIKMIN2_MAMUTA_BEHAVIOR.md). No native hook
wiring changed; hook requests are flagged at the end.

## Install

`experimental/pikmin2_mamuta_install.py` consumes the batch-1 extraction
(`mamuta.json` schema 1) and installs three hash-verified source poses
(`wait` live anchor, last `dead` pose, `attack1` bury-event pose) into the
private run layout at `run/assets/dataDir/courses/pikmin2room/` plus actor
config `run/p2-mamuta-actors.txt`. `plan` rejects before IO: bad actor
counts/IDs, duplicates, wrong schema/species/enemy_id, missing or unconverted
clips, unsafe pose filenames, and pose hash mismatches. `install` refuses
existing targets and non-private room dirs. `verify_install` reloads an
installed layout and proves config and pose bytes match the import.

Reproducibility: two independent arena stagings from the two batch-1
extraction trees produced byte-identical installed artifacts
(`miulin_wait.mod`, `miulin_dead.mod`, `miulin_attack1.mod`,
`p2-mamuta-actors.txt`; manifest compare `identical: True`). Source pose
hashes are those recorded in `output/mamuta-first/imported/mamuta.json`.

## Arena staging

`experimental/pikmin2_mamuta_arena.py` stages a private Impact Site arena
(stage slot chal0, original practice course preserved byte-for-byte) with:

- generator 221001 "P2 Mamuta": native **P1 Miurin** proxy
  (`tekimgr.cpp` tekiNames[24] "miurin", Mamuta — the direct ancestor of P2
  Miulin), engineered position (-150, 30, 1850);
- generator 221002 "P1 Chappy control": ordinary P1 combat enemy at
  (150, 30, 1550).

Private fixture circle-radius-zero birth policy applied to both generators
(engineered choice, recorded in `arena.json`); `p2-cargo-free.txt` satisfies
the preview cargo policy (`native/pc_port/pc_p2_preview_policy.h`). Run dir:
`output/p2-mamuta-arena/5c09e99b8d6e4a109c191c0c055fd025`.

## Native runtime acceptance

Launch: `native/build-randomizer/bin/nectar.exe --experimental-pikmin2-room`,
cwd = run dir, MinGW64 on PATH. The session ran interactively for 90 s with
zero errors before manual termination. Evidence in the run's `native.log`
(hash recorded in `arena.json`).

| Gate | Result |
|---|---|
| native_identity | **PASS (proxy level)**: log shows `tekipara/miurin.bin` (344 B), `tekis/miurin/miurin.mod` (44794 B), `tekikeys/miurin.key`, `tekis/miurin/miurin.anm` (153116 B) loaded; memStat `miurin : 36.46 kbytes`; no asserts/errors |
| natural_AI | PASS (natural-observation fixture: captain entered the territory, proxy covered states `a8`→`17fa8`, closest approach 55.3; [PIKMIN2_MAMUTA_NATURAL.md](PIKMIN2_MAMUTA_NATURAL.md)) |
| bury_attack | PASS (proxy level): natural `P2_MAMUTA_PLANT` flower-stage same-kind events with no forced `InteractBury`; P2 cap/navi/receiver semantics proven separately by the rules fixture |
| flick_collateral | PASS (proxy level): three natural plants in run-06 without injected bury |
| territory_watchdog | PASS (proxy level): the Miurin autonomously engaged the following squad |
| death_corpse | PASS (rules fixture: legal lethal hit, natural death, native `tkmu` carcass; plus natural no-injection kill at tick 957/968; see [PIKMIN2_MAMUTA_DEATH.md](PIKMIN2_MAMUTA_DEATH.md) and [PIKMIN2_MAMUTA_NATURAL.md](PIKMIN2_MAMUTA_NATURAL.md)) |
| day_floor_reset | UNTESTED |
| save_load | UNTESTED |
| piklopedia_observation | UNTESTED |

An earlier staging without the cargo-free marker exited rc=3 with "P2
preview: treasure generator missing"; that failure mode is recorded and
fixed in the arena module.

## Batch-1 trace follow-ups

**Cave generator restore.** Cave floors place enemies through
`MapRoom::placeObjects` (`src/plugProjectKandoU/gameMapParts.cpp:406`):
each `Cave::EnemyNode` (`include/Game/Cave/Node.h:313-339`) births fresh via
`generalEnemyMgr->birth(objectId, arg)` with node position/direction/extra
code (`gameMapParts.cpp:495-533`). The only per-enemy persistence check in
that path is the Waterwraith (`playData->mCaveSaveData.mIsWaterwraithAlive`).
Miulin has no special-casing: a regenerated/restored floor re-births it
fresh, and killed-Miulin state does not persist into floor regeneration.
The Piklopedia kill/stat tracking noted in batch 1 therefore relies on
defeat events at kill time, not on generator restore.

**ShijimiChou side-birth persistence.** `createGroupByEnemy`
(`shijimiChouMgr.cpp:246-269`) births one leader with
`mSpawnSource = SHIJIMISOURCE_Enemy` and raw pointer
`mSpawningEnemy = <Mamuta>`; group members inherit the pointer
(`shijimiChouMgr.cpp:191`). Members hover against the spawning enemy's root
collision sphere (`shijimiChou.cpp:948-950, 1255-1258, 1479-1482`) and leave
Rest for Fly when the spawner is unconstrained
(`shijimiChouState.cpp:55-84`). The pointer is nulled only on init paths
(`shijimiChou.cpp:73,124,265`; leader at `shijimiChouMgr.cpp:83`); no
owner-death cleanup or serialization exists, so the group is a raw-pointer
runtime coupling that re-births with the Mamuta on every spawn/floor
generation — nothing carries across day/floor/save boundaries. An
integration must clear or rebind these references on owner death/reset.

## Hook requests (flagged, not wired)

1. Optional visual bank binding for `miulin_{wait,dead,attack1}.mod` onto the
   P1 Miurin actor, preserving baseline when absent (same pattern as the
   sheargrub/kochappy installs).
2. Fixture/observer hooks for bury conversion (planted → flower sprout,
   99 cap, CKILL_DontCountAsDeath), flick collateral, territory watchdog,
   day/floor reset, save-load, and Piklopedia observation. Until these exist
   the corresponding gates stay UNTESTED.

## Tests

`tests/test_pikmin2_mamuta_install.py` (11 tests) covers plan rejections,
install/verify roundtrip, overwrite refusal, and tamper detection on the
installed artifacts, plus arena contract constants and gates. Combined with
batch 1: 28 lane tests, all passing.
