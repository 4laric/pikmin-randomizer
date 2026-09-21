# #730 stage-table extension landing packet (lane p730-landing-packet, issue #852)

Tooling-only preparation packet for the sole integration owner. It verifies the
done-unlanded producer lane `challenge-stage-table-extension-native` (#730),
re-applies its native commits in order in a private wave-pinned worktree, runs
its declared tests, and records one apply-order packet plus hashed artifacts.
**No source is landed by this lane; no native commit, merge or export was made.**

Producer packet (handoff evidence, now archived):
`output/deepseek-wave/inbox/done/challenge-stage-table-extension-730-packet.md`
sha256 `109594c7…` (handoff-time hash was `87429f4f…`; the archived copy gained
an appended ack line after review). #186 owner decision + review acceptance:
`output/workflow/integration-recovery/species-owner/stagetable730-186-decision.md`
sha256 `e30ecb1b…`.

## 1. Producer lane verified at its exact commits

The producer registry source records are incomplete: `native.commits=[]`,
`root.commits=[]`, both `head==base`, `dirty=""`. The actual branch tips carry
commits. The exact commits below come from the producer packet and were
re-verified directly against both repos with clean trees.

| Repo | Branch | Base | Ordered commits (final head) | Worktree clean |
|---|---|---|---|---|
| native | `codex/autofill-challenge-stage-table-extension-native` | `93603dc2` | `5e871f88`, `5372bf65`, `1bbf9eeb` | yes @ `1bbf9eeb` |
| root | `codex/autofill-challenge-stage-table-extension-native` | `ecf5f53a` | `a7c43d22`, `56392896` | yes @ `56392896` |

### Changed files re-hashed (final content at producer head)

Native (sha256 of `git cat-file blob <head>:<path>`):

| Path | Blob | SHA-256 |
|---|---|---|
| `pc_port/pc_p2_challenge_stages_ext.cpp` | `ca117202` | `1e7dbd35082d41b5331c60b3e88c8105b41c6b98c491646efd9c821a0684456f` |
| `pc_port/pc_p2_challenge_stages_ext.h` | `6d47f509` | `3cca5d721eee16b5b89807c6d0f456ab15e8594420b0f5a87f4c706e1cdf9f8e` |
| `tools/p2_challenge_stage_table_ext_fixture.cpp` | `c55caddc` | `8edf61b22665bd7d8d65efe1453931ba7a79bab2abe1a0bac4bbce1cec7b0e7a` |

Root (final content at `56392896`):

| Path | Blob | SHA-256 |
|---|---|---|
| `docs/PIKMIN2_CHALLENGE_STAGE_TABLE_EXTENSION.md` | `269196bb` | `9c1d4200f8fc81c7f7377e8b16f6e0d94feeb97a4f639b18bf7eb069c0366bed` |
| `experimental/pikmin2_challenge_stage_table_extension.py` | `755b27e8` | `220e58d7a3188dc8317d9e6bff3f720b65b14d78f53d7b8f7c88709b251b9a12` |
| `scripts/build_p2_challenge_stage_table_ext.py` | `01b6074e` | `2b95d89a667e19438561389bd6aecebec2e65d6dc168d3290f7967c3cc27a355` |
| `tests/test_pikmin2_challenge_stage_table_extension.py` | `63d286b6` | `c3718e4c38fe219e4f08736526a0b8427d2f0259d6f5959f1a4b6ebced5d14b9` |

Machine-readable: `output/p730-landing-packet/producer-verification.json`
sha256 `c03efbb5eba0f248cfe1482815912fb6aad01e3e0e12ef57d5c25e976c2c6639`.

## 2. Apply-order result (private wave-pinned native worktree)

Destination pin: native wave line `claude/p2-deepseek-wave-native` head
`9c144414562597e1f35659d754cc9acc02d9fbd0`. Private worktree:
`output/p730-landing-packet/wave-native` (detached, ignored).

**The producer native commits are already landed on the wave line.** All three
are ancestors of `9c1444145`, folded in by merge
`66d98a4d0392271aefc6709327441d49ef32a7e5`. Re-applying them in order
(`git cherry-pick --no-commit` ×3, resolving the two fixture conflicts by
keeping the destination's already-later revision) produced an **empty net
change**: the resulting index tree `ffd75213…` is byte-identical to the
destination tree `ffd75213…`, and the worktree status is clean. Every expected
file blob matches the producer final blob exactly.

- Conflict `5e871f88`: add/add in `tools/p2_challenge_stage_table_ext_fixture.cpp`
  (destination already has the later revision) — resolved to destination content.
- Conflict `5372bf65`: content conflict in the same file — resolved to destination
  content.
- `1bbf9eeb`: applied with no conflict.
- No unrelated curated file was touched.

Machine-readable: `output/p730-landing-packet/apply-report.json`
sha256 `e5210a5668c5440be2564b831efb6f8f2f58f6b8b76c4722a8b71494a92852bd`.

Rehash any expected file on the destination:

```powershell
git -C native rev-parse 9c144414562597e1f35659d754cc9acc02d9fbd0:<path>
git -C native cat-file blob 9c144414562597e1f35659d754cc9acc02d9fbd0:<path> |
  py -3.12 -c "import hashlib,sys;print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())"
```

## 3. Declared tests

Declared command (from the producer docs) run against the exact producer root
tree `56392896`:

```
py -3.12 -m pytest tests/test_pikmin2_challenge_stage_table_extension.py -q
```

Result: exit `0`, **10 passed, 1 skipped** (0.12 s). The skipped test is
`TestNativeTable.test_ext_table_compiles_strict_and_resolves`: it hard-codes the
now-deleted producer native worktree
`output/workflow/autofill/prerequisites/challenge-stage-table-extension-native-native`.
The producer reported 11 passed while that worktree existed.

Independently reproduced the skipped strict check against the wave-pinned
worktree using the test's own `EXT_TU` and flags
(`g++ -std=c++17 -O1 -Wall -Wextra -Werror -I <wave>/pc_port …`):
build exit `0`, run exit `0`, stdout `EXT_TABLE_OK`, executable SHA-256
`8c895303aaca7f5c786edecbc6b2abce3dfed7d57b8796ec9111b35cf5af1047`.

Evidence: `test-results.json` sha256
`697441ed332a37f5617f1b33db10f0d350e46ccbc6d368514afda8c4ec368dea`;
`native-strict-check.json` sha256
`489b732b38c4fed3581d099cf487589be5b3a2c1f78bbfee39aec412cdba233b`.
No heavy `pikmin_pc` build or runtime launch was required; the strict test is a
two-file compile into a private ignored directory.

## 4. Owner-decision items

1. **Root commits unlanded.** `a7c43d22` and `56392896` are ancestors of neither
   the root canonical head `fdd55812` (`kimi/p2-bulblax-import`) nor the root
   wave head `3a33cbde` (`claude/p2-deepseek-wave`). The declared tests cannot run
   on either line until they land. Owner action: land the two root commits or
   record an explicit waiver.
2. **Engine wiring follow-on absent.** The native ext table is landed but inert:
   `pc_p2_challenge_stages_ext.*` are referenced only by the fixture TU, which
   `CMakeLists.txt` does not reference. There is still no
   `pc_p2_challenge_stage_lookup` → `pc_p2_challenge_stages_ext_lookup`
   fallthrough and no `pikmin_pc` membership for the ext TU. The #186 decision
   approved exactly this follow-on in shape with current-line conditions
   (coexist with the #718/#722/#728 `pc_bbft.cpp` seams). It is **not** part of
   the producer commits and needs its own serialized implementation + leased
   rebuild + guarded run.
3. **Mechanical conflict (informational).** The ordered add/add and content
   conflicts above are expected when replaying intermediate commits onto a
   destination that already holds the final revision; resolve by taking the
   destination content. No owner decision needed.

## 5. Boundaries

- Tooling-only: `native = null`; no native commit, no merge, no export, no
  protected-branch write. Producer lane and maintained checkouts untouched.
- No gameplay/runtime acceptance is claimed; all six arena gates remain UNTESTED.
- Artifacts under `output/p730-landing-packet/` (ignored); checksums in
  `sha256sums.txt`. Apply-order packet:
  `output/p730-landing-packet/apply-order-packet.json` sha256
  `a68396f57c9b1c44648e4ea422619c4dc7b6cbbc3d59d20904595ba94e34d6d1`.
