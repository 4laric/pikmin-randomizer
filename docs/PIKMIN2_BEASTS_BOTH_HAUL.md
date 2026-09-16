# Both floor3 source treasures (#371)

Codex owns this diagnostic fixture using the shared 4laric account. Both frozen
source treasures are installed simultaneously: green generator63000 at
(-85,0,-960), value150/weight12/slots20, and donut63001 at
(175,20.5,-55), value230/weight15/slots25. Each model and source plan is
hash-bound to the existing assembly/package. The shared Pod is (-85,0,-280).
No source anchor, route, geometry or physics settings are changed.

The native multiple-cargo registry already assigns separate private configs
and model shapes. The fixture checks distinct actor/config pointers and both
carry settings. It restores20 Red Pikmin, assigns green Transport, waits for
native delivery and crew detachment, then uses Formation mode and controller
walking to approach the donut before assigning its remaining carriers.
The five engineering walking goals are (-85,-120),(-85,85),(150,0),(150,-55),
(175,-55). They are controller destinations, not invented cargo route links.
Natural already-attached carriers are retained only when alive Red Pikmin in
Transport mode on that exact donut; other attachments are rejected.

Two actual P2_POD_RECEIPT events and the exact sorted two-row economy prove
both collections. The legacy treasure-receipt.txt only tracks the first
preview cargo, so it is used solely to observe green completion. Completion
is detected before any further cargo dereference, then that pointer is nulled.
Same-process duplicate tests use native P2Economy reopen/credit and require
false without changing the receipt ledger; killed actors are not redelivered.

After green delivery the fixture copies the actual150-Poko economy bytes to
partial-economy.txt. A fresh process can seed that exact snapshot and physically
rehaul both respawned source treasures: green must credit0 and donut230,
ending at380. This restores economy only, not a persistent world or campaign.
The20-member roster, actor placement and world are deliberately restaged.

## Limits and evidence

Native source/build remain frozen at e0418c798e808bd1b29217532ebb36f4f0d89406
from#365. The external fixture links the completed private build; no native
production change or shared build was needed. Both use donor pellet physics;
the donut source visual/economy does not implement its source radius50/height5.
Scripted assignment, formation and captain controller are engineering
interventions. Physical trace endpoints and carrier counts do not certify
exact native waypoint choices or general clearance. No terminal opt-in marker,
campaign rewards, successful descent, enemies or full floor3 completion.

The initial run1a0d29506115429bbd835dc501664431 delivered green and walked
all five captain goals, then failed the fixture's blanket no-attachment guard.
It remains preserved under output/both371/runs. The revised guard observes
and preserves valid same-target Transport attachments instead of resetting
native actions. Captured successful outcomes and review are recorded below.

## Captured runs and reproduction

Private evidence is under output/both371 in the owning
output/p2-beasts-both-haul worktree.

First successful run4325179c03a646a4bb81c75a950c3d39 passed with36 green
and33 donut trace points, peak20 carriers for each, exact native events
150/new1 then230/new1, and final380. Nineteen Pikmin naturally attached to
the donut before the final assignment; each read back same_target1,
TransportMode9/action21. Their existing actions were preserved.

The actual captured partial150 ledger SHA256 is
530496e73e288c54695be73e05568441b8707acf345d020d8dc0e5a22b11b344.
The final exact380 ledger SHA256 is
71e1c489271e826dffa8df66eacf47f3d216ce529ef3dce3bf4cb1f57b595155.
Executable linked2/fixture.exe SHA256 is
2503557c90985b85003735b030f2de32b1f6b17c04a3e1ce2b2f4aa3ed0977b6.

Use pikmin2_beasts_both_haul.stage with both frozen plan paths, assembly,
source package, base assets and a caller diagnostic token. Generate the
external fixture with fixture(), link against clean e0418c79 through
scripts.build_pikmin2_fixture, and call run(). For the supported partial
restart pass the first run's actual partial-economy.txt as initial_ledger.
The fixture has a10000-tick bound and the host a360-second wall timeout.
No all-credited380 restart mode is claimed by this stage.

Eleven Python tests and62 subtests pass, covering exact receipts/ledger bytes,
partial credit semantics, distinct phase markers, roster, physical traces,
and inherited donut/green/ground acceptance. Native source needed no rebuild
or changes. Independent review verified first-run hashes/receipt semantics,
the partial snapshot binding, and the guarded natural-attachment behavior.

Fresh-process partial restart `86ee1673c2554f4bbc1fb41767ba1247` passed:
36 green and32 donut trace points, peak20 for each. The actual green Pod
event credited0; donut credited230, leaving the exact same380 ledger as the
first successful run. All stage/log/executable/economy hashes and the captured
partial-to-restart binding were revalidated in output/both371/verification.json.
Independent final review also verified the partial restart's log/input/economy
hashes and exact green/new0 then donut/new1 receipt sequence. No review blocker
remains for this diagnostic economy restart scope.
