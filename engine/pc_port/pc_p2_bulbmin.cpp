#include "pc_p2_bulbmin.h"
#include "pc_p2_captain.h"
#include "pc_p2_kochappy.h"
#include "pc_p2_species.h"
#include "pc_p2_preview.h"
#include "pc_bbft.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "MapMgr.h"
#include "teki.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <string>
#include <unordered_map>

namespace {
constexpr float kPi = 3.14159265358979323846f;

P2BulbminBridge bridge;
bool active = false;
std::unordered_map<Piki*, std::uint32_t> idOfPiki;
std::unordered_map<std::uint32_t, Piki*> pikiOfId;
std::uint32_t nextId = 1;

// Default label for the Chappy-family actor standing in for the missing
// LeafChappy mother. The bridge registry holds the host pointer (compared,
// never dereferenced); this constant is only the proxy label reported to logs.
constexpr const char* kKochappyProxyModel = "kochappy_proxy";

std::uint32_t idFor(Piki* piki) {
    auto found = idOfPiki.find(piki);
    if (found != idOfPiki.end()) return found->second;
    const std::uint32_t id = nextId++;
    idOfPiki[piki] = id;
    pikiOfId[id] = piki;
    return id;
}
} // namespace

bool pc_p2_bulbmin_active() { return active; }

void pc_p2_bulbmin_reset() {
    bridge.reset();
    idOfPiki.clear();
    pikiOfId.clear();
    nextId = 1;
    active = false;
}

void pc_p2_bulbmin_setup() {
    pc_p2_bulbmin_reset();
    if (!pc_pikipelago_room_preview()) return;
    std::string body;
    if (const char* env = std::getenv("PIKMIN_P2_BULBMIN")) {
        if (env[0] != '\0') {
            body = env;
            // A bare positive epoch is accepted as shorthand.
            if (body.rfind("P2_BULBMIN_1", 0) != 0)
                body = "P2_BULBMIN_1 " + body + " "
                     + std::to_string(P2BULBMIN_MAX_DEPENDENTS);
        }
    }
    if (body.empty()) {
        std::ifstream file("p2-bulbmin.txt");
        if (!file.is_open()) return; // no config: inert no-op
        std::ostringstream stream;
        stream << file.rdbuf();
        if (file.bad()) {
            std::fprintf(stderr, "Cannot read P2 Bulbmin config\n");
            std::abort();
        }
        body = stream.str();
    }
    std::istringstream in(body);
    P2BulbminConfig config;
    if (!p2_bulbmin_read(in, config) || !bridge.setup(config, nullptr)) {
        std::fprintf(stderr, "Invalid P2 Bulbmin config\n");
        std::abort();
    }
    active = true;
    // Wire the recruited body to the lane-12 captain ownership table when the
    // live adapter is available (single-captain slot 0). With no NaviMgr the
    // whistle still converts the body in place.
    if (pc_p2_captain::setup_from_navi_mgr()) {
        if (P2CaptainAdapter* captainAdapter = pc_p2_captain::adapter())
            bridge.bindCaptains(captainAdapter->ownershipTable());
    }
    std::printf("P2_BULBMIN_READY mother_epoch=%llu dependents=%d behavior=policy_ledger proxy_model=%s proxy=1 live_leafchappy=0 captain_table=%d\n",
                static_cast<unsigned long long>(config.motherEpoch), config.maxDependents,
                config.motherModel.c_str(), bridge.hasCaptains() ? 1 : 0);
    std::fflush(stdout);
}

bool pc_p2_bulbmin_birth(Piki* bulbmin) {
    if (!active || !bulbmin) return false;
    const P2BulbminCommand command = bridge.birth(idFor(bulbmin));
    if (!command.accepted) return false;
    if (!pc_p2_is_bulbmin(bulbmin)) pc_p2_make_bulbmin(bulbmin);
    return true;
}

Piki* pc_p2_bulbmin_birth_dependent(Creature* leader, const Vector3f& motherPos,
                                    float faceDir, int index) {
    if (!active || !pikiMgr || !naviMgr || !leader
        || index < 0 || index >= P2BULBMIN_MAX_DEPENDENTS)
        return nullptr;
    Creature* born = pikiMgr->birth();
    if (!born || !born->isPiki()) return nullptr;
    Piki* bulbmin = static_cast<Piki*>(born);
    bulbmin->init(naviMgr->getNavi());
    pc_p2_make_bulbmin(bulbmin);
    bulbmin->mLeaderCreature = leader;
    const float angle = faceDir + kPi;
    const float modifier = 2.5f * index + 17.5f;
    Vector3f position(motherPos.x + modifier * std::sin(angle), motherPos.y,
                      motherPos.z + modifier * std::cos(angle));
    if (mapMgr) position.y = mapMgr->getMinY(position.x, position.z, true);
    bulbmin->inputPosition(position);
    if (!pc_p2_bulbmin_birth(bulbmin)) {
        bulbmin->setEraseKill();
        bulbmin->kill(false);
        return nullptr;
    }
    return bulbmin;
}

