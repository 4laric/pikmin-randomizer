#pragma once
#include <pc_p2_groink.h>
#include <cstddef>

struct P2GroinkTargetCandidate {
    P2GroinkVec3 position;
    bool alive = true;
    bool captain = false; // Source isNavi(): Navi/captain.
    bool pikmin = false; // Actual isPikmin(), not every isPiki().
};
struct P2GroinkTargetQuery {
    P2GroinkVec3 muzzle;
    P2GroinkVec3 direction; // Source getDirection(faceDir); horizontal unit vector.
    float searchDistance = 0;
};
struct P2GroinkTargetResult {
    bool valid = false;
    bool found = false;
    std::size_t index = 0;
    P2GroinkVec3 position;
};
// Candidates must already be filtered by the host source-compatible cell query
// and retain its iteration order. No pointer or target registration is retained.
P2GroinkTargetResult p2_groink_select_target(const P2GroinkTargetQuery& query,
    const P2GroinkTargetCandidate* candidates, std::size_t count);

enum class P2GroinkNextState { None, Dead, Flick, WalkHome, TurnHome, Attack,
                             Walk, Turn, WalkPath, TurnPath };
struct P2GroinkAttackEndInput {
    float health = 1;
    bool flick = false;
    float homeDistanceSquared = 0; // XZ only.
    float territoryRadius = 0, homeRadius = 0;
    float homeAngle = 0, pathAngle = 0, searchedAngle = 0; // getAngDist radians.
    float maxAttackAngleDegrees = 0;
    bool attackable = false;
    bool searchedTarget = false;
};
struct P2GroinkAttackEndResult {
    bool valid = false;
    P2GroinkNextState state = P2GroinkNextState::None;
    // Commit query side effects only for the queries reached by source order.
    bool useAttackableQuery = false;
    bool useSearchedQuery = false;
};
P2GroinkAttackEndResult p2_groink_attack_end(const P2GroinkAttackEndInput& input);
