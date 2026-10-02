# Experimental P1 and admitted P2 enemies

This package carries Python installers and a pinned admission catalog, not game
assets. Use your own extracted Pikmin 1 assets and prepared Pikmin 2 content.
The experimental enemy pool currently admits 42 source identities. The
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
