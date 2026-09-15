# Mamuta behavior record — non-lethal profile, Piklopedia rules, P1 differences

Companion to [PIKMIN2_MAMUTA_AUDIT.md](PIKMIN2_MAMUTA_AUDIT.md) (issue #214,
parent #168). All anchors are `native/pikmin2-research` (P2) and `engine/`
(P1 snapshot) source reads; no native behavior was changed.

## Non-lethal profile vs. standard combat enemies

Mamuta's defining difference: its attack never kills Pikmin.

- The attack interaction is `InteractBury`, not `InteractAttack`/`InteractKill`.
  Pikmin receive damage **0.0** (`miulinState.cpp:292`) and captains 5.0
  (`miulinState.cpp:312`) — versus ordinary combat enemies whose attack event
  delivers `mAttackDamage` through a kill-capable interaction.
- The Pikmin outcome is conversion, not loss: a same-kind **Flower-stage**
  sprout is planted at the floor and the original is removed with
  `CKILL_DontCountAsDeath` (`interactPiki.cpp:377-442`), so the kill counter
  and Pikmin-lost statistics do not register a death.
- Conversion is bounded: rejected outright for invincible-state Pikmin and
  once `GameStat::mePikis >= 99` (US; PAL subtracts zikatu), and falls back to
  a Walk state on bald terrain, missing sprout manager, or failed sprout
  birth (`interactPiki.cpp:379-442`).
- Residual hazard is the flick collateral of the same animation event:
  nearby/stuck Pikmin and captains are flicked with retail shake damage 1.0,
  knockback 40, range 40 (`miulinState.cpp:317-326`; retail general params in
  `output/mamuta-first/imported/mamuta.json`). The dedicated Flick state
  applies the same shake (`miulinState.cpp:486-514`).
- Consistent with this, the registry still classes Mamuta `BDT_Strong`
  (`enemyInfo.cpp:88`) for battle-music intensity, and its lifegauge (500 HP,
  fp00) is shown once it leaves Wait (`miulinState.cpp:59-77`) — it is a
  durable, aggressive non-killer, not a passive creature.
- Net effect on population: planting *upgrades* leaf/bud Pikmin to flowers at
  the cost of temporarily removing them from the squad, until the 99-planted
  cap or terrain rules stop it.

## Piklopedia discovery rules

- `Zukan_Miulin` ↔ `EnemyID_Miulin` (`zukan2D.cpp:179`).
- Miulin sits in the "hides just pikmin lost" display group: the lost counter
  is blinded (`mPikiLostCounter->setBlind(true)`, `zukan2D.cpp:2173-2183`),
  matching its non-lethal profile. Value and defeated counters are still
  shown.
- It does not carry `EFlag_HasNoInfo` (`enemyInfo.cpp:88` vs flag definition
  `enemyInfo.h:40`), so creatures-defeated and Piklopedia-entry tracking are
  active; day-end map clearing would not credit kills anyway because Miulin
  lacks `EFlag_CanAppearDayEnd` and is outside the
  `prepareDayendEnemies` clear list (`generalEnemyMgr.cpp:923-941`).

## Pikmin 1 foundation differences (engine/ snapshot)

The P1 Mamuta (`TEKI_Miurin = 24`, `engine/include/teki.h:105`; strategy in
`engine/src/plugPikiYamashita/TAImiurin.cpp`, params in
`engine/include/TAI/Miurin.h`) is the same species with materially different
mechanics:

| Aspect | Pikmin 1 (TAImiurin) | Pikmin 2 (Miulin) |
|---|---|---|
| Attack payload | `InteractBury(&teki, true, 10.0f)` on Pikmin, `20.0f` on Navi (`TAImiurin.cpp:559-574`) | `InteractBury(enemy, 0.0f)` Pikmin, `5.0f` Navi (`miulinState.cpp:292,312`) |
| P1 bury receiver | Sets `mHappa = Flower` in place (makeFlower=true) and transits to `PIKISTATE_Bury`; no sprout item, no cap, no kill of the original (`engine/src/plugPikiKando/interactBattle.cpp:73-90`) | — |
| P2 bury receiver | — | Births a Flower-stage `ItemPikihead` sprout, kills the original with `CKILL_DontCountAsDeath`, capped at 99 planted, terrain/manager dependent (`interactPiki.cpp:377-442`) |
| Aggression | Relax/angry cycle: watches Navi (`TAIAwatchNaviMiurin`), Angry state with own rotation speed, Groggy state, and *satisfaction* — it calms when ≥ 10 flower Pikmin exist (`TAImiurin.cpp:202-230, 772-779`) | Alert/caution timer (2 s retail) widens search to 180°; no satisfaction or groggy cycle (`miulin.cpp:1027-1049`) |
| FSM | 24-state TAI action tree (`Miurin.h:30-57`) | 8-state FSM (`Miulin.h:20-31`) |
| Companion spawns | none in strategy | five ShijimiChou at +80 on birth (`miulin.cpp:27-43`) |

Porting implications: the P1 engine snapshot has a full Mamuta implementation
whose bury receiver semantics (in-place flowering, no cap) differ from P2's
itemized sprout conversion. A P1-proxy lane must decide explicitly which
planting contract to honor; the randomizer's bestiary/discovery rules already
treat corpse-less/non-lethal species specially (README "Expanded bestiary":
Mamuta pays by body delivery, not defeat).

## Open items

- Native runtime acceptance: burial at terrain/cap/invincible/missing-sprout
  boundaries, carcass return route, day/floor reset, save-load, and
  Piklopedia entry behavior (carried forward from #168's acceptance list).
- Cave generator serialization/restore for Miulin untraced.
- ShijimiChou side-birth persistence untraced.
