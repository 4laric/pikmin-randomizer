# Native Snow health fixture (#120)

`experimental.pikmin2_snow_health_fixture` instruments a private copy of
`native/tools/preview_p2_room.cpp`. It never edits production source. Compile
and link it against a completed production build, replacing only the source,
object and executable paths in the isolated fixture recipe. Add `native/tools`
to the include path for fixture includes. Do not link while production objects
are being rebuilt.

```powershell
py -3.12 -m experimental.pikmin2_snow_health_fixture instrument --source native/tools/preview_p2_room.cpp --output output/my-health-fixture/preview_p2_room.cpp
```

Run the resulting private binary with `run --assets PATH --converted PATH
--pod PATH --snow PATH --exe PATH --output NEW_DIRECTORY`. Supply `--policy
PATH` for the extracted optional policy directory; omit it for the baseline.
Set PATH to include `C:/msys64/mingw64/bin` and `SDL_AUDIODRIVER=dummy`.

The short probe requires actual initial and maximum health, an ordinary
same-family actor's original values, explicit forget and reload, and registry
reset. Ordinary actors are born through newTeki and then reset: health is
initialized by BTeki::reset, not newTeki itself. If the Snow actor is removable,
the probe also kills its manager entry and births a new actor at the same address
to validate the real manager reuse guard. It does not force reference counts;
otherwise that case is explicitly unmeasured. This test terminates immediately
after registry changes so it cannot disturb later gameplay.

For the longer corpse test, instrument with `--lifecycle`, then run with
`--lifecycle --seconds 180`. It retains the existing real combat, corpse carrying,
Pod delivery and duplicate receipt checks. The additional maximum-health query
runs only while the corpse PelletView still points at the actor, before native
cleanup clears that relationship. It never queries the actor after delivery.

## Evidence

Fresh native objects from integration 8510d34c were used for private binaries.
`output/p2-health-runtime/opted2/evidence.json` and `baseline/evidence.json` pass.
The installed ordinary family health is 130: Snow initial/max becomes 150 only
with the optional policy, while the ordinary actor stays 130. Explicit registry
forget, setup reload and reset pass in both configurations.

`output/p2-health-runtime/corpse-run/evidence.json` passes all lifecycle assertions
and the corpse max150 query. Natural combat, death, corpse rendering, physical
transport, 182-Poko exact ledger and duplicate receipt rejection all completed.
The capture records the executable SHA256 and exit status. No P2 combat FSM or
attack-event timing fidelity is claimed. Scene-manager reconstruction is still
unmeasured by this harness; explicit registry reload is not a complete scene load.

Eleven focused harness tests validate source anchors, missing evidence, policy
mode, incorrect health, nonzero exits and corpse observation guards. First failed
private attempts were a variable-name collision and omitted ordinary actor reset;
they were corrected in fixture code, without a production change.

The final probe also exercised actual same-address manager kill/birth with the
policy enabled: `output/p2-health-runtime/reuse/evidence.json` passes slot_reuse.
The equivalent baseline run `baseline-reuse` passes health/fallback assertions
but records slot reuse unmeasured because that actor was not removable at the
probe moment. No reference counts were changed to force it. Both final probe
runs use SHA256
`500557aae9ef88fa6c9dfa31cac4ec87f14acf370ba5b2c3e8eff7067c2fb3f8`.
There are now twelve harness tests (26 together with the policy suite).
