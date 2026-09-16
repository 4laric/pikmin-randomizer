# Lane 13 — Snow encounter completion (assignment 2)

Assignment 2 of the [next-wave dispatch](PIKMIN2_NEXT_WAVE.md) (family lane 13,
consuming dependency lanes 07/08/10). Scoped issue: reuse
[#120](https://github.com/4laric/pikmin-randomizer/issues/120) (Pikmin 2 slice:
Snow Bulborb native enemy pipeline), owner Codex via shared account `4laric`;
coordination [#186](https://github.com/4laric/pikmin-randomizer/issues/186)
(single real-GL slot — a second autonomous GL-B slot is now available).

## Pinned pair under test

| Identity | Value |
|---|---|
| Root commit | `a94fbdf9f40973cfc26ef98dca26a95c8b7d7f87` (`codex/p2-sweep437-root`) |
| Native commit | `5b446a64156b338628c6d636cab3dc76f5a9d224` |
| Executable | `C:/Users/alari/pikmin-randomizer/output/p2-integration-5b446a64/nectar.exe` |
| Executable SHA-256 | `4abdd82ada810088e95a41ded05c7e959f4aeb44d16207743a41cee65c9240a6` |
| Assets | `C:/Users/alari/bbft/dist/cohesion/pikmin/assets` |

The integration exe is a lean build: it contains the P2 runtime markers
(`P2_SNOW_GENERATED_READY`, `P2_ENEMY_READY`, `P2_SNOW_DRAW`) but **not** the
`P2GEN_SNOW_DEATH/CORPSE/SUCKME/RESULT` fixture/death instrumentation, and not
`P2GEN_SNOW_ENCOUNTER`. Machine-verifiable witnesses on the pinned pair are
therefore the spawned/live-draw markers; the lethal-fight/corpse/carry gate needs
an operator-played day.

## Exact Snow identity and asset bank

- **Source ID 45 = `YellowKochappy` (Snow Bulborb).** EnemyID 45 resolves onto
  the P1 host actor `TEKI_Chappy` (`src/plugPikiNakata/genteki.cpp:21`); Dwarf
  Orange 44 and Kochappy 1 share the host.
- **Asset bank:** shared Kochappy bank — `enemy/data/Kochappy/model.szs` +
  `anim.szs` aliased into `kochappy/` motion/collision managers, plus its own
  retail `enemy/data/yellowkochappy/enemyparm.txt` (health 150, speed 50, turn
  0.4/max 10, attack range 30, half-angle 20, bite 10; Purple impact 50/0.3/5s).

## Which behavior is P1-derived (authoritative)

Snow runs the **P1 Dwarf-Bulborb strategy on the P1 chappy host**; the P2 layer
adds visual identity, retail parameters and session registration only.
P1-derived (`src/plugPikiNakata/tekinakata.cpp:35,82-85` `TaiChappyStrategy`/
`TaiChappyParameters`, the Chappy FSM, `TEKI_Chappy` creature plumbing):
base AI FSM, collision/atari, creature registration + generator binding,
capture/mouth/swallow/bite, death & corpse (`pcEscapeNow`), carcass motion,
sounds, natural chase scheduling. P2 opt-ins: health 150 / speed 50 / 5 s stun /
attack geometry (range 30, half-angle 20). Snow never runs `pc_p2_kochappy_fsm`
(Dwarf Orange-only, default OFF).

## Registration, generated binding, teardown (native source)

- `bindSnow()` `pc_port/pc_p2_enemy.cpp:93`; `P2_ENEMY_READY` line 130; the
  post-stage sweep `P2_SNOW_GENERATED_READY dwarfs=N ... bridge=1` line 271;
  ordinary P1 binding line 282; draw `P2_SNOW_DRAW corpse=0/1` line 312.
- Teardown: `pc_p2_snow_forget(BTeki*)` line 62 erases the actor from
  `instances`, `actors` and all four policies (health/attack/turn/chase) at
  TekiMgr forget — no registration outlives the actor, so scene exit / process
  restart leaves no stale Snow references. Restart evidence below confirms it.

## Candidate QA chain (pre-admission, private)

Scope `private-snow-candidate-v1`, source 45, `product_admission=false`,
`evidence_kind=pre_admission_candidate`. Inputs were the real handoffs:
`output/lane33-candidate/snow-placement.json` (slot uid `1849273021`, stage 1,
ground, `family_lane: 13`, cohort dwarf, source_identity `campaign:dwarf:3`) and
`snow-content-manifest.json` (identities `[45]`, 121 entries).

| Step | Output | Result |
|---|---|---|
| plan | `output/qa-lane13-plan.json` | PASS (`exit 0`) |
| prepare | `output/qa-lane13-prepared.json` | PREPARED (`exit 0`; bindings `[45]`, identities 45, content 121 ok) |
| run run2 | `output/qa-lane13-01/runs/d9fc1af7…` | game booted full day-2 scene |
| run run4 | `output/qa-lane13-01/runs/519dce76…` | clean run, all runtime markers, no SeedBridgeError |
| observe | `output/qa-lane13-01/observations.json` | install PASS, natural_fight/reward/revisit/restart BLOCKED (no operator markers) |

### Observed runtime witnesses (run4 `native.log`, integration exe)

```
[Pikmin Randomizer] START_STAGE 1 day=2 color=1 stored=20
[BBFT] PIKMIN_WORLD_RENDERED
P2_SNOW_BANK poses=120 mod_bytes=1920000 texture_attach_calls=1 load_seconds=0.035 load_budget_seconds=5 budget_exceeded=0
P2_ENEMY_READY species=YellowKochappy native_family=Chappy generator=1849273021 behavior=P1
P2_SNOW_GENERATED_READY dwarfs=1 interpolation=0 bridge=1
[BBFT] PIKMIN_GAMEPLAY_READY
P2_SNOW_DRAW corpse=0
[BBFT] PIKMIN_FOH_READY day=2 field_red=20 main_engine_ap_check=0
[Pikmin Randomizer] START_COLOR_READY stage=1 color=1 field=20
[Pikmin Randomizer] START_READY stage=1 field_red=20
```

Stdout additionally carries the install witness: `PIKMIN_CONTENT_STAGED:
{'entries': 121, 'staged': 121, ...} identities=['45']`.

The day renders at 30 fps with the Snow alive (`corpse=0`) and 20 reds on the
Forest of Hope field. The BBFT background mode is render-only — it does **not**
autoplay a day — so the lethal fight to `corpse=1` did not occur within the
window and is not claimed as machine-verified on the pinned pair.

### Restart / journal-recovery proof (schema-9 p2 layout)

run4 is a fresh process on the same `--prepared`; it re-created its own
bootstrap (`runs/519dce76…`) with the identical `FINGERPRINT
3596d4c4…`, recovered run2's check journal
(`SESSION …d9fc1af7…`), and re-registered exactly one Snow (no duplicates), so
process restart restores the session without stale references.

This exposed a real restart blocker, now fixed in this repo:

- `randomizer/session.py` field-count check did not count the `ENEMY_P2 …`
  block, so any second launch of a schema-9 p2-layout session failed its own
  journal recovery (`ValueError: native journal belongs to an incompatible
  manifest`). The formula now adds `4 + 2 × p2_layout.bindings`, matching
  `experimental/pikmin2_seed_bridge.build_bootstrap`.
- The overlay/tracker subprocess did not inherit the candidate's in-process
  `admitted_ids` patch → `SeedBridgeError: [45]` in the run log. `admitted_ids`
  now honors `PIKMIN_P2_ADMITTED_IDS` (set by `candidate_session run` for the
  process tree only), and the candidate CLI exports it, so the overlay validates
  consistently. The product path is unchanged (env never set there).

## Historical lifecycle evidence reproduced (fixture scope)

The `p2-lane13-snow-life` tree reproduces the full lifecycle with fixture
instrumentation on Snow builds (e.g. fixture build `34182d17…`):
`P2GEN_SNOW_DEATH frame=9`, `P2GEN_SNOW_CORPSE frame≈106`, `P2GEN_SNOW_SUCKME`,
`P2_SNOW_DRAW corpse=1`, `PASS P2GEN_SNOW_ENCOUNTER`, and the 10-stage repro
`repro-run-1/evidence.json` (live draw, attack, death, corpse draw, carried,
combat, native delivery, duplicate credit, ledger exact, binary identity).
This is fixture-scope evidence, not final natural acceptance per the fan-out.

## Connection to assignment 1 (ordinary spawn)

Assignment 1 (#459) integrated the generated Snow spawn connection; the content
manifest used here (identities `[45]`, 121 entries across `snow_*.mod` banks) is
that a1 handoff. The candidate run stages the same content
(`PIKMIN_CONTENT_STAGED identities=['45']`) and reaches the ordinary generated
spawn path (`ENEMY_P2` bootstrap binding target `1849273021` → native
`P2_ENEMY_READY generator=1849273021`), so lane-13 spawn evidence extends the a1
chain: generate → stage → ordinary native spawn → live draw.

## Gates and pending items

- [x] Pinned pair verified (exe exists + SHA matches).
- [x] plan/prepare PASS — real a1/a3 handoffs used.
- [x] Clean integration-exe run: spawn, registration (`behavior=P1`), live draw,
      restart/journal recovery.
- [x] Overlay admission consistency + p2 session field-count fixes committed.
- [ ] **Operator gate:** play the generated-session day (interactive GL-A) to
      machine-witness the natural kill (`P2_SNOW_DRAW corpse=1`), corpse carry
      and delivery, then record operator-declared markers and re-run `observe`
      (natural_fight/reward stages) + `records --kind natural`.
- [ ] Lane 02/33 reviewed admission of source 45 → product plan/prepare/records.

Session: `p2-lane13-snow-01`; scope `output/qa-lane13-prepared.json`; session dir
`output/qa-lane13-01` (dirs `d9fc1af7…` run2, `519dce76…` run4, `4b89e6bb…`
DLL-probe, `22a4888c…` prepare-time). Run recipe: `py -3.12 -m
experimental.pikmin2_candidate_session run --prepared output/qa-lane13-prepared.json`
from `p2-sweep437-root` with `PYTHONUTF8=1`, `PIKMIN_P2_ROOM_WINDOW=960x540`,
`PIKMIN_RANDOMIZER_TEST_BACKGROUND=1`, `SDL_AUDIODRIVER=dummy`, and PATH prefix
`C:\msys64\mingw64\bin` (the four runtime DLLs: SDL2, libgcc_s_seh-1,
libstdc++-6, libwinpthread-1). `PIKMIN_P2_ADMITTED_IDS=45` is now exported by
the CLI itself.