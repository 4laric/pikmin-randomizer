# tutorial_3 carrier-token staging for floors 3/5/8 (#826)

Lane `tutorial3-carrier-token-staging`: root-only staging contract resolving the
tutorial_3 floors 3/5/8 carrier-token fail-closed blockers for the downstream
consumer `p2-cave-tutorial_3-p1-later-floors` (#812, blocked gen2).
Implementation owner: Codex through shared account 4laric. No native edits, no
builds, no launches, no ADMIT.

## Exact pins (fail closed on any missing/unknown pin)

- Source bytes: `user/Mukki/mapunits/caveinfo/tutorial_3.txt`, offset 770672856,
  size 9701, sha256
  `adcc816653957fbf00919c313291142cb110b5479c7790d997399e380c9b1abb`.
- Handoff A (read-only, done gen2): `p2-cave-tutorial_3-p1-source-recovery`
  (#153), root `5c12c69916ae2cc6bb0084e4848ce5f9e9cb7c3f`.
- Handoff B (read-only, done gen2): `provider-placement-carrier-landing` (#657),
  root `4a4e367b420fc3f3bca1e5dff4d464e78db9db61`; catalog pin `7a21ce6a…`,
  packaging pin `04d58d33…`, native pin `e2aa476e…` recorded only. Its slot-99
  Waterwraith scope is NOT reused as tutorial_3 carrier semantics.
- Consumer (#812, blocked gen2): root base
  `fdd558123223f94d706b9a00973037553e864756`, head
  `2a97c0682c6bead1990f8f4cedb469623da18e06`; native base
  `a95040b66a0ffc9cdbfc649502569a29e66949a7`, head
  `a6a63f0ddd18f3ab9d08a7e6110c464766b9bd92`.
- Recovery request: `9002486c30bb9ab1e6dd030aa8cb82d317750911844ed2aca2c84d35e0d08372`.
- Packet: schema `p2-cave-import-p0-1`, cave `tutorial_3`, 8 floors; sidecar tag
  `P2_TUTORIAL3_CARRIER_STAGING_1`.

## Contract result

- `experimental/pikmin2_tutorial3_carrier_token_staging.py`: validates the P0
  envelope, checks exact pins/handoffs fail-closed, records per-floor carrier
  rows verbatim (enemy_id, source_token, carried_treasure, drop_mode) with no
  invented semantics. Floors 2/4/6/7 must be exact; floors 3/5/8 must carry at
  least one carrier row and stage `BLOCKED_CARRIER_TOKEN`; floor 1 is refused
  (owned by the DONE floor-1 lane).
- `tests/test_pikmin2_tutorial3_carrier_token_staging.py`: 14 focused tests —
  pass on known pins, fail-closed on missing/unknown pins/handoffs, carrier-row
  checks per floor, consumer-check naming. All green, stdlib only.
- Emitted packet (`p2-tutorial3-carrier-token-staging.json/.txt`) binds both done
  handoffs to the #812 closure with the concrete consumer re-run check.

## Downstream consumer re-run check (#812)

1. `py -3.12 -m unittest tests.content_lanes.test_p2_cave_tutorial_3_p1_later_floors -v`
   — 11/11 green expected.
2. `py -3.12 experimental/content_lanes/p2-cave-tutorial_3_p1_later_floors.py --packet <p0-packet.json> --output <out> --floors 2,4,6,7`
   — stages clean.
3. Same adapter with `--floors 3,5,8` — must exit nonzero with `non-exact token`
   until the carrier follow-on lands.
4. `py -3.12 experimental/pikmin2_tutorial3_carrier_token_staging.py --packet <p0-packet.json> --output <out> --floors 3,5,8`
   — emits `BLOCKED_CARRIER_TOKEN` rows for the follow-on carrier implementation.

## Gates and claims

All six runtime gates UNTESTED. No gameplay claim beyond observed evidence; no
duplication of #153/#657/#812 scopes; no ADMIT. This slice performs no runtime
run, so no fresh #632 guard run is claimed here.

## Follow-on implementation guidance (not executed here)

- Use the canonical lease CLI under the current elastic cap with a private build
  dir under `output/`; record pinned commits, executable SHA-256 and `ninja -n`.
- Adopt the fixture baseline (`docs/PIKMIN2_IMPLEMENTATION_FANOUT.md`): fresh
  private arena from the current overlay, 960x540 centred-window startup, live
  starting squad, no immediate extinction.
- Apply captain safety #632 (`scripts/p2_fixture_captain_guard.h`, canonical
  hash `47b99b7bfd43310c35a7815d46d4f8591b21f573`; #812 doc cites historical
  vendored hash `d2f678c9…`): check orimaDead, NaviDead and HP<=1 before
  pause/movie returns or observed ticks; emit CAPTAIN_DOWN and exit BLOCKED.
  Park the captain outside attack reach except when captain damage is the test.
  No blanket invincibility.
- Shared-file decisions (#186) go through the reviewer ledger, not this lane.
