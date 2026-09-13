# Reusable converter + lifecycle handoff for family owners (#128 / #397 / #404)

Issues: [#186](https://github.com/4laric/pikmin-randomizer/issues/186)
(coordination/acceptance), [#128](https://github.com/4laric/pikmin-randomizer/issues/128)
(converter/animation), [#397](https://github.com/4laric/pikmin-randomizer/issues/397)
(non-invincible cleanup/re-entry fixture), [#404](https://github.com/4laric/pikmin-randomizer/issues/404)
(mandatory fixture adoption). Worked example: [#171](https://github.com/4laric/pikmin-randomizer/issues/171)
(flora parent), [#353](https://github.com/4laric/pikmin-randomizer/issues/353)
(source/import lane), [#405](https://github.com/4laric/pikmin-randomizer/issues/405)
(converter capability).

This note lets any P2 family owner reuse two things that are now proven:

1. The converter capabilities from **#405** (`singular_scale='allow'`) and
   **#233** (`singular_normal='transpose-adjugate'`, missing-normal policies),
   wired per species in the flora lane.
2. The lifecycle/six-gate fixture pattern proven on **Flora/Pelplant**: a
   non-invincible registered proxy is killed, cleaned up, respawned by its own
   generator and re-entered.

Read first: [the import pipeline](PIKMIN2_ENEMY_IMPORT_PIPELINE.md),
[the arena contract](PIKMIN2_ENEMY_ARENA.md),
[blockers](PIKMIN2_FULL_IMPL_BLOCKERS.md),
[family status](PIKMIN2_FAMILY_STATUS.md),
[the singular-scale policy](PIKMIN2_SINGULAR_SCALE.md),
[the fixture builder](PIKMIN2_FIXTURE_BUILDS.md), and the
[fan-out fixture baseline](PIKMIN2_IMPLEMENTATION_FANOUT.md).

Everything below is a **proxy** proof unless explicitly stated otherwise. A
proxy lifecycle does not establish source P2 FSM, receivers, rewards, collision
or campaign persistence.

---

## 0. Preconditions

- One family/FSM owner, a claimed child issue, and family-owned modules. Do not
  edit a neighbour's lane or shared converter defaults.
- Separate the two ledgers from the start:
  - **conversion** (asset correctness: clip count, clips/species unlocked), and
  - **runtime** (native spawn/behaviour/lifecycle gates).
- Keep all generated artifacts, fixtures, executables, logs, saves and disc
  content under private `output/`. Never commit them, never push native origin,
  never relink the shared Archipelago install.

Reusable assets:

| Item | Location | Notes |
|---|---|---|
| Reusable lifecycle runner | `experimental/pikmin2_lifecycle_runtime.py` on `codex/p2-family-integration` @ `4da2964` (not yet on this branch) | Instruments `native/tools/preview_p2_room.cpp`, stages the arena, writes `lifecycle-positions.txt`, validates the six-gate markers and emits `lifecycle-evidence.json`. |
| Reward/duplicate-receipt runner | `experimental/pikmin2_reward_lifecycle.py` on `opencode/p2-lifecycle-397` @ `9280a2f` | Gate-5 reward/ledger contract for the Pod economy. |
| Pelplant private fixtures | `output/converter-lane/flora_lifecycle_room.cpp`, `flora_carry_room.cpp`, `flora_deliver_room.cpp` (private, uncommitted) | Replacement-`main` fixtures. `flora_lifecycle_room.cpp` is the rebind/re-entry example wired to `pc_p2_batch2_rebind()`. |
| Native rebind/query candidate | `opencode/p2-lifecycle-native` @ `5c9492c6` (tolerant rebind), `4a16ef98` (read-only queries), `fb6389ce` (corpse-registry rebind) | **Needs integration export + #186 review; do not treat as landed.** |

`4da2964`'s runner re-enters with the strict `pc_p2_batch2_setup()` (all actors
present). The additive `pc_p2_batch2_rebind()` used by the Pelplant fixture
tolerates legitimately absent actors; it is still a native **candidate** and
does not change the startup contract.

---

## 1. Refresh a converted bank and record cleared blockers

Run the family's real extraction into a **new** private output (output must not
already exist, or the extractor refuses). Record the before/after clip counts
and the exact blocker text that moved.

```powershell
# generic form
py -3.12 -m experimental.pikmin2_<family>_assets `
  --iso output/pikmin2-runtime/pikmin2-source-test.iso `
  --source native/pikmin2-research `
  --output output/p2-converter-evidence/<family>-runN `
  --pose-limit 6
```

Flora worked form:

```powershell
py -3.12 -m experimental.pikmin2_flora_assets `
  --iso output/pikmin2-runtime/pikmin2-source-test.iso `
  --source native/pikmin2-research `
  --output output/p2-converter-evidence/flora-run2 `
  --pose-limit 6
```

What to do and record:

1. Extract twice into two new directories and diff the manifests
   (`<family>.json`). Only timing may differ; generated `.mod` bytes must be
   identical.
2. Diff against a pre-fix/baseline run. Non-target species output must be
   byte-identical (no silent global change).
3. Record the cleared blocker with its source:
   - `experimental/pikmin2_batch2_families.py` `blocked` string (for flora,
     `pelplant_receptor` changed from "poses do not convert" to "poses convert
     but the receptor is not registered"), and
   - the parent issue + `PIKMIN2_SINGULAR_SCALE.md`-style note.
4. Keep **conversion cleared** separate from **behaviour still blocked**. The
   converter knobs are opt-in and per species:
   - `experimental.pikmin2_purple.bca_pose(..., singular_scale='allow')` must be
     paired with `allow_scale=True`; it only relaxes an authored **zero scale**,
     leaving the authored value in the matrix.
   - `experimental.pikmin2_convert.decode(..., singular_normal='transpose-adjugate')`
     bakes normals through the unnormalized cofactor.
   - Wire both through the family's own per-species tolerance hook
     (`POSE_TOLERANCES` / `TOLERANCES` in the flora module). Leave other species
     and the strict defaults untouched. Unknown mode values must raise.
5. Do **not** claim runtime or gameplay from a successful conversion. #405
   explicitly is conversion correctness only.

If a species still fails on a new class of defect (for flora, HikariKinoko's
mix of shape-matrix type 1 billboard with type 3 skin), record it as a
**separate in-flight converter slice** rather than folding it into the passed
count. Billboard semantics are a renderer capability, not a static tolerance.

---

## 2. Stage a non-invincible proxy arena

Stage the family arena from its import manifest using the shared batch-2 core
(`experimental.pikmin2_batch2_core.prepare`). The arena uses the neutral P1
Chappy placement vehicle when the family has no P1 counterpart; identity is the
config key, not source identity.

Arena-only command (flora form):

```powershell
py -3.12 -m experimental.pikmin2_flora_arena `
  --assets "<P1 assets dir>" `
  --imported output/p2-converter-evidence/flora-run2 `
  --output output/p2-lifecycle-flora-evidence
```

Or through the reusable runner, which also stages positions and runs the
fixture:

```powershell
py -3.12 -m experimental.pikmin2_lifecycle_runtime run `
  --family flora --assets "<P1 assets dir>" `
  --imported output/p2-converter-evidence/flora-run2 `
  --output output/p2-lifecycle-flora-evidence --exe output/<fixture-dir>/fixture.exe
# re-stage an existing installed arena through the current overlay (optionally
# refreshes only the stage + starting squad; keeps installed banks byte-identical):
#   --existing output/p2-flora-397-evidence/<run-id>
```

Non-invincible requirements (do not fake these):

- The fixture must read `actor->getTekiOption(BTeki::TEKI_OPTION_INVINCIBLE)`
  and **require 0** before targeting; the birth log must show `invincible=0`.
  The reusable runner enforces `all_mortal`.
- Drive the source damage receiver with repeated
  `InteractAttack(navi, nullptr, 100000, false)` until death, or use natural
  combat; label injection explicitly.
- The starting squad comes from the arena `overlay()` (`ensure_pikmin_squad`,
  20 red Pikmin); this prevents startup extinction, not gameplay extinction.
- The replacement-`main` fixture does not run production `pc_main.cpp`, so it
  must set the #404 window policy itself:
  `pc_window_init(..., 960, 540)` then `pc_window_center()` (the Pelplant
  fixture does exactly this). Environment variables cannot add the behavior to
  an old executable.
- The lifecycle positions file columns are
  `generator native_teki_type registered x y z`, where `registered` is
  `1` for a family actor and `0` for the control. The reusable runner derives it
  from `arena.json`:
  `int(species != control)` + `expected_xyz`.
- Re-entry: respawn via the staged actor's own `Generator::init()`, then call
  the family registration hook (`pc_p2_batch2_rebind()` in the Pelplant
  fixture, or `pc_p2_batch2_setup()` for the all-present case). Assert a fresh
  pointer is not reused (`fresh_pointer_reused=0`) and the control is alive.

---

## 3. Build a private fixture against a private native build

Build a lane-owned native worktree and private Ninja build; never use the
shared `native/build-randomizer` for exploratory work.

```powershell
$env:PATH='C:\msys64\mingw64\bin;'+$env:PATH
cmake -S output/native-<lane> -B output/native-<lane>-build -G Ninja `
  -DCMAKE_C_COMPILER=gcc -DCMAKE_CXX_COMPILER=g++
cmake --build output/native-<lane>-build --target pikmin_pc -j 6
cmake --build output/native-<lane>-build --target pikmin_pc -- -n   # expect: ninja: no work to do.
```

Replacement-main fixture builder command form:

```powershell
py -3.12 scripts/build_pikmin2_fixture.py `
  --source output/native-<lane> `
  --build output/native-<lane>-build `
  --fixture <fixture.cpp> `
  --expected-native-head <full-40-char-native-commit> `
  --output output/<lane>-fixture-<attempt>
```

Pelplant example (native rebind candidate):

```powershell
py -3.12 scripts/build_pikmin2_fixture.py `
  --source output/native-lifecycle-397 `
  --build output/native-lifecycle-397-build `
  --fixture output/converter-lane/flora_lifecycle_room.cpp `
  --expected-native-head 5c9492c651ff1a9d75b228f9bf72ea31aa2b326e `
  --output output/p2-flora-397-fixture-rebind
```

Rules:

- `--expected-native-head` must equal the observed Git HEAD exactly, or the
  builder rejects. Use only an attempt whose `provenance.json` `status` is
  `built`; a produced exe from a rejected attempt is unusable.
- Wait for a completed `pikmin_pc` build, then hold inputs. Record native commit
  **and dirty state**, private build dir, executable SHA-256 and the `ninja -n`
  result. `--check-only` reports `checked_not_built` and does not check
  fixture-specific headers.
- The builder does not launch, stage assets or supply the squad/window policy;
  run it from the staged run directory.

Run:

```powershell
$env:PATH='output\native-<lane>-build\bin;C:\msys64\mingw64\bin;'+$env:PATH
$env:SDL_AUDIODRIVER='dummy'; $env:PIKMIN_P2_ROOM_WINDOW='960x540'
& output\<lane>-fixture-<attempt>\fixture.exe --experimental-pikmin2-room
```

For the Pelplant lifecycle run, the fixture source is
`output/converter-lane/flora_lifecycle_room.cpp` and the native candidate is
`opencode/p2-lifecycle-native` @ `5c9492c6` (tolerant `pc_p2_batch2_rebind`).

---

## 4. Run the six gates and record PASS/FAIL/BLOCKED/source-backed N/A

Every row needs a result **and** an evidence path plus hashes. Do not fold a
limitation into a PASS.

| # | Gate | Must observe | Pelplant proxy result |
|---|---|---|---|
| 1 | Exact identity and spawn | native type + full effective XYZ from logs | PASS (proxy): `P2_BATCH2_BIND generator=353001 key=flora|Pelplant`; `P2_LIFECYCLE_BIRTH id=353001 type=3 registered=1 invincible=0 x=-360 y=30 z=1850` |
| 2 | Autonomous movement and animation | live pose/anim selection, source looping | PASS with limitation: flora bank binds/loads and `P2_BATCH2_DRAW ... clip=wait`; source Pelplant is stationary, so this is P1 Chappy locomotion, not growth FSM |
| 3 | Attacks and receivers | actual receiver path, immunity conditions | PASS (injected): non-invincible proxy accepts `InteractAttack(...,100000)` to death; natural P1-proxy combat also observed. Not the source "Full only" rule |
| 4 | Death and corpse | death marker + corpse creation | PASS (proxy): `P2_LIFECYCLE_DEATH id=353001 frame=203`; `P2_BATCH2_DRAW corpse=1 key=flora|RedPom clip=dead`. Source pellet corpse N/A |
| 5 | Actual transport and reward | attach, route traversal, exactly-once delivery | PASS (P1-proxy reward) on a converted Pod room: `P2_POD_RECEIPT id=corpse:353001 value=2 new=1 pokos=2 seeds=0`, repairs unchanged. Source pellet→Onion seed reward N/A |
| 6 | Cleanup and re-entry | cleanup + respawn + no stale identity | PASS: `P2_LIFECYCLE_CLEANUP`, `P2_LIFECYCLE_RESPAWN_INJECT generator=353001`, `P2_LIFECYCLE_REENTRY ... reused=0`, control alive |

Status vocabulary: **PASS / FAIL / BLOCKED / UNTESTED / source-backed N/A**.
A noncarryable enemy needs an explicit `source-backed N/A`, never a silent
omission. Gate 5 for a proxy that cannot be carried must be recorded against
the reward ledger as N/A, not inferred from gate 4.

Evidence to capture per run (all under private `output/`):

- `arena.json` + sha256 (actor roster, XYZ, install receipt).
- `lifecycle-positions.txt` + sha256.
- `native*.log` + sha256 (UTF-16 from PowerShell redirection; decode explicitly).
- `lifecycle-evidence*.json` + sha256 (machine-readable gate markers).
- fixture `provenance.json` `status: built`, fixture.exe sha256, fixture source
  sha256, native commit + dirty state, build type, window policy, squad source.

The reusable runner emits `lifecycle-evidence.json` with `passed` and a
`checks` map (`completion`, `birth_count`, `all_mortal`, `target_selected`,
`receiver_accepted`, `health_reached_zero`, `died`, `cleaned_up`, `respawned`,
`rebound`, `drew`, `reentry_alive`). A PASS requires the
`PASS P2_LIFECYCLE_RUNTIME` marker and exit 0.

---

## 5. Mandatory #404 fixture-adoption record

Every lane's next handoff is incomplete without this record (from the fan-out
guide). A document link or commit acknowledgement is **not** runtime adoption
evidence. Fill every field; do not claim PASS from source alone.

```text
Fixture baseline adoption
Child issue / lane / implementation owner:
Root commit + dirty state / overlay source:
Native commit + dirty state / worktree / private build directory:
Squad change present / window change present (ancestry or source evidence):
Fresh arena command / run directory / asset and config hashes:
Executable SHA-256 / fixture provenance status if applicable:
Window setting / observed size and centring evidence:
Live starting Pikmin / active gameplay / no immediate extinction evidence:
PASS, FAIL, or BLOCKED; remaining work:
```

Pelplant worked example:

```text
Fixture baseline adoption
Child issue / lane / implementation owner: #397 (parents #171/#353/#405), lifecycle/acceptance, Codex via shared 4laric
Root commit + dirty state / overlay source: opencode/p2-flora-397 @ 2dd19ad (clean)
Native commit + dirty state / worktree / private build directory: 5c9492c651ff1a9d75b228f9bf72ea31aa2b326e / output/native-lifecycle-397 / output/native-lifecycle-397-build (RelWithDebInfo)
Squad change present / window change present: arena overlay ensure_pikmin_squad (20 reds); fixture pc_window_init(...,960,540)+pc_window_center()
Fresh arena command / run directory / asset and config hashes: py -3.12 -m experimental.pikmin2_flora_arena ... / output/p2-flora-397-evidence/61f4407845144c84a35f9c9b1a9bef91 / arena.json sha256 d40442be7e63980bc49e503ce579dca34f8993fc9736e6ece3cba532497cd4bb0
Executable SHA-256 / fixture provenance status: 1c44c368e66a3ee659b94de6cd5c32634fc6f6dc048716776c8d2e243a5423ac / provenance.json status=built
Window setting / observed size and centring evidence: PIKMIN_P2_ROOM_WINDOW=960x540; fixture init+center marker in native-rebind.log
Live starting Pikmin / active gameplay / no immediate extinction: squad present; P2_LIFECYCLE_* progression with control alive
PASS, FAIL, or BLOCKED; remaining work: PASS (proxy six gates); remaining source Pelplant FSM/pellet/seed, HikariKinoko shape-matrix type 1
```

---

## Recording checklist

Keep these three columns strictly separate; a green cell in one does not imply
another.

**A. Animation-event execution (runtime)**

- [ ] Which source events/loops execute natively (not just loaded as data)?
- [ ] Natural combat vs injected state/health/task clearly labelled.
- [ ] Frame markers for death, cleanup, respawn, re-entry; pointer reuse flag.
- [ ] Runtime failures: `FAIL p2 room: <message>`, non-zero exit, timeout.
- [ ] Unmeasured list: source FSM, receivers, rewards, campaign resume, mixed-scene perf.

**B. Material / TEV fidelity (conversion + visuals)**

- [ ] Clip/pose counts and pose sampling limit (`--pose-limit`).
- [ ] `pose_conversion_policy` / `decode_conversion_policy` / `singular_normal`.
- [ ] Explicit non-claims: no TEV/BTK/BRK parity; approximate material policy.
- [ ] Non-target species byte-identical; no silent static substitution.

**C. Runtime / lifecycle gates (native)**

- [ ] Six-gate table with PASS/FAIL/BLOCKED/UNTESTED/source-backed N/A.
- [ ] Fresh arena command, run directory, every artifact sha256.
- [ ] Native commit + dirty state, build type, exe sha256, provenance `built`.
- [ ] Injection vs natural behavior stated; no source-reward claim from a proxy.

**Cross-cutting**

- [ ] #404 adoption record filled (all fields).
- [ ] Cleared blockers recorded against their source (config string + issue).
- [ ] New blockers split out (e.g. HikariKinoko shape-matrix type 1) as their own slice.
- [ ] Native rebind/delivery candidates flagged for integration export + #186 review.
- [ ] No disc assets, generated models, executables, saves or logs committed.

---

## Pelplant worked example (hash summary)

| Item | Value |
|---|---|
| Native commit (rebind candidate) | `5c9492c651ff1a9d75b228f9bf72ea31aa2b326e` |
| Fixture source | `output/converter-lane/flora_lifecycle_room.cpp` sha256 `a74c3c3147dec792f961fb001d7c89e9e0090af720510b1ea09188086104357f` |
| Fixture exe | `output/p2-flora-397-fixture-rebind/fixture.exe` sha256 `1c44c368e66a3ee659b94de6cd5c32634fc6f6dc048716776c8d2e243a5423ac` (provenance `built`) |
| Arena run | `output/p2-flora-397-evidence/61f4407845144c84a35f9c9b1a9bef91`; `arena.json` sha256 `d40442be7e63980bc49e503ce579dca34f8993fc9736e6ece3cba532497cd4bb0` |
| Native log | sha256 `79ceeef4868ff77b55096e22432f138c4c8075060c3879de193d561485ed23a6` |
| Evidence JSON | `lifecycle-evidence-rebind.json` sha256 `87ab400f1e42e33426d419bfbd88d873f109542e72dc3892e792f1464b3c5571` |
| Gate-5 delivery native / fixture | `fb6389ce2968ae4c6da4563580f5ce672a9e32f7` / `output/p2-flora-deliver-fixture/fixture.exe` sha256 `2be01c43afcaac15657a2ecf0c66e8123029efeb6ba80db263642b43e0d62b43` (provenance `built`) |
| Gate-5 run | `output/p2-flora-deliver-evidence/a34e00c954ca4ea79ab977d3dd0e927e`; log sha256 `ec4c77cca31d4d9a8d2d7bce622980dcab26f1c638dca6b1b22f7833f4b6d2b9` |

Converter (from #405): Pelplant went 0/10 to **10/10** clips (`damage3`, `dead3`,
`grow1`, `grow2`, `wait1`-`wait3`, `bgrow1`, `bdamage1`, `bdead1`). No other
species' output changed. HikariKinoko remains 0/1 (`Unsupported shape matrix
type`) and is a **separate in-flight converter slice**, not part of this
handoff.

### Explicit proxy / source-reward limitation (mandatory wording)

Gate 5 is **PASS at the P1-proxy reward level, not the source reward.** On the
converted Pod room the proxy corpse is attached (20 carriers), traverses
~134 units, enters the goal and produces exactly one Pod receipt
(`corpse:353001`, 2 Pokos, `new=1`, `seeds=0`, repairs unchanged). The **source
Pelplant pellet release/capture and Onion seed reward are NOT implemented**: the
corpse is a P1 Chappy corpse drawn with the flora bank. The cargo-free arena
stalls mid-route and is not the gate-5 fixture. The proxy is a Dwarf Bulborb
vehicle, so this does not establish source Pelplant AI, collision or reward
semantics.

## Non-claims

No source FSM, pellet receptor, transport/reward parity, campaign persistence,
mixed-scene performance or material/TEV parity is claimed. The proxy identity is
deliberately not source identity. The native rebind/query/corpse-registry
commits (`opencode/p2-lifecycle-native` @ `5c9492c6`, `4a16ef98`, `fb6389ce`)
are candidates pending integration export and #186 review. Disc assets,
generated models, executables and logs stay under private `output/`.
