#pragma once
// P2 challenge host-mode engine runtime bridge (lane
// challenge-hostmode-engine-hook-native, #710; #186 review before any
// shared-line landing).
//
// Binds the selected P2ChallengeStageRow to the landed p2challenge
// HostState/StageEntry, owns the runtime state, and drives
// p2challenge::wiring::syncTick from live engine facts. Emits
// P2_CHALLENGE_MODE_BOOT/_TICK/_DONE plus the wiring tick stream.
//
// Link-safety contract (why pc_bbft.cpp calls this through a hook):
// pc_bbft.cpp is ALSO linked into the small pc_bbft_test target, which has
// no engine objects. So pc_bbft.cpp itself stays engine-free and only holds
// a null-by-default hook pointer plus a plain params copy; the
// engine-dependent bridge below lives only in pikmin_pc (and the replacement
// fixture link), never in pc_bbft_test. In pc_bbft_test the hook stays null
// and pc_bbft_update() is inert. This indirection is forced by the dual
// linkage, not optional; the engine still drives the bridge every frame in
// pikmin_pc.
//
// This header is engine-free (plain types only) so both targets compile it.

// Plain copy of the selected stage row. Strings point at the static decoded
// table in pc_bbft.cpp (process lifetime); arrays are copied by value.
struct P2ChallengeStageParams {
    const char* caveId;
    int uiIndex;
    int floors;
    float floorSeconds[8];
    int roster[7][3];
    int bitterSprays;
    int spicySprays;
};

// Copies the currently selected stage row into out; false when no valid
// stage key is selected (silent inert path). Defined in pc_bbft.cpp.
bool p2_challenge_stage_params(P2ChallengeStageParams& out);

// Per-frame bridge hook. The pikmin_pc bridge registers its update at
// startup; pc_bbft_update() invokes it when set, inert otherwise.
using P2ChallengeRuntimeHook = void (*)();
void p2_challenge_runtime_set_hook(P2ChallengeRuntimeHook hook);
