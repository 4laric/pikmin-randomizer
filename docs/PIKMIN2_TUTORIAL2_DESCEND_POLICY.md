# Tutorial-2 descend policy (#757)

Lane `tutorial2-descend-policy-native`, issue #757 (OPEN). Implementation
owner: Codex through shared account 4laric. Coordinator blocked-producer
follow-up for stopped consumer `p2-cave-tutorial_2-p1-later-floors` (#747,
gen 2): floor-2 boot PASS proven, but floors 3-8 had no engine path (entry
admits 1-2 only; `pc_p2_cave.cpp` descends solely from floor 1).

## Wire (native worktree, base 93603dc2)

`native/pc_port/pc_p2_cave.cpp` (the shared entry header stays read-only):

1. Entry: `p2_tutorial2_entry_profile` admits `P2_CAVE_ENTRY_4` floors 3-8
   under the same 32-hex token contract as Tutorial 1-2 and routes them to
   the Tutorial path. All previously valid pairs behave identically; floor
   9+ stays Invalid.
2. Descend: `p2_tutorial_descends` — tutorial floors 1-7 transition
   downward (`BulbminDescendFloor`, "Descend" label); floor 8 exits
   terminal until the floor-9 follow-on. Beasts arms untouched.
3. Engine-emitted `P2_TUTORIAL2_DESCEND_POLICY floor=N descend=0/1` proves
   the decision in-band on every tutorial entry.
4. Non-aborting `pc_p2_tutorial2_entry_check` serves the fail-closed
   battery (same mapping + header rules, no engine state).

Native commits (branch `codex/autofill-tutorial2-descend-policy-native`):

- `f2c136b99760941e5cc6f3df765e054f935af4d5` entry/descend + fixture
- `eaabe9c816478b35b95e7fe8efe4de9a87096537` live-count WAIT lines

## Compiled evidence (private leased build `output/tutorial2-descend-build`)

- `ninja: no work to do.` (`ninja -n` exit 0).
- Engine `bin/nectar.exe` sha256
  `62e52cda0c825edf5c2ee7a9da7a3da54786a4cdb7918dfa4c5dd32af874fafe`.
- Fixture exe sha256
  `cdedd5042445d68bb0e2f34a2dd32d5b744bbfe1890a22ae47a41399326c00fb`
  (linked against the pikmin_pc graph minus `pc_main`; `nm` pattern per
  #732: production TU defines, fixture references).
- Symbol: `pc_p2_tutorial2_entry_check` strong-defined (`T`) in the
  production `pc_p2_cave.cpp` object.

## Runtime proof (`run-757/run-floor{3..8}/boot.log`)

Staging mirrors #747's floor-2 run (entry + arena + generate sidecars,
complete asset tree): `P2_CAVE_ENTRY_4 <token> N 1 8` + 8x `1 1`.

| Floor | Boot log sha256 (prefix) | Markers |
|---|---|---|
| 3 | 528f3b56 | READY floor=3 survivors=8, POLICY descend=1, PASS, no captain-down |
| 4 | 4d078ae1 | READY floor=4 survivors=8, POLICY descend=1, PASS, no captain-down |
| 5 | 6ad53577 | READY floor=5 survivors=8, POLICY descend=1, PASS, no captain-down |
| 6 | 386a0515 | READY floor=6 survivors=8, POLICY descend=1, PASS, no captain-down |
| 7 | 565a8306 | READY floor=7 survivors=8, POLICY descend=1, PASS, no captain-down |
| 8 | b6340cb5 | READY floor=8 survivors=8, POLICY descend=0, PASS, no captain-down |

Entry battery: `--check-entry` admits floor 5 (exit 0), refuses floor 9
(exit 1). Guard self-test 7/7 + negative exit 86 re-verified.

Two staging facts recorded for the consumer: (1) the room yields 8 live
Piki at setup in the current tip (stable over 8400 ticks), so entries
carry count 8; #747's historical floor-2 count of 20 predates the
Bulbmin-mother ordering fix (wild births no longer perturb the count).
(2) The cave run-asset tree must be complete (47 files incl.
`dataDir/consFont.bti` were missing from the old tree and crashed boot
before room preview).

Guard adoption: #632 vendored truth table + self-test in the fixture;
observation-only, captain parked by the room scenario (no captain-damage
claim). Guard `scripts/p2_fixture_captain_guard.h` sha256 `d2f678c9…3c3474`.
Gates UNTESTED except observed boots. Floor-9 cargo + persistence are
follow-ons. No other edits; no ADMIT.

## Handoff

Downstream consumer `p2-cave-tutorial_2-p1-later-floors` (#747): floors
3-8 now have an engine entry + descend path with boot proof above; stage
`P2_CAVE_ENTRY_4` entries with count 8.
