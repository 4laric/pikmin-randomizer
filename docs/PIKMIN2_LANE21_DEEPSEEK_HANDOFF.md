# Pikmin 2 lane 21 (Groink) DeepSeek handoff — fix4

Lane 21 — Gatling Groink (`MiniHoudai` 78 / `FminiHoudai` 97). Tracking #198;
candidate reuse #204–#210. Executing agent: opencode (deepseek-v4-pro), 2026-09-14.
Implementation owner: Codex through shared account `4laric`.

## Slice delivered

Resume the parked Codex Groink carcass policy (`pc_p2_groink_carcass` +
`pc_p2_groink_lifetime`), bind it to a live generated actor sidecar
(`pc_p2_groink_teki`), and prove the death/corpse recovery timeline in a real-GL
run. The native branch was merged from `claude/p2-deepseek-wave-native` (lanes
06–32) keeping both the lane-12 `pc_p2_king_teki` and lane-21
`pc_p2_groink_teki` hooks. The prior review's blockers are fixed: the birth
marker's binding-erase is now observed through a process-wide tally, the frame
budget is met by short sidecar parameters, and the GL scenario is actually run.

## Concrete source IDs (six-gate tables)

> The fix4 six-gate tables were superseded by the **Slice 3** tables at the end of
> this document (MiniHoudai death/corpse now a natural PASS, transport BLOCKED).
> The authoritative handoff tables are the Slice 3 ones; the fix4 tables below are
> retained only as history and are not the ingest tables.
>
> (fix4 history: 78 MiniHoudai and 97 FminiHoudai were both all-injected/UNTESTED,
> death/corpse UNTESTED (injected pcEscapeNow kill).)

## Honest labelling (review item 4)

The BECOME chain follows an injected kill. `tools/p2_groink_runtime.cpp` writes
`mHealth = 0` then `pcEscapeNow()` on the generated Frog and logs
`P2_GROINK_CARCASS_KILL_INJECTED method=pcEscapeNow`; the Frog leaves a real
corpse pellet (`TaiOtimotiParameters` `TEKICORPSE_LeaveCorpse`), and the
`P2_GROINK_CARCASS_READY/BECOME/GAUGE_ACTIVE/KILL_PELLET/BIRTH` markers then run
**naturally on that corpse** (the regrowth is real, only the kill is injected).
So the previous wording "natural `P2_GROINK_CARCASS_*` markers" is corrected to
"natural revival timeline after a labelled injected kill"; gate 4 stays UNTESTED.

## Ordered commits and dirty state

