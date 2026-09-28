# Beetle native binding handoff (#228)

Owner Codex via4laric; Kimi retains import219. This batch is a buildable registration
and optional visual binding, not a source FSM. Integration baseline root73239ad95bc833e85cd7eff18b00e7519c3f27c6;
new family TU compiled against this checkout's exported engine headers (exit0).
No shared native/build/source export edits.

Files native-patches/kogane/pc_p2_kogane.{cpp,h} and pc_p2_kogane_policy.h are ready
for root to place in native/pc_port. Add cpp to CMake; call setup after births;
call draw from live BTeki visual dispatch, false delegates baseline; add name/source_id
to fixture diagnostics; reset on actual manager/stage reset; forget on successful
birth before init/slot reuse. Setup validates matching generator IDs exactly once,
requires host TEKI_Chappy3 and rejects existing Snow/Red/Sheargrub registrations.
Ordinary control untouched; missing sidecar leaves all baseline registrations/visuals.
Reset clears registry/timing/shape references; forget removes actor. Corpse draw
falls back to P1. Full reset/reentry runtime remains pending.

Kimi P2_KOGANE_ACTORS_1 remains unchanged. It has no species column and therefore
cannot independently express source identity. NEW experimental/pikmin2_kogane_native.py
emit(bank,run,arena,expected_manifest_sha256) validates Kimi plan/installedpose bytes,
source BMD hash, unique karada material and INF1 shape mapping. It writes a separate
P2_KOGANE_NATIVE_1 config containing karada shape, explicit generator/sourceID9/10/11,
and all three source sample-frame lists. Ambiguous species and existing sidecars
are refused; no ID-order inference. Call after Kimi arena prepare. Native shader
materials correspond to exported per-shape MOD material ordering.

Actual installed source bank:9poses/110880bytes; clipsmove/wait/damage. New private
arena output/kogane228/arena/e005a3ad80654602b439a48dd98aaeec; sidecar hash
d3391491680097c6643808ffbe833d2e40782f976d0ce6d6b58c89c59df9543d.
Actor219001->9,219002->10,219003->11;219004 remains ordinary P1 control.
Source frames preserved (move/wait0,7,14;damage0,24,49). The native sampler maps
normalized host counter to nearest source sample, with host damage/movement/wait
selection. This is approximate visual timing; source eventframes are not executed.

Each draw sets source karada K0 grey60/100/15 and restores it immediately afterward,
preventing shared-material colour leakage into other actors. This explicitly binds
the source constant; the restricted exported TEV may not consume it equivalently.
Per-species replacement textures and full TEV fidelity remain unimplemented; do not
claim species appearance parity. Materials/textures are shared within the bank after
resource-byte equality checks to avoid duplicate texture attachments.

One compiled policy test passes: typed source mapping, colour constants, duplicate/
unknown species and ambiguous v1 rejection. Full family TU compile passes;
output/kogane228/command.json and compile.log record it. Actual sidecar preparation
from Kimi run1 passed. Native runtime identity/render/control remains pending root
hook integration and fresh build. Current host type3 still runs P1 AI/rewards;
source five-state FSM, flip-event7 drops, Fart gas, three-flip escape, cave relocation
and natural hit acceptance are follow-on work. No runtime pass inferred from compile.
