# Baby31 captain-attack receiver - runtime handoff (#400)

Slice: shard-enemies-3-baby31-captain-receiver (parent #256, umbrella #172).
Owner: Codex via shared 4laric. Keep #400 OPEN; no ADMIT.

## Claim

P2_QUEEN_LARVA_ATTACK observed with captain health 100.0 -> 98.0
(drop = 2.0) through the engine InteractAttack::actNavi path. No raw
mHealth mutation anywhere in the slice (fixture samples read-only; the
bite is applied by the engine attack object). Existing Queen behavior
(host bind, combat damage, flick, rolling, press, crash, Born) stayed green
in the same run.

## Source contract (docs/PIKMIN2_BULBLAX_BOSS_AUDIT.md)

Baby Attack state 4, key 2 hits captains with mAttackDamage = 2
(pc_p2_queen_policy.h:102); kamu joint radius 20, sight 800 / angle 180,
attack range 30 / angle 45. Ingestion/swallow/poison are deferred and
untested here. The actor is the family-owned Queen sampled actor, not a
real Baby Teki.

## Changes (private branches only)

Native branch codex/shard-enemies-3-baby31-receiver-native at
2a5106585bbccef6dc74eb8574daef06a3c4a528:

- pc_port/pc_p2_queen cpp/h (+ teki, policies): cherry-picked verbatim
  from reviewed wave-native 6a87eb29 (Queen-family owner bytes). Includes
  the fail-closed p2-queen-inject.txt sidecar: without the file it is fully
  inactive; with P2_QUEEN_INJECT_1 <tick> it places one already-active
  larva at the captain mouth and forces Baby Attack 4. The Attack FSM
  frames, key-2 event, InteractAttack(2) and actNavi are unmodified code.
- tools/p2_queen_larva_receiver_fixture.cpp (new): complete RoomApp.
  Parks the captain at (-104, 1790) - beside the squad spawn, ~174u from
  the Queen - so the 64-Pikmin escort never latches her and her
  Wait->Born schedule runs undisturbed. Captain guard #632 runs FIRST
  every tick (orima/dead/hp<=1 -> P2_FIXTURE_CAPTAIN_DOWN, exit 86).
  Never writes health. PASS exits 0 on observed drop >= 2.
- pc_port/pc_p2_preview.cpp + CMakeLists.txt (+ pc_p2_actor_slots.h,
  pc_p2_material_srt.h, pc_p2_specular_layer.*): hook/registration
  for the cherry-picked module only.

Root branch: this doc only. No shared checkouts touched.

## Arena recipe (private run dir, reproducible)

- Base default.gen bytes: lane-24 proven 70-record gen (Queen host
  generator 230010 type 3 Chappy at 34, 30, 1896) + canonical 64-red
  squad overlay.
- p2-queen-actor.txt: lane-24 11-row clip profile replicated verbatim
  (Queen dead/sleep/wait1/damage/flick/rolling_l/rolling_r/born + Baby
  born/move/dead) + placement row 230010 default 1 34 30 1896 0
  (co-located with host).
- p2-queen-teki.txt: P2_QUEEN_TEKI_1 1 230010 3.
- p2-queen-inject.txt: P2_QUEEN_INJECT_1 300 (test accelerator;
  labeled, see Limitations).
- Bank: 54 Queen + 36 Baby .mod (incl. Baby attack/attackfail) +
  treasure.mod, pod.mod; pikmin_settings.conf tutorials off.

## Build evidence

- Leased configure+build, canonical scripts/build_pikmin2_fixture.py:
  output/baby31-fixture2/provenance.json -> status: built, error: None,
  native_head: 2a51065, clean tree.
- output/baby31-fixture2/fixture.exe SHA-256:
  4903c00b05c6d485172acf6c1356d6583d8267798f1a0e2a950e9a6aeecf531f.
- Full-tree ninja -n after leased completion: ninja: no work to do.

## Run evidence (run2, exit 0 in 31 s)

output/workflow/autofill/planning-shards/enemies-3/prepared/
baby31-captain-receiver/out/run2/native.log (+ capture.json:
exit_code 0, same exe SHA):

- L7: 960x540 centred window; L895: P2_MUSE_LARVA_READY squad=64
  captain_health=100.0.
- L888-889: teki host bound + AI suppressed (Queen gate).
- L897/921: combat damage (stuck=32) + flick (Queen gate).
- L1042+: rolling passes ending near_home=1, press/crash markers
  (Queen gate).
- L1491: P2_QUEEN_STATE from=2 to=6 (Wait->Born, natural, larvaDue).
- L1493: P2_QUEEN_LARVA born=1 (natural birth).
- L1494: P2_QUEEN_INJECT_LARVA tick=863 state=4 fixture=1 (hook).
- L1497: P2_QUEEN_LARVA_ATTACK damage=2 captain_before=100.0
  captain_health=98.0.
- L1498: P2_MUSE_LARVA_RECEIPT drop=2.0; L1519-1520 SESSION +
  PASS P2_MUSE_LARVA attack+bite.
- No P2_FIXTURE_CAPTAIN_DOWN (captain never down; guard armed,
  untriggered). End-of-run squad 11/64 (natural Queen press attrition,
  not fixture writes).

A first run (run1, captain parked at the Queen feet) is kept as a
negative-shape record: the escort latched her (stuck=32 -> Damage/Flick/
Rolling loop), no larva was born in ~8900 ticks, health stayed 100.0,
honest timeout - this motivated the away-park + inject design.

## Gate verdicts (only evidenced gates PASS)

- Baby31 attack (bite, damage 2 via actNavi): PASS (L1497 + receipt).
- Baby31 birth/identity (larva born active): PASS (L1493).
- Baby31 move/seek, dead, cleanup: UNTESTED (larva was delivered,
  never walked; pool/death paths not exercised).
- Ingestion/swallow/poison: UNTESTED (deferred per contract).
- Transport: N/A (larvae are not transported).
- Queen regression (host/combat/flick/roll/press/Born): PASS (same log).
- Captain guard #632: adopted (first-every-tick, exit-86 armed);
  negative captain-down test BLOCKED - no natural captain-death
  mechanism exists in this arena and health writes are banned, so the
  exit-86 path is code-reviewed but unexercised.

## Limitations / remaining blockers

- The bite used the family-reviewed inject sidecar for positioning;
  natural 400u larva trekking is unproven. Do not cite this run for
  natural Baby31 admission.
- No Baby attack clip row in the profile (attack pose falls back, mesh
  not drawn during the bite - logic unaffected).
- Single run (n=1); no death/cleanup/pool-exhaustion coverage.
- Shared captain-damage semantics route to #186 / Queen owner; generic
  providers to #570.
