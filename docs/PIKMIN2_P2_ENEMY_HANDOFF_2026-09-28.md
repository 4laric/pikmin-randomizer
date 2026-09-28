# P2 enemy import: handoff, 2026-09-28 (cloud session → local agent)

This file is for a local agent that is picking up the Pikmin 2 enemy-import track. Before you do anything,
read `AGENTS.md`, the tracking issue **#888**, and the fidelity sweep **#886**. They follow the
issue-first rule: claim or comment before you change anything, and put progress, commits and evidence
on the issue.

This session ran in a Linux cloud container. It had no ISO, no Windows build and no game runtime, so
**nothing below was exercised in the game**. Everything it claims was checked only by code reading
against the decomp, by engine-free tests, and by Linux builds.

## 1. Where things stand (all merged by the owner)

| Repo | `main` | Contains |
|---|---|---|
| root `4laric/pikmin-randomizer` | `9bac7d0a` | P2 final-v2 line + #882; #888 roster decisions (#889); Groink staging (#890) |
| native `4laric/Open-Nectar---Pikmin-Native-PC-Port` | `0b9f6c8` | final-v2 `20edccdc8`, #883 `3135ab9e5`, #884 `fd70a54ac`; Linux CI fixes; co-op captain (#3); Groink FSM (#4) |

