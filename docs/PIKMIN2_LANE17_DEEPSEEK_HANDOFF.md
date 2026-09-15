# Lane 17 DeepSeek handoff — reward beetles (fix 3)

Worker: DeepSeek (`deepseek/p2-l17`). Implementation owner: Codex via shared `4laric`.
Tracked on #219 (parent #168). Three slices delivered on this branch; this file is the
post-review fix-3 record and supersedes the earlier slice sections. Source ID 9 Kogane
(Iridescent Flint Beetle) is the completed identity; 10 Wealthy / 11 Doodlebug share the
family module but are not separately accepted.

## Review fixes applied (fix 3)

1. **Merged lane-06 fix 2** (`claude/p2-deepseek-wave-native` @ `c0b195cf`) and ported the
   receipt probes to the new handle-per-path API (**done**): `pc_p2_receipt_host_open`
   now returns a `P2ReceiptHostHandle`; `pc_p2_receipt_host_grant(handle, …)`; the kogane
   module holds its own `koganeReceiptHandle` and never reopens unconditionally.
   `run_mixed` now runs for real and the two ledgers stay separate (**done**, see below).
2. **Re-ran on the committed head** until flips landed (**done**): the injected cross
   passes deterministically; the natural receiver flips land (this re-run below).
3. **Pass-2 second-flip sequence now executes** (**done**): `command()` aims at the
   TARGET birth anchor from `hold` (not the null `beetle`), so
   `P2_KOGANE_NATURAL_COMMAND ... mode=reattempt` is emitted and validated.
4. **Natural-vs-injected label corrected** (**done**): gate 3 is `PARTIAL` "native
   receiver, forced AI attack" — no longer claimed as a natural player throw.
5. `pc_p2_kogane_nectar_dropped(unsigned generator)` is now per-generator; `_launch` is
   factored out of `run_mixed`/`run_cross_process`; the commit list names every commit;
   the binary is named per run (**done**).

## Source ID

```
Source ID: 9 `Kogane`
```

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | output/dsw/l17-out/fix3-cross-inj/stages/67e22bc33b63448a8304d38f80e33b7c/native-pass0.log:748 | natural |
| 2. Movement and animation | PASS (natural) | output/dsw/l17-out/fix3-cross-inj/stages/67e22bc33b63448a8304d38f80e33b7c/native-pass0.log:752 | natural |
| 3. Attacks and receivers | PARTIAL (native receiver; forced AI attack) | output/dsw/l17-out/fix3-natural/stages/13e162a3eae842238369cb69a8700fc1/native.log:758 | forced AI attack, not a player throw |
| 4. Death and corpse | PASS (source-backed N/A corpse) | output/dsw/l17-out/fix3-cross-inj/stages/67e22bc33b63448a8304d38f80e33b7c/native-pass0.log:773 | source-backed N/A (burrow, no corpse) |
| 5. Transport and reward | PASS (natural transport) | output/dsw/l17-out/fix3-cross-inj/stages/67e22bc33b63448a8304d38f80e33b7c/native-pass0.log:795 ; onion:enemy:9 | natural transport; flip trigger is a fixture command |
| 6. Cleanup and re-entry | PASS (natural restart) | output/dsw/l17-out/fix3-cross-inj/stages/67e22bc33b63448a8304d38f80e33b7c/native-pass2.log:726 | natural restart dedupe |

Honesty notes on gate 3: the flip *stimulus* is the native `InteractAttack` receiver
(`pc_p2_kogane_attacked` -> `doFlip`, `P2_KOGANE_NATURAL_ATTACK`), but the *trigger* is a
forced fixture `startAction(PikiAction::Attack)+AttackMode` after a `resetPosition`
teleport, plus a per-frame hold of the *other* beetles (the TARGET is free to wander).
No captain punch or thrown Purple exists, so this is not natural combat: it is a forced
AI attack exercising a native receiver. The full natural 3-flip -> escape -> collect chain
is flaky under host AI (flips 1-3 land in some runs, stall at 2 in others); the
deterministic full chain is the injected fallback below, labelled `mode=injected`.

## Source IDs and files owned

- Source IDs: 9 Kogane (slice target), 10 Wealthy, 11 Doodlebug (family 9-11).
- Native (worktree `output/dsw/native-l17`): `pc_port/pc_p2_kogane.cpp`,
  `pc_port/pc_p2_kogane.h` (owned, edited). Shared `pc_port/pc_p2_receipt_host.*` /
  `pc_p2_delivery_host.*` are lane-06 and were only merged/read, not edited.