bool pc_p2_bulbmin_whistle(Piki* bulbmin) {
    if (!active || !bulbmin) return false;
    const auto found = idOfPiki.find(bulbmin);
    if (found == idOfPiki.end()) return false;
    const int captain = bridge.hasCaptains() ? P2CaptainA : P2CaptainInvalid;
    const P2BulbminCommand command = bridge.whistle(found->second, captain);
    if (!command.accepted) return false;
    bulbmin->mLeaderCreature = nullptr;
    if (naviMgr) {
        if (Navi* navi = naviMgr->getNavi()) bulbmin->mNavi = navi;
    }
    return true;
}

void pc_p2_bulbmin_forget(Piki* piki) {
    if (!active || !piki) return;
    const auto found = idOfPiki.find(piki);
    if (found == idOfPiki.end()) return;
    bridge.forget(found->second);
    pikiOfId.erase(found->second);
    idOfPiki.erase(found);
}

std::vector<std::uint32_t> pc_p2_bulbmin_transition(P2BulbminCaveTransition move) {
    const P2BulbminTransitionOut result = bridge.transition(move);
    for (const std::uint32_t id : result.removed) {
        auto found = pikiOfId.find(id);
        if (found != pikiOfId.end()) {
            idOfPiki.erase(found->second);
            pikiOfId.erase(found);
        }
    }
    return result.removed;
}

void pc_p2_bulbmin_bind_captain_table(P2CaptainOwnershipTable* ownership) {
    bridge.bindCaptains(ownership);
}

int pc_p2_bulbmin_dependent_count() {
    return active ? bridge.dependentCount() : 0;
}

namespace {
// Context handed to the driver's spawn callback for one birthChildren() pass.
struct DriveContext {
    Creature* leader = nullptr;
    Vector3f position;
    float faceDir = 0.0f;
};
DriveContext driveContext;

std::uint32_t driveSpawn(void*, int index) {
    Piki* p = pc_p2_bulbmin_birth_dependent(driveContext.leader, driveContext.position,
                                            driveContext.faceDir, index);
    return p ? idFor(p) : 0;
}
} // namespace

int pc_p2_bulbmin_drive_birth(Creature* leader, const Vector3f& leaderPos,
                              float faceDir, int requested) {
    if (!active) return 0;
    P2BulbminDriver driver;
    if (!driver.bind(&bridge, &driveSpawn, nullptr)) return 0;
    driveContext.leader = leader;
    driveContext.position = leaderPos;
    driveContext.faceDir = faceDir;
    return driver.birthFlock(requested);
}

int pc_p2_bulbmin_attach_mother_ex(Creature* mother, const char* model, bool proxy) {
    if (!active || !mother) return 0;
    const std::string label = (model && model[0] != '\0') ? model : kKochappyProxyModel;
    if (!bridge.registerMother(mother, label, proxy)) return 0;
    return pc_p2_bulbmin_drive_birth(mother, mother->getPosition(),
                                     mother->mFaceDirection,
                                     bridge.settings().maxDependents);
}

int pc_p2_bulbmin_attach_mother(Creature* mother) {
    return pc_p2_bulbmin_attach_mother_ex(mother, kKochappyProxyModel, true);
}

int pc_p2_bulbmin_attach_dedicated_mother() {
    if (!active) return 0;
    const char* env = std::getenv("PIKMIN_P2_BULBMIN_MOTHER");
    if (!env || env[0] == '\0') return 0;
    Creature* host = static_cast<Creature*>(pc_p2_kochappy_first_registered());
    if (!host) return 0;
    // Same-host re-registration only refreshes the label; it never re-births.
    return pc_p2_bulbmin_attach_mother_ex(host, env, true);
}

const char* pc_p2_bulbmin_mother_model() {
    if (!active || !bridge.hasMother()) return "none";
    return bridge.motherActorInfo().model.c_str();
}

bool pc_p2_bulbmin_has_mother() {
    return active && bridge.hasMother();
}

int pc_p2_bulbmin_call_pikis(Navi* navi, float radius) {
    if (!active || !navi || !pikiMgr || radius <= 0.0f) return 0;
    const float radius2 = radius * radius;
    int recruited = 0;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (!p || !p->isAlive()) continue;
        const auto found = idOfPiki.find(p);
        if (found == idOfPiki.end()) continue;
        if (bridge.phaseOf(found->second) != P2BulbminWild) continue;
        const Vector3f delta = p->mSRT.t - navi->mCursorWorldPos;
        if (delta.x * delta.x + delta.z * delta.z >= radius2) continue;
        if (pc_p2_bulbmin_whistle(p)) ++recruited;
    }
    return recruited;
}

int pc_p2_bulbmin_leader_died() {
    if (!active) return 0;
    const std::vector<std::uint32_t> released = bridge.leaderDied();
    bridge.clearMother();
    for (const std::uint32_t id : released) {
        auto found = pikiOfId.find(id);
        if (found == pikiOfId.end()) continue;
        if (found->second) found->second->mLeaderCreature = nullptr;
        idOfPiki.erase(found->second);
        pikiOfId.erase(found);
    }
    return static_cast<int>(released.size());
}

void pc_p2_bulbmin_proxy_forget(BTeki* mother) {
    if (!active || !mother) return;
    if (!bridge.motherIs(static_cast<void*>(mother))) return;
    pc_p2_bulbmin_leader_died();
}
