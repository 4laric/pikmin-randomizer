// Lane 45 (#483, cave wave #468): engine glue for real cave-unit geometry and a
// real electric-gate actor.
//
// Reads the host bridge's P2_CAVE_GEOMETRY_1 plan, loads each real converted unit
// model through the port's own model path (``gameflow.loadShape``) and draws it at
// the node's grid transform instead of lane 44's proxy square. The electric leaf
// door instantiates a real gate actor that carries the converted P2 electric-gate
// model, opens when an electric-immune Pikmin reaches it and otherwise delivers
// the lane-10 ``InteractDenki`` receiver. Everything is labelled real/proxy in the
// per-node markers; a failed model load leaves the node a proxy and is logged.
#include "pc_p2_cave_geometry_engine.h"

#include "Graphics.h"
#include "Camera.h"
#include "Shape.h"
#include "MapMgr.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Interactions.h"
#include "gameflow.h"
#include "system.h"
#include "pc_p2_species.h"
#include "pc_p2_hazard_emitter.h"
#include "pc_p2_cave_carry_engine.h"  // lane 50 (#488): carry blocking owns plan gates

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#include <vector>

namespace {
P2CaveGeometryPlan geometry;
bool geometryActive = false;

struct NodeShape {
    std::string id;
    Shape* shape = nullptr;
};

struct GateActor {
    std::string node_id;
    std::string actor;
    Vector3f position;
    Shape* shape = nullptr;
    bool open = false;
    float cooldown = 0.0f;
};

std::vector<NodeShape> nodeShapes;
std::vector<GateActor> gateActors;

// A node is real only when its model actually loaded; otherwise it stays proxy.
bool nodeLoaded(const std::string& id)
{
    for (const NodeShape& entry : nodeShapes) {
        if (entry.id == id && entry.shape) return true;
    }
    return false;
}

const P2CaveGeometryGate* gateRecordFor(const std::string& node_id)
{
    for (const P2CaveGeometryGate& gate : geometry.gates) {
        if (gate.node_id == node_id) return &gate;
    }
    return nullptr;
}

Vector3f worldPosition(const P2CaveGeometryNode& node)
{
    const float x = static_cast<float>(node.gx);
    const float z = static_cast<float>(node.gz);
    const float y = mapMgr ? mapMgr->getMinY(x, z, true) : 0.f;
    return Vector3f(x, y, z);
}

void drawShapeAt(Graphics& gfx, Shape* shape, const Vector3f& position, float yaw)
{
    if (!shape) return;
    Matrix4f world, view;
    world.makeSRT(Vector3f(1, 1, 1), Vector3f(0, yaw, 0), position);
    gfx.mCamera->mLookAtMtx.multiplyTo(world, view);
    shape->updateAnim(gfx, view, nullptr, nullptr);
    shape->drawshape(gfx, *gfx.mCamera, nullptr);
}

Shape* loadShape(const std::string& model)
{
    if (model.empty()) return nullptr;
    Shape* shape = gameflow.loadShape(model.c_str(), true);
    if (!shape) return nullptr;
    for (int i = 0; i < shape->mTexAttrCount; ++i) {
        if (shape->mTexAttrList[i].mTexture) shape->mTexAttrList[i].mTexture->attach();
    }
    return shape;
}

Piki* nearestPikmin(const Vector3f& position, float radius, bool immuneOnly, bool& immune)
{
    Piki* best = nullptr;
    float bestSq = radius * radius;
    immune = false;
    if (!pikiMgr) return nullptr;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* piki = static_cast<Piki*>(*it);
        if (!piki || !piki->isAlive()) continue;
        const int species = pc_p2_species(piki);
        const bool pikminImmune = p2_species_immune(species, P2HazardElectric);
        if (immuneOnly && !pikminImmune) continue;
        const float dx = piki->getPosition().x - position.x;
        const float dz = piki->getPosition().z - position.z;
        const float distance = dx * dx + dz * dz;
        if (distance >= bestSq) continue;
        bestSq = distance;
        best = piki;
        immune = pikminImmune;
    }
    return best;
}
}  // namespace

bool pc_p2_cave_geometry_active() { return geometryActive; }

const P2CaveGeometryPlan* pc_p2_cave_geometry_plan()
{
    return geometryActive ? &geometry : nullptr;
}

void pc_p2_cave_geometry_shutdown()
{
    geometry = P2CaveGeometryPlan{};
    geometryActive = false;
    nodeShapes.clear();
    gateActors.clear();
}

