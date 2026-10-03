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

Package import/generation tests are source checks. Public release readiness also
requires a real AP fill and packaged mixed-enemy gameplay, normal checks and
item receipts, day-end save, fresh resume and reconnect on the exact candidate.
Those gameplay gates are not established by this package change.

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

This candidate is **not yet gameplay-qualified**. The full-pool Linux installer
attempt passed source-file verification but stopped when its disk filled;
complete staging, actual admitted P2 births in mixed scenes, ordinary combat
and real AP checks remain to be observed. Native day-end save, fresh resume,
and client/server reconnect also remain unverified for the exact packaged seed.
Do not advertise co-op support based on this solo release test.

For the direct smoke, start the generated seed normally, encounter both a P1 and
a P2 enemy, and earn their actual manifest check IDs through the required
delivery or defeat. Save normally, exit and resume, then reconnect the client
and restart the server using its existing save. Verify enemy identities and
progress persist without duplicate awards. Synthetic events, forced deaths,
and startup logs do not satisfy these checks.
