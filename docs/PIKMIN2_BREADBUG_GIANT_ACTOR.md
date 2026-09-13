# P2 Giant Breadbug actor (#220 batch 4)

The Giant Breadbug (OoPanModoki, P2 scope id 40, boss) runs as a **bound P1
Collec actor** with P2 parameters, paired to an owner-linked P1 Hollec nest.
P1 FSM locomotion/cargo and P1 collision scale are retained; the module owns
identity, P2 stats, Purple-only press, the PelletCarry contest, hide-digest
healing, defeat throw-up and nest birth/death linking.

## Pieces

- Native module `pc_port/pc_p2_giant_breadbug_actor.{cpp,h}` (private worktree
  branch `codex/p2-breadbug-actor`): parses `p2-giant-breadbug-actor.txt`
  (header `P2_GIANT_BREADBUG_ACTOR_1`, sampled wait/move clip frames, giant→nest
  generator pairs), binds generator rows (giant = P1 TEKI_Collec type byte 8,
  nest = P1 TEKI_Hollec type byte 12), sets health/maxHealth 2000 and logs
  `P2_GIANT_BREADBUG_ACTOR_READY`.
- Lane installer `experimental/pikmin2_giant_breadbug_actor.py`:
  `prepare` (from verified breadbug-lane-03 extraction), `plan` (config bytes +
  hash-verified models, generator type validation), `install` (refuse-overwrite,
  receipt json).
- Arena `experimental/pikmin2_giant_breadbug_arena.py`: original Impact Site
  practice map staged as chal0, giant 187001 at (-150,30,1850), nest 187002 at
  (-150,30,1650); Purple bank and Research Pod are required inputs.
- Native fixture `scripts/pikmin2_giant_breadbug_actor_fixture.cpp` + driver
  `scripts/test_pikmin2_giant_breadbug_actor_native.py`.

## Behaviors (all natively validated in giant-actor-native-14)

- **Spawn identity**: generator-bound birth XYZ, health/maxHealth = 2000.
- **Purple-only press**: `BTeki::eventPerformed` hook swallows the native
  400-damage P1 press. Purple Pikmin: exactly 100 damage + velocity zeroed.
  Non-purple Piki: resisted, no damage. (`P2_GIANT_PRESS`)
- **PelletCarry contest**: carriers ≥ (min+max)/2 steal the cargo back
  (`P2_GIANT_CONTEST_LOST`, 0.5 s freeze, FSM reset to wander so the giant does
  not complete an empty carry cycle).
- **Hide-digest**: cargo carried home is digested when the giant goes
  underground (`P2_GIANT_DIGEST` on state-8 entry, pellet consumed); health is
  restored to 2000 when it resurfaces to wander (`P2_GIANT_DIGEST_HEAL`).
- **Defeat throw-up**: on death, digested treasure is thrown back in a ring at
  the bound nest (`P2_GIANT_DEFEATED`, `P2_GIANT_THROWUP`). Defeat handling runs
  from the lethal press, the tick observer, or the tekiMgr forget hook —
  `isAlive` is option-based and updateAI can pause once the death sequence
  starts.
- **Nest linking**: `P2_GIANT_NEST_BIRTH` / `P2_GIANT_NEST_DEATH`; bound nests
  draw the lane nest model; the hidden giant draws nothing.

## Fixture lessons (do not rediscover)

- The pod-triggered tutorial overlay (`mIsUIOverlayActive=1`) freezes object
  updates: seed all demo flags before the ready gate and wait for the overlay
  to clear, exactly like the breadbug cargo fixture.
- The fixture link replays frozen objects from `baseline/link-inputs/`; after
  changing native sources, refresh `30-pc_p2_giant_breadbug_actor.cpp.obj` and
  `55-libpikmin_legacy.a` from the private-worktree ninja build before relink.
- `git-bash` PATH breaks MinGW gcc — run compile/link through PowerShell with
  `C:\msys64\mingw64\bin` prepended.

## Gaps / engine-owner flags

- Texture-matrix animation: static sampled frames (explicit gap, logged in
  `P2_GIANT_BREADBUG_ACTOR_DRAW`).
- Nest treasure day-save persistence: engine owner.
- Manager lifetimes: engine owner.
- P1 collision scale retained by design.
