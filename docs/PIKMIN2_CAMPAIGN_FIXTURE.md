# P2 campaign fixture (issue #837)

Reusable root tooling that productizes the successful issue #830 non-preview
campaign setup. It starts a real enabled randomizer session and stays
species-contract driven. It is infrastructure, not gameplay proof: it makes no
gameplay claim, native production change, pool admission, shared AP relink, or
user-game mutation.

Tool: `scripts/p2_campaign_fixture.py`. Tests:
`tests/test_p2_campaign_fixture.py` (pure, never boots the game).

## Background (#830 recipe)

The #830 gen-3 runs used preview mode (`--experimental-pikmin2-room`), where
`pc_port/pc_bbft.cpp` takes the bridge-only early return before
`pc_randomizer_init`, so no enabled session ever exists (zero
`[Pikmin Randomizer]` lines) and no receipt is possible. The gen-4 correction
built a non-preview campaign harness in the owned native runtime: production
`pc_main`-style boot, a real source-23 seed override, production-generated
session bootstrap/sidecar with the production `ENEMY_P2` block (33 rows, no
hand-staging), `install_layout` content/actors, 20-red forest squad, session
keepalive, 960x540 centred startup, captain guard first, one bounded run
(173 s, exit 86 on `CAPTAIN_DOWN`). This tooling captures that setup so any
species consumer can repeat it without reimplementing it.

## Usage

Stage a real enabled campaign (deterministic seed, short private session path):

```powershell
py -3.12 scripts/p2_campaign_fixture.py stage --seed p2-campaign-23 `
  --session-dir C:/p2fix/sess --content-root <prepared p2-content> `
  --assets C:/path/to/assets --exe <nectar.exe> --species 23 `
  --out C:/p2fix/fixture-manifest.json
```

Launch it bounded against a species marker contract, then validate offline:

```powershell
py -3.12 scripts/p2_campaign_fixture.py launch --manifest C:/p2fix/fixture-manifest.json `
  --exe <nectar.exe> --seconds 173 `
  --pass-marker 'P2_SARAI_DELIVERY_BIND generator=\d+' `
  --block-marker 'P2_SETUP_ABORT\s+Sarai' --report-out C:/p2fix/report.json
py -3.12 scripts/p2_campaign_fixture.py validate --manifest C:/p2fix/fixture-manifest.json
```

`--species` is `admitted` (default), `playable`, or comma-separated source
ids. Species meaning always comes from the caller's `--pass-marker` /
`--block-marker` regexes; the fixture only checks the enabled-session
handshake (`SESSION enabled=1 ready=1`), boot, guard, and bind coverage.

## What gets recorded

The fixture manifest pins root HEAD, native presence (absent on this lane;
read-only through configured integration paths), executable/assets/seed/
session hashes, `content prepared.json` hash, 960x540 centred startup
(`PIKMIN_P2_ROOM_WINDOW=960x540`), the #632 captain guard source hash, the
production boot command (never a preview flag), and the species contract.

## Fail-closed table

| Condition | Behaviour |
|---|---|
| Preview flag on the boot argv (`--experimental-pikmin2-room`, `--preview*`, any `--experimental-*`) | `FixtureRejected`, nothing launches |
| Staged bootstrap `ENEMY_P2` not byte-equal to the production derivation for the manifest | rejected as hand-written/stale rows |
| Stale content (`prepared.json` missing/unreadable/empty) or stale executable (sha mismatch) | rejected before staging/launch |
| Missing session handshake in the log | `FAIL` (preview logs never emit it) |
| Unsafe session path (relative, `..`, NUL, >100 chars, inside assets, or already existing) | rejected without deleting anything |
| Missing captain guard header | rejected; a guard trip is `BLOCKED` (exit 86) |
| Launch budget outside 1..600 s | rejected as unbounded |

## Captain safety (#632)

The native fixture must adopt `scripts/p2_fixture_captain_guard.h` (or an
equivalent tested guard): check `orimaDead`, `NaviDead` and HP<=1 before
pause/movie returns or observed ticks, emit `CAPTAIN_DOWN`, exit 86. Park the
captain outside attack reach when not testing captain hits; no blanket
invincibility. Protected observation is labelled and cannot prove captain
damage. This tooling records the guard hash and maps any guard marker to
`BLOCKED`, never to a pass.

## Adoption contracts (issue #842)

Reusable consumer contracts live in `scripts/p2_campaign_fixture.py`
(`SPECIES_MARKER_CONTRACTS`, `species_contract()`, `consumer_markers()`).
Setup markers prove staging/binding only; behavior markers prove natural
gameplay beyond setup and are required as `pass_markers`, so setup-only
evidence fails closed (`FAIL: no species pass marker observed`). The fixture
parser already counts binds generically; consumers only supply behavior +
block markers. Offline proof:
`tests/test_p2_campaign_fixture_adoption.py` (pure, never boots the game).

