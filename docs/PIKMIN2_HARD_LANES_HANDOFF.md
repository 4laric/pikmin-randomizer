# P2 hard lanes handoff — BombSarai (#244), Fuefuki (#245), BigTreasure (#246) + engine parm pipeline (#128)

Prepared 2026-09-13 by Codex via shared account 4laric. Everything below is **local only — no branch has been pushed**. Merge/build serialization stays with the integration lead; family lanes own their mechanics, registration hooks, private builds and runtime evidence (per the 2026-09-13 ownership assignment on #128).

## Where the work lives

| Repo / worktree | Branch | Lane commits (newest first) |
|---|---|---|
| root `pikmin-randomizer/` | `kimi/p2-bulblax-import` | `dd2aade` `beb3286` `d29a41d` `14b666d` `54772fd` `7f50bbe` `5774557` `7db2faf` `65777c0` `0d77d51` `92a2955` `9553c20` `cbdf891` |
| `native/` | `codex/pikmin2-room-preview` (shared with other lanes — cherry-pick by file) | `4ccb7778` `c07858d1` `e3079bda` `224b06da` `a2a77006` `cf95d690` `ffbcafdd` `a4c83fe7` `fceba9bb` `b1d0089c` |
| `output/native-bombsarai-policy/` (worktree) | `codex/p2-bombsarai-policy` | `e9f1851f` `72f1969b` `6d423c4b` `8e892958` `88749414` `b5668de1` |

Disc assets: staged copy at `assets/disc/PIKMIN2 for GAMECUBE.iso` (verified GPVE01, US, rev 0). Original in Downloads is never touched. Generated/extracted data (`output/p2-engine-parms/`, runtime logs/captures) is local/uncommitted per policy.

## Lane state

### #244 BombSarai (Careening Dirigibug) — most complete
Audit → bomb/clock/terrain/hover/blast policies → integration seam → private build (`[499/499]`, nectar.exe) → **runtime probes executed PASS** → **13-state carrier FSM driving the seam end-to-end** (3 runtime scenarios: approach / purple-Fall / death-drop, exit 0).
- Docs: `docs/PIKMIN2_BOMBSARAI_{AUDIT,PROJECTILE_CONTRACT,HOST_ADAPTER,INTEGRATION_SEAM,RUNTIME_EVIDENCE,FSM}.md`
- Code: `pc_port/pc_p2_bombsarai_*.{h,cpp}`, fixtures `tools/p2_bombsarai_*_test.cpp`, runtime `tools/p2_bombsarai_runtime.cpp` (run via `preview_pikmin2_room.prepare()` overlay; see runtime evidence doc for exact commands).
- Open: retail .bca keyframe timings, kamu_jnt1 capture-joint transform, flick effect routing, walkToTarget horizontal movement, multi-carrier pool limit + ip02=15 induction, save/resume persistence, visual assets (debug markers).

### #245 Fuefuki (Antenna Beetle)
Audit → interference policy → 9-state FSM bridge → lane-owned binding seam (5 hook specs) → **real-GL runtime verification on the live P1 squad/whistle path** (zero ownership writes while beetle lives; Panic-only reclaim via real `Navi::callPikis`, one write; Carry carcass; exit 0).
- Docs: `native/tools/P2_FUEFUKI_{AUDIT,INTERFERENCE_POLICY,FSM,BINDING,RUNTIME_EVIDENCE}.md`
- Code: `pc_port/pc_p2_fuefuki_{interference_policy,fsm,binding}.h`, fixtures `tools/p2_fuefuki_*_test.cpp`, runtime `tools/p2_fuefuki_runtime.cpp`; install glue `experimental/pikmin2_fuefuki_install.py`.
- Open: physical arena placement (#186), follow-action locomotion (no P1 follow-teki action), true panic-state staging, suspend brain-fallback (Formation vs Free), claim persistence across day/cave transitions, motion-bank visual staging (10 clips confirmed on disc).

### #246 BigTreasure (Titan Dweevil)
Audit → weapon ownership/teardown policy (11 fixture groups) → per-element attack policies (fire/gas/water/elec + director) → P1 map binding + host glue → **runtime probes PASS** → model/motion conversion handoff (27/29 clips converted; `wait1` + `dead` staged live via the #259 retail event player, KEYEVENT_100 @ frame 320 verified).
- Docs: `docs/PIKMIN2_BIGTREASURE_{AUDIT,CONTRACT,ATTACKS,SEAM,CONVERSION}.md`
- Code: `pc_port/pc_p2_bigtreasure*.{h,cpp}`, fixtures `tools/p2_bigtreasure*_test.cpp`, runtime `tools/p2_bigtreasure_runtime.cpp`; install glue `experimental/pikmin2_bigtreasure_install.py`.
- Open: **loozy model unconverted** (shape-3 matrix type 1 unsupported — debug marker, no fabricated geometry), 27 converted clips not runtime-staged (host heap capacity; only 2 staged), skeletal playback, pellet joint tracking, material fidelity, visual acceptance vs retail, ballistics-vs-retail gameplay acceptance, damage receivers, FSM host, arena mixed-level staging, root-owned merge of seam entry points.

### Engine lane (#128) — disc parm pipeline (done this round)
`experimental/pikmin2_engine_parms.py` + `tests/test_pikmin2_engine_parms.py` (12 tests; full suite 587 OK); tables in `docs/PIKMIN2_ENGINE_DISC_PARMS.md`; JSON at `output/p2-engine-parms/engine_disc_parms.json` (uncommitted). Covers retail parms for all three lanes, weapon pellet configs, finale treasure identity (loozy = King of Bugs; `mPelletDropCode` null in story mode), and confirmation that BigTreasure has no .btk/.brk (material animation is procedural). The #259 retail-motion event player is closed/integrated (root `3486cc0`, native `c5845468` on engine branches; independently re-verified 203 checks / 29 clips).
- Open: BMD/BCK conversion of `enemy/data/{BombSarai,Bomb}/` archives; BMG name→INF1 index map; bomb trace radius resolved to collision part radius 15 (`bomb/enemycoll.txt`) by #244.

## How to resume (per lane)

1. Read the lane's audit doc first, then the newest evidence doc — each lists its own open items.
2. Build fixtures standalone: `g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/<fixture>.cpp pc_port/<modules>.cpp` from the lane's native checkout (BigTreasure fixtures need `pc_p2_bigtreasure.cpp`, host additionally needs attacks — see lane docs).
3. Runtime fixtures need the staged disc assets and a real GL window; put `native/build-randomizer/bin` on PATH (DLL dependency). Exact commands are in each lane's runtime evidence doc.
4. Keep lane-owned files only; shared `native/build-randomizer` binaries/exports are never overwritten; verify with `ninja -n pikmin_pc` (should be no-op).
5. Commit locally referencing the issue; post progress/evidence comments on the issue; integration lead owns merges/pushes.
