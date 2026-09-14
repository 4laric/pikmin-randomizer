// Honeywisp (Qurione, EnemyID 16) source lifecycle FSM for the flying family
// lane (#166, disjoint Honeywisp slice). Implements the source
// QurioneState.cpp machine (Stay/Appear/Disappear/Move/Drop/Dead) on the
// TEKI_Qurione host, driven by p2-qurione-bank.txt / p2-qurione-actors.txt
// written by the qurione arena. Source revision
// 632af93787b9c95b63f0c13be32b161375ce3a96.
//
// Port adaptations (recorded, not retail-faithful):
//   * The carried Egg (EnemyID_Egg 37, joint "water") is reported through
//     P2_QURIONE_EGG action=attach|drop markers. The shared Egg projectile is
//     owned by lane 20, so no duplicate primitive is spawned here; the host
//     reward remains P1 nectar.
//   * The qurione bank does not carry KEYEVENT frames, so the Drop release
//     fires at half the damage clip (recorded adaptation).
//   * Sight is a distance test (SIGHT); the source uses viewAngle *
//     sightRadius through EnemyFunc::getNearestPikminOrNavi.
//   * Glow/appear/disappear/hit effects and the scale grow/shrink are not
//     ported; ModelHidden is honoured for Stay.
// Every hook is a no-op for unregistered actors; ordinary P1 play is untouched.
#include "pc_p2_qurione.h"
#include "pc_p2_qurione_policy.h"
#include "pc_p2_enemy.h"
#include "pc_p2_sheargrub.h"
#include "teki.h"
#include "system.h"
#include "MapMgr.h"
#include "Generator.h"
#include "Shape.h"
#include "Texture.h"
#include "Material.h"
#include "gameflow.h"
#include "Graphics.h"
#include "Camera.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include <map>
#include <set>
#include <vector>
#include <string>
#include <fstream>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>

namespace {
enum QState { QS_STAY = 0, QS_APPEAR = 1, QS_DISAPPEAR = 2, QS_MOVE = 3, QS_DROP = 4, QS_DEAD = 5 };

const char* qStateName(QState s) {
    switch (s) {
    case QS_STAY: return "stay";
    case QS_APPEAR: return "appear";
    case QS_DISAPPEAR: return "disappear";
    case QS_MOVE: return "move";
    case QS_DROP: return "drop";
    case QS_DEAD: return "dead";
    default: return "null";
    }
}

// Source values (Qurione.cpp / Qurione.h proper parms).
constexpr float LIFE = 9999.0f;          // invulnerable source actor
constexpr float FLIGHT_HEIGHT = 60.0f;   // fp01
constexpr float SLIDE_DIST = 30.0f;      // birth slideDist
constexpr float FLY_DIST = 200.0f;       // birth flyDist
constexpr float DEATH_RATE = 100.0f;     // fp04
constexpr float DEATH_TIME = 1.0f;       // fp05
constexpr float SIGHT = 200.0f;          // port adaptation
constexpr float MOVE_SPEED = 80.0f;      // port adaptation (source moveSpeed class)
constexpr float PITCH_RATE = 2.5f;       // fp02
constexpr float PITCH_AMP = 20.0f;       // fp03
constexpr float TURN_RATE = 3.14159265f; // unused fallback heading rate
constexpr float HIT_RADIUS = 30.0f;      // Piki contact -> Drop
constexpr float DROP_FRACTION = 0.5f;    // recorded adaptation (no bank events)

struct Wisp {
    QState state = QS_STAY;
    float stateTime = 0.0f;
    float timer = 0.0f;
    Vector3f spawn[2];
    int spawnIndex = 0;
    float heading = 0.0f;
    float pitch = 0.0f;
    bool eggAttached = true;
    bool dropFired = false;
    bool deadLogged = false;
    float logTimer = 0.0f;
    std::string clip = "appear1";
    float phase = 0.0f;
};

std::map<std::string, std::vector<Shape*>> clips;
std::map<std::string, p2animation::Clip> timing;
std::map<PelletView*, Wisp> actors;
bool ready = false;
bool logged[2] = {false, false};

float distXZ(const Vector3f& a, const Vector3f& b) {
    const float dx = a.x - b.x, dz = a.z - b.z;
    return std::sqrt(dx * dx + dz * dz);
}

float clipDuration(const std::string& name) {
    auto it = timing.find(name);
    return it == timing.end() || it->second.duration <= 0 ? 1.0f : float(it->second.duration) / 30.0f;
}

Creature* nearestTarget(const Vector3f& pos) {
    Creature* best = nullptr;
    float bestSq = SIGHT * SIGHT;
    if (naviMgr) {
        Navi* n = naviMgr->getNavi();
        if (n && n->isAlive()) {
            const Vector3f p = n->getPosition();
            const float dx = p.x - pos.x, dz = p.z - pos.z;
            const float d = dx * dx + dz * dz;
            if (d < bestSq) { bestSq = d; best = n; }
        }
    }
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (!p || !p->isAlive()) continue;
            const Vector3f q = p->getPosition();
            const float dx = q.x - pos.x, dz = q.z - pos.z;
            const float d = dx * dx + dz * dz;
            if (d < bestSq) { bestSq = d; best = p; }
        }
    }
    return best;
}

