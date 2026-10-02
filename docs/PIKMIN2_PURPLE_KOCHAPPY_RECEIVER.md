# Natural Purple impact receiver (#1155)

Codex through shared account `4laric` implements this private candidate under
[#1155](https://github.com/4laric/pikmin-randomizer/issues/1155), following the
imported tutorial encounter in #1150 and integration issue #1144. Source starts
at native `35ad0ad401a531709ed747f6878b9b0e845f63d3` and root
`09e504322b60d5ab796f3b42f19ab8009c946806`. Original producer claims and private
worktrees remain intact through supported editing-only agreements.

The existing natural Purple earthquake emitter already calls the registered
Kochappy receiver. Its P1 TAI state16 consumer cannot run for an imported actor
whose own source FSM suppresses P1 `doAI`. The candidate recognizes registered
own-FSM actors through that FSM's living phase, accepts the existing receiver
event without a P1 transition, and consumes bounce/Fit in its actual update.
Unowned actors retain the previous P1 eligibility and mandatory TAI transition.

The source reference is the read-only P2 checkout at
`632af93787b9c95b63f0c13be32b161375ce3a96`, `EnemyBase.cpp`: Earthquake/Fit is
a lifecycle overlay, stopping the current motion and suspending ordinary
`doUpdate`, then resuming it. The host saves its manual-animation option and
motion speed, sets animation advancement to zero, and freezes the FSM clock
and attack/swallow/flick one-shot flags. Completion restores those saved values
without entering a new behavior or restarting an attack. Repeated impacts
retain the original saved motion. This is a host animation adaptation; it does
not change actor movement speed, collision geometry or earthquake radius.

Natural queued damage is still consumed before the overlay. Death or Press
restores motion and interrupts the receiver before entering the existing
terminal behavior; actor forget restores before erasing its FSM lifetime.
Red's existing exactly-once native drops/private corpse remain unchanged.

The registered receiver still owns bounce200+100*roll, the existing0.3 Fit
chance, strict greater-than duration boundary, positive Fit timer preservation
across repeated impacts, and per-actor source durations Red10s/Orange5s. The
existing receiver's conditional random-draw convention is retained, including
its existing P1 behavior; this change does not certify retail random-stream
parity. Fit visual effects/tilt are not newly implemented by this bridge.

`p2_kochappy_stun_receiver_test` compiles the real receiver with narrowly
stubbed host, TAI and own-FSM edges. It checks the original staleP1state0/nullTAI
failure, terminal rejection, legacy transitions, source durations, repeated
Fit, interruption and fresh actor lifetime. It is explicitly unit evidence,
not production-FSM execution or a natural throw acceptance result.

Remote compilation and independent source review are required before integration.
Natural acceptance must use a fresh <=60s supervised ordinary throw fixture,
960x540 centered startup, immediate canonical post-idle captain guards and
negative exit86 checks. A mixed roster must conserve20 starting bodies:19 Red
and one explicitly disclosed native Purple, or ordinary conversion of one of
20 Red. No additional21st body, positive actor-state injection, relocation or
speed change may establish acceptance. Until a fresh natural impact run proves
bounce/Fit recovery and natural damage/death interruption, that gate stays open.

Final combination with the latest #1150 source and #1144/#1148 source needs an
independently reviewed merge and fresh consumers. Feature CI or this document
does not confer a source receipt, complete gameplay approval or issue completion.

The separate `pikmin_ci_fixture_purple_kochappy` engineering preview uses the
current twenty-Red overlay and ordinary SDL Violet conversion/approach/pluck,
then actual Purple throwing. It observes the real animator counter and saved
motion option while the registered receiver is active, production state-clock
pause/resume logs, natural recovery and terminal interruption. A preview pass
cannot close the ordinary tutorial/AP mixed gate: current surface boot refuses
AP seed sessions and has no ordinary Purple enable/acquisition recipe.

Use `python -m scripts.run_pikmin2_purple_kochappy --help` from this root
worktree. Supply the exact remote fixture executable and package directory,
full root/native source pins, its SHA256 and explicit private source banks.
The runner requires all four manifest-verified CI DLLs beside the executable,
clears ambient game/co-op settings, creates a fresh save and caps wall time60s.
Run READY and both exit86 guards before positive mechanics. The focused
prelaunch tests run with
`py -3.12 -B -m unittest scripts.test_purple_kochappy_fixture_inputs -v`.

POSIX supervision observes its child with `waitid(WNOWAIT)` and retains the
session leader until a single group retirement, before reaping it. Cleanup is
idempotent and never kills a numeric group after leader reaping. It records actual
child reaping and group absence before success; unknown ownership or missing
cleanup witnesses fail. This requires default SIGCHLD and sole child reaping for
the supervisor's lifetime. The native execution budget is60s; retirement/reaping
and absence observation have a separate bounded cleanup budget. This group
supervisor does not contain descendants that deliberately escape their session
or survive an abrupt supervisor death; the separately admitted broker cgroup
must contain those cases. Harmless Python process controls do not admit a native
fixture or close the natural/AP gameplay gate.
