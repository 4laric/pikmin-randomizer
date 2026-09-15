#include "pc_p2_waterwraith_register.h"

#include "pc_p2_waterwraith_actor.h"
#include "pc_p2_waterwraith_encounter.h"
#include "pc_p2_waterwraith_visual.h"

#include "Graphics.h"
#include "Matrix4f.h"
#include "Pellet.h"

#include <cmath>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

namespace {
constexpr float kSourceDelta = 1.0f / 30.0f;
constexpr int kMaxTicksPerFrame = 4;
constexpr float kPi = 3.14159265358979323846f;
constexpr std::streamoff kProfileBytes = 4096;

struct RegisterState {
    bool ready = false;
    bool visualReady = false;
    bool finished = false;       // source Dead KEYEVENT_END reached
    bool corpseSpawned = false;  // Dead KEYEVENT_5 stand-in drop spawned once
    P2WaterwraithRegisterPlacement placement;
    P2WaterwraithActor actor;
    P2WaterwraithActorOutput out;
    std::uint64_t actorTicks = 0;
    double debt = 0.0;
};

RegisterState sState;

// Source Dead KEYEVENT_5 releases the held treasure; the P1 host has no P2
// treasure item, so a labelled number-pellet stand-in is spawned at the wraith
// position (the same adaptation the Kogane lane records for its cave treasure).
// Lane 06 owns the durable exactly-once receipt path; this is the on-field drop.
void spawnWraithCorpse()
{
    sState.corpseSpawned = true;
    if (!pelletMgr) {
        std::printf("P2_WATERWRAITH_CORPSE skipped=no_pelletMgr\n");
        return;
    }
    const Vector3f base(sState.placement.placement.x, sState.placement.placement.y,
                        sState.placement.placement.z);
    const P2WaterwraithVec3 local = sState.actor.position();
    Pellet* pellet = pelletMgr->newNumberPellet(PELCOLOR_Blue, NUMPEL_OnePellet);
    if (!pellet) {
        std::printf("P2_WATERWRAITH_CORPSE skipped=no_pellet\n");
        return;
    }
    const Vector3f pos(base.x + local.x, base.y + local.y + 10.0f, base.z + local.z);
    pellet->init(pos);
    pellet->mVelocity.set(0.0f, 100.0f, 0.0f);
    pellet->startAI(0);
    std::printf("P2_WATERWRAITH_CORPSE pos=%.3f,%.3f,%.3f standin=number_pellet\n", pos.x, pos.y,
                pos.z);
    std::fflush(stdout);
}

bool lineExhausted(std::istringstream& values)
{
    std::string extra;
    return !(values >> extra);
}

bool finiteCoord(float value)
{
    return std::isfinite(value) && std::fabs(value) <= 100000.0f;
}

bool badProfile(P2WaterwraithRegisterPlacement& out)
{
    out = P2WaterwraithRegisterPlacement{};
    return false;
}
} // namespace