bool pikiContact(const Vector3f& pos) {
    if (!pikiMgr) return false;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (p && p->isAlive() && distXZ(p->getPosition(), pos) < HIT_RADIUS) return true;
    }
    return false;
}

void enter(Wisp& w, QState state, const char* clip) {
    w.state = state;
    w.stateTime = 0.0f;
    if (clip) w.clip = clip;
}
}

void pc_p2_qurione_reset() {
    clips.clear();
    timing.clear();
    actors.clear();
    ready = false;
    logged[0] = logged[1] = false;
}

void pc_p2_qurione_forget(BTeki* actor) { actors.erase(static_cast<PelletView*>(actor)); }
const char* pc_p2_qurione_name(PelletView* actor) { return actors.count(actor) ? "Honeywisp (source FSM)" : nullptr; }

float pc_p2_qurione_param_f(const BTeki* actor, int idx, float fallback) {
    if (!ready || !actors.count(static_cast<PelletView*>(const_cast<BTeki*>(actor)))) return fallback;
    if (idx == TPF_Life) return LIFE;
    if (idx == TPF_LifeRecoverRate) return 0.0f;
    switch (idx) {
    case TPF_VisibleRange:
    case TPF_VisibleAngle:
    case TPF_AttackableRange:
    case TPF_AttackableAngle:
    case TPF_AttackRange:
    case TPF_AttackHitRange:
    case TPF_AttackPower:
    case TPF_DangerTerritoryRange:
    case TPF_SafetyTerritoryRange:
        return 0.0f;
    default:
        return fallback;
    }
}

