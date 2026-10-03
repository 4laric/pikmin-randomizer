# Sprays, nectar and berries (#142)

Implementation owner: Codex through shared GitHub account `4laric`.
This track remains outside Pikipelago v0.1. Issue #142 stays open.

## Current concrete slice

Native branch `codex/p2-sprays-142` implements captain Walk-state D-pad Up
ultra-spicy use. It consumes one spray from the original campaign's single
`p2originalresource::ResourceState`, then visits the captain's actual CPlate
formation. Normal, living Pikmin enter a separate spicy reaction state with
a random 0–0.3 second delay. The verified retail GROWUP1 action key starts the
effect; no nectar or maturity credit occurs. Existing affected Pikmin refresh
their duration without stacking stats. An empty formation still spends a spray,
matching source Navi use. Zero stock and an uninstalled inventory refuse use.

The effect provides 40 seconds of active gameplay, absolute 10 attack damage,
absolute 190 run speed, and twice the animation rate. Purple and White receive
the same spicy overrides. Expiry restores normal species/maturity/stat rules.
Pikmin initialization clears the transient effect; pauses, movies and UI overlays
freeze its clock. Production does not create or initialize stocks for this slice.

Source values were read from the user's private US GPVE01 revision 0 disc:

| Member | SHA-256 | Values |
|---|---|---|
| `user/Abe/piki/pikiParms.txt` | `f22ae88fade54bf8f142ecc5aae4ce0c82078e6aed448d029f16b75e5a3d7996` | P007=40, P008=10, P009=190 |
| `user/Kando/aiConstants.txt` | `0bf964d8d4c975ef021d83180a3c81e6264c9bdd18d75035af4a48995a5a41a5` | dopecount=10 |

Reference behavior: `Navi::applyDopes`, `InteractDope::actPiki`,
`PikiDopeState`, `Piki::getSpeed/getAttackDamage/doAnimation` and
`FakePiki::doAnimation` in the local read-only P2 research checkout.
The #1252 SourceBank validates the staged receiver table and its hashes.
GROWUP1 has 35 source frames and action key 2 at frame 14; its shared
ReceiverClock uses strict key.frame < int(timer), and END1000 returns to Normal.
Inherited P1 character keys do not drive this mechanic; the character motion is
presentation only. Native Pani animation rate applies after fixed-speed selection.

## Composition boundary

Resource #1252 owns physical ItemHoney/Egg/Honeywisp actors, authored drinking
receivers and nectar maturity. Its ResourceState owns stock counts, berry
remainders, made flags, actual use counters and source-child/captain completion
records. This lane consumes those services and does not duplicate factories.
Save #1229 owns authoritative fresh-campaign installation and atomic campaign
checkpoint restore, including the physical source/drop graph.

After the actual resources and authoritative campaign state are installed,
startup calls `pc_p2_sprays_bind(&resourceState, &resources.receiverClips[1], error)`
using Resources from the verified Honey SourceBank. It calls
`pc_p2_sprays_bind(nullptr, nullptr, error)` before that object is destroyed. An isolated
ResourceSnapshot codec roundtrip does not establish gameplay save/resume.
Per-Pikmin remaining spicy duration has a validated atomic `restore(float)`
method (finite 0–40 seconds), but is not yet carried by the campaign codec.
Saving during the pending Dope reaction must wait for its source END or serialize
the entire pending clock; a remaining-duration scalar alone cannot restore it.

## Verification and gameplay script

The compiled `pc_p2_spicy_policy_test` covers source key/END boundaries, expiry, pause,
invalid/negative delta, refresh, recovery, zero/uninstalled stock, ten-berry
production and actual use counting. Local MinGW checks pass. Four edited
production translation units, the Honey bank/backend and the replacement-main fixture pass syntax
checks using the engine's forced `pc_types.h` and permissive legacy flags.

`tools/p2_spicy_runtime.cpp` is a guarded engine regression. It requires a fresh
20-Pikmin room and verifies a 960×540 centered window. It injects two stocks and
Up input, observes actual reaction callbacks, unchanged maturity, speed/damage,
pause freeze, refresh, zero-stock refusal and full 40-second recovery. The
captain remains unprotected. `--guard-negative` must exit 86 before window boot;
runtime must be supervised for at most 90 seconds and preserve its logs.
Injected stock/input cannot qualify the following ordinary gameplay script.

Once the Honey provider and original campaign binding are composed, run this
60–90 second smoke in a fresh private 20-Pikmin/960×540 room:

1. Walk a captain to an actual spicy drop from the resource provider. Complete
   the normal drink animation; verify one stock credit at the receiver's END.
2. Whistle nearby Pikmin into formation, leave one working away from the squad,
   and press D-pad Up once. Verify one stock debit/use credit, visible reaction
   and faster movement/attacks in the squad; the outside worker is unaffected.
3. Pause for five seconds, resume and observe the effect until 40 active seconds
   have elapsed. Verify recovery and unchanged leaf/bud/flower maturity.
4. Press Up with no stock: verify no effect or use credit. Drink actual nectar
   with a leaf Pikmin and observe its authored grow-up/maturity event separately.
5. For save qualification, acquire another actual spray, save through the
   campaign checkpoint owner, exit the process and relaunch the same private
   campaign. Verify stock/use counts and no duplicate drop completion credit.

Current ordinary pickup/use, fresh-process persistence and campaign transitions
are **UNTESTED**. Actual berry harvest/carry-to-ship production, bitter spray
enemy receivers/immunity/petrification/recovery, source effect visuals, and
transient spicy-duration save/resume remain open. A build or policy PASS does
not clear those gates.

## Bitter Stone implementation boundary

The first bounded original enemy receiver is Armor (source ID 15), coordinated
with its family owner. Existing `TEKIOPT_Pressed`/`set_bittered` hooks do not
implement source Stone. Source `dopeCallBack` may queue under NoInterrupt and
returns false even when the effect was accepted; its return value cannot serve
as the admission result. Entry backs up enemy events, stops the authored motion
and velocity, and invokes the family-specific Stone callback. Recovery restores
the event backup and resumes the same family state rather than resetting its FSM.

The private GPVE01 `enemy/parm/enemyParms.szs` member `armor/enemyparm.txt`
(SHA-256 `3fb448374d10a483a8fb3422d16349bacc9fcec33121006863a8694b35f2a57c`)
sets fp35 to 1.0 second. This is the threshold for starting source shake,
not the total petrification duration. `armor/enemystoneinfo.txt` defines 17
authored stone pieces; source draw clocks stagger their start and proceed through
five shake phases with strict time comparisons. Recovery requires the actual
viewed-demo, Shake and Break flags as well as a living enemy. An immediate
one-second timeout cannot qualify this mechanic.

Stone death bypasses the ordinary `becomePellet` path. Source `EnemyBase::kill`
calls Stone `dead`, `deathProcedure` (including carried-cargo throw-up), authored
Honey drops and `becomeCarcass`; that last function removes the enemy through
its manager. The normal carryable body must therefore be suppressed before
host corpse activation. Armor is BDT_Strong: one Honey roll chooses nectar below
0.9, spicy below 0.95, otherwise bitter. Corpse #1261 owns the typed activation
suppression API, while resource #1252 owns actual Honey factories and child
identity. Stone cannot create a second normal corpse or an independent drop store.

This source audit is preparation only. Original Stone admission, source stone
geometry, per-piece clocks, actual shatter/drop and save/resume remain unimplemented
and unqualified in the spicy candidate.
