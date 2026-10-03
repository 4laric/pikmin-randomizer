#pragma once
#include <cmath>
#include <cstdint>
#include <string>

enum class P2CaveBoundaryAction { Enter, Return };
// Read-only descriptor of the provider's current owned native scene.
struct P2CaveBoundarySnapshot {
    bool ready=false;
    P2CaveBoundaryAction action=P2CaveBoundaryAction::Enter;
    std::uint64_t seed=0,checkpointGeneration=0;
    unsigned long sceneGeneration=0;
    std::string cave,token;
    int floor=0;
    float x=0,z=0,radius=80;
};
inline bool p2CaveBoundaryMatches(const P2CaveBoundarySnapshot& selected,
    const P2CaveBoundarySnapshot& current) {
    return selected.ready && current.ready && current.sceneGeneration!=0
        && !current.token.empty() && current.cave=="forest_1"
        && ((current.floor==0 && current.action==P2CaveBoundaryAction::Enter)
            || (current.floor==1 && current.action==P2CaveBoundaryAction::Return))
        && std::isfinite(current.x) && std::isfinite(current.z)
        && current.radius==80.f
        && selected.action==current.action && selected.seed==current.seed
        && selected.checkpointGeneration==current.checkpointGeneration
        && selected.sceneGeneration==current.sceneGeneration
        && selected.cave==current.cave && selected.floor==current.floor
        && selected.token==current.token && selected.x==current.x
        && selected.z==current.z && selected.radius==current.radius;
}