Root base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`; native base
`b805d9c626e4f4558c95aef7cac311a5d9a2068f`. Both clean at handoff.

Native (`deepseek/p2-l21-native`):
1. `45697128` — cherry-pick `codex/p2-groink-carcass` @ `8324a5a0` (carcass policy).
2. `016a3b77` — cherry-pick `codex/p2-groink-lifetime` @ `14d9391d` (registration guard).
3. `5f5cf5fe` — birth descriptor + CMake test wiring.
4. `b3f784e9` — bind carcass policy to a live generated actor sidecar.
5. `e22e075d` — [hook] wire sidecar into shared teki lifecycle hooks.
6. `12298fd5` — review fixes 2: pellet recycle guard, corpse-type gate, honest birth wording.
7. `3e9f52be` — review fixes 3: snapshot birth before pellet kill, fix use-after-free.
8. `53916b1c` — review fixes 3: carcass automatic-binding runtime scenario.
9. `6581ddfe` — merge `claude/p2-deepseek-wave-native` (lanes 06–32), keeping both `pc_p2_groink_teki` and `pc_p2_king_teki` in `gameCoreSection.cpp`.
10. `dfdccbfe` — review fixes 4: process-wide birth counter surviving pellet-kill forget.
11. `eef03f93` — review fixes 4: poll the process-wide tally independent of the frog generator.

Root (`deepseek/p2-l21`):
1. `895124b` — carcass-policy Python twin/tests/doc (superseded API, kept in history).
2. `cd0c59f` — fix1 handoff (superseded).
3. `795b208` — resume parked carcass API in the Python twin/tests/doc.
4. `5b27c79` — fix1 handoff.
5. `8d8db52` — pin fix1 handoff head hash.
6. `af4b599` — drop lane-private paths from the Groink carcass doc.
7. `c711545` — root validator guarding the carcass-birth marker.
8. `ea78fd0` — slice-2 handoff for live carcass-actor binding.
9. `857f11a` — review fixes 2: ordered run-log validator + sidecar config writer.
10. `e5da007` — review fixes 2: slice-2 handoff honesty and placeholders.
11. `f7f9b62` — review fixes 3: hygiene placeholders, [hook] label, validator cleanup.
12. `e3ffce3` — review fixes 3: slice-2 handoff update.
13. `988c7ab` — review fixes 4: short sidecar helper + injected-kill marker validator and tests.
14. (this handoff commit) — review fixes 4: fix4 handoff.

## Interfaces and hooks touched

Merged wave keeps lane 12's `include "pc_p2_king_teki.h"` and
`pc_p2_king_teki_setup()` beside lane 21's `pc_p2_groink_teki.h` /
`pc_p2_groink_teki_setup()` (`src/plugPikiKando/gameCoreSection.cpp`). The
`pc_p2_groink_teki` sidecar exposes a new process-wide probe
`pc_p2_groink_teki_total_births()` (survives `pc_p2_groink_teki_forget`); the
per-actor `timer`/`health`/`births`/`is_bound` probes are unchanged. No other
shared file was edited beyond the merge.

## Build evidence

- `output/dsw/l21-build-evidence.txt`: `pikmin_pc` built at the merged head,
  `bin/nectar.exe` sha256 `86d84a2fb80828d0884290e9b3c066170ed279fcef0ba751ce4e1e79ec1fa628`,
  `ninja -n` = `ninja: no work to do.` (eef03f93 only edits the fixture source,
  not a product TU, so the product freshness carries over).
- Fixture: `scripts/build_pikmin2_fixture.py` (expected native head `eef03f93`)
  → `output/dsw/l21-out/groink-carcass-fixture5/fixture.exe` sha256
  `3806c96c1e2f10c3bd01072db43719436bffe1066b49f5317def5fc6a0de69fd`.

## Runtime evidence (real-GL, `slot.py run gl l21`)

Run directory `output/dsw/l21-out/run-carcass-binding2/`, native.log starts with
`SDL2 Window ... (960x540)` + `Experimental preview window set to 960x540 windowed
and centered`, no extinction. Ordered markers (native.log line numbers):

```
715  P2_GROINK_CARCASS_READY generator=201001 type=0 gauge_delay=2.000 recovery=3.000 max_health=1200.000
1268 P2_GROINK_CARCASS_KILL_INJECTED host=generated_Frog generator=201001 method=pcEscapeNow health_write=1
1269 P2_GROINK_CARCASS_BECOME generator=201001 pos=-150.000,0.000,1850.000 face_dir=0.000
1278 P2_GROINK_CARCASS_GAUGE_ACTIVE generator=201001 timer=2.017
1293 P2_GROINK_CARCASS_KILL_PELLET generator=201001 health=1206.351
1294 P2_GROINK_CARCASS_BIRTH generator=201001 pos=-150.000,0.000,1850.000 face_dir=0.000 existence_length=-1.000 in_piklopedia=0 health=1206.351
1295 P2_GROINK_CARCASS_BIRTH_PASS ticks=162 total_births=1
1296 PASS GROINK_RUNTIME carcass_automatic_binding
```

The short sidecar (`sidecar_config(201001, 0, gauge_delay=2.0,
recovery_seconds=3.0)`) is what makes the 1200-tick budget reachable (documented
choice: shorter sidecar values, budget unchanged). Note `health=1206.351` at
KILL_PELLET exceeds `max_health=1200` — confirming the policy does not clamp,
as the source does not.

## Tests

- Native CTest: `ctest --test-dir output/dsw/native-l21-build -R p2_groink` →
  11/11 PASS (log `output/dsw/l21-out/ctest-groink-fix4.log`). The earlier
  `ctest-groink-slice2.log` (21:52) predates `3e9f52be`/`53916b1c`, so it is not
  cited here.
- Root Python: `tests/test_pikmin2_groink_carcass.py` +
  `tests/test_pikmin2_groink_carcass_teki.py` → 29 passed, 1 skipped.

## Assumptions

- The kill is injected (`pcEscapeNow`) because the isolated preview pauses the
  ordinary Teki-manager update, so no natural squad kill can run; this is
  surfaced as `KILL_INJECTED` and gate 4 stays UNTESTED. Remove the `mHealth=0`
  write once a natural combat slice lands (natural targeting/burst, the skipped
  next-wave item).
- Short sidecar values (2s gauge + 3s recovery) are the documented budget choice;
  the 1200-tick / 1800-frame budgets are unchanged.

## Remaining blockers (provider lane)

- Natural targeting/burst/shell effects (the next-wave order) were skipped; they
  need the live MiniHoudai actor over `teki.h`/`tekimgr.cpp`/`gameCoreSection.cpp`
  (lane 01; lane 20 primitives, #128 angle-aware bake).
- Carcass pellet drop (`EnemyBase::onKill`) and `generalEnemyMgr->birth` +
  Rebirth transit (lane 06/07).

## Subagent usage

Three parallel subagents, per the brief:
1. `explore` — source audit (frog corpse/pellet flow, `TEKICORPSE_LeaveCorpse`,
   `sys->getDeltaTime()` vs `gsys->getFrameTime()`). Used as-is; grounding that
   the port rehosts the policy timestamp and that the frog leaves a real corpse.
2. `explore` — inventory + merge-conflict surface. Used as-is; it confirmed the
   merge is one additive conflict in `gameCoreSection.cpp` (keep both includes +
   both `_setup()` calls), which I resolved exactly as described.
3. `general` — root-side validator/test additions (`sidecar_config_short`,
   `is_injected_kill`, `injected_kill_label` + 5 tests, 14 pass/1 skip). Used
   as-is.

The delegation offloaded the read-heavy source/inventory work and the Python
port; my context stayed on the native merge, the birth-counter fix, the GL run
and this handoff.

## check_p2_handoff_gates output

`py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_LANE21_DEEPSEEK_HANDOFF.md` (exit 0):

```
78 MiniHoudai (role=source):
  1. identity_spawn     ignored [N/A]
  2. movement_animation ignored [UNTESTED]
  3. attacks_receivers  ignored [UNTESTED]
  4. death_corpse       ignored [UNTESTED]
  5. transport_reward   ignored [N/A]
  6. cleanup_reentry    ignored [BLOCKED]
