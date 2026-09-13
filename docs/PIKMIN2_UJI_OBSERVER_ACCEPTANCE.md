# Uji observer-camera acceptance

The male bite/eat visual gate PASSED against native7a4cca762b626cac4807b1ed0cc22987bed3de43. The private fixture05-observer snapshot, instrumented family object, final input hashes, Git state and Ninja freshness checks all passed. The previously rejected fixture04 executable was never run.

Static case: output/p2-uji-bite-runtime/validation04-observer/runs/1e642b24307947658a4faaa21b564fec. Animated case: output/p2-uji-bite-runtime/validation04-observer/runs/fcdeee40f45b45cab313b3cb066e5889. Both contain bite-acceptance.json and native.log showing native states6/7, mouth capture, prey death, zeroPokos and unchanged repairs. The fixture assigns a normal carrying task; enemy motions, health, positions and states are never forced. Stage-time bait geometry and exact slot checks are retained in bite-stimulus.json/logs.

Animated renderer telemetry records attack2 pose indices0-11 and eat0-9. PcamCamera::setTarget(source male) keeps the subject visible while Olimar follows the same approach/retreat controller route. Observed camera position(658.91,253.02,-566.08), defaultFOV23, target_visible1; the inherited Camera::mFocus field logs zero and is not treated as the computed Pcam watchpoint. Actual non-Navi target selection uses the male position through Pcam outputTargetWatchpoint. No production camera behavior changes.

Both uji-natural-bite.ppm and uji-natural-eat.ppm were converted losslessly to PNG for inspection in the animated run. The source male/prey encounter is visible beside the bait cargo; telemetry establishes sampled pose selection over the motion, rather than inferring animation from a single screenshot. The prey is visibly captured in the eat-state capture. This is developer fixture observation, not human manual gameplay QA or full P2 AI fidelity.

Female bridge attack1 remains open: it requires a real built WorkObject bridge absent from the Beasts scene. The prior free-prey/outside-range and off-camera diagnostic failures remain retained to explain the setup constraints. Existing bite fixture/module/test files were left unchanged during this acceptance run.
