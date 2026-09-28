# Bumbling Snitchbug first capture slice (#215)

User-selected P2-exclusive Demon ID32; parent166. Codex hard lane owns this
isolated successor to14d9391d. Groink revival is parked with issues open.
Source revision632af93787b9c95b63f0c13be32b161375ce3a96, Demon.cpp:20-91.

The target gate advances its timer per source query call, requires strictly
more than3 seconds, owner strictly inside territory, then returns the first
living non-mouth-stuck Navi within inclusive view angle and strict XZ sight
radius. Host supplies current angular/distance snapshots in Navi-manager
order; no nearest-target sorting is invented. Reset maps the source attack
timer reset hook; do not reset automatically on every successful query.

Per-slot grab eligibility uses strict 3D distance below slot radius, alive,
not already mouth-stuck and unoccupied slot. Host scans Navis then slot indices
in source order, reads live occupancy after each interaction and breaks after
the first eligible slot per Navi. Source increments caughtCount after calling
stimulate regardless of its return value: this counts attempts, not accepted
attachments. No captain ownership is changed by this module.

Demon inherits Sarai FSM/mouth machinery (Entities/Demon.h). Attack capture
checks occur after frame16 through30; event4 tests actual occupied slots and
can enter Fail; END chooses CatchFly only when a slot remains occupied
(SaraiState.cpp:408-517). Do not substitute attempted count for slot state.

P2 InteractSarai::actNavi (interactNavi.cpp:29-39) requires active game world
and an unstuck Navi, then startStick and NSID_Sarai transition. The decompiled
no-op path has no explicit return; do not copy undefined return behavior.
startStick/endStick update both linkage and slot occupancy (creatureStick.cpp).
Death init flicks occupied slots; final Creature::kill releases all stickers
before onKill. Host attachment and release must retain both sides consistently.

Validation: MinGW C++17 -Wall -Wextra -Werror, tools/p2_demon_capture_test.cpp
with -Ipc_port; output ../demon-capture-test-01/test.exe reports PASS. Tests
cover exact3-second threshold, first-versus-nearest selection, species-state
filters, strict territory/sight/slot boundaries, inclusive angle, pause/reset
and malformed snapshot rejection. Adapter bounds: finite nonnegative scalar
snapshots <=1e12, delta<=0.25, at most64 captains, angles within2*pi; per-slot
radius <=1e6. These are host budgets, not retail parameter claims.

Next: extract Demon/Sarai resource aliases, retail mouth geometry and motion
events; implement the capture flight/release host bridge. No converted assets,
live grabbing, captain state support, aerial movement, release or scene cleanup
acceptance is claimed by these policy tests. Shared hooks/build/export remain
with the integration lead; game assets stay private.