97 FminiHoudai (role=source):
  1. identity_spawn     ignored [N/A]
  2. movement_animation ignored [UNTESTED]
  3. attacks_receivers  ignored [UNTESTED]
  4. death_corpse       ignored [UNTESTED]
  5. transport_reward   ignored [UNTESTED]
  6. cleanup_reentry    ignored [BLOCKED]
```

## Reproduction

```
cd C:/Users/alari/pikmin-randomizer/output/deepseek-wave
$env:PATH="C:/msys64/mingw64/bin;"+$env:PATH
py -3.12 slot.py run gl l21 -- py -3.12 C:/Users/alari/pikmin-randomizer/output/dsw/l21-out/run_carcass_binding.py
```

## Slice 3

Natural free-mode squad kill for the Groink death/corpse gate, a Groink corpse
Pod receipt hook, and CTest coverage for the engine-side sidecar.

### Source ID: 78 `MiniHoudai`

Superseded by the Slice 4 table at the end of this document (gate 5 is now a
natural carcass -> Pod receipt). Retained only as history.

| Gate | Historical note | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | N/A | no live MiniHoudai actor is spawned; the P2 carcass policy is bound to a generated Frog actor by p2-groink-teki.txt | - |
| 2. Autonomous movement and animation | UNTESTED | locomotion + Rebirth animation (AnimID 7) remain on the shared teki actor hook | - |
| 3. Attacks and receivers | UNTESTED | strike bridge integrated; in-flight moving hits remain fixture-pinned | - |
| 4. Death and corpse | PASS (natural) | output/dsw/l21-out/run-carcass-natural3/native.log:1275 | natural (free-mode squad kill; life-clamp parameter override) |
| 5. Actual transport and reward | BLOCKED | output/dsw/l21-out/run-carcass-transport2/native.log:722 | - |
| 6. Cleanup and re-entry | BLOCKED | generalEnemyMgr->birth + MINIHOUDAI_Rebirth transit on lane 06/07 | - |

### Source ID: 97 `FminiHoudai`

Superseded by the Slice 4 table at the end of this document. Retained only as
history.

| Gate | Historical note | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | N/A | no live pedestal Groink actor is spawned; shares the same policy binding | - |
| 2. Autonomous movement and animation | UNTESTED | not run separately | - |
| 3. Attacks and receivers | UNTESTED | not run separately | - |
| 4. Death and corpse | UNTESTED | not run separately | - |
| 5. Actual transport and reward | UNTESTED | not run separately | - |
| 6. Cleanup and re-entry | BLOCKED | generalEnemyMgr->birth + Rebirth transit on lane 06/07 | - |

Gate 4 (MiniHoudai) is now a natural PASS: the P1 Frog `TEKI_Frog` actor at
generator 201001 is killed by a free-mode squad of red Pikmin (lane 19 recipe:
park the captain, ring-deploy on a 22-unit circle, re-ring every 120 ticks, no
Pikmin action assigned, **no health write**). Because that 800 HP actor kills the
squad in some runs and dies in others, its max life is capped through the
`pc_p2_groink_teki_param_f` parameter-override seam (chained in `teki.h`, like
lane 24's King) — a parameter override, not a health write. The natural death is
`P2_FROG_DEAD`, then the frog's own dead clip finalizes the corpse
(`pcEscapeNow`), and the carcass sidecar runs BECOME -> GAUGE_ACTIVE ->
KILL_PELLET -> BIRTH to completion.

Transport (gate 5): `pc_p2_groink_receipt` is implemented and hooked as one
labelled branch in `pc_p2_preview_deliver` (`corpse:groink:<gen>`), and a Pod was
staged over the Frog arena (`P2_POD_READY treasure=dia_a_red`, run log :722).
The free squad did **not** carry the dropped corpse to the Pod in the captured
runs (pokos stayed 0 over 2400 ticks), so gate 5 is BLOCKED rather than PASS.

Fixture4 note (review item 3): the earlier `run-carcass-binding` (fixture4) timed
out because it re-looked up the dead Frog by generator after death (the generator
clears); the process-wide tally fix made it poll `pc_p2_groink_teki_total_births()`
instead.

### Ordered commits (Slice 3)

Native (`deepseek/p2-l21-native`):
1. `3e97037a` — natural free-mode squad kill, engine-free birth counter, CTest sidecar compile coverage.
2. `178971b3` — Groink corpse Pod receipt hook in the shared delivery chain.
3. `bf7e8f7c` — raise natural-kill budget for the corpse-finalization + regrowth tail.
4. `a5262011` — preview-gated life-clamp parameter override for the natural kill.
5. `9b0c4669` — carcass transport scenario (natural corpse carry to the Pod).
6. `fcd281c3` — keep the free squad on the corpse until grasped for transport.

Root (`deepseek/p2-l21`):
1. `cfe440e9` — slice 3: receipt and natural-death validator helpers with tests.
2. (this handoff commit) — slice 3 handoff.

### Build and test evidence

- `output/dsw/l21-build-evidence.txt`: `pikmin_pc` built at native `a5262011`,
  `bin/nectar.exe` sha256 `75c76fec7b00a5bf6c18cb83a9ede58e3f2d3a7d8863249011a4095fda791590`,
  `ninja -n` = `ninja: no work to do.`
- Fixture: `groink-carcass-fixture9` (natural kill) sha256 `09529e77…`;
  `groink-carcass-fixture11` (transport) sha256 `c966272c…`
  (`scripts/build_pikmin2_fixture.py`).
- Native CTest: 11/11 `p2_groink*` PASS (log `output/dsw/l21-out/ctest-groink-slice3.log`),
  including `p2_groink_teki_test`, which now also compiles the sidecar as an
  object-only library (`p2_groink_teki_sidecar`) so a sidecar source regression
  fails the test build.
- Root Python: `tests/test_pikmin2_groink_carcass.py` +
  `tests/test_pikmin2_groink_carcass_teki.py` -> 35 passed, 1 skipped.

### Real-GL evidence (natural kill, `slot.py run gl l21`, exit 0)

`output/dsw/l21-out/run-carcass-natural3/native.log` (960x540 windowed and
centered, no extinction):

```
715  P2_GROINK_CARCASS_READY generator=201001 type=0 gauge_delay=2.000 recovery=3.000 max_health=1200.000
1268 P2_GROINK_CARCASS_HOST_BOUND ... kill=free_mode_squad health_write=0 host_life_clamp=120
1275 P2_GROINK_CARCASS_BECOME generator=201001
1293 P2_FROG_DEAD species=Frog generator=201001 health=0
1321 P2_GROINK_CARCASS_GAUGE_ACTIVE generator=201001 timer=2.009
1337 P2_GROINK_CARCASS_KILL_PELLET generator=201001 health=1201.402
1338 P2_GROINK_CARCASS_BIRTH generator=201001 ...
1340 P2_GROINK_CARCASS_BIRTH_PASS ticks=447 total_births=1
1341 PASS GROINK_RUNTIME carcass_natural_kill
```

### Subagent usage (Slice 3)

Three parallel subagents, per the brief:
1. `explore` — source audit (Pikmin attack -> Teki damage path, red attack power,
   `mHealth` vs `TPF_Life` lifecycle, lane 24's King param seam, free-mode deploy
   API). Used as-is; it established that a lowered `TPF_Life` clamps `mHealth`
   down on the next update, which is why the life-clamp works.
2. `explore` — inventory/fixtures (lane 19 ring recipe, lane 13 Pod witness, the
   receipt chain, the Groink sidecar map, the CMake test link). Used as-is.
3. `general` — extended `experimental/pikmin2_groink_carcass_teki.py` +
   `tests/test_pikmin2_groink_carcass_teki.py` with `has_groink_receipt`,
   `groink_receipt_generator`, `natural_death_timeline` and tests (20 passed/1
   skipped at the time). Used as-is.

Net: the delegation covered the read-heavy audit/inventory and the Python
validator; my context stayed on the native kill/transport/CMake work and the GL
runs.

### slice3 check_p2_handoff_gates output

`py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_LANE21_DEEPSEEK_HANDOFF.md` (exit 0):

```
78 MiniHoudai (role=source):
  1. identity_spawn     ignored [N/A]
  2. movement_animation ignored [UNTESTED]
  3. attacks_receivers  ignored [UNTESTED]
  4. death_corpse       accepted [PASS]
  5. transport_reward   ignored [BLOCKED]
  6. cleanup_reentry    ignored [BLOCKED]
