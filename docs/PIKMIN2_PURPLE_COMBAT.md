# Ordinary campaign Purple combat

Issue #940 follows the acquisition/storage slice #929 and attack specification
#393. Implementation owner: Codex through shared account 4laric. This is a draft;
adult staged-contact acceptance passed; Red runtime qualification is pending.

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
| Red Bulborb (2) | Exact registered identity, one generic hipdrop attack of 50 through native damage handling | PASS: one staged descending collision, native queue50 and health750 to700 |
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

Validation so far: 13 staging/production-header tests and 7 malformed-input
subtests; 18 existing direct/emitter/motion tests and 4 subtests. Tests cover
exact identities, wrong-species lookalikes, deterministic ordering, malformed
UIDs, duplicate bindings, opt-out and legacy parsing. These do not prove combat.

Fresh guarded runtime must establish the direct hit, nearby quake, duplicate
suppression, repeated throws/recovery, damage/death during stun and unsupported
controls. Scripted actor/captain placement and throw commands must be disclosed;
physical-controller acceptance remains separate. Every artifact stays private
under output; CI compiles source only and receives no proprietary assets.

## Current validation boundary

Windows CI at native `52712fcdb115f712ed1f2e3f30c9af59e7c3715e`
passed 164/164 policy tests and built the production executable and combat
fixture. All five downloaded executable/DLL hashes were verified. A subsequent
CI build at `40f0e8846fcdfc12da86d1371994de8f4587e520` also preserves
`ninja: no work to do.` in its artifact. CI receives no game assets.

Fresh local `guard01` returned raw exit 86, captain-down true, and no combat
marker. `adult01` with fixture-only sources 1+2 failed before acquisition because
source 1 retained an adult host while its adapter requires a dwarf host.
The scoped repair selects Chappy type 3 only for source 1 with Purple enabled;
protected spawns and the general/Purple-disabled host policy stay unchanged.
Source 1 is not currently admitted to generated seeds; this fixture does not
change admission. Source 2 is admitted.

Fresh source-2-only `adult02` booted and passed native Violet conversion and
plucking with the 20-Pikmin baseline. It then failed the untouched-health
precondition before any combat throw. Investigation found the adult health
registry binds PelletView pointers while its getter looks up BTeki pointers;
this needs independent repair/verification. Neither run is combat acceptance.
The Red quake fixture observes bounce, naturally selected Fit, a repeated quake
with retained timer and timed recovery. Quake, crush, and death while stunned
still require passing local runtime evidence. New Red paths must remain gated
if those checks cannot be completed; adult evidence cannot qualify Red.

Fresh adult03 on native c4fc540fa661973682055b8cd3b7de11483e0992 passed the
external production-log checker: native/family maximum750, regeneration0,
exact UID/source direct queue0 to50, one collision wave, health750 to700.
Guard02 passed expected negative exit86. This is staged descending-contact
acceptance, not physical controls or a full unstaged throw. Windows CI passed
164/164 tests and recorded no-work. Fixture SHA256:
346a24ff8b0c913bc3071a9199a2667aaf5eb740363c46af82c35c9a941a6379.

Both adult health accessors are repaired in native848f456bd. Actual production
accessor bodies pass bind, unregistered control, and forget tests; independently
restoring either old lookup fails. Live adult03 baseline confirms the fix.

Quake01 failed its unchanged airborne oracle: accepted wave velocity was cleared
by generic stopMove during state16 entry, so Fit began without physical bounce.
Native41eddb04f removes only that state's stopMove; receiver horizontal stopping
and landing/Fit stopping remain. Compiled actual state-factory/start-loop test
passes and rejects the old factory. Fresh bounce/repeated-Fit/recovery and
stunned-crush proof remain pending. Current focused tests:31 passed plus11
subtests, including the scoped root engine snapshot. No Red admission change or
runtime qualification follows from the source fix alone.
