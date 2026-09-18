# ElecHiba source-22 admission pin audit (#816)

Owner: Codex through shared account 4laric. Read-only audit; no runtime,
build, manifest write or ADMIT. All six runtime gates UNTESTED.

## Verdict

ElecHiba (source id 22) is a **fixed hazard** (electrical wire), not an
actor. Its binding/admission path is the lane-22 hiba sidecar:

- `pc_port/pc_p2_hiba.h` — `pc_p2_hiba_setup`, `pc_p2_hiba_denki_hit_seen`,
  `pc_p2_hiba_denki_immune_seen`, `pc_p2_hiba_denki_lethal`, …
- `pc_port/pc_p2_hiba.cpp` — behavior implementation
- `pc_port/pc_p2_hiba_policy.h` — policy header

Present on the maintained wave (`claude/p2-deepseek-wave-native`); **absent
from `main`** (verified: `git cat-file -e main:pc_port/pc_p2_hiba.h` fails).
No `pc_p2_elechiba.*` file exists anywhere.

## Category finding

Elemental stimulus flows through the real Pikmin receivers the engine owns
(`InteractDenki` → `PIKISTATE_DenkiDying`, immunity via the lane-10/11
contracts), gated on `p2-hiba-native.txt` (absent file = inert, malformed =
fail closed). There is no actor bind/forget and no Onion receipt path, so
the ElecBug28 delivery-bridge pattern (`pc_p2_elecbug_setup` /
`pc_p2_elecbug_forget` + exactly-once `onion:p2:28`) is **inapplicable by
category**, not merely unimplemented. ElecBug28 receipt (#585) and gate-5
adjudication were consumed read-only and are not duplicated here.

## Producer / blocker

- Producer: lane-22 fixed-hazard line, issues #170 (OPEN backlog) and #447
  (OPEN child). No live registry lane owns either issue.
- Blocker: the hiba module is wave-only; it needs integrator landing, not a
  new family module. Shared generic providers stay read-only.

## First executable slice (named, not implemented)

ElecHiba denki-hit observation slice: a guarded fixture driving
`InteractDenki` hits through the hiba module in a staged arena, asserting
`denki_hit_seen` / `denki_immune_seen` markers under captain safety #632.
Reserve callsite `pc_port/pc_p2_hiba.cpp` plus a new fixture TU for build
membership; destination pins = current wave tips. Owned by the lane-22
owner or a new bounded lane; out of scope for this audit.

## Tests

`tests/test_pikmin2_elechiba22_pin_audit.py`: 10 tests (wave-header happy
path, malformed/missing-input refusal, bridge-applicability rule, record
shape). Run: `py -3.12 -m pytest tests/test_pikmin2_elechiba22_pin_audit.py -q`
from the private root worktree.
