#pragma once
// P2 species that leave no carcass (#1088). Engine-free.
//
// Owner ruling 2026-10-01: "nah get rid of the jellyfloat corpses and the larva
// corpses let's stay P2-accurate"; extended the same day to Man-at-Legs and
// Raging Long Legs ("yeah thanks"). Each source disables EB_LeaveCarcass in
// onInit, so the body is removed at the end of its death clip and nothing is
// left to carry (decomp pikmin2-research, src/plugProjectNishimuraU):
//   31 Bulborb Larva          Baby.cpp:40;      BabyState.cpp:41/80 kill() at the dead/deadpress END
//   57 Lesser Spotted Jfloat  Kurage.cpp:36;    KurageState.cpp:75 burst (key 3), :84 kill() at END
//   66 Man-at-Legs            Houdai.cpp:71;    HoudaiState.cpp:55-62 dead END: throwupItem, dead bomb, kill()
//   69 Raging Long Legs       BigFoot.cpp:69;   BigFootState.cpp:56-60 key 2 item/Mitites, key 3 kill()
//   72 Greater Spotted Jfloat OniKurage.cpp:46; OniKurageState.cpp:80-88 burst (key 3), :90-91 kill() at END
// The port bound these to P1 vehicles that leave a corpse, and the randomizer
// check was earned by delivering it. Now the vehicle corpse is suppressed and
// the check is earned at the kill (pc_randomizer_p2_killed). The source gives
// no Pikmin seeds for these deaths, so none are given.
namespace p2nocarcass {

inline bool leavesNoCarcass(unsigned source) {
    switch (source) {
    case 31: case 57: case 66: case 69: case 72: return true;
    default: return false;
    }
}

// Corpse type a P1 vehicle reports for a bound source (TPI_CorpseType; P1
// TEKICORPSE_NoCorpse = 0, TEKICORPSE_LeaveCorpse = 1).
inline int corpseType(unsigned source, int vehicleValue) {
    return leavesNoCarcass(source) ? 0 : vehicleValue;
}

// The actor-lifetime seam (BTeki::doKill) also runs for teardown that is not a
// death (day end, slot reuse). Only a real kill earns the receipt: a death
// runs dieSoon, which clears TEKIOPT_Alive before doKill; a plain teardown
// reaches doKill still alive. Health is not consulted: a hazard death (water,
// fire) is a kill even when it did not drain the health bar.
inline bool killEarnsReceipt(unsigned source, bool alive) {
    return leavesNoCarcass(source) && !alive;
}

}  // namespace p2nocarcass
