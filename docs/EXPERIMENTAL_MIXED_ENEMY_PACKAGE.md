# Experimental P1 and admitted P2 enemies

This package carries Python installers and a pinned admission catalog, not game
assets. Use your own extracted Pikmin 1 assets and prepared Pikmin 2 content.
The experimental enemy pool uses the release's pinned admission catalog. The
`playable` and `all` choices select that admitted set; the legacy `full` choice
also includes model proxies and is not the admitted-only release choice.

Prepare the identity-keyed content folder from your own extracted Pikmin 2
files with `scripts/p2_prepare_content.py --help`. That command documents the
source members and converters. Keep its output outside the release directory.
A raw ISO or an ordinary Pikmin 1 assets folder is not a prepared P2 content
folder. Do not download or share converted game assets.

In the launcher, enter the prepared P2 content folder or an existing verified
content manifest JSON. From a terminal, use:

```text
Play.cmd --console seed.json --p2-content "D:\Games\My P2 content"
Play.cmd --console seed.json --content-manifest "D:\Games\My content manifest.json"
```

Use one of those inputs. The same flags work with the window launcher. P1-only
seeds do not require P2 content. The runner checks chosen-family coverage and
content identities/hashes, stages a private asset tree and refuses missing or
invalid content before native gameplay. The matching native executable must
support the seed's declared capabilities; a launcher cannot bypass that check.

Package import/generation tests are source checks. The evidence below supports
an experimental solo playtest release. Full gameplay qualification also requires
ordinary mixed-enemy combat, enemy checks and item receipts on the exact
candidate, alongside native save, fresh resume and reconnect.

## Experimental release candidate notes

`examples/ExperimentalP2Enemies.yaml` opts a normal P1 Archipelago campaign into
combined P1 and admitted P2 enemy randomization. It uses `p2_enemy_pool: all`,
`p2_density: sampled`, and an empty `p2_species` list to keep the full pinned
cohort eligible. Placement still respects compatible slots and arenas; a seed
does not need to place every eligible species. The generated manifest preserves
the exact chosen enemies and resolved check catalog for that session.

The default remains P1-only. Use the experimental sample unchanged for release
qualification; do not narrow its species list to make a failing installation
or encounter pass. Prepared content must cover every selected identity.

Linux qualification of the candidate APWorld passed 15 actual loader,
generation and restrictive-fill runs, including the unchanged sample at three
seeds, repeat generation, and default-versus-disabled regression. Checks were
filled and reachable through item collection; repeated manifests and catalogs
matched. These results establish generation correctness, not playable status.
The detailed source and artifact hashes are recorded on issue #1153.

Ordinary Linux launches use the production CLI (the Windows HUD is not available):

```text
python -m randomizer run /absolute/path/Player1.pikmin.json --session-dir /absolute/path/new-session --exe /absolute/path/nectar --assets /absolute/path/p1-assets --p2-content /absolute/path/prepared-p2 --server localhost:38281
```

Run from the matching release source directory, with its Python dependencies.
The server must host the multidata generated alongside that exact player
manifest. Choose a fresh private session for the first test; later resume and
reconnect tests must reuse it and the same server save. Keep older player saves
and installations untouched. Asset staging and its cache need additional free
disk space beyond the prepared-content directory.

The unchanged experimental sample at seed `1153` has these observed results:

- Full selected-family content staging and cache validation passed. The generated
  seed has 78 P2 bindings and 42 distinct admitted species, combined with its
  resolved P1 campaign. Eligibility does not imply every species appeared in
  the tested area.
- The real Forest of Hope scene rendered. P2 actors initialized and moved
  naturally, and ordinary keyboard input moved the captain and produced punches.
- A native population check reached the real AP server. Its location, received
  item and AP identity persisted across restart.
- Ordinary pause, **Go to Sunset**, diary/summary confirmations and **Save**
  produced `CAMPAIGN_SAVED generation=1`, a native card file and a campaign
  checkpoint. A fresh process loaded that unchanged checkpoint, displayed day 3
  (`CAMPAIGN_RESUMED day=3`) and rejoined the saved AP room.

The qualified Linux executable SHA-256 is
`800bc863f1cbb9437c9da4dfdc7d0df7d30cfddd4628dbcf5f92185ff7f117f6`
(native source `92b77add2baaa99af6d437c6820e0e396609837c`). The player manifest
fingerprint is
`2ae2ec6d57a2a1cefdac488daf9056a42a48e83edb8a79905532f13f61bc0ccd`.
The mixed-journal restart fix is included through PR #1208. Exact seed, APWorld,
YAML, card and checkpoint hashes, raw logs and screenshot evidence are recorded
in [the #1153 qualification report](https://github.com/4laric/pikmin-randomizer/issues/1153#issuecomment-5964832141).

**Limits:** ordinary enemy combat and corpse delivery/check receipts have not
been accepted in this combined-seed run. This is not certification of all
admitted families' behavior or co-op support. Three absent ship-part animation
clips are a P1 baseline metadata/bundle limitation; native substitutes dummy
animations. The existing player installation and saves were preserved.

For the remaining combat playtest, start the generated seed normally, encounter
both a P1 and a P2 enemy, and earn their actual manifest check IDs through the required
delivery or defeat. Save normally, exit and resume, then reconnect the client
and restart the server using its existing save. Verify enemy identities and
progress persist without duplicate awards. Synthetic events, forced deaths,
and startup logs do not satisfy these checks.
