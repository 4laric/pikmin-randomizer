# Opt-in Honeywisp TEV patch (#207)

New experimental/pikmin2_qurione_material_patch.py provides descriptor(model),
patch(mod,rows), and prepare(imported,output). It recognizes only the audited retail
Qurione BMD SHA e5d733bf28a8721ebd5ad325c368fabbb9cf18f500fab72fcf962a5fe2abc8ad.
Unknown models/formulas and repeated/already-modified MOD materials are rejected.
The descriptor follows INF1 shape-to-material mapping and extracts the source C0
register and nine-byte color/alpha expressions. No hard-coded guessed colour is
introduced. Format: {shape,material,register0:[signedRGBA],color:[A,B,C,D,op,bias,
scale,clamp,out],alpha:[same nine fields]}.

The MOD patch changes only register0 bytes0..7, color100..108, alpha112..120 inside
each124-byte exported TEV block. All geometry, channels, lighting control, draw order,
blend/depth, textures and unrelated material fields remain byte-identical. Current
retail bank requires18 actual changed bytes per pose. All21 poses patched into
output/p2-qurione207/tev-only; patch.json records before/after hashes and descriptors.
This helper does not alter converter defaults, shared native or existing playtests.

Three tests cover exact C0 bytes and permitted-diff regions, geometry preservation,
repeat/truncation rejection, unknown model and unsupported expression rejection.
Run `py -3.12 -m unittest tests.test_pikmin2_qurione_material_patch`.

## Private runtime comparison

Reused immutable native fixture executable8894d6f57e4b6ff12374d9f5682e4ddebc3c71909dc0c6026584f64cc5932908,
based on nativeb602d8c43dc6a1132821f787b99a28097c3c7521. New private original-map
arena891590a760474c5997d4bd895bc258f8 installed all patched models; exact overridden
model hashes are available in tev-only/patch.json (arena's initial installation
manifest describes the pre-patch bank, so use this explicit override record).
Run output/p2-qurione207/compare completed exit0 in25.81seconds, with registered
draw and no timeout. Runtime comparison image compare/tev-only.png is INCONCLUSIVE:
normal host flight phase put actorY168.97 at tick60, versus baselineY91.27 despite
same fixture/camera stimulus. The actor is outside the useful sampled view. This
is not proof of invisible materials and not a visual fidelity pass. Baseline capture
remains output/p2-qurione203-runtime/observe/arena.png, untouched.

No lighting flags were changed; content lane is separately auditing EnableColor0
and source channel translation. Do not combine the two causes prematurely. Next
runtime comparison should use camera-only actor framing or a source-backed fixed
random/flight fixture, leaving gameplay state untouched, then compare TEV-only and
lighting-only variants. Root can wire this opt-in helper after reviewing source
recognition and descriptor format; generalized converter support is not implemented.
