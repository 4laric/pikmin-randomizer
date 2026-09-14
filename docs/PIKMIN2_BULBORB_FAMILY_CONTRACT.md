# Lane 13 — Bulborbs, dwarfs and Sheargrubs: source audit and behavior contract

Fan-out: [`docs/PIKMIN2_IMPLEMENTATION_FANOUT.md`](PIKMIN2_IMPLEMENTATION_FANOUT.md)
lane 13 (`#120`/`#197`). Parent `#186`; first bounded deliverable is the
required *source ID / variant difference* audit followed by the special Bulbear
and Fiery Bulblax rules.

Implementation owner: Codex via shared account `4laric`. Executing
agent/session: opencode (deepseek-v4.1-flash). Root branch
`opencode/p2-lane13-15`, base `codex/p2-main-review` `e514e6d`.

Machine-readable form: `experimental/pikmin2_bulborb_family.py`
(schema `p2-bulborb-family-v1`), tests
`tests/test_pikmin2_bulborb_family.py` (17 passed). Source of truth is the
read-only decomp checkout `native/pikmin2-research` (`Game/enemyInfo.h`,
`Game/Entities/{ChappyBase,KochappyBase,FireChappy,KumaChappy,KumaKochappy,Ujia,Ujib}.h`,
`Game/ChappyRelation.h`).

## 1. Identity audit (source IDs and variant differences)

| ID | Internal | English | Base | Branch | Status | Native marker |
|---|---|---|---|---|---|---|
| 1 | `Kochappy` | Dwarf Red Bulborb | KochappyBase | dwarf | implemented | `P2_KOCHAPPY_*` |
| 2 | `Chappy` | Red Bulborb | ChappyBase | adult | missing | `P2_CHAPPY_*` |
| 12 | `Ujia` | Female Sheargrub | EnemyBase | sheargrub | implemented | `P2_SHEARGRUB_*` |
| 13 | `Ujib` | Male Sheargrub | EnemyBase | sheargrub | implemented | `P2_SHEARGRUB_*` |
| 33 | `FireChappy` | Fiery Bulblax | ChappyBase | adult | missing | `P2_FIRECHAPPY_*` |
| 35 | `KumaChappy` | Spotty Bulbear | KumaChappy | adult | missing | `P2_KUMACHAPPY_*` |
| 42 | `BlueChappy` | Orange Bulborb | ChappyBase | adult | missing | `P2_BLUECHAPPY_*` |
| 43 | `YellowChappy` | Hairy Bulborb | ChappyBase | adult | missing | `P2_YELLOWCHAPPY_*` |
| 44 | `BlueKochappy` | Dwarf Orange Bulborb | KochappyBase | dwarf | staged | `P2_BLUEKOCHAPPY_*` |
| 45 | `YellowKochappy` | Snow Bulborb | KochappyBase | dwarf | implemented | `P2_SNOW_*` |
| 76 | `KumaKochappy` | Dwarf Bulbear | KumaChappy | dwarf | staged | `P2_KUMAKOCHAPPY_*` |

Out of lane 13: `Baby`/`Queen`/`KingChappy` (lane 24), `LeafChappy`/Bulbmin
(lane 11), `Tobi`/Shearwig (separate identity).

Structural variant differences (`variant_differences()`, all source-backed):

- **adult vs dwarf.** Adult `ChappyBase` has `Sleep`, `turnToHome`/`goHome` and
  no `Press`; dwarf `KochappyBase` has `Wait`, `Demo` and `Press`, and no
  `Sleep`. Adults take `damageCallBack`/`setUnderGround`; dwarfs take
  `pressCallBack` (flip) and `hipdropCallBack`.
- **elemental.** Only `FireChappy` owns a fire body state, water extinguish and
  an `InteractFire` touch receiver.
- **revival.** Only `KumaChappy` carries a reviving carcass and gauge-rebirth
  timers (`fp11=30`, `fp12=10`).
- **relation.** `KumaChappy` owns a `ChappyRelation` list; `KumaKochappy` is the
  relation consumer and walks `WalkPath` to the parent.
- **sex.** `Ujia` has no mouth slots and no Pikmin-damaging attack (bridge
  damage `fp01=25` only); `Ujib` has `mMouthSlots`, `attack1`/`attack2`/`eat`
  and white poison `fp01=300`.
- **mimicry.** Dwarf variants reuse an adult model/anim bank; identity differs
  by change texture and, for `KumaKochappy`, the parent relation.

## 2. Special Fiery Bulblax rules (`FireChappy`)

Source: `FireChappy.cpp` / `FireChappy.h`.

- `startFireState`/`updateFireState`: `mOnFire` defaults true; the material
  animation timer resets to 30 on (re)ignite.
- **Water extinguish:** while on fire and `mWaterBox` is set, the body effect is
  finished, a dead-steam effect plays and the fire-end sound starts; the enemy
  re-ignites only while alive and out of water.
- **Fire touch receiver:** `collisionCallback` stimulates `InteractFire` on a
  living Pikmin/Navi with `mGeneral.mAttackDamage`. The receiver/immunity
  semantics belong to lane 10.
