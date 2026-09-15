# KingChappy natural combat -> lethal death gate (#172 / #289 / #445)

Lane-24 bounded slice. Moves the Emperor Bulblax (KingChappy, enemy 53) natural
combat receiver from a per-entry unit blow to a continuous latch, and proves the
lethal path end-to-end **without the opt-in kill/health injection** that the
bumped #289 fixture uses. Family parent [#172]; actor issue [#289]; tracking
[#445].

## What changed

- Native `pc_port/pc_p2_king.cpp`: the actor-local `receiveScan` now keeps
  delivering the unit per-blow damage while Pikmin remain stuck to a collision
  part, not only on the tick each Pikmin first enters the root sphere. A
  per-actor `damageClock` accumulates ticks and applies
  `stuckCount * DamagePerBlow` every `BlowIntervalTicks`, emitting
  `P2_KING_COMBAT_DAMAGE`. This is what drives the natural health-to-zero path.
  The entry blow (`1.0 * damageTier(...)`) and the `blows`/`stuckCount` flick
  counters are unchanged, so the already-passed flick/trample timing is
  untouched.
- Native `pc_port/pc_p2_king_policy.h`: adds `DamagePerBlow = 1.0f` (stuck-to-part
  tier x1) and `BlowIntervalTicks = 20` (2/3 s at the 30 Hz behavior clock),
  documented as an approximation of the ordinary Pikmin attack cadence. The P1
  per-color blow strength remains out of scope.
- Root `experimental/pikmin2_king_natural_death_runtime.py`: new fixture that
  stages a 32-red starting squad in a ring around the buried Emperor, removes
  `p2-king-inject.txt` and aborts if it reappears, and lets the actor's own
  `receiveScan` drive health to 0. The only staging is the labeled per-tick
  re-pin of the live squad into a ring (as in the natural-Flick harness; note this pin neutralises the shake-off, so the entry blow at pc_p2_king.cpp re-fires for all stuck Pikmin after every Flick — roughly 7 flicks × 32 ≈ 220 of the 1300 HP came from that pin-defeats-flick loop; staging that inflates damage, not injection) plus
  the larger authored squad so blows accumulate on this host's clock. There are
  no bombs and no force/Flick/kill injection. Exit 0 only when the Dead clip's
  frame-185 kill key fires naturally; a bounded window without a Dead key exits 3.
- Root `tests/test_pikmin2_king_natural_death_runtime.py`: validator-only tests
  for the new gate (injection/bomb markers and the natural combat/death markers).
- `tests/pikmin2_king_policy.cpp`: asserts the two new policy constants.

## Six arena gates (this slice)

| Gate | Status | Evidence |
|---|---|---|
| 1. Exact identity and spawn | PASS | `P2_KING_READY id=230020 enemy=53 variant=default` |
| 2. Autonomous movement and animation | PASS | `P2_KING_APPEAR_TRIGGER`, sampled clip draw, un-injected |
| 3. Attacks and receivers | PASS | `P2_KING_COMBAT_DAMAGE id=230020 stuck=N damage=M health=H interval=20` — natural | receiver damage |
| 4. Death and corpse | PASS | `P2_KING_STATE ... to=2 health=0`, `P2_KING_DEAD_KEY id=230020 frame=185 kill=1` |
| 5. Actual transport and reward | source-backed N/A | Emperor has no corpse/carry reward in this fixture (family-local outcome; rewards are lane 06) |
| 6. Cleanup and re-entry | PASS | natural `P2_KING_NATDEATH` exit with no leftover process (re-entry alias not exercised this slice) |

Injected state (health forced to 0 via `P2_KING_INJECT_KILL`) is the previously
passed #289 gate and is **not** re-run with unchanged inputs here. This run has
no injection channel at all.

## Evidence

Observed natural sequence (unicode fixture run, exit 0):

```text
P2_KING_NATDEATH_BASELINE red=32 other=0
P2_KING_NATDEATH_ARMED no_injection=1
P2_KING_COMBAT_DAMAGE id=230020 stuck=32 damage=32.0 health=1236.0 interval=20
        ... 38 continuous damage lines, health monotonic 1236.0 -> 0 ...
P2_KING_COMBAT_DAMAGE id=230020 stuck=25 damage=25.0 health=11.0 interval=20
P2_KING_COMBAT_DAMAGE id=230020 stuck=25 damage=25.0 health=0.0 interval=20
P2_KING_STATE id=230020 from=4 to=2 health=0 death_rate=0
P2_KING_DEAD_KEY id=230020 frame=185 kill=1
PASS P2_KING_NATURAL_DEATH natural_combat_death
```

- Run directory: `output/dsw/l24-out/king-natdeath-runtime2/king/ec2894c79d0641388d6795febc4ebb99`
  (`native.log`, `result.json`, `king-natural-death.ppm`).
- Native commit `1131c8fb723d731f0c11d286b2456dd89166e0ce`; `pikmin_pc` `nectar.exe`
  SHA-256 `325041047cd29ac59f85a3d25326b05a1c3bd1447232410dff797ece451a66d9`;
  `ninja: no work to do.` dry run.
- Fixture `output/dsw/l24-out/king-natdeath-fixture2/build/fixture.exe`, provenance
  `built`, expected native head `1131c8fb...`, SHA-256
  `7840a6ddf52327751270f500d01150a5799c93e33b5025ab69dd2abc911b1afc`.
- Bank: `output/dsw/l24-out/bulblax-bank` (174 poses, 8,154,624 bytes) rebuilt from
  the US GPVE01 rev 0 disc this session.

### Fixture baseline adoption

```text
Fixture baseline adoption
Child issue / lane / implementation owner: #445 / lane 24 (King natural combat->death) / Codex via shared account 4laric
Root commit + dirty state / overlay source: 63d15eae1394dce1a4db484d729f01f724f10323 (clean); scripts/preview_pikmin2_room.py overlay ensure_pikmin_squad present (20 reds), but this fixture authors its own 32-red squad so the overlay does not top up.
Native commit + dirty state / worktree / private build directory: 1131c8fb723d731f0c11d286b2456dd89166e0ce (clean), worktree output/dsw/native-l24, build output/dsw/native-l24-build.
Squad change present / window change present: overlay ensure_pikmin_squad present in root; window 960x540 centred default present in native pc_port/pc_main.cpp and the fixture entrypoint tools/preview_p2_room.cpp.
Fresh arena command / run directory: py -3.12 -m experimental.pikmin2_king_natural_death_runtime run --assets <P1> --bank <bank> --output <dir> --exe <fixture.exe> -> king/ec2894c7...
Window setting / observed size and centring evidence: PIKMIN_P2_ROOM_WINDOW=960x540; native.log "Experimental preview window set to 960x540 windowed and centered".
Live starting Pikmin / no immediate extinction: P2_KING_NATDEATH_BASELINE red=32 other=0; no extinction screen.
PASS, FAIL, or BLOCKED; remaining work: PASS for the bounded natural combat->death gate. Material/BTK fidelity (#239/#128), campaign lifecycle, mixed-scene performance and reward/transport (lane 06) remain open.
```

## Scope boundary

This closes the natural combat -> lethal death arrow for the Emperor and labels
its remaining approximations (unit blow, 2/3 s interval, P1 per-color strength
out of scope). It does not complete the family: material/TEV/BTK fidelity
(#239/#128), the campaign lifecycle, mixed-scene performance and actual
reward/transport (lane 06) remain open.
