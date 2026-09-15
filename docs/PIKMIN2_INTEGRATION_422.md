# P2 family integration #422

Implementation owner: Codex through shared GitHub account `4laric`.
Root candidate `codex/p2-family-integration` starts at `152f28d`; native private
branch `codex/p2-family-native-422` starts at source-equivalent `e2247215`.
Both worktrees are under `output/p2-family-integration`; build directory is
`output/p2-family-native-build`. Shared dirty worktrees and native origin are untouched.

## Integrated handoffs

| Pushed candidate | Integrated scope |
|---|---|
| Flora `8e7ad1b` | Fresh Pelplant arena and lifecycle evidence; uses #419 explicit collapsed-normal policy |
| Lifecycle `fabf58d` | Death/forget/respawn/rebind fixture, registration queries and tolerant native rebind |
| Mamuta `643d2c9` | Rules/death/corpse harness and small-window replacement main; maintained rules already include stronger type guards |
| Armor `cc2ee2e`, Sokkuri dependency `e172a6f` | Source behavior modules, additive parameter/update/press/cleanup hooks and arena runners; native `c102a4d5` / `52c96fdc` |
| Receivers `82dbeaa` | Proxy damage and Pikmin immunity diagnostic, evidence parser and tests |
| Bulblax `7ae29b5` | Baby captain bite, King death/bomb/tongue scenarios, BTK diagnostic and export reconciliation |
| Envmap `c8aa791` | Optional Queen material conversion interface and tests; does not replace maintained #399 renderer |
| Window native `1d5a242b` / `da285dbf` | Default 960×540 centred production and replacement-main preview; existing squads preserved |

Selective application preserves the newer maintained material renderer, Snow
crossfades, Kogane hooks, actor-slot revocation, computed normals and skeletal
bindings. Older whole-tree exports and redundant native patch copies were not
used to replace current source. Scope is pinned to these handoffs; later lane
commits are separate work.

## Integration corrections

- Two branches used `pikmin2_batch2_runtime.py` for different probes. Retain the
  south fixture and add `pikmin2_north_runtime.py` for receiver infrastructure;
  importing receivers no longer changes another module's instrumentation.
- Lifecycle accepts the current replacement-main window setup, distinguishes its
  own marker from older corpse-observer markers, records a live squad, and uses
  tolerant rebind rather than the strict all-actors-present startup path.
- Rebind retains immutable model banks instead of allocating them again. Armor's
  captured-Pikmin pointer is revoked through the existing pre-recycle hook.
- Parameter overrides and manager cleanup preserve existing registered families.
  Baby draw selection retains maintained animated Queen specular handling.
- BTK diagnostics use the current display/source clock. The existing Queen
  material binding remains authoritative; the static envmap conversion is opt-in.
- The retained strict King injection parser initially rejected the new optional
  fields. A bounded parser now accepts legacy and 1–3 optional tick fields and
  rejects malformed, negative, out-of-range and extra tokens.

## Validation and provenance

Local evidence root: `output/p2-family-integration-evidence/`. No generated assets,
executables, screenshots, saves or logs are committed.

Full Python suite: **1562 passed, 23 skipped, 1052 subtests passed**. Subsequent
King-parser regression: **7 passed**, including compiled valid/boundary/rejection
cases. Other focused integration tests include receiver import isolation and
current-window lifecycle instrumentation.

Build attempt 1 compiled at `c32297aa` but link failed on `Jac_NoteDemoSkipped`
with the default JAudio option OFF. No executable acceptance claimed for it.
Attempt 2 at `7309e689` matches maintained Release/MinGW/Ninja and
`PIKMIN_NATIVE_JAUDIO=ON`: build PASS, no-work dry run; production SHA256
`C4533C12B75AF6915BE69F2B06F2D1FA0BDFD7DC6EC13CEFB2E5CC7D7297F3F6`.
Attempt 3 at `02279aea` contains only the King parser correction: build PASS,
no-work dry run; production SHA256
`BC644DAF20C03E9DEE4B35BF1AA1912DE9896C928B543DB387FF812EABB9859C`.
Fixture provenance status is `built` for each executable used below.

| Runtime | Result and limitation |
|---|---|
| Armor, native `7309e689` | PASS appear/move/attack2, bites at source frames 17.8/17.4 with matching eat events; no extinction. 35-second observation intentionally timed out; not a graceful-exit gate |
| Sokkuri, native `02279aea` | PASS hidden start/appear/movement/animation, 151.41-unit spread, no extinction; bounded 25-second observation |
| Flora, native `7309e689` | PASS death frame5, explicit forget, generator respawn, re-entry frame126 (`reused=0`), control alive; 20 starting Pikmin and small centred-window marker |
| Mamuta, native `7309e689` | PASS 10-red explicit squad, three flower sprouts, cap99 rejection, captain damage5, death tick151, native corpse and reset |
| Queen envmap conversion | Real profiled bank converts successfully in a new private directory; no new renderer-fidelity claim |
| King, native `02279aea` | Corrected run PASS all required gates: tongue/swallow, bomb damage, WarCry/cross-Emperor, death key, reset/reload; clean exit and no leftover process. Optional flick/trample remains untested |

Lifecycle fixture SHA256:
`aa83e2e87ff9ffc899053b4c31f4ecf9ade1b2bc7b3663b7dc9fbce42a8dc320`.
Mamuta fixture SHA256:
`15b98913bbdb309e75f2abfb2470a4d3a3b866cd3f1c1a0df119d350ea604643`.
The 20-red overlay only adds a squad when none exists; Mamuta's existing ten
are intentionally preserved. Window setup is now implemented in both entrypoints.
Older executables and staged directories must still be refreshed by lane owners.

## Acceptance limits

This merges bounded mechanics and fixtures, not Family complete. Injected
attacks/respawns do not establish natural combat, full scene/heap teardown,
campaign resume, transport/rewards or mixed-scene performance. Armor's source
part receiver/bridge behavior, Sokkuri water behavior, Pelplant source growth and
pellet delivery, and remaining Bulblax fidelity gates remain open. Receiver
observations distinguish queued P1-proxy damage from source Dweevil semantics.

## Final merge validation

PR #428 also incorporates maintained root `b4d57e9` material-color foundation.
Final native commit: `0ab3ea1219298235f8a1f4804c82cee2570b062c` (clean).
Build attempt 4 in `output/p2-family-native-build`: PASS; dry run reports
`ninja: no work to do.` Production executable SHA256:
`8B9CCAFEE79BFFDD8961FAF2E06814D484067B632A8117510B5A19179962A61A`.
All 1589 exported source files match this native checkout. Final affected suite:
**163 passed**, including the newly incorporated material-color tests.
Runtime evidence above is pinned to its stated pre-color native commits.

Corrected King fixture SHA256:
`b332bb1a5de1b4c5d644fc5c33c65be9c8d061349f6ac9a69b456e6f728a27df`.
Result: `king-runtime2/result.json`, all required checks true, exit 0.
The initial parser-failure evidence remains retained locally.

Agents should refresh from the maintained branch after PR #428 and follow
[the shared fan-out guide](PIKMIN2_IMPLEMENTATION_FANOUT.md), rebuilding their
fixture from their pinned native commit. Existing fixture executables do not
acquire the default squad or centred 960x540 window by fetching source alone.
