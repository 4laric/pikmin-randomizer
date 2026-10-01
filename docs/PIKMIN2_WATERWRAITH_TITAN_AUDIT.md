# Waterwraith, rollers and Titan Dweevil source audit (#175)

Source behavior audit for enemy IDs 99 `BlackMan`, 98 `Tyre` and 73 `BigTreasure`.
Paths are relative to `native/pikmin2-research` unless they name a disc file.
Numbers marked *disc* come from `enemy/parm/enemyParms.szs` on the US GPVE01
revision 0 disc and override the header defaults quoted next to them. This is an
audit, not an implementation: no actor, save or animation interface changes.

## Identity and placement

| ID | Internal | Piklopedia | Drop table | Registry (`src/plugProjectYamashitaU/enemyInfo.cpp`) |
|---:|---|---:|---|---|
| 99 | `BlackMan` | 81 (stats hidden) | `BDT_Boss` | line 111: spawnable, own ID, child `EnemyID_Tyre` × 1 |
| 98 | `Tyre` | none | `BDT_Empty` | line 112: spawnable, own ID, no child |
| 73 | `BigTreasure` | 75 | `BDT_FinalBoss` | line 105: spawnable, own ID |

`BlackMan` and `BigTreasure` are in `IS_ENEMY_BOSS` (`include/Game/enemyInfo.h:214`).
`BDT_FinalBoss` gives the Titan Dweevil `PSM::EnemyBigBoss` music and a bitter drop
table with zero chance (`enemyBase.cpp:1350`), so it never drops nectar. `Tyre` is a
helper: no Piklopedia entry, no carcass, no drops.

Retail rosters (caveinfo; every entry is type 8 "special enemy" unless noted, which
spawns individually and adds nothing to the floor score, `include/Game/Cave/Info.h:42`):

| Cave | Floors | Entry | `f016` BlackManTimer | Held treasure |
|---|---:|---|---:|---|
| `yakushima_4` (Submerged Castle) | 1 to 4 | `BlackMan_fue_pullout` (type 1) | 300 s | Professional Noisemaker |
| `yakushima_4` | 5 (final) | `BlackMan_fue_pullout` | 15 s | Professional Noisemaker |
| `last_3` (Dream Den) | 14 (final) | `BigTreasure` (type 1) | 0 | four weapons and Louie |
| `ch_MIYA_trap` (Challenge) | 1 | `BlackMan_key`, `BlackMan_doll` | 60 s | The Key, doll |

No surface generator and no Battle definition spawns any of the three. The
Noisemaker is listed on all five Submerged Castle floors but is one unique
collectible (see the treasure ledger). Assets: `enemy/data/{BlackMan,Tyre,BigTreasure}`
model and animation archives; the Waterwraith also has `kagebozu_model.btk`.
Carcasses: none of the three has a `carcass_config.txt` entry.

## Waterwraith (`BlackMan`)

Files: `include/Game/Entities/BlackMan.h`, `src/plugProjectMorimuraU/blackMan.cpp`,
`blackManState.cpp`, `blackManMgr.cpp`.

**Spawn and timer.** The floor layout code, not a manager, births it
(`src/plugProjectKandoU/gameMapParts.cpp:508-529`): only while the cave save data's
`mIsWaterwraithAlive` flag is set (set true on entering floor 1,
`baseGameSection.cpp:2313`; cleared when a floor is left with the wraith dead,
`singleGS_CaveGame.cpp:357-363`). The spawn passes the floor's `f016`
`BlackManTimer` (`gameCaveInfo.cpp:234`, default 0, range 0 to 10000) to
`setTimer`, and the object counts it down every frame (`blackMan.cpp:347`). The
timer saved on leaving a floor is written but never read back; each floor restarts
from its own `f016`. Start height is `mInitialSpawnHeight` (1100) above the floor.

**Fall gate** (`blackMan.cpp:356-386`): when the timer is under 1 s, the fall needs a
live active captain and, on the final Submerged Castle floor, that captain within
`mFallRadius` (300); on other floors the captain must be more than 100 units away.
Until then the timer is pinned at 1 s. In Submerged Castle below the final floor the
first fall plays movie `x20_blackman` and sets `DEMO_Waterwraith_Appears`
(`:391-413`). Emergence Cave (`'y_01'`) and the Piklopedia skip the rollers
entirely and start in Walk with escape phase 2 (`:155-158`).

**States** (`BlackMan.h:367`, FSM `blackManState.cpp:18`): Walk 0, Dead 1, Freeze 2,
Bend 3, Escape 4, Fall 5, Flick 6, Recover 7, Tired 8.