- `onKill` calls `finishFireState(false)` → dead smoke (water gives dead steam).
- Material animation loops `yakichappy.btk` + `.brk`; effects are `TYakiBody`,
  `TYakiFlick`, `TYakiDeadsmoke`, `TYakiSteam`, `THanachoY`.

## 3. Special Spotty Bulbear rules (`KumaChappy`)

Source: `KumaChappy.h`, `KumaKochappyState.cpp`, `Game/ChappyRelation.h`.

- **Revival:** death leaves a reviving carcass (`doUpdateCarcass` /
  `doBecomeCarcass`), then `StateRebirth` after the health-gauge timer
  (`fp11=30`) and respawn rate (`fp12=10`). This must be reported separately from
  ordinary death (fan-out: "report revival ... separately").
- **Waypoint patrol:** `setNearestWayPoint`/`setLinkWayPoint` over
  `mCurrWP`/`mPrevWP`; requires a staged route asset. `WalkPath`/`TurnPath`/
  `Lost` are distinct states.
- **Relation:** `createChappyRelation`/`getChappyRelation` own the
  `ChappyRelation` list consumed by Dwarf Bulbears. Parent loss must release the
  dwarf to its home-return path.

## 4. Six-gate status (source-backed; no new runtime claim)

| Identity | 1 spawn | 2 move/anim | 3 attacks/receivers | 4 death/corpse | 5 transport/reward | 6 cleanup/re-entry |
|---|---|---|---|---|---|---|
| Snow `YellowKochappy` | PASS | PASS P1-proxy (+source policies) | PASS entry geometry | PASS | PASS | UNTESTED scene revisit |
| Dwarf Red `Kochappy` | PASS | PASS P1-proxy | PASS Purple stun | PASS P1-proxy | PASS P1-proxy | partial manager only |
| `Ujia` | PASS | PASS sampled | source-backed N/A (no damage) | PASS | PASS | partial forget fallback |
| `Ujib` | PASS | PASS sampled | PASS bite/eat | PASS | PASS | partial forget fallback |
| `FireChappy` | BLOCKED assets | BLOCKED | BLOCKED (lane 10 receivers) | BLOCKED assets | UNTESTED | UNTESTED |
| `KumaChappy` | BLOCKED assets | BLOCKED | UNTESTED | UNTESTED | UNTESTED | BLOCKED revival lifecycle |
| `KumaKochappy` | STAGED (standalone) | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED |
| `BlueKochappy` | STAGED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED |
| `Chappy`/`BlueChappy`/`YellowChappy` | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED | UNTESTED |

Existing PASS rows reuse the integrated Snow (`pc_p2_enemy`), Dwarf Red
(`pc_p2_kochappy`) and Sheargrub (`pc_p2_sheargrub`) modules and their docs; the
gate values live in `GATE_STATUS` in the module.

## 5. Requested shared hooks (narrow, additive, no-op for unregistered actors)

For Fiery Bulblax:

- `pc_p2_firechappy_update(BTeki*)` from `BTeki::update` — fallback alongside the
  existing batch-2 clip chain.
- fire-body state mutation (`startFireState`/`finishFireState`) with an explicit
  `mWaterBox` read; requires the lane-10 `InteractFire` receiver contract.
- reset/forget from the batch reset/forget lists.

For Spotty Bulbear / Dwarf Bulbear:

- `pc_p2_kumachappy_update` + a `ChappyRelation` bridge so Dwarf Bulbears can
  resolve a parent.
- a revival/lifecycle hook (lane 06/07) that reports `revive_carcass` and
  `gauge_rebirth` separately from ordinary death.

No shared semantics are edited by this lane; these are hook requests for lane 01.

## 6. Blockers

1. **FireChappy and KumaChappy assets are not staged** (`enemy/data/FireChappy`,
   `enemy/data/KumaChappy`): the shared asset set only carries `tekis/chappy`.
   Content identity/staging is lane 05.
2. **Elemental receivers** for `InteractFire` and water extinguish are lane 10.
3. **Revival/lifecycle** for the Bulbear carcass is lane 06/07 plus #397.
4. **Dwarf Orange/Bulbear native registration** remains unintegrated; batch-2
   install/arena staging exists but `prepare()` was recorded blocked on a private
   P1 asset copy, and the parent Spotty Bulbear is not imported.
5. **Sheargrub ownership ambiguity:** the fan-out assigns Sheargrubs to lane 13
   while the repo tracks Uji under Ground `#165`/lane 14. Reconcile before either
   lane claims final sign-off.

## 7. Fixture baseline adoption

Not applicable to this root-only slice: no native build and no real-GL run were
performed, so the `#404` adoption record is intentionally not claimed. The next
runtime attempt must follow the fan-out baseline (fresh overlay, regenerated
arena, 20-red squad, centred 960x540 window, active gameplay) and record the
adoption fields.

## 8. Tests

`py -3.12 -m pytest tests/test_pikmin2_bulborb_family.py -q` → 17 passed.
Coverage: source-ID audit, adult/dwarf branch invariants, FireChappy fire/water
and Bulbear revival/relation rules, female-Sheargrub no-damage rule, variant
difference keys, acceptance-contract marker/source-ID, and the native-log
validator (inference, unknown ID rejection, missing source state, extinction
rejection, non-text rejection).
