# Hana (Creeping Chrysanthemum, EnemyID 84) buried/no-atari + fp02 poison + attackNavi

Issue #407 / #165 residual slice. Source: `src/plugProjectNishimuraU/Hana.cpp`,
`src/plugProjectYamashitaU/chappyState.cpp` and
`src/plugProjectYamashitaU/enemyAction.cpp` at research revision
`632af93787b9c95b63f0c13be32b161375ce3a96` (`native/pikmin2-research`).

## Source rule (retail)

`Hana::setUnderGround` (Hana.cpp:169-180) runs in `StateSleep::init` and:

```cpp
flickStickPikmin(...);
mBuried = true;
enableEvent(0, EB_BitterImmune);
hardConstraintOn();
enableEvent(0, EB_Invulnerable);
setAtari(false);
```

`Hana::resetUnderGround` (Hana.cpp:155-163) runs in `StateSleep::cleanup` and
reverses all six. While buried Hana is therefore non-targetable/no-atari and
invulnerable (any attack is swallowed), and it becomes targetable/damageable on
wake. `StateSleep::init` (`chappyState.cpp:98-118`) calls `setUnderGround` and
only the `EnemyID_Hana` branch calls `hardConstraintOn`.

`StateAttack::exec` (`chappyState.cpp:1613-1656`) fires on the attack animation
key events:

* `KEYEVENT_2`: `attackNavi(enemy, mAttackRadius, mAttackHitAngle,
  mAttackDamage, ...)` then `eatAttackPikmin()`.
* `KEYEVENT_3`: `swallowPikmin(enemy, mPoisonDamage, nullptr)`.

`EnemyFunc::attackNavi` (`enemyAction.cpp:1179-1203`) damages every Navi whose
angle is inside the `mAttackHitAngle` half-cone and whose distance is below
`mAttackRadius`. `swallowPikmin` (`enemyAction.cpp:1148-1173`) kills each Pikmin
stuck to the mouth and, only when the `InteractKill` stimulate succeeds **and**
the kind is `White`, calls `EnemyBase::eatWhitePikminCallBack` with the poison
damage (`enemyBase.cpp:3293`), which `addDamage`s it to the enemy. Hana's proper
`fp02` is `2500.0` (US GPVE01 rev 0; equal to its `fp00` life).

## P1 host facts

* The P1 Chappy host has no `EB_Invulnerable`/`EB_BitterImmune`/`EB_ModelHidden`
  event flags and no state-driven atari override.
* `BTeki` does expose `TEKIOPT_Atari` and `TEKIOPT_Invincible`, and
  `BTeki::interactDefault` (`tekibteki.cpp:1820`) returns `false` for an
  invincible Teki. However `setTekiOption`/`clearTekiOption` early-return unless
  `pc_render_is_authoritative()` (`teki.h:260-287`), so the flag write is not a
  reliable headless/test gate.
* The shared attack routing points are `InteractAttack::actTeki` /
  `InteractBomb::actTeki` (`src/plugPikiNakata/tekiinteraction.cpp`).

## Port implementation

`pc_port/pc_p2_hana_residual_policy.h` (pure, `<cstdint>` only) encodes the
gate and poison matrix:

```
undergroundGate({registered, buried}):
    !registered            -> Inactive           (shared hook no-op)
    buried                 -> NoAtariInvulnerable
    otherwise              -> Inactive
noAtari / blocksDamage     == (gate == NoAtariInvulnerable)

appliesWhitePoison({killSucceeded, isWhite}) == killSucceeded && isWhite
poisonDamage(...) == appliesWhitePoison ? 2500.0f : 0.0f
```

`pc_port/pc_p2_hana.cpp` drives the FSM and:

* Tracks the buried window as `state == HANA_SLEEP` (setup starts buried;
  `gohome -> sleep` re-buries). `applyUndergroundGate` logs
  `P2_HANA_UNDERGROUND event=enter|exit no_atari=… invulnerable=…` on the
  transition and, when authoritative, mirrors the source with
  `clearTekiOption(TEKIOPT_Atari)` + `setTekiOption(TEKIOPT_Invincible)` on enter
  and the inverse on exit.
* `pc_p2_hana_buried(const BTeki*)` and `pc_p2_hana_rejects_attack(Teki*)` are
  the read-only gate queries. The reject query is wired into
  `InteractAttack::actTeki` **and** `InteractBomb::actTeki`; a buried Hana
  swallows the hit before `mStoredDamage` accumulates and logs
  `P2_HANA_UNDERGROUND_BLOCK generator=… source_id=84 buried=1`. Unregistered
  actors fall through unchanged, so every other lane is a no-op.
* At the source attack1 `KEYEVENT_2` (retail bite frame from the disc bank) it
  fires `doAttackNavi` once per attack and logs
  `P2_HANA_ATTACK_NAVI generator=… frame=… navi=… damage=10.0`; radius `fp22=80`,
  half-angle `fp23` default `15 deg` (`0.261799` rad), damage `fp24=10.0`.
* At the source `KEYEVENT_3` swallow frame it kills the captured Pikmin with
  `InteractKill` (unchanged normal death/corpse) and applies `fp02=2500` exactly
  once when the kill succeeded and the colour is `White`, logging
  `P2_HANA_POISON generator=… pikmin=1 damage=2500.0 health=…`. Failed kills and
  non-White colours apply nothing.

The non-authoritative `TEKIOPT_Atari`/`TEKIOPT_Invincible` write is a documented
limitation; the query hooks are the deterministic guard and are what the
standalone matrix and the residual harness exercise.

## Tests

```
g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port \
    tools/p2_hana_residual_policy_test.cpp -o ../p2_hana_residual_test.exe
../p2_hana_residual_test.exe   # p2_hana_residual_policy_test PASS
```

The matrix covers the buried gate (registered/unregistered x buried/surfaced,
`noAtari`/`blocksDamage`/`gateName`) and the poison gate (successful White,
failed White, successful non-White, failed non-White). Compiler:
`C:/msys64/mingw64/bin/g++.exe`.

The runtime side is `experimental/pikmin2_hana_residual_behavior.py` (same
private ground arena and Hana fixture as `pikmin2_hana_behavior.py`), whose
`validate()` checks `P2_HANA_UNDERGROUND*`, `P2_HANA_ATTACK_NAVI` and
`P2_HANA_POISON`. Live GL execution is owned by the ground-lifecycle runtime
slot and is **not** run by this slice.

## Honest limits

* The no-atari/invulnerable flag write relies on `pc_render_is_authoritative()`;
  in a non-authoritative/headless phase the host option does not change. The
  read-only `pc_p2_hana_rejects_attack` hook is authoritative in all phases.
* The source three-slot mouth swallow (`kamu1..3`) remains the documented P1
  capture + single-kill adaptation; the poison is applied exactly once per
  consumed White in that adaptation.
* `attackNavi` uses the header-default `fp23=15 deg` because the Hana disc
  general block exposes no `fp23`.