- Fall → Recover once landed (`kagebozu_land`, hard constraint, key 2 fanfare);
  Recover plays `kagebozu_recover`, flicks, and on the final floor key 5 starts the
  boss music; end → `moveRestart` → Walk.
- Walk on rollers (`blackManState.cpp:46-121`, `walkFunc` `blackMan.cpp:831`):
  route-finds toward the pod or waypoints, regenerates 5 health per frame while
  riding (`:843-848`), switches to the faster second step after
  `mTimerToTwoStep` frames (300 header, 0 *disc*, so immediately) using
  `mTravelSpeed` (200 header, 120 *disc*); `isTyreFreeze` → Bend; `isTyreDead` →
  Escape; `isStartFlick` → Flick.
- Bend (`kagebozu_bend`) plays the crouch after a Purple stun; end → Recover, or
  Escape when the rollers are gone. Freeze (`kagebozu_bend2`) is the rollerless
  stun, held `mFreezeTimerLength` frames (200) then back to Walk.
- Escape (`kagebozu_getoff`) is the dismount after the rollers break; end → Walk in
  escape phase 2: distance bands to the active captain choose `Wait` (over 800),
  `Walk` (over 400) or `Run` (`mEscapeSpeed`, 10 header, 250 *disc*), and running
  for `mContinuousEscapeTimerLength` frames (200) → Tired (`blackMan.cpp:873-929`).
- Tired (`kagebozu_wait2`) stands still `mStandStillTimerLength` frames (200) then
  flicks and walks. Flick plays `kagebozu_flick` on rollers or `kagebozu_flick2` on
  foot and returns to the state that requested it.
- Dead (`kagebozu_dead`): key 5 releases the held treasure and effects; end → `kill`.

**Vulnerability** (`blackMan.cpp:624-733`). Any non-Purple Pikmin touching it is
flicked with `PSSE_EN_KAGE_REJECT`; a Purple touching it in Walk or Tired triggers
the rollers' quake stagger. `damageCallBack`: in Tired only a thrown Purple still in
the air (no floor triangle) counts and forces Freeze; in Freeze or Bend the damage is
forwarded into the rollers while they exist and the wraith itself takes none; while
petrified it takes nothing; every other state returns false. Purple pounds follow the
same routing with damage forced to 0.1 while petrified. Bombs do nothing. Collision
parts `kosi` 28, `mune` 20, `head` 15 (`blackman/enemycoll.txt`) become stickable
only in Freeze, Bend or stone. Health 1500 *disc*.

**Death and treasure.** No carcass, no death effects flag; the body vanishes
(`blackMan.cpp:150-152`). The roster-held treasure is thrown from the Dead state's
key 5 (`deadEffect` → `throwupItem`, `:4261-4269`). The radar hides it while it
holds a treasure on rollers (`:245-247`).

**Parameters** (`BlackMan.h:234`, *disc* in parentheses): `mPodMoveSpeed` fp01 10
(20), `mEscapeSpeed` fp02 10 (250), `mEscapeRotationSpeed` fp03 0.1 (0.2),
`mMaxEscapeRotationStep` fp04 10 (30), `mTravelSpeed` fp05 200 (120),
`mRotationSpeed` fp06 0.1 (0.04), `mMaxRotationStep` fp07 10 (3), `mWalkingSpeed`
fp11 10 (50), `mTimerToTwoStep` ip01 300 (0), `mDosinStopTimerLength` ip03 200,
`mFreezeTimerLength` ip04 200, `mContinuousEscapeTimerLength` ip05 200,
`mStandStillTimerLength` ip06 200. Tags fp08 to fp10 and ip02 do not exist.

**Animation keys** (`blackman/enemyanimmgr.txt`, frame:type): `kagebozu_bend`
4:2 5:0 24:1; `bend2` 2:2 3:0 22:1; `dead` 14:2 65:3 102:4 125:5; `flick` 10:2;
`flick2` 12:2; `getoff` 5:2 13:3 21:4 26:5; `move` 0:0 29:1; `recover` 14:2 41:3
43:4 50:5; `run` 0:0 1:2 5:3 11:1; `wait` 8:0 27:1; `wait2` 9:0 28:1; `walk` 7:0
20:2 35:3 36:1; `through` 6:0 6:1; `land` 0:0 0:1 4:2.

## Waterwraith rollers (`Tyre`)

Files: `include/Game/Entities/Tyre.h`, `src/plugProjectMorimuraU/tyre.cpp`,
`tyreState.cpp`, `src/plugProjectNishimuraU/TyreShadow.cpp`.

