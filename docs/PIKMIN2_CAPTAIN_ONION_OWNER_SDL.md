# Offline switched-captain Onion ownership (#1166)

Implementation owner: Codex through shared GitHub account `4laric`.
This is a separate fixture derived from #1130. The #1157 fixture and evidence
remain unchanged. Preparation is not runtime acceptance.

The fixture uses one real SDL virtual controller assigned to player 1, with
player 2 unassigned. It switches the selected captain through D-pad Up. This
does not exercise the independent player-2 channel or online co-op. Those paths
remain with #1148 and captain UX #1133.

## Ordinary input sequence and assertions

1. Fresh campaign: observe production startup's 20 live red Pikmin from actual
   Onion stock, both healthy captains, and slot-0 formation/count agreement.
2. Walk slot 0 to the actual Onion, open its ordinary menu, select a squad of
   zero, confirm, and wait for 0 live / 20 stored. No stock or ownership writes.
3. Switch to slot 1 through SDL, walk to the Onion, select a squad of 20 in its
   menu, confirm, and wait for 20 live / 0 stored.
4. Count live `Piki` objects in Formation mode with `mNavi` equal to captain 1.
   Require all 20 to match, captain 0 to own none, and both CPlate used-slot
   counts to agree. Check this continuously during the following controls.
5. Switch to slot 0 and back to slot 1 through ordinary SDL edges; verify camera
   binding and preserved formation ownership. Observe actual slot-1 Gather
   state after a whistle. These observation-gated controls replace the older
   100-tick movement demonstration. Walking to the Onion is the movement used
   here; this gate does not claim a separate inactive movement oracle.
6. Open the ordinary pause menu, choose Sunset, and complete native diary,
   results, and card dialogs. Require generation 1 and the native day increment.
7. Two independent processes load that exact committed card and start with
   native stored stock. Each switches to slot 1, withdraws through the ordinary
   menu, and repeats formation/switch/whistle assertions. Card hashes, day,
   total population, checks, and rewards must remain unchanged.

Original practice generator assets are preserved in every phase. The window
must be observed as 960×540 and centred after settings load. Guards run before
and after engine updates, before all early returns. Four separate negatives
cover active health, inactive health, initialized null state, and missing
manager; each must exit 86 without PASS. Only negative controls inject damage
or missing state.

## Timing and current limitation

Every child has the unchanged 60-second wall-clock limit, plus finite fixture
stage bounds. Stage receipts record elapsed monotonic time for initial stock,
deposit, switch, withdrawal, formation, controls, and native save. Historical
#1130 saves took approximately 57 seconds, leaving insufficient demonstrated
slack for deposit plus withdrawal. No whole-sequence timing claim is made yet.

The PC-only const observer reports input eligibility from the actual result
window, only during DiaryMessage and the message's ActiveDisplay state with
input enabled. The fixture sends an ordinary SDL B edge to reveal a page and
an A edge to advance a revealed page, followed by a neutral frame. When
eligibility is unavailable, the existing ordinary A cadence serves fades and
results/card prompts; it never emits B there. Observer/action changes are logged.
There is no clock change, message state write, direct reveal/update call, or
direct card writer invocation.

The engine-free test exercises eligibility boundaries and verifies unavailable
outer gates do not invoke inner readers. Explicit checks and static assertions
remain effective under Release/NDEBUG. It does not instantiate real UI objects;
production compilation, source review, and actual UI runtime remain necessary.

## Source and execution boundary

Base root: `36ac5ddd2877b9308276f96b28a81e137ae58c5a`.
Base native: `67f91ef9a9d3a8fec9f7ae84a653321fe153c893`.
Private branches: `codex/captain-onion-1166` in separate root/native worktrees.
The supported editing agreement also claims the five read-only observer files
and new engine-free test. It retains both primary integration and radar producer
claims and evidence. The shared #1157 fixture remains outside this claim.

The runner preserves the reviewed #1157 runtime-directory hashes and environment
scrub in its own file, with additional mandatory ownership markers. Build and
runtime remain pending matched #1157 packaging and independently reviewed source.
No full campaign, persisted squad ownership, or human gameplay claim follows
from this bounded test: ownership is freshly established by real withdrawal
after loading native stock.
