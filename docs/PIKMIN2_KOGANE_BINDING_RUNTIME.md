# Beetle registry runtime acceptance (#228)

Fixture module experimental/pikmin2_kogane_binding_runtime.py is a NEW adapter over
Kimi's placement fixture. It preserves ordinary stage updates and legitimate
private tutorial input dismissal; no enemy state, health or animation field writes.
It verifies exact requested stored birth and generator XYZ, then real source-ID
query9/10/11 for actors219001/2/3 and -1/name-null for control219004. A native draw
log is required separately. It captures kogane-binding.ppm at observation60 and
requires all four actors alive at300. Source FSM/flips/drop/gas are not exercised.

Three tests pass: missing evidence rejection, explicit typed/control mapping,
exit-code rejection and real-source instrumentation. The builder delegates to the
existing strict native fixture builder and preserves initial/final dependency/hash
checks; shared native stays unchanged. Runtime artifacts are recorded below after
the fresh build and actual run finish.

Actual run PASS on fresh native7faa64475176658af85e2f558858c6d660cd4d20.
Executable5385bd991cdd91456d81d19736f97c5c874567198bad9b0e2a82bc9f838baa36
exited0. Typed source IDs9/10/11, baseline control-1, exact full stored birth and
native generator XYZ, native draw invocation and alive4 at frame300 all passed.
Capture shows all three imported beetle models and ordinary P1 control. They share
a black/silver approximation: source texture variants and full material fidelity
are not accepted. No source FSM/drop/gas behavior was tested.

Fixed run: output/kogane228/runtime/stages/f0bb11777d6040f5a68e7be3768dbc95.
Check.cmd runs the copied BindingCheck.exe and exits automatically after300 observed
frames. fixed-manifest.json records exact executable, configs, poses and command.
Binding-evidence.json and kogane-binding.png preserve result/capture. Current DLL
resolution uses C:/msys64/mingw64/bin; this is a local developer fixture, not portable
release packaging. Root can pass this fixed run to Kimi for independent validation.