- Root (worktree `output/dsw/l17-root`): `experimental/pikmin2_kogane_collect.py`,
  `tests/test_pikmin2_kogane_collect.py`, `experimental/pikmin2_kogane_arena.py`,
  `experimental/pikmin2_kogane_natural.py`, tests and docs.

## Ordered commits (dirty: clean on both)

Root (`deepseek/p2-l17`, base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`):
- `3a018b0` natural press receiver (slice 1)
- `944cb6d` + `a9d0711` slice-1 handoff / commit-list
- `8d44bcf` real collection + restart dedupe (slice 2)
- `595cbe7` + `6055ee4` slice-2 fixes / handoff
- `85946ee` honest re-arm message (slice 3 prep)
- `7e126f8` + `35ec3a3` slice-3 natural flips + restart re-probe + handoff
- `95f2991` review fixes 3 — handle-API port, real second-flip re-attempt, mixed-scene separation, per-generator nectar, `_launch` helper

Native (`deepseek/p2-l17-native`, base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`):
- `14e88cc3` natural attack -> flip (slice 1)
- `75153537` + `b5676090` lane-06 onion receipt grant + lazy reopen (slice 2)
- `04af0bce` + `1ccc4f37` restart-dedupe ledger introspection + total-nectar (slice 3)
- `938d552d` review fixes 3 — merge wave native (`c0b195cf`) and port the receipt probes to the handle API

## Interfaces / hooks touched

- `pc_p2_kogane_attacked(Teki*)` — routes a landed Pikmin `InteractAttack` to the flip
  (native receiver; the flip is the only combat outcome).
- `pc_p2_kogane_pressed(Teki*, Creature*)` — injected-press path (shared `doFlip`).
- `doDrop` grants each drop exactly once via `pc_p2_receipt_host_grant(koganeReceiptHandle,
  "enemy:<id>", "<gen>", "flip<N>")`, logging `P2_KOGANE_ONION_RECEIPT … ledger=onion`.
- `pc_p2_kogane_onion_ledger_rows()` — reads the lane-06 `P2_RECEIPTS_1` ledger row count
  (0 missing, -1 malformed). *Lane-06 count-accessor ask:* re-parses the on-disk format
  rather than calling a host accessor.
- `pc_p2_kogane_reprobe_duplicates(unsigned generator,int id)` — re-drives the three grants
  through the real `pc_p2_receipt_host_grant` on the per-consumer handle; every result must
  be Duplicate (returns 3, else -1 and the fixture fails closed).
- `pc_p2_kogane_nectar_dropped(unsigned generator)` — per-generator nectar census.

## Build evidence (`output/dsw/l17-build-evidence.txt`, latest)

```
native=938d552dffc8cc8481a997758109ed45eb45ac52 dirty=no exe=nectar.exe
sha256=d54895a787460085277e77379e4d7f3811f6520967f15789edac451185c61659 ninja_n="ninja: no work to do."
```

Fixture `fix3-fixture` status `built`; `fixture.exe` SHA-256
`099e1588b04ae55f3b16df76555828934410daca12fca258e94b31f383d41b57`.

## Runtime evidence (real-GL, 960x540 centred, `slot.py run gl l17`)

- **Injected cross-process** (`output/dsw/l17-out/fix3-cross-inj/stages/67e22bc33b63448a8304d38f80e33b7c`,
  both processes exit 0) — the deterministic full chain. pass0: 3 flips, exact source
  drops, 3 `P2_KOGANE_ONION_RECEIPT granted=1`, escape, `P2_KOGANE_COLLECTED pellets_collected=1
  nectar_drunk=5 sprouts=2`, `PASS P2_KOGANE_COLLECT`. pass2: `P2_KOGANE_RECEIPTS loaded=1`,
  `P2_KOGANE_RESTORED_ESCAPE ... flips=3`, `P2_KOGANE_NATURAL_COMMAND ... mode=reattempt`,
  `P2_KOGANE_REPROBE duplicates=3`, `P2_KOGANE_ONION_LEDGER rows=3`, `PASS P2_KOGANE_RESTART`.
