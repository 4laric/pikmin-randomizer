# Tank proxy runtime evidence

Issue #202. This is a private native fixture on the original P1 Impact Site, not a P2 combat implementation. The fire actor retains P1 Tank AI, collision, health, flame receiver and corpse behavior. Water remains a static, noninteractive display without an enemy actor, collision or Bubble receiver.

## Fixture and provenance

`scripts/pikmin2_tank_actor_fixture.cpp` uses actual generator IDs 186151 (fire appearance), 186152 (ordinary P1 control), and asserts no actor owns display ID 186153. It permits normal native movement, records animation counters, checks the ordinary control declines appearance delegation, and resets the optional module before verifying both actors decline delegation. Only the captain is repositioned for observation. No enemy action, state, velocity or position is forced.

Startup extinction tutorial 13 is dismissed through normal Controller A updates in a private instrumented `newPikiGame.cpp`; no UI flag is forcibly cleared. Movies are skipped. This is injected fixture input, not physical controller QA.

Frozen completed production inputs: native `b602d8c43dc6a1132821f787b99a28097c3c7521`, root integration `95be51e`. Snapshot provenance is `output/p2-lifecycle-batch/tank-runtime-link-01/provenance.json`. Exact private compile/link commands and fixture/tutorial source hashes are retained in each `tank-runtime-link-*/commands.json`; no shared native source or build was changed. Models derive from `tank-assets-05`.

## Results

Run 01 was deliberately retained as failed evidence: putting the captain 100 units from the actor triggered repeated normal P1 attacks and only 2.7 units of movement. It did not satisfy the movement gate. GX display-list warnings appeared during that attack run; their origin has not been isolated and this does not establish flame rendering acceptance.

Run 02, with captain observation distance 400, passed native birth `(-150,30,1850)`, 84.204376 units maximum autonomous movement, 198 moving frames, changing counters within native motion 6, live appearance and reset fallback. The actual moved/reset captures show the white source appearance reverting to the original P1 appearance. Exact executable and evidence are in `output/p2-lifecycle-batch/tank-native-02/result.json`.

Water load/draw logs alone are not treated as full visual acceptance. A dedicated framing run follows below. The static placement is explicitly an engineering display, not a physical aquatic enemy. Initial control XYZ is logged after startup settling, not claimed to be its exact birth height.

## Reproduction

Run `py -3.12 -m scripts.test_pikmin2_tank_actor_native` with `--assets`, `--profile`, `--exe`, `--output`, and a bounded `--timeout`. Use a fresh output path and an immutable private executable built from the fixture. The driver captures the executable path/SHA256 before launch, uses dummy audio, and validates logs. Focused checks: `py -3.12 -m pytest -q tests/test_pikmin2_tank_actor_native.py tests/test_pikmin2_tank_install.py`.

Open gates: P2 attack/receiver parity, corpse/combat outcomes, unsupported-motion visual fallback polish, dynamic material parity, pause mapping, and interactive Water Tank behavior. Passing these fixture checks does not close those gates.

### Final dedicated display run

Run 03 passed, using `output/p2-lifecycle-batch/tank-runtime-link-05/fixture.exe`, SHA256 `9807ee23edec4045529e7156623bdc83d69f0e8169caae895b1c60da4a354e9b`. Report: `output/p2-lifecycle-batch/tank-native-03/result.json`; session `d3f0fc8c78ec43fd8a77c9193067ae10`. It recorded 83.348083 units of autonomous movement and 269 moving frames, the same exact birth, changing native counters, an ordinary-control draw-decline assertion throughout the active bank, and reset fallback. Six focused tests passed.

The dedicated `tank-water-display.png` visibly shows the blue nozzle and white source body; `tank-actor-reset.png` shows it disappears after module reset while the ordinary P1 control remains. Foreground leaves obscure the lower body, so feet/ground alignment and unobstructed full-body framing remain unverified. No Water Tank actor exists in the native manager. There were zero GX DESYNC/Malformed/Unsupported-display messages in this final run. This narrows the first attack-run warning but does not diagnose or resolve it.
