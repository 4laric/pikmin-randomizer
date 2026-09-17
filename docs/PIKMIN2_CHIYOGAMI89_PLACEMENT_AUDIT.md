# Chiyogami89 retail placement audit (lane enemies-1-chiyogami89-placement-audit)

Closes the recorded missing prerequisite from the completed enemies-1 missing
audit (#653) for source ID 89 (Chiyogami) only. Verdict: **89 is an ordinary
spawnable plant actor**, placed as a `CGT_Plant` generator (weight 2) on
yakushima_2 floor 2. The prior `scenery_usage_unconfirmed` classification is
resolved. Root-only tooling; no runtime, no ADMIT; all six gates UNTESTED.

## Identity anchors (read-only decomp source, never edited)

Research tree `native/pikmin2-research` (file sha256 prefixes shown):

- `include/Game/enemyInfo.h:148`: `EnemyID_Chiyogami = 89` (`0e68be79...`).
- `src/plugProjectYamashitaU/enemyInfo.cpp:85`: info row flags
  `EFlag_HasNoInfo | EFlag_CanBeSpawned | 2 | EFlag_UseOwnID`, no model, no
  child drop, `BDT_Empty` (`305f8260...`). `EFlag_CanBeSpawned` is what lets
  the cave loader resolve the name (see below).
- `src/plugProjectYamashitaU/genEnemy.cpp:551`:
  `GENERATOR_CASE(EnemyID_Chiyogami, ...)` with the retail generator token
  (`36a1d13f...`).
- `src/plugProjectYamashitaU/generalEnemyMgr.cpp:385-386`:
  `mgr = new Chiyogami::Mgr(limit, viewNum);` (`a01db128...`).
- `src/plugProjectMorimuraU/plantsMgr.cpp:428-450`: `Chiyogami::Mgr` derives
  `EnemyMgrBaseAlwaysMovieActor`; `doAlloc` inits `EnemyParmsBase`; `birth`
  delegates to the engine funnel (`02620aa3...`).
- `src/plugProjectKandoU/gameCaveInfo.cpp:66-128` (`TekiInfo::read`):
  the caveinfo name resolves via `getEnemyID(name, EFlag_CanBeSpawned)`,
  then weight and `CaveGenType` are read (`e449bf46...`).
- `include/Game/Cave/Info.h:33-43`: `CGT_Plant = 6` (`8d7b76ef...`).

## Confirmed retail placement (legal ISO, read-only)

- File `user/Mukki/mapunits/caveinfo/yakushima_2.txt`, disc offset 770701016,
  6284 bytes, sha256
  `5a071801508a55ee5d21f5a9e5ff28c085c105a8a9af3eae1467c725c406db15`.
- Floor-2 block (file lines 52-74), unit pool `1_units_large_toy.txt`.
- TekiInfo block (lines 75-94), entry index 7: `Chiyogami 2` (line 92) with
  type 6 `CGT_Plant` (line 93); sibling treasures `g_futa_kyusyu`,
  `cookie_m_l`.
- It is the ONLY `Chiyogami` reference across all 85 retail caveinfo files
  (exhaustive byte scan of the disc directory).

## What this rules out

- Not scenery-only and not a generated/ambient non-actor identity: real
  manager, real birth, real generator case, and a confirmed floor encounter.
- Surface (overworld) placement: unconfirmed; no values invented.

## P1 blockers and owners

1. P1 gate scoping for 89 belongs to a future enemies-1 P1 observer lane
   (broad backlogs #143/#171 are refs, not producers).
2. Flora conversion contract (#171 lane scope) now that placement is proven.

## Adapter, tests, packet

- `experimental/pikmin2_chiyogami89_placement_audit.py`: isolated stdlib
  adapter encoding the row above; `validate_audit` refuses malformed rows;
  `build_packet` emits the machine-readable packet. `--check` and
  `--packet-out` supported.
- `tests/test_pikmin2_chiyogami89_placement_audit.py`: 17 focused tests
  (positive validation/packet plus the malformed/missing-input battery).
- Packet: `out/packet/chiyogami89-packet.json` under this lane output dir
  (generated, hashed in the handoff).