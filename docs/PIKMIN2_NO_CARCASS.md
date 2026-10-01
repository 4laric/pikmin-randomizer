# P2 deaths without carcasses (#1088)

Owner ruling, 2026-10-01: "nah get rid of the jellyfloat corpses and the larva
corpses let's stay P2-accurate". The owner extended this to Man-at-Legs and
Raging Long Legs with "yeah thanks".

Sources 31 (Bulborb Larva), 57 (Lesser Spotted Jellyfloat), 66 (Man-at-Legs),
69 (Raging Long Legs), and 72 (Greater Spotted Jellyfloat) leave no carcass.
They finish their source death animation/burst, then vanish. Their randomizer
check is earned on the kill instead of Onion delivery. They produce no Pikmin
seeds. Randomizer logic does not depend on corpse seed yield.

New resolved catalogs use `event=defeat`, `carry_min=1` for these five sources.
The three-Onion and stage-access requirements remain. Legacy saved catalogs
retain their snapshot event and carry values. AP names (`Bestiary: Deliver P2 …`)
and source-based location IDs stay stable for compatibility, despite the older
display wording.

Native kill and corpse paths share a seed-stable durable receipt ledger and
consume the same actor binding. The AP check is persisted before the secondary
ledger. A leftover corpse path cannot award a second check. The ledger identity
remains `onion:p2:<source>:<stage>`; a kill uses the encounter tag `kill` and marker
`P2_KILL_P2_RECEIPT`.

The teardown hook uses the canonical `PelletView*` binding address, not the
distinct `BTeki*` subobject address. It tests the raw host Alive option cleared
by `dieSoon`, preserving compatibility with #1064's earlier combat rejection.
Live day-end/slot-reuse teardown earns no kill receipt.

P2 decompilation references (revision
`632af93787b9c95b63f0c13be32b161375ce3a96`, `src/plugProjectNishimuraU`):

| Source | No-carcass flag | Death endpoint |
| --- | --- | --- |
| 31 | Baby.cpp:40 | BabyState.cpp:25–44; 56–80, kill at dead/deadpress END |
| 57 | Kurage.cpp:36 | KurageState.cpp:61–86, key 3 burst; END kill |
| 66 | Houdai.cpp:71 | HoudaiState.cpp:32–63, END explosion and kill |
| 69 | BigFoot.cpp:69 | BigFootState.cpp:30–60, item event then kill |
| 72 | OniKurage.cpp:46 | OniKurageState.cpp:80–91, key 3 burst; END kill |

Larva's chance nectar drop (`Baby.cpp:286–300`) and Raging Long Legs' Mitite
spawn (`BigFoot.cpp:661–672`, 30 when no treasure) remain unimplemented and
outside this issue's scope. The port's long-legs birth marker is not a spawn.

Historical corpse transport claims in the roster and playable-pool report
predate the ruling. The evidence roster preserves each complete historical
`delivery_receipt` citation and records the new endpoint separately as
`kill_receipt`. Source 66 retains its original `onion:p2:66:3` admission; the
new stage-1 kill receipt does not overwrite it. Current validation and its
limitations are recorded below.

Implementation owner: Codex through shared GitHub account 4laric, continuing
Claude's committed native WIP without squashing it. Shared checkout and
maintained build/export are unchanged. Native and root PRs remain draft.

## Current validation

Native candidate `d703218cae578376338fd292aed8477949a661b4` is clean in
`output/native-smooth-jelly`, branch `claude/p2-no-carcass-kill`. It retains the
inherited WIP `ee1ba8b9d` and merges current fork/main before final validation.
Private Ninja/MinGW build `output/native-smooth-jelly-build`, `-j2`, passes with
no work in the dry run. Production executable SHA-256:
`5209860aacee5e6301de2cd066efc57062c8529aff08723f488692fdd370bdb6`.

235 Python tests and 27 subtests pass, including `test_p2_rfix_cli.py`, current
pool/placement/roster, family reward tests, smoke seed tests, and the paired
native IPC probe. For all five IDs, both kill-first and corpse-first receipt
orderings earn one durable AP check; replay after process/session recreation
writes no second check. This is engine-free IPC evidence, separate from combat.
Five focused native ctests pass: no-carcass policy, Kurage bank and non-campaign
transport, Queen own FSM, and long-legs FSM.

Each fresh campaign run uses autoplay power x30 and a test-only initial squad/
captain teleport. Damage comes through existing combat receivers; enemy health/death
state is not injected. These are accelerated bot fights, not normal player
combat acceptance. All five runs show death/animation completion, vanish, no
carcass markers, `P2_NO_CARCASS`, `P2_NO_CARCASS_KILL receipt=1`, and exactly one
`P2_KILL_P2_RECEIPT new=1` for the target. Frame dumps are retained per run.

