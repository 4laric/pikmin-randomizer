# P2 enemy import: handoff, 2026-09-29

This covers the 2026-09-28/29 session, which was run as Opus and Sonnet Workflow fan-outs driven from one Claude session. It follows the 2026-09-28 handoff (`docs/PIKMIN2_P2_ENEMY_HANDOFF_2026-09-28.md`, PR #891). Read this file first, then the issues it links.

## 1. Where main is

| Repo | Branch | Head |
|---|---|---|
| Root `4laric/pikmin-randomizer` | `main` | `5be6db3a` (merge of #916) |
| Native `4laric/Open-Nectar---Pikmin-Native-PC-Port` | `main` (remote `fork` in `native/`) | `c7dae173f` (merge of #17) |

These landed this session. Pairs are listed native first, then root; the conflict notes are on #899, [comment 5898755061](https://github.com/4laric/pikmin-randomizer/issues/899#issuecomment-5898755061).

| Work | Native | Root | Issue |
|---|---|---|---|
| Boss arenas | #18 (via #13) | #917 (via #911) | #899 |
| Held ship part (partly proven, kept by owner) | #13 | #911 | #901 |
| Visual fidelity: P1-lit materials, dense interpolated poses | #19 | #918 | #895 |
| 32 Bumbling Snitchbug, own behaviour, admitted | #14 | #913 | #215 |
| 94 Segmented Crawbster, fixes plus arena | #15 | #914 | #897 |
| 73 Titan Dweevil, own behaviour, admitted | #16 | #915 | #246 |
| 66 Man-at-Legs walk animation (IK legs), **not admitted** | #17 | #916 | #173 |

**Playable pool: 38 species.** Arena bosses 94 and 73 are placed separately. The other 36 ordinary species compete for 35 slots, so each seed samples one out (#893).

At the time of writing, every generated seed puts 94 in `hope_snagret_pit` and 73 in `impact_goolix`. 94 has kill evidence in the Goolix arena, not in the pit.

## 2. Open PRs, ready but not merged

| Species | Native | Root | Issue |
|---|---|---|---|
| 38 Breadbug | #21 | #921 | #898 |
| 41 Antenna Beetle | #22 | #922 | #245 |
| 58 Careening Dirigibug | #23 | #923 | #244 |

- **Review status.** All three passed their re-review except for one wrong log hash each, and those hashes are now corrected and verified against each run's `score.json`.
- **Merge order.** 38, then 41, then 58, native first in each pair.
- **Expected conflicts, all mechanical:**
  - Native: `include/teki.h` (keep every TPF_Life wrapper and include) and the test-only bot files `pc_p2_autoplay*.{h,cpp}`.
  - Root: every admission pins the pool size, so recompute it at 39, then 40, then 41. The files are `P2_PLAYABLE_POOL`, the bridge `PLAYABLE_IDS`, `docs/PIKMIN2_PLAYABLE_POOL.md`, the roster and evidence, and the regenerated `docs/PIKMIN2_ADMITTED_PLACEMENT.json`. The pinned-count tests are `test_p2_pool_sampling`, `test_p2_species_density`, `test_p2_playable_pool` and frogs5/stageA.
- **Why they're unmerged.** An agent-driven merge was refused by the permission classifier ("merge without review"). The owner must either merge them or give an explicit merge instruction.

Stale or unrelated open PRs, not part of this line: #891 (the 09-28 handoff doc), #436.

## 3. In flight when this was written

- **Held-part follow-ups (#901).** A Sonnet agent is working on `claude/p2-held-part-followup` from the new mains. Its items:
  - Make root placement produce the P2 takeover of P1 holder slots from a seed, with no hand-bound driver.
  - Add an env-gated, test-only hook so the bot can reach arenas behind bomb walls or the FoH pit.
  - Run the missing acceptance runs: an arena boss going assign → drop → carry → ship CHECK; un09 carry; a holder leaving without dying; a part that was already collected; a dropped part surviving day end (the save half is proven, the load half isn't); two-peer lockstep; and vanilla regressions for the ust1, Snagret and BLL holders.
  - Check issue #901 and the branch for its result.
- **SnakeCrow 34 regression** (a separate session the owner started). 34 is in the pool but fails its bot run on native main: either the kill never completes, or the corpse can't be grabbed (`reason=no_grab`). Pose-only exe `7e310bdd` passes, so the regression came in with captors #5 or Groink shells #6.
- **Long Legs 56/69 source HP** (a separate session, now ended). Branch `claude/p2-longlegs-life-56-69` makes TPF_Life return the source max life. Before this, the per-frame clamp left 56/69 at 130 HP, so all earlier admission evidence for them ran at the capped HP. Its status is on #173. Check whether its `teki.h` wrapper now conflicts with main.

## 4. What is proven, and what isn't

**Held ship part (#901).**
- Proven:
  - A P2 enemy in a regular holder slot (Spring, species 44, part uf02) drops the part on death through its own death path.
  - The bot carries it to the ship, and `CHECK 5 Pikmin: Interstellar Radio` fires at the vanilla location index.
  - The vanilla P1 holder is unchanged.
- Not proven: an arena boss delivering its part (the bot can't get past the Spring and Navel bomb walls or the FoH pit), un09 delivery, day-end reload, and netplay.

**Bot code.**
- The bot changes from #15 (94) and #16 (73) were merged together. They compile and the unit tests pass, but the combination has never run in game. 73's hinder-rock push and 94's obstacle push now coexist.
- Nobody has run a kill → carry → Onion smoke test for 32, 73 or 94 on merged main yet. That is the first thing to do.

**66 Man-at-Legs.** It has a real P2 IK leg walk and a natural kill/carry/receipt on an ordinary slot. It is not admitted: the owner wants it in an arena, and the bot can't reach arenas (`target_unreachable`).

**Visual fidelity.**
- UmiMushi `sturn1` had 0 poses (the retail BCA has 26 tracks for the 25-joint model). Fixed in #995: the trailing track is ignored, as J3D does; re-extract to get 24 poses.
- These families still use their own loaders: King/Queen, Kurage, Fuefuki, Qurione, Kogane, Shijimi and Snow.
- Content staging got slower because the banks are bigger.

## 5. Owner rulings, all still in force

- Bosses may enter the pool. Their placement is limited to **boss arenas**, which replace the P1 boss.
- The **Emperor arena stays protected** because it's the finale.
- The Puffstool arena may take a P2 occupant, but the Puffstool bestiary check is not re-keyed.
- **Bestiary checks must follow which enemies are actually in the seed.** This is #905, and it includes the suspected suppression at `goalItem.cpp:379-383`. Not started.
- P2 enemies may replace every ship-part holder, including the non-arena ones: Breadbug un09, Puffy uf02 and Clamclamp un12. The held-part visual is radar-marker only, matching P1.
- A carryable corpse is fine in P1 even where P2 leaves none (Titan, Man-at-Legs).
- Titan gas stays lethal to every P1 colour. White Pikmin are planned.
- Man-at-Legs admission waited on the walk animation, which is done. It now waits only on arena reach.
- Crawbster 94 stays in the pool.
- **Empress 30 is parked.** Don't block on it. Its branches are `claude/p2-port-30-*`, and the admission branch `claude/p2-port-30-queen-admit-v2` is stale.
- The resident pose budget is 1 MiB per clip and 48 MiB per setup.
- Owner-merged PRs may land out of the recommended order. Re-check the conflicts against the real main before resolving.

## 6. Suggested next slice

1. **Smoke test merged main.** Run one bot session each for 32, 73 and 94. Include 94 in the Snagret pit, where it currently lands.
2. **Merge 38, 41 and 58** (section 2).
3. **Family variants** that reuse admitted modules and are cheap:
   - 1 Dwarf Red Bulborb (from 44).
   - 42 Orange Bulborb (Chappy family; it has no native code yet).
   - 95/96 Cannon Beetle variants (from 75).
   - 97 Groink on a pedestal (from 78; its inputs are staged under #888).
   - 40 Giant Breadbug (from 38).
   - 45 Snow Bulborb (a candidate; only spawn is tested).
4. **Flyer targeting.** P1 Pikmin won't target airborne enemies (`piki.cpp:951` needs `!isFlying()`, and `aiAttack.cpp:297` drops airborne targets). This one wall blocks 57/72 Jellyfloats, 16 Honeywisp, 29 Puffy Blowhog, 55 Withering Blowhog and 77 Spectralids. In P2 these are hit when they come low or land, so implement a "vulnerable when low" rule or let Pikmin latch on.
5. **Bot arena routing** (infrastructure). It unblocks the 66 admission, in-arena boss evidence and the held-part arena runs.
6. **Later:**
   - Mechanics lanes: 26 Water Dumple and 27 Wogpole (water), 84 Creeping Chrysanthemum, 93 Volatile Dweevil, and 99 Waterwraith (a boss with rollers).
   - An owner decision on the excluded Iridescent beetles (9, 10, 11). 9 passes all six gates.
   - #905 bestiary seed-awareness.
   - Audit which older "admitted" species are still proxies underneath. The owner's bar is own behaviour.

## 7. Operating lessons from this session

- **Load crashes the PC.** It bluescreened twice on 2026-09-29, at 14:03 (0x3B) and 14:14 (0x7E), both times with about 8 parallel builds plus several headless game sessions running. Minidumps are in `C:\Windows\Minidump\092926-*.dmp`. Run at most one or two game/bot sessions at a time, and check `tasklist | grep -i nectar` before starting one.
- **The second crash zeroed `.git/config`** in the root repo, and in native too, which was since restored. It also zeroed the index of worktree `output/wt-p2-boss-arenas-v3`, which is still `index file corrupt` and belongs to another session. Per-branch upstream tracking was lost; `git push -u` restores it.
- **Workflow tool:**
  - Resume reuses only the longest *unchanged prefix* of agent calls, so dropping a lane re-runs everything after it. To skip a lane, write a follow-on workflow that reads the old results from `journal.jsonl`.
  - After a session restart, copy the script into the scratchpad before resuming.
  - Strip CRLF from the script first.
- **Don't SendMessage a running workflow agent.** It forks a second copy in the same worktree. Post owner decisions on the lane's issue instead.
- **Fix passes need review.** Several "fix" stages re-committed admissions that nobody had reviewed. Always re-review a fix before opening a PR, and verify every cited log hash against the file and `score.json`.
- **Evidence rules** (unchanged): a natural kill → carry → Onion receipt on the species' own generator token, with power-mode bot runs accepted. Spawn, READY or CORPSE_READY markers are never behaviour. The pool, roster, evidence and placement change together.

## 8. Useful paths

- Drivers:
  - `output/claude-orch/p2-groink-own/groink_botrun.py` (template)
  - per-lane `output/claude-orch/p2-*-own/*_botrun.py`
  - `output/claude-orch/p2-held-part/held_part_run.py`
  - `output/claude-orch/p2-boss-arenas/`
- Arena catalogue: `randomizer/p2_boss_arenas.py`. Placement: `docs/PIKMIN2_ADMITTED_PLACEMENT.json`.
- Pose tooling: `scripts/p2_pose_density_audit.py`, `scripts/p2_loop_seam_audit.py`, `scripts/p2_pose_motion_evidence.py`. Docs: `docs/PIKMIN2_POSE_FIDELITY.md`.
- Env switches:
  - `PIKMIN_P2_INTERPOLATION=0` (A/B)
  - `PIKMIN_P2_CROSSFADE_MS`
  - `PIKMIN_FRAME_DUMP` / `_EVERY` / `_FROM` / `_TO`
  - `PIKMIN_RANDOMIZER_AUTOPLAY`, plus `_TARGET` and `_P1_UID` for P1 targets