97 FminiHoudai (role=source):
  1. identity_spawn     ignored [N/A]
  2. movement_animation ignored [UNTESTED]
  3. attacks_receivers  ignored [UNTESTED]
  4. death_corpse       ignored [UNTESTED]
  5. transport_reward   ignored [UNTESTED]
  6. cleanup_reentry    ignored [BLOCKED]
```

## Slice 4 — natural carcass -> Pod receipt LANDED

The Slice 3 transport blocker is resolved. The lane's transport profile now
drives the killed host's own corpse pellet to the Research Pod natively: the
`pc_p2_groink_teki` sidecar parks the captain beyond the 250u join-party range
and re-rings the survivors onto the corpse pellet in FreeMode every 60 ticks
until a carrier latches (`Piki::graspSituation`), holds the corpse at the kill
site, forces `carry_min` to 1, and re-forms the squad after the Pod credits the
carcass. The goal is the preview Pod (`aiTransport::decideGoal` ->
`pc_p2_preview_goal()`), and `pc_p2_preview_deliver` calls
`pc_p2_groink_receipt` for `corpse:groink:<gen>`. No delivery endpoint is called
directly and no health is written.

### Ordered commits (Slice 4)

Native branch `deepseek/p2-l21-native` (base `7ed95228`, fast-forward merge of
`claude/p2-deepseek-wave-native`; clean):

1. `d7f608e1` — `lane21: natural carcass -> Pod receipt: transport tail (park
   captain, free-mode ring, carry_min 1, re-form) (#198)` — adds the optional
   `transport` sidecar token (`pc_p2_groink_teki_policy.h`), the carcass
   transport tail in `pc_port/pc_p2_groink_teki.cpp`, the receipt delivery flag,
   and hands the post-kill captain/squad ownership from the fixture to the
   sidecar (`tools/p2_groink_runtime.cpp`).

Root branch `deepseek/p2-l21` (base `6caa8d01`; clean):

1. (this commit) — `lane21: stage/run Groink carcass transport, six-gate table (#198)` —
   new `experimental/pikmin2_groink_transport_run.py` (base-squad expansion to 40
   + `transport` sidecar + Pod cargo staging + GL run) and this handoff.

### Build evidence

- `build_lane.py l21` at native `d7f608e1`: `dirty=no`,
  `bin/nectar.exe` sha256 `754fe59a89f383e1f6ac16c55f9dfbbab9f73792455de7ab93e3eeea40c3ef8b`,
  `ninja -n` = `ninja: no work to do.`
- Fixture (`scripts/build_pikmin2_fixture.py`, expected head `d7f608e1`) →
  `output/dsw/l21-out/groink-transport-fixture/fixture.exe` (`status: built`).

### Real-GL runtime evidence (executed, exit 0)

Run via `slot.py run gl l21 -- py -3.12 experimental/pikmin2_groink_transport_run.py`
at `PIKMIN_P2_ROOM_WINDOW=960x540`; log
`output/dsw/l21-out/run-carcass-transport3/native.log`:

```
:723  [Pikipelago] P2_POD_READY treasure=dia_a_red value=180 weight=15 capacity=25 pokos=0
:1275 P2_GROINK_CARCASS_HOST_BOUND ... kill=free_mode_squad health_write=0 host_life_clamp=120
:1276 P2_GROINK_CARCASS_RING tick=1 reds=40 health=0.0
:1277 P2_FROG_DEAD species=Frog generator=201001 health=0
:1279 P2_GROINK_CARCASS_BECOME generator=201001 pos=-150.000,0.000,1850.000 face_dir=0.000
:1302 P2_GROINK_CARCASS_CORPSE_CONFIG carry_min=7 carry_max=14 min_free_slot=0 alive=1
:1303 P2_GROINK_CARCASS_CAPTAIN_PARK x=-150.000 z=2150.000
:1304 P2_GROINK_CARCASS_FREE_RECRUIT count=40 carriers=0 squad=40
:1308 P2_GROINK_CARCASS_CORPSE tick=30 x=-149.540 z=1832.987 moved=17.019 carriers=40
:1346 P2_GROINK_CARCASS_CORPSE tick=270 x=-285.628 z=1444.301 moved=427.770 carriers=25
:1371 P2_GROINK_CARCASS_CORPSE tick=420 x=-496.701 z=1451.072 moved=528.531 carriers=11
:1378 [Pikipelago] P2_POD_RECEIPT id=corpse:groink:201001 value=2 new=1 pokos=2 seeds=0
:1379 P2_GROINK_CARCASS_HOST tick=629 health=0.0 bound=0 reds=29 pokos=2 transport=11
:1380 P2_GROINK_CARCASS_TRANSPORT_PASS ticks=629 pokos=2
:1381 PASS GROINK_RUNTIME carcass_transport
```

Reading: 40 reds kill the generated Frog (`P2_FROG_DEAD` :1277) with no health
write; the dead actor's own corpse pellet spawns with `carry_min=7 carry_max=14`
and `min_free_slot=0`; the captain is parked at (-150.0, 2150.0) (300u beyond
the corpse); 40 survivors are released FreeMode onto the corpse; carriers latch
(40 -> 25 -> 11) and haul it 17 -> 528 units to the Pod; the Pod credits
`corpse:groink:201001` (value 2, pokos 0 -> 2).

### Source ID: 78 `MiniHoudai`

| Gate | Historical note | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | N/A | no live MiniHoudai actor is spawned; the P2 carcass policy is bound to a generated Frog generator 201001 | - |
| 2. Autonomous movement and animation | UNTESTED | locomotion + Rebirth animation (AnimID 7) remain on the shared teki actor hook | - |
| 3. Attacks and receivers | UNTESTED | strike bridge integrated; in-flight moving hits were not re-run this slice | - |
| 4. Death and corpse | PASS | output/dsw/l21-out/run-carcass-transport3/native.log:1277 P2_FROG_DEAD and :1279 P2_GROINK_CARCASS_BECOME (natural free-mode squad kill) | natural |
| 5. Actual transport and reward | PASS | output/dsw/l21-out/run-carcass-transport3/native.log:1378 P2_POD_RECEIPT id=corpse:groink:201001 value=2 new=1 pokos=2 seeds=0 | natural |
| 6. Cleanup and re-entry | BLOCKED | generalEnemyMgr->birth + MINIHOUDAI_Rebirth transit on lane 06/07 | - |

### Source ID: 97 `FminiHoudai`

| Gate | Historical note | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | N/A | no live pedestal Groink actor is spawned; shares the same policy binding | - |
| 2. Autonomous movement and animation | UNTESTED | not run separately | - |
| 3. Attacks and receivers | UNTESTED | not run separately | - |
| 4. Death and corpse | UNTESTED | not run separately | - |
| 5. Actual transport and reward | UNTESTED | not run separately | - |
| 6. Cleanup and re-entry | BLOCKED | generalEnemyMgr->birth + Rebirth transit on lane 06/07 | - |

Honest labels: gate 5 is a natural FreeMode grasp -> `aiTransport` route ->
`pc_p2_preview_deliver` Pod credit. Fixture concessions: (1) the carcass
`carry_min` is forced to 1 (`pc_p2_groink_teki.cpp`; the source pellet config
read 7/14 and 40 carriers latched anyway); (2) the staged starting squad is
expanded from 20 to 40 reds, because the area-landing attack thins a 20-red
squad before the carry completes; (3) the generated identity is the lane-16
staged Frog actor (EnemyID 78 is not spawned), so gate 1 stays `N/A`; (4) the
kill-phase deploy + captain park is applied locomotion, while the grasp, route
and Pod credit are the natural engine path. No injected delivery fallback
remains.

### slice4 check_p2_handoff_gates output

`py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_LANE21_DEEPSEEK_HANDOFF.md` from
`output/dsw/wave-root` (exit 0):

```
78 MiniHoudai (role=source):
  1. identity_spawn     ignored [N/A]
  2. movement_animation ignored [UNTESTED]
  3. attacks_receivers  ignored [UNTESTED]
  4. death_corpse       accepted [PASS]
  5. transport_reward   accepted [PASS]
  6. cleanup_reentry    ignored [BLOCKED]
97 FminiHoudai (role=source):
  1. identity_spawn     ignored [N/A]
  2. movement_animation ignored [UNTESTED]
  3. attacks_receivers  ignored [UNTESTED]
  4. death_corpse       ignored [UNTESTED]
  5. transport_reward   ignored [UNTESTED]
  6. cleanup_reentry    ignored [BLOCKED]
```

## Slice 5 — live movement/animation and receiver witnesses (lane 21)

The two remaining non-corpse gates are closed on the generated actor itself. A
new lane-local fixture mode (`tools/p2_groink_runtime.cpp --groink-live`) leaves
the generated Frog at generator 201001 alive and lets its own source FSM (lane
16, wired into `BTeki::update`) drive it: no squad is ringed, no damage is
written and no kill is injected. The staged starting squad is already inside the
actor's sight, so it turns, hops and lands on its own. A read-only probe
(`pc_p2_frog_probe`, `pc_port/pc_p2_frog.cpp`) reports the running source-FSM
state, the current animation clip and the clip phase, and a per-Piki witness
records each live target's `mHealth`/`PIKISTATE` change caused by the source
`InteractPress` landing.

Run via the GL slot at `PIKMIN_P2_ROOM_WINDOW=960x540`; log
`output/dsw/l21-out/run-groink-live/native.log` (exit 0):

```text
:1269 P2_GROINK_MOVE generator=201001 tick=30 x=-150.000 y=0.000 z=1850.000 travel=0.000 state=wait clip=wait1 phase=0.945 health=800.0
:1305 P2_GROINK_MOVE generator=201001 tick=90 x=-147.107 y=42.922 z=1850.498 travel=2.937 state=jumpwait clip=wait2 phase=0.316 health=575.0
:1313 P2_FROG_LAND species=Frog radius=23.0 bittered=0 pikmin=3 navi=0 behavior=source
:1314 P2_GROINK_TARGET_HIT id=2835558504432 health=30.0->20.0 state=22->33 alive=1->1 x=-133.685 z=1855.977
:1319 P2_GROINK_MOVE generator=201001 tick=120 x=-143.177 y=0.000 z=1851.043 travel=10.256 state=attack clip=attack phase=0.283 health=575.0
:1453 P2_FROG_LAND species=Frog radius=23.0 bittered=0 pikmin=2 navi=0 behavior=source
:1455 P2_GROINK_TARGET_HIT id=2835558504432 health=10.0->0.0 state=22->33 alive=1->0 x=-117.181 z=1852.338
:1566 P2_GROINK_LIVE_PASS ticks=600 travel=84.377 health_drops=18 state_changes=151
:1567 PASS GROINK_RUNTIME groink_live
```

Reading: the generated actor travels 84.377 units over 600 ticks while the
source FSM cycles wait->turn->jump->jumpwait->fall->attack->wait with the matching
clips (wait1/type1/wait2/type2/attack/waitact1) and per-clip phase; the landing
press (`behavior=source`) applies the engine `InteractPress` to the live Pikmin
inside the source head radius (23u), dropping one 30->20 and then 10->0 HP with
the `PIKISTATE` change 22->33 and alive 1->0. No health write, ring or injected
hit is involved; the only fixture input is the staged starting squad from the
lane-16 base session.

### Source ID: 78 `MiniHoudai`

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | N/A | no live MiniHoudai actor is spawned; the P2 carcass policy is bound to a generated Frog generator 201001 | - |
| 2. Autonomous movement and animation | PASS | output/dsw/l21-out/run-groink-live/native.log:1269,:1305,:1319,:1566 P2_GROINK_MOVE (position + source-FSM state + clip + phase; travel 0 -> 84.377 over 600 ticks) | natural |
| 3. Attacks and receivers | PASS | output/dsw/l21-out/run-groink-live/native.log:1313 P2_FROG_LAND radius=23.0 pikmin=3 behavior=source and :1314 P2_GROINK_TARGET_HIT health=30.0->20.0 state=22->33 alive=1->1 (and :1455 health=10.0->0.0 alive=1->0) | natural |
| 4. Death and corpse | PASS | output/dsw/l21-out/run-carcass-transport3/native.log:1277 P2_FROG_DEAD and :1279 P2_GROINK_CARCASS_BECOME (natural free-mode squad kill) | natural |
| 5. Actual transport and reward | PASS | output/dsw/l21-out/run-carcass-transport3/native.log:1378 P2_POD_RECEIPT id=corpse:groink:201001 value=2 new=1 pokos=2 seeds=0 | natural |
| 6. Cleanup and re-entry | BLOCKED | the binding is forgotten on the engine death funnel (output/dsw/l21-out/run-carcass-transport3/native.log:1379 bound=0 after the natural kill); re-entry needs a new born actor, which the shared P2 manager birth does not provide here (pc_port/pc_p2_groink_teki.cpp:287 RequestBirth records a descriptor and defers the birth to the shared hook; no generalEnemyMgr birth / MINIHOUDAI_Rebirth transit on lane 06/07) | - |

### Source ID: 97 `FminiHoudai`

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | N/A | no live pedestal Groink actor is spawned; shares the same policy binding | - |
| 2. Autonomous movement and animation | UNTESTED | not run separately | - |
| 3. Attacks and receivers | UNTESTED | not run separately | - |
| 4. Death and corpse | UNTESTED | not run separately | - |
| 5. Actual transport and reward | UNTESTED | not run separately | - |
| 6. Cleanup and re-entry | BLOCKED | generalEnemyMgr->birth + MINIHOUDAI_Rebirth transit on lane 06/07 | - |
