# Snow actor lifecycle fixture (#120, #128)

`experimental.pikmin2_snow_lifecycle` creates a private copy of the existing
native room integration fixture and validates its evidence. Production native
source, saved games and shared executables are untouched.

The fixture uses one Snow-skinned native Chappy, twenty native Pikmin, the
source Citrus Lump and Research Pod in the existing concrete test room. This is
a controlled engineering layout, not a complete Emergence Cave floor. It keeps
the existing native controller movement, real carrying, combat and corpse
delivery test. It repositions the captain near the enemy before combat for
camera visibility and to expose the enemy's natural P1 attack. It never overrides
enemy health or animation. Pikmin transport/attack actions are assigned by the
inherited fixture rather than player input.

New observations capture `snow-attack.ppm`, `snow-death.ppm` and
`snow-carried.ppm`; log native attack/death motion and counter, corpse drawing and
carrying displacement; and require the existing full-delivery assertion. P1
attack motion 8 and death motion 0 select the imported source visual clips. This
does not implement or assert P2 combat/FSM fidelity.

After real delivery, the fixture reloads `p2-economy.txt` with `P2Economy` and
replays the saved corpse identity. It requires no additional credit and unchanged
P1 repair count. The identity is saved while the enemy is alive: native cleanup
clears the delivered actor's view/generator state, so post-delivery validation
must not dereference those fields. Receipt replay tests persistent economy
idempotency, not a second physical delivery.

## Running it

Generate isolated instrumentation:

```powershell
py -3.12 -m experimental.pikmin2_snow_lifecycle instrument --native native --output output/snow-lifecycle/fixture
```

Compile that generated `preview_p2_room.cpp` with the current native production
flags, and link it instead of `pc_main.cpp.obj` against current objects/libraries.
The integration lead owns the production build. This validation used
`native/build-randomizer` at native commit `872f0f00`; `native/build-stats` was
stale. The exact local compile/link recipe is retained in
`output/p2-snow-lifecycle/fixture/commands.json`.

With MinGW runtime DLLs on PATH, run the copied fixture and validate results:

```powershell
py -3.12 -m experimental.pikmin2_snow_lifecycle run --assets C:/path/to/assets --converted output/pikmin2-room105 --pod output/pikmin2-pod111/import-01 --snow output/p2-animation128/dense24 --exe output/snow-lifecycle/fixture/preview_p2_room.exe --output output/snow-lifecycle/test --seconds 180
```

Output must be a new directory. The command prepares private assets and saves,
records the fixture executable SHA-256 before launch, captures logs, then writes
`evidence.json`. Failure exits nonzero and lists missing stages. It requires all
draw/combat/carry/delivery markers, a zero process exit, exact two-receipt ledger
(180 treasure + 2 corpse Pokos), duplicate-credit evidence and matching binary
identity. Tests reject missing stages, duplicate/incorrect/unrelated ledger rows
and changed binary identity.

Run the thirteen focused evidence/instrumentation tests:

```powershell
py -3.12 -m pytest tests/test_pikmin2_snow_lifecycle.py -q
```

Early private fixture attempts are diagnostic failures, not native regression
claims: one missed its camera-setup tick and left the enemy outside the view;
later replay instrumentation incorrectly queried already-cleared actor fields.
The corrected instrumentation captures the identity while alive and only queries
the animator before the corpse phase. All such changes are in generated private
fixture copies; no production native fix was needed.

## Completed native validation

The corrected dense24 fixture completed with exit zero in 50.8 seconds. Every
required evidence stage passed: live draw, natural P1 attack motion 8, death
motion 0, corpse draw, carrying displacement, combat completion, real Pod
delivery, duplicate receipt rejection, exact ledger and executable identity.
The ledger contains only `treasure:dia_a_red 180` and `corpse:385875968 2`;
P1 repairs remain zero and both deliveries report `seeds=0`. The unprefixed
corpse ID belongs to this standalone room fixture; campaign floor-scoped receipt
logic is outside this test.

Evidence is under `output/p2-snow-lifecycle/final/`: `evidence.json`,
`capture/native.log`, `capture/capture.json` and the three PNG captures. Inspected
attack/death/carried screenshots show the Snow model retained through the
lifecycle. Combat particles and attached Pikmin partly obscure the death/corpse
images, so this is a material/lifecycle smoke test, not a review of every source
animation pose. Fixture SHA-256:
`62e44a7e797ec0f537c864866e66f37cfeb810553ead8fcabddbfa34e791f8f0`.
