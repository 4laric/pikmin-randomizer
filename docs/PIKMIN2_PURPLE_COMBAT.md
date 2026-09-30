# Ordinary campaign Purple combat

Issue #940 follows the acquisition/storage slice #929 and attack specification
#393. Implementation owner: Codex through shared account 4laric. This is a draft;
fresh combat runtime acceptance is pending.

Opt-in staging writes `P2_PURPLE_DIRECT_2` with exact seed spawn-slot UID/source
pairs for source 1 Kochappy and source 2 Chappy. Native setup validates the table
against ENEMY_P2, independently of which stage actors are currently loaded.
Each hit resolves the current generator UID and live family registration again;
other species sharing a P1 host cannot inherit the special direct damage.
An absent actor on another stage is allowed. Actor pointers are not cached for
campaign eligibility. The existing room-only v1 protocol remains unchanged.

| Identity | Implemented bounded behavior | Runtime status |
| --- | --- | --- |
| Red Dwarf (1) | Campaign visual/health adapter initialization; existing press/crush and radius-60 quake/bounce/Fit adapter | Pending ordinary setup and real collision evidence |
| Red Bulborb (2) | Exact registered identity, one generic hipdrop attack of 50 through native damage handling | Pending campaign direct-hit evidence |
| Other identities | Existing family behavior; no new direct-hit binding | No new coverage claim |

The adult receives no new earthquake/stun reaction. The wave is not area damage.
Existing Orange behavior is preserved, but this slice does not certify it.
The Red adapter runs before Orange because it clears their shared stun registry.
The separate Kochappy source FSM currently owns Orange, not Red; this change
does not install two behavior schedulers on one actor. Red still uses the native
Chappy behavior/pressed lifecycle with the bounded source quake adapter.

The existing attack lifecycle provides source pause/descent/recovery and a
separate one-shot wave. Enemy contact runs direct dispatch, quake, then a vertical
velocity recheck before the second press callback. Payloads must not be summed
as unconditional damage. See PIKMIN2_PURPLE_DIRECT_HIT.md for historical room
proof and its limits; it is not evidence for this new ordinary campaign path.

Validation so far: 11 staging/production-header tests and 7 malformed-input
subtests; 18 existing direct/emitter/motion tests and 4 subtests. Tests cover
exact identities, wrong-species lookalikes, deterministic ordering, malformed
UIDs, duplicate bindings, opt-out and legacy parsing. These do not prove combat.

Fresh guarded runtime must establish the direct hit, nearby quake, duplicate
suppression, repeated throws/recovery, damage/death during stun and unsupported
controls. Scripted actor/captain placement and throw commands must be disclosed;
physical-controller acceptance remains separate. Every artifact stays private
under output; CI compiles source only and receives no proprietary assets.
