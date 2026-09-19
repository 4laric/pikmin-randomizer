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

| Source | Species | Host type | Model binding | Campaign-ready? |
| --- | --- | --- | --- | --- |
| 44 | BlueKochappy | `TEKI_Chappy` 3 | own module | **in pool** |
| 54 | Miulin / Mamuta | `TEKI_Miurin` 24 | own module | **in pool** |
| 59–62 | Fire/Water/Gas/Elec Otakara | `TEKI_Chappy` 3 | batch2 `dweevil` | **in pool** |
| 9 | Kogane | `TEKI_Chappy` 3 ✓ | own module, bridge-aware | **yes** — no known blocker |
| 79 | Sokkuri | `TEKI_Chappy` 3 ✓ | batch2 `ground|Sokkuri` | **yes** — no known blocker |
| 23 | Sarai | `TEKI_Chappy` 3 ✓ | own module, bridge sweep | **yes** — no known blocker |
| 57 | Kurage | `TEKI_Frog` 0 ✓ | own module, bridge-aware | visual yes, **AI gated** |
| 78 | MiniHoudai / Groink | `TEKI_Frog` 0 ✓ | **none in campaign** | no |
| 1 | Kochappy | needs 3, **absent** | own module, `_70`-keyed | no |
| 45 | Snow / YellowKochappy | needs 3, **absent** | own module, source-blind | no |
| 58 | BombSarai | needs `TEKI_Napkid` 11, **absent** | **none in campaign** | no |

✓ = the table entry is present and matches what that species' own setup actually requires.

## What each "no" needs

**58 BombSarai** — the largest gap, and the one most likely to crash rather than just look
wrong. `pc_p2_bombsarai_teki.cpp:588,604` `std::abort()` unless the host is `TEKI_Napkid` (11),
and `hostType` has no `case 58`. Beyond the table row it needs: the setup's
`if (!pc_pikipelago_room_preview()) return;` gate at `:581` replaced with a bridge path;
generator matching via `pc_p2_campaign_token()` rather than `mGenerator->_70` at `:601` (Sarai
does this correctly in `pc_p2_generated_placement.cpp:75-88`); removal of the
abort-on-multiple/abort-on-missing single-instance behaviour at `:583-593`, `:604`, `:615-620`,
since a seed places N copies with ids unknown at authoring time; and a draw hook — there is no
`pc_p2_bombsarai_*_draw` in either chain (`tekibteki.cpp:177,2118`), so it renders as a stock
Napkid.

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
