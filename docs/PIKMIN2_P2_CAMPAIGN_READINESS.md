# P2 species: campaign readiness

What stands between each staged P2 species and a seat in the playable pool
(`randomizer/seed.py` `PLAYABLE_P2_SPECIES`).

"Staged" means `experimental/pikmin2_family_install.py` `IDENTITY_FAMILY` can install it.
"Campaign" means the game running under `pc_randomizer_p2_bridge()` — a real seed, not the
arena/room preview. A species is admitted to the pool only when it boots, is bound to its own
model, and behaves; staging alone is not enough.

Two failure modes matter, and neither is a compile error:

* **Wrong host type.** `pc_port/pc_p2_campaign_policy.h` `hostType()` maps a seed source id to
  a native `TEKI_*` vehicle (`include/teki.h`). Getting it wrong crashed the game ~12s after
  boot (source 44 returned `TEKI_Swallow`=4 where the setup required `TEKI_Chappy`=3, fixed in
  45a0c26b). A source absent from the table falls through to `original`.
* **Silent non-binding.** In bridge mode `bindFamilies` logs `P2_SETUP_SKIP` instead of
  failing, and most per-species setups `return` early when their sidecar or bank is missing.
  The enemy then walks around wearing its P1 host's model — which is how the Dweevils drew as
  Bulborbs before 8ba89e4e.

## Matrix

A species must clear **three** gates, in this order:

1. **Content** — `scripts/p2_prepare_content.py` `EXTRACTORS` can pull its assets off the ISO.
   Without this the species cannot be staged at all, whatever the native code does. Note that
   an entry in `IDENTITY_FAMILY` is *not* enough: the installer knows how to lay the files down,
   but something still has to produce them.
2. **Host type** — `hostType()` matches what its setup checks.
3. **Binding** — something binds its model in bridge mode, and its draw hook is in the chain.

