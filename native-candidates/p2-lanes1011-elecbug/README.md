# Native candidate: lanes 10/11 ElecBug electrical emitter

Private native branch `opencode/p2-lanes1011-elecbug` (not pushed to native
origin). This directory carries the focused review patches.

Composition:

- base `opencode/p2-submerged-native` @ `3d65f611` (lanes 10-12 consolidated
  candidate: electric/gas receivers, reaction states, species capability,
  Bulbmin identity/bridge, captain/squad)
- merge of `opencode/p2-species-elecflip` @ `3ae68101` (species umbrella,
  including the lane 14 ElecBug actor and its press/immunity gates) as
  `faa996e1`; the only conflict was the `TekiMgr::newTeki` forget-hook list,
  resolved by unioning both hook sets.

Focused commits (this series):

1. `058b67fc` Lane 10: named emitter/attack-volume acceptance contract + gate
2. `c94cd610` ElecBug: deliver real `InteractDenki` emitter and lane-11 immunity
3. `d345b108` ElecBug: log receiver acceptance and target reaction state
4. `eddbf832` ElecBug: emit one immunity marker per immune species in the sweep
5. `416ccb49` lane 11: extract cave checkpoint wire format + schema-3 gate

Full branch head `416ccb49`. Apply with `git am 0001..0005` on top of the merge,
or review the branch directly.
