# Frog visual proxy handoff

Issue #201, family #167, integration #186. Codex owns implementation using the
shared 4laric account. This is a prepared visual proxy, not a playable or complete
P2 enemy port. Source import #194 is integrated at root `65ad102`.

## Contract and source mapping

`pikmin2_frog_install.plan(bank, actors)` validates every pose before installation.
The accepted source contract is GPVE01 revision 0, `P2_FROG_IMPORT_1`, concrete
Frog17 and MaroFrog18, all eleven clips in source order. Bounds are twelve poses
per clip, 512 KiB per clip and 10 MiB total. Frames must include both endpoints
and increase strictly. Filenames, file sizes, SHA256 and immutable render chunks
are checked. Config is exact UTF8/LF bytes, hashed after construction; existing
targets and shared model destinations are rejected before mutation.

P1 `tekinakata.cpp:58` and `:165` register Frog0 and Frow33 with
`TaiOtimotiStrategy`; Frow has separate parameters/sound. Source P2 assets and
retail differences remain documented in `PIKMIN2_FROG_IMPORT.md`.

| P1 motion | P2 visual clip | Source basis |
|---|---|---|
| Dead / Damage | dead / damage | dying and failed jump actions |
| Wait1 / Wait2 | wait1 / wait2 | idle / airborne wait |
| WaitAct1 / WaitAct2 | waitact1 / waitact2 | turning / idle activity |
| Move1 | move1 | TaiGoingHomeAction |
| Flick | type1 | taiotimoti.cpp:550–571 jump wind-up, key then jumping |
| Type1 | type2 | :593 dropping before pressing |
| Attack | attack | :944 TaiOtimotiPressingAction starts attack |
| Type5 | type5 | PaniAnimator carried-pellet motion label |
| Others | static wait1 first pose | explicit unsupported mapping |

The source frame selected is nearest to the current native animator's normalized
counter. No wall-clock animation, source events or FSM callbacks are added.
Corpse rendering selects the final dead pose; source carry tremble fidelity is
not claimed. Health, collision, crush/stone/water receivers, drops and rewards
remain P1 behavior. In particular this module does **not** install P2 5/7-Poko
corpse rewards. Material/TEV approximation and attachment alignment require
runtime visual review.

## Isolated native patch and required integration

Only local `output/p2-frog-proxy/native/` contains `pc_p2_frog.cpp`, `.h` and
`pc_p2_frog_policy.h`; exact hashes/base are in `native-patch-manifest.json`.
No shared native source or build was changed. Root should copy these into
`native/pc_port` after review and add the following existing-pattern hooks:

- Preview setup: call `pc_p2_frog_setup()` alongside family setup after generators
  exist. It resets first, leaves absent config untouched, validates every requested
  generator/type and rejects duplicate actual IDs. No Pod prerequisite.
- `tekibteki.cpp`: add `pc_p2_frog_draw` to both live and corpse fallback chains.
- `tekimgr.cpp`: call reset at all family reset/teardown points and forget at
  actor reuse. Registry keys are PelletView pointers; reset clears all banks and
  shape references before heap reuse.
- `pc_p2_frog_name` is available for diagnostics. No receipt hook is requested.
  The arena deliberately does not bind a Pod or P2 economy.
- Preserve ordinary controls and missing-profile P1 fallback. CMake discovery,
  full build/export and runtime belong to the integration lead.

## Private arena and evidence

```
py -3.12 -m experimental.pikmin2_frog_arena --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets --bank output/p2-frog-import/import04 --output output/p2-frog-proxy/arena
```

Prepared run: `output/p2-frog-proxy/arena/15f17bac0c294931a9a04f3093c63d9b`.
Original Impact Site course files (render, collision, routes) remain byte-identical.
Existing generators are retained. Four additional engineering actors:

| Generator | Species / native type | Expected XYZ |
|---|---|---|
| 201001 | Frog / 0, registered | -150,30,1850 |
| 201002 | MaroFrog / 33, registered | 150,30,1850 |
| 201003 | ordinary P1 Frog / 0 | -150,30,1550 |
| 201004 | ordinary P1 Frow / 33 | 150,30,1550 |

IDs were searched for collisions and are checked against the source roster.
Generic offsets are zero. Exact template circle radius 50 is explicitly changed
to zero with before/after hashes, leaving other record bytes untouched. These
are engineering placements, not retail P2 generated positions or verified terrain
heights. Native stored birth XYZ and later physics drift must be logged separately.

Installed: 264 models, 8,583,168 bytes. Import SHA256
`b228f17f48e800fccb72fab1ccc5986f29e647e7a6126035386f010133ebfcb4`;
protocol SHA256
`0c929f7b0ac5c7375d0df2c277f8a574c71e61b9dcd9eaac4e0f1148071065ec`.

Validation: twelve Python tests pass (`test_pikmin2_frog_install` and
`test_pikmin2_frog_assets`). Isolated native syntax compile using current Ninja
flags passes; `compile.json` records exact command/base and `compile.log` warnings.
An isolated object compilation also passes (`object-compile.json`, including
the resulting object hash); no production linking or shared build occurred.
Standalone `tests/pikmin2_frog_policy.cpp` passes against the real installed config:
valid banks, duplicate ID, excess count, truncation/trailing tokens, endpoint/NaN
counter selection and unknown-motion fallback. This is parser/policy evidence,
not an engine runtime test.

All six arena gates—spawn, movement/animation, combat, death, transport and
cleanup/re-entry—remain **UNTESTED** pending a fresh integrated runtime. Mixed
scene performance, visible scale/ground/contact alignment and source gameplay
parity remain open. No player session or QA bundle was changed.
