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

Production build and fresh guarded runtime acceptance are pending. No existing
player sessions were launched or modified for this slice.

Focused command (private candidate selected using `PIKMIN_NATIVE_ROOT`):
`py -3.12 -m pytest tests/test_pikmin2_captain_switch.py tests/test_pikmin2_captain_adapter.py tests/test_pikmin2_captain_squad_split.py -q`
passed **4 tests**. A first test attempt incorrectly expected a raw zero-health
refresh to mark the adapter slot Down; the existing adapter preserves its phase.
The live input guard checks health independently, and the corrected regression
verifies that distinction plus actual Down/captured rejection.
