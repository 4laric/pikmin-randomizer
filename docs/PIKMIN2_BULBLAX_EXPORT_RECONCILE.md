# Bulblax native hook export reconciliation (#414)

Reconcile plan for landing the local Bulblax native hook commits into the
six-lane/integration export **without** running the full export script, pushing
native origin, or dirtying shared checkouts.

- Child issue: [#414](https://github.com/4laric/pikmin-randomizer/issues/414) — assigned 4laric.
- Parents: [#186](https://github.com/4laric/pikmin-randomizer/issues/186) (import pipeline / integration queue), [#172](https://github.com/4laric/pikmin-randomizer/issues/172) (Empress/Emperor Bulblax and Larvae).
- Owner: Codex on the shared 4laric account.
- Status of this document: **analysis + plan only.** The export has NOT been run and native origin has NOT been pushed.

## 1. Commit graph summary

```
native branch opencode/p2-batch5-actor-hooks (worktree output/p2-kimi-bulblax-native), HEAD cb14f494
  cb14f494  King deterministic bomb line-up injection (#289)
  23bbdea5  J3D TTK1 BTK decoder + opt-in Bulblax display hook (#239)
  b0531098  Baby larva captain-bite injection (#400)
  ffe8b1cb  Queen profile: allow Baby attack/attackfail clips (#400)
  5f7329f1  Baby larva captain-attack receiver, state 4 InteractAttack (#400)
  59a2aa8f  optional King death injection (#289)
  e5529771  King WarCry injection (#289)
  4f517e01  kimi/p2-king-actor  <-- merge-base with integration-six
  ... (kimi/p2-king-actor base 650dc165 kimi/p2-queen-actor ...)

native branch opencode/p2-integration-six (worktree output/integration-six), HEAD 2c98a71f
  2c98a71f  Merge KingChappy sampled actor (#289)  -> parents b602506f, 4f517e01
  b602506f  Merge Queen sampled actor (#256)
  ...
```

`git merge-base opencode/p2-integration-six opencode/p2-batch5-actor-hooks` = `4f517e01`.
`git merge-base --is-ancestor 2c98a71f opencode/p2-batch5-actor-hooks` = **false**
(exit 1): integration-six is not an ancestor of actor-hooks. actor-hooks is a
straight continuation of the king-actor lane that integration-six already merged
plus five later display commits (`eb69578b`, `c541b0ff`, `f2173b51`, `bef5232e`,
`629d94a5`).

## 2. Exact family file set (relative to the integration line)

`git -C native diff --stat opencode/p2-integration-six...opencode/p2-batch5-actor-hooks`:

| Native path | Change | Raw SHA-256 (native @ cb14f494) | LF-normalized SHA-256 |
|---|---|---|---|
| `pc_port/pc_p2_btk.h` | new (195 lines) | `649197a4038983d21f117afced508059e9269c03d23ed41aee1f186301dd68f0` | `88fb61efab153d71d5fb252d886815ac1c9bb95787921308e9d6e73fbaa260d4` |
| `pc_port/pc_p2_bulblax_visual.cpp` | changed (+ ~12/-1 BTK hook on the 4f517e01 base) | `c43d7ea7052d5efa576be3b486f00e66b2b9cdf505570baafcaafca122e2493f` | `5b4fc260c6c4cd6822da2bfe170674308a8bb8d6b5b0e0bef4757be186f62134` |
| `pc_port/pc_p2_king.cpp` | changed (+85) | `9ef025f0e195362d71eaebe1e12bb1d8cbf0e916bd54e072bbb32dcd6fda4e99` | `fb3abb7e0597aff9deb2bc27372b91323569ebba1606fc4db82d1b11cbc82d2f` |
| `pc_port/pc_p2_queen.cpp` | changed (+112/-8) | `15ce2027d9db56937c8e5ba6b56557e1b6c7442c9579c9813806b480739d2233` | `8f97fb3c338bb52792577974ff544e71c380e732aa557ac1e74e86467a977c90` |
| `pc_port/pc_p2_queen_policy.h` | changed (1 line) | `9362a4e633680c091d8746fae662bfcbb8f3b7ac26da7245b103e0b712bdcfbb` | `56517770745bc786be012e6f0450b0127dd8087e877e857d6d431301b2eef5a8` |

Note: `pc_p2_btk.h` is genuinely new on actor-hooks; integration-six does not
have it. The other four exist on both sides.

## 3. Conflicts with other lanes / integration drift

`git -C native merge-tree --write-tree --name-only 2c98a71f opencode/p2-batch5-actor-hooks`
reports exactly one conflicted path:

```
pc_port/pc_p2_bulblax_visual.cpp   CONFLICT (content)
```

- No cross-lane conflict. The five other lanes merged into integration-six do
  not touch these files.
- The conflict is **same-family integration drift**: integration-six advanced
  `pc_p2_bulblax_visual.cpp` with shared display-clock / retail-player /
  pose-bank interpolation work (#268, #272, #277, #313), which actor-hooks
  branched before. Four conflict hunks exist:
  1. anonymous-namespace globals (integration clocks/retail/interpolate/baked vs
     actor-hooks `btk` globals / removed `started`),
  2. `pc_p2_bulblax_visual_reset()` (integration clears clocks/retail/baked; actor-hooks clears `btk*`),
  3. `pc_p2_bulblax_visual_setup()` sidecar block (interpolation sidecar vs BTK sidecar),
  4. `pc_p2_bulblax_visual_draw()` (integration clock/retail/interpolation draw vs BTK one-shot log using the removed `started`).
- Resolution rule: **integration-six is authoritative host state; add the BTK
  hook on top.** Use the integration `p2display::Clock`/`p2retail::Player`
  frame (authoritative source clock) for the one-shot BTK sample instead of the
  removed `started`/`SDL_GetTicks()` frame. A prepared resolution is included as
  a patch (section 6); it was **not compiled** (no-build constraint).
- Other four files (`pc_p2_btk.h`, `pc_p2_king.cpp`, `pc_p2_queen.cpp`,
  `pc_p2_queen_policy.h`) auto-merge/apply cleanly.

## 4. Root-side parity result

Root branch `opencode/p2-batch5-bulblax` (worktree `output/p2-batch5-bulblax`,
HEAD `9cd091c`) already contains synced copies under `engine/pc_port/`.

`python scripts/verify_p2_bulblax_export_parity.py` result:
**all five files MATCH `opencode/p2-batch5-actor-hooks`, raw byte-identical and
LF-normalized identical** (both sides stored CRLF, so no normalization was
needed; the script normalizes CRLF→LF regardless and reports `raw-eq`).

However, the root `engine/pc_port/pc_p2_bulblax_visual.cpp` is the **pre-integration**
actor-hooks version: `git diff --stat 6e79fe6 9cd091c` shows this file regressing
`-112` relative to root `opencode/p2-integration-six`. Merging the root batch5
branch as-is would re-introduce the same conflict and could drop the
interpolation machinery. Reconcile in native first (section 5), then re-sync the
exported file.

Also note `native-patches/bulblax/pc_p2_bulblax_visual.cpp` on the root branch is
stale (blob `9c6a3293`, the pre-BTK base). It is a duplicate copy and should be
refreshed or dropped after reconciliation to avoid drift.

## 5. Recommended reconciliation order

Do everything in an isolated native worktree; never in the maintained
`native/` checkout and never in `output/integration-six`.

Preferred (patch application, conflict-free, verified):

```powershell
git -C C:\Users\alari\pikmin-randomizer\native worktree add -b opencode/p2-integration-six-bulblax `
  C:\Users\alari\pikmin-randomizer\output\integration-six-bulblax 2c98a71f
$wt = 'C:\Users\alari\pikmin-randomizer\output\integration-six-bulblax'
$art = 'C:\Users\alari\pikmin-randomizer\output\p2-export-reconcile-artifacts'
git -C $wt apply "$art\bulblax-family-clean-4files.patch"       # btk.h, king.cpp, queen.cpp, queen_policy.h
git -C $wt apply "$art\bulblax-visual-btk-resolved.patch"       # conflicted file resolved
git -C $wt add pc_port/pc_p2_btk.h pc_port/pc_p2_bulblax_visual.cpp pc_port/pc_p2_king.cpp pc_port/pc_p2_queen.cpp pc_port/pc_p2_queen_policy.h
git -C $wt commit -m "pc_port: land Bulblax native hooks on integration-six (#239, #289, #400)"
```

Cherry-pick alternative (same result; expects one conflict on
`pc_p2_bulblax_visual.cpp`), oldest first:

```powershell
git -C $wt cherry-pick e5529771 59a2aa8f 5f7329f1 ffe8b1cb b0531098 23bbdea5 cb14f494
# resolve pc_port/pc_p2_bulblax_visual.cpp per section 3, then: git -C $wt cherry-pick --continue
```

Both patches were apply-checked cleanly against the `2c98a71f` blob contents.

Then export **only the five family files** (avoids the full-tree sweep of other
workers' dirty state), driven from the reconciled worktree, not the dirty
maintained checkout:

```powershell
# after the integration lead fast-forwards / checks out the reconciled commit in an isolated native worktree
$src = 'C:\Users\alari\pikmin-randomizer\output\integration-six-bulblax\pc_port'
$dst = 'C:\Users\alari\pikmin-randomizer\engine\pc_port'
'pc_p2_btk.h','pc_p2_bulblax_visual.cpp','pc_p2_king.cpp','pc_p2_queen.cpp','pc_p2_queen_policy.h' |
  ForEach-Object { Copy-Item "$src\$_" "$dst\$_" -Force }
```

Fallback (full export) is only safe once the maintained checkout is clean:
`git -C native status --porcelain` must show no modified tracked files and no
unmerged paths, then the integration lead runs
`py -3.12 scripts/export_native_source.py`.

Parity gate after export:

```powershell
python scripts/verify_p2_bulblax_export_parity.py `
  --native-rev <reconciled-native-commit> --root-rev <root-export-commit>
```

## 6. Include / exclude sets

Include (exact):
- `pc_port/pc_p2_btk.h`
- `pc_port/pc_p2_bulblax_visual.cpp` (reconciled: integration machinery + BTK hook)
- `pc_port/pc_p2_king.cpp`
- `pc_port/pc_p2_queen.cpp`
- `pc_port/pc_p2_queen_policy.h`

Exclude:
- **Unmerged other-worker file** `tools/preview_p2_purple_direct.inc` (native
  index stage `u UU`). A full `git ls-files` export would copy conflict markers.
- **CRLF-only dirty tracked files** `src/plugPikiKando/creatureCollision.cpp`
  and `src/plugPikiKando/goalItem.cpp` (native `core.autocrlf=true`; no logical
  diff, but the export reads working-tree raw bytes and would write CRLF into
  `engine/`).
- `pikmin2-research/` (untracked decomp checkout; not in `git ls-files`).
- All non-family paths from the other lanes currently in the maintained
  checkout; do not sweep them.

## 7. Artifacts (uncommitted, under `output/`)

- `output/p2-export-reconcile-artifacts/bulblax-family-clean-4files.patch`
  (4 clean files; applies to `2c98a71f`).
- `output/p2-export-reconcile-artifacts/bulblax-visual-btk-resolved.patch`
  (resolved conflicted file; applies to `2c98a71f`; not compiled).
- `scripts/verify_p2_bulblax_export_parity.py` (committed; parity gate).

## 8. Blockers

1. Maintained `native/` checkout is not export-safe: it has an unresolved
   merge on `tools/preview_p2_purple_direct.inc` and CRLF-modified tracked
   files. Do not run the full export from it.
2. `pc_p2_bulblax_visual.cpp` must be resolved by hand (or via the prepared
   patch) before it can land on integration-six; the root branch's existing
   `engine/pc_port` copy is pre-integration and would regress the interpolation
   work if merged directly.
3. The prepared resolved patch is uncompiled (builds were out of scope), so the
   integration lead should compile it in an isolated worktree before accepting.
