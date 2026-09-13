# Review and integration pass #322

Owner: Codex using shared account 4laric. P2 base b6c6ad5.

Accepted cave stacks #298/#305/#310/#316/#319 and
#299/#303/#309/#315/#321. The only overlapping native implementation was the
cave entry profile, anchor admission and window title. The floor3-aware version
was retained while preserving the common guarded exit42 implementation; no old
engine animation/material work was replaced with the cave branch's older base.

Review covered: explicit tutorial/Beasts profile separation, failure/transition
admission, durable transfer before exit42, original revision/token correlation,
input/evidence hashes, uncertain commit replay, persisted launch intent before
process creation, no automatic relaunch, and source-bound floor assembly/cargo.
Floor3 remains an engineering entry with descent and failure persistence disabled.
The supervisor stops at its durable floor3 checkpoint. This is not full campaign
recovery or a complete playable five-floor cave.

Accepted Jellyfloat source material package commit
1243a13efc26965d8b934963570ca2cf4568b10b, cherry-picked as 1adf8ed.
It uses the already reviewed two-stage environment-map exporter. Its manifest
records the supplied converted geometry hashes; it does not attest the conversion
history, install actors, or claim full source material fidelity.

Validation on this combined root:

- 98 Beasts test methods passed.
- Nine focused material/interpolation test methods passed, including the native
  environment-map math and real pose-bank probes.
- Native cave profile probe passed tutorial1/2, Beasts2/3 and invalid floor/token
  cases with warnings treated as errors.
- Combined native production target pikmin_pc built successfully.
- Revalidated three frozen floor3 native runs using the merged validator and
  rechecked their executable/input/log hashes. These are existing worker runs,
  not newly executed gameplay on the combined binary.
- Rehashed both final-floor packages: all 19 files match their recorded hashes.
- Rehashed all 20 Jellyfloat patched models and their input model/pose files.

Local evidence: output/review322-beasts.log, review322-engine-final.log,
review322-artifacts.json; native output/build-322.log. Native integration is
recorded in #322. No retail assets, player saves or generated bundles committed.

Demon ec36f5cca611b42e5293d7ec953cee55b90efc6a is deferred. Its delta includes a
29-file unmerged state/ownership stack, not just the final follow hook. The owner
confirmed three exact-head pose/drop/teardown runs passed, but escape, external
state change and pre-heap teardown coverage belongs to older binaries. Repeat
those interactions with the final follow hook before integrating the stack;
render orientation and natural FSM acceptance also remain open. The unvalidated
efc0607b successor was not included. No code defect is asserted from this evidence
gap, and no aggregate old-binary test count is presented as exact-head acceptance.
