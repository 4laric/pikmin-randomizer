# Campaign treasure economy (#1232)

Implementation owner: Codex through shared GitHub account `4laric`.

Near the ship, an enabled White retail campaign now shows accepted Pokos, debt
remaining, and unique Hoard progress in the existing native ship window title.
It reads the #1191 diamond provider's in-memory state, which is saved/restored
through its authenticated native-card generation. It does not commit an
independent economy file. Ordinary ship withdrawal/deposit controls are retained.

For the currently wired original `dia_a_red` provider, delivery shows **180 Pokos,
Debt 9820, Hoard 1/201**. Repeating the view, depositing Pikmin, and loading the
same committed card do not add another reward. Catalog membership grants nothing.
Missing or modified catalog data displays **Catalog not staged**, while retaining
the proven provider's Pokos/debt display. Relaunch after staging a valid catalog;
the file is intentionally loaded once at first ship observation.

## Source catalog

Reuse #140's `experimental.pikmin2_treasure_ledger`: its loaded-generator-count
rules and cave/enemy-held/boss-drop references classify all 201 GPVE01 revision 0
entries as campaign collectibles. Mode references overlap those entries, rather
than becoming additional collectibles. The catalog includes source ID, pellet
kind/index, dictionary slot, classification, uniqueness, value, minimum carry
strength, physical slots, and source code flags. Strength may exceed slot count.
Source catalog presence does not establish actor, model, digging or carry support.

Generate numeric metadata into a **new private ignored directory**:

```powershell
py -3.12 -m experimental.pikmin2_treasure_catalog --iso "C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso" --output output/economy-catalog-1232
```

The manifest digest is
`f0f9c1f60953f63b5460037e5bf276193172f526b869f7642b97d44a0704d751`.
The native loader requires this exact complete catalog, bounds input at 32 KiB,
and rejects corruption before publishing parsed state. Models, raw config bytes,
translated names and generated catalog reports stay private. The public change
contains tooling, synthetic controls and the manifest digest.

## Direct gameplay acceptance

Use an existing isolated White/Purple/diamond manifest and its explicit legal
banks. The wrapper delegates to the ordinary runner, creates its normal fresh run
token, and passes the verified catalog path through an environment variable.
It does not edit a seed, repair a card or inject a collection.

```powershell
py -3.12 scripts/play_p2_economy.py --catalog output/economy-catalog-1232/p2-treasure-catalog.txt -- output/white-session/manifest.json --session-dir output/white-session --exe <qualified-pikmin_pc.exe> --assets <private-baseline-assets> --purple-bank <private-purple-bank> --purple-motion <private-purple-motion> --white-bank <private-white-bank> --white-treasure-bank <private-diamond-bank>
```

1. Verify the current 20-Pikmin starting fixture, native 960x540 centered window,
   and active living captain. Stay within the genuine campaign provider; preview
   Pod/corpse or AP rewards are excluded from this view.
2. Near the ship before collection, observe `0 Pokos | Debt 10000 | Hoard 0/201`.
   Acquire the original fifteen natural Whites through the source Ivory budgets,
   pluck them normally, and physically carry the unmodified 15..25/180 diamond
   through native suction. These are #1191's ordinary mechanic gates.
3. Return near the ship. Observe `180 Pokos | Debt 9820 | Hoard 1/201`; use
   Ctrl+F10 for species, Shift+F10 to deposit eligible nearby squad Pikmin, and
   F10 to withdraw. Repeated controls/observations must retain the same economy.
4. End the day and complete the visible native SAVE flow. Close normally and
   relaunch the same private session with a fresh native process through the same
   command. Select the saved course through ordinary map controls. Near the ship,
   confirm 180/9820/1; verify consumed diamond and usable saved White stock.
   Keep full native logs/card generation and hash/window evidence under `output/`.

Prior #1191 actual 74/75 delivery/SAVE/fresh-resume evidence is component evidence
for the reused provider. It does **not** establish a new 1232 ship-title gameplay
pass, nor does this recipe imply one has occurred. A normal fresh seed uses
engineering supply placement; imported retail campaign geometry remains separate.

## Validation and remaining work

Python controls exercise deterministic projection, source/count/classification
and numeric refusal, duplicate IDs/dictionary/index, oversize/tampered input and
ordinary launcher delegation. Native controls exercise receipt identity/value
refusal, modes excluded from currency/Hoard, unique deduplication, 9999/10000 debt
boundary, post-debt Treasure Hunt/full-set policy, empty-catalog refusal, and
transactional parsing. A local native control run also verified all 201 real
numeric profiles and rejected a changed diamond value.

`p2economy::CollectionView` is a read-only reconstruction API. Its synthetic
controls do not prove ordinary delivery. Only the existing diamond receipt is
wired into production here; no new persistent ledger or ending engine transition
is introduced. #1232 stays open for the remaining ordinary source collectors,
unified surface/cave receipt and save coverage, actual 10000-Poko crossing,
post-debt/full-Hoard ending progression, current whole-engine gameplay acceptance
and full-campaign human sign-off. Existing cave/SAVE/provider owners retain scope.
# Source-bound collector continuation (#1232)

