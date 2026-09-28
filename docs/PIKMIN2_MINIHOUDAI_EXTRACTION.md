# MiniHoudai 78 ISO extraction (lane rd-p2-minihoudai-extractor, issue #849)

Parent coordination: #827. Concrete provider required by #847 (guarded
three-species launcher: Sarai 23 + MiniHoudai 78 + Sokkuri 79).

## Problem

`scripts/p2_prepare_content.py` refuses source 78 because the MiniHoudai
family installer exists (`experimental.pikmin2_family_install`: `78:
'minihoudai'`, `_validate_minihoudai` / `_adapt_minihoudai`) but no ISO
extractor is wired in `EXTRACTORS`. This lane owns the extractor; the
`scripts/p2_prepare_content.py` registration below is a structured shared
review because unfinished #643 owns that file. It is not applied here.

## Owned implementation

`experimental/pikmin2_minihoudai_assets.py :: extract(iso, output,
pose_limit=3)` reads the retail MiniHoudai banks off the US GPVE01 rev 0 disc
and writes the identity-keyed `MiniHoudai` directory the family installer
pre-flights (`_read_identity_source(source, 78, 'MiniHoudai')`):

* `identity.json` (schema 1, source_id 78, enum_name `MiniHoudai`).
* `minihoudai.json` schema-1 manifest: 8 retail clips, 24 sampled
  `minihoudai_<clip>_<ii:02>.mod` poses with per-pose `.json` conversion
  records, model-space `kuti` muzzle samples (before the runtime aim
  callback), `enemy.bmd`, the four `minihoudai/enemy*.txt` metadata files and
  `fixed-enemyparm.txt` (pedestal variant, audit only).
* Deterministic (hashed reads, fixed clip order); fail-closed (`ValueError`
  on missing/truncated entries, ambiguous `kuti` joint, bad pose limit,
  existing output). Unsupported frames are recorded, never placeholdered.

Real-ISO result: 8/8 clips `converted`, 24 poses, 64 files, installer
pre-flight and `p2-groink-teki.txt` sidecar emission verified
(`tests/test_p2_minihoudai_assets.py`, `tests/test_p2_prepare_content_minihoudai.py`).

## Verified ISO members (all real, `C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso`)

| Member | Offset | Size |
| --- | --- | --- |
| `enemy/data/MiniHoudai/model.szs` | 776253776 | 14336 |
| `enemy/data/MiniHoudai/anim.szs` | 776218224 | 35552 |
| `enemy/parm/enemyParms.szs` (`minihoudai/*`, `fminihoudai/enemyparm.txt`) | 777415504 | 160224 |

General parameters (audited `profile`): health 1200.0, search 250.0, radius
15.0, angle 65.0, damage 10. Native pose-naming citations: none staged yet --
pose meshes are data-only (the adapter stages only the actor sidecar), so no
native file:line is claimed for them. Installer contract:
`experimental/pikmin2_family_install.py:398-410` (`_read_identity_source`),
`:468-513` (`_validate_minihoudai` / `_adapt_minihoudai`).

## Shared review R1: wire 78 into `scripts/p2_prepare_content.py` (owner #643)

Reason: CONTENT gate -- without this, source 78 keeps reporting "family
installer exists but no ISO extractor is wired here". Applies cleanly at
`48a2a69` (root pin of this slice). On landing, also update
`tests/test_p2_prepare_content.py::test_prepare_orchestrates_playable_first_with_stubs`,
which currently pins 78 as the supported-but-unextractable case (that
assertion becomes false; 78 joins the extracted set).

```diff
--- a/scripts/p2_prepare_content.py
+++ b/scripts/p2_prepare_content.py
@@ -31,6 +31,11 @@ Existing per-family extractors are reused as-is; nothing here rewrites them:
  * 57 Kurage: ``pikmin2_kurage_assets.extract`` -> ``<out>/Kurage/``; the Kurage
    adapter stages the visual files through ``pikmin2_kurage_content``.
+ * 78 MiniHoudai: ``pikmin2_minihoudai_assets.extract`` -> ``<out>/MiniHoudai/``
+   (``minihoudai.json`` + ``identity.json`` + ``minihoudai_<clip>_<ii>.mod``);
+   the MiniHoudai adapter stages the actor sidecar through
+   ``experimental.pikmin2_groink_carcass_teki.sidecar_config``. Pose meshes
+   are data-only.
  * 79 Sokkuri: ``pikmin2_sokkuri_assets.extract`` -> ``<out>/Sokkuri/``
    (``sokkuri.json`` + ``ginv_Sokkuri_<clip>_<ii>.mod``); the Sokkuri
    adapter stages the batch-2 ground files through ``pikmin2_sokkuri_content``. A legacy
@@ -331,6 +336,33 @@ def extract_kurage(iso, dest):
     return target


+def extract_minihoudai(iso, dest, pose_limit=3):
+    """Build <dest>/MiniHoudai/ via the MiniHoudai extractor.
+
+    ``pikmin2_minihoudai_assets.extract`` produces the identity-keyed tree
+    (``minihoudai.json`` + ``identity.json`` + sampled poses); the MiniHoudai
+    adapter stages the actor sidecar from that tree (pose meshes are
+    data-only).
+    """
+    from experimental import pikmin2_minihoudai_assets as minihoudai_assets
+
+    iso, dest = Path(iso), Path(dest)
+    if not iso.is_file():
+        raise ValueError(f"ISO not found: {iso}")
+    if type(pose_limit) is not int or not 2 <= pose_limit <= 8:
+        raise ValueError(f"pose limit must be 2..8: {pose_limit!r}")
+    target = dest / "MiniHoudai"
+    if target.exists():
+        raise ValueError(f"content dir already exists: {target}")
+    tmp = dest / ".tmp-minihoudai"
+    if tmp.exists():
+        shutil.rmtree(tmp, ignore_errors=True)
+    try:
+        minihoudai_assets.extract(iso, tmp, pose_limit=pose_limit)
+        shutil.copytree(tmp, target)
+    finally:
+        shutil.rmtree(tmp, ignore_errors=True)
+    return target
+
+
  def extract_sokkuri(iso, dest, pose_limit=6):
      """Build <dest>/Sokkuri/ via the Sokkuri extractor.

@@ -343,6 +375,7 @@ EXTRACTORS = {
      23: "extract_sarai",
      9: "extract_kogane",
      57: "extract_kurage",
+     78: "extract_minihoudai",
      79: "extract_sokkuri",
  }

@@ -412,6 +445,9 @@ def prepare_content_root(iso, out, research=None, pose_limit=3, wanted=None):
          elif source_id == 79:
              extract_sokkuri(iso, out, pose_limit=pose_limit)
              extracted.append(source_id)
+         elif source_id == 78:
+             extract_minihoudai(iso, out, pose_limit=pose_limit)
+             extracted.append(source_id)
          else:
              # Supported by the family map but with no extractor wired here
              # (e.g. Kochappy 1 / Snow 45 / BombSarai 58): report, don't invent.
```

