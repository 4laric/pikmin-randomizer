# Chappy siblings pin registry (source-45 YellowKochappy, source-53 KingChappy; #810)

Read-only pin-audit for lane `chappy-siblings-pin-audit` (issue #810).
Consumes the DONE KumaChappy35-P0 handoff and the LeafChappy67 bridge staging
(#774, done) read-only; never duplicates them. No engine edits, builds,
runtime runs, shared edits or ADMIT. All six gates UNTESTED.

## Research pins (verified read-only)

### Source-45 YellowKochappy (Snow Bulborb)

- `include/Game/Entities/YellowKochappy.h`: `struct Obj : KochappyBase::Obj`,
  `struct Mgr : KochappyBase::Mgr`; NO dedicated StateID enum (reuses the
  KochappyBase FSM).
- `src/plugProjectYamashitaU/YellowKochappy.cpp` + `YellowKochappyMgr.cpp`
  (Mgr:8 snow texture swap `cKochappyChangeTexName`); family
  `KochappyBase`, `kochappyState`, `kochappyAnimator`, `kochappyMgr`.
- `src/plugProjectYamashitaU/enemyInfo.cpp:13`: YellowKochappy row,
  model bank `Kochappy`; `include/Game/enemyInfo.h:104`
  `EnemyID_YellowKochappy = 45`.

### Source-53 KingChappy (Emperor Bulblax)

- `include/Game/Entities/KingChappy.h:22-29` (`KINGCHAPPY_Walk/Attack/Dead/
  Flick/WarCry/Damage`, dedicated boss FSM), `:318` (`AnimID`).
- `src/plugProjectMorimuraU/kingChappy.cpp` + `kingChappyMgr.cpp`
  (Mgr:9 `kingChappyMgrName`) + `kingChappyState.cpp`.
- `src/plugProjectYamashitaU/enemyInfo.cpp:87`: KingChappy row,
  `BDT_Boss`, no model bank; `include/Game/enemyInfo.h:112`
  `EnemyID_KingChappy = 53`.

## Maintained-wave binding inventory (verbatim absence where absent)

- Family base `native/pc_port/pc_p2_kochappy.{h,cpp}` PRESENT but binds
  source-1 Kochappy only (`P2_ENEMY_READY species=Kochappy source_id=1`);
  NO Yellow/King variant dispatch.
- NO `pc_p2_yellowkochappy.*` and NO `pc_p2_kingchappy.*` port modules:
  verbatim ABSENT in the maintained checkout.
- Entry-geometry refs only: snow policy (`pc_p2_snow_attack_policy.h:7`,
  YellowKochappy attack entry + `P2_ENEMY_READY species=YellowKochappy`
  in `pc_p2_enemy.cpp:165`), bulblax species mapping
  (`pc_p2_bulblax_visual_policy.h:10`, id 53 -> KingChappy).

## Producer / blocker verdicts

| Sibling | Binding | Producer | Blocker |
|---|---|---|---|
| YellowKochappy (45) | ABSENT as dedicated module | none | missing YellowKochappy port module + family receiver for source-45 snow variant; birth seam with provider actor-birth-projectiles |
| KingChappy (53) | ABSENT as dedicated module | none | missing KingChappy boss port module (KINGCHAPPY_* FSM) + family receiver for source-53 emperor; birth seam with provider actor-birth-projectiles |

## First executable slices + destination pins

- YellowKochappy: bind source-45 to the KochappyBase spawn path; reserve
  `native/pc_port/pc_p2_yellowkochappy.cpp` +
  `native/pc_port/pc_p2_yellowkochappy.h` (new module + receiver registration).
- KingChappy: bind source-53 to a boss spawn path; reserve
  `native/pc_port/pc_p2_kingchappy.cpp` +
  `native/pc_port/pc_p2_kingchappy.h` (new boss module + receiver registration).
- Destination pins for downstream consumers: root
  `3a33cbdefd5e4057eef9fb0d824cce4510ddab05`, native
  `f363d04d71dc12488b563618a2d7db2423a868f7`.

Downstream consumers: the future source-45/53 admission lanes in this shard
(Chappy group 35/45/53/67); the #791/#616-style bridge + birth pattern applies.

## Tooling

- `experimental/pikmin2_chappy_siblings_audit.py` verifies all pins
  fail-closed and emits the registry packet (no writes by default).
- `tests/test_pikmin2_chappy_siblings_audit.py`: focused pin/owner/helper
  tests plus live checks against the reference trees.
