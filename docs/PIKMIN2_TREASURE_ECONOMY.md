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
