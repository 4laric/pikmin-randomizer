> **Historical snapshot (2026-10-01).** This handoff predates the current
> [co-op/P2 integration #1144](https://github.com/4laric/pikmin-randomizer/issues/1144)
> and [complete-state protocol #1148](https://github.com/4laric/pikmin-randomizer/issues/1148).
> The branch/worktree status, pending issues, commands and capacity gates below
> describe that original handoff only. Follow current [AGENTS.md](../AGENTS.md)
> and the [workflow operating contract](PIKMIN2_WORKFLOW.md); supported remote
> builds use the canonical `output/workflow/GITHUB_RUNNER_QUICKSTART.md` without
> local heavy-build leases. Preserve the original provenance and interrupted
> worktrees; do not execute inherited commands as current instructions.
> Historical test results do not establish current combined-source or gameplay
> acceptance. The original handoff is preserved verbatim below.

# Netplay handoff (2026-10-01, Claude → Codex)

This page is for whoever picks up online co-op netplay for the native Pikmin PC port: Codex working through the shared `4laric` account. It covers what has shipped, what is half-done, where every branch and folder is, and the rules learned the hard way.

- The umbrella issue is #876. Workflow rules are in `AGENTS.md`.
- Paths under `output/` are git-ignored and exist only on the owner's machine (`C:\Users\alari\pikmin-randomizer\output`).

## 1. Current state in one paragraph

The owner and a friend played the first real two-network sessions on 2026-09-30, using zip `pikmin-netplay-b251978`. They found bugs #1028 to #1037. All of them are fixed in the **combined playtest zip `pikmin-netplay-58c0fed`**, which was sent to the owner on 2026-10-01 and is waiting for their retest.

Work then started on **#1048 (M4e: Archipelago in online co-op, started from the Pikipelago launcher)**. Wave 1 was interrupted. One lane is in the middle of a merge, one is merged but not implemented, and one has not started (section 4).

Upstream Open Nectar merged our co-op swarm-sound fix (SSunnKing/Open-Nectar---Pikmin-Native-PC-Mobile-Port#64).

## 2. Shipped: combined playtest zip `pikmin-netplay-58c0fed`

| | |
|---|---|
| Zip | `output/netplay-playtest/pikmin-netplay-58c0fed.zip`, SHA-256 `a4ae90b4ec53dfc9de3ec12567796d631ef11d275f326fb1af6963b32844d2b2` |
| Unzipped copy | `output/netplay-playtest/pikmin-netplay-58c0fed/` (8 files) |
| np `nectar.exe` | SHA-256 `9e2596073e94cd95acdeec17f0d74de65bda08603bf4c31301d55fafc37a3c49` (`PIKMIN_NETPLAY_BUILD=ON`) |
| Source | native `claude/netplay-playtest2-native` @ `58c0fed7a`, pushed to `fork` and `origin` |
| Package notes | `output/netplay-playtest/PACKAGE-58c0fed.md` (the recipe, smokes, and the continue test) |
| Handoffs | `output/netplay-wave/scratch/playtest2/` (part A) and `playtest2/partB/` (part B, sweep, package) |

**What is in it.** Every lane below was merged onto `b251978a7`, the previous shipped line.

| Issue | Fix | Lane branch @ head |
|---|---|---|
| #1028 | Captain 2's whistle works, and Onion withdrawals go to the captain who asked | `claude/netplay-coopfix-native` @ `f204db1f9` |
| #1029 / #1031 | The cutscene skip goes through synced input. The black bar is gone from the end-of-day countdown. F3 photo mode is locked out in a session. Text-window button labels are fixed | `claude/netplay-skipfix-native` @ `a86971fc9` |
| #1033 | `invalid slotId!` panic: crowd-slot bookkeeping when a squad Pikmin changes captain | `claude/netplay-crowdslot-native` @ `c1d321f54` |
| #1034 | Pellet seeds stranded in the Onion are re-posted. Every pellet delivery is logged | `claude/netplay-pelletbonus-native` @ `8018b6005` |
| #1030 | Audio, in three rounds. Captain ownership. A stall cap and the keep-stream at takeoff. Cinematic SEs played on SE child 0, not 15 (they had never played). One cue cursor per demo. Per-captain whistle, C-stick and fly-ready state | `claude/netplay-audiofix-native` @ `093c82df6` |
| #1036 | Multi-part bosses in the presentation pass (`BossPresentJoints`). The King shadow caster is guarded | `claude/netplay-bossview-native` @ `774db3187` |
| #1037 | Desync forensics, the King caster guard, and the Slime spring guard | `claude/netplay-desync-native` @ `52aeb3238` |
| #1035 | Upstream 0.9 geyser gate: with two captains, only captains within 80 units launch | on the integration branch (`pc_port/pc_geyser_gate.h`) |
| (sweep) | Bridge platform countdown, counted in the authoritative pass only (`workObject.cpp:1036`) | integration commit `62da1045a` |

**Verified on the shipped exe.**
- ctest np 204/204 and default 194/194. M1 replay `52283babc3bb5298` on np and default. `run_pair` 3000 passes.
- Every lane's scripted acceptance passes.
- A day-end pair gives byte-equal saves on both peers.
- The desync forensics work end to end.
- An asymmetric-window determinism sweep ran from the owner's day-15 checkpoint: 72 tour pairs (360,000 ticks), covering all 5 stages and every boss, all identical. The sweep also re-detects the King, Goolix and Bridge bugs on the pre-fix exe.

**Campaign continue** was tested on a copy of the owner's save. The owner runs this (PowerShell):

```powershell
$old = 'C:\Users\alari\pikmin-randomizer\output\netplay-playtest\pikmin-netplay-b251978'
$new = 'C:\Users\alari\pikmin-randomizer\output\netplay-playtest\pikmin-netplay-58c0fed'
robocopy "$old\netplay" "$new\netplay" /E /XD shader_cache
Copy-Item "$old\pikmin_settings.conf" "$new\"   # optional: window and display settings
Set-Location $new
.\host.bat --continue    # expect: checkpoint 13 (day 15)
```

The friend unzips the same zip and runs `join.bat`. The host sends them the checkpoint.

**Waiting on the owner:**
- the two-PC retest;
- listening to the day-end march, the takeoff, and whether cutscene music still sounds fast (#1030);
- if a desync recurs, both players' newest `netplay\run-*` folders (the game now writes `desync-report.txt` and `session-inputs.pknl`).

The day-15 desync is fixed as **"likely, not confirmed"**: the joiner's `desync subs` line never arrived.

## 3. Open issues (netplay)

| Issue | State | Next step |
|---|---|---|
| #1028 #1029 #1030 #1031 #1033 #1034 #1035 #1036 #1037 | Fixed in `58c0fed`, each with a "shipped" comment | Close after the owner's retest. #1030 also needs the listen. #1035 has a unit test only, because no harness profile loads a geyser |
| #1048 | M4e spec. Wave 1 interrupted (section 4) | Resume A0 first; it gates the rest |
| #1060 | The Pikmin murmur never plays on the legacy facade: `Jac_UpdatePikiGaya` writes SE child 3, but the track is child 2 | One-line fix, but the owner must listen first |
| #1062 | The session digest covers only `stages/**`; boss, teki, effect and parms data is unverified | Widen the digest with a per-file hash cache |
| #982 | Alt playtest build with admitted P2 enemies | Parked. Last zip `pikmin-netplay-p2-c70bef6` |
| #997 | One P2 sidecar spanning several transfer messages (Titan Dweevil 73) | Parked |
| #998 | P2 Dwarf Orange Bulborb (44) never binds | Parked |
| #896 | M6 rollback (snapshot/restore) | Parked mid-phase 1. See `output/netplay-wave/handoffs/m6b-p1.md` |
| #887 / #965 | M5 internet play and its follow-ups | Mostly done. Only the remaining minors are open |
| #885 | M4 (randomizer/AP under lockstep) | Native side done. The live-AP part moved to #1048 |

## 4. M4e (#1048): interrupted wave 1

Spec: #1048. Its lanes are A0 (gating), then A, B, C, D and E1/E2. The four owner questions proceed on their stated defaults until the owner rules:
1. The host hands over `.pikmin.json`.
2. Ship two exes.
3. The host's `session.json` wins.
4. Do not seed `checked` from the server.

| Lane | Worktree | Branch | State |
|---|---|---|---|
| A0, native: merge `fork/main` into the shipped line | `output/native-m4e` | `claude/netplay-m4e-base` (local only) | **Mid-merge.** `HEAD` is `58c0fed7a`, `MERGE_HEAD` is `fork/main` `03fa75bd4` (525 commits). 460 paths staged, **11 still conflicted** (list below). No build dirs yet. Either finish the resolution, or run `git merge --abort` and redo it |
| B, root: runner and mirror client | `output/root-m4e` | `claude/netplay-m4e-runner` @ `7c8fda70` (pushed) | `origin/claude/netplay-m4c` (`41ad8372`) merged with `origin/main` (`e77be0b3`). The #1048 B items 2-8 are not started |
| E1, root: room helper and MultiServer starter | `output/root-m4e-aptest` | `claude/netplay-m4e-aptest` (local, = `origin/main`) | Not started |

**A0 conflicted files:**
- `pc_port/pc_p2_bulbmin.cpp`, `pc_p2_hardlanes.cpp`, `pc_p2_queen_teki.cpp`
- `pc_port/pc_randomizer.cpp`, `pc_port/settings/pc_settings.cpp`
- `src/plugPikiColin/moviePlayer.cpp`
- `src/plugPikiKando/dualCreature.cpp`, `gameCoreSection.cpp`, `navi.cpp`
- `src/plugPikiNakata/pcamcamera.cpp`, `tekibteki.cpp`

**A0 must:**
- Keep every netplay determinism fix: the presentation-pass guards (King caster, Slime spring, Bridge countdown, `BossPresentJoints`), the #1029 synced start inside `run_advance()`, the forensics, and the audio ownership.
- Advertise every capability the current root seed emits, and parse the bootstrap keys `MATURITY`, `DAY_LENGTH`, `WHISTLE_PLUCK` and `PURPLE`. The `b251978`/`58c0fed` hello lacks them, so a current AP seed is refused on the np exe today.
- Give the same M1 hash on np and default. The value may legitimately change from `52283babc3bb5298`; record the new one on #1048.

Prior art for the resolutions: the P2-pool netplay line `claude/netplay-p2pool-native` (`output/native-np-p2pool`) merged native main twice (`317f09db2`, and an earlier one).

**Lane B** codes against the native contract named in #1048: `--netplay-host-ice`/`--netplay-join-ice`, `--bootstrap`, `--netplay-code-out`, `--netplay-answer-in`, `PIKMIN_NETPLAY_RUN_ROOT` and `--netplay-external-state`. The last two do not exist yet; Lane A adds them. Put them behind one adapter, and test against a scripted fake native process.

## 5. Upstream (Open Nectar, SSunnKing)

- **#64, merged:** the co-op swarm (C-stick) sound arbiter (`PcFormationArbiter` in `SeMgr::playNaviSound`, under `PIKI_PC_PORT`). Branch `claude/upstream-coop-formation-sound` @ `e30dbc6d1` in `output/native-water-upstream`. **Still to do:** port it to our fork for local co-op in JAUDIO=ON randomizer builds. Netplay builds already have a per-captain stick in `audio_stubs.cpp`.
- **#60, draft:** gamepad unbind and remaps (#59). Waiting for the owner's manual F1 check, or permission to mark it ready. Our fork's #74 has merged.
- The maintainer often closes PRs without comment and hand-integrates them into the next release; a closed PR is not a rejection.
- **Every upstream write needs the owner's OK.**
- Upstream ships JAudio. Fixes to the legacy audio facade do not apply upstream.
- Upstream CI runs the decomp matching build, so guard any decomp signature change under `PIKI_PC_PORT`.

## 6. Branch and folder map

Native repo remotes: `fork` is GitHub `4laric/Open-Nectar---Pikmin-Native-PC-Port`. `origin` is the **local** checkout `C:/Users/alari/Documents/ChatGPT/decomp/pikmin-research`. `upstream` is SSunnKing's repo; never push there.

| Worktree | Branch | Build dirs |
|---|---|---|
| `output/native-netplay` | `claude/netplay-playtest2-native` (shipped) | `native-netplay-build` (default), `native-netplay-build-np` |
| `output/native-np-f965n` | skipfix / pelletbonus lanes | `native-np-f965n-build*` |
| `output/native-np-5cc` | desync lane | `native-np-5cc-build`, `-build-np` |
| `output/native-np-5cb` | bossview lane | `native-np-5cb-build`, `-build-np` |
| `output/native-np-audiofix` | audiofix lane | `native-np-audiofix-build`, `-build-np` |
| `output/native-np-d15` | `claude/netplay-d15-diag` (diagnostic only, never ship) | |
| `output/native-water-upstream` | upstream PR branches. It has **uncommitted local build tweaks** (`CMakeLists.txt` chmod, `pc_port/gl/pc_opengl.h`) that must never be committed | `native-water-upstream-build` (JAUDIO=ON) |
| `output/native-m4e`, `output/root-m4e`, `output/root-m4e-aptest` | M4e wave 1 (section 4) | none yet |

Evidence: `output/netplay-wave/scratch/`.
- `playtest2/`, `desync15/` (the repro drivers and the checkpoint-13 copies), `bossview/`, `audiofix2/`.
- Issue-body drafts: `comment-*.md`, `issue-*.md`.
- Package notes: `output/netplay-playtest/PACKAGE-*.md`.
- Older milestone handoffs: `output/netplay-wave/handoffs/` (`HANDOFF.md` there is stale).

## 7. Harness cheat sheet (native repo `tools/netplay/`)

Gate every launch and build:
- games: `py -3.12 output/gate-main/scripts/capacity_gate.py --kind game --wait`
- builds: `py -3.12 output/gate-main/scripts/capacity_gate.py --kind build --jobs 2 --wait`, then build with `-j 2`

Then:
- **Two-PC pair:** `run_pair.py --exe <np exe> --ticks 3000 --delay 2 --throttled --host-port <port> --out <dir>`. Keep loopback binds (`PIKMIN_NETPLAY_UDP_BIND`/`ICE_BIND=127.0.0.1`).
- **M1 single-player replay:** `run_replay.py --exe <exe> --replay output/netplay-wave/scratch/integ-m4gf/K/in9000-s42.pkni --ticks 9000 --out <dir>/x/run`. The first 16 hex digits of `sha256(hashes.txt)` must be `52283babc3bb5298` on the 58c0fed line. Use the `<dir>/x/run` layout, or a stale shared campaign dir trips a header/seed mismatch.
- **Co-op:**
  - `coop_whistle_pair.py --scenario both`;
  - `coop_policy_pair.py --acceptance --ticks 3000`.
- **Emperor regression:** `run_pair.py --profile trial-day2 --ticks 3000` with `PIKMIN_RANDOMIZER_TEST_BACKGROUND=1` and `PIKMIN_NETPLAY_TEST_TELEPORT=300:0:17:2450;300:1:-100:2450`.
- **From the owner's day-15 checkpoint:** `output/netplay-wave/scratch/desync15/repro/tools/pair15.py`, plus its menu scripts. It always works on a fresh copy of the owner's run folder.
- **Forensics:**
  - `check_desync_forensics.py`;
  - `replay_session.py` (replays a `session-inputs.pknl`);
  - `diff_desync.py`.
- **Test knobs.** All are scrubbed in `run_pair.SCRUB_KEYS`/`SCRUB_PREFIXES`, and all are documented in native `docs/NETPLAY_PLAY.md`:
  - `PIKMIN_NETPLAY_TEST_NAVI_TO_BOSS`;
  - `PIKMIN_NETPLAY_TEST_TELEPORT` (needs `TEST_BACKGROUND=1`);
  - `PIKMIN_NETPLAY_TEST_DESYNC_NUDGE`;
  - `PIKMIN_TEST_ONLY_PELLET_BONUS`;
  - `PIKMIN_TEST_CLOCK_TOD`;
  - `PIKMIN_NETPLAY_AUDIO_TRACE`.

## 8. Rules and lessons

- **The owner plays on this machine.**
  - Kill only processes you launched, by PID or process tree. Never by image name, `-Name` or window title: a name-wide kill once ended the owner's playtest.
  - Never run anything from or write into `output/netplay-playtest/<owner folders>`. Copy out instead.
  - Commands for the owner must be PowerShell.
- **Load.** The laptop bugchecks under heavy agent load (0x116, the GPU driver). Builds use `-j 2` through the capacity gate, with one pair at a time. If it bugchecks, remind the owner to update the NVIDIA driver.
- **Never** commit, zip or upload disc-extracted content or the owner's save/card files. Never modify firewall or security settings. Never relink the shared Archipelago install.
- **Presentation-pass rule (the whole desync class).** The frame runs an authoritative null-GX pass with the sim camera, then a presentation pass with each player's own camera. How often the presentation pass runs, and what it can see, differs per PC.
  - Any write in a `draw`/`refresh` path that the next authoritative pass reads must be guarded with `pc_render_is_authoritative()`.
  - Found so far: the King shadow caster, the Slime spring, the Bridge countdown, and the multi-part boss matrices.
  - Particles draw from the **sim** RNG, so a cosmetic divergence becomes a hard desync. Moving particles to the cosmetic stream is a possible follow-up; it changes the M1 sequence.
  - Before shipping, run the asymmetric sweep: unequal windows, teleports to every boss, and an extra presentation pass on one peer.
- **Give sweep and probe agents their own worktree and build dir.** In part B a sweep applied scratch diffs in the shared integration worktree and rebuilt there, and the reviewer then found a 0-byte exe.
- **Scripted pairs never exercise the live-pad path.** Input bugs need a human run or `PIKMIN_NETPLAY_INPUT_TRACE=1`. Pair evidence can pass vacuously, so require gameplay proof: distinct navi/piki/teki/item tuples, and `START_STAGE`.
- **Audio.** Netplay builds use the legacy facade (`PIKMIN_NATIVE_JAUDIO=OFF`, needed for rollback snapshots). Releases and upstream use JAudio.
  - `pikise.jam` track names are not child indexes: demo track 15 is child 0, and murmur track 3 is child 2.
- **Issue-first.** Every implementation needs an issue in `4laric/pikmin-randomizer` assigned to `4laric`. Record Codex as the implementation owner, and post progress, commits and evidence on the issue.
- **Pushing.** Push only `claude/**`, `codex/**`, `fix/**` and `feature/**` branches. Never push main, master or p2-integration, never push tags, and never force-push.

## 9. Suggested next steps, in order

1. Wait for the owner's retest of `58c0fed`. Triage anything new, and close #1028 to #1037 as they are confirmed.
2. #1048 A0: finish or redo the merge in `output/native-m4e`. Do a full build in new private dirs (`native-m4e-build`, `-build-np`). Run the regression set from section 7, plus a current-seed hello check.
3. #1048 B and E1 in parallel (root only), then A (native seams on A0), then D, then C, then E2 (live MultiServer acceptance and the owner playtest).
4. Port the upstream #64 arbiter to the fork for JAUDIO=ON local co-op.
5. #1060 (after the owner listens) and #1062.
