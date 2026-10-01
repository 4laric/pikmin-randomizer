# Jigumo63 funnel-path post-DEAD removal/carcass diagnosis (#823; consumer #374)

Lane `jigumo-funnel-removal-diagnosis`, issue #823 (OPEN, assigned 4laric).
Downstream consumer: shard-enemies-4-jigumo63-observer (#374 blocked gen 3
rev 7). The observer demonstrated the #729 technique (HP 500->0, natural
DEAD at 16 throws) but the actor persists post-funnel with no corpse
recorded. Bounded tooling-only diagnosis: research family source plus the
gen-3 run evidence audited read-only. No native/shared edits, no builds,
no launches, no ADMIT. Diagnosis only; never an engine unblock. All six
gates UNTESTED. Captain safety #632 not applicable (no runtime); guard
standard `scripts/p2_fixture_captain_guard.h` sha256
`d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`
recorded for follow-on runs.

## Sources (uncommitted research tree; content-hashed, read-only)

- `native/pikmin2-research/src/plugProjectMorimuraU/jigumoState.cpp`
  sha256 `6ecc82c841371c8b8c912bf0d4295aeb7aeda8ffd686eeac195d850cf2253200` (800 lines).
- `native/pikmin2-research/include/Game/enemyInfo.h` sha256
  `0e68be790e4f7f4a99a48064b4750a95367c09996b7484292a33b2969d9b44ba` (`EnemyID_Jigumo = 63` at :122,
  `EnemyID_JigumoNest = 64` at :123).
- `native/pikmin2-research/src/plugProjectYamashitaU/enemyBase.cpp`
  sha256 `9871a460d0bb60cfd41565ebbb8c87222417f88dce15e768256b0395b7ec9e88` (`deathProcedure` at :2525).
- Observer evidence: `.../shard-enemies-4-jigumo63-observer/out/jigumo-run2/pass1/c386be146feb4b5cac32abae073616a8/`
  (`native.log` 107815 bytes/1466 lines; `runtime-evidence.json` sha256
  `c7501ffcbe0bc9de462f178c414b4f35a5ea2290ba54fc37876208b0ea92e2d3`).

## Post-DEAD lifecycle chain (cited)

1. Health->0 entries to `JIGUMO_Dead`: Return :457-458, Carry :521-522,
   Eat-end :671-672 (health==0, else Hide). State registry :18-31.
2. `StateDead::init` (:254-260): Dead motion + `deathProcedure()`
   (setAlive(false), throwup items, death FX at enemyBase.cpp:2525-2547).
3. `StateDead::exec` (:266-280): while the dead anim plays, on
   `KEYEVENT_END` calls `enemy->kill(nullptr)` (:277).
4. `kill()` has NO definition anywhere in the research source tree: it is
   Creature-layer removal, outside family scope.
5. `EB_LeaveCarcass` is never enabled for Jigumo (enablers exist only for
   ShijimiChou :203 and Tamagomushi :264; disablers for bomb/egg/nest/
   plants/tyre/blackMan). Default flag state governs any carcass.

## Observed post-DEAD trace (run2 pass1, cited log lines)

- :1314 `P2_JIGUMO_DEAD ... health=0`, :1315 state=dead, :1317
  `NATURAL_DEATH tick=186 throws=16 jigumo_alive=0`, :1318 DEATH_POS.
- :1319 `P2_JIGUMO_FUNNEL_DROVE engine=dieSoon` - funnel accounted, drove
  the death path; not the blocker.
- :1320 `P2_BATCH3_DRAW corpse=1 ... clip=dead1` (draw-layer flag only).
- POS lines :1323-1463: generator released (generator=0), dead clip phase
  0.21 -> 1.00 then STUCK at 1.00 while the actor keeps drifting
  (x -14.72 -> -32.63, y falling) - physics still integrates the dead
  actor; removal never took effect.
- :1465 `P2_JIGUMO_REMOVAL_STALLED no_removal_no_corpse`, :1466
  `FAIL p2 room: death produced neither removal nor corpse`.

## Attribution: family-owner-then-engine-167

The dead anim completed (phase stuck at 1.00) with the actor persisting
and no corpse, so `kill()` never took effect:

- FAMILY OWNER FIRST: verify `StateDead::exec` reaches `enemy->kill`
  (jigumoState.cpp:266-280). Prime suspect: the `:268` `mIsPlaying` gate
  vs `KEYEVENT_END` delivery in the port - if the anim stops playing at
  end before the event is processed, `kill()` is skipped forever. Named
  as the check, not the conclusion.
- ENGINE #167 SECOND: kill-to-removal plus the carcass pipeline
  (`EB_LeaveCarcass` default for Jigumo; corpse registration). The
  observer dependency already names #167; this diagnosis confirms it as
  the removal/carcass owner once the family-side kill fires.

No invented providers. If the dead anim had never completed, the finding
would be UNATTRIBUTABLE pending a longer-bounded run with per-tick
anim-phase markers (encoded in the analyzer).

## Pins

- Research sources (hashes above; untracked tree, no commit pin).
- Observer root d1c87e2d / native ef4ed817; fixture exe `1350f741b46bfed02058098af152c8d62f617c966d75339dcef162050c834224`.
- This lane: root 3a33cbde (branch
  `codex/jigumo-funnel-removal-diagnosis`), analyzer + 8 tests green,
  this doc. No ADMIT.
