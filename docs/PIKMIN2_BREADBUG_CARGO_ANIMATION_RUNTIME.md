# Optional cargo animation runtime comparison

Scope #168, Codex owner under shared 4laric. A new private fixture subclasses
the unchanged natural cargo test. It observes the actual native animator and
production cargo phase helper while the P1 actor autonomously takes a real
red 1-pellet back to its nest. The comparison uses the same binary with and
without the optional bank; it does not force an enemy action or state.

Fresh native base `7a4cca762b626cac4807b1ed0cc22987bed3de43` was built by root.
The private builder verified freshness and copied link inputs at
`output/p2-lifecycle-batch/breadbug-cargo-animation-link-01/provenance.json`.
The existing recorded dirty creatureCollision/goalItem diff remains part of
that provenance; this is not a pristine-source claim. A private current-source
newPikiGame object supplies normal Controller A tutorial dismissal. Its hashes
and exact relink commands are in `breadbug-cargo-animation-link-02/commands.json`.

Executable: `output/p2-lifecycle-batch/breadbug-cargo-animation-link-02/fixture.exe`.
SHA256: `ad22547f2320289814d5a78030c90fe5b994a8f721ffc1893792bb99411b678e`.
Result: `output/p2-lifecycle-batch/breadbug-cargo-animation-native-01/result.json`.

| Observation | Baseline | Optional bank |
|---|---:|---:|
| Held update frames | 203 | 195 |
| Maximum horizontal displacement | 137.808 | 138.435 |
| Closest approach progress toward nest | 96.779 | 96.017 |
| Natural release and pellet no longer alive | Yes | Yes |
| Production cargo draw states | None | 5, 6, 8 |

This establishes unchanged bounded behavior, not identical trajectories or
simulation determinism. All three mapped states showed advancing source phases.
The original absent-bank draw path emitted no cargo-animation logs.

The fixture injects an engine simulation pause using `mPauseAll`, holds the
native counter across 59 checked updates in a 60-App-frame interval, then
restores the flag and lets the haul finish. Both runs passed. This tests the
native counter contract; it is not physical Start/F1/menu input QA. The logged
`frames=60` describes the interval, not 60 separate counter comparisons.

Captures were inspected. The Hide capture shows the imported model, but the
stump rim obscures its mouth/pellet connection and most of the Back pose. Thus
exact carrying alignment is still unverified. The result is a native state,
phase, pause and gameplay regression pass, not complete animation visual QA.
The fixture exits at release, so it does not independently test state 9's
invisibility or a later emergence cycle.

The new parser regression passes. It rejects missing pause evidence, absent
native draw states, non-advancing phases and cargo rendering without a bank.
Both actual native processes exited 0. No shared native changes/builds or
gameplay events were added by this runtime batch.
