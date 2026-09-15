#pragma once
#include <pc_p2_groink.h>

enum class P2GroinkHitKind { None, Bomb, Wind };
enum class P2GroinkCandidateKind { Other, Captain, Pikmin, OtherPiki, Enemy };
struct P2GroinkHitCandidate {
    P2GroinkVec3 position;
    P2GroinkCandidateKind kind = P2GroinkCandidateKind::Other;
    bool alive = true;
    bool owner = false;
    float cellRadius = 0;
};
struct P2GroinkHitInput {
    // Already shifted down 10 units by the shell step. Host supplies candidates
    // from the source cell query; this is not a replacement broad phase.
    P2GroinkVec3 start, end;
    float radius = 0, terminalRadius = 0, damage = 0;
    bool terminal = false;
};
struct P2GroinkHitCommand {
    bool valid = false;
    bool insideSweep = false;
    P2GroinkHitKind kind = P2GroinkHitKind::None;
    float damage = 0;
    P2GroinkVec3 impulse;
};
P2GroinkHitCommand p2_groink_classify_hit(const P2GroinkHitInput& input,
                                        const P2GroinkHitCandidate& candidate);
