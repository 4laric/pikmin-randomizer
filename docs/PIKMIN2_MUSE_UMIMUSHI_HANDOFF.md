# Muse UmiMushi handoff - natural death/corpse + re-entry observer (shard, #374)

Worker: Muse Spark 1.3 (`opencode/muse-spark-1.3-contributor`, lane
shard-enemies-6-umimushi71-observer, generation 5). Implementation owner: Codex
through shared GitHub account `4laric`. Parent #167; family lane #374.
Slice target: 101 UmiMushiBlind (near-squad, staged in red-squad reach);
71 UmiMushi staged at the family arena default and recorded as still blocked.

## Scope result

Gate 4 (death/corpse) and gate 6 (cleanup/re-entry) are CLOSED for source
101 with a genuinely natural chain on a live bound actor. The stimulus is
the engine's own squad-vs-actor combat: the arena's 20 reds retaliate
against the near Blind Bloyster's flick/Eat and drain the native 800-HP
pool through the untouched family FSM, which raises `P2_UMIMUSHI_DEAD`
itself. The fixture writes no health, mode or attack state, and its only
staged action is ONE captain park outside every actor's 700-unit sight
radius (captain safety #632) - no throw path exists. Transfer/restore,
Beasts paths, nav strings and family modules are untouched.

Source 71 (the ordinary Bloyster at the family arena default x=120) stays
BLOCKED with fresh negative evidence: staged in red-squad reach
(x=-160), it drained 1455 -> 420 HP then stalled across 12000 ticks while
eating 10 attackers and flicking 21 more, surviving the observation
window. Its 1500-HP pool plus attacker removal outpaces a 20-red damage
budget; a non-red squad composition is the species-lane route (out of this
slice, per the #662 review's own framing). Gate 5 stays source-backed N/A
for both, and the #662 corpse/receipt registration gap remains a
family-owner change before any Pod receipt can exist.

## Source IDs

- Source ID: 101 `UmiMushiBlind`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | docs/PIKMIN2_UMIMUSHI_NATIVE.md gate table; death-run3/pass2 native.log:712 BIND 374006/101 re-observed | natural (preserved, not relabelled) |
| 2. Movement and animation | PASS (natural) | docs/PIKMIN2_UMIMUSHI_NATIVE.md gate table (blind walk/wait/move pacing) | natural (preserved) |
| 3. Attacks and receivers | PASS (natural) | docs/PIKMIN2_UMIMUSHI_NATIVE.md blind bite+eat (blind=1, scale 0.5, 800 HP); death-run3 BITE/EAT rows on 374006 | natural (preserved, re-exercised) |
| 4. Death and corpse | PASS (natural) | death-run3/pass1 native.log:1009 DEAD 374006/101, :1011 NATURAL_DEATH tick=538 hp_dropped=1, :1012 DEATH_POS ground plane, :1013 FUNNEL_DROVE, :1014 CORPSE_PRESENT engine_funnel | natural squad combat, zero substitutes |
| 5. Transport and reward | N/A | docs/PIKMIN2_UMIMUSHI_NATIVE.md: no verified source loot; no Pod receipt registration exists (#662 review) | source-backed N/A |
| 6. Cleanup and re-entry | PASS (natural stage boundary) | death-run3/pass2 native.log:865 REBOUND stale/fresh differ, single re-bind at :712 | natural rebirth |

- Source ID: 71 `UmiMushi`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | docs/PIKMIN2_UMIMUSHI_NATIVE.md gate table; death-run3/pass2 native.log:709 BIND 374004/71 re-observed | natural (preserved, not relabelled) |
| 2. Movement and animation | PASS (natural) | docs/PIKMIN2_UMIMUSHI_NATIVE.md gate table; live walk/attack/eat cycling observed | natural (preserved) |
| 3. Attacks and receivers | PASS (natural) | docs/PIKMIN2_UMIMUSHI_NATIVE.md natural walk/flick/attack/eat + bite receiver (frame 39) | natural (preserved) |
| 4. Death and corpse | BLOCKED | death-run4/pass1 native.log: HP 1455.0 -> 420.0 then stalled across 12000 ticks, 10 attackers eaten, 21 flicked; target survived the window | natural combat attempted, zero substitutes; no death claimed |
| 5. Transport and reward | N/A | docs/PIKMIN2_UMIMUSHI_NATIVE.md: no verified source loot; no Pod receipt registration exists (#662 review) | source-backed N/A |
| 6. Cleanup and re-entry | BLOCKED | gated on gate 4 for 71 (rebirth pass ran for the 101 target instead) | not run for 71; no claim |

Gate detail (pass1 `death-run3/pass1/565118a0.../native.log`, 1015 lines,
sha256 ce0d7b98516b2555aa5ee042d7b8f2c0dce7c1112dfefe55cfae2dd1b7be7d21):

- :864 `P2_UMIMUSHI_CAPTAIN_PARKED nx=600.000 ny=0.000 nz=1200.000
  reason=outside_all_sight` (single staged action; outside all 700-unit
  sight radii, so the guard never tripped: no `P2_FIXTURE_CAPTAIN_DOWN`).
- :880 starting squad 20; :917/:970 `P2_UMIMUSHI_VITALS` HP 470.0 -> 245.0
  (real combat drain, not a write); 23 engagement rows (EAT/FLICK/BITE).
- :1009 `P2_UMIMUSHI_DEAD generator=374006 source_id=101 health=0`;
  :1011 `NATURAL_DEATH tick=538 hp_dropped=1`;
  :1012 `DEATH_POS x=-109.01 y=0.00 z=1856.90 ground=-0.00` (on the
  practice-stage ground plane; fall/floating deaths are machine-rejected);
  :1013 driven engine funnel; :1014 bound corpse pellet;
  :1015 `PASS P2_UMIMUSHI_NATURAL_DEATH death1 gone1 squad_alive`, exit 0.
- pass2 :865 `REBOUND stale=0x1b20c5086f0 fresh=0x1f2a8a786f0` (differ),
  single re-bind, :866 `PASS P2_UMIMUSHI_REBIRTH rebound1 control_alive`,
  exit 0.

## Source IDs and files owned

- Native (worktree `.../prepared/umimushi71-observer-native`, branch
  `codex/shard-enemies-6-umimushi71-observer-native`, head `1c8299d6`):
  `tools/p2_muse_umimushi_fixture.cpp` (new, owned). `pc_port/pc_p2_umimushi.*`
  inspected only - the #662 review's additive corpse/receipt registration is
  a family-owner change and was NOT made here.
- Root (worktree `.../prepared/umimushi71-observer-root`, branch
  `codex/shard-enemies-6-umimushi71-observer`):
  `experimental/pikmin2_muse_umimushi.py` (new), `tests/test_pikmin2_muse_umimushi.py`
  (new, 19 passed), `docs/PIKMIN2_MUSE_UMIMUSHI_HANDOFF.md` (this file).

## Ordered commits (dirty: clean on both)

Root: observer/runner/tests/doc series (base `8ff3001e4e469cf9d33430e0ff769c15738270e3`);
native: fixture series (base `6a87eb2994b66355b05ce40bf3a8823884236299`), head `1c8299d6`.

## Interfaces / hooks touched

- None in shared engine code. The fixture observes the family FSM's own
  markers and drives the public `pcEscapeNow()` death-funnel helper once
  (the port suppresses doAI for family actors, so dieSoon never runs
  alone). Captain guard `p2_fixture_require_captain` (canonical
  `scripts/p2_fixture_captain_guard.h` sha256
  `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`,
  vendored) runs before every pause/movie return and observed tick.

## Build evidence

- Private build dir `output/umimushi71-build`, native base `6a87eb29`
  (fixture series head `1c8299d6`, clean); `pikmin_pc` linked,
  `ninja: no work to do.` dry run. Production exe `bin/nectar.exe` sha256
  `13aba5a65057c130043f24d5c92e0e3caf86213fcc4c65f8fd594639e83b1993`.
- Fixture `umimushi71-fx4` provenance `built` for head `939774e1`;
  `fixture.exe` sha256
  `fc663ef2128e3da4017e0339044c1528245238634b66e7d310775d26b74db54d`
  - the binary that produced the accepted death-run3 evidence.
- Fixture adoption: fresh arena via the current overlay (20-red starting
  squad), observed 960x540 centred startup, live room at ~30 fps, no
  immediate extinction; squad alive at PASS in both passes.
- Build-dir note: the launch-dir template path makes the provenanced link
  line exceed the Win32 32K limit (proven by a failed attempt, log kept);
  lane-private `output/umimushi71-build` + `output/umimushi71-fx*` used
  instead (same isolation guarantees, tadpole-lane precedent).

## Remaining work

- 71 death/cleanup: needs a squad composition with sufficient damage
  against a 1500-HP pool (species-lane scope), or a stronger natural
  stimulus; recorded with the fresh negative run.
- Gate 5 for both: the #662 review's additive corpse/receipt registration
  in `pc_p2_umimushi.cpp` (family-owner review required) before any
  `receipt=corpse:umimushi:` Pod credit can exist.