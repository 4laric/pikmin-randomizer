# Pikmin 2 scavenger/enemy source audit (#168)

Implementation owner: Codex using shared account 4laric. This is a source-only
audit of the requested cohort. It enables no seed entry, placement,
or gameplay claim. Evidence was read at native `pikmin2-research`
`632af93787b9c95b63f0c13be32b161375ce3a96` (origin
`projectPiki/pikmin2`); no native or shared source was changed.

Bare beetle filenames are under `src/plugProjectNishimuraU/`; Breadbug, nest, and Mamuta filenames are under `src/plugProjectMorimuraU/`; registry/generator files are under `src/plugProjectYamashitaU/`; interaction receivers are under `src/plugProjectKandoU/`; entity headers are under `include/Game/Entities/`.

## Identity, construction, and aliases

The requested numeric IDs are declared as Kogane 9, Wealthy 10, Fart 11,
PanModoki 38, PanModokiNest 39, OoPanModoki 40, Miulin 54, and PanHouse 83
in `include/Game/enemyInfo.h:68-70,97-99,113,142`. `GeneralEnemyMgr` constructs
the three beetle managers separately (`generalEnemyMgr.cpp:244-252`), Breadbug
and Giant Breadbug managers separately (`:328-332`), a `Nest::Mgr` only for
PanHouse (`:334-335`), and a Miulin manager (`:394-395`). Thus a numeric
substitution must preserve a manager-compatible runtime type; the registry is
not evidence that arbitrary IDs share allocation, parameters, collision, or
FSM behavior.

Inheritance is concrete for the beetles: `Wealthy::Obj` and `Fart::Obj` derive
from `Kogane::Obj` (`include/Game/Entities/Wealthy.h:13`, `Fart.h:13`), while
`Kogane::Mgr::doAlloc` supplies one shared parameter family for IDs 9/10/11
(`KoganeMgr.cpp:24-61`). Their own `getEnemyTypeID` overrides retain 10 or 11.
Breadbug and Giant Breadbug each derive from `PanModokiBase::Obj`
(`PanModoki.h:12`, `OoPanModoki.h:12`); the shared base owns `Nest::Obj* mNest`
(`PanModokiBase.h:181`). Miulin is a separate `EnemyBase` subtype
(`Miulin.h:134`), not a Breadbug or beetle variant.

There is an important narrow alias: `EnemyInfoFunc::getEnemyResName` rewrites
ID 39 (and JigumoNest 64) to PanHouse before obtaining the resource name
(`enemyInfo.cpp:168-173`). Generator parsing recognizes the Japanese token for
39 (`genEnemy.cpp:532-534`), while `getEnemyResName` is the only traced rewrite.
This proves a *resource-name* alias only. It does not prove `getEnemyInfo`,
manager dispatch, birth, persistence, or live `getEnemyTypeID()` aliases 39 to
83. Treat a nest record and a live PanHouse as distinct until the generator and
restore paths are traced together.

## Beetle contract: Kogane 9, Wealthy 10, Fart 11

`Kogane::Obj::onInit` (`Kogane.cpp:34`) starts effectively invisible at scale
0.0001, clears carcass/death-effect events, marks it invulnerable, clears its
hit count and timers, and starts the five-state FSM. `Kogane::FSM::init`
(`KoganeState.cpp:13`) registers Appear, Disappear, Move, Wait, and Press.
Appear only advances when Olimar or Pikmin is within sight (`Kogane.cpp:356`);
Move/Wait eventually disappear, and Press is entered only from Move or Wait by
a Pikmin press, hipdrop, or Piki earthquake callback (`Kogane.cpp:139-183,230`).
The callbacks reject non-Piki sources. The source does not establish the exact
collision footprint, terrain safety, or whether every generator anchor reaches
the sight test.

