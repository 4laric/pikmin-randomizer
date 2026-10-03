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

## Actual rescue follow-up (#1245)

Native candidate `ba6e12b48c42127f52875927bb0dc3fc4ffc67a1` extends the first
fix in [native PR 145](https://github.com/4laric/Open-Nectar---Pikmin-Native-PC-Port/pull/145).
The PC held state now follows the live Blue rescue action instead of consulting
the victim captain's ThrowWait state. Ownership is cleared on interruption,
release, reused actions and stale roster entries. Competing Blues cannot steal
an already held victim. Source water volumes additionally mark submerged authored
waypoints as wet; source positions, radii and links remain unchanged.

The private Windows Ninja/MinGW Release build at
`output/native-blue-rescue-held-build` completed production `pikmin_pc`, both
actual-source unit targets, and `pikmin_ci_fixture_blue_rescue`, with optimize,
IPO, JAUDIO and netplay disabled. CTest passed 2/2 and the target dry-run reported
`ninja: no work to do.` Source checkout was clean at the candidate pin.

- Production `bin/nectar.exe` SHA-256:
  `adf54a42a03c8a22a65fa0e28332c820c3a5ebd26cb9fffd5be457363834a7ee`.
- Rescue fixture SHA-256:
  `298f8f40376cf2ce6f5970fd3d301d9466b1fa63ba36a8fa691707ff9abd6d10`.
- `output/p2-blue-rescue/arena01/run`: ordinary controller scenario passed in
  27.437 seconds, observing Blue-owned WaterHanged, Flying and living dry landing,
  with all 20 alive and all 5,332 source faces/three water boxes retained.
  The first hold was interrupted; a subsequent attempt succeeded. This proves
  eventual rescue in the scenario, not uninterrupted rescue or normal Blue return.
- `arena02/run`: forced captain-down stopped with exit 86, no PASS marker,
  in 0.797 seconds. `arena03/run`: hidden human startup passed in 4.687 seconds.
  All owned child processes were reaped; logs and input/result hashes remain local.

These receipts explicitly stage 19 Red and one Blue and use controller input
after staging. No post-staging actor position, velocity, held-state or health
writes substitute for rescue. Natural acquisition, an actual no-dry-route
gameplay scene, full campaign/save-resume and human gameplay judgment remain open.
The unit regression covers missing dry routes without holding a victim.

`scripts/play_pikmin2_blue_rescue.py` creates a fresh private scene every launch,
checks the supplied fixture hash, and supervises only its child for 60 seconds.
Use `--mode startup` for hidden startup, `--mode automatic` for ordinary rescue,
or the default human mode for the short direct-gameplay script above. Supply
`--exe output/native-blue-rescue-held-build/fixtures/pikmin_ci_fixture_blue_rescue.exe`
and `--expected-exe-sha256 298f8f40376cf2ce6f5970fd3d301d9466b1fa63ba36a8fa691707ff9abd6d10`.
Human readiness or a bounded stop does not record a gameplay verdict.

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

The first fix changed no PikiState/cave/identity hook. The follow-up changes only
WaterHanged hooks and the rescue action; ordinary captain-held behavior remains
the fallback when no Blue rescue ownership exists. Cave, identity and Free hooks
stay with their existing owners.