**Ownership.** Birthed by the wraith in its init with `mOwner` set back
(`blackMan.cpp:159-167`); positions, velocity, facing and scale are pushed from the
rider every frame (`:448-478`, `:982-995`). The rollers have no steering or AI.

**States** (`Tyre.h:235`): Move 0, Land 1, Freeze 2, Dead 3. Starts in Land; on the
first floor contact it flicks, plays the land effect and enters Freeze
(`tyreState.cpp:105-115`). `moveStart` from the wraith's `moveRestart` enters Move;
a purple quake in Move enters Freeze (`tyre.cpp:347-353`). Dead is entered only when
health is gone **and** the wraith has set `EB_Invulnerable` after its dismount
animation finished (`blackMan.cpp:4054-4064`); it plays `tyre_getoff` and kills at
the end with two burst effects.

**Rolling and crushing** (`tyre.cpp:263-313`): while moving and not petrified, any
grounded or stuck Pikmin and any captain in contact is pressed with
`mAttackDamage` (10 *disc*); any other enemy except the wraith gets a 10000 damage
bomb interaction (instant kill); pellets lift the rollers for `mOnPelletAirTime`
(10) frames. Roll rate = distance travelled / `WRAITH_ROLLER_CIRCUMFERENCE` (44π)
scaled by `mTyreRotationSpeed` fp01 (0.5 header, 25 *disc*). Rear wheel follows
terrain via `getMinY` with a ±50 clamp; front wheel leans with the steering angle.
Six collision spheres `tyr1` to `tyr6` (radius 22) become stickable only in Freeze
or stone (`collisionStOn/Off`). Shadow is two joint tubes scaled up from 0.01 to 1
after the fall begins.

**Vulnerability** (`tyre.cpp:319-329`): no Pikmin-kind check of its own; damage is
accepted only when it has moved at least once, is in Freeze or Dead, and is not
petrified. The Purple-only gate lives on the wraith. Health 1800 *disc*, shake-off
thresholds *disc* blows 1/2/5/10, sticking 1/2/3. Bombs do nothing; `hipdropCallBack`
is a stub, the wraith applies pound damage directly.

## Titan Dweevil (`BigTreasure`)

Files: `include/Game/Entities/BigTreasure.h`, `src/plugProjectNishimuraU/BigTreasure.cpp`,
`BigTreasureAttack.cpp`, `BigTreasureState.cpp`, `BigTreasureMgr.cpp`,
`BigTreasureShadow.cpp`.

**Weapons and Louie.** `setupTreasure` (`BigTreasure.cpp:703-742`) births the
pellets `elec`, `fire`, `gas`, `water` and `loozy` (reserved by `BigTreasureMgr`) and
captures them on joints `otakara_*`; each weapon has 6000 health. Collision parts
`elec`, `fire`, `gasi`, `mizu` (radius 25) are stickable while the weapon is held;
body parts `tam1`/`tam2` become stickable only once all four weapons are gone
(`:670-697`). Weapon health is the only thing Pikmin can damage until then, so the
body's health (5000 *disc*) is gated by the weapons implicitly
(`damageCallBack`, `:248-275`: ×0.25 during Land, ×0.1 while petrified). A weapon
at 0 health is released with velocity (0, 100, 0) and becomes an ordinary carriable
pellet (`dropTreasure`, `:788-818`). Louie is released at the death animation's
key 100 and again defensively in `onKill` (`:912-920`, `:115-120`). Carrying Louie
sets `STORY_LouieRescued` (`pelletState.cpp:246-250`). Death is health 0 only.

**States** (`BigTreasure.h:57`): Dead, Stay, Land, Wait, ItemWait, Flick, PreAttack,
Attack, PutItem, DropItem, Walk, ItemWalk. Stay holds frame 0 of `appear` until a
captain or Pikmin is within `mPrivateRadius` (100 *disc*), plays the story movie
`g36_find_louie` once (`DEMO_Find_Titan_Dweevil`), then Land after 4 s. Land walks
the legs in with foot effects and flicks (bitter-immune during Stay and Land).
With weapons: ItemWait (up to 5 s) / ItemWalk (up to 10 s) → PreAttack when Pikmin
are on it or the attack cadence fires → Attack → PutItem. Without weapons: Wait /
Walk / Flick. DropItem (`dropitem` animation) plays only when the last weapon is
lost. Attack cadence (`isAttackLimitTime`, `:356-403`): a timer fed 1× per frame,
3× while a nearby creature is stuck to something else, fires above
`2 × weapons + 4` seconds with a live captain or Pikmin within 225 units.