void pc_p2_cave_geometry_setup()
{
    geometry = P2CaveGeometryPlan{};
    geometryActive = false;
    nodeShapes.clear();
    gateActors.clear();
    const char* env = std::getenv("PIKMIN_CAVE_GEOMETRY");
    const std::string path = env && env[0] ? env : "p2-cave-geometry.txt";
    std::ifstream in(path);
    if (!in) return;
    std::string error;
    if (!p2CaveGeometryParse(in, geometry, error)) {
        std::printf("P2_CAVE_GEOMETRY FAILED reason=%s\n", error.c_str());
        std::fflush(stdout);
        return;
    }
    const char* base = std::getenv("PIKMIN_CAVE_GEOMETRY_MODELS");
    const std::string prefix = base && base[0] ? std::string(base) : std::string();
    int loaded = 0;
    for (const P2CaveGeometryNode& node : geometry.nodes) {
        if (!node.real || node.model.empty()) continue;
        Shape* shape = loadShape(prefix + node.model);
        if (!shape) {
            std::printf("P2_CAVE_GEOMETRY_MODEL_FAILED id=%s model=%s\n", node.id.c_str(),
                        (prefix + node.model).c_str());
            continue;
        }
        nodeShapes.push_back({node.id, shape});
        ++loaded;
        std::printf("%s\n", p2CaveGeometryNodeMarker(node).c_str());
    }
    for (const P2CaveGeometryGate& gate : geometry.gates) {
        if (!gate.placed) continue;
        const P2CaveGeometryNode* node = p2CaveGeometryFindNode(geometry, gate.node_id);
        GateActor actor;
        actor.node_id = gate.node_id;
        actor.actor = gate.actor;
        actor.position = node ? worldPosition(*node) : Vector3f(0, 0, 0);
        actor.shape = loadShape(prefix + gate.model);
        std::printf("P2_CAVE_GEOMETRY_GATE id=%s hazard=%s actor=%s model=%s placed=%d\n",
                    gate.node_id.c_str(),
                    gate.hazard.empty() ? "none" : gate.hazard.c_str(), gate.actor.c_str(),
                    gate.model.empty() ? "-" : gate.model.c_str(), actor.shape ? 1 : 0);
        gateActors.push_back(actor);
    }
    geometryActive = true;
    std::printf("%s\n", p2CaveGeometryMarker(geometry).c_str());
    std::printf("P2_CAVE_GEOMETRY_CLASS geometry=%s nodes=%zu real=%d gate_actors=%zu\n",
                geometry.geometry.c_str(), geometry.nodes.size(), loaded, gateActors.size());
    std::fflush(stdout);
}

void pc_p2_cave_geometry_tick()
{
    if (!geometryActive) return;
    const float dt = gsys ? gsys->getFrameTime() : 0.0f;
    for (GateActor& actor : gateActors) {
        // Lane 50 (#488): when a P2_CAVE_GATES_1 carry blocker owns this node it
        // drives the carry hazard; the gate mesh is still drawn here.
        if (pc_p2_cave_carry_handles(actor.node_id)) continue;
        if (actor.cooldown > 0.0f) actor.cooldown -= dt;
        bool immune = false;
        // Electric-immune Pikmin (Yellow / Bulbmin) open the gate; this is the
        // live half of the "come back with yellow" loop.
        Piki* opener = nearestPikmin(actor.position, 60.0f, true, immune);
        if (opener && !actor.open) {
            actor.open = true;
            std::printf("P2_CAVE_GEOMETRY_GATE_OPEN id=%s actor=%s reason=electric_immune\n",
                        actor.node_id.c_str(), actor.actor.c_str());
            std::fflush(stdout);
        }
        if (actor.open) continue;
        Piki* target = nearestPikmin(actor.position, 70.0f, false, immune);
        if (!target || immune || actor.cooldown > 0.0f) continue;
        Vector3f direction(target->getPosition().x - actor.position.x, 0.0f,
                           target->getPosition().z - actor.position.z);
        const bool accepted = target->stimulate(InteractDenki(nullptr, 1.0f, &direction));
        actor.cooldown = 1.5f;
        std::printf(
            "P2_CAVE_GEOMETRY_GATE_DENKI id=%s actor=%s target=%d accepted=%d target_state=%d\n",
            actor.node_id.c_str(), actor.actor.c_str(), pc_p2_species(target), int(accepted),
            target->getState());
        std::fflush(stdout);
    }
}

void pc_p2_cave_geometry_draw(Graphics& gfx)
{
    if (!geometryActive || !gfx.mCamera) return;
    static bool drawLogged = false;
    gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx, gfx.mCamera->mFov,
        gfx.mCamera->mAspectRatio, gfx.mCamera->mNear, gfx.mCamera->mFar, 1.f);
    gfx.useMaterial(nullptr);
    gfx.setDepth(true);
    const Colour oldColour = gfx.mPrimaryColour;
    const Colour oldAux = gfx.mAuxiliaryColour;
    const int oldBlend = gfx.setCBlending(BLEND_Alpha);
    Texture* oldTexture = gfx.mActiveTexture[0];
    const bool oldLight = gfx.setLighting(false, nullptr);
    gfx.useTexture(nullptr, 0);
    gfx.useMatrix(gfx.mCamera->mLookAtMtx, 0);
    for (const P2CaveGeometryNode& node : geometry.nodes) {
        if (!node.real || node.model.empty()) continue;
        Shape* shape = nullptr;
        for (const NodeShape& entry : nodeShapes) {
            if (entry.id == node.id) { shape = entry.shape; break; }
        }
        if (shape) drawShapeAt(gfx, shape, worldPosition(node), 0.0f);
    }
    for (GateActor& actor : gateActors) {
        const float drop = actor.open ? 32.0f : 0.0f;
        Vector3f position(actor.position.x, actor.position.y - drop, actor.position.z);
        drawShapeAt(gfx, actor.shape, position, 0.0f);
    }
    if (!drawLogged) {
        drawLogged = true;
        int models = 0;
        for (const NodeShape& entry : nodeShapes) {
            if (entry.shape) ++models;
        }
        int gates = 0;
        for (const GateActor& actor : gateActors) {
            if (actor.shape) ++gates;
        }
        std::printf("P2_CAVE_GEOMETRY_DRAW nodes=%zu models=%d gates=%d geometry=%s\n",
                    geometry.nodes.size(), models, gates, geometry.geometry.c_str());
        std::fflush(stdout);
    }
    gfx.setColour(oldColour, true);
    gfx.mAuxiliaryColour = oldAux;
    gfx.setCBlending(oldBlend);
    gfx.useTexture(oldTexture, 0);
    gfx.setLighting(oldLight, nullptr);
}

bool pc_p2_cave_geometry_handles(const std::string& id)
{
    if (!geometryActive) return false;
    const P2CaveGeometryNode* node = p2CaveGeometryFindNode(geometry, id);
    return node && node->real && nodeLoaded(id);
}