- **Natural receiver** (`output/dsw/l17-out/fix3-natural/stages/13e162a3eae842238369cb69a8700fc1/native.log`)
  — `P2_KOGANE_NATURAL_ATTACK generator=219001 flip=1,2,3` and `P2_KOGANE_ESCAPE` land via
  the forced AI attack; the follow-on collection did not finish within the window (host-AI
  flakiness), so the natural chain is `PARTIAL` on gate 3 and the full deterministic chain
  is the injected run.
- **Mixed scene** (`output/dsw/l17-out/fix3-mixed/stages/7f59da91d04d42b48d8e79f78e2874ac`,
  exit 0) — Flora co-staged; `p2-kogane-onion-receipts.txt` has exactly three `enemy:9` rows
  and zero `flora-pelplant:` rows, `p2-flora-receipts.txt` has zero `enemy:9`. The two
  per-consumer ledgers stay separate under the handle-per-path host.

## Mixed-scene (lane-06) — now satisfied

The slice-3 "single-consumer singleton" blocker is gone after lane-06 fix 2: the receipt
host is keyed by path (`std::map<path, ReceiptHost>`), so Kogane and Flora each hold their
own handle and write their own file. `run_mixed` proves the separation (`kogane == 3 x
enemy:9`, `flora == []`, no cross-leak).

## Tests

- `py -3.12 -m pytest tests/test_pikmin2_kogane_collect.py -q` -> 23 passed.
- Full lane-17 suite `py -3.12 -m pytest tests/test_pikmin2_kogane_*.py -q` -> 139 passed, 11 subtests.

## Gate-check output

```
$ py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_LANE17_DEEPSEEK_HANDOFF.md
9 Kogane (role=source):
  1. identity_spawn     accepted [PASS]
  2. movement_animation accepted [PASS]
  3. attacks_receivers  ignored [PARTIAL]
  4. death_corpse       accepted [PASS]
  5. transport_reward   accepted [PASS]
  6. cleanup_reentry    accepted [PASS]
10 Wealthy (role=source): warning (shared table) - named in prose but no table of its own; give it a `Source ID` line + six-gate table to claim its gates
```

No refused PASS; the only non-PASS row (gate 3 `PARTIAL`) is an honest non-natural label and is
correctly `ignored` (the forced AI trigger never advances a natural-combat gate).

## Subagent usage (fix 3, honest)

- `explore` #1 (source audit + lane-06 handle host + gate-table contract): used as-is; gave
  the exact handle-per-path semantics, flora sidecar name, and the NONNATURAL_MARKERS /
  citation rules that shaped the gate table. Saved ~30 min.
- `explore` #2 (slice-3 candidate inventory + build evidence): used as-is; confirmed the
  receipt-host function inventory and that the fix3 native head builds. Saved ~15 min.
- `general` #3 (reattempt + mixed-scene tests): used, then corrected — its `natural_reattempt`
  test correctly reported the check missing, which I then added to `validate_restart`; its
  5 `validate_mixed_scene` separation tests passed against my rewritten validator. Net saved
  ~10 min of test authoring.

## Exact reproduction

```powershell
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/build_lane.py l17
py -3.12 -m experimental.pikmin2_kogane_collect build `
  --native C:/Users/alari/pikmin-randomizer/output/dsw/native-l17 `
  --build-dir C:/Users/alari/pikmin-randomizer/output/dsw/native-l17-build `
  --output C:/Users/alari/pikmin-randomizer/output/dsw/l17-out/fix3-fixture `
  --head 938d552dffc8cc8481a997758109ed45eb45ac52
# deterministic full chain (gates 4/5/6) + restart dedupe:
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l17 -- `
  py -3.12 -m experimental.pikmin2_kogane_collect run-cross `
  --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets `
  --bank C:/Users/alari/pikmin-randomizer/output/dsw/l17-out/bank `
  --output C:/Users/alari/pikmin-randomizer/output/dsw/l17-out/fix3-cross-inj `
  --exe C:/Users/alari/pikmin-randomizer/output/dsw/l17-out/fix3-fixture/fixture.exe --mode injected
# mixed-scene ledger separation:
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l17 -- `
  py -3.12 -m experimental.pikmin2_kogane_collect run-mixed `
  --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets `
  --bank C:/Users/alari/pikmin-randomizer/output/dsw/l17-out/bank `
  --output C:/Users/alari/pikmin-randomizer/output/dsw/l17-out/fix3-mixed `
  --exe C:/Users/alari/pikmin-randomizer/output/dsw/l17-out/fix3-fixture/fixture.exe
```
