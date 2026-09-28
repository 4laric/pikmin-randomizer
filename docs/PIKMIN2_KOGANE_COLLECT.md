# Reward beetle real collection and restart dedupe (lane 17, #168/#219) — Slice 2

Implementation owner: Codex through shared account `4laric`. Executing agent:
DeepSeek (`deepseek/p2-l17`), 2026-09-14. Continues slice 1 (`docs/PIKMIN2_KOGANE_NATURAL.md`),
which proved the natural press receiver; this slice closes the next gate: the drops
are actually collected through the ordinary P1 Onion/nectar path (not the Pod), and
a process restart neither duplicates nor loses the receipts nor re-arms the farmed
beetle.

## Source ID and gates

- **Source ID 9 Kogane (Iridescent Flint Beetle)**.
- Gate 5 (actual transport and reward) and gate 6 (cleanup/re-entry) upper bound:
  real carry-to-Onion + nectar drink + exactly-once restart dedupe.

## Native change (worktree `output/dsw/native-l17`, `deepseek/p2-l17-native`)

`pc_port/pc_p2_kogane.cpp` only. The module now grants the drop reward exactly once
through the shared lane-06 ordinary Onion receipt ledger (`pc_p2_receipt_host_*`,
the native counterpart of `experimental/pikmin2_receipts.py`), mirroring the Flora
`P2_FLORA_ONION_RECEIPT` pattern:

- `pc_p2_kogane_setup` reads `PIKMIN_P2_SEED` (product seed when provided, else the
  stable token `kogane-arena`) and opens `p2-kogane-onion-receipts.txt`.
- On every `doDrop`, `pc_p2_receipt_host_grant(seed, "enemy:9", "<generator>",
  "flip<N>")` runs once and logs `P2_KOGANE_ONION_RECEIPT generator=<g> flip=<n>
  granted=<0|1> duplicate=<0|1> ledger=onion seed=<s>`; an `Error` aborts (a receipt
  failure is never consumed as a duplicate).
- The host ledger is a single-consumer singleton that another lane's setup may close
  (e.g. `pc_p2_flora_reset`); `doDrop` lazily re-opens it right before granting so a
  drop reward is never lost.

The family-local flip sidecar (`p2-kogane-receipts.txt`, `restoredFlips`) is unchanged
and remains the separate "press count / no re-arm" layer; the Onion ledger is the
"reward granted exactly once" layer. No shared file was edited.

## Arena fix (placement, not enemy change)

`experimental/pikmin2_kogane_arena.py` relocates the four actors so the collection is
deterministic without touching any enemy behaviour:

- Kogane 219001 -> (-440, 30, 1500), within carry range of the audited red Onion
  goal (practice `red goal` at about (-498, 0, 1454)).
- Wealthy/Fart/control (219002/219003/219004) -> the validated north-east corner
  (150,1850 / 100,1650 / 50,1450), away from the starting squad and the drop zone, so
  their wander never pollutes the collection census.

## Runtime fixture (root, `experimental/pikmin2_kogane_collect.py`)

One parameterized fixture (pass marker `kogane-pass.txt`) with two processes on one
run directory.

- **pass 0 — collection**: verifies births, then issues three *injected* `InteractPress`
  flips on 219001 (labelled; slice 1 already proved the natural receiver). The three
  drops (1 number pellet + 5 `OBJTYPE_Water` nectar) are born near the red Onion; the
  third flip forces the source escape. The fixture then stages the squad onto the
  drop zone and observes real collection: the pellet is carried to the Onion
  (labelled grab+transport initiation via the engine's `PikiAction::Transport`; the
  carry and `GoalItem::suckMe` are native) and the five nectar are drunk (`PIKISTATE_Absorb`).
  A free-Pikmin "nudge" places a Pikmin on any nectar not yet drunk (labelled); the
  drink itself is native. It emits `P2_KOGANE_COLLECTED pellets_collected=1
  nectar_drunk=5 sprouts=N` and `PASS P2_KOGANE_COLLECT collect1 drink5 onion_receipt3`.
- **pass 2 — restart**: a fresh process on the same directory loads the flip sidecar
  (`P2_KOGANE_RECEIPTS loaded=1`, `P2_KOGANE_FLIPS_RESTORED generator=219001 flips=3`,
  `P2_KOGANE_RESTORED_ESCAPE generator=219001 flips=3`), asserts the beetle is not
  re-armed (no new flip/drop/onion grant), and emits `PASS P2_KOGANE_RESTART
  dedupe_ok rearmed=0`.

Validators `validate_collect` / `validate_restart` / `validate_cross` with
`tests/test_pikmin2_kogane_collect.py` (11 tests).

## Accepted run

- Native `b56760901e4f47d03a111ff567af72a00cdf0e12` (clean), JAUDIO=ON;
  `nectar.exe` SHA-256 `d5e6ec9bb9ac6f0aad97f9b92c9de174121f80e16ebd9d9d0500428d398ffc3a`.
