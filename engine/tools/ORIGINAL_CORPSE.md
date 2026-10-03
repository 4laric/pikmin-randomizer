Original source corpse pipeline (#1261)
======================================

Providers supply `pc_p2_original_corpse_resources(unsigned,std::string&)` from
`pc_p2_original_corpse_native.h` to Cannon's CorpseResources callback, or call
it during their own resource preflight. This checks an audited literal profile,
native manager and slot capacity. Each provider must also admit its genuine
dead body/animation bank. Null retail archive/bmd means an actor-backed view.

GPVE01 revision0 `user/Abe/Pellet/us/carcass_config.txt` member SHA256:
`a76c476352cb0d7386a8ab448f0e35285cc8668f43f2b9189cfdd87b03de9de0`.
Source names, zero-based indices, carrier min/max, seed yield and dimensions are
literal facts. Source26=5/10/5;33=10/20/12;34=5/10/15;95/96=7/15/8.
The independent audit examined research632af937 and all51 catalog rows;
50 enemy profiles and49 explicit no-corpse policies are represented. Unclassified
sources39/64/100 remain refused. Source55 has no corpse. Poko fields are never
used for Onion seeds. Held treasure841 is a separate #1232 resource.

Explicit original registry identity selects a private config BEFORE native
pellet initialization. Ordinary P1/AP/preview actors retain their existing path.
Actual dead actors remain PelletViews until native pellet teardown. Source slots,
centered terrain contacts and single-sphere collision use source dimensions;
Frog has its source collision offset. This uses the port's native dynamic solver;
the retained inertiaScaling literal is not a port of the retail rigid solver.

Only completed ordinary Onion suction consumes the independent corpse receipt.
It retains catalog fingerprint/generator UID/ordinal/respawn epoch/activation
after actor retirement and suppresses P1 bestiary/preview economy credit.
Duplicate callback grants zero. Native birth/resource readiness grants nothing.

For the actual retail Stone death boundary, the family producer calls
`pc_p2_original_corpse_set_death_cause(actor, p2original::CorpseDeathCause::StoneShatter, error)`
BEFORE `pcEscapeNow`/`dieSoon`. The header is
`pc_port/pc_p2_original_corpse_native.h`. This one-way policy is keyed by full
catalog/UID/ordinal/epoch/activation, refuses nonoriginal/invalid activations,
unknown causes and a body already born, and prevents direct normal corpse birth.
Duplicate selection is harmless; a new epoch/activation retains ordinary policy.
The bounded policy persists on ordinary course unload/reentry and clears only
on an explicit new session. It grants/consumes no corpse reward. The producer
still owns proof of real Stone state, authored cargo throwup and Honey children.
The policy is not physical-death SAVE state; no Stone gameplay claim is made by
the pure policy tests or native object compilation.

At an explicit NEW session, startup calls
`pc_p2_original_corpse_new_session(catalog,error)` after previous bodies retire.
Do not reset it on ordinary course reentry. Providers must kill owned corpse
pellets before their actor; the real PelletView kill retires that actor.
Before source actors/providers are released or the App heap is reset, call
`pc_p2_original_corpse_unload(error)`. It refuses any still-bound native corpse
physical graph, including a consumed body awaiting teardown. Successful unload
preserves the receipt ledger and persistent literal configs for course reentry.

`CorpseSnapshot` and its bounded schema1 codec contain address-free receipt
state. SAVE must authenticate that payload together with Onion stock. These
records do NOT serialize physical corpse/held/carry graphs. Full corpse cache
and fresh-process restore remain unsupported until the SAVE owner implements
and tests physical preflight/create/import and an atomic stock transaction.

Focused ledger tests prove state/codec invariants only. Native object compilation
does not establish physical death, pickup, carry, suction or population.

Short human gameplay script (fresh20-Pikmin/960x540 centered fixture):
1. Defeat the admitted source actor through ordinary Pikmin attacks; wait for
   its authored death END. Confirm one body and the original UID in the log.
2. For Dumple/Snagret use4 carriers first (insufficient), then5; Cannon use6
   then7; FireChappy use9 then10. Confirm physical pickup and free slot counts.
3. Carry to the actual RGB Onion. Record live/sprout/stored population before
   and after: respectively5/15/8/12 new Pikmin. Confirm corpse/actor removal.
4. For source33 confirm held841 remains separate and its ship delivery grants
   only its own treasure receipt. For source55 confirm no body exists.
5. Repeat after ordinary course reentry. Do not claim SAVE acceptance until an
   actual checkpoint and fresh-process graph restore are supported and tested.
