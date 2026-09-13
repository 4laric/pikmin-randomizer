# Honeywisp source asset bank (#196, parent #166)

Codex via assigned 4laric. Source-contract and converted-assets evidence only.

Run `py -3.12 -m experimental.pikmin2_qurione_assets --iso <local-iso> --output <new-directory>`.
The output is private local game data and must not be committed or distributed.

Qurione source ID 16 is a concrete Honeywisp. Its model and animation resources are
`enemy/data/Qurione/{model,anim}.szs`; parameter registrations are in
`enemy/parm/enemyParms.szs`, under `qurione/`. The model has nine joints.
There is no Qurione `enemystoneinfo.txt` entry; the first exploratory import retained
that missing-entry failure under output/p2-qurione196/first and was corrected to
require only the three actual parameter/animation/collision files.

The manifest records disc header, source revision/file hashes, archive hashes,
all retail parameter blocks separately, collision hierarchy and every motion.
Proper parameters are flight height 90, pitch rate 1.75, pitch amplitude 20,
death ascent speed 400 and death time 0.5. These are retail values, not header defaults.

| Motion | Frames | Events | Meaning |
|---|---:|---|---|
| waitl | 100 | 0:key0, 99:key1 | Wait loop markers |
| damage | 35 | 5:key2 | Drop state releases attached Egg |
| run | 10 | 0:key0, 9:key1 | Dead/ascent loop |
| appear1 | 30 | none | Appearance; state advances at animation end |
| hide1 | 30 | none | Disappearance; state advances at animation end |

`Qurione.cpp::attachItem` births a separate Egg and calls startCapture with the
`water` joint world matrix. `dropItem` calls endCapture and clears the pointer.
`body_jnt2` supplies glow/hit effects. Every sampled pose records both attachment
matrices in model space; a future actor must apply its scene transform. The bank
executes no events, spawns no Egg and awards no reward. Loop markers and source
frame durations are retained metadata, not native playback or event scheduling.

Two actual local ISO imports are recorded in
`output/p2-qurione196/reproducibility.json`: all output files hash-identical,
21 converted poses, 410592 MOD bytes, approximately 0.187 and 0.179 seconds on this
machine. Five clips converted without a blocker. Default four base samples per
clip include event frames; maximum eight base samples, at most fifty total poses,
eight MiB MOD disk budget and 120-second extraction budget. These timings are
asset conversion timings, **not game FPS**. Native load time and material safety
are unmeasured. Baked poses duplicate texture/material payloads and should not be
expanded to full frames or bulk-loaded without profiling. Materials are approximate;
no native rendering fidelity claim is made.

Next receiver contract: a separately identified Qurione actor on a P1 flying proxy
may display these samples and retain full placement XYZ. It must not inherit P1
nectar/drop credit implicitly. A dedicated Egg attachment/release receiver, state-
gated Pikmin collision, appearance/disappearance scaling, source flight movement,
and ascent removal are still needed. Source Move-only flyCollisionCallBack enters
Drop on a Pikmin collision; Drop key2 releases the Egg, then motion end enters Dead.
This is not a carryable-corpse workflow. Translating those mechanics is a separate
native increment; neither the Egg lifecycle nor the source FSM is implemented here.

Validation: `py -3.12 -m unittest tests.test_pikmin2_qurione_assets` (three tests).
Checks include registration/event mismatches, missing/duplicate attachment joints,
invalid pose limits, malformed animation records and nonfinite parameters.
