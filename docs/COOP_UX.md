# Online co-op UX — issue #1133

This audit follows the accepted co-op feature line `5468b2eca`, including the radar and live Onion menu fixes. It covers the native online flow, independently of the P2 implementation program. BBFT has no active launcher for this native co-op flow and needs no change.

| Priority | Verified player problem | Current disposition |
|---|---|---|
| 1 | Verbose disconnect/desync diagnostics can wrap past the recovery screen's 14-row cap, hiding restart actions. | Fixed: separate short save status and role-specific steps; full diagnostics remain in the console. |
| 2 | Closing the host window while waiting for an answer leaves setup waiting on console input. | Follow-up: cancellation must stop the input wait safely. |
| 3 | Session-controlled F1 settings look editable but revert on closing/saving. | Follow-up: disable those rows with a clear host-controlled explanation. |
| 4 | The local launcher announces both windows before the peers finish connecting. | Follow-up: wait for both actual session-start events, early exits and timeout. |

Hosting and joining currently require an offer code and an answer code. Both players need the same executable and their own game data. The host's gameplay settings and saved day are sent to the joiner. There is no readiness lobby or reconnect within a running session. After loss, both restart, exchange fresh codes, and resume the last saved day; an unsaved first day starts again. The recovery screen now describes this directly. Pending day-end saves are explicitly unconfirmed, with the host deciding the saved day on restart.

The new text changes presentation only. It does not change networking, deterministic inputs, saves, the 10-second dismissal timer, or campaign continuation selection. The original Onion/radar packages and evidence remain immutable.

## Short human smoke

Use the versioned package's `Recovery-Smoke.cmd`. It starts two fresh local online peers: keyboard host and first-gamepad partner. Once both connect and enter gameplay, play for 20 seconds. The launcher then closes only its own disposable partner to show the host's connection-loss screen. Read the save status and restart steps. Rerun for another fresh campaign. No existing saves or shared assets are changed. The automated connection is loopback; internet reliability and player feel need separate human testing.

Human acceptance is pending: can the player read the screen before it closes, distinguish saved from unsaved progress, and know which launcher/code action comes next? The current short timer and any-button dismissal deserve feedback.

## Verification boundaries

Engine-free recovery tests cover all six end kinds, both roles, high-level and low-level launch paths, confirmed/no-save/pending/day-one/unknown-day states, and oversized diagnostic paths. Console recovery output stays unchanged. Wrapped text is checked against the fixed 640-wide DGX logical canvas, separate from the 960x540 desktop window.

The runtime smoke uses ordinary P1 co-op production startup and the game's fresh online-session seed. It is not a P2 room, cave arena or replacement-main fixture, so the P2 starting-squad overlay/captain-guard adoption is inapplicable; no P2 arena or campaign acceptance is claimed. Private production builds use the shared workflow registry and exclusive heavy-build leases. Actual paired gameplay, deterministic hashes and failure/recovery logs are recorded separately from this source explanation.