The native PR numbers above (#2, #3, #4) are on the fork. The root PR numbers are on the root repo.
The fork's `main` is now the maintained native line, and its CI is green.

**Rebuild your local package from these two `main`s.** The old `output/p2play` package
(native `20edccdc8`, root `3f7963ac`) and `output/p2-884-future` are both older than this work.

## 2. Owner decisions (2026-09-28, recorded on #888 and in `docs/PIKMIN2_PLAYABLE_POOL.md`)

1. **Groink 78 is being finished. Kogane 9 and Jellyfloat 57 are pulled for now.**
2. **The co-op second captain is in scope** for P2 enemy behaviour.
3. **Unkillable enemies get no Archipelago check.** These are 9, 10, 11 and 16:
   `excluded` in the roster evidence, and dropped from every proxy tier via
   `randomizer.p2_proxy.NO_CHECK_SOURCE_IDS`. **Bosses belong in the pool.**
4. Push and promote. That is done.

## 3. What changed and why

**Root roster, #889 (`5bafcc03`).**
- Roster admission now **equals** the 35-species pool. `tests/test_p2_pool_roster_sync.py`
  checks for equality, so a bare `--p2-enemies` seed generates again.
- 57 and 78 are `candidate`. Their movement and attack gates are BLOCKED, because both
  ran on the P1 Frog host AI.
- Side effect: the `proven` proxy tier is now **empty**, because 10 Wealthy was its only row with evidence.

**Native Linux CI, in #2.**
- Case-correct `system.h` and `teki.h` includes.
- The guard header from root `scripts/` is now optional.
- `tools/p2_putenv_compat.h` provides `_putenv_s`.
- Two link stubs were added.
- `packaging/linux/package-standalone.sh --clean` passes.

**Co-op captain, #3.**
- `pc_port/pc_p2_navi_select.h` provides `pc_p2_navis()`, `pc_p2_nearest_navi`,
  `pc_p2_source_active_navi`, `pc_p2_captor_navi` and `pc_p2_is_navi`.
- About 45 target sites now pick the nearest alive captain. About 30 hit and area sites now apply to every captain.
- 52 captain-1 sites were left deliberately; the reasons are in the PR body.
- Solo play is unchanged, because solo runs `naviMgr->create(1)`.
- **Use these helpers for any new captain logic. Never call `naviMgr->getNavi()` to select a captain.**

**Groink 78/97, #4 (native) and #890 (root).**
- `pc_p2_groink_fsm.{h,cpp}` is an engine-free port of `MiniHoudaiState.cpp`, with a
  source-line table in its header.
- The Frog AI is suppressed. A stored-damage drain lets the Groink die naturally.
- A draw hook shows the staged P2 pose bank. There is a new `onion:p2:78` delivery bind.
- 97 now runs the FixMiniHoudai FSM.
- Root stages these for it:
  - `p2-groink-parms.txt` and `p2-groink-fixed-parms.txt` (retail `enemyparm.txt`);
  - `p2-groink-bank.txt` (`P2_GROINK_BANK_1`: clips, key events, pose frames, `kuti` muzzle);
  - 48 `minihoudai_<clip>_<ii>.mod` poses.
- The format and the unverified parts are documented in `docs/PIKMIN2_MINIHOUDAI_EXTRACTION.md`.

**Merge risk with netplay** (checked, not tested).
- #884's Kabuto Stone draw is idempotent: it only sets a log-once flag and restores the shared animation context.
- The stone update runs on `gsys` frame time, which netplay fixes in deterministic mode.
- The gap: the netplay state hash does not include the stone fleet, Chappy mouth slots or the Groink FSM.
- The netplay agent owns netplay, handshake and frame-loop code. This track owns the `pc_p2_*` enemy files.

## 4. Next steps, in priority order

### A. Groink OWN run (Windows; blocks admitting 78)
1. Build native from fork `main` (`0b9f6c8`). Stage content from root `main`:
   `python scripts/p2_prepare_content.py --iso <iso> --out <content> --species 78,97 ...`.
   Check that `<content>/MiniHoudai/minihoudai.json` has a `muzzle` entry and 48 poses.
2. `--p2-species` accepts only admitted ids. To bind candidate 78, use the local
   candidate-validation route that earlier lanes used, i.e. the `output/claude-orch` bot tooling
   with a target rebound to a bot-proven slot. Use a fresh isolated session. Do not touch
   `output/p2play` or its `.apsave`.
3. Check that the run directory has the three `p2-groink-*.txt` files and the `minihoudai_*.mod` poses.
   Also check that `p2-groink-teki.txt` does not read 2.0/3.0/1200.
4. Look for these log markers:
   - `P2_GROINK_PARMS source_id=78 retail=1`
   - `P2_GROINK_BANK staged_clips=8 muzzle_staged=1 … draw=p2_model`
   - `P2_GROINK_OWN_BIND … variant=NormMiniHoudai`
   - `P2_GROINK_DELIVERY_BIND … source_id=78`
   - `P2_GROINK_FSM_STATE` transitions
   - `P2_GROINK_VOLLEY shells=3`
   - `P2_GROINK_SHELL_HIT`
   - `P2_GROINK_FLICK`
   - `P2_GROINK_DAMAGE`, with health decreasing
   - `state=dead`, then `P2_GROINK_DEAD` and `P2_GROINK_ESCAPE`
   - `P2_GROINK_CARCASS_BECOME`, then `P2_GROINK_DRAW corpse=1`
   - after the carry: `P2_ORDINARY_P2_RECEIPT … id=onion:p2:78:<stage> … new=1`
5. Check by eye:
   - there are no Frog jumps or slams;
   - shells leave the mouth and point forward;
   - the model faces its direction of travel.

   If either orientation check fails, the `kuti` muzzle basis or the +Z facing assumption is wrong.
6. If all of that passes, re-admit 78 **in one commit**: fill the evidence gates
   (`docs/PIKMIN2_ENEMY_ROSTER_EVIDENCE.json`, pinned to the root and native commits and the exe SHA-256),
   add the placement `accepted_gates`, and add the `P2_PLAYABLE_POOL` row. The equality sync test enforces this.
   Placement is an exact 35-on-35 fit, so the 36th species needs a slot. Groink's profile keeps its
   original slot uids, but check that a unique target exists.

### B. #886 fidelity sweep (native)
- **Slice 1 is done and in PR `4laric/Open-Nectar---Pikmin-Native-PC-Port#5`** (`claude/p2-886-captors`): defect 3,
  the captor mouth-slot rework with hold, swallow-only-if-held and forget hooks for Jigumo, Snagret, UmiMushi and Armor;
  and defect 5, UjiA harmless to creatures and UjiB/Tobi striking once and then eating. Native ctest passes 169/169.
  Its runtime markers are in the PR body. Follow-ups it found:
  - Snagret has no captain attack when its box is empty, and no KEYEVENT_4 re-bite.
  - Jigumo never calls `attackNavi`.
  - The Armor attack gate is 45° against source 15°.
  - Captor `isStartFlick` is a proximity approximation.
  - Held Pikmin are drawn at the hidden host slot.
- Remaining confirmed defects, all still present at `fd70a54ac` and checked against the decomp:
  - **4, UmiMushi 71/101:** an angle-free fallback at `pc_p2_umimushi.cpp:388-392` and `:467-468`, and
    `SHAKE_RANGE` 20 against the source default 120. This one needs an owner keep-or-replace decision.
  - **6, Long Legs 56/69:** the crush fires on **every Walk tick** (`pc_p2_long_legs.cpp:682-691`, `pc_p2_long_legs_fsm.cpp:81-88,205`),
    as a body-centre `InteractFlick` with no captain hit. Source uses a per-foot `InteractPress`.
    Dango 94 rolls against only its first target. Watch out: P1 Pressed is stun-then-death, not an instant P2 death.
  - **7, Miulin 54:** `doBury` writes `navi->mHealth` directly (`pc_p2_mamuta_fsm.cpp:268-283`).
    Route it through a receiver that respects invincibility and death.
  - **8, Whiskerpillar 65:** the wake condition is inverted and has no 6 s timer (`pc_p2_imomushi.cpp:356-366`).
    This needs an owner decision, because the faithful version may never surface without fruit plants.
  - **Host squash:** Sarai 23 is an unsuppressed TEKI_Chappy with no press or smash hook, so it dies to
    150-damage thrown landings. Sokkuri 79 dies through the host smash instead of `SOKKURI_PRESS`.
  - **Stray:** Armor 15 can FLICK from GOHOME (`pc_p2_armor.cpp:675`). The unmerged `a1ec3f2fc` gates this to MOVE.

### C. Remaining species (29 outside the pool; see the stock-take classification)
- Near-ready:
  - 26 Catfish, 27 Tadpole and 84 Hana share one `carry_no_grab` bug after doAI suppression. Tadpole regressed when suppression was added.
  - 66 Houdai (Man-at-Legs) has a full loop and is a boss (allowed). It needs roster evidence refreshed from the
    misc4/misc5 logs, a placement profile, an OWN review, and a decision on bind-pose legs.
- Cheap Bulborb variants:
  - 1 Kochappy and 45 Snow: generalize the 44-keyed `kochappy_fsm`, and add an extractor and hostType 3.
  - 42 BlueChappy: add it to the `pc_p2_chappy` kSpecies table and add the texture swap.
- Bosses in scope: 30 Queen, 40 Giant Breadbug, 73 Titan Dweevil, 99 Waterwraith.
- 57 Kurage re-entry needs its P2 FSM out from behind `PIKMIN_P2_KURAGE_SHOWCASE` (`pc_p2_kurage_teki.cpp:456`),
  plus suppression and a damage drain.
- **Placement capacity blocks every new admission.** All 49 ground slots are in use, so new
  evidenced slots or a density policy must land first (#838, #841).

### D. Housekeeping
- The root `engine/` is a stale native snapshot (last P2 export `48a2a693`). Re-export only if the root package needs it.
  `tests/test_p2_groink_stage.py`'s native round-trip needs `P2_NATIVE_PC_PORT=<native>/pc_port` until then.
- Stale docs: `docs/PIKMIN2_P2_CAMPAIGN_READINESS.md` (2026-09-19 matrix), and the error text at
  `randomizer/__main__.py:78` ("33-slot target set").
- Root draft PR #432 is superseded by #889, so close it.
- The `proven` proxy tier is empty. Decide whether `p2_enemy_pool=full` in the apworld still makes sense.

## 5. Working rules learned this session
- **Treat Muse/DeepSeek-era worker code as unverified until you check it against the decomp.** The P2 decomp is
  `projectPiki/pikmin2`. Typical faults: test-only shortcuts in the gameplay path (captain teleports,
  carry_min=1), invented or inverted behaviour, P1 host AI still running underneath, and tests that assert nothing.
- Every behaviour fix needs an engine-free regression that fails on the old code (use a mutant), wired into CMake
  next to the related `p2_*_test`. A natural runtime encounter is the fidelity evidence; spawn or bind logs are not.
- Native CI (`linux.yml`) builds **every** target and runs ctest in a native-only checkout with GCC 11.
  New tests must build without the root `scripts/` directory, and Windows-only APIs need a shim.
- Linux build recipe: `cmake -S <native> -B <build> -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo -DP2_CHALLENGE_GUARD_INCLUDE_DIR=<root>/scripts`.
  The expected result is that `bin/nectar` links and ctest passes 168/168.
- Root tests: many fail in any environment without the owner's Windows paths, ISO or tkinter.
  Compare the FAILED set against `main` instead of expecting green.
- Suppressing a host's doAI without a stored-damage drain makes the enemy invulnerable,
  and suppression has broken carry before. Check both for every OWN species.