- Fixture `output/dsw/l17-out/collect-fixture` `status: built`,
  `fixture.exe` SHA-256 `354a3a02f1d2b012350ff63810008bceeab5b63c1e77f2e80ca10e02175cbd61`.
- Run `output/dsw/l17-out/collect-cross/stages/c0f299055a2646da94b5127ee7264e26`
  (pass0 + pass2, both exit 0, 960x540 centred). Markers:

```
# pass 0
P2_KOGANE_RECEIPTS loaded=0
P2_KOGANE_ONION_RECEIPT generator=219001 flip=1 granted=1 duplicate=0 ledger=onion seed=kogane-arena
... flip=2 ... flip=3 (each granted=1)
P2_KOGANE_ESCAPE generator=219001 source_id=9 flips=3
P2_KOGANE_COLLECTED pellets_collected=1 nectar_drunk=5 sprouts=2
PASS P2_KOGANE_COLLECT collect1 drink5 onion_receipt3

# pass 2
P2_KOGANE_RECEIPTS loaded=1
P2_KOGANE_FLIPS_RESTORED generator=219001 flips=3
P2_KOGANE_RESTORED_ESCAPE generator=219001 flips=3
P2_KOGANE_RESTART rearmed=0
PASS P2_KOGANE_RESTART dedupe_ok rearmed=0
```

`collect-run` (single-process) also passes: `output/dsw/l17-out/collect-run/stages/0e5be9a57a0b41ea9df8d895e5db2f80`.

## Six arena gates (post slice 2)

| Gate | Result | Evidence / label |
|---|---|---|
| 1. Exact identity and spawn | PASS | `P2_KOGANE_BIRTH` ×4 exact stored XYZ; `P2_KOGANE_BIND source_id=9` |
| 2. Autonomous movement/animation | PASS | wander/draw accepted (slice 1); unchanged |
| 3. Attacks and receivers | PASS (natural, slice 1) | `P2_KOGANE_NATURAL_ATTACK` ×3 (slice 1 fixture) |
| 4. Death and corpse | PASS (corpse source-backed N/A) | 3rd flip -> `P2_KOGANE_ESCAPE`; burrow, no corpse |
| 5. Actual transport and reward | **PASS (transport collected)** | pellet carried to Onion (sprout credit), 5 nectar drunk; drops spawned + Onion ledger granted; `P2_KOGANE_COLLECTED` |
| 6. Cleanup and re-entry | **PASS (restart)** | cross-process: receipts reloaded, no re-arm, no duplicate/lost receipt |

Injections, labelled only: three `InteractPress` flips (deterministic flip trigger), a
grab+transport initiation for the pellet, a free-Pikmin "nudge" onto any un-drunk
nectar, and the squad staging teleport. The carry, `GoalItem::suckMe`, the nectar
`PIKISTATE_Absorb` drink and the Onion seed/sprout credit are all native P1 execution.
The lane-06 receipt grant is the ordinary Onion ledger (never the Pod/Poko economy).

## Tests

- `tests/test_pikmin2_kogane_collect.py` -> 11 passed.
- Full lane-17 suite `tests/test_pikmin2_kogane_*.py` -> 127 passed, 11 subtests.

## Remaining (not claimed here)

- Durable P2-save bridge (lane 01/06): both sidecars are run-directory local, not the
  Pikmin save. The receipt ledger is the exact-once ordinary-Onion contract, not a
  save-game mutation.
- Cave treasure object / cave relocation (`Cave::randMapMgr`) — no P2 cave in the P1
  host; first-flip treasure stays a labelled P1 number-pellet stand-in.
- Generated-session admission / mixed-scene budgets (lane 01/33).

## Reproduction

```powershell
py -3.12 -m experimental.pikmin2_kogane_collect build `
  --native C:/Users/alari/pikmin-randomizer/output/dsw/native-l17 `
  --build-dir C:/Users/alari/pikmin-randomizer/output/dsw/native-l17-build `
  --output C:/Users/alari/pikmin-randomizer/output/dsw/l17-out/collect-fixture `
  --head b56760901e4f47d03a111ff567af72a00cdf0e12
py -3.12 -m experimental.pikmin2_kogane_collect run-cross `
  --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets `
  --bank C:/Users/alari/pikmin-randomizer/output/dsw/l17-out/bank `
  --output C:/Users/alari/pikmin-randomizer/output/dsw/l17-out/collect-cross `
  --exe C:/Users/alari/pikmin-randomizer/output/dsw/l17-out/collect-fixture/fixture.exe
```

(single-process collect via `run`; `run-cross` opens a real-GL window and must be
wrapped by the host `gl` slot; the bank is regenerated from
`C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso` via
`py -3.12 -m experimental.pikmin2_kogane_assets --iso <iso> --output <bank dir>`.)