void pc_p2_qurione_setup() {
    pc_p2_qurione_reset();
    std::ifstream bank("p2-qurione-bank.txt"), bindings("p2-qurione-actors.txt");
    if (!bank && !bindings) return;
    if (!tekiMgr) return;
    std::vector<p2animation::Clip> manifest;
    std::set<std::uint32_t> wanted;
    if (!bank || !bindings || !p2qurione::bank(bank, manifest) || !p2qurione::bindings(bindings, wanted)) std::abort();
    // Reject identity overlap and unresolved/duplicate generator IDs before loading.
    std::vector<Teki*> selected;
    std::set<std::uint32_t> seen;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        Teki* actor = static_cast<Teki*>(*it);
        if (!actor || !actor->mGenerator || !wanted.count(actor->mGenerator->_70)) continue;
        if (!seen.insert(actor->mGenerator->_70).second || actor->mTekiType != TEKI_Qurione
            || pc_p2_enemy_name(actor) || pc_p2_sheargrub_name(actor)) {
            std::abort();
        }
        selected.push_back(actor);
    }
    if (seen != wanted) std::abort();
    size_t total = 0, poses = 0;
    std::vector<unsigned char> reference;
    for (const auto& clip : manifest) {
        size_t clipBytes = 0;
        for (int i = 0; i < clip.count; ++i) {
            char path[160];
            std::snprintf(path, sizeof(path), "assets/dataDir/courses/pikmin2room/qurione_%s_%02d.mod", clip.name.c_str(), i);
            std::ifstream file(path, std::ios::binary | std::ios::ate);
            if (!file) std::abort();
            auto bytes = file.tellg();
            if (bytes <= 0 || size_t(bytes) > p2animation::ClipBytes - clipBytes || size_t(bytes) > p2animation::TotalBytes - total) std::abort();
            clipBytes += size_t(bytes);
            total += size_t(bytes);
            file.seekg(0);
            std::vector<unsigned char> data(size_t(bytes), 0), resources;
            if (!file.read(reinterpret_cast<char*>(data.data()), bytes) || !p2animation::resources(data, resources)) std::abort();
            if (!reference.empty() && reference != resources) std::abort();
            reference = resources;
        }
    }
    const auto started = std::chrono::steady_clock::now();
    Shape* shared = nullptr;
    int attachments = 0;
    for (const auto& clip : manifest) {
        timing[clip.name] = clip;
        for (int i = 0; i < clip.count; ++i) {
            char path[128];
            std::snprintf(path, sizeof(path), "courses/pikmin2room/qurione_%s_%02d.mod", clip.name.c_str(), i);
            Shape* shape = gameflow.loadShape(path, true);
            if (!shape) std::abort();
            if (!shared) {
                shared = shape;
                for (int t = 0; t < shape->mTexAttrCount; ++t) {
                    if (shape->mTexAttrList[t].mTexture) { shape->mTexAttrList[t].mTexture->attach(); ++attachments; }
                }
            } else {
                if (shape->mMaterialCount != shared->mMaterialCount || shape->mTexAttrCount != shared->mTexAttrCount
                    || shape->mTevInfoCount != shared->mTevInfoCount) {
                    std::abort();
                }
                for (int j = 0; j < shape->mTotalMatpolyCount; ++j) {
                    auto* poly = shape->mMatpolyList[j];
                    if (!poly || !poly->mMaterial) continue;
                    int material = -1;
                    for (int m = 0; m < shape->mMaterialCount; ++m) {
                        if (poly->mMaterial == &shape->mMaterialList[m]) material = m;
                    }
                    if (material < 0) std::abort();
                    poly->mMaterial = &shared->mMaterialList[material];
                }
                shape->mMaterialList = shared->mMaterialList;
                shape->mTexAttrList = shared->mTexAttrList;
                shape->mTevInfoList = shared->mTevInfoList;
            }
            clips[clip.name].push_back(shape);
            ++poses;
        }
    }
    for (Teki* actor : selected) {
        Wisp& w = actors[static_cast<PelletView*>(actor)];
        const Vector3f pos = actor->getPosition();
        const float dir = actor->getDirection();
        w.heading = dir;
        w.spawn[0] = Vector3f(pos.x, pos.y + FLIGHT_HEIGHT, pos.z);
        const float flyX = FLY_DIST * std::sin(dir);
        const float flyZ = FLY_DIST * std::cos(dir);
        const float orth = dir - HALF_PI;
        const float slideX = SLIDE_DIST * std::sin(orth);
        const float slideZ = SLIDE_DIST * std::cos(orth);
        w.spawn[1] = Vector3f(w.spawn[0].x + flyX + slideX, w.spawn[0].y, w.spawn[0].z + flyZ + slideZ);
        w.spawnIndex = 0;
        w.state = QS_STAY;
        w.stateTime = 0.0f;
        w.timer = 0.0f;
        w.clip = "appear1";
        actor->mHealth = LIFE;
        const unsigned gen = actor->mGenerator->_70;
        std::printf("P2_QURIONE_BIND generator=%u source_id=16 visual_only=0\n", gen);
        std::printf("P2_ENEMY_READY species=Qurione native_family=Qurione generator=%u x=%.7f y=%.7f z=%.7f "
                    "health=%.1f max_health=%.1f behavior=native source_FSM=implemented reward=P2_Egg\n",
                    gen, pos.x, pos.y, pos.z, actor->mHealth, LIFE);
        std::printf("P2_QURIONE_EGG generator=%u action=attach\n", gen);
    }
    std::printf("P2_QURIONE_BANK poses=%zu mod_bytes=%zu texture_attach_calls=%d load_seconds=%.3f\n",
                poses, total, attachments, std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count());
    ready = true;
}

bool pc_p2_qurione_suppress_ai(const BTeki* actor) {
    return ready && actors.count(static_cast<PelletView*>(const_cast<BTeki*>(actor))) != 0;
}

