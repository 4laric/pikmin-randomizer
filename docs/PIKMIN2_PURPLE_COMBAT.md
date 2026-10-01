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
health loss50. Controls, throw aiming, broad enemy support and fresh day-save
persistence are separate gates, not established by this fixture. Custom startup
uses centered960x540; starting squad20 and captain-down exit86 must be observed
in fresh bounded runs. CI only compiles and packages, never runs game assets.

Red Dwarf quake, repeated Fit and stunned crush remain excluded and open on#940.
No runtime PASS is claimed by this document before fresh evidence is recorded.