The concrete item trigger is the animation event, not merely a function name:
`StatePress::exec` calls virtual `createItem()` at `KEYEVENT_3`
(`KoganeState.cpp:244-267`). `createTreasureItem` can instead produce the
configured `mPelletDropCode` in a scaling-appear birth state only when
`mHitCount == 0`; it conditionally sets `mFromEnemy` when `Pellet::sFromTekiEnable`, launches the pellet, removes this enemy
from radar, and sets `mAppearTimer` and `mHitCount` to 12800 (`Kogane.cpp:386-417`). The
same drop code is also consulted by `transitDisappear` in a cave, where a valid drop
code with zero hits and an available cave map manager causes a new base generator position/home position and prevents ordinary
disappearance (`:250-266`). This is a concrete cave-reset/relocation hook, but
the audit did not trace cave generator serialization or prove its result stays
available across floor reload.

Absent that treasure branch, Kogane emits one size-1 pellet outdoors or one
yellow nectar in a cave on the first flip; flip 2 emits two yellow nectar; and
flip 3 emits one red nectar after the spicy-spray demo flag or three yellow
nectar. Wealthy emits three size-5 pellets outdoors on the first flip and
three yellow nectar in caves; flips 2 and 3 emit either one red nectar after
that flag or three yellow nectar. The respective implementations are
`Koganemushi.cpp:52-108` and `Wealthy.cpp:52-113`; flip 3 forces
the 12800 disappearance timer (`Wealthy.cpp:52-113`). Fart emits three yellow
nectar on flip 1 and, on flips 2/3, one bitter nectar after the bitter-spray
flag or three yellow nectar; flip 3 likewise sets that timer
(`Fart.cpp:116-167`). These are independent spawned items, not corpses and not
an ownership or delivery guarantee. `createPellet` randomly selects among met
Pikmin colors and launches numbered pellets (`Kogane.cpp:420-636`), so it is
not a fixed-color reward contract.

Fart adds a real receiver interaction. At every common update it runs
`interactFartGasAttack` (`Fart.cpp:24-32`); for 2.5 seconds after
`createFartEffect` it queries a radius/vertical band around a body-joint-offset
position and stimulates living Navis and Pikmin with `InteractGas` and the
general attack damage (`:76-114,213-234`). This is a time/radius receiver
contract, not evidence that gas hits at a proposed anchor. The beetles’
`onKill` only fades their body effect then delegates to `EnemyBase::onKill`
(`Kogane.cpp:70-77`); their initialization explicitly disables leaving a
carcass. Do not infer conventional corpse cargo, score, or a persistent enemy
drop from any `create*` name.

## Breadbug family: PanModoki 38, OoPanModoki 40, PanHouse 83

Each Breadbug birth allocates a separate object through the PanHouse manager,
initializes it, stores it in `mNest`, sets its house type from the parent's live
enemy type, and applies the Breadbug parameter's nest scale
(`panModoki.cpp:54-79`). Base on-init starts the shared 11-state FSM
(`:81-125`; `panModokiState.cpp:13-29`). On either death-state initialization
or final onKill, `killNest` gives the nest `mDeathTimer = 1` and nulls the
parent pointer (`panModokiState.cpp:43-61`; `panModoki.cpp:687-699,1520-1530`).
This is explicit coupled lifetime. The auxiliary object is `EnemyID_PanHouse`,
but whether generator-owned ID 39 enters this same birth route has not been
verified.

The nest itself is a special non-living `Nest::Obj` rather than an ordinary
updating enemy: its header supplies empty update/simulation hooks and returns
false from `isLivingThing` (`include/Game/Entities/Nest.h:25-43`). Its init
disables carcass, damage animation, death effect, and platform collision and
enables bitter immunity (`enemyNest.cpp:25`); `setHouseType` selects Jigumo or
Breadbug presentation (`:62`). The manager's simple-draw path advances the
death timer and starts its delayed fade once that draw-driven counter exceeds 80 (`enemyNestMgr.cpp:86,
143`); the same path decrements alpha by 10 and kills the nest below -255. Do not turn
this draw-driven timer into a claim that the nest has normal enemy persistence
or a standard kill reward.

