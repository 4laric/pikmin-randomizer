# P2 Pellet Posy native release + capture receptor (lane 23, #171)

## Scope

This is lane 23's first **native** slice on top of the delivered pure-Python
behavior model (`experimental/pikmin2_flora_behavior.py`,
[`PIKMIN2_FLORA_BEHAVIOR.md`](PIKMIN2_FLORA_BEHAVIOR.md)). It implements the
bounded, opt-in source behavior of the **Pellet Posy** (`Pelplant`, source ID
0) on the existing P1 Palm actor:

- only a **full** posy is vulnerable; small and growing posies are invulnerable,
- a direct head latch (`s__0`) fells a full posy instantly,
- the dead state **releases its pellet**, which a Pikmin can pick up,
- there is no posy regrowth (a replacement is a generator respawn).

The visuals and the pelvis/pellet-drop mechanics are the existing **P1 Palm**
actor (`src/plugPikiNakata/taipalm.cpp`); this module is a native policy layer,
not a new actor. Registration reuses the existing experimental-room path
(`pc_p2_preview` + `pc_p2_*` module slots) and is additive: absent the sidecar
the module is inert and P1 Palm behavior is untouched.

New files (native):

- `pc_port/pc_p2_flora_policy.h` - pure, engine-free policy and strict
  `P2_FLORA_PELPLANT_1` parser (shared by the native actor and the standalone
  strict test).
- `pc_port/pc_p2_flora_actor.cpp` / `.h` - sidecar-gated binding, vulnerability
  enforcement, release claim and capture receptor.

Registration:

- `CMakeLists.txt` source list,
- `pc_port/pc_p2_preview.cpp` setup + capture-receptor hook in `pc_p2_preview_deliver`,
- `src/plugPikiKando/gameCoreSection.cpp` per-frame `pc_p2_flora_tick()` after
  `pelletMgr->update()`,
- `src/plugPikiNakata/tekimgr.cpp` `pc_p2_flora_forget` / `pc_p2_flora_reset`.

## Source anchors

| Behavior | Value | Anchor |
|---|---|---|
| States | WaitSmall 0 .. WitherSmall 9 | `Pelplant.h:37-50` |
| Full-only vulnerability | full only | `Pelplant.h:187-190` |
| Instant fell on head | special code ends in `0` (`s__0`) | `pelplant.cpp:485,518` |
| Dead releases captured pellet | release, not destroy | `pelplantState.cpp:445-451` |
| Growth fp01/fp02 | 90 s / 60 s disc | `Pelplant.h:284-285`, `pelplantState.cpp:193-257` |
| Colour cycle fp03 | 1.5 s Blue/Red/Yellow | `pelplant.cpp:407-450` |
| P1 Palm proxy | strategy/actions/visuals | `src/plugPikiNakata/taipalm.cpp` |
| Attacker-follows-drop | P1 PC port block | `src/plugPikiNakata/tekibteki.cpp:952-974` |

