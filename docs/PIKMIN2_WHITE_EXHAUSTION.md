# Ordinary Ivory exhaustion slice

Tracking [#1094](https://github.com/4laric/pikmin-randomizer/issues/1094), following merged root #1091/native #97. Implementation owner: Codex through shared account `4laric`.

This fixture-only slice observes five normal Red-to-White conversions, five naturally spent slots, real Ivory death and generator cleanup, twenty conserved Pikmin bodies and zero new legacy P1 reward pellets. It changes no production source and does not inject species, capture, budget, timers, conversion, plucking or death.

## Exact observed boundary

Fresh run01 at native `4f460a409b5e367ba19d710c56206ed22c1fcd54` returned raw0 in 49.891 seconds. Final fresh run02 at `f8a53fe96f2d68a647f732dd0897ea61403d1bf2` returned raw0 in 56.063 seconds. The actual virtual SDL/native P1 path whistles, walks, aims and presses/releases the normal throw action. Each run ends with fifteen Red actors and five White sprouts, no captured inputs and twenty bodies. No plucking is required for this exhaustion result.

The actual `PomAi::mReleasedSeedCount` reaches five, the normal die animation finishes, and the bud leaves BossMgr's active list with `isAlive=false` and its generator detached. The live pellet count stays at the actual baseline of one (the staged treasure); zero new reward pellets appear. Sixty further engine frames retain the same counts after cleanup. Every engine idle is followed by the captain guard before movie, pause or readiness returns. Neither positive run triggers it.

BossMgr moves the existing Pom node to its free pool without deleting its object. This fixture rejects unexpected other active bosses and preserves the exact generator inventory: one Ivory Pom and no other boss generators, with all other challenge generator files empty. Post-kill field observations rely on this bounded no-spawn/no-reuse arena. They do not establish safety across allocator reuse, scene reentry or saves.

Final fixture SHA-256 `7a597d7d85aa42b11be139dbe003052eb483160c1e2ca56d33ddc0b2d0f1aa66`. Full separate Release/GCC16.2/Ninja/JAudio/IPO production build passed; final same-source certificate reports `ninja: no work to do.`, production executable SHA-256 `09f092e6c9135f370e33b28dfaf740860c77b9864789a4dbc5f5fc972296769a`. The same final fixture's forced guard returned raw86 in 0.969 seconds with no exhaustion marker. This is artificial guard-input evidence, not an observed captain death.

## Short manual smoke

The prepared local launcher is `output/white-exhaustion/Start-Ivory-Smoke.cmd`. It creates a new private arena for each attempt and opens a sixty-second smoke. Startup automatically skips movies, suppresses tutorials, whistles the twenty Reds, walks into range and aims at Ivory. The handover has twenty Reds, no White actors or sprouts, no captures and zero spent slots. It then yields actual P1 control to the keyboard/mouse. Startup-only verification reached this state in 10.172 seconds; no human feel approval is inferred.

Aim at the white flower and throw a few Pikmin. Judge the aiming/capture feel and whether the White sprout feedback is clear. Counts and exhaustion already have automated evidence.

- WASD moves; mouse aims.
- Hold and release Space to throw; Shift whistles.
- F5 requests a fresh reset; closing the game finishes the smoke.

The title displays these controls. Audio is muted. Controls/settings and runtime files are local to each disposable attempt. The reset branch reads the real native F5 keyboard state and the local helper relaunches on raw77; an actual human reset press has not been claimed as tested. There are no campaign or progression prerequisites. The manual mode returns before the automated exhaustion oracle and cannot create an automated gameplay PASS.

For source reproduction, build `native/tools/preview_p2_white_exhaustion.cpp` with the canonical leased fixture builder. Stage with the existing `scripts/preview_p2_white_acquisition.py` and explicit local `--assets`, `--white`, `--pod`, collision-backed `--room` and a fresh `--output`. Run automated acceptance through `scripts/run_pikmin2_fixture.py --arg=--experimental-pikmin2-room --pass-marker P2_WHITE_EXHAUSTION_PASS --timeout 60`. Set `P2_WHITE_MANUAL_SMOKE=1` for the manual handover; `P2_WHITE_MANUAL_STARTUP_CHECK=1` exits at readiness for an automatic startup-only check. Exact helper, input and executable hashes are recorded in the local handoff.

## Remaining work

Same-White ordinary refund, complete batch plucking, persistent exhausted-bud generation, ship storage, cave save/restart, campaign enablement, mixed selection/actions, poison, ingestion and buried treasure remain separate gates. This is one disposable arena's ordinary five-slot exhaustion/cleanup proof, not full White species or campaign acceptance. The prior #1075 handoff remains unchanged.