Expected post-landing behavior (verified locally with the wiring applied via
monkeypatch, file untouched): `prepare_content_root(iso, out,
wanted=[23, 78, 79])` extracts `['Sarai', 'MiniHoudai', 'Sokkuri']` with empty
`skipped`, and a 33-binding seed manifest yields 33 actor bindings. The
`test_docstring_bullets_match_extractors` and
`test_every_wired_extractor_has_a_dispatch_arm` guards pass with this diff.

## Non-goals (explicit)

* No change to the playable pool, no runtime gate claimed, no ADMIT writes.
* No native work; no launch or modification of the user's game.
* FminiHoudai 97 stays out of scope (pedestal variant params preserved for
  audit only; roaming MiniHoudai identity belongs here per the Groink lane).

## Native OWN staging (#888 WP5)

The native Groink sidecar now drives a campaign-bound 78 (and 97) with the
engine-free source FSM (`pc_port/pc_p2_groink_fsm.cpp`, Open-Nectar PR #4).
`experimental/pikmin2_groink_stage.py` stages what it reads, from the
extraction above:

| Run file | Content | Native reader |
| --- | --- | --- |
| `p2-groink-parms.txt` | verbatim retail `minihoudai/enemyparm.txt` | `p2groinkfsm::parseEnemyParm` |
| `p2-groink-fixed-parms.txt` | verbatim retail `fminihoudai/enemyparm.txt` | same, for 97 |
| `p2-groink-bank.txt` | `P2_GROINK_BANK_1` clip/key-event/pose/muzzle bank | `p2groinkfsm::parseBank` |
| `assets/dataDir/courses/pikmin2room/minihoudai_<clip>_<ii>.mod` | sampled poses | `pc_p2_groink_teki_draw` |
| `p2-groink-teki.txt` | carcass sidecar, SOURCE timeline (proper fp11/fp12, fp00) | `p2groink::read` |

Bank grammar (whitespace separated, ASCII):

```
P2_GROINK_BANK_1 <clipCount 1..8>
clip <animId 0..7> <name> <frames 2..10000> <eventCount 0..64> (<frame> <type>)* <poseCount 0..24> <poseFrame>*
muzzle <c0x c0y c0z c1x c1y c1z c2x c2y c2z c3x c3y c3z>     (optional)
END
```

`animId` is the enemyanimmgr.txt row index (= MiniHoudai AnimID: walk,
search1, turn1, attack1, flick1, dead1, type5, rebirth); events are the
registry `(frame, type)` rows in order; pose frames are strictly increasing;
the muzzle is the model-space `kuti` joint matrix (columns) at the attack1
type-4 emission frame, before the runtime aim callback. `tests/test_p2_groink_stage.py`
round-trips the bank through a Python copy of the grammar and, when the native
sources and a compiler are available, through the native parser itself.

The extractor now samples poses per clip (`POSE_LIMITS`: walk 8, search1 4,
turn1 4, attack1 10, flick1 6, dead1 8, type5 2, rebirth 6; 48 poses,
a fail-closed 12 MiB budget, native cap 24 MiB) instead of 3 per clip. The 2.0/3.0/1200 gauge profile is
no longer written by the family adapter. It remains available to the
room-preview tools as `pikmin2_groink_carcass_teki.sidecar_config_short`. The
native campaign setup ignores sidecar gauge values in any case: it takes the
timeline from the parms file.

97 FminiHoudai is extracted by the cannon extractor. The `cannon_projectile`
family adapter stages `p2-groink-fixed-parms.txt`, and the shared bank and
poses when no 78 install has staged them already (the cannon FminiHoudai
bank uses the global pose limit). The cannon extractor also records the same
`kuti` muzzle.

Unverified without the ISO: real clip frame counts and pose bytes, the kuti
basis orientation versus the native `+Z` forward assumption, and that every
sampled frame converts.