| Source | Species | Content | Host type | Model binding | Ready? |
| --- | --- | --- | --- | --- | --- |
| 44 | BlueKochappy | ✓ | `TEKI_Chappy` 3 | own module | **in pool** |
| 54 | Miulin / Mamuta | ✓ | `TEKI_Miurin` 24 | own module | **in pool** |
| 59–62 | Fire/Water/Gas/Elec Otakara | ✓ | `TEKI_Chappy` 3 | batch2 `dweevil` | **in pool** |
| 23 | Sarai | ✓ extract, **install incomplete** | `TEKI_Chappy` 3 ✓ | own module, bridge sweep | no — see below |
| 9 | Kogane | **no extractor** | `TEKI_Chappy` 3 ✓ | own module, bridge-aware | blocked on content |
| 79 | Sokkuri | **no extractor** | `TEKI_Chappy` 3 ✓ | batch2 `ground\|Sokkuri` | blocked on content |
| 57 | Kurage | **no extractor** | `TEKI_Frog` 0 ✓ | own module, bridge-aware | blocked on content; AI also gated |
| 78 | MiniHoudai / Groink | **no extractor** | `TEKI_Frog` 0 ✓ | **none in campaign** | no |
| 1 | Kochappy | **no extractor** | needs 3, **absent** | own module, `_70`-keyed | no |
| 45 | Snow / YellowKochappy | **no extractor** | needs 3, **absent** | own module, source-blind | no |
| 58 | BombSarai | ✓ `extract_bombsarai` (#244) | `TEKI_Napkid` 11 ✓ (#244) | OWN module `pc_p2_bombsarai_own_teki.cpp` (#244) | no — OWN bot evidence passes, admission held (see below) |

✓ = present and matching what that species' own setup actually requires.

## Measured: Sarai 23 does not bind (2026-09-19)

A seed of the playable six plus Sarai (`--p2-species 44,54,59,60,61,62,23`, 33 enemies, 5 of
them Sarai) was staged and launched headless against native `5e175953`. It boots and runs at
~30 FPS, and the log settles it:

```
P2_GENERATED_PLACEMENT source_id=61 target=3138990329 bound=1
P2_GENERATED_PLACEMENT source_id=60 target=4222852521 bound=1
P2_GENERATED_PLACEMENT source_id=23 target=3640055869 bound=0 reason=host
```

`reason=host` is `buildHost` returning nullptr (`pc_p2_sarai_manager.cpp:70-81`) because the
files it loads are not in the run directory. The install stages `p2-sarai-actors.txt` — correctly,
with all five generator ids — and **none of the eight files the host needs**:

| Needed by `buildHost` | In run dir |
| --- | --- |
| `assets/dataDir/courses/pikmin2room/sarai0.mod` | missing |
| `sarai-wait-poses.txt`, `-move-`, `-attack-`, `-waitact1-`, `-waitact2-` | missing |
| `sarai-attack-mouths.txt` | missing |
| `sarai-retail-events.txt` | missing |

The pose `.mod` files *are* extracted, under `<content>/Sarai/` — so the gap is in the install
step, not extraction: nothing copies them into the run directory or derives the pose/mouth/event
tables there. That is root-line work (`experimental/pikmin2_family_install.py` and
`scripts/p2_prepare_content.py`), not native work.

Note the failure is silent in-game: the five Sarai slots stay Dwarf Bulborbs and nothing
crashes. `bound=0 reason=host` in `native.log` is the only signal.

**So a fourth gate exists: install.** Extraction producing the assets is not the same as the
installer staging what the native loader opens. Check `bound=1` per source id in `native.log`
before calling a species ready.

**Beyond that, the binding constraint is content, not native code.** `EXTRACTORS`
(`scripts/p2_prepare_content.py:252`) covers exactly 44, 54, 59–62 and 23. Seven of the eleven
species have an installer but no way to produce what it installs, so native work on them cannot
be proven in a seed until an extractor exists. Sarai (23) is the only un-pooled species that
clears all three gates.

## What each "no" needs

**58 BombSarai** — OWN port on `claude/p2-port-58-bombsarai` (#244; native fork, root
origin). The earlier gaps listed here (no extractor, no `case 58`, room-preview-only setup,
`_70` matching, `std::abort()`, no draw hook) are closed on that branch: `extract_bombsarai`
stages the retail parms, the own bank and the Bomb payload; `hostType` has `case 58: return 11`;
the OWN module binds every source-58 actor by campaign token through
`pc_randomizer_p2_bind_source(view, 58, token)`, uses `pc_p2_setup_skip` instead of `abort()`,
suppresses the Napkid AI and draws the staged P2 model and Bomb.

Fix stage (2026-09-28): the bomb blast is now lethal to Pikmin. P2
`InteractBomb::actPiki` (`interactPiki.cpp:304-327`) blows every Pikmin with
`BlowStateArg.mIsLethal = true`; the OWN blast had passed fp24 (10, captain damage) to Pikmin,
which only flicked them. Pikmin now take the P1 host's own bomb-rock Pikmin damage
(`PikiMgr` p77 `mBombDamagePiki`, 765 > health 100), resolved by P1 as flick then
`PIKISTATE_Dead` on landing; captains keep fp24. Bot runs on native `36c7fce81` / `c5e11d51b`
show the field count dropping by exactly the lethal hit count (power: 100 -> 62 with
`pikmin_lethal=38`; normal squad: 20 -> 17 with `pikmin_lethal=3`), and the carrier is still
killed, carried and received (`onion:p2:58:3`).

Killing the carrier while it holds a bomb (bot run with
`PIKMIN_RANDOMIZER_AUTOPLAY_BOMBSARAI_HOLD=0`, power x500) follows the source path:
`getNextStateOnHeight` returns `Fall` at `mHealth <= 0` (`BombSarai.cpp:314-318`), the Fall
key-2 event throws the held bomb (`BombSaraiState.cpp:590-596`, log `THROW kind=fall`), and
`Fall` END transits to `Dead` (`:618-621`). The `onKill -> throwBomb(zero)` drop
(`BombSarai.cpp:57-60`) is implemented but was not reached: through the FSM a carrier that dies
holding a bomb always passes through `Fall` first, so that drop only fires on a kill that bypasses
the state machine. `BombFlick` and `TakeOff2` were not seen on the final pins (TakeOff2 was seen
at `8e0cf7a82`).

Admission is **held** until (a) an independent adversarial OWN review passes on the fixed build
and (b) the #893 per-seed sampling (root PR #894) is on main — main has 35 pool species on 35
placement slots, so a 36th cannot be placed without it.

Known fidelity gaps (accepted for now, not admission blockers on their own):

* Carcass: the host Napkid pellet is used and never mutated. Its carry config (3/6) matches the
  P2 retail BombSarai carcass entry (`user/Abe/Pellet/us/carcass_config.txt` min 3, max 6,
  sha256 `a76c4763...de9de0`); the run logs `p2_match=1`. P2's `money 4` and carcass offset
  (10.5, 0, -37) are not staged; the P1 pellet decides the Onion yield.
* Draw: the nearest of 8 sampled rigid poses per clip, no interpolation. The balloons are baked
  static. `supli1` has no convertible pose (zero joint scale) and draws as `wait2`.
* No P2 sound effects; no balloon-pop, down or supply effects. Each blast plays the P1
  bomb-rock explosion effect instead of the P2 Bomb efx.
* Vertical motion uses P1 host gravity while grounded, not P2's. The grounded carrier drifts
  ~90u under a 100-Pikmin crowd; this matches the decomp's direction of effect — P2
  `Creature::resolveOneColl` (`creature.cpp:703-712`) splits collision push by mass ratio and
  BombSarai fp05 is 0.01 against the Piki default 100 (`creature.cpp:33`), so the carrier takes
  essentially all of the push — but the host push magnitude is not measured against P2's.
* Bitter spray and purple Pikmin gates exist but cannot occur in P1.
* The bot's 6 s "stand under the carrier" hold is bot input only. Release/Supply was reached
  with that strategy; a throw-first player knocks the carrier down before it drops the bomb.

**1 Kochappy** — `pc_p2_kochappy_setup()` is only reached from the room-preview branch of
`pc_p2_preview.cpp` (call site `:280`, after the bridge branch returns at `:161-172`), so it
never installs in a campaign. Its actor matching is hard-wired to `mGenerator->_70`
(`pc_p2_kochappy.cpp:50,51,95,100`) and every failure path is `std::abort()` with no
`pc_p2_setup_skip` escape. Needs the same bridge treatment `dwarf_orange` already has.

**45 Snow** — has a campaign branch, but it binds by native type rather than by seed source:
`pc_p2_enemy.cpp:315` reskins *every* `TEKI_Chappy` in the scene. So it cannot coexist with any
other dwarf, and `bindSnow` aborts on an actor already claimed by Kochappy
(`pc_p2_enemy.cpp:171`). Needs the sweep keyed on `pc_p2_campaign_source(actor) == 45` /
`pc_p2_campaign_ids(45)` before it is a per-slot species.

**78 Groink** — the carcass lifecycle is bridge-aware, but the only model loader is the arena
fixture (`pc_p2_groink_arena.cpp:132-148`), whose callers are all under `tools/`, and there is
no `pc_p2_groink_*_draw` in the draw chain. It would play as an invisible-to-the-eye Wollywog.
It must **not** be added to batch2's `cannon` family: `expectedType` there forces
`TEKI_Beatle`/`TEKI_Iwagon`, contradicting the Frog host.

**57 Kurage** — binds and draws correctly in bridge mode
(`pc_p2_kurage_teki.cpp:372-382`), but its FSM is behind `PIKMIN_P2_KURAGE_SHOWCASE`
(`:390-398`), so a campaign Kurage has corpse/receiver behaviour and no Jellyfloat AI. Admit it
only if a decorative, killable Jellyfloat is acceptable; otherwise ungate the FSM first.

## Notes on two things that look like blockers and are not

* **The per-species sidecars are staged.** `p2-kogane-native.txt`, `p2-kurage-teki.txt` and
  `p2-groink-teki.txt` gate their setups with a bare `return` when absent, which reads like a
  hard campaign blocker from inside the native tree. The writers are on the *root* line —
  the `_adapt_kogane` / `_adapt_kurage` / `_adapt_minihoudai` adapters in
  `experimental/pikmin2_family_install.py` (lane #442) — and they run during content prep.
* **Missing assets under `native/assets/`.** That directory holds only a README; the real
  assets come from `--assets` at launch. Absence there does not mean absence at runtime.

## Adding a species to the pool

1. Confirm the `hostType` row matches what the species' own setup checks — find the
   `mTekiType ==` comparison or `static_assert`, do not infer from a sibling species.
2. Confirm something binds its model in bridge mode: either a row in `pc_p2_batch2.cpp`
   `campaignWanted` (only for the five `FAMILIES`), or its own module's bridge-aware setup.
   Check its draw hook is in `tekibteki.cpp`.
3. Launch a seed containing it and watch for `P2_SETUP_SKIP` / `P2_BATCH2_MISSING` in the log.
4. Then add it to the pool table with that evidence.
