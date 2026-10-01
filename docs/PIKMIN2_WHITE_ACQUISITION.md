# Ordinary Ivory acquisition slice

Tracking: [#1075](https://github.com/4laric/pikmin-randomizer/issues/1075), following [#395](https://github.com/4laric/pikmin-randomizer/issues/395) and merged root #1053/native #83. Implementation owner: Codex through shared account `4laric`.

Bound experimental Ivory buds now use five normal intake/lifetime slots and a one-second closing interval. They accept inputs independently of the inherited P1 backing color and do not create P1 reward pellets when exhausted. The checks query Ivory after generator attachment; they do not modify shared Pom properties. Ordinary P1, generic Candypop and Violet branches retain their existing behavior.

Retail authority is local GPVE01 disc member `enemy/parm/enemyParms.szs::pom/enemyparm.txt`, SHA-256 `dd165853c89edfa3bf2779c377b9df5048535fda2bfa9e4aea179324de25be7e`. Its final ProperParms block has `ip01=5` and `fp01=1`; earlier base blocks repeat the keys and are excluded. Research `include/Game/Entities/Pom.h` names the fields; `src/plugProjectNishimuraU/Pom.cpp::setPomParms`, collision capture and `shotPikmin` define normal capacity and same-species refund. The P1 animation host remains an adaptation, not complete retail flower timing fidelity.

## Guarded controller evidence

Native source `e6bc894e86abed2eefb94f2863f3af4a0bc19fd0`, clean private tree `output/native-white-acquisition`, uses actual native input polling through an SDL virtual gamepad. The fixture explicitly assigns its virtual instance to P1 and P2 to none, avoiding an already connected physical controller. It drives whistle, movement, grab/throw, UI acknowledgement and plucking. It does not inject species, attach Pikmin to the bud, call the conversion callback, or stimulate plucking directly.

The independent state-query probe temporarily supplies captured-count, spent-slot and timer query inputs, then restores those values and generator binding before the next engine idle. Its five-input/one-second/five-slot results and legacy P1 capacity check are separate from controller acquisition evidence.

Fresh `output/white-acquisition/stage-08` observed twenty Reds, one bound Ivory, active Walk state, a centered 960x540 window and captain HP100. A real captured Red passed through `P2_IVORY_CONVERT count=1 slots=1`; nineteen Reds plus one White sprout became nineteen Reds plus one White actor and zero sprouts, conserving twenty bodies. The White actor had no Red immunity. The bounded launcher returned raw0 in 41.579 seconds with `P2_WHITE_ACQUISITION_PASS`. This proves one ordinary acquisition in a disposable arena. It does not prove a full five-input natural exhaustion/revisit sequence.

Fixture executable SHA-256: `7dfd1ebcda28d06369657f35eaf45e28a182d2aa6256a152cf979943928c4fde`. Production Release/GCC16.2/Ninja/JAudio/IPO build passed, with final no-op certificate at the same source pin; production executable SHA-256 `4b8176391ed90776d994ceb4a03b662af9b67e0993f42b92c52674b24027ed14`, dry run `ninja: no work to do.`

The same fixture's fresh forced captain guard run returned raw86 in 0.969 seconds, `captain_down=true`, with no acquisition PASS. That is a deliberate guard-input test, not an observed gameplay captain death. Every guard runs immediately after engine idle, before movie, pause or readiness returns.

## Fresh staging and retained failures

`scripts/preview_p2_white_acquisition.py` stages twenty explicit Reds through the current overlay, generator25 Ivory, existing local White pose models and Pod presentation, and an imported `room_4x4a_4_conc` model with capped collision and audited prototype routes. It requires an explicit converted-room directory. Local assets, output, saves and shader caches remain private.

Runs01-03 retained the original callback-only stager's incorrect P1 practice map. Run03 diagnosed six survivors falling at y=-1892 through-2034, with no captures, throws or sprouts. Runs04-06 retained input/UI limitations of the first harness; run07 retained virtual-pad assignment to the second controller slot. Run09 missed the mouth after neutral input; runs10-11 retained twenty healthy Reds but tighter continuous steering drifted or circled without capture. These failures are preserved. The final fixture separates walking into range from low-stick cursor pulses followed by neutral settle; its fresh repeat is pending. None of these failed runs is a gameplay PASS. Fixing the map and input ownership did not weaken the exact twenty-body assertion.

For reproduction, extract the prototype with `experimental.pikmin2_assets`, convert `arc/view.bmd` with render y-offset -1, and attach collision from `texts` using `experimental.pikmin2_collision --cap-exits`. Use `room.route.ini` as `room.ini`, then stage with the current script's explicit `--assets`, `--white`, `--pod`, `--room` and fresh `--output`. Build `tools/preview_p2_white_acquisition.cpp` with the canonical leased fixture builder. Launch through `scripts/run_pikmin2_fixture.py --arg=--experimental-pikmin2-room --pass-marker P2_WHITE_ACQUISITION_PASS --timeout 60`.

## Remaining gates

White remains an experimental preview species. Ordinary P1/AP campaign enablement, mixed selection/dismissal, complete action animation, natural five-slot exhaustion and refunds, source counters, stable bud persistence, ship storage, cave save/restart, gas, ingestion and buried treasure remain separate acceptance work. Previous injected callback allocation/refund evidence from #395 is preserved; it is not relabeled as controller gameplay. This slice closes neither the full White specification nor complete campaign gameplay admission.