void pc_p2_qurione_update(BTeki* actor) {
    if (!ready) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    Wisp& w = it->second;
    const float dt = gsys->getFrameTime();
    if (dt <= 0.0f || dt > 0.5f) return;
    const unsigned gen = actor->mGenerator ? actor->mGenerator->_70 : 0u;
    const Vector3f pos = actor->getPosition();
    w.stateTime += dt;
    switch (w.state) {
    case QS_STAY:
        actor->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
        actor->mVelocity.set(Vector3f(0.0f, 0.0f, 0.0f));
        w.timer += dt;
        if (w.timer > 1.0f && nearestTarget(pos)) {
            std::printf("P2_QURIONE_STATE generator=%u state=appear\n", gen);
            enter(w, QS_APPEAR, "appear1");
        }
        break;
    case QS_APPEAR:
        actor->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
        if (w.stateTime >= clipDuration("appear1")) {
            std::printf("P2_QURIONE_STATE generator=%u state=move\n", gen);
            enter(w, QS_MOVE, "waitl");
        }
        break;
    case QS_MOVE: {
        // Source moveFaceDir: forward speed plus a pitch bob about
        // mapMinY + fP03 * sin(mPitchRatio) + fP01 (flight height).
        w.pitch += PITCH_RATE * dt;
        if (w.pitch > TAU) w.pitch -= TAU;
        const float minY = mapMgr ? mapMgr->getMinY(pos.x, pos.z, true) : pos.y - FLIGHT_HEIGHT;
        const float targetY = minY + (PITCH_AMP * std::sin(w.pitch) + FLIGHT_HEIGHT);
        const float vy = 2.5f * (targetY - pos.y);
        const Vector3f drive(std::sin(w.heading) * MOVE_SPEED, vy, std::cos(w.heading) * MOVE_SPEED);
        actor->inputDrive(drive);
        actor->mVelocity.set(drive);
        if (pikiContact(pos)) {
            std::printf("P2_QURIONE_STATE generator=%u state=drop\n", gen);
            enter(w, QS_DROP, "damage");
        } else if (distXZ(pos, w.spawn[w.spawnIndex]) > FLY_DIST) {
            std::printf("P2_QURIONE_STATE generator=%u state=disappear\n", gen);
            enter(w, QS_DISAPPEAR, "hide1");
        }
        break;
    }
    case QS_DISAPPEAR:
        actor->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
        actor->mVelocity.set(Vector3f(0.0f, 0.0f, 0.0f));
        if (w.stateTime >= clipDuration("hide1")) {
            w.spawnIndex ^= 1;
            w.heading += PI;
            actor->setDirection(w.heading);
            std::printf("P2_QURIONE_STATE generator=%u state=stay\n", gen);
            enter(w, QS_STAY, "appear1");
            w.timer = 0.0f;
        }
        break;
    case QS_DROP:
        actor->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
        actor->mVelocity.set(Vector3f(0.0f, 0.0f, 0.0f));
        if (!w.dropFired && w.stateTime >= clipDuration("damage") * DROP_FRACTION) {
            w.dropFired = true;
            w.eggAttached = false;
            std::printf("P2_QURIONE_EGG generator=%u action=drop\n", gen);
        }
        if (w.stateTime >= clipDuration("damage")) {
            std::printf("P2_QURIONE_STATE generator=%u state=dead\n", gen);
            enter(w, QS_DEAD, "run");
        }
        break;
    case QS_DEAD: {
        const Vector3f up(0.0f, DEATH_RATE, 0.0f);
        actor->inputDrive(up);
        actor->mVelocity.set(up);
        if (!w.deadLogged && w.stateTime > DEATH_TIME) {
            w.deadLogged = true;
            std::printf("P2_QURIONE_DEAD generator=%u source_id=16\n", gen);
        }
        if (w.stateTime >= DEATH_TIME) actor->die();
        break;
    }
    default:
        break;
    }
    {
        const float duration = clipDuration(w.clip);
        w.phase = duration > 0.0f ? w.stateTime / duration : 0.0f;
        if (w.phase > 1.0f) w.phase = 1.0f;
    }
    w.logTimer += dt;
    if (w.logTimer >= 1.0f) {
        w.logTimer = 0.0f;
        std::printf("P2_QURIONE_POS generator=%u state=%s clip=%s phase=%.2f x=%.2f y=%.2f z=%.2f\n",
                    gen, qStateName(w.state), w.clip.c_str(), w.phase, pos.x, pos.y, pos.z);
        std::fflush(stdout);
    }
}

bool pc_p2_qurione_draw(BTeki* actor, Graphics& gfx, const Matrix4f& matrix, bool corpse) {
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return false;
    if (!logged[corpse ? 1 : 0]) { std::printf("P2_QURIONE_DRAW corpse=%d\n", int(corpse)); logged[corpse ? 1 : 0] = true; }
    if (corpse) return false;
    const Wisp& w = it->second;
    if (w.state == QS_STAY) return true;
    auto bankIt = clips.find(w.clip);
    if (bankIt == clips.end() || bankIt->second.empty()) return false;
    const p2animation::Clip& clip = timing.at(w.clip);
    size_t index = clip.index(w.phase, false);
    if (index >= bankIt->second.size()) index = bankIt->second.size() - 1;
    Shape* shape = bankIt->second[index];
    shape->updateAnim(gfx, matrix, nullptr, actor);
    shape->drawshape(gfx, *gfx.mCamera, nullptr);
    return true;
}

