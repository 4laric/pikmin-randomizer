# Lane 13 — Mixed Dwarf Orange + Snow Bulborb scene probe

Fan-out lane 13 (`#120`/`#186`). This probe stages **two distinct enemy
identities in one native stage** on a single private build that contains both
the `pc_p2_dwarf_orange` module (source BlueKochappy 44) and the maintained
Snow Bulborb module (YellowKochappy fp00). It is the first mixed-scene check for
this lane; it is **not** a production admission and **not** a generated-session
run.

## 1. Scene contract

One private arena (`dataDir/stages/chal0/default.gen`) contains:

| generator | host type | identity | health | source |
|---|---|---|---|---|
| 211001 | `TEKI_Chappy` | Dwarf Orange Bulborb | 250 | `pc_p2_dwarf_orange` (BlueKochappy) |
| 211002 | `TEKI_Chappy` | ordinary P1 Chappy control | native fallback 130 | unmodified host |
| 5001 | `TEKI_Chappy` | Snow Bulborb | 150 | `pc_p2_enemy` (YellowKochappy) |

plus exactly **20 red starting Pikmin** (topped up from the overlay squad, never
exceeded). Snow configs (`p2-snow.txt`, `p2-snow-actors.txt` with generator
5001, `p2-snow-policy.txt` health 150) and all 60 `snow_*.mod` bank files are
installed from the read-only preparation; the Dwarf Orange bank/profile/actors
come from the audited `orange-bank-first` / `orange-profile-first` configs.

The maintained Snow setup gate (`pc_p2_snow_setup`) aborts unless
`pc_p2_preview_goal()` is non-null. The probe therefore stages the Pod anchor
(`p2-pod.txt` + `pod.mod`) from the same read-only preparation. This is a hard
prerequisite of the Snow module, recorded as a limitation, not hidden.

All three generator scatter circles are zeroed by the deterministic fixture
override (`PRIVATE_CIRCLE_RADIUS_ZERO_1`); positions are engineered fixture
coordinates, not production placement evidence.

## 2. Fixture provenance

- Native source: `output/native-lane13-orange` @
  `2e3941c8d41fe541998b46e58b19179eb899dea7` (private candidate; **not** on the
  maintained line).
- Private build: `output/native-lane13-orange-build`, `nectar.exe` SHA-256
  `F72EF559FB45147FB7468D54C636E3DC6F6BFB871B84D470E195F5358DAEBCFD`.
- Instrumented fixture built by `scripts/build_pikmin2_fixture.py`
  (`--expected-native-head 2e3941c8d41fe541998b46e58b19179eb899dea7`):
  `output/p2-lane13-mixed-fixture2/baseline/fixture.exe`, fixture executable
  SHA-256 `AED5CF4932217B76351CA3B54BAF4AB3C635199034B1F778C2207AC93247DCAC`,
  provenance `status=built` with two `ninja: no work to do` freshness checks.
- Arena/run: `output/p2-lane13-mixed-arena/30f460e622b141168731406139e0e978`,
  evidence/log in `…/observe3/`.
- Probe driver: `experimental/pikmin2_mixed_bulborb_runtime.py`. The observer
  **replaces** the old two-actor Dwarf Orange observer (which hardcodes a
  2-actor roster) with a three-Teki-tolerant one. It injects no enemy state:
  health, AI, animation and damage are untouched. Its only stimuli are captain
  repositioning (tick 1 near the Dwarf Orange, tick 90 near the Snow) so each
  visual is drawn at least once.

## 3. Evidence and gates

Natural native markers (unmodified engine output):

```text
P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy generator=211001 ... health=250.0 max_health=250.0
P2_DWARF_ORANGE_BANK poses=64 ...
P2_ENEMY_READY species=YellowKochappy native_family=Chappy generator=5001 behavior=P1
P2_SNOW_POLICY generator=5001 health=150.0 ...
P2_SNOW_BANK poses=60 ...
P2_DWARF_ORANGE_DRAW corpse=0
P2_SNOW_DRAW corpse=0
[PC tick] ...
```

Because the maintained Snow module emits `P2_ENEMY_READY species=YellowKochappy`
(the source id) and resolves its display name "Snow Bulborb" through
`pc_p2_enemy_name`, the probe adds an explicitly **injected** observer assertion
`P2_MIXED_SNOW_DISPLAY name=Snow Bulborb generator=5001`. The native
`species=Snow Bulborb` string does **not** exist on this build; it is not faked.

| Gate | Result | Evidence |
|---|---|---|
| Both identities ready | PASS | `P2_ENEMY_READY species=BlueKochappy source_id=44`; `P2_SNOW_POLICY` + `P2_SNOW_BANK` for Snow |
| Both rendered | PASS | `P2_DWARF_ORANGE_DRAW corpse=0` and `P2_SNOW_DRAW corpse=0` |
| Exactly 3 live Teki at spawn | PASS | `P2_MIXED_ARENA_SPAWN teki=3 reds=20` |
| 20 red Pikmin | PASS | overlay squad = 20 |
| Centred 960x540 | PASS | `PIKMIN_P2_ROOM_WINDOW=960x540` + window log |
| No extinction | PASS | `Extinction` absent; exit code 0 |
| Frame budget | MEASURED (not accepted) | native rolling `[PC tick]` `tick` mean = 8.5 ms over 4 windows |

## 4. Measured scene budget

The native rolling `[PC tick]` rows are captured with `PIKMIN_TICK_STATS=1`. The
`tick` row is CPU tick milliseconds. Observed across 4 windows (window budget
16.7 ms):

- **MEAN tick = 8.5 ms** (the measured mixed-scene budget);
- last window 8.3 ms, slowest window 8.66 ms, last-window p95 9.47 ms.

This is explicitly **not** an accepted production budget: it is one run, one
camera stimulus, a 960x540 windowed preview and a single process.

Note: the Dwarf Orange ready line is split in the log by a concurrent
`P2_BOMBSARAI_ARENA invalid profile` write from another module's stdout; the
`P2_ENEMY_READY species=BlueKochappy source_id=44 … generator=211001` prefix and
the trailing `health=250.0 max_health=250.0 behavior=P1 purple_stun=…` remain
intact and are the natural witness. Exercise convenience: the 20 free Pikmin
engaged and killed the Dwarf Orange during the 240-tick window
(`P2_DWARF_ORANGE_DRAW corpse=1`); the spawn-identity gate is evaluated at tick
1 before any combat.

## 5. Limitations

- The native candidate (`output/native-lane13-orange` @ `2e3941c8`) is **not on
  the maintained line**; the integration lead owns export/acceptance.
- **No generated-session admission**: this stages a private fixture arena, not a
  generated/randomized session. There is no roster/admission-gate integration.
- The Snow actor's display identity is an injected observer assertion; the
  native Snow module identifies as `YellowKochappy`.
- Frame timing is a measured point estimate, not an accepted budget, and covers
  a scripted camera reposition, not player-driven play.
- Arena coordinates and the zeroed scatter radius are engineered fixture
  choices; terrain/physical placement acceptance remains unmeasured.
- This is additive tooling; no native source was edited and no engine target was
  rebuilt for the probe (only the isolated fixture object was compiled/linked).

## 6. Tests

`tests/test_pikmin2_mixed_bulborb_runtime.py` — three-Teki observer transform,
double-patch refusal, all-pass evidence, missing Snow/Dwarf draw, wrong Dwarf
identity, Snow policy/bank requirement, non-three roster, extinction/bad-exit,
tick parsing and the `mixed-arena.json` roster validation.
