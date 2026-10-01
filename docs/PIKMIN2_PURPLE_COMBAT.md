# Purple ordinary campaign adult direct-hit slice (#940)

Owner: Codex through shared GitHub account 4laric.

Current recovery is based on root 5c96cdec and native 39973576f. Acquisition,
Violet staging, ship storage and species-aware day saves from #929 are already
on main. Closed PRs #941/native #29 are historical evidence, not merged combat.

This slice binds only source2 Chappy (adult Bulborb), by canonical seed UID and
source identity. Fire/Hairy variants and source1 Red Dwarf do not gain direct-hit
eligibility. Root writes P2_PURPLE_DIRECT_2 only for exact Chappy rows; native
rejects source1 in that campaign format. The legacy explicit fixture format is
unchanged. Later-stage and already defeated actors need not exist during setup;
each contact checks current UID, source and family registration. No host-type
fallback grants eligibility. Native collision and existing per-throw token
handling deliver the existing 50-point adult hipdrop without extra area damage.

New Purple sessions pin version2/adult-direct-v2 in purple-campaign.json. Existing
version1 sessions fail with a fresh-session instruction, without overwriting the
marker or saves. Use the matching older package to continue an old session.
No automatic save migration. Conversion, storage and AP check/protocol hooks are
unchanged. The paired native change must accompany root staging.

The opt-in purple_combat fixture uses an ordinary seed and natural Violet
conversion/pluck before native throw/collision. Captain approach, one descending
Pikmin placement/velocity adjustment and post-contact isolation are scripted.
It does not inject enemy HP, damage, FSM or RNG. Acceptance requires correlated
production UID/source/pointer traces, exactly50 queued damage and compensated
health loss50. Controls, throw aiming, broad enemy support and day-save persistence are
separate gates, not established by adult_direct mode. Custom startup
uses centered960x540; starting squad20 and captain-down exit86 must be observed
in fresh bounded runs. CI only compiles and packages, never runs game assets.

Red Dwarf quake, repeated Fit and stunned crush remain excluded and open on#940.
Adult staged-collision evidence is pinned to native 77d2b56f7: ordinary Violet
conversion/pluck followed by native 50-point collision, healthy captain,44.531 seconds.
It is preserved separately from persistence evidence.

## Fresh day-save/restart acceptance

Native a8e86b1bf adds fixture-only persistence_dayend and persistence_resume modes;
production code is unchanged from 77d2b56f7. Root staging code is cf1db9e5.
Set P2_PURPLE_COMBAT_MODE to the mode; restart also requires
P2_PURPLE_EXPECT_DAY and P2_PURPLE_EXPECT_MATURITY from the save observation.

Final save02 PASS in 95.766 seconds: native Violet acquisition from 20 Red Pikmin, one Leaf Purple,
ship deposit/withdraw conservation, ordinary sunset day 2 → 3, production
CAMPAIGN_SAVED generation 1 and native save index 0 → 5. Clock advance and menu
confirmation are scripted; no identity, maturity or checkpoint injection.
The checkpoint contains a complete 32768-byte native card, a valid checksum,
Purple counts [1, 0, 0] and White counts [0, 0, 0].

A separate process/run PASS in 14.438 seconds restored day 3, withdrew a Leaf Purple with
strength 10 / selection class 4, rejected an extra withdrawal from empty stock, and
re-deposited to stock 1 with field population 0 → 1 → 0. All campaign-file hashes
were unchanged. Root rejected legacy and wrong-combat session markers without
modifying saves; the exact original adult-direct-v2 marker was restored.

Restart's scripted map confirmation selected Impact Site, while the configured
adult UID 3640055869 belongs to Hope. The source2 seed catalog/profile binding
remained valid with no live actor required in the other area. This does not
certify returning to Hope and fighting the actor after restart. An earlier
fixture wrongly required that absent actor; its failed run remains preserved.
The correction waits for normal captain walk/idle and respects absent-stage
bindings. No production persistence blocker was found.

Both final positive runs observed 960×540 centered startup and healthy captain;
negative guard02 exited 86 with no PASS. Windows CI 36821664691 passes 204 tests
and no-work dry-run. Final fixture SHA-256:
5bf611a877d7ea6723c6ab66b1bfe55a56fdfa6df4658ab568d6e8cf1479a121.
Evidence is recorded on issue 940 and in local
output/purple940-persistence-final-review.json; prior runs are immutable.
Remaining: Red quake/crush, player aiming, live AP/network persistence, broader
families, and independent integration/export review. This bounded pass does
not close #940 or establish universal Purple gameplay acceptance.
