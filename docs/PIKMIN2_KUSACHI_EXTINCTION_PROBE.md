# Kusachi extinction-window probe (#793)

Lane `kusachi-extinction-probe-native`, issue #793 (OPEN). Implementation
owner: Codex through shared account 4laric. The #787 verdict attributes the
kusachi extinction to the engine manager level (single-tick 20->0, no death
trail); this lane builds the discriminating probe. Fixing the extinction is
explicitly not this job; the cascade-vs-clear verdict belongs to the #780
consumer reading the probe stream.

## Wire (native worktree, base 93603dc2)

`native/pc_port/pc_p2_challenge_runtime.cpp` (the only engine TU touched):

- Opt-in `probeTick` called on every wiring tick: with a
  `p2-kusachi-probe.txt` sidecar whose first word is `P2_KUSACHI_PROBE_1`,
  each tick emits
  `P2_KUSACHI_PROBE tick=N navimgr= navi= navi_alive= orima_dead= alive=
  reds= slots=<20 alive flags>`.
  Without the sidecar the TU emits nothing beyond the pre-existing bridge
  lines (production behavior bit-identical). Guarded reads only; never
  aborts, never changes state.
- Probe placement covers manager-loss ticks too (it runs before the
  early-return arms), which is exactly the discriminating region.

Note on the brief's second callsite: `pc_p2_challenge_content.cpp` carries
no `countSquadByColor` at this pin (verified absent across the tree);
per-color counting lives in `countSquad` (reds) above, so that TU is
intentionally untouched. Owned but unchanged.

Native commit (branch `codex/kusachi-extinction-probe-native`):

- `b9f07431bd000251a5200b608c33e9b8bb61f68f` probe + fixture

Base note: the published proposal pins native a95040b6, where `countSquad`
does not exist (verified absent there and at b805d9c6); the callsites exist
only from the wave tip onward, so the lane rebased to 93603dc2 (divergent
lines, recorded via checkpoint rev 3).

## Compiled evidence (private leased build `output/kusachi-extinction-probe-build`)

- `ninja: no work to do.` (`ninja -n` exit 0).
- Engine `bin/nectar.exe` sha256
  `fbc6b16380a5a61669eb1b5af2d7e7556bc2bba1b43109058ae640c7d7892d55`.
- Fixture exe sha256
  `17dd759c94d411b581652b9d70ab01c41418788b06af74e36da17c260015927c`
  (linked against the pikmin_pc graph minus `pc_main`).

## Runtime proof (`run-793/probe0/probe.log`, sha256 `4ea12ef3…`)

Staging: complete asset tree + `p2-kusachi-probe.txt`
(`P2_KUSACHI_PROBE_1`) + cargo-free sidecar; `--experimental-pikmin2-room
--experimental-challenge-stage ch_NARI_01kusachi`, 960x540, exit 0:

- 1254 probe lines: early ticks show `navimgr=0` (manager-loss coverage),
  later ticks `alive=8 reds=8 slots=11111111`.
- `P2_CHALLENGE_MODE_BOOT`, `P2_KUSACHI_PROBE_PASS`, `PASS KUSACHI_PROBE`;
  no abort; no `P2_FIXTURE_CAPTAIN_DOWN`.
- Guard self-test 7/7 + negative exit 86 re-verified.

Guard adoption: #632 vendored truth table + self-test in the fixture;
observation-only, captain parked by the room scenario (no captain-damage
claim). Guard `scripts/p2_fixture_captain_guard.h` sha256 `d2f678c9…3c3474`.
All six runtime gates UNTESTED. SERIALIZED: shared-line integration via
#186 + integrator. No other edits; no ADMIT.

## Handoff

Downstream consumer `kusachi-gameplay-obs` (#780): the probe stream above
is the prescribed input; read ticks around the extinction window to settle
navi-drop cascade vs direct manager clear, then re-run the guarded boot.
