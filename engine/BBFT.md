# BBFT Pikmin prototype

Run from a folder containing extracted Open Nectar assets:

```powershell
.\nectar.exe --bbft-port 39001
```

Without that argument or `BBFT_PORT`, the adapter is inert and normal play is
preserved. BBFT launches directly into a fresh day-one Impact Site story run,
using the native new-game initialization and opening teardown. Title and file
menus are bypassed; first Red Onion/tutorial events remain. Main Engine is not
granted or checked. Each launch isolates memory-card I/O under
`save/bbft_sessions/<timestamp>/card0` (and card1), so existing named saves are
never overwritten. Restarting this prototype begins a fresh run, rather than
resuming a previous native save. Later native save prompts may still appear.
The mandatory title audio initialization still runs: its bank-load callback
releases JAudio's first-load barrier before the intro. Bypassing that callback
would strand the main thread in the intro audio wait. Diagnostic milestones
distinguish audio setup, an actually rendered world, and active gameplay;
process survival alone is not a valid boot smoke test.

New seeds may set `pikmin_skip_tutorial=true`. This instead starts day two in
Forest of Hope, with the Red Onion already booted and twenty red leaf Pikmin
automatically withdrawn onto the field after landing. The native campaign
counts Main Engine as collected, while its AP check is disabled at both adapter
and transport boundaries. This mode reports Eternal Fuel Dynamo and Shock
Absorber, and does not require the old internal Forest of Hope Access item.
Old seeds retain the Impact Site / Main Engine behavior. The `PIKMIN_FOH_READY`
milestone requires twenty actual field reds and an empty Onion, rather than
merely a requested population count.
Impact Site is also unavailable in the native world map in this mode.

For isolated automated smoke tests only, `PIKMIN_BBFT_TEST_BACKGROUND=1` allows
simulation without foreground focus. It still requires server state, warp
release and region access, and still rejects background controller input.
Pair it with `SDL_AUDIODRIVER=dummy` so the test does not disturb another game.
The log explicitly records `TEST_BACKGROUND_ENABLED`; normal launches do not
enable this override.

BBFT mode waits for initial state, holds all application ticks while
the conductor parks Pikmin or its window is in the background, and keeps SDL
events and transport pumping. F9 requests the next game. The frame scheduler is
reset during the hold so returning does not catch up the elapsed day time.
Both audio outputs are silenced while held: the mixer leaves its output buffer
zeroed and the separate JAudio queue pauses, then resumes only if it was playing.
Saved user volumes are never changed.

The opening sequence automatically takes its existing skip-to-game teardown
path in BBFT mode. Start can skip other cinematics only when both movie and
scenes are authored as skippable and contain no event keyframes. Event-bearing
tutorials, Onion introductions, ship repair and ending sequences remain intact:
the engine's fast-forward path would omit their scripted commands. This does
not add a decoder for the port's unsupported pre-rendered video.

The prototype reports `Pikmin: Main Engine` and
`Pikmin: Eternal Fuel Dynamo` when those parts reach the ship. Native ship-part
collection and saves remain intact. Loading a save reconciles these two checks
when the course selection queries its accessible areas. Forest of Hope needs
both vanilla access (collect Main Engine) and the received
`Pikmin: Forest of Hope Access` item. The world map refreshes that access while
open, so incoming items do not require relaunching or spending another day.
A new native save paired with an existing
AP seed still needs to collect Main Engine locally; server checks do not inject
parts or replay tutorial cinematics.

This is a two-check connectivity prototype, not a full Pikmin randomizer.
Normal day limits and all other native progression remain in force. Actual
ship-part delivery, save transitions, and three-game foreground switching need
interactive playtest coverage.

## Native Windows build

Use MinGW GCC, CMake, Ninja, and MinGW SDL2. The configured local build is
`build-bbft`, with the executable at `build-bbft/bin/nectar.exe`.
Configure `PIKMIN_NATIVE_JAUDIO=ON` to match the tested release audio engine.
MinGW needs `-UWIN32` (the original Win32 renderer is incompatible); CMake adds
it unless already supplied. SDL OpenGL headers avoid case-insensitive header
collisions with old port stubs. Unix chmod is skipped on Windows.

The current local build statically links the GCC/C++ runtimes and needs
`SDL2.dll` plus `libwinpthread-1.dll` from its matching MinGW installation.
Its native CPU optimization is suitable for this machine. Set
`PIKMIN_NATIVE_OPTIMIZE=OFF` before distributing a portable release.

`pc_bbft_test` verifies opt-in behavior, hold/release, foreground handling,
continued transport polling, F9 and incoming access using a fake transport.
It does not substitute for the actual gameplay test.

The files in `pc_port/bbft` are unchanged copies of the canonical Windows C
transport in the BBFT repository. Keep updates synchronized with that source.


## Full Pikmin progression (opt in)

`pikmin_progression: true` implies the Forest of Hope day-two start. Impact Site
is unavailable. The three later areas use `Pikmin: Forest Navel Access`,
`Pikmin: Distant Spring Access`, and `Pikmin: Final Trial Access` without vanilla
ship-part-count gates. All 28 parts outside Impact Site report permanent checks.

Yellow/Blue Onion discovery checks use the original wild-onion generator
coordinates; receiving an Onion item never awards discovery. `Yellow Onion` and
`Blue Onion` unlock their colors independently and grant five stored leaf Pikmin
once per fresh session. Existing local onions activate immediately; an onion
absent from the current area appears at camp on the next normal landing.
Reconnecting or changing area never refills the starter stock. Locked local
sprout/candypop colors become red and locked onions cannot boot or dispense.

Diagnostics log `PIKMIN_AREA_ACCESS` when area availability changes and
`PIKMIN_COLOR_STOCK` plus `PIKMIN_*_ONION_GRANTED` once for each color grant.


## Shared capabilities (opt in)

With `shared_capabilities: true`, `Zora Tunic` replaces `Blue Onion` as the blue
Pikmin unlock; an old Blue Onion item cannot unlock blue in this mode. Yellow
Onion is unchanged. Bomb-rock pickup/mining and placing/throwing additionally
require both Yellow Onion and Bomb Bag. Legacy seeds retain their original
blue-item and bomb-rock behavior. `PIKMIN_BOMB_ROCKS enabled=0/1` reports changes.

`python scripts/test_pikmin_progression.py --shared --exe <staged executable>`
from the BBFT repo runs the isolated native startup/item-state smoke. It verifies
blue stock is withheld for Blue Onion, granted for Zora Tunic, and bomb eligibility
changes only after Bomb Bag. Physical bomb pickup/throw still needs playtesting.
