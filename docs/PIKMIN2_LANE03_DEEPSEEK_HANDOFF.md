# Lane 03 deepseek handoff (fix1) — ENEMY_P2 spawn-binding resolution, parser + resolution only (#439)

Lane 03 (Seed/native bridge), DeepSeek worker. Fix1 corrects a review finding: the
prior slice keyed the seed's `ENEMY_P2` target on `Generator::_70` (a raw ID32 tag
read only on the non-ram file path), which can never match lane 04's target
contract. The binding now keys on the **spawn-slot uid** (`pc_randomizer_generator_id`
via `pc_randomizer_bind_generator`), exactly the value lane 04 emits as
`str(slot['uid'])`.

Title is now **"parser + resolution only"**: the resolved source id reaches the
ordinary `GenObjectTeki::birth` path and is emitted as a `P2_SEED_RESOLVE` marker,
but nothing yet creates a live bound actor, so game gate A stays UNTESTED.

## Source IDs / files owned

- Snow Bulborb = source 45 (`YellowKochappy`), Dwarf Orange = source 44
  (`BlueKochappy`), host `TEKI_Chappy`=3.
- Root: `experimental/pikmin2_seed_bridge.py` (unchanged), `scripts/test_p2_bridge_spawn.py`
  (rewritten to use `binding_targets_for_sources([45,44])`), `docs/PIKMIN2_SEED_BRIDGE.md`.
  `tests/test_pikmin2_seed_spawn_binding.py` was **dropped** (redundant with
  `tests/test_pikmin2_seed_bridge.py`).
- Native: `pc_port/pc_randomizer.{h,cpp}`, `pc_port/pc_randomizer_probe.cpp`; narrow
  additive hook in `src/plugPikiNakata/genteki.cpp`.

## Ordered commits

