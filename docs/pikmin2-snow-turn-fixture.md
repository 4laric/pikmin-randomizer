# Native Snow turning receiver fixture (#120)

`experimental.pikmin2_snow_turn_fixture` copies/instruments the existing room
fixture and calls real `BTeki::turnToward` on native actors. It changes direction
between direct calls and runs no simulation tick during the probe. Production
source and live seeds are untouched.

Nine cases cover positive/negative capped turns, small proportional turns,
359-to1 wraparound, the source negative180 tie, P1 arrival snapping, an already
aligned actor and a different P1 speed argument. The profile uses0.4 gain and a
10-degree cap per update while the P1 speed argument still sets arrivalStep via
native delta time. The fixture measures that delta time rather than assuming it.

The ordinary same-family actor, a temporarily cleared native ALIVE flag, forgotten
registration and reset registration must use the original P1 receiver predicate.
A full pc_p2_snow_setup reload restores opted behavior. The nonliving probe is a
controlled flag test, not a physically rendered or delivered corpse. This fixture
does not evaluate natural turn-state selection, locomotion or attack timing.

## Running

```powershell
py -3.12 -m experimental.pikmin2_snow_turn_fixture instrument --source native/tools/preview_p2_room.cpp --output output/my-turn-fixture/preview_p2_room.cpp
```

Compile/link only against a completed fresh native build. Replace source/object/
executable paths in the private recipe and add native/tools to include paths.
Regenerate the link inputs from current Ninja commands if new modules were added;
an older fixture recipe can omit new production objects. Do not overwrite shared
fixtures. Set PATH to include C:/msys64/mingw64/bin and SDL_AUDIODRIVER=dummy.

Run using `run --assets PATH --converted PATH --pod PATH --snow PATH --exe PATH
--output NEW_DIRECTORY`; add `--policy PATH` for the extracted turning profile or
omit it for the baseline. Output includes per-case directions/arrival flags,
native log, capture metadata and evidence.json. The binary hash is captured before
launch and compared to the capture identity.

Ten harness tests reject incomplete/duplicate cases, missing actors, wrong
arrival flags, failed exits, invalid delta time and wrong source angular patterns.
There are28 tests together with the turning policy suite. Runtime receiver results are recorded below, separately from helper tests.


## Runtime evidence

Fresh native build156cbefaf26841fc4f3e1d380605957d94b3a490 supplied the production
objects. The private fixture compiled and linked from the current Ninja object
list, including Sheargrub modules, with private executable/import-library outputs.
Recipe: output/p2-turn-runtime/fixture/commands.json.
Binary SHA256:
`dca1faf449c8c84f439d13d52df9a3b8f69bd039da7bb85ba029560f56e1ba99`.

Both output/p2-turn-runtime/opted/evidence.json and baseline/evidence.json pass
with exit0 and matching captured binary identity. Each contains54 direct receiver
calls: nine cases across six actor/registration states. Ordinary, nonliving,
forgotten and reset actors preserve original P1 results; reload restores the
configured policy. The baseline keeps P1 behavior throughout.

The enabled run measured native dt0.032057013 seconds. A90-degree target produced
a9.999999-degree Snow step versus3.3061166 degrees for the ordinary P1 actor in
the same run. A10-degree target produced3.9999998 degrees with the profile. The
half-turn tie took the negative direction, and a0.5-degree arrival snapped exactly
with the arrival result true. The baseline run had a different measured dt, so
its absolute P1 step should not be compared as though both runs used fixed30Hz.

No full scene reconstruction, natural P2 locomotion, attack event timing or
source180-degree completion behavior is inferred from these direct calls.