bool p2_waterwraith_register_parse(const char* profilePath, P2WaterwraithRegisterPlacement& out)
{
    out = P2WaterwraithRegisterPlacement{};
    if (!profilePath || !*profilePath) {
        return false;
    }
    std::ifstream input(profilePath);
    if (!input) {
        return false;
    }
    input.seekg(0, std::ios::end);
    if (input.tellg() < 0 || input.tellg() > kProfileBytes) {
        return false;
    }
    input.seekg(0);

    std::string line;
    if (!std::getline(input, line) || line != "P2_WATERWRAITH_ACTOR_1") {
        return false;
    }
    bool havePlacement = false;
    bool haveTarget = false;
    bool haveSpeed = false;
    while (std::getline(input, line)) {
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        if (line.empty()) {
            continue;
        }
        std::istringstream values(line);
        std::string key;
        values >> key;
        if (key == "placement") {
            float x = 0.0f, y = 0.0f, z = 0.0f, yaw = 0.0f;
            if (havePlacement || !(values >> x >> y >> z >> yaw) || !finiteCoord(x) || !finiteCoord(y)
                || !finiteCoord(z) || !std::isfinite(yaw) || std::fabs(yaw) > kPi
                || !lineExhausted(values)) {
                return badProfile(out);
            }
            out.placement = P2WaterwraithVec3{ x, y, z };
            out.yaw = yaw;
            havePlacement = true;
        } else if (key == "target") {
            float x = 0.0f, y = 0.0f, z = 0.0f;
            if (haveTarget || !(values >> x >> y >> z) || !finiteCoord(x) || !finiteCoord(y)
                || !finiteCoord(z) || !lineExhausted(values)) {
                return badProfile(out);
            }
            out.target = P2WaterwraithVec3{ x, y, z };
            haveTarget = true;
        } else if (key == "speed") {
            float speed = 0.0f;
            if (haveSpeed || !(values >> speed) || !std::isfinite(speed) || speed <= 0.0f
                || speed > 1000.0f || !lineExhausted(values)) {
                return badProfile(out);
            }
            out.travelSpeed = speed;
            haveSpeed = true;
        } else {
            return badProfile(out);
        }
    }
    if (!havePlacement || !haveTarget) {
        return badProfile(out);
    }
    return true;
}

bool pc_p2_waterwraith_register_setup(const char* profilePath)
{
    pc_p2_waterwraith_register_reset();
    P2WaterwraithRegisterPlacement placement;
    if (!p2_waterwraith_register_parse(profilePath, placement)) {
        return false;
    }

    P2WaterwraithActorParms parms;
    parms.startPhase = P2BM_Fall; // source onInit unless cave y_01
    parms.travelSpeed = placement.travelSpeed;

    sState.placement = placement;
    sState.actor = P2WaterwraithActor(parms);

    P2WaterwraithWaypoint route[1];
    route[0].position = P2WaterwraithVec3{ placement.target.x - placement.placement.x, 0.0f,
                                           placement.target.z - placement.placement.z };
    if (sState.actor.setRoute(route, 1) != 1) {
        pc_p2_waterwraith_register_reset();
        return false;
    }
    if (!sState.actor.alive() || !sState.actor.rig().alive()
        || !sState.actor.rig().attachedToOwner()) {
        pc_p2_waterwraith_register_reset();
        return false;
    }

    // The visual bank is a display slice; a missing profile leaves the seam
    // tumbling/drawing zero rather than rejecting the actor registration.
    sState.visualReady = pc_p2_waterwraith_visual_setup("p2-waterwraith-visual.txt");
    if (sState.visualReady) {
        pc_p2_waterwraith_visual_play("BlackMan", "kagebozu_walk", true);
        pc_p2_waterwraith_visual_play("Tyre", "tyre_move", true);
    }

    sState.ready = true;
    std::printf("P2_WATERWRAITH_REGISTER_PROFILE placement=%.3f,%.3f,%.3f yaw=%.4f "
                "target=%.3f,%.3f,%.3f speed=%.3f visual=%d\n",
                placement.placement.x, placement.placement.y, placement.placement.z,
                placement.yaw, placement.target.x, placement.target.y, placement.target.z,
                placement.travelSpeed, sState.visualReady ? 1 : 0);
    return true;
}

void pc_p2_waterwraith_register_reset()
{
    sState = RegisterState();
    pc_p2_waterwraith_visual_reset();
    pc_p2_waterwraith_encounter_reset();
}

bool pc_p2_waterwraith_register_ready()
{
    return sState.ready;
}

bool pc_p2_waterwraith_register_finished()
{
    return sState.finished;
}

bool pc_p2_waterwraith_register_corpse_spawned()
{
    return sState.corpseSpawned;
}

