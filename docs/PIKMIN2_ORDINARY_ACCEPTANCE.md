# Ordinary-input campaign acceptance (#1264)

Implementation owner: Codex through shared GitHub account `4laric`.

Use a frozen production executable, its matching host modules/assets, and an
independent copy of a genuine checkpoint. Keep all derived files under private
`output/`; preserve the original package and each failed attempt. Compilation,
host handshake, and body restore logs alone do not establish playable controls.

## Direct checkpoint launcher

`scripts/prepare_pikmin2_manual_checkpoint.py` copies a supplied manual cave
package into a fresh private destination. It verifies the executable/DLL and
starting-session hashes before copying. Include the package's `docs/` roster;
seed validation imports it. The original card is copied unchanged and subsequent
launches use the private `human-session`. Legal assets stay at their local path.

```powershell
py -3.12 scripts/prepare_pikmin2_manual_checkpoint.py --package <qualified-package> --output output/my-p2-play --seconds 600
```

Run the resulting `Start.cmd`. Normal keyboard/controller controls remain active.
The copied host closes its own game at the chosen wall-clock deadline. Unsaved
play then rolls back to the last real checkpoint. Each launch records native
logs, executable/source pin, duration, and any owned deadline stop. Preparation
does not certify gameplay. Never replace a profile's binary or card to upgrade
it silently; stage a new version instead.

## Short human route

Record each step independently, including any refusal or unexpected screen:

1. Reach active gameplay with 20 living Pikmin and a centered 960x540 window.
   On a genuine saved checkpoint, distinguish restored stock from live followers.
   Use Enter to skip allowed cinematics and Space to advance actual prompts.
2. Tap Up to switch captains; move each captain and switch back.
3. Acquire a Pikmin through the actual available source, wait for its native
   animation, and pluck/whistle normally. Saved or staged Pikmin do not establish
   natural acquisition. In a Violet room, throw a Red into the bud and pluck the
   resulting Purple; do not substitute a pre-created Purple.
4. Throw/swarm against a real receiver, observe damage, death and release from
   combat. Carry a real item to its receiver and verify the resulting collection.
5. Approach the cave boundary, press F6 and complete the actual native file UI.
   Traverse the available floor. Leave Reds on dry ground with X before crossing
   its water channel alone. At the exit near (800,0), use F6 and native file
   confirmation. This route does not establish Red water immunity or a Blue route.
6. Observe surface return. End the day and complete the native SAVE UI; close
   only after the resulting selection screen appears.
7. Relaunch the same private profile in a genuinely new process. Verify day,
   captains, party identities/health, collections and stock, then land again.

A provider with one floor cannot certify descent between multiple floors.
Full original-course progression and campaign graph resume require their own
qualified source providers and checkpoints.

## Isolated Linux partial route

`scripts/run_pikmin2_checkpoint_controls.py` uses a frozen resume39 surface or
floor41 cave input package (`--scene surface|floor`), exact production ELF hash,
explicit `--source-pin`, and a hash-pinned canonical
`OwnedX11Keys` helper. It creates its own displayfd Xvfb, private copied executable,
card/profile and settings. The helper verifies the actual native PID/window,
executable hash, focus, and centered dimensions before sending held ordinary
keyboard input. PNGs read that window's framebuffer; no observer fixture or
native actor/card edits are used. Run it within an owned 90-second user unit.
Its internal work deadline is 80 seconds, with bounded child cleanup. Two-second
holds allow the actual software-rendered engine to observe the keys at low FPS.

The current script tests only selected-checkpoint startup and controls. It records
actual `P2_CAPTAIN_SWITCH` events and screenshots for review. Sending a key is
not a PASS. Read the after-intro and final images before deciding whether the
game reached active play. `full_campaign_accepted` remains false.

## Concrete regression found on October 3, 2026

Independent Windows generation-1 copies of frozen native `8a3797de` restored
20 bodies and reached scene-ready, then displayed the P1 extinction tutorial.
The cave owner reproduced this on Linux native `59f78a8e` without movement.
`GameCoreSection::finalSetup` queued the P1 bonus-seed demo before the selected
living cave party was restored. The floor also failed to create two treasures
because its setup searched for a live `pr05` template instead of the native
configuration catalog. The cave owner owns both fixes under #930; builds and
fresh ordinary-play reruns are required before replacing the frozen package.

The generation-2 Linux route also enters `demo65.cin`: source review identifies
this as the Forest P1 bonus/extinction-seed cinematic. It is the same premature
startup check when the saved bonus-seed demo flag is already set. Longer waits
or forced skips do not qualify the intended selected-checkpoint startup. The
partial route now refuses either known startup flow and returns a failure.

Corrected native `3a2f4c11ad9dc1b06e0f7f1fed0ff6ac9654cdef` passed
the owner's fresh floor startup with 20 restored bodies and two treasure actors.
Independent generation-2 surface controls05 also avoided both startup defects,
preserved its card, and reaped its children, but recorded no captain switches.
The native party restore leaves captain FSMs in their landing state; the owner
is investigating surface readiness. Independent floor08 on that same corrected
ELF passed actual captain switches in both directions with ordinary held input
in 33.813 seconds. Screenshots show the cave, 20 followers, and the native pause
menu; the card remained unchanged and owned processes were reaped. This floor
control result does not certify bud conversion, treasure delivery, or campaign
save/resume.

Windows short-tap automation also had concurrent foreground interference;
unobserved taps are not mechanic evidence. Use a coordinated focus interval or
an isolated Linux display with held keyboard input.
