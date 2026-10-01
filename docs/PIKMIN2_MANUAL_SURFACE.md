# Bounded manual entrance trip (#114 / #112)

`scripts/play_pikmin2_surface.py` connects a separate manual entrance App to the
normal production cave executable through the existing SurfaceLedger/SurfaceRunner.
This is one trip per session: entrance, two playable cave floors, interactive return.
It does not run the cave lifecycle fixture or inject deaths, conversions, receipts,
test control files, or automatic transitions.

The entrance retains the actual source floor and radius-60 engineered collision
fence. Terrain visible beyond it is inaccessible. All three source water boxes
remain in the staged metadata; native surface water gameplay remains unsupported.
The engineering cargo cannot be picked up. The private Pod and single waypoint
exist solely to satisfy native checkpoint/bootstrap requirements, not a hauling graph.

## Controls and persistence

Walk to the orange source-entrance marker and press F6, then confirm the existing
native descent dialog. Movement, throws, whistle, camera and F1 settings retain
their usual bindings. The separate App consumes nonrepeat F6 events exclusively,
avoiding a second request from `pc_window`. It invokes the same native checkpoint
guard after the frame. A private linker wrapper forwards settings-menu state and
rejects F6 while the settings menu is open; no production native source changes.
The accepted native handoff and actual captain position are captured before exit42.

In the cave, play normally; F6 at each source hole/geyser performs the normal
confirmed boundary save. Closing mid-floor resumes from that floor's entry, not
the current combat/treasure state. Relaunch the same command/output to resume.
At final return the entrance is interactive, but F6 re-entry is disabled. Closing
and reopening that returned entrance restores the committed cave result.

Surface world/day-clock state is not saved. The initial host day/time is a snapshot
placeholder, not a native surface campaign clock. No full-world restoration claim.
The staged entrance supports at most20 survivors: a larger cave result remains
durable but is rejected explicitly rather than truncating the party. Extinction at
the initial entrance is recorded as a failed session and cannot silently revive.

`entry-command.json` is a replayable launch/entry command. Only `session/surface-ledger.json`
owns committed progress. Interrupted handoffs require both a valid native transfer
and matching token-bound position; missing position fails without resetting state.
Per-launch records capture both executable paths and hashes before execution.

## Build and validation

Compile the separate `scripts/pikmin2_manual_entrance.cpp` App against current
production objects, replacing only the main object in the existing fixture link
recipe. Add `-Wl,--wrap=pc_window_set_settings_menu_open`. The current private
recipe/log are in `output/p2-lifecycle-batch/manual-entrance/`; object-base provenance
is native3cc4a532. No production/shared rebuild is required.

Run `py -3.12 -m scripts.play_pikmin2_surface --help` for required local asset paths.
Use the new `manual.exe` as `--surface-exe` and a **normal production game executable**
as `--cave-exe`, never `preview_p2_room.exe`. The remaining imported asset arguments
match `scripts.test_pikmin2_surface_roundtrip`; choose a new private `--output`.

Focused tests cover exact native entry/replay, rejected conflicting snapshots,
missing position, persistent extinction, manual staging, explicit >20 refusal,
close/resume and process-launch failure. Existing runner/ledger tests cover floor
progression, resume and returned state. Build/startup smoke does not establish
physical F6/controller acceptance or completion through normal cave gameplay;
those remain manual playtest gates.