void pc_p2_waterwraith_register_tick(float delta)
{
    if (!sState.ready || sState.finished || !std::isfinite(delta) || delta <= 0.0f) {
        return;
    }
    sState.debt += static_cast<double>(delta);
    int ticks = static_cast<int>(sState.debt / static_cast<double>(kSourceDelta));
    if (ticks > kMaxTicksPerFrame) {
        ticks = kMaxTicksPerFrame;
    }
    sState.debt -= ticks * static_cast<double>(kSourceDelta);
    for (int i = 0; i < ticks; ++i) {
        P2WaterwraithActorInput in;
        // Fixed host script: floor contact resolves the roller, the fall end
        // lifts the wraith into Recover, Recover's end key restarts the roll
        // and the wraith walks the host route at fp05 travel speed.
        if (sState.actorTicks == 0) {
            in.landFloorContact = true;
        } else if (sState.actorTicks == 1) {
            in.isFallEnd = true;
        } else if (sState.actorTicks == 2) {
            in.animEnd = true;
        }
        // Live-squad combat: Purple stun/damage and roller crush, plus the
        // roller death script (dismount -> tyre_getoff -> child removal) and
        // then the wrapped-body death once the child is gone.
        pc_p2_waterwraith_encounter_step(sState.actor, in);
        sState.actor.tick(in, sState.out, kSourceDelta);
        ++sState.actorTicks;
        // Death side effects (source Dead key sequence, see encounter.cpp):
        // KEYEVENT_5 drops the stand-in corpse; KEYEVENT_END tears the seam down.
        if (sState.out.releaseTreasure && !sState.corpseSpawned) {
            spawnWraithCorpse();
        }
        if (sState.out.killRequested) {
            sState.finished = true;
            std::printf("P2_WATERWRAITH_FINISHED tick=%llu bodyHealth=%.1f\n",
                        static_cast<unsigned long long>(sState.actorTicks),
                        sState.actor.bodyHealth());
            std::fflush(stdout);
            break;
        }
        if (sState.visualReady) {
            pc_p2_waterwraith_visual_update();
        }
    }
}

int pc_p2_waterwraith_register_draw(Graphics& gfx, const Matrix4f& world)
{
    if (!sState.ready || sState.finished || !sState.visualReady) {
        return 0;
    }
    const P2WaterwraithVec3 base = sState.placement.placement;
    const P2WaterwraithVec3 wraith = sState.actor.position();
    const P2WaterwraithVec3 roller = sState.actor.rig().position();

    Matrix4f local;
    Matrix4f placed;
    local.makeSRT(Vector3f(1.0f, 1.0f, 1.0f),
                  Vector3f(0.0f, sState.placement.yaw + sState.actor.facing(), 0.0f),
                  Vector3f(base.x + wraith.x, base.y + wraith.y, base.z + wraith.z));
    world.multiplyTo(local, placed);
    int drawn = pc_p2_waterwraith_visual_draw_species(gfx, "BlackMan", placed);

    local.makeSRT(Vector3f(1.0f, 1.0f, 1.0f),
                  Vector3f(0.0f, sState.placement.yaw, sState.actor.rig().rollAngle()),
                  Vector3f(base.x + roller.x, base.y + roller.y, base.z + roller.z));
    world.multiplyTo(local, placed);
    drawn += pc_p2_waterwraith_visual_draw_species(gfx, "Tyre", placed);
    return drawn;
}

std::uint64_t pc_p2_waterwraith_register_ticks()
{
    return sState.actorTicks;
}

float pc_p2_waterwraith_register_distance()
{
    return sState.actor.rig().travelledDistance();
}

float pc_p2_waterwraith_register_roll()
{
    return sState.actor.rig().rollAngle();
}

const char* pc_p2_waterwraith_register_phase()
{
    return sState.actor.phaseName();
}

P2WaterwraithVec3 pc_p2_waterwraith_register_wraith_position()
{
    return sState.actor.position();
}

P2WaterwraithVec3 pc_p2_waterwraith_register_roller_position()
{
    return sState.actor.rig().position();
}

bool pc_p2_waterwraith_register_attached()
{
    return sState.actor.rig().alive() && sState.actor.rig().attachedToOwner();
}

float pc_p2_waterwraith_register_tyre_health()
{
    return sState.actor.rig().tyreHealth();
}

float pc_p2_waterwraith_register_body_health()
{
    return sState.actor.bodyHealth();
}