The carry path is contested cargo, not a simple loot drop. Targeting rejects
non-carryable pellets, treasure when the held-treasure capacity is reached,
pellets stuck to any Teki, and carry configurations that fail `pullable` at
the calculated strength (`panModoki.cpp:1532-1568`). State Stick requires a
free slot 9999, calls `startPick`, then backs away with the target
(`panModokiState.cpp:554-624`). At home, `endCarry` kills Pikmin stickers,
gives up carry state, captures the first treasure into the nest matrix and
marks it not alive; additional treasures, pellets, and carcasses are killed
instead (`panModoki.cpp:1322-1361`). Therefore a treasure can be removed from
ordinary carrier ownership and retained as nest capture. Its later release,
restore, and delivery semantics remain incomplete traces.

The Giant variant is not behaviorally interchangeable just because it shares
the base. It has its own type override and target threshold
(`OoPanModoki.h:14-19`), special sounds in Pulled
(`panModokiState.cpp:276-287`) and Damage (`:453-482`), and a press override
that rejects non-Purple Pikmin before delegating to the base
(`panModoki.cpp:1738-1744`). The audit found no score or cargo-award path.
Press/damage state is also conditional:
base press only accepts Piki sources in selected movement/carry states and
routes to Damage; Damage releases the current carry target and applies proper
press or suck damage (`panModoki.cpp:462-528`; `panModokiState.cpp:453-497`).
Collision suppresses acceleration against PanHouse and while bittered
(`panModoki.cpp:530-546`), and the carrying pathfinder explicitly permits water
and two-way routing (`:1439-1507`). Neither fact certifies water traversal or
safe routes for a randomized placement.

## Mamuta: Miulin 54

Miulin initializes its own FSM in Wait (`miulin.cpp:45-70`) and births a group
of five ShijimiChou at 80 units above its position when that manager exists
(`:27-43`). This is an owner-dependent side birth; absence/capacity behavior
and its persistence are untraced. It searches Navis/searchable, non-stuck
Pikmin inside configured angle/distance windows (`miulin.cpp:582-634`) and
returns home when its no-search/territory rules require it (`:636-704`).

At attacking animation `KEYEVENT_2`, `StateAttacking::exec`
(`miulinState.cpp:253-363`) checks an attack-centered vertical band of +/-20
and horizontal attack radius. Eligible non-stuck, live Pikmin receive
`InteractBury(enemy, 0)`; Navis receive the same interaction with 5.0. The
same event flicks nearby/stuck Pikmin and Navis using shake parameters. The
receiver decides whether Pikmin actually convert: `InteractBury::actPiki`
(`interactPiki.cpp:377-442`) rejects invincible state and US `mePikis >= 99`
(PAL subtracts zikatu), then requires a non-bald triangle, `might_bury()`, and
`ItemPikihead::mgr`. Only after a sprout birth succeeds does it create a
flower-stage same-kind sprout at ground height and kill the original with
`CKILL_DontCountAsDeath`; later terrain/birth failures send the Pikmin to Walk, while the early invincibility/cap rejections return directly. Thus Mamuta
planting is conditional conversion with a cap and terrain/manager dependency,
not damage, a guaranteed seed, a score, or a reusable resource guarantee.
The captain/Navi receiver is materially different: `InteractBury::actNavi`
(`interactNavi.cpp:218-226`) rejects invincibility and starts damage only; it does
not create a sprout.
Miulin's dead state runs deathProcedure then kills at animation end
(`miulinState.cpp:531-556`); corpse carry/yield and save/reset behavior were
not established in this audit.

## Native acceptance still required

Before any cohort member can be enabled, test actual generator/restore identity
for IDs 39/83; all beetle item/relocation branches in cave and field; Breadbug
target capture, nest death, release and path routes with real cargo; Giant
parameters and scoring; and Mamuta burial at terrain, cap, invincible, and
missing-sprout boundary cases. Also observe collision, water, carcass/drop,
day/floor reset, and save-load behavior at each intended anchor. These source
findings identify contracts to preserve; they do not accept physical placement.
