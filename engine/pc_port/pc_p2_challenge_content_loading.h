#pragma once
// Game-linked P2 challenge stage content-loading boot path (#694).
//
// Binds a selected P2 challenge stage floor to live content WITHOUT
// reimplementing generation, birth, or the arena: it validates a stage-content
// sidecar (stage key + floor + unit pool + roster spawns + anchor), runs the
// integrated cave-generator consumer (#129, pc_p2_cave_generate_run) over the
// caller-staged p2-cave-generate.txt manifest, verifies the staged spawn
// intents cover the stage roster, and exposes read-only liveness probes
// (live squad, live actors, finite positions) for the guarded fixture.
// Species-resolved behavior belongs to the per-stage P1 lanes (downstream
// #533/#561/#562), not to this provider. Every function is fail-closed on
// malformed/missing input and a no-op without a valid selection.
#include <string>
#include <vector>

namespace p2_challenge_content {

// One roster spawn intent from the stage-content sidecar.
struct RosterSpawn { std::string id; int count = 0; };

// Validated stage-content expectation (bounding, not owning, engine state).
struct Expectation {
    std::string caveId;
    int floor = 0;
    std::string pool;
    std::vector<RosterSpawn> roster;
    std::string anchor;
    bool valid = false;
};

// Read + validate p2-challenge-content.txt. Returns false (and emits
// P2_CHALLENGE_CONTENT_REFUSED) on missing/malformed input; never fabricates.
bool select(const char* sidecarPath, Expectation& out);

// Verify staged spawn intents (from p2-cave-generate.txt) cover the roster.
// Emits P2_CHALLENGE_CONTENT_SPAWN_COVERED per roster id on success.
bool verifyCoverage(const Expectation& expect);

// Read-only liveness probes for the fixture (no writes, no spawns).
int liveSquad();
int liveActors();
bool positionsFinite();

// Reset module state (forget selection). Additive; never touches engine state.
void reset();

} // namespace p2_challenge_content