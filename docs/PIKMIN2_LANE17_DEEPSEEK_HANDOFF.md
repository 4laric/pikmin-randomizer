# Lane 17 DeepSeek handoff — reward beetles (fix 4)

Worker: DeepSeek (`deepseek/p2-l17`). Implementation owner: Codex via shared `4laric`.
Tracked on #219 (parent #168). Source ID 9 Kogane (Iridescent Flint Beetle) is the
completed identity; 10 Wealthy / 11 Doodlebug share the family module but are not
separately accepted.

## Review fixes applied (fix 4)

1. **Failed-natural-run disclosure** (see run inventory below): `fix3-cross` pass 0 stalled
   at flip 2, so pass 2 read `P2_KOGANE_FLIPS_RESTORED ... flips=2` (below the escape cap)
   and logged `FAIL p2 room: restarted beetle re-armed (still alive)` at
   `native-pass2.log:756` — a fixture-precondition failure (no escape, no receipts, a
   legitimate respawn), not a reward-cap bug. Listed with its exe SHA.
2. **Mixed-scene wording corrected**: the "flora file has zero `enemy:9`" claim was vacuous
   (the file is never written — Flora bound=0 pending=1, never granted). What is real:
   Flora's handle is opened concurrently (`pc_p2_flora_actor.cpp:247`) with Kogane's, Flora
   never grants, and Kogane's own file holds only its three `enemy:9` rows (no
   `flora-pelplant:` leak) — so the Kogane handle writes only to its own path while Flora's
   handle is open. `run_mixed`'s docstring now says "injected collection pass
   (kogane-mode.txt=0)" rather than "natural".
3. **Pass-2 wording corrected**: pass 2 does not re-flip the (absent, restored-escaped)
   beetle — `command()` positions only (`:68` "no beetle in pass 2: position only, must not
   flip") and emits `P2_KOGANE_NATURAL_COMMAND ... mode=reattempt`; the ledger-cap assertion
   is the genuine `pc_p2_receipt_host_grant` Duplicate re-probe. Gate 3 Result now names the
   per-frame hold of the other beetles/observers (`holdOthers`/`pinObservers`).
4. **Native**: `pc_p2_kogane_reset()` now clears `nectarDropped`; `pc_p2_kogane_onion_ledger_rows()`
   now uses the lane-06 `pc_p2_receipt_host_count(handle)` accessor (no on-disk re-parse).

## Source ID

```
Source ID: 9 `Kogane`
```

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | output/dsw/l17-out/fix4-cross/stages/08b36a21ef504eaa8af9d4ac13e45a8b/native-pass0.log:749 | natural |
| 2. Movement and animation | PASS (natural) | output/dsw/l17-out/fix4-cross/stages/08b36a21ef504eaa8af9d4ac13e45a8b/native-pass0.log:753 | natural |
| 3. Attacks and receivers | PARTIAL (native receiver; forced AI attack; other beetles/observers held per frame) | output/dsw/l17-out/fix3-natural/stages/13e162a3eae842238369cb69a8700fc1/native.log:758 | forced AI attack, not a player throw |
| 4. Death and corpse | PASS (source-backed N/A corpse) | output/dsw/l17-out/fix4-cross/stages/08b36a21ef504eaa8af9d4ac13e45a8b/native-pass0.log:774 | source-backed N/A (burrow, no corpse) |
| 5. Transport and reward | PASS (natural transport) | output/dsw/l17-out/fix4-cross/stages/08b36a21ef504eaa8af9d4ac13e45a8b/native-pass0.log:793 ; onion:enemy:9 | natural transport; flip trigger is a fixture command |
| 6. Cleanup and re-entry | PASS (natural restart) | output/dsw/l17-out/fix4-cross/stages/08b36a21ef504eaa8af9d4ac13e45a8b/native-pass2.log:727 | natural restart dedupe |

Honesty notes on gate 3: the flip *stimulus* is the native `InteractAttack` receiver
(`pc_p2_kogane_attacked` -> `doFlip`, `P2_KOGANE_NATURAL_ATTACK`), but the *trigger* is a
forced fixture `startAction(PikiAction::Attack)+AttackMode` after a `resetPosition` teleport,
with the *other* beetles and the observers held per frame (`holdOthers`/`pinObservers`) while
the TARGET wanders free. No captain punch or thrown Purple exists, so this is not natural
combat: it is a forced AI attack exercising a native receiver. The full natural 3-flip ->
escape -> collect chain is flaky under host AI (flips 1-3 land in some runs, stall at 2 in
others); the deterministic full chain is the injected fallback, labelled `mode=injected`.

```
Source ID: 10 `Wealthy`
```

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | UNTESTED | — | — |
| 2. Movement and animation | UNTESTED | — | — |
| 3. Attacks and receivers | UNTESTED | — | — |
| 4. Death and corpse | UNTESTED | — | — |
| 5. Transport and reward | UNTESTED | — | — |
| 6. Cleanup and re-entry | UNTESTED | — | — |

Wealthy shares the `pc_p2_kogane` module (source id 10, karada 100, distinct drop table) but
no separate acceptance run has been produced; every gate remains `UNTESTED`.

## Source IDs and files owned

- Source IDs: 9 Kogane (slice target), 10 Wealthy, 11 Doodlebug (family 9-11).
- Native (worktree `output/dsw/native-l17`): `pc_port/pc_p2_kogane.cpp`,
  `pc_port/pc_p2_kogane.h` (owned, edited). Shared `pc_port/pc_p2_receipt_host.*` /
  `pc_p2_delivery_host.*` are lane-06 and were only merged/read, not edited (fix 4 uses
  `pc_p2_receipt_host_count`).
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
- `95f2991` + `28925dc3` review fixes 3 — handle port / handoff gate table
- `(fix 4)` review fixes 4 — mixed/docstring wording, Wealthy table, failed-run disclosure

Native (`deepseek/p2-l17-native`, base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`):
- `14e88cc3` natural attack -> flip (slice 1)
- `75153537` + `b5676090` lane-06 onion receipt grant + lazy reopen (slice 2)
- `04af0bce` + `1ccc4f37` restart-dedupe ledger introspection + total-nectar (slice 3)
- `938d552d` review fixes 3 — merge wave native (`c0b195cf`) and port the receipt probes
- `(merge)` merge `claude/p2-deepseek-wave-native` @ `518284a6` (lane 06/18/21 wave tip)
- `1df2d6f8` review fixes 4 — clear nectar census on reset; use `pc_p2_receipt_host_count`

## Interfaces / hooks touched

- `pc_p2_kogane_attacked(Teki*)` — routes a landed Pikmin `InteractAttack` to the flip
  (native receiver; the flip is the only combat outcome).
- `pc_p2_kogane_pressed(Teki*, Creature*)` — injected-press path (shared `doFlip`).
- `doDrop` grants each drop exactly once via `pc_p2_receipt_host_grant(koganeReceiptHandle,
  "enemy:<id>", "<gen>", "flip<N>")`, logging `P2_KOGANE_ONION_RECEIPT … ledger=onion`.
- `pc_p2_kogane_onion_ledger_rows()` — now returns `pc_p2_receipt_host_count(koganeReceiptHandle)`
  (lane-06 count accessor, no on-disk re-parse).
- `pc_p2_kogane_reprobe_duplicates(unsigned generator,int id)` — re-drives the three grants
  through the real `pc_p2_receipt_host_grant` on the per-consumer handle; every result must
  be Duplicate (returns 3, else -1 and the fixture fails closed).
- `pc_p2_kogane_nectar_dropped(unsigned generator)` — per-generator nectar census, cleared on reset.

## Build evidence (`output/dsw/l17-build-evidence.txt`, latest)

```
native=1df2d6f8f13c06a2035ece2be5e53adc2b5155d8 dirty=no exe=nectar.exe
sha256=5db9d5ccf2b12037ee95d0e7a1b68a89e077f4965a19681dc5a8452ada664e5c ninja_n="ninja: no work to do."
```

Fixture `fix4-fixture` status `built`; `fixture.exe` SHA-256
`aaffbd12d758f5cbc9bb8bcf2d20fdc5d633d54a2b7273bcd8cd3574ffa62d7d`.

## Runtime evidence (real-GL, 960x540 centred, `slot.py run gl l17`)

- **Injected cross-process** (`output/dsw/l17-out/fix4-cross/stages/08b36a21ef504eaa8af9d4ac13e45a8b`,
  both processes exit 0, native 1df2d6f8) — the deterministic full chain. pass0: 3 flips,
  exact source drops, 3 `P2_KOGANE_ONION_RECEIPT granted=1`, escape,
  `P2_KOGANE_COLLECTED pellets_collected=1 nectar_drunk=5 sprouts=2`, `PASS P2_KOGANE_COLLECT`.
  pass2: `P2_KOGANE_RECEIPTS loaded=1`, `P2_KOGANE_RESTORED_ESCAPE ... flips=3`,
  `P2_KOGANE_NATURAL_COMMAND ... mode=reattempt`, `P2_KOGANE_REPROBE duplicates=3`,
  `P2_KOGANE_ONION_LEDGER rows=3` (via the `pc_p2_receipt_host_count` accessor),
  `PASS P2_KOGANE_RESTART`.
- **Natural receiver** (`output/dsw/l17-out/fix3-natural/stages/13e162a3eae842238369cb69a8700fc1/native.log`)
  — `P2_KOGANE_NATURAL_ATTACK generator=219001 flip=1,2,3` and `P2_KOGANE_ESCAPE` land via
  the forced AI attack; the follow-on collection did not finish within the window (host-AI
  flakiness), so the natural chain is `PARTIAL` on gate 3 and the full deterministic chain
  is the injected run.
- **Mixed scene** (`output/dsw/l17-out/fix3-mixed/stages/7f59da91d04d42b48d8e79f78e2874ac`,
  exit 0) — Flora co-staged with one pending Pelplant spec. The Kogane collection grants
  three `enemy:9` rows into `p2-kogane-onion-receipts.txt`; Flora's handle is opened
  concurrently but never grants (bound=0 pending=1, no live TEKI_Palm), so
  `p2-flora-receipts.txt` is never written. The separation proof is the absence of any
  `flora-pelplant:` row in Kogane's file while Flora's handle is open; the "flora file empty"
  observation is stated as a non-grant, not as a positive cross-consumer test.
- **Failed natural cross** (`output/dsw/l17-out/fix3-cross/stages/b2469388b75046e4ad5595b6959b12d9`,
  fixture.exe `099e1588…1b57`) — disclosed: pass0 flips 1,2 then stalls (no flip 3 -> no
  escape); pass2 `P2_KOGANE_FLIPS_RESTORED ... flips=2` (below cap) then
  `FAIL p2 room: restarted beetle re-armed (still alive)` at `native-pass2.log:756`. A
  fixture-precondition failure (the cap was never reached), not a reward-cap bug.

## Mixed-scene (lane-06) — satisfied, stated precisely

After lane-06 fix 2 (`pc_p2_receipt_host` keyed by path), Kogane and Flora each hold their
own handle. `run_mixed` proves Kogane writes only its own `enemy:9` rows while Flora's
handle is open concurrently (`pc_p2_flora_actor.cpp:247`). Flora is a non-grant in this run
(no live TEKI_Palm), so a two-file both-granted scene is not claimed.

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
10 Wealthy (role=source):
  1. identity_spawn     ignored [UNTESTED]
  2. movement_animation ignored [UNTESTED]
  3. attacks_receivers  ignored [UNTESTED]
  4. death_corpse       ignored [UNTESTED]
  5. transport_reward   ignored [UNTESTED]
  6. cleanup_reentry    ignored [UNTESTED]
```

No refused PASS; gate 3 `PARTIAL` and the Wealthy `UNTESTED` table are honest non-natural
labels and correctly `ignored`.

## Subagent usage (fix 4)

This pass had no subagent delegation: the fixes were wording/table edits plus two small
native changes (clear + accessor), all in files already loaded in context, so three parallel
subagents would have added coordination cost without parallelisable load. Honest negative:
no time saved by subagents this pass.

## Exact reproduction

```powershell
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/build_lane.py l17
py -3.12 -m experimental.pikmin2_kogane_collect build `
  --native C:/Users/alari/pikmin-randomizer/output/dsw/native-l17 `
  --build-dir C:/Users/alari/pikmin-randomizer/output/dsw/native-l17-build `
  --output C:/Users/alari/pikmin-randomizer/output/dsw/l17-out/fix3-fixture `
  --head 1df2d6f8f13c06a2035ece2be5e53adc2b5155d8
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