| Species (sources) | Setup markers (bind/stage only) | Behavior markers (pass) | Block markers |
|---|---|---|---|
| Sarai (23) | `P2_SARAI_READY source_id=23`, `P2_SARAI_BIND generator=`, `P2_ENEMY_READY species=Sarai generator=` | `P2_SARAI_CORPSE_READY`, `P2_SARAI_DELIVERY_BIND generator=` (campaign delivery analogue) | `P2_SETUP_ABORT Sarai`, `P2_SETUP_SKIP Sarai` |
| Kogane (9, 10, 11) | `P2_KOGANE_BIND generator=`, `P2_ENEMY_READY species=Kogane generator=` | `P2_KOGANE_COLLECT_PASS`, `P2_KOGANE_NATURAL_ATTACK` | `P2_SETUP_ABORT Kogane`, `P2_SETUP_SKIP Kogane` |
| Kurage (57) | `P2_KURAGE_TEKI_READY`, `P2_KURAGE_TEKI_CORPSE`, `P2_ENEMY_READY species=Kurage generator=` | `P2_KURAGE_CORPSE_RECEIPT_PASS generator=`, `P2_KURAGE_DEAD_CORPSE_RECEIPT_PASS generator=`, `P2_KURAGE_CORPSE_CLEANUP_PASS` | `P2_SETUP_ABORT Kurage`, `P2_SETUP_SKIP Kurage` |
| Sokkuri (79) | `P2_SOKKURI_BIND generator=`, `P2_ENEMY_READY species=Sokkuri generator=` | `P2_SOKKURI_DELIVERY_BIND generator=`, `P2_SOKKURI_DEAD`, `P2_SOKKURI79_DELIVERED_TO_GOAL`, `P2_ORDINARY_P2_RECEIPT id=onion:p2:79` | `P2_SETUP_ABORT Sokkuri`, `P2_SETUP_SKIP Sokkuri` |

Pinned requirements (asserted offline): fresh absolute private session path
(`require_safe_session_dir`, <=100 chars, never inside assets, never
pre-existing); source/executable/content hashes (guard + exe + prepared.json
sha256, stale pins rejected); 960x540 centred startup
(`PIKMIN_P2_ROOM_WINDOW=960x540`); #632 captain guard (trip -> `BLOCKED`,
exit 86); bounded supervision (1..600 s, preview flags refused, nothing
spawns on rejection).

## Consumer referrals (referrals only; this tooling lane never boots the game)

Stage once, then launch per species against its contract (same manifest;
`--species` selects the cohort). Consumers may also call
`consumer_markers(<species>)` to obtain the exact pass/block lists.

```powershell
py -3.12 scripts/p2_campaign_fixture.py stage --seed p2-campaign-23 `
  --session-dir C:/p2fix/sess --content-root <prepared p2-content> `
  --assets C:/path/to/assets --exe <nectar.exe> --species 23 `
  --out C:/p2fix/fixture-manifest.json
py -3.12 scripts/p2_campaign_fixture.py launch --manifest C:/p2fix/fixture-manifest.json `
  --exe <nectar.exe> --seconds 173 `
  --pass-marker 'P2_SARAI_CORPSE_READY\b' `
  --pass-marker 'P2_SARAI_DELIVERY_BIND\b.*?generator=\d+' `
  --block-marker 'P2_SETUP_ABORT\s+Sarai\b' --block-marker 'P2_SETUP_SKIP\s+Sarai\b' `
  --report-out C:/p2fix/report-sarai.json
py -3.12 scripts/p2_campaign_fixture.py launch --manifest C:/p2fix/fixture-manifest.json `
  --exe <nectar.exe> --seconds 173 `
  --pass-marker 'P2_KOGANE_COLLECT_PASS\b' `
  --pass-marker 'P2_KOGANE_NATURAL_ATTACK\b' `
  --block-marker 'P2_SETUP_ABORT\s+Kogane\b' --block-marker 'P2_SETUP_SKIP\s+Kogane\b' `
  --report-out C:/p2fix/report-kogane.json
py -3.12 scripts/p2_campaign_fixture.py launch --manifest C:/p2fix/fixture-manifest.json `
  --exe <nectar.exe> --seconds 173 `
  --pass-marker 'P2_KURAGE_CORPSE_RECEIPT_PASS\s+generator=\d+' `
  --pass-marker 'P2_KURAGE_DEAD_CORPSE_RECEIPT_PASS\s+generator=\d+' `
  --pass-marker 'P2_KURAGE_CORPSE_CLEANUP_PASS\b' `
  --block-marker 'P2_SETUP_ABORT\s+Kurage\b' --block-marker 'P2_SETUP_SKIP\s+Kurage\b' `
  --report-out C:/p2fix/report-kurage.json
py -3.12 scripts/p2_campaign_fixture.py launch --manifest C:/p2fix/fixture-manifest.json `
  --exe <nectar.exe> --seconds 173 `
  --pass-marker 'P2_SOKKURI_DELIVERY_BIND\b.*?generator=\d+' `
  --pass-marker 'P2_SOKKURI_DEAD\b' `
  --pass-marker 'P2_SOKKURI79_DELIVERED_TO_GOAL\b' `
  --pass-marker 'P2_ORDINARY_P2_RECEIPT\b.*?id=onion:p2:79\b' `
  --block-marker 'P2_SETUP_ABORT\s+Sokkuri\b' --block-marker 'P2_SETUP_SKIP\s+Sokkuri\b' `
  --report-out C:/p2fix/report-sokkuri.json
py -3.12 scripts/p2_campaign_fixture.py validate --manifest C:/p2fix/fixture-manifest.json
```
