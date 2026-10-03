# Groink living recovery (#1007)

The original P2 `LivingState::update` invokes `EnemyBase::lifeRecover` before
`injure`, whenever the actor is living and its health is positive. The rate is
max health times general `fp31` per update, with a full-health clamp. It is not
multiplied by delta time, delayed by caution, or cancelled by incoming damage.
Source: read-only pikmin2-research 632af93787b9c95b63f0c13be32b161375ce3a96,
`src/plugProjectYamashitaU/enemyBase.cpp` 516-518 and 2416-2422.

Private extracted retail parameters: both variants have fp31=0.000010. Source
78 max health is 1200 (0.36 HP per second at 30 Hz); source 97 max health is 700
(0.21 HP per second). Parameter file SHA-256:

- MiniHoudai: 676326296563c8c544f38902457bdc890a7f29d7e49b9fa52f54a27a00b4e1e0
- FminiHoudai: bc07dda92384631964d28591e1854041d106d0330788cd04e89b3eb4e0900008

The parser now reads/validates fp31; the campaign host applies recovery before
stored injury once per source-clock tick. Pending injury waits for that tick,
so presentation frames cannot suppress recovery-before-injury ordering. A
zero-health actor, Dead FSM state, dead host, or pellet owner cannot recover.
Missing fp31 keeps the previous zero-recovery preview behavior. This intentionally
differs from the original constructor's .01 default to avoid silently introducing
1000 times the retail rate into an unstaged or invalid-file fallback.

`p2_groink_fsm_test` covers retail rate parsing, invalid rates without mutation,
positive/full/zero/negative health, dead/carcass exclusion, recovery before injury,
and identical 30-update recovery at 60 and 120 presentation frames per second.
The existing carcass tests remain separate: living recovery does not fix campaign
corpse revival, which still emits `P2_GROINK_CARCASS_REVIVE_SKIPPED`.

## Short natural encounter acceptance (manual, pending)

Use the current private production candidate and a fresh Groink arena staged by
the current root overlay with 20 Pikmin, 960x540 centred startup, and unprotected
captain. Preserve original saves. Confirm `P2_GROINK_PARMS` reports retail=1 and
regeneration=0.00001000 for the encountered variant.

1. Let the Groink aim/fire naturally and dodge normally. Throw Pikmin onto its
   back to remove some HP, then whistle them away and retreat outside attack
   reach. Do not inject damage, health, death state, or synthetic fire events.
2. Leave the game active for 30 seconds. Compare `P2_GROINK_FSM_POS` health
   before/after: source78 should recover about 10.8 HP, source97 about 6.3 HP,
   bounded by max HP (floating-point/clock rounding may slightly differ).
3. Pause for 10 seconds; confirm health does not progress during pause. Resume,
   repeat damage, and verify combat remains possible and eventually kills it.
4. Confirm natural death creates its normal carriable corpse/drop. Carry it to
   the Pod/Onion normally; do not interpret the living recovery fix as evidence
   that corpse revival works. Existing skipped-revival marker is still a known
   full-campaign limitation.

This procedure is supplied for player acceptance; compiled tests and builds do
not establish natural attack, death, carry delivery, or full-campaign acceptance.
