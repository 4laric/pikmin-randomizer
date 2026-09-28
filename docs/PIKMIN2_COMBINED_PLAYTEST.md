# Combined enemy and transition increment

Integration issue #114; Codex owner through shared account 4laric. Experimental branch only, outside v0.1.

The three isolated tracks have been integrated into source. The current two-floor engineering playtest can opt into imported Snow Bulborb visuals and explicit descent/exit marker positions. The full source content manifest is available separately, with all three treasure assets and 480 Pokos; it is not yet consumed by the single-treasure native receiver.

## Current playable scope

- One Snow Bulborb replaces the existing first-floor dwarf scaffold. Floor 2 still has no enemies. This does not reproduce the source cave's four-plus-seven enemy roster.
- Snow uses the disc's YellowKochappy texture and shared Kochappy mesh, with five sampled animation banks. P1 dwarf behavior, collision, parameters and attack event timing remain authoritative. It is not a full P2 enemy behavior port.
- Floor 1's amber ring/down arrow marks descent. Floor 2's cyan ring/up arrow marks exit. Approach the marker and press F6, then confirm. These are engineering markers, not imported hole/geyser actors or their source placements.
- Checkpoints still preserve squad/species/maturity, captain health and receipts at floor boundaries. Closing mid-floor restores the entire entry checkpoint. Exiting floor 2 saves a terminal result; surface return remains unimplemented.

Local marker positions are floor 1 `(80, 0, -100)` and floor 2 `(-550, 25, 520)`, radius45. Collision ground and four neighboring approach samples are flat at each position. These are deliberately placed near the existing landing areas, not claimed as source-generated positions.

## Compatibility

Optional Snow model/config/metadata bytes and transition config enter the campaign content fingerprint. Existing no-option profiles retain their previous fingerprint. Use a new session for the combined playtest. The previous `output/pikmin2-lifecycle112/Play.cmd`, executable and save remain available.

The Snow installer reads the actual prepared generator ID in native byte order and preserves the scaffold label used by receipt validation. Source Snow corpse value is two Pokos, matching the current Pod config. Empty floor-2 actor selection installs no enemy config.

## Validation

The combined Windows production build and native fixture linked successfully. Python suite:172 tests and20 subtests passed. Native configured-anchor tests passed distance/vertical/actor guards, two-floor transfer,19 survivors, ten Purples, maturity/health restoration,380-Poko terminal result, repeated reload and extinction. These persistence fixtures inject casualties/conversions and invoke collection directly; they are not manual gameplay acceptance.

The separate combined Snow fixture passed controller movement, treasure transport, Pikmin combat kill and far corpse delivery for182 Pokos without repairs/seeds. It uses explicit action assignment for parts of combat/transport. Logs and fixtures remain local under `output/p2-next`.

Next content integration must implement per-instance multi-treasure registration and receipt handling before enabling the480-Poko roster. Surface round trip, authentic physical transition actors and full P2 behavior remain further gates.

Final native revision: `292c6830`. Both markers were visually inspected in native captures after synthetic captain positioning; their world projection/material state is set explicitly. Final executable SHA-256: `d696330562032d720952875c52d94a2d725fa114661c57dc735952ebf1467af9`. Fresh local launcher: `output/p2-next/Play.cmd`; player session was not pre-run.

Subsequent integration: [roster playtest](PIKMIN2_ROSTER_PLAYTEST.md) adds optional native per-instance cargo and the full treasure/enemy counts. The original extraction manifest remains immutable and describes its preparation-stage limitations; the runtime installer writes a separate engineered roster report.