| Source | Own generator | Runtime evidence | Outcome |
| --- | --- | --- | --- |
| 31 | 4222852521 | `output/codex-1088-death-31-2/{run-inputs.json,native.log,run-result.json,frames/}` | PASS |
| 57 | 4222852521 | `output/codex-1088-death-57-2/{run-inputs.json,native.log,run-result.json,frames/}` | PASS |
| 66 | 4222852521 | `output/codex-1088-death-66-2/{run-inputs.json,native.log,run-result.json,frames/}` | PASS |
| 69 | 4222852521 | `output/codex-1088-death-69-2/{run-inputs.json,native.log,run-result.json,frames/}` | PASS |
| 72 | 2049888785 | `output/codex-1088-death-72-2/{run-inputs.json,native.log,run-result.json,frames/}` | PASS |

Death bursts/explosions use the port's existing P1 wave/glow/smoke stand-ins,
not exact retail particle reproduction. Sparse frame dumps support observation;
source FSM events and final receipt logs establish the death endpoint.

All four packages (`output/smoke-smooth-jellyfloat`, `output/smoke-larva`,
`output/smoke-man-at-legs`, `output/smoke-smooth-longlegs`) are rebuilt with the
same seed labels and UID placements, current dense cache, the candidate binary,
and resolved P2 checks. Independent bounded verification passes at the original
1100-unit limit, with every requested slot bound. Previous inputs are preserved
in `output/codex-1088-<package>-previous`; owner's existing `session-*` folders
are untouched. Evidence: `output/codex-1088-package-verification.json` and
`output/codex-1088-package-install.json`. Run each package with PowerShell:

```powershell
& .\output\smoke-smooth-jellyfloat\play.ps1
& .\output\smoke-larva\play.ps1
& .\output\smoke-man-at-legs\play.ps1
& .\output\smoke-smooth-longlegs\play.ps1
```

Historical baseline adoption on the final native candidate: fresh
`output/codex-1088-baseline-arena2` via current root overlay and
`ensure_pikmin_squad`. The unprotected custom startup reports 960x540 client,
position (373,263), display (0,0,1707,1067), 20 live reds, captain HP100, Walk
and five active frames without extinction. Bounded runner passes in 11.656sec.
The old forced captain-down test exits raw86 before SDL/engine startup; it
proves helper refusal only, not in-engine guard ordering. Baseline fixture SHA-256:
`b2c70da0b95354805f04656f54817abf3d6e056ea41b43a9a44bf50c44b6514b`;
provenance status built in `output/codex-1088-baseline-build2/provenance.json`.
Inputs/log/result are in the fresh arena; negative evidence is
`output/codex-1088-baseline-negative2.{json,log}`.

Earlier diagnostic attempts are preserved: x10 Man-at-Legs did not finish
within 180sec; the first mixed Jellyfloat run completed death/receipts but still
had obsolete startup corpse-readiness markers. A report encoding/import error
was recovered from intact logs after safe child teardown. One build failed
because its output executable was still running; rebuilding after that owned
run stopped passes. No failed attempt is counted as acceptance.

Six-gate scope: identity/spawn, death/no-carcass, and kill reward PASS for this
bounded smoke slice; comprehensive movement, normal combat/receivers and full
cleanup/re-entry remain UNTESTED here. Ledger replay is covered by the probe,
not a full campaign-resume run. Shared hooks require integration review through
#186, including reconciliation with #1064. `PIKMIN2_PLAYABLE_POOL.md` remains
owned by unfinished lane p2-start-fix-882; this report and the current seed/
roster evidence supersede its historical corpse descriptions. Generated roster
identity JSON is unchanged because no source identity changed.

## Resumed validation after #1064 integration

The complete historical delivery citations for all five species are restored,
with current kill evidence stored separately. The unrelated source-79/source-66
preservation regression is unchanged. The root CI slice passes 450 tests and
55 subtests (14 skipped, one deselected); both fixed-seed generation pairs are
byte-identical. The additional focused roster/receipt checks pass 31 tests.

A new external `output/codex-1088-baseline-v2.cpp` corrects the inherited guard
ordering. Immediately after engine idle it checks both initialized captain
slots before null-manager/state, movie/UI and readiness returns, and blocks
unexpected initialized-captain disappearance. Positive observation is
unprotected. It is built against the unchanged clean native candidate d703218
in `output/codex-1088-baseline-v2-build1` with recorded built provenance and
no-work Ninja checks, using the canonical exclusive build lease.

Fresh regenerated arenas `output/codex-1088-baseline-v2-positive-arena1`,
`output/codex-1088-baseline-v2-health-arena1` and
`output/codex-1088-baseline-v2-missing-arena1` use the same executable and
60-second supervisors. Positive startup observes 20 live Reds, HP100, five
active frames and a centred 960x540 window, exiting 0. Both negatives initialize
the actual captain in-engine at tick 3 before injecting zero HP or hiding its
observation pointer; each exits 86 without a PASS marker. Raw negative run
results remain interrupted/failed; separate checks verify the expected refusal.
These are fixture instrumentation tests, not natural damage or species combat.
Prior sources, runs and logs remain preserved.