The general collector adds a 201-bit unique receipt snapshot (`P2TR1`, exactly
188 bytes) inside the campaign owner's authenticated native card. It has no
standalone file persistence. Production callers must verify the pinned retail
catalog, bind the selected placement digest and authenticate the enclosing card
before restoring. White's existing diamond record remains its own authority;
the displayed economy unions both sources by treasure ID.

`randomizer.campaign_treasures.prepare` builds private generator/model inputs
from explicit engineering positions. `experimental.pikmin2_campaign_treasures`
converts any explicitly selected catalog models from the user's legal ISO. The
helpers return data without activating a campaign or changing installed assets.
The caller must check reserved UID collisions in every scheduled generator file
and bind the exact descriptor digest through explicit seed/session activation.

The bounded `P2_TREASURE_PLACEMENTS_1` descriptor contains the pinned catalog
digest, converted Pod model hash and row count. Each row contains stage, cargo
UID, receiver UID, catalog ID, converted model hash and final `default.gen` hash.
The native surface provider routes only these actual cargo actors to their
bound receiver. Receipt occurs at completed native suction, suppressing native
P1 seed/repair rewards for that cargo. On authenticated resume, collected source
actors are removed during reconstruction. Changed actor identity, profiles,
receiver, models or generator bytes are refused. White cargo IDs cannot alias
general treasure IDs; a shared receiver requires the identical verified model.

Current limits: the new provider uses native physical pellet hosts and explicit
engineering positions on surface stages 0–4. It does not implement the full
retail placement map, source collision geometry, enemy-held drops or cave-floor
actor lifecycle. Cave entry preserves the receipt state and leaves actor
ownership with the cave provider. Ship debt/hoard phase is a projection; actual
debt-crossing cinematics and ending transitions remain open.

Before gameplay acceptance, compose the campaign owner's explicit activation,
optional authenticated SAVE record and source getter, then build that exact
source. Run a fresh private 20-Pikmin, centred 960×540 ordinary campaign:

1. Reach each explicitly staged treasure with a living captain. Carry it using
   the actual catalog minimum and show arrival, native suction and one receipt.
2. Confirm its Pokos and unique count appear at the ship, with no P1 repair or
   Onion seed reward. Leave unrelated pellets/corpses on their ordinary paths.
3. Complete the native day-boundary SAVE. Exit the process and launch a fresh
   process from that same authenticated card. Confirm consumed cargo stays
   absent and total/unique state survives without another receipt.
4. Test changed generator/model/descriptor refusal using separate private runs;
   preserve failure logs. Natural debt crossing and all-201 completion require
   actual collection evidence before claiming ending acceptance.

Synthetic codec/descriptor controls and successful model extraction do not
qualify ordinary carrying, native SAVE or endings.

## Literal held-drop continuation

`randomizer.held_treasures.prepare` binds a `P2_TREASURE_HELD_1` descriptor to
unchanged original `P2OC1` and typed Onyon manifests, selected campaign, actual
enemy UID/source/treasure code and original converted models. It returns private
data without activating the campaign. Runtime repeats the native source parser
checks and requires the campaign owner's authenticated `TREASURE_SOURCE` binding.
The first targeted literal is tutorial `initgen.txt#17`, source 33, code 841:
`watch`, dictionary 87, 110 Pokos, carry strength 30 and 40 physical slots. The
receiver is the original typed ship at tutorial `defaultgen.txt#0`, not an
engineering Onion. Neither source generator nor its held code is replaced.

The native held provider preflights models before enemy birth, emits actual cargo
through the original death/drop path, and grants a unique receipt only after
completed native ship suction. Pending released cargo is a physical graph, not
a collection bit: course teardown and SAVE must refuse it until that graph has
an authenticated restore implementation. This guard is a development limitation;
it does not establish ordinary pending-cargo persistence or course-exit acceptance.

Atlas (`map01`, item index 10, dictionary 184) is a loose treasure on Emergence
Cave floor 2. Projection Sphere (`map02`, item index 11, dictionary 185) is a loose
surface source at `forest/initgen.txt#16`. Both catalogue profiles are 200 Pokos,
101 carry strength and 101 slots. Neither placement qualifies for the original
boss-held/story/cave/last-floor squad-weight adjustment. Preserve their weights
and require actual Purple carrying strength; floor context alone cannot lower
a loose treasure's weight. Collection must produce the equipment owner's normal
map unlock, followed by native SAVE and fresh-process verification.

Held native commit `9a2aaba90e218bfea4cd2c45f1c73bfd51cdfcdf` passed all three
hosted focused CTests and a no-work Ninja check. These are codec/descriptor checks,
not a production compile or a death/carry/save/resume gameplay result.

The private model extractor now emits schema 2 banks. It verifies the literal
GPVE01 item and otakara configuration hashes before creating output, compares
dictionary/value/minimum/maximum with the pinned catalogue, and retains original
configuration and archive bytes alongside member and converted-model hashes.
Each selected treasure includes its original radius, carry radius, height,
inertia scaling, friction and dynamics mode. These are inputs for the original
cargo provider; extraction does not activate it or establish collision fidelity.
The held provider no longer renders a cave Pod model as the surface Ship. Actual
Ship type 4 uses original object bank 2 and requires its own source provider.
