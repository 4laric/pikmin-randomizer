# Sheargrub extraction reproducibility (#135)

Audit date: 2026-09-12. Source base: `984d7bdd2f67f71cc655b10b52f50514d76cc841`.
Windows, Python 3.12, user-owned US GPVE01 revision 0 disc.

Two fresh extractions and two fresh private installations produced identical relative
paths and file bytes. No content fields were excluded or normalized by the comparison.
Filesystem timestamps and the enclosing output-directory names are not file contents
and do not enter the manifest digest. Extraction already records relative conversion
filenames. No production extractor or installer changes were needed.

| Output | Files | Bytes | SHA-256 of canonical manifest |
| --- | ---: | ---: | --- |
| Extraction | 123 | 467969 | `7da294d8ad46069d6febea39b587b3b6d3fd9bb446205d6338499a7cb7489fa1` |
| Installation | 5 | 25711 | `93f903a663e823dcdf7aa2deec49b73d3b5901baf8adec7293e158b8d829efa1` |

Both runs converted all 7 UjiA clips (21 poses) and all 9 UjiB clips (27 poses).
Installation selected the first move and last dead pose for each species, verified
their declared hashes, and wrote four models plus `p2-sheargrub.txt`.

## Reproduce

Run from the repository root with fresh output directories. The exact local disc
path used below must be replaced with your own lawful source as appropriate.

```powershell
py -3.12 -m experimental.pikmin2_sheargrub_assets --iso 'C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso' --output 'output/first/imported' --pose-limit 3
py -3.12 -m experimental.pikmin2_sheargrub_assets --iso 'C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso' --output 'output/second/imported' --pose-limit 3
@'
from pathlib import Path
import json
from experimental.pikmin2_sheargrub_install import install
for name in ('first', 'second'):
    root = Path('output') / name
    meta = json.loads((root / 'imported/sheargrubs.json').read_text())
    assert all(c['status'] == 'converted' for v in meta['species'].values() for c in v['clips'])
    assert sum(len(c['poses']) for v in meta['species'].values() for c in v['clips']) == 48
    (root / 'run/assets/dataDir/courses/pikmin2room').mkdir(parents=True)
    install(root / 'imported', root / 'run', [(60000, 'UjiA'), (60001, 'UjiB')])
'@ | py -3.12 -
py -3.12 -m scripts.compare_pikmin2_extractions --left output/first/imported --right output/second/imported --output output/imported-comparison.json
py -3.12 -m scripts.compare_pikmin2_extractions --left output/first/run --right output/second/run --output output/run-comparison.json
py -3.12 -m unittest tests.test_pikmin2_extraction_reproducibility tests.test_pikmin2_sheargrub_assets tests.test_pikmin2_sheargrub_install
```

The audit originally invoked `write_report` directly with these same arguments;
the CLI uses the same function. Reports contain complete file manifests. Its digest
is SHA-256 of UTF-8 JSON for the sorted relative-path mapping of size and SHA-256,
with sorted keys and compact separators. Exit code 0 means identical; 1 means a
difference (or an execution error; inspect stderr). Empty/missing trees, linked
paths, reports inside input trees, and existing reports are rejected. Reports are
written exclusively and their parent directory must already exist.

Validation: 11 tests discovered, 10 passed, 1 skipped because Windows did not permit
symlink creation. The linked-directory guard is implemented but that test was not
exercised on this host. Negative tests cover changed/added/removed files, differing
JSON paths, empty/missing inputs, and report overwrite/input-tree protection.

## Disc inputs

The importer recorded these archive SHA-256 values in both runs:

| Disc path | SHA-256 |
| --- | --- |
| `enemy/data/UjiA/anim.szs` | `a31685af0b15a7405c9219c6150530a64ed54713adbc9f96f147cd471a24e628` |
| `enemy/parm/enemyParms.szs` | `3618455a8561f1e1b0aad0253a75a69fae1fe3a47160d1c1efa294b0ddeb2a84` |
| `enemy/data/UjiA/model.szs` | `f7aed88e3f31dd9c29243b897e0f30c8f5104fc981c3cc412a48cc384f08d34d` |
| `enemy/data/UjiB/model.szs` | `6ca5d43a84c86dd7fbcda69c829961b83884e71aac929d33f412759064a2ff17` |

This establishes same-host reproducibility for this disc and pose budget only.
It does not establish cross-platform output identity, other discs or pose budgets,
full `stage_pair` generator staging, native compilation, installation UX, or gameplay.
The private installer still labels behavior as P1 KabekuiA/KabekuiB proxy behavior;
the extraction remains `native_ready: false`. Runtime QA remains a separate lane.
Disc assets and comparison reports stay under ignored `output/` and are not shipped.