Audit: [`PIKMIN2_FLORA_AUDIT.md`](PIKMIN2_FLORA_AUDIT.md) (#171). Asset contract:
[`PIKMIN2_FLORA_ASSETS.md`](PIKMIN2_FLORA_ASSETS.md) (#353).

## Sidecar contract

`pc_p2_flora_setup()` runs once from `pc_p2_preview_setup()` and returns
immediately unless the experimental-room preview is active. It reads
`p2-flora-pelplant.txt` from the process working directory:

```text
P2_FLORA_PELPLANT_1 <count>
<generator-u32> <small|middle|full> <1|5|10|20> <blue|red|yellow|random>
```

- absent file -> **inert**, P1 Palm behavior unchanged,
- malformed file -> **fail-closed abort** (`P2_FLORA_PELPLANT invalid sidecar`),
- a bound generator must resolve to a live `TEKI_Palm`, or the module aborts.

For each bound posy the module stamps the P1 Palm personality
(`FLT_Strength`, `mPelletKind`, `INT_PelletMinCount/MaxCount`,
`FLT_PelletAppearChance`) and, for a fixed colour, `INT_Parameter0`/`_3BC`.
Non-full posies are kept invincible; full posies are cleared to vulnerable.

## Log contract

```text
P2_FLORA_PELPLANT_READY generator=<id> stage=<stage> pellet=<n> colour=<c> ...
P2_FLORA_PELPLANT_FELL generator=<id> stage=full instant_fell_head=<0|1> ... regrowth=0
P2_FLORA_PELLET_RELEASED generator=<id> pellet=<actual> colour=<actual> declared_pellet=<n> declared_colour=<c> declared_match=<0|1> capture_receptor=1
P2_FLORA_PELLET_CAPTURED generator=<id> carriers=<n> carrier=<ptr>
P2_FLORA_ONION_RECEIPT generator=<id> pellet=<n> pokos=0 seeds=0 onion_slice_unimplemented=1
```

The fixture self-terminates on a wall-clock ceiling (110 s) and prints
`P2_FLORA_RUNTIME_BLOCKED <gate> reason=<reason>` (`ready` / `fell` /
`captured`) instead of hanging; `completion` requires the explicit
`PASS P2_FLORA_PELPLANT_RUNTIME release_and_capture` line, so a blocked run can
never be read as a pass.

## Implemented vs BLOCKED

**Implemented (native, this slice)**

- Full-only vulnerability: small/growing bound posies are made invulnerable and
  stored damage is discarded; full posies are vulnerable (`gameCoreSection`
  tick).
- Instant fell on the head: observed and logged (`instant_fell_head=1`); the
  fell itself is the existing P1 Palm flower-damage route.
- Dead-state pellet release: the configured number pellet is dropped by the
  existing P1 Palm `spawnItems`; the module claims the new number pellet and
  logs `P2_FLORA_PELLET_RELEASED` with the **actual** dropped type/colour and a
  `declared_match` flag against the sidecar's declared identity. The module
  deliberately does **not** rewrite the proxy's `mPelletKind`/`mPelletColor`:
  the P1 arena only loads the pellet configs the stage references, so forcing a
  different kind makes `newNumberPellet` return null and `spawnPellets` drops
  nothing. The sidecar's `pellet`/`colour` are therefore a declared expectation,
  recorded and compared, not force-applied.
- Capture receptor: the module observes a Pikmin pick up the released pellet
  (`mCarrierCount >= 1`) and, if it reaches the Pod delivery path, reports
  `P2_FLORA_ONION_RECEIPT ... seeds=0`.
- No regrowth: no posy regrowth timer is added; the P1 Palm has none.
- Two-phase binding: the sidecar is parsed into pending specs and a proxy may
  resolve on any later frame, because generator actors can spawn after
  `GameCoreSection::finalSetup`. A spec that never resolves simply never emits
  its observation lines (the validator then fails closed). The first pending
  scan logs every scanned actor (`P2_FLORA_PELPLANT_SCAN generator=<id>
  type=<t> palm=<0|1>`) so a binding failure is diagnosable from the log.

**BLOCKED / remaining**

- **Onion-side seed receipt.** This module does not credit Onion seeds. A
  captured posy pellet that reaches a receiver is reported with `seeds=0` and
  `onion_slice_unimplemented=1`. The source-backed Onion arrival contract is
  still open.
- **Native Candypop actor** (`Pom` family, IDs 3-8), slot reservation and
  `ItemPikihead` births.
- **Plant spawn placement** (cave type 6 rosters, surface `plantsgen.txt`) and
  the Spectralid sentinel.
- **Hikari camera-facing** (#429).

## Approximations and labeled injections

- The bound actor is the **P1 Palm proxy**, not a from-scratch P2 `Pelplant`
  FSM. This is deliberate reuse; it is a valid P1 pelplant and carries the
  P1 model, animation and drop path.
- The `pellet_growth` timings use the disc fp01/fp02 (90/60 s) in the pure
  policy; the native layer does not re-time the P1 Palm growth, which already
  advances through the same strengths. Labeled as a policy/native split.
- The fixture stages a Pellet Posy generator by cloning the P1 enemy generator
  template and setting the type byte to 7 (`TEKI_Palm`). That is a **fixture
  injection** (the practice stage has no posy in this room layout), not source
  placement.
- Capture is observed at the pellet carrier counter and, when a Pod exists, at
  the delivery boundary. Neither proves full transport/reward accounting.

## Build and fixture provenance

- Native branch `opencode/p2-lane23-native`, commit
  `39217be67342829a4daa4c6e8682d1f0ee201ba6` (base `57bb1a4e`), clean.
- Private build `output/p2-lane23-native-build`, Ninja; dry run
  `ninja: no work to do.`
- Fixture `output/p2-lane23-flora-fixture-5/build/fixture.exe`
  SHA-256 `1548edcf876403d93c76c199caf779a9261f44c043620234c4bfb83c26ef231d`,
  `provenance.json` status `built`, expected native head matches.
- GL fixture runs are serialized and owned by the coordinator. This lane built
  only; no runtime/gameplay acceptance is claimed.

### Staged assets (`pikmin2_flora_runtime.stage`)

The private chal0 slot reuses the byte-preserved practice course, so no
`courses/pikmin2room/*.mod` asset is required and `pc_p2_preview` never tries
`treasure.mod`:

- `dataDir/stages/chal0.ini` = `dataDir/stages/practice.ini` (map is
  `courses/practice/practice.mod`),
- `dataDir/stages/chal0/default.gen` = the practice `default.gen` records plus
  10 Red Pikmin (injected squad) and one `TEKI_Palm` Pellet Posy generator
  (`_70 = 240001`, authored at `(34, 30, 1896)`; labeled fixture injection).
  The id is stamped **little-endian** at record offset 8 so `Generator::_70`
  reads back `240001` (`Stream::readInt` byte-swaps on the little-endian host
  and `Generator::readID` byte-swaps again; the same convention as
  `preview_pikmin2_room.ensure_pikmin_squad`),
- every existing `dataDir/stages/chal0/*.gen` overridden to an empty stage,
- `p2-cargo-free.txt` (`P2_CARGO_FREE_1`) so the preview skips the missing
  `courses/pikmin2room/treasure.mod`,
- `p2-flora-pelplant.txt` (`P2_FLORA_PELPLANT_1` / `240001 full 1 red`).

`stage()` asserts each of these files exists before launch and raises a clear
error otherwise; the fixture does not fall back to a partial asset tree.

Exact GL run command (from `output/p2-lane23-root`):

```powershell
$env:PIKMIN_P2_ROOM_WINDOW='960x540'
py -3.12 -m experimental.pikmin2_flora_runtime run --assets C:\Users\alari\bbft\dist\cohesion\pikmin\assets --output output/p2-lane23-flora-runtime-04 --exe C:\Users\alari\pikmin-randomizer\output\p2-lane23-flora-fixture-5\build\fixture.exe
```

## Validation

```text
py -3.12 -m pytest tests/ -q -k flora        # 74 passed
g++ -std=c++17 -Wall -Wextra -Werror -I native-patches/flora tests/pikmin2_flora_policy.cpp
```

No runtime/native gameplay acceptance is claimed by this lane.
