# Species-lane residual slices 2: Blind UmiMushi, ElecBug flip/immunity, Armor receiver

Issue [#407](https://github.com/4laric/pikmin-randomizer/issues/407). Three
parallel residual-gap slices merged into the species lane branch
(`opencode/p2-species-native`). Owner: Codex via shared `4laric`.

## Blind UmiMushi (source id 101) — shared-base variant

Extends `pc_p2_umimushi` with the source Blind half-scale / fp12=800 health /
reduced-turn-rate split.

- Native: `pc_port/pc_p2_umimushi.{cpp,h}`, `pc_p2_batch3.cpp` (bind log/aliases).
- Standalone + pytest: `tests/test_pikmin2_umimushi_blind_behavior.py` (9 passed).
- Runtime PASS: `output/p2-species-blind/e9922b77777c4012ba51cb12584d7b5a` —
  `P2_UMIMUSHI_BIND generator=374006/374007 source_id=101 blind=1`,
  `P2_UMIMUSHI_BLIND scale=0.500 health=800.0 turn_rate=0.30`,
  `P2_BATCH3_BIND key=aquatic|UmiMushiBlind`, bites at frame 39 with eat; the
  ordinary UmiMushi (374004) unchanged. Log `633C5C8C…A98B6D91`; isolated exe
  `143034AC…562ADEB`.
- Visuals reuse the ordinary UmiMushi bank as an explicit stand-in
  (`umimushi-blind-standin.json`); no provenance fabricated.

## ElecBug press-to-flip + electrical immunity (#165)

Extends `pc_p2_elecbug` so the press/flip and immunity matrix are observable.

- Native: `pc_port/pc_p2_elecbug.{cpp,h}` (discharging-beetle press shock,
  Yellow-exclusion marker, `ATTACK_BLOCKED`/`ATTACK_ACCEPTED`, read-only
  `pc_p2_elecbug_state_name` probe).
- Instrumented fixture: `output/p2-species-elecbug-immunity-fixture/fixture.exe`
  (`27FD05E4…EF4E018`); the room fixture was fixed to honor the mandated
  `PIKMIN_P2_ROOM_WINDOW` 960×540 centred baseline
  (`tools/preview_p2_room.cpp`, native `87ac3ab3`).
- Runtime PASS: `output/p2-species-elecbug-immunity-final/5dc6283e94b443848959fe2f5755c45e`
  — checks `window`, `flip_path` (FLIP → `state=reverse`), `immunity_matrix`
  (Yellow immune, non-Yellow shocked), `attack_blocked` (invulnerable until
  flipped), `attack_reversed`, `attack_path`, no extinction; `exit_code 0`.
  Log `37716CAB…BBED791`. NOTE: `RECOVER` is not observed because the fixture
  exits at the attack path; it is unit-covered.

## Armor `dmg1` / bittered receiver + stone flick (#165)

- Native: `pc_port/pc_p2_armor_receiver_policy.h` (pure accept/reject policy),
  `pc_p2_armor.{cpp,h}`, `src/plugPikiNakata/tekiinteraction.cpp`
  (`InteractAttack`/`InteractBomb` hooks).
- Source rule: accept only when `EB_Bittered` or collision part id `dmg1`;
  reject otherwise. **The P1 host does not expose a real `dmg1` part** (Armor
  collision comes from the P1 Chappy model), so a documented port approximation
  registers the actor's bounding-sphere part as the single weakpoint
  (`P2_ARMOR_RECEIVER_PART … dmg1=absent mode=port_bounding_sphere`); a null part
  is always rejected. `doStartStoneState` mouth flick is wired to the
  `TEKIOPT_Pressed` host analogue.
- Standalone policy test PASS; pytest 7 passed.
- Runtime: `output/p2-species-armorrecv-run/391fe50162a447ac889be4276634b387`
  — setup contract PASS (`receiver_part`, `stone_contract`), but the accept/reject
  matrix is **UNMEASURED** because no Pikmin attacks Armor unattended. Log
  `508D92B6…0D61D63E`; combined exe `1FD48E4A…08345A1C`.

## Remaining

- Live Pikmin-attack / press-driving fixtures for the receiver matrices (the
  unattended arena cannot attack), death/corpse/cleanup (#397), and the
  documented per-species fidelity gaps.
