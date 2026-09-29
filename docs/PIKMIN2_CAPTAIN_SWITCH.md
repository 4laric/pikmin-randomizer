# Opt-in single-player captain switching (#928)

Implementation owner: Codex through shared account `4laric`.

Enable the existing `PIKMIN_P2_SECOND_CAPTAIN=1` option before launching a
private game. Press **D-pad Up** to change captain; the default keyboard binding
is **Up arrow**, remappable with the existing D-pad Up setting. Startup prints
`P2_CAPTAIN_CONTROLS` with the binding. Holding the button switches once; release
it before switching again.

Both captains must be alive, uncaptured, empty-handed and in Walk or Idle.
Throwing, plucking, menus, damage and cutscenes prevent switching. Rejected
presses are not queued: release and press again when safe. The camera and single
HUD follow the selected captain; squads keep their existing owners. The inactive
captain receives neutral buttons/sticks and uses the existing follow policy.
Co-op and versus bypass this feature and retain per-player input.

The existing second-captain model is shared Olimar. Louie assets, persisted
captain selection and two-captain cave/campaign checkpoints are separate work.

## Validation

`tests/test_pikmin2_captain_switch.py` compiles the production edge/neutralization
helpers and existing captain adapter. It checks held-button debouncing, unsafe
states, stale sticks/buttons, preserved device/freeze fields, switching both ways
without ownership writes, refreshed zero health and captive-target rejection.
This is an engine-double test; it does not establish walking/camera/throw gameplay.

Private native production build passes; fresh guarded runtime acceptance is pending. No existing
player sessions were launched or modified for this slice.

Focused command (private candidate selected using `PIKMIN_NATIVE_ROOT`):
`py -3.12 -m pytest tests/test_pikmin2_captain_switch.py tests/test_pikmin2_captain_adapter.py tests/test_pikmin2_captain_squad_split.py -q`
passed **4 tests**. A first test attempt incorrectly expected a raw zero-health
refresh to mark the adapter slot Down; the existing adapter preserves its phase.
The live input guard checks health independently, and the corrected regression
verifies that distinction plus actual Down/captured rejection.

Review correction: the first production build failed because the live glue
needed `Kontroller.h`; it did not produce accepted build evidence. Camera
rebinding now changes both target and controller, including automatic survivor
selection. Mouse aim, wheel and global lock-on/swarm queues follow the active
captain in this mode. The expanded focused regression passes **5 tests**,
including camera input rebinding and preserved co-op device ownership. Guarded
rendered gameplay remains untested.

Second production build passed at native `f4bafacfc`, executable SHA-256
`076149874106d0f830a498c058c5a1c9e607e4122821f639f0477beab2fc25ba`, with
no-work dry run recorded under `output/p2-wip-landing/captain-build-02` in the
canonical workspace. Independent review then found the free-camera drag path
still selected a physical input stream by target captain ID. The follow-up maps
this shared local mode to player 0's mouse/touch/right-stick stream, preserving
co-op/VS routing. A further production build is required for that correction.

Final source candidate: native `d723aae1107bdeefab7f32f37d1318a8faa3a1d1`, clean. Private Release/Ninja build in `output/native-p2-wip-captain-build` passed with four jobs; source identity stayed unchanged. Executable SHA-256: `78e9e0a8c2f8eff383b17f185b536560fe3cc3b302f174f123e4a866129abe21`. Follow-up dry-run: `ninja: no work to do.` Evidence: `output/p2-wip-landing/captain-build-03/` in the canonical workspace.

The root engine snapshot receives only the seven-file captain delta from native base `c7dae173f87fc18dedcc903f789b65fb67986b17`; unrelated snapshot differences are preserved. Five focused tests also pass against that resulting snapshot. The production build above certifies the private native tree, not a complete root-snapshot build. Independent review covers shared control routing and camera device ownership. This remains source-only draft delivery until fresh rendered acceptance; two external netplay processes occupied the current runtime limit during delivery.