**Weapon choice** (`setTreasureAttack`, `:984-1035`): weighted random over surviving
weapons, weight = 12000 − weapon health, so damaged weapons are used more.
Each weapon has a pattern 1 (health above 3000) and pattern 2 block; crossing 3000
starts pinch smoke. Charge times fp10 to fp13 are 2.5 s (fire 2.8 s pattern 1),
attack durations fp20 to fp23 are 5 s.

- **Flare Cannon** (`fire`): 8 flame nodes, one every 0.1 s, reach 200 × scale
  (`ff00` 1.0 / `ff10` 1.25), fire status on Pikmin, captains flicked 33 percent of
  the time; aimed by the captain's quadrant (F, FR, FL, FB animations).
- **Comedy Bomb** (`gas`): 200 nodes in 3 arms (pattern 1, `fg00` 0.015 rad/frame,
  reversal 30 s) or 4 arms (pattern 2, `fg10` 0.02, reversal `fg30` 30 or `fg40`
  2 s), reach 480, poison status, rotation frozen while petrified.
- **Monster Pump** (`water`): 16 shots every `fw00` 0.5 s (pattern 2 `fw10`
  0.25 s), aimed at a random non-Blue Pikmin or the nearest captain with angle and
  distance jitter, gravity 20 per frame, drowning bubble on hit.
- **Shock Therapist** (`elec`): 17 nodes scattered from the weapon joint with
  bounce and friction from the `fe` blocks, chained after the discharge start
  time; the link segments deal electric damage with a 150 unit knockback.

**Legs and body.** Four IK limbs with ground callbacks and foot effects; the leg
collision tubes `lft`/`lht`/`rft`/`rht` 1 to 5 are model-defined and deal **no
damage**. All Pikmin harm comes from the weapons and from shake-offs.

**Death** (`BigTreasureState.cpp:41-118`): `dead` animation with leg and body bomb
effects on keys 2 to 11, key 100 throws the held item and releases Louie, end kills.
No carcass and no death throw-up (`EB_LeaveCarcass` disabled, empty
`throwupItemInDeathProcedure`). Music tracks by remaining weapon count come from
`PSM::EnemyBigBoss`; the Defeated track is never requested from this class.

**Animation keys** (`bigtreasure/enemyanimmgr.txt`): `appear` 26:2 30:3 50:4 60:5
82:6 90:7 100:8 115:9 191:10; `wait1` 0:0 89:1; `preattackF` 20:2 68:0 82:1 85:3;
`preattackW/G/E` 20:2 68:0 82:1; `attackF/FR/FL/FB` 0:0 1:2 119:1; `attackW` 0:0
1:2 29:1; `attackG` 0:0 1:2 79:1; `attackE` 0:0 1:2 39:1; `dropitem` 60:2; `wait2`
0:0 29:1; `flick` 35:2; `dead` 60:2 100:3 125:4 150:5 175:6 200:7 290:8 295:9
300:10 305:11 320:100. The `preattackFR/FL/FB` and all `attackend*` motions carry
no keys. The disc parameter file lists the `fg99` tag twice, matching the duplicated
tag on `mPatternCheckWater` in the header (`BigTreasure.h:375`).

## Dependencies a reimplementation must provide

- Cave save data (`mIsWaterwraithAlive`, timer), the floor `f016` parameter and the
  layout spawn hook for the wraith; `RoomMapMgr::mWraith`; route manager and
  two-way pathfinding; pod position for the roller route.
- Joint callbacks that slave hands and feet to roller joints
  (`tyreFL`, `TyreFR`, `TyreBL`, `tyreBR`, inconsistent capitalisation is part of the
  model), joint shadows, XFB refraction material and BTK for the wraith.
- Pellet births with `startCapture`/`endCapture` for five Titan pellets, IK system,
  cell iterators, `traceMove`, water boxes, `PSM::EnemyMidBoss`/`EnemyBigBoss`
  requests, movie player and demo flags.

## Unknowns and decomp caveats

- `walkFunc`, `findNextRoutePoint`, `setPathFinder` and the joint matrix functions of
  the wraith, the roller shadow code, and the Titan's attack and shadow modules are
  reconstructed beside retained assembly; evaluation order there is inferred.
- The wraith `escape()` helper is empty; the saved per-floor timer is never read.
- `Tyre` lacks `createEfxHamon`/`fadeEfxHamon` declarations that the wraith calls.
- Titan `hipdropCallBack` returns the negation of `damageCallBack`; the `fg99` tag is
  duplicated; leg part names beyond `*1` are model data.
- Natural runtime evidence, the timed-floor pressure with full squads and the
  Louie rescue ending flow remain runtime work for the enemy and campaign lanes.
