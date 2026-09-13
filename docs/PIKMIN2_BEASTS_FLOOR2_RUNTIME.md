# Cargo-free Hole of Beasts floor 2 runtime (#263)

Owner: Codex using shared GitHub account 4laric, cave lane under #129/#154.
Native commit `0f3ddbd9f1d91fab50fbd2c8242a22a34805c034` is a fixture-only
child of `0c42821d` (#260). Production gameplay is unchanged. The root branch
`codex/p2-beasts-floor2-runtime` follows the frozen #260 candidate.

## Delivered boundary

The dedicated fixture dispatches through `pc_p2_preview_cargo_free_ready()`
before the room fixture's treasure-specific readiness gate. It requires no
treasure actor, no other living bosses/enemies/pellets, the existing Pod receiver
and Purple bank, twenty Reds and exactly two Violet conversion proxies.
Source generator identities and stored birth/live/ground XYZ are checked:

| Generator | Source type-8 slot | XYZ |
| --- | --- | --- |
| 62000 | 30 | (-55, 0, 75) |
| 62001 | 31 | (75, 0, -95) |

The captain walks within 80 units of each flower through controller input and
stops before throwing. Five originals are assigned to each flower in sequence.
The fixture enters the normal flying state and calls `Navi::throwPiki`, then
waits for actual collision, conversion and sprout emission. Missed throws retry
only surviving, unattached normal Pikmin while that flower is open. No direct
Purple identity assignment, sprout birth, conversion call or reward is injected.
`Navi::throwPiki` itself performs the normal placement at the captain's throw
origin; this is a synthetic action driver, not a manual grab/throw input test.

Each flower must replace its five original Reds. Ten Purple sprouts plus ten
remaining Reds must exist before plucking. One sprout goes through the delayed
captain pluck state; the remainder use native `InteractBikkuri`. The final
population must be ten Purples, ten Reds and zero sprouts, with correct Purple
carry strength/selection identity, unchanged repairs, zero Pokos and no cargo
or receipt files. The source room, existing Pod and sampled Purple models load
and render; captures are retained. Material fidelity is not signed off.

The marker is strictly parsed and opt-in. Other fixture paths are unchanged.
The runner rejects missing/duplicate milestones, wrong IDs, changed or nonfinite
coordinates, absent approaches/conversions/throws, wrong populations and reward
markers. It hashes all staged overrides/configs, the executable and log, and
verifies the executable and staged inputs remain unchanged during execution.
Ordinary `readiness.json` retains `native_ready=false`; `acceptance.json` is the
separate record certifying only that exact runtime/configuration.

## Reproduction and evidence

From `C:/Users/alari/pikmin-randomizer/output/p2-cave-lane`:

```powershell
python -m experimental.pikmin2_beasts_floor2_runtime --root ../.. `
  --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets `
  --exe output/beasts263-final/linked/fixture.exe `
  --output output/beasts263-repro
```

`--root` selects read-only prepared inputs: `output/p2-mapcode0-batch/import`
(the audited dry-attribute-0 unit import), `output/p2-cave-catalog-batch/audit-final/catalog.json`,
`output/pikmin2-purple113/import-05` and `output/pikmin2-pod111/import-02`.
The older `p2-beasts-units-batch/approximate` import predates the collision audit
and correctly fails readiness for this room. Every run creates a fresh UUID
directory; earlier runs and player saves remain untouched. SDL audio is silent.

Build with `scripts.build_pikmin2_fixture` against a completed private native
CMake/Ninja build and the exact native commit above. The delivered executable
is `output/beasts263-final/linked/fixture.exe`, SHA256
`ebca7c6e2a82b04cdf150f1ad9b5ae9efcf62888bb3a495cbf550c146e33e961`.
`linked/provenance.json` records source/object/link hashes and two no-work Ninja
freshness checks. It reuses the cave lane's private Release/MinGW/JAudio build,
with IPO and randomizer test hooks off; it does not modify a maintained build.

Two fresh final runs passed all runtime and hash checks:

| Run under `output/beasts263-final/runs/` | Log SHA256 |
| --- | --- |
| `d50573181ba440afa979088c3c0bfe2a` | `04bc1e0e130cc207dd085167b00381b215aa1d2cf10afd9f0b70302a95e95a05` |
| `60cc67bd00af4de79818bfde0df0c99e` | `b058cd18c67ac370bfbc69eb7731cd792a0f859d47defe348d754b70499eabef` |

Their identical readiness SHA256 is
`9ca9b9f2e929db9f9284578ea941192154beaf7d7fbc0cc63dfa2f3973edf7e3`.
Both used exactly ten initial throws, converted five plus five, and restored
all twenty bodies. Captures and every staged input hash are in `acceptance.json`.

The same executable also passed the ordinary P1 scaffold treasure/combat/corpse
control without the Beasts marker: `output/beasts263-final/p1-control/fe87673984b14d05ac48b868c56d377d`.
It completed native corpse transport over 398.87 units and Onion removal; log
SHA256 `9d345d7c60e586dbf9a98361258f13efdf2a8d7840213508fb208e566262f0ad`.

Focused pytest result: **36 passed, 3 skipped, 51 subtests passed**. The skips
are historical optional asset tests using worktree-relative asset directories;
the real floor-2 runs explicitly use the available audited imports. Tests cover
runtime evidence rejection, stage source/zero-cargo contracts, native cargo-free
policy, generator offsets, fixture linking and existing instrumentation. The
policy test now uses exported `engine/` by default, or `PIKMIN_NATIVE_SOURCE`,
so it also runs in private root worktrees without an initialized `native/` tree.

An earlier distant-throw probe stopped at seven sprouts and failed; its unchanged
evidence is retained at `output/beasts263-probe/runs/1642b74214e54e1ba0a8032b1d4a1698`.
The approach probe `runs03/355cc3fa861844c8930b13b3e0db0773` passed before the
final per-flower assertions/hashes were added. It is not substituted for the
final evidence above.

## Remaining work

This uses one explicitly selected cent2 room with capped exits, P1 Pom behavior
with the existing Violet conversion proxy, and scripted actions. Source yaw is
recorded but not applied. Eggs/helpers, plants, global Purple suppression,
descent and full cave lifecycle remain unsupported. It is not retail seeded
generation, full P2 Candypop behavior, complete floor content or natural-play
acceptance. Shared integration and combined-build review remain separate.
