# PanModoki (source 38) contested-cargo transport and receipt contract (#220)

Lane `shard-enemies-4-panmodoki38-gate5`, issue #220 (parent #168), worker
muse-l76. Private root pin `2849a068`, private native pin `009f0937`.
Scope: close the single remaining `transport_reward` gate on the source-38
ledger row while preserving the existing PASS gates. Siblings 40 OoPanModoki
and 83 PanHouse are audited read-only and not claimed.

## Ledger state (docs/PIKMIN2_ENEMY_ROSTER_EVIDENCE.json, entry "38")

| Gate | Status |
|---|---|
| identity_spawn | PASS (preserved) |
| movement_animation | PASS (preserved) |
| attacks_receivers | PASS (preserved) |
| death_corpse | PASS (preserved) |
| cleanup_reentry | PASS (preserved) |
| **transport_reward** | **UNTESTED (this slice)** |

## What this contract adds

- `experimental/pikmin2_panmodoki_transport.py` ? read-only observer that
  parses the real bridge markers from `pc_p2_breadbug_actor` +
  `pc_p2_breadbug_contest_host` and validates the natural tug plus the durable
  nest/Pod receipt and its exactly-once negatives. It emits nothing and never
  invents a run.
- `tests/test_pikmin2_panmodoki_transport.py` ? 12 focused tests (synthetic
  logs only): positive sequence, plus refusal of missing bind, unknown
  behavior, proxy-only carry, injected receipt, grant without steal, wrong
  receipt identity, duplicate delivery, missing duplicate negative, missing
  drag, and cross-generator noise.
- `native/tools/p2_panmodoki_transport_fixture.cpp` ? standalone stdlib-only
  log checker (`-Wall -Wextra -Werror`, no engine dependency) implementing the
  same grammar for a native-side gate script.

## Marker grammar (real, from the pinned bridge)

`P2_BREADBUG_ACTOR_READY ... behavior=P1_Collec_proxy`, `P2_BREADBUG_CONTEST
generator=<id> native_power=<p> carriers=<n>` (natural carry latch),
`..._BEGIN ... identity=onion:p2:38:0`, `..._UPDATE ... outcome=held|stolen|
released`, `..._STOLEN ... released=1`, `..._GRANT ... granted=1` /
`granted=0 duplicate=1`, `..._PROBE ... injected=1`.

Required order for `transport_reward`: bind -> natural carry latch (real
carriers) -> sustained held drag -> stolen tug -> exactly one granting receipt
for `onion:p2:38:*` -> a later duplicate attempt refused. Injected probes and
grants without a preceding steal are rejected.

## Evidence revalidated this turn (NOT a fresh run)

- `tests.test_pikmin2_panmodoki_transport`: 12/12 OK.
- Native checker compiled clean with `-Wall -Wextra -Werror`; exit 0.
- Against the existing natural contested-cargo receipt run
  `output/dsw/l33-out/slice3/breadbug-run2/host.log` (older pin, lane 33):
  `PASS ... carry_line=768 drag_line=831 stolen_line=772 grant_line=773
  duplicate_line=797 injected_probes=2`, exit 0. This is revalidation of prior
  natural evidence, not a fresh pin run; it is not relabeled.
- Negative contracts all refused with exit 1: proxy-only carry, injected
  receipt, duplicate delivery.

## Exact remaining dependency for a fresh gate-5 PASS

A fresh natural contested-cargo run at pin `2849a068` / native `009f0937` needs
the lane 06/07 shared cargo surface: the small proxy owns no P2 cargo, so a
fresh run must supply real P2 cargo ownership and contest arbitration, or
rebuild the lane-33 staged host contest fixture at the pin. Until then
`transport_reward` stays UNTESTED; no admission, no allowlist write, no
playability claim. OoPanModoki (40) and PanHouse (83) remain open.
