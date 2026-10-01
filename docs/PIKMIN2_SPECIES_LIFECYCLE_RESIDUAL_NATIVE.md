# Species-lane lifecycle proof + Hana/Catfish residual fidelity

Issue [#407](https://github.com/4laric/pikmin-randomizer/issues/407). Three
parallel slices merged into the species lane branch
(`opencode/p2-species-native`). Owner: Codex via shared `4laric`.

## Ground death / corpse / cleanup / re-entry (Sokkuri, Armor)

First runtime proof of the fan-out's gates 4 and 6 for two implemented species,
using a replacement-main fixture with fixture-injected lethal damage (explicitly
labelled `not_natural_combat=1`).

- Native: `pc_port/pc_p2_sokkuri.{cpp,h}` + `pc_p2_armor.{cpp,h}` read-only
  registration probes (`pc_p2_*_count`/`_registered`) and a host-strategy corpse
  teardown fix.
- **Bug found and fixed:** the modules called `BTeki::die()` from the update
  hook, which permanently blocked the host's `dieSoon()`→`becomePellet()` path
  (Sokkuri died but left no corpse; Armor's strategy happened to win the race).
  Commit `b635db09` lets the host strategy complete teardown/corpse.
- Fixture: `output/pikmin2-ground-lifecycle-fixture` (provenance `built`,
  fixture.exe `4a57C0D5…41ED2FD`), 960×540 centred, `P2_LIFECYCLE_READY squad=20`.
- Runtime PASS: `output/pikmin2-ground-lifecycle-run5/d659543ab9f04665a2a90e94a3910018`
  (`PASS P2_GROUND_LIFECYCLE death=Sokkuri,Armor corpse=2 registry_empty=2
  reentry=2 stale=0 duplicate_reward=0 injected=1`; log `7E72FCFF…3DA7173`).

| Gate | Result | Evidence |
|---|---|---|
| 4 Death | PASS | `P2_SOKKURI_DEAD`/`P2_ARMOR_DEAD` + forced `dead1`/`dead` clips |
| 4 Corpse | PASS | host corpse pellet with `mPelletView==actor`; `P2_BATCH2_DRAW corpse=1` |
| 5 Delivery/reward | UNTESTED | arena is cargo-free/no Pod (`pod=0`, `pokos=-1`); #397 owns the receipt path |
| 6 Cleanup | PASS | `pc_p2_*_forget` → `count=0 registered=0`, stale `clip()` false |
| 6 Re-entry | PASS | fresh generator rebirth + family setup; `stale=0 fresh=1`, no fresh corpse/duplicate reward |

## Hana residual: underground gate, `fp02` poison, `attackNavi`

- Native: `pc_port/pc_p2_hana.*`, `pc_p2_hana_residual_policy.h`,
  `tekiinteraction.cpp` attack/bomb gate; `tools/P2_HANA_RESIDUAL.md`.
- Underground: read-only gate rejects damage while buried and toggles host
  `TEKIOPT_Atari`/`Invincible` (authoritative-only); the P1 host has no
  `EB_Invulnerable`/`ModelHidden`, so this is a documented approximation.
  Runtime enter/exit markers are informational here (Hana wakes immediately in
  the arena); the gate is covered by the standalone policy test.
- `fp02` poison = 2500 on a successful White swallow, exactly-once;
  `attackNavi` at the `attack1` bite frame.
- Runtime PASS: `output/p2-species-hanaresid-final2/5bda94bdc87c44c0959cf1fcdf90a542`
  (`P2_HANA_ATTACK_NAVI … damage=10`, `poison_accounting` true); log
  `B73A3C2A…1595E70C`. 38 focused tests pass (this + catfish + lifecycle).

## Catfish residual: two-slot mouth, `attackNavi`, `fp02` poison, banked flick

- Native: `pc_port/pc_p2_catfish.*`, `pc_p2_catfish_residual_policy.h`;
  `tools/P2_CATFISH_RESIDUAL.md`.
- Two-slot capture at the banked bite frame 17 (nearest-first, exactly-once),
  one kill per slot at the banked swallow frame 75; `attackNavi` fp24=10 at
  frame 17; `fp02` poison = 300 per consumed White; flick from the banked events
  (25 knockback / 47 restore).
- Runtime PASS (re-validated): `output/p2-species-catfish-residual/b071f8bf398b4e0fbae4403ba1e37aba`
  — all checks true (log `E80AC058…822C90`). Only one target was inside the
  sweep per attack cycle, so two simultaneous slots remain policy-tested only.

## Remaining

- Delivery/receipt for gate 5 (#397), dead-but-corpseless press path, two
  simultaneous mouth slots at runtime, and the documented per-species fidelity
  gaps.
