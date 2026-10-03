# Blue rescue acceptance (#1230)

Implementation owner: Codex through shared account 4laric. Native candidate
`62dc59374017418bf40facae91e3e363fff0318b` is based on accepted combined
`66994856fce274cb280d18b0a4fda5497331a724`.
[Native PR](https://github.com/4laric/Open-Nectar---Pikmin-Native-PC-Port/pull/136).

The fix refuses rescue before holding the victim when no open dry waypoint is
available. It also clears reused survivor and animation state. The compiled
actual-source regression tests these branches and preserved valid-route control
flow. Its doubles replace route lookup, animation, FSM effects and trajectory;
it does not prove a physical rescue or Pikmin 2 gameplay parity.

## Short direct-gameplay script

Use a fresh private scenario with the candidate executable, twenty total Pikmin,
a 960x540 centered window, captain guard and sixty-second owned-child supervisor.
Keep player saves separate. Disclose staged colors: 19 Red and 1 Blue is suitable
for a mechanic test but cannot establish natural Blue acquisition. Leave eighteen
Reds safely on the bank. Disable Pikmin invincibility and Blues Only In Water.

1. Use ordinary controls to take the remaining Red and Blue to a shallow shoreline.
   Let the Red enter actual water and start struggling; keep the captain alive.
2. Stop whistling. Observe the Blue choosing Rescue, approaching, holding and
   throwing the Red to dry ground. Whistle escape cannot count as Blue rescue.
3. Confirm the Red lands alive on dry terrain, its water timer resets, and the
   Blue returns to ordinary activity. Recall and count all twenty survivors.
4. In a second fresh imported scene with no open dry rescue waypoint, repeat the
   approach. The game must remain responsive and the Red remain eligible for
   whistle recovery rather than entering an orphaned held state.
5. For campaign acceptance, acquire Blue naturally, cross the real water gate,
   save through normal UI, restart and repeat the route. Record species counts
   and the actual checkpoint. This step remains open.

Preserve source/executable/scenario hashes, native log, input/result records and
failure logs. Captain death or incomplete rescue is an unfinished/failed run.

No candidate-built Windows rescue launcher or successful ordinary rescue receipt
exists yet. The older `output/p2-surface-water/play_tutorial_water.cmd` uses a
different executable and proves water/whistle only. A new candidate-built scene
must pass guarded startup before offering its human direct-play launcher.

## Current boundaries

Accepted #1124 observed Red drowning, Blue immunity and ordinary whistle recovery
on source water volumes. Historical #1086 color labels were corrected by #1125,
which supplies actual Red-to-Blue bud evidence. Neither proves natural Blue rescue
or campaign progression.

Yellow electric immunity, fixed GasHiba/ElecHiba receivers, White ingestion poison
and Purple ten-strength carrying already have production consumers. Cave electric
gates include a proximity-open proxy; immune contact does not prove retail gate
work. White buried-item digging and full gate routes remain open. Acquisition and
party persistence stay with their existing cave/White/Purple owners.

Inherited `PikiWaterHangedState::exec` consults the victim captain's ThrowWait
state. Actual held-state continuity during Blue rescue needs investigation before
successful rescue is claimed. This PR changes no PikiState/cave/identity hook.