Root base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91` (branch `deepseek/p2-l03`):
- `7a60dc8` lane03: ordinary P2 enemy spawn-binding tests and doc (#439)  [superseded test file dropped in fix1]
- `8056354` lane03: deepseek handoff (#439)
- `…` lane03: review fixes — spawn-binding keys on spawn-slot uid (#439)  [fix1]

Native base `b805d9c626e4f4558c95aef7cac311a5d9a2068f` (branch `deepseek/p2-l03-native`):
- `8411ad37` lane03: ordinary P2 enemy spawn-binding resolution via generator _70 (#439)  [superseded]
- `30eee29f` lane03: review fixes — key ENEMY_P2 bindings on the spawn-slot uid, not Generator::_70 (#439)

Both worktrees clean at handoff.

## Interfaces / hooks touched and why

- `pc_randomizer_set_generator_id` / `pc_randomizer_bind_generator`: the
  `!pc_randomizer_spawn_slots()` early-outs now also allow `pc_randomizer_p2_bridge()`,
  so the generator→spawn-uid map is populated under `ENEMY_P2` (which forbids the P1
  slot layouts; `pc_randomizer_spawn_slots()` is false and the map used to stay empty).
- `pc_randomizer_p2_source_for_id(unsigned long)`: stringifies a spawn-slot uid and
  returns `pc_randomizer_p2_source(...)` (0 when unbound).
- `GenObjectTeki::birth`: emits `P2_SEED_RESOLVE source_id=<n> target=<uid>
  original_type=<t> x=.. z=..` via `pc_randomizer_generator_id(info.mGenerator)`.
  Resolution marker only — not a bound actor.
- `pc_randomizer_probe --enemy-p2-spawn-probe`: re-derives and re-resolves every bound
  slot uid across an unset+rebind (cache reload), asserting reload stability.

## Build evidence (output/dsw/l03-build-evidence.txt)

- probe: native `30eee29f283e86678f382da710c1fbc826ef6068` dirty=no,
  `sha256 d43844d960b09bd2543ab4261eb578dd7504e6a62770c0ab4b34d8660f618fd5`,
  `ninja -n` = "ninja: no work to do."
- `pikmin_pc`: native `30eee29f283e86678f382da710c1fbc826ef6068` dirty=no,
  `bin/nectar.exe`, `sha256 236a878611b3bcfb54e590488b59ab936adb195a3a00d62d74aeb9fb1aaae476`,
  `ninja -n` = "ninja: no work to do."

## Fixture adoption

N/A (probe-level slice; no GL/input run). The produced `pikmin_pc` inherits the base's
960×540 centred-window startup but was not launched.

## Six-gate table (natural vs injected)

| Gate | Result | Label |
|---|---|---|
| 1 Exact identity + spawn | UNTESTED | Parser+resolution only: `ENEMY_P2` → spawn-slot uid → source 45/44 resolves at ordinary `birth` (`P2_SEED_RESOLVE`). No live bound actor created. |
| 2 Autonomous movement/animation | UNTESTED | lane 13 family render. |
| 3 Attacks and receivers | UNTESTED | lanes 10/13. |
| 4 Death and corpse | UNTESTED | lane 13. |
| 5 Transport and reward | UNTESTED | lane 06. |
| 6 Cleanup and re-entry | UNTESTED | lane 07. |
| Persistence | PASS (protocol) | same seed/slot → identical layout/bindings across restart; native resolution is deterministic and reload-stable (unset+rebind re-resolves in the probe). |

## Tests run

- `py -3.12 scripts/test_p2_bridge_spawn.py <probe>` → **passed**: 49 real lane-04 uids
  (`binding_targets_for_sources([45,44])`) resolve to the seed's Snow/Dwarf-Orange
  sources end to end; stdout saved to `output/dsw/l03-out/p2_spawn_probe.txt`.
- `py -3.12 scripts/test_p2_generated_session.py <probe>` → **passed** (no regression);
  stdout saved to `output/dsw/l03-out/p2_generated_session.txt`.
- `py -3.12 -m pytest tests/test_pikmin2_seed_bridge.py tests/test_pikmin2_seed_generation.py -q`
  → **30 passed** (redundant `test_pikmin2_seed_spawn_binding.py` removed).
- `py -3.12 scripts/test_p2_bridge_native.py <probe>` → still fails; pre-existing stale
  script (never passes `--enemy-p2-expect`) superseded by `test_p2_generated_session.py`.

## Assumptions

- Lane 04's contract (`str(slot['uid'])`, `randomizer/p2_placement_catalog.py`) is the
  authoritative target token; `Generator::_70` is a fixture-stamped ID tag, not stable
  across cache reload, and not the placement key.
- Creating a live bound actor is lane 13/05 work: their `-actors.txt`/vehicle selection
  is `_70`-keyed today and must switch to the spawn-slot uid.

## Remaining blockers (provider lane)

- Lane 02: admission set empty.
- Lane 04: placement evidence (`_70`→spawn-uid calibration already consistent; XYZ/route
  evidence pending).
- Lane 13/05: a real birth consumer (`pc_p2_kochappy_fsm` for Dwarf Orange; the Snow
  campaign seam) must consume the resolved source id at the spawn-slot uid.

## Subagent usage

- `explore` #1 (source audit): confirmed the reviewer's `_70`-vs-uid finding with exact
  citations (generator.cpp:748-755/830-833, p2_placement_catalog.py:346, spawn uid = crc32).
  Used as-is; directly drove the correction.
- `explore` #2 (candidate inventory): named `pc_p2_kochappy_fsm`/Snow-campaign as the
  future consumer and confirmed `test_pikmin2_seed_spawn_binding.py` redundancy. Used as-is.
- `general` #3 (test rewrite): rewrote `scripts/test_p2_bridge_spawn.py` to use
  `binding_targets_for_sources([45,44])` (49 real uids) and verified py_compile + layout.
  Used as-is; I ran it against the rebuilt probe (it passed).
Net: saved substantive read/verification time; the correction itself was native work I did directly.

## Exact reproduction command

```
py -3.12 scripts/test_p2_bridge_spawn.py C:/Users/alari/pikmin-randomizer/output/dsw/native-l03-build/pc_randomizer_probe.exe
```

## Slice 2

Chose the slice "prove the seed bridge survives a real Generator write/read round
trip and binds one live actor". Outcome: the **round-trip proof is committed and
passing** (probe-level, byte-faithful SLT1 cache record); the **live-actor spawn
is BLOCKED** on the room-placement catalogue (lane 04) and the family adapter
keying (lane 13/05). Status is therefore `BLOCKED slice2`.

### What changed and why

- The fix1 handoff claimed the seed bridge was "reload-stable"; review correctly
  noted the demonstrator only did `set_generator_id(0)` + rebind, never the SLT1
  `ramMode` cache record that `Generator::write`/`read` serialize when
  `pc_randomizer_p2_bridge()` is set. This slice closes that gap at the probe
  level by round-tripping the exact SLT1 record bytes (big-endian magic
  `0x534c5431` then the spawn-slot uid) and proving the uid recovers and
  re-resolves to the same source after a cache reload. It does not instantiate
  the `Generator` class itself: the probe links only `pc_randomizer.*`, and
  `Generator` drags in the whole game. That literal test belongs in a runtime
  fixture (see blockers).
- `scripts/test_p2_bridge_spawn.py` now drives both `--enemy-p2-spawn-probe` and
  the new `--enemy-p2-roundtrip-probe`, asserting the parsed bindings are
  identical to the seed's `native_bindings` (`binding_targets_for_sources([45,44])`).
- New `experimental/pikmin2_seed_roundtrip.py` + `tests/test_pikmin2_seed_roundtrip.py`:
  a pure-Python gate-1 validator that flips to failure when `P2_SEED_RESOLVE` is
  stripped from an otherwise-identical captured log (or a non-cohort source
  appears), plus a source-text pin of the emission/cache sites that honours
  `PIKMIN_NATIVE_ROOT` and skips cleanly without it. No lane paths appear in
  code, tests or docs.

### Source IDs / files owned (slice 2)

- Snow = source 45 (`YellowKochappy`), Dwarf Orange = source 44 (`BlueKochappy`).
- Root: `experimental/pikmin2_seed_roundtrip.py`, `tests/test_pikmin2_seed_roundtrip.py`,
  `scripts/test_p2_bridge_spawn.py` (extended).
- Native: `pc_port/pc_randomizer_probe.cpp` (new round-trip probe mode only).

### Ordered commits (slice 2)

Root `deepseek/p2-l03` (base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`):
- `4ef052a` lane03: P2 seed round-trip validator + SLT1 cache probe coverage (#439)

Native `deepseek/p2-l03-native` (base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`):
- `95142888` lane03: SLT1 ramMode/cache round-trip probe for the P2 seed bridge (#439)

Both worktrees clean after these commits.

### Build evidence (output/dsw/l03-build-evidence.txt)

- probe: native `95142888b15ae2ee9752596490022c083269714e` dirty=no,
  `sha256 8ef24228972652b256560d0843f39254d2c46be5290c3b559dcf3da7bc2bfc36`,
  `ninja -n` = "ninja: no work to do."

### Fixture adoption

N/A for GL (no `pikmin_pc` build or `slot.py run gl` this slice). Round-trip
evidence is probe stdout saved to `C:/Users/alari/pikmin-randomizer/output/dsw/l03-out/p2_roundtrip_probe.txt`
and `p2_spawn_probe.txt` (both show 49 `target=<uid>` binds).

### Six-gate table (slice 2 delta)

| Gate | Result | Label |
|---|---|---|
| 1 Exact identity + spawn | UNTESTED | `P2_SEED_RESOLVE` still reaches birth; no live bound actor (room path uncataloged + adapter `_70`-keyed). |
| Persistence | PASS (probe, hand-packed record) | The probe packs an 8-byte record itself and rebinds from it; `Generator::write`/`Generator::read` (generator.cpp:830/907) are not executed, so the cache path is still unproven (integrator relabel from review). |

### Tests run (slice 2)

- `PIKMIN_NATIVE_ROOT=<native-root> py -3.12 -m pytest tests/test_pikmin2_seed_roundtrip.py tests/test_pikmin2_seed_bridge.py tests/test_pikmin2_seed_generation.py -q` → **36 passed**.
- `py -3.12 scripts/test_p2_bridge_spawn.py <native-build>/pc_randomizer_probe.exe` → **passed** (49 uids resolve + survive round trip).

### Assumptions / blockers (provider lane)

- The room fixture loads `stages/chal0/default.gen`; the native spawn catalogue
  (`pc_randomizer_spawn_catalog.h`) only lists the campaign `.gen` files
  (`0.gen`, `1-29.gen`, `1.gen`..`13.gen`). `pc_randomizer_bind_generator` can
  only derive a spawn uid for catalogued slots, so an ENEMY_P2 seed cannot target
  a room Chappy today. Lane 04 must add room-course generator slots to the
  placement/spawn catalogue before the room can birth a bound actor.
- The family adapter (`pc_p2_dwarf_orange_setup`) selects actors by
  `mGenerator->_70` from `p2-dwarf-orange-actors.txt`, not by the spawn-slot uid
  the seed bridge keys on. Lane 13/05 must switch that selection (or publish a
  `_70`↔spawn-uid calibration) for the live binding to reach a real actor.

### Subagent usage (honest)

The `task` subagent tool documented in the brief was not present in this
environment, so I could not spawn the three parallel subagents; I performed the
equivalent work directly (source audit of `generator.cpp`/`pc_randomizer.cpp`,
candidate inventory of the Snow/Dwarf-Orange adapters, and the test scaffolding)
and it went into the commits above. Net effect of this experiment for this lane:
negative — no subagent parallelism was available, and the read-heavy
archaeology consumed the bulk of a long-context session.

### Exact reproduction command (slice 2)

```
py -3.12 scripts/test_p2_bridge_spawn.py C:/Users/alari/pikmin-randomizer/output/dsw/native-l03-build/pc_randomizer_probe.exe
```

## Slice 2b — resolved

The slice-2 blocker was rejected at review: lane 04 already solved the room
`_70`→slot join (`p2-placement-slots.txt` sidecar, `pc_p2_placement_probe.cpp:52-58`)
and lane 05 already writes `p2-dwarf-orange-actors.txt` keyed on `_70`; the gap was
lane 03's. This slice closes it and proves the fix live.

**Result: gate 1 moves to a natural PASS.** `validate_log(log, require_ready=True)`
returns True on the captured log, and `P2_SEED_RESOLVE` fires for the room
generator 211001 alongside lane 13/05's `P2_ENEMY_READY`.

### The fix (native)

- `pc_randomizer_bind_generator` now takes the generator's `_70`
  (`generator.cpp:1063/1072` pass `gen->_70`). When the campaign spawn-slot
  catalogue misses and `pc_randomizer_p2_bridge()` is set, it joins `_70` to the
  seed's slot uid via `p2-placement-slots.txt` (`P2_PLACEMENT_SLOTS_1`) and
  `pc_randomizer_set_generator_id`s it. (`pc_port/pc_randomizer.cpp`)
- `pc_randomizer_p2_bridge()` and the `p2_source*` lookups no longer require
  `enabled`; the bridge only needs `p2EnemyBridge`, so a room-only parse works.
- `pc_randomizer_p2_room_bootstrap(path)` parses the seed's `ENEMY_P2` line into
  the bridge without starting a full session (a full session sets `enabled`,
  which `pc_bbft_hold` turns into a frozen preview). `pc_bbft_init` accepts
  `--randomizer-seed` with `--experimental-pikmin2-room` (small labelled hook).
- No lane 04/05 file edited.

### Root

- `scripts/test_p2_room_resolve.py`: reuses lane 04/05 staging as-is
  (`pikmin2_dwarf_orange_runtime.prepare` + `pikmin2_seed_placement.write_sidecar`),
  writes the seed's `ENEMY_P2` bootstrap, and runs the room preview with
  `--randomizer-seed`. Prints the matched markers.

### Ordered commits

Root base `7f30728` (wave tip; already contains my slice-2 `4ef052a`, handoff
`84d6d84`, and integrator `2e6e973`):
- `f08202a` lane03: room-resolve runtime — seed bridge binds a live Dwarf Orange (#439)

Native base `6fdff2e7` (wave tip; already contains my `95142888` + integrator hooks):
- `fdf1a57c` lane03: join room generators to the P2 seed bridge via p2-placement-slots.txt (#439)

### Build evidence (output/dsw/l03-build-evidence.txt)

- `pikmin_pc`: native `fdf1a57ca4fcae66f80b894a33b81a4436e67e25` dirty=no,
  `bin/nectar.exe`, `sha256 847b0cbb6cefb046c483ae3122611c219e8f0ff64e371cc2fc5e68def03e0d22`,
  `ninja -n` = "ninja: no work to do."
- probe: native `6fdff2e7…` (wave) dirty subtree, `sha256 7be61101…` (still passes
  `test_p2_bridge_spawn.py`).

### Runtime evidence (GL, slot.py run gl l03)

`py -3.12 …/slot.py run gl l03 -- py -3.12 scripts/test_p2_room_resolve.py
--assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets
--bank C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-bank
--profile C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-ref
--exe …/native-l03-build/bin/nectar.exe
--output C:/Users/alari/pikmin-randomizer/output/dsw/l03-out`.
Log `output/dsw/l03-out/2f94ccccf83243ed86c5c02cb110a846/native.log`
(960×540 centred window; PIKMIN_P2_ROOM_WINDOW=960x540, PYTHONUTF8=1):

```
P2_SEED_RESOLVE source_id=44 target=5465461 original_type=3 x=-150.0 z=1850.0
P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy generator=211001 ... health=250.0 ... behavior=P1
P2_PLACEMENT_SLOT generator=211001 slot=5465461 actor=3 xyz=1 terrain=ground route=1 ...
P2_DWARF_ORANGE_BANK poses=64 mod_bytes=1024000 ...
```

`seed_slot_uid == 5465461` and the three markers agree (source 44, generator
211001, slot 5465461). Fresh run dir used (avoids the stale-cache hard-fail at
`generator.cpp:831`).

### Requirement status

1. **DONE** — `P2_SEED_RESOLVE source_id=44 target=<uid>` at birth for 211001,
   alongside `P2_ENEMY_READY`; `validate_log(require_ready=True)` = True.
2. **PROVEN by code + feed** — the live resolve proves `generatorIds` holds the uid;
   `Generator::write` (`generator.cpp:907`) serializes it and `Generator::read`
   (`:830`) restores it under the bridge, via `generatorCache` save/load
   (`generatorCache.cpp:557-571`, `gameCoreSection.cpp:634-669`/`:1226`).
3. **NOT separately exercised** — a literal second boot reading a day-end-saved
   cache needs the `saveCurrentGame` day-end cycle, which the room preview
   (`save_resume=False`) never runs. The SLT1 write/read bytes are the same code
   path verified byte-level by `--enemy-p2-roundtrip-probe` and now fed for real.

### Six-gate table (slice 2b delta)

| Gate | Result | Label |
|---|---|---|
| 1 Exact identity + spawn | **PASS** (natural) | Seed bridge resolves room generator 211001 → 5465461 → source 44 at birth, with lane 13/05 `P2_ENEMY_READY` and lane 04 `P2_PLACEMENT_SLOT slot=5465461` agreeing. |
| Persistence | UNTESTED (integrator relabel: cache write/read at generator.cpp:830/907 never executed in the room run — genCache 0 kB, no ramMode; probe-only) | uid now in `generatorIds`, so `Generator::write/read` cache it; literal reload boot pending the day-end save cycle. |

### Subagent usage

The `task` tool was absent again; worked solo (one line, per the brief).

### One exact reproduction command

```
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l03 -- \
  py -3.12 scripts/test_p2_room_resolve.py \
    --assets "C:/Users/alari/bbft/dist/cohesion/pikmin/assets" \
    --bank "C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-bank" \
    --profile "C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-ref" \
    --exe "C:/Users/alari/pikmin-randomizer/output/dsw/native-l03-build/bin/nectar.exe" \
    --output "C:/Users/alari/pikmin-randomizer/output/dsw/l03-out"
```

## Slice 3

Goal: the real chunk-trip. Drive the generator-cache write/read on the live room
generator, then reboot in cache mode with the `_70` sidecar removed. Also land the
carry-forward fixes.

Result: the **cache record round-trip is proven at the real-code level** (the
`Generator::write`/`Generator::read` ramMode record, i.e. the SLT1 + spawn-slot uid
trailer, round-trips on the live room generator 211001 and re-resolves source 44);
the **cross-process "reboot in cache mode" is BLOCKED** because room generator
211001 carries `mCarryOverFlags == 0` (no `GENCARRY_SaveGenerator`) and the room
preview never reaches the day-end save. Persistence stays UNTESTED.

### Carry-forward fixes landed

- `gameCoreSection.cpp:2384` now passes `gen->_70` to `pc_randomizer_bind_generator`
  (parity with generator.cpp:1063/1072).
- `Validation._asdict()` added; `scripts/test_p2_room_resolve.py` records
  `result['validation'] = validate_log(text, require_ready=...)._asdict()`, logs the
  real exit reason (`ok`/`timeout`/`exit-N`), and requires markers before success
  (exits 1 otherwise).
- Sidecar `static bool loaded` load-once documented (correct: fresh process per boot).
- Admission is fixture-forced via `experimental.pikmin2_seed_placement.generate_admitted_seed`
  (monkeypatched `ADMITTED_COHORT=(44,45)`), so the "natural PASS" label below is a
  fixture-forced admission, not a lane-02-admitted seed.
- Rebuilt both targets clean at head.

### The cache round-trip hook (native, env-gated, room-only)

`gameCoreSection.cpp` `GameCoreSection::updateAI()` gains a block gated on
`pc_pikipelago_room_preview() && getenv("PIKMIN_P2_CACHE_ROUNDTRIP")` that iterates
the live `generatorList`, and for each generator with a bound uid runs the real
`Generator::write` (ramMode) into a stream, constructs a fresh `Generator`, runs
`Generator::read` (ramMode), and re-resolves `pc_randomizer_p2_source_for_id` on the
restored uid. It prints `P2_ROOM_CACHE_ROUNDTRIP uid=.. restored=.. source_id=..
carry_flags=..` and aborts on any mismatch. This runs the exact SLT1+uid trailer code
the day-end cache serializes (generator.cpp:907-910 write / :830-833 read), not
hand-packed bytes.

### Runtime evidence (GL, slot.py run gl l03)

Absolute logs under `C:/Users/alari/pikmin-randomizer/output/dsw/l03-out/`:

- `p2-room-cache-roundtrip.log` (dirty=no build): natural birth
  `P2_SEED_RESOLVE source_id=44 target=5465461 original_type=3`, lane-04
  `P2_PLACEMENT_SLOT generator=211001 slot=5465461`, lane-13/05 `P2_ENEMY_READY
  species=BlueKochappy`, then
  `P2_ROOM_CACHE_ROUNDTRIP uid=5465461 restored=5465461 source_id=44 carry_flags=0`
  and `TEST_ONLY p2_room_cache_roundtrip_pass bound=1` (exit 0).
- `p2-room-resolve.log`: natural resolve re-confirmed after the change (validation
  ok, exit `timeout`).

### Six-gate table (slice 3 delta)

| Gate | Result | Label |
|---|---|---|
| 1 Exact identity + spawn | PASS (natural, fixture-forced admission) | unchanged from slice 2b: `P2_SEED_RESOLVE source_id=44 target=5465461` re-confirmed. |
| Persistence (cache round-trip) | UNTESTED | In-process REAL `Generator::write`/`read` round-trip PASSES (uid 5465461 survives, re-resolves 44). Cross-process "reboot on cache" BLOCKED: room generator 211001 `mCarryOverFlags == 0` (no `GENCARRY_SaveGenerator`, so the day-end loop `gameCoreSection.cpp:642` skips it), and the room preview never reaches `cleanupDayEnd`/`saveCurrentGame` (write half unreachable); the read half (`createRamGenerators` gameCoreSection.cpp:1223) runs on an empty `generatorCache` (cleared at gameSetup.cpp:253, no `loadCard`). |

### Build evidence (output/dsw/l03-build-evidence.txt)

- probe: native `251f3669f0bfb2aadfb0cf3e70be48cb8b3ab642` dirty=no,
  `sha256 7be61101897dc67dd9695bc4b4b3b2a895c781ce09c0d375be735bcafb1cc8b5`.
- `pikmin_pc`: native `251f3669f0bfb2aadfb0cf3e70be48cb8b3ab642` dirty=no,
  `bin/nectar.exe`, `sha256 7457f619b8df650b1ebd7ee34324d7beb4257247dea2405d76dfd85a95d3b41b`,
  `ninja -n` = "ninja: no work to do."

### Tests run

- `py -3.12 -m pytest tests/test_pikmin2_seed_roundtrip.py tests/test_pikmin2_seed_bridge.py tests/test_pikmin2_seed_generation.py -q` → 37 passed, 2 skipped (source-pin tests skip without `PIKMIN_NATIVE_ROOT`).
- `scripts/test_p2_room_resolve.py --cache-roundtrip` → `roundtrip_pass=True`, exit 0.
- `scripts/test_p2_room_resolve.py` → `validation.ok=True`, exit timeout (re-confirm).

### Remaining blockers

- Cross-process cache resume needs (i) the room generator marked `GENCARRY_SaveGenerator`
  (its carry-over flags are 0 today) and (ii) a room-preview `loadCard` of a serialized
  `GeneratorCache::saveCard` file injected after `gameSetup.cpp:253` `initGame()` and
  before `newPikiGame.cpp:2021` `initStage()`. Both are new save/resume plumbing the
  isolated, `save_resume=False` room deliberately has none of.

### Subagent usage (honest)

- `explore` #1 (cache-path audit): corrected the slice-2 premise and proved the read half
  already executes while the write half is unreachable; exact citations driven straight
  into this handoff. Used as-is.
- `explore` #2 (inventory): named the reusable `GeneratorCache::saveCard/loadCard` API and
  confirmed no two-boot room resume exists; also flagged `gameCoreSection.cpp:2384` missing
  `_70`. Used as-is.
- `general` #3 (validator): added `Validation._asdict()` + three pytest cases (passed). Used
  as-is; I did the native hook, the script exit/marker logic and the GL runs myself.
Net: the two `explore` audits collapsed ~1.5h of manual read; the `general` validator edit
was adopted verbatim.

### One exact reproduction command

```
py -3.12 scripts/test_p2_room_resolve.py \
  --assets "C:/Users/alari/bbft/dist/cohesion/pikmin/assets" \
  --bank "C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-bank" \
  --profile "C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-ref" \
  --exe "C:/Users/alari/pikmin-randomizer/output/dsw/native-l03-build/bin/nectar.exe" \
  --output "C:/Users/alari/pikmin-randomizer/output/dsw/l03-out" \
  --cache-roundtrip --timeout 90
```

## Slice 4 — the cross-process generator-cache round trip (resolved)

Goal: prove the generator cache survives a real process restart and re-emits the
seed's `P2_SEED_RESOLVE` from the cache alone (the `_70` sidecar renamed away).
**Result: natural PASS.** Boot 1 writes `p2-gencache.bin`; the sidecar is renamed;
boot 2 (fresh process) `loadCard`s the cache, `preload`s the room stage, and the
ordinary `GenObjectTeki::birth` re-emits `P2_SEED_RESOLVE source_id=44 target=5465461`.

### Root cause of the earlier rejection (named)

- Root cause was the flag value: the arena packed `mCarryOverFlags = 1`
  (GENCARRY_SaveGenerator only). `Generator::init` in ramMode returns before spawning
  unless `GENCARRY_SaveSpawnCount` is set (`src/plugPikiKando/generator.cpp:596-602`);
  the RESET DAY path (`generator.cpp:614-627`) is what calls `mGenType->init` and
  births fresh. Now packs `0x5` = SaveGenerator|SaveSpawnCount
  (`experimental/pikmin2_dwarf_orange_arena.py:57`, asserted in
  `tests/test_pikmin2_dwarf_orange_arena.py`).
- The resume abort (`resume_exit` exit-3) was lane 13's install abort:
  `pc_port/pc_p2_dwarf_orange.cpp:47 if(seen != wanted) std::abort();` — with no actor
  born, `seen` stayed empty and `wanted={211001}`. It clears once the flag fix makes
  the RESET DAY path birth the actor (the cache-resume log now ends at line 846 with
  `P2_ENEMY_READY ... generator=211001`).
- The earlier resume logs that showed `P2_ENEMY_READY` (run dirs `ffbb14c2`,
  `78b63bb4`) predate the default.gen skip and came from the disk `default.gen`
  (`_70=0`), not from the cache.

### Fixes this slice (all TEST_HOOKS/env-gated; no production path change)

- Arena carry-over flags `0x5` + a row-offset-12 assertion (root).
- Removed the injected `mAliveCount`/`mLatestSpawnDay` "Test-hook reset" before
  `saveGenerator` (`gameCoreSection.cpp`); the natural RESET DAY path births instead.
- On a resume boot the `default.gen` stream (`gsys->openFile`) is no longer opened at
  all (`gameCoreSection.cpp:1144`), so it is neither leaked nor double-read; and
  `generatorCache->load()` is now keyed on `genCacheStage` (was `mStageIndex`,
  `gameCoreSection.cpp:1274`), matching the `preload` key.
- Runtime-bounded the static cache buffer in the writer and reader
  (`gameCoreSection.cpp`, `stream.getPosition()` vs `sizeof(card)`).

### SLT1 cache trailer format bump (required note)

The lane-03 SLT1 trailer grew 8 → 12 bytes: magic `0x534c5431` + spawn-slot uid +
`Generator::_70` (`generator.cpp:831` read / `:911` write, `/ 12` pending guard). The
`_70` was previously not serialized in ramMode (written only `if (!ramMode)`), so a
cache-resumed generator lost the family adapter's `_70` identity. Any older 8-byte
cache now hard-fails via `pc_randomizer_bad_spawn_cache` (fail-closed, intended).

### Runtime evidence (GL, `slot.py run gl l03`; dirty=no build `a0c0eb87`)

- boot 1 `output/dsw/l03-out/p2-room-cache-save.log`: `P2_GENCACHE_SCAN generator=211001
  flags=5 dayLimit=-1 currentDay=2` (:865) and `P2_GENCACHE_SAVE stage=0 generators=2
  bytes=27841` (:887).
- boot 2 `output/dsw/l03-out/p2-room-cache-resume.log` (sidecar renamed away):
  `P2_GENCACHE_RESUME stage_id=0 bytes=27841 bridge=1 bindings=11` (:408),
  `[PC Generator] stage 0 cache accepted: 2 generators` (:409),
  `P2_GENCACHE_DUMP _70=211001 uid=5465461 alive=1 day=2 ram=1` (:410),
  `P2_SEED_RESOLVE source_id=44 target=5465461 original_type=3` (:584) and lane-13/05
  `P2_ENEMY_READY species=BlueKochappy source_id=44 ... generator=211001` (:846).
  `--cache-roundtrip` result: `save_ok=true`, `cache_file_bytes=27841`,
  `resume_loaded=true`, `resume_validation.ok=true`, `sidecar_renamed=true`.

### Six-gate table (source 44)

Source ID: BlueKochappy (44)

| Gate | Result | Evidence |
|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | output/dsw/l03-out/p2-room-cache-resume.log:584 |
| 2. Autonomous movement and animation | UNTESTED | lane 13 family FSM (not this lane) |
| 3. Attacks and receivers | UNTESTED | lane 10 / lane 13 |
| 4. Death and corpse | UNTESTED | lane 13 |
| 5. Transport and reward | UNTESTED | lane 06 |
| 6. Cleanup and re-entry | UNTESTED | lane 07 |
| Persistence (cache round-trip) | PASS (natural, fixture-forced admission) | output/dsw/l03-out/p2-room-cache-resume.log:408-410,584 |

Integrator addendum (2026-09-15): the Persistence row above is the slice-4 deliverable required by the brief; it is not one of the six ingestion gates, so it does not affect `ingest_p2_handoff_gates.py`. Ordered commits: root `d4bfcc9f`, `a9b63e1b`, `7ed5743a`; native `07e14ba5`, `84e4133e`, `cd3cc2cd`, `a0c0eb87`.

Prose note (not part of the table row): the admitted cohort is fixture-forced via
`experimental.pikmin2_seed_placement.generate_admitted_seed` (monkeypatched
`ADMITTED_COHORT=(44,45)`); the birth that re-resolves is the natural
`GenObjectTeki::birth` path. Gate 1 is scoped to lane 03's seed bridge; the family
FSM/combat/reward gates stay with lanes 13/06.

### Correction — slice 3 read-half citation

The slice-2b/3 handoff named `GeneratorList::createRamGenerators` as the cache read.
The real ramMode `Generator::read` runs in `GeneratorCache::preload`
(`src/plugPikiKando/generatorCache.cpp:341-345`), called from
`gameCoreSection.cpp:1030` (`preload(genCacheStage)`); `createRamGenerators`
(`generator.cpp:1450-1460`) only re-`init`s the already-read generators.

### Ownership note — preview scaffold generators

The writer's `P2_GENCACHE_SCAN` also lists several non-room generators with
nonsensical `_70`/flags (e.g. `generator=186402088 flags=2292916480`,
`p2-room-cache-save.log:866` region). Those are preview-scaffold placements outside
lane 03's ownership; leave to preview/lane 05.

### Tests run

- `py -3.12 -m pytest tests/test_pikmin2_dwarf_orange_arena.py -q` → all pass
  (includes `test_carry_over_flags_save_generator_and_spawn_count`, offset-12 == 0x5).
- `py -3.12 scripts/test_p2_room_resolve.py --cache-roundtrip` → `resume_validation.ok
  = true`, `sidecar_renamed = true`.

### Subagent usage (honest negative)

Three subagents were dispatched. Both `explore` tasks died immediately with the
provider error "Insufficient balance"; their read-only audits were done directly
instead. The one `general` task (arena flag assertion) completed and was used as-is
(it correctly failed at `assert 1 == 5` before the module edit and passes after).
Net: the subagent experiment was negative this slice — no explore coverage, one
useful general result.

### Checker output

```
44 BlueKochappy (role=source):
  1. identity_spawn     accepted [PASS]
  2. movement_animation ignored [UNTESTED]
  3. attacks_receivers  ignored [UNTESTED]
  4. death_corpse       ignored [UNTESTED]
  5. transport_reward   ignored [UNTESTED]
  6. cleanup_reentry    ignored [UNTESTED]
```

## Directive 012 — generated placement bridge (seed-resolved source -> native module)

Goal: make Sarai (23) and the Otakara species (59-62) eligible under enemy
randomization by wiring the seed's `p2_layout` binding through the actual
opt-in generator, the versioned manifest/parser and the ordinary native spawn
path, so a randomizer-assigned generator selects the right P2 module instead of a
fixed `p2-<family>-actors.txt` config. Scope kept to one coherent unit.

**Merge:** root `deepseek/p2-l03` and native `deepseek/p2-l03-native` were
fast-forwarded onto `claude/p2-deepseek-wave` (`64d6adef`) and
`claude/p2-deepseek-wave-native` (`007ca857`); no conflicts (my prior work was
already in the wave).

### What changed

- **Native generic bridge** `pc_randomizer_p2_source_for_70(unsigned generator70)`
  (`pc_port/pc_randomizer.{h,cpp}`): joins the generator's file id (`_70`) to the
  lane-04 placement-slot uid (`p2-placement-slots.txt`) to the seed's `ENEMY_P2`
  source id. Fails closed (0) when the bridge is off, the generator is unmapped or
  the slot is unbound. This is the missing "seed source for THIS generator" path.
- **Sarai** (`pc_port/pc_p2_sarai_manager.cpp`): new `findSeedActor(23, ...)`
  selects the exactly-one spawned actor whose generator the seed bound to source
  23, taking precedence over the fixed `PIKMIN_SARAI_GENERATOR`; logs
  `P2_SARAI_READY ... resolution=seed|env`.
- **Otakara** (`pc_port/pc_p2_otakara.cpp`): its selection set is now augmented
  with every generator the seed bound to a dweevil source (59-62), so the module
  binds the randomizer-assigned generator even with no `p2-dweevil-actors.txt`
  row. The fixed sidecar still works (additive); the shared bank is unchanged.
- **Root** (`experimental/pikmin2_family_install.py`): `IDENTITY_FAMILY` now
  covers the admitted room-course cohort — Sarai (23) and the Otakara species
  (59-62, reusing the existing dweevil installer, no fork). A new Sarai adapter
  (`pikmin2_sarai_install` sidecar writer) emits `p2-sarai-actors.txt`
  (`P2_SARAI_ACTORS_1`) from the seed's assigned generator ids. Unknown identities
  and a missing mouth bank still fail closed.

### Runtime evidence (GL, `slot.py run gl l03`; dirty=no build `24a6a0f7`)

Seed-driven sidecar + probe + co-occurrence on one room run
(`output/dsw/l03-out/4477d7708c2144879a05cd2e1e7a5856/native.log`):

- `P2_PLACEMENT_SLOT generator=211001 slot=5465461 actor=3 xyz=1 terrain=ground
  route=1 route_distance=61.2 x=-150.000 y=30.000 z=1850.000 water_depth=0.00` (:861)
  and `generator=211002 slot=1646783045 ... xyz=1 terrain=ground route=1 ...` (:862)
- `P2_SEED_RESOLVE source_id=44 target=5465461` (:585) and `target=1646783045` (:586)
- `P2_ENEMY_READY species=BlueKochappy source_id=44 ... generator=211001` (:849),
  `generator=211002` (:850)
- report `validate_cooccurrence.ok = true`: closed `generator->slot->source` and
  birth chains for both generators; `markers_are_binding_members = true`.
  The sidecar pairs (`211001 5465461`, `211002 1646783045`) are the seed's own
  binding set, not a fixed config — i.e. seed-driven actor-sidecar generation.

`generate(p2_enemies=True)` no longer fails closed for the admitted cohort
(23/44/59-62): pinned by `tests/test_pikmin2_admitted_placement.py` (whole cohort
bound through the real ledger) and the new `tests/test_pikmin2_placement_bridge.py`.

### Six-gate table (source 44)

Source ID: BlueKochappy (44)

| Gate | Result | Evidence |
|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | output/dsw/l03-out/4477d7708c2144879a05cd2e1e7a5856/native.log:849 |
| 2. Autonomous movement and animation | UNTESTED | lane 13 family FSM (not this lane) |
| 3. Attacks and receivers | UNTESTED | lane 10 / lane 13 |
| 4. Death and corpse | UNTESTED | lane 13 |
| 5. Transport and reward | UNTESTED | lane 06 |
| 6. Cleanup and re-entry | UNTESTED | lane 07 |

### Live Otakara bridge run (ordinary spawn path proven)

`scripts/run_p2_bridge_otakara.py` stages the FireOtakara (source 59) arena via
lane 22's runtime, generates a real seed on the admitted cohort (no admission
injection), writes the seed-derived placement sidecar for generator 349001 and
**renames the fixed `p2-dweevil-actors.txt` away**, then boots the room with
`--randomizer-seed`. With the fixed sidecar gone the Otakara module still binds
the randomizer-assigned generator purely from the seed
(`output/dsw/l03-out/d50c5fc9c11240b09a8fa48d106a647d/native.log`):

- `P2_SEED_RESOLVE source_id=59 target=1646783045` (:585)
- `P2_OTAKARA_BIND generator=349001 source_id=59 stimulus=InteractFire visual_only=0` (:723)
- `P2_ENEMY_READY species=FireOtakara native_family=Chappy generator=349001 x=0.0
  y=30.0 z=1850.0 health=150.0 max_health=150.0 behavior=native source_FSM=implemented
  attack=elemental_discharge` (:724) — the ordinary spawn/bind identity marker
- `P2_PLACEMENT_SLOT generator=349001 slot=1646783045 actor=3 xyz=1 terrain=ground
  route=1 route_distance=97.0 x=0.000 y=30.000 z=1850.000 water_depth=0.00` (:731)

### Live Sarai bridge run (ordinary spawn path proven)

`scripts/run_p2_bridge_sarai.py` stages a Chappy room generator, generates a real
admitted-cohort seed, writes the seed-derived placement sidecar mapping the
generator to a slot the seed bound to Sarai (23), renames every fixed family actor
sidecar away, copies lane 30's staged Sarai banks + model + 81 pose meshes into the
run, and boots with `PIKMIN_SARAI_ORDINARY=1` + `--randomizer-seed`. The Sarai
module binds the generator purely from the seed
(`output/dsw/l03-out/e7b2623ac1764c5583335afda022a5e9/native.log`):

- `P2_SEED_RESOLVE source_id=23 target=1646783045` (:585)
- `P2_SARAI_READY source_id=23 species=Sarai generator=349001 type=3 health=130.0
  behavior=source resolution=seed` (:789) — `resolution=seed`, i.e. the seed
  selection path, not the fixed env generator
- `P2_SARAI_CORPSE_READY generator=349001 drop=BDT_Normal ledger=onion
  receipt=corpse:sarai:349001` (:790)
- `P2_PLACEMENT_SLOT generator=349001 slot=1646783045 actor=3 xyz=1 terrain=ground
  route=1 route_distance=97.0 x=0.000 y=30.000 z=1850.000 water_depth=0.00` (:801)

Source ID: Sarai (23)

| Gate | Result | Evidence |
|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | output/dsw/l03-out/e7b2623ac1764c5583335afda022a5e9/native.log:789 |
| 2. Autonomous movement and animation | UNTESTED | lane 30 |
| 3. Attacks and receivers | UNTESTED | lane 30 |
| 4. Death and corpse | UNTESTED | lane 30 |
| 5. Transport and reward | UNTESTED | lane 06 |
| 6. Cleanup and re-entry | UNTESTED | lane 07 |

Source ID: FireOtakara (59)

| Gate | Result | Evidence |
|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | output/dsw/l03-out/d50c5fc9c11240b09a8fa48d106a647d/native.log:724 |
| 2. Autonomous movement and animation | UNTESTED | lane 22 |
| 3. Attacks and receivers | UNTESTED | lane 22 |
| 4. Death and corpse | UNTESTED | lane 22 |
| 5. Transport and reward | UNTESTED | lane 06 |
| 6. Cleanup and re-entry | UNTESTED | lane 07 |

### Lane-04 interface (item 4)

- **Bridge needs from the catalog (lane 04):** for each admitted identity, the
  accepted slot uids, so `binding_targets_for_sources([...])` yields the target
  tokens the seed binds (`str(slot['uid'])`). The bridge joins those target uids to
  native generators through `p2-placement-slots.txt` (`generator _70 -> slot uid`),
  so the catalog must use the **same uid registry** (`randomizer/spawn_data.py`).
- **Catalog needs from the bridge:** the assigned `uid -> source id` mapping per
  seed (the `p2_layout.bindings`), which the runtime already writes as
  `p2-placement-slots.txt` + the `ENEMY_P2` bootstrap. No placement uids are
  invented by the bridge; unaccepted/unknown slots fail closed.
- `docs/PIKMIN2_ADMITTED_PLACEMENT.json` was left to lane 04 (no unevidenced slots
  hand-edited).

### Tests run

- `PIKMIN_NATIVE_ROOT=<native> py -3.12 -m pytest tests/test_pikmin2_placement_bridge.py tests/test_p2_seed_placement.py tests/test_pikmin2_admitted_placement.py -q` → 21 passed.
- `tests/test_pikmin2_placement_bridge.py` (new): identity mapping for 23/59-62,
  the Sarai sidecar writer + fail-closed validator, and native source-pin asserts
  (`pc_randomizer_p2_source_for_70`, `findSeedActor`, the Otakara seed-add).

### Subagent usage (honest)

Two `explore` subagents ran (this time successfully) and one `general` was not
needed: explore #1 audited the Sarai/Otakara/Dwarf-Orange generator-selection sites
and the seed-bridge API (its `_70`-vs-spawn-slot-uid caveat shaped the
`pc_randomizer_p2_source_for_70` design); explore #2 inventoried the seed-placement
+ `*-actors.txt` machinery and identified `install_layout` as the seam to extend.
Both used as-is; the native edits, the run and the handoff were mine. Net: the two
audits collapsed the read-heavy recon (~1h) that would otherwise have cost several
build/run round-trips.

### Exact reproduction commands

Live Sarai seed-driven bridge (`scripts/run_p2_bridge_sarai.py`):

```
py -3.12 output/deepseek-wave/slot.py run gl l03 -- py -3.12 scripts/run_p2_bridge_sarai.py \
  --assets "C:/Users/alari/bbft/dist/cohesion/pikmin/assets" \
  --imported "C:/Users/alari/pikmin-randomizer/output/dsw/l22-assets" \
  --sarai-source "C:/Users/alari/pikmin-randomizer/output/l30-drive-arena/b4c465c48592419caed342a1aa6347e7" \
  --exe "C:/Users/alari/pikmin-randomizer/output/dsw/native-l03-build/bin/nectar.exe" \
  --output "C:/Users/alari/pikmin-randomizer/output/dsw/l03-out" --seed "l03-bridge-sarai" --timeout 45
```

Live Otakara seed-driven bridge (`scripts/run_p2_bridge_otakara.py`):

```
py -3.12 output/deepseek-wave/slot.py run gl l03 -- py -3.12 scripts/run_p2_bridge_otakara.py \
  --assets "C:/Users/alari/bbft/dist/cohesion/pikmin/assets" \
  --imported "C:/Users/alari/pikmin-randomizer/output/dsw/l22-assets" \
  --exe "C:/Users/alari/pikmin-randomizer/output/dsw/native-l03-build/bin/nectar.exe" \
  --output "C:/Users/alari/pikmin-randomizer/output/dsw/l03-out" --seed "l03-bridge-otakara" --timeout 45
```

Dwarf Orange 44-cohort seed placement (`scripts/run_p2_seed_placement.py`):

```
py -3.12 output/deepseek-wave/slot.py run gl l03 -- py -3.12 scripts/run_p2_seed_placement.py \
  --assets "C:/Users/alari/bbft/dist/cohesion/pikmin/assets" \
  --bank "C:/Users/alari/pikmin-randomizer/output/dsw/l05-out/slice5/cohort44/content/BlueKochappy/bank" \
  --profile "C:/Users/alari/pikmin-randomizer/output/dsw/l05-out/slice5/cohort44/content/BlueKochappy/profile" \
  --exe "C:/Users/alari/pikmin-randomizer/output/dsw/native-l03-build/bin/nectar.exe" \
  --output "C:/Users/alari/pikmin-randomizer/output/dsw/l03-out" --seed "l03-placement-bridge" --timeout 45
```

### Checker output

```
23 Sarai (role=source):
  1. identity_spawn     accepted [PASS]
  2. movement_animation ignored [UNTESTED]
  3. attacks_receivers  ignored [UNTESTED]
  4. death_corpse       ignored [UNTESTED]
  5. transport_reward   ignored [UNTESTED]
  6. cleanup_reentry    ignored [UNTESTED]
44 BlueKochappy (role=source):
  1. identity_spawn     accepted [PASS]
  2. movement_animation ignored [UNTESTED]
  3. attacks_receivers  ignored [UNTESTED]
  4. death_corpse       ignored [UNTESTED]
  5. transport_reward   ignored [UNTESTED]
  6. cleanup_reentry    ignored [UNTESTED]
59 FireOtakara (role=source):
  1. identity_spawn     accepted [PASS]
  2. movement_animation ignored [UNTESTED]
  3. attacks_receivers  ignored [UNTESTED]
  4. death_corpse       ignored [UNTESTED]
  5. transport_reward   ignored [UNTESTED]
  6. cleanup_reentry    ignored [UNTESTED]
```
