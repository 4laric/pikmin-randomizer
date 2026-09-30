# Opt-in single-player captain switching (#928)

Implementation owner: Codex through shared account `4laric`.

Set `PIKMIN_P2_SECOND_CAPTAIN=1` before launching. Press **D-pad Up** (default
keyboard **Up arrow**, remappable) to switch captain. Hold switches once; release
before another press. Both captains must be alive, uncaptured, empty-handed and
in Walk or Idle. Rejected presses are not queued.

Camera, cursor, mouse aim, wheel, lock-on, swarm and free-camera drag follow the
selected captain. The inactive captain receives neutral controls and retains its
existing follow policy. Switching preserves squad ownership. Disband a captain's
formation before recruiting it with the other captain's whistle. Co-op and versus
retain their per-player input mapping.

Purple ship admission uses the selected captain, so a healthy survivor remains
eligible when the original primary is down. Health must exceed 1, matching the
native captain-down threshold. Movie, pause, UI and day-end exclusions remain.

The second actor still uses Olimar. Louie assets, persisted selection and full
two-captain cave/campaign checkpoints remain outside this slice.

## Source and validation boundary

This branch incorporates root main `7a94f88145a807a922bdc1d5c72c1ce9183889a5`
and native main `5d566d63817aa95b87284bb598332adea7a0f305` (Purple storage).
Current native candidate: `8ae1b5380` (clean when pushed). The root snapshot
receives only the captain source/test delta, the selected ship guard, and the
optional fixture CMake registration/helper. Native `.github` workflows and
unrelated snapshot differences are not copied into `engine/`.

Six focused checks compile the actual input/adapter helpers and the actual
`GameCoreSection::updateAI` ship-call prefix. They cover held-button edges,
stale input, camera ownership, safe states, squad preservation, captured/dead
rejection, and selected-survivor ship admission including pause/movie/UI/day-end
exclusions. Run with the desired `PIKMIN_NATIVE_ROOT`:

```text
py -3.12 -m pytest tests/test_pikmin2_captain_switch.py tests/test_pikmin2_captain_adapter.py tests/test_pikmin2_captain_squad_split.py -q
```

The existing production Kurage receiver harness also passes with its engine
doubles updated for the captain input/camera dependencies. Independent review
approved the current input, camera, ship guard and fixture source. This source
review does not establish gameplay acceptance.

## Runtime evidence and remaining checks

Windows CI run [36656631365](https://github.com/4laric/Open-Nectar---Pikmin-Native-PC-Port/actions/runs/36656631365)
passed 163 tests at native `9c0202b9c`. Its separately packaged fixture and
production EXE/DLL hashes were verified locally. Fixture SHA-256:
`9fbae0d836b87c18b05b2ca0ee9d10f847025467ffb2181ae26ebb1243aa41a8`.
This is CI-built evidence; no local full-engine rebuild is claimed.

Fresh runtime runs used current overlays with 20 live Pikmin, observed 960x540
centred windows after settings, and the canonical 60-second supervisor. Logs,
input hashes and rendered captures are under `output/p2-wip-landing/` in the
canonical workspace.

- Pair run 01 exposed a hidden selected cursor that prevented whistle entry;
  the cursor handoff was fixed and independently reviewed.
- Pair run 02 confirmed switching both ways, held-Up debouncing, movement,
  inactive neutral input, preserved squad ownership, camera drag consumption and
  rotation, pad zoom, and whistle entry. Its throw precondition was invalid: all
  Pikmin still belonged to the other captain's formation.
- Default single-player and co-op exclusion runs passed on that same CI build.
- Pair run 03 confirmed real disbanding, but the free squad remained outside the
  cursor's whistle range. The revised fixture explicitly stages only positions
  after disband, logs every Pikmin's eligibility and distance, and requires live
  recruitment before throwing. It tracks the same held Pikmin through rejected
  switching and post-release flight. Ownership/action states are not injected.

Final guarded pair acceptance, both survivor directions, and the negative
captain guard are pending on the current candidate. The next Windows artifact
also includes a no-work build dry-run. No final gameplay, Purple F10 transaction
in a survivor scenario, persistence or integration claim is made here.
