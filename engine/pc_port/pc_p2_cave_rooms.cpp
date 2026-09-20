// Lane 44 (#482, cave wave #468): engine glue for the proxy cave-room module.
//
// Reads the host bridge's P2_CAVE_ROOMS_1 config, reports the live squad's
// hard-hazard keys, answers per-unit reachability over the proxy graph and draws
// the proxy floor. This is labelled proxy geometry: it is not a P2 MapUnit room
// and never a generation PASS.
#include "pc_p2_cave_rooms_engine.h"
#include "pc_p2_cave_geometry_engine.h"  // lane 45 (#483): real geometry takes over loaded nodes

#include "Graphics.h"
#include "Camera.h"
#include "MapMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "pc_p2_species.h"

#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <fstream>
#include <string>

namespace {
P2CaveRoomLayout rooms;
bool roomsActive = false;

bool readLayout(const std::string& path, P2CaveRoomLayout& out, std::string& error)
{
    std::ifstream in(path);
    if (!in) {
        error = "cannot open rooms config: " + path;
        return false;
    }
    return p2CaveRoomsParse(in, out, error);
}

Vector3f unitGround(const P2CaveRoomUnit& unit)
{
    const float x = p2CaveRoomsWorldX(rooms, unit);
    const float z = p2CaveRoomsWorldZ(rooms, unit);
    const float y = mapMgr ? mapMgr->getMinY(x, z, true) : 0.f;
    return Vector3f(x, y, z);
}

Colour unitColour(const std::string& kind, const std::string& hazard)
{
    if (kind == "gate") {
        if (hazard == "elec") return Colour(255, 235, 60, 255);
        if (hazard == "water") return Colour(70, 200, 255, 255);
        if (hazard == "fire") return Colour(255, 120, 40, 255);
        if (hazard == "poison") return Colour(200, 120, 255, 255);
        return Colour(255, 255, 255, 255);
    }
    if (kind == "choke") return hazard == "water" ? Colour(70, 200, 255, 255) : Colour(255, 235, 60, 255);
    if (kind == "leaf") {
        if (hazard == "elec") return Colour(255, 235, 60, 255);
        if (hazard == "water") return Colour(70, 200, 255, 255);
        if (hazard == "fire") return Colour(255, 120, 40, 255);
        if (hazard == "poison") return Colour(200, 120, 255, 255);
        return Colour(210, 210, 210, 255);
    }
    if (kind == "bud") return Colour(120, 255, 120, 255);
    if (kind == "segment") return Colour(190, 190, 190, 255);
    return Colour(255, 255, 255, 255);
}

void drawSquare(Graphics& gfx, const Vector3f& centre, float half, float y)
{
    const Vector3f corners[4] = {
        Vector3f(centre.x - half, y, centre.z - half),
        Vector3f(centre.x + half, y, centre.z - half),
        Vector3f(centre.x + half, y, centre.z + half),
        Vector3f(centre.x - half, y, centre.z + half),
    };
    for (int i = 0; i < 4; ++i) {
        gfx.drawLine(corners[i], corners[(i + 1) % 4]);
    }
}
}  // namespace

bool pc_p2_cave_rooms_active() { return roomsActive; }

const P2CaveRoomLayout* pc_p2_cave_rooms_layout() { return roomsActive ? &rooms : nullptr; }

void pc_p2_cave_rooms_shutdown()
{
    rooms = P2CaveRoomLayout{};
    roomsActive = false;
}

void pc_p2_cave_rooms_setup()
{
    rooms = P2CaveRoomLayout{};
    roomsActive = false;
    const char* env = std::getenv("PIKMIN_CAVE_ROOMS");
    const std::string path = env && env[0] ? env : "p2-cave-rooms.txt";
    if (!std::ifstream(path)) return;
    std::string error;
    if (!readLayout(path, rooms, error)) {
        std::printf("P2_CAVE_ROOMS FAILED reason=%s\n", error.c_str());
        std::fflush(stdout);
        return;
    }
    roomsActive = true;
    std::printf("%s\n", p2CaveRoomsMarker(rooms).c_str());
    std::fflush(stdout);
}

P2CaveAbilities pc_p2_cave_rooms_squad_abilities()
{
    P2CaveAbilities keys;
    if (!pikiMgr) return keys;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* piki = static_cast<Piki*>(*it);
        if (!piki || !piki->isAlive()) continue;
        switch (pc_p2_species(piki)) {
        case P2SpeciesBlue: keys.blue = true; break;
        case P2SpeciesYellow: keys.yellow = true; break;
        case P2SpeciesRed: keys.red = true; break;
        case P2SpeciesWhite: keys.white = true; break;
        default: break;
        }
    }
    return keys;
}

std::string pc_p2_cave_rooms_unit_at(float x, float z)
{
    if (!roomsActive) return std::string();
    const P2CaveRoomUnit* best = nullptr;
    float bestDistance = 0.f;
    for (const P2CaveRoomUnit& unit : rooms.units) {
        const float dx = p2CaveRoomsWorldX(rooms, unit) - x;
        const float dz = p2CaveRoomsWorldZ(rooms, unit) - z;
        const float distance = dx * dx + dz * dz;
        if (!best || distance < bestDistance) {
            best = &unit;
            bestDistance = distance;
        }
    }
    return best ? best->id : std::string();
}

bool pc_p2_cave_rooms_reachable_now(const std::string& target)
{
    if (!roomsActive) return false;
    return p2CaveRoomsReachable(rooms, target, pc_p2_cave_rooms_squad_abilities());
}

void pc_p2_cave_rooms_draw(Graphics& gfx)
{
    if (!roomsActive || !gfx.mCamera) return;
    gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx, gfx.mCamera->mFov,
        gfx.mCamera->mAspectRatio, gfx.mCamera->mNear, gfx.mCamera->mFar, 1.f);
    gfx.useMaterial(nullptr);
    gfx.setDepth(true);
    const Colour oldColour = gfx.mPrimaryColour;
    const Colour oldAux = gfx.mAuxiliaryColour;
    const int oldBlend = gfx.setCBlending(BLEND_Alpha);
    Texture* oldTexture = gfx.mActiveTexture[0];
    const bool oldLight = gfx.setLighting(false, nullptr);
    const float oldWidth = gfx.setLineWidth(2.f);
    gfx.useTexture(nullptr, 0);
    gfx.useMatrix(gfx.mCamera->mLookAtMtx, 0);
    const float half = rooms.cell * 0.4f;
    for (const P2CaveRoomUnit& unit : rooms.units) {
        // Lane 45 (#483): a node with a loaded real model is drawn once, by the
        // geometry module, so the proxy square is not drawn underneath it.
        if (pc_p2_cave_geometry_handles(unit.id)) continue;
        const Vector3f ground = unitGround(unit);
        gfx.setColour(unitColour(unit.kind, unit.hazard), true);
        drawSquare(gfx, ground, half, ground.y + 2.f);
        for (const std::string& item : unit.items) {
            (void)item;
            const float y = ground.y + 12.f;
            gfx.drawLine(Vector3f(ground.x - 8.f, y, ground.z), Vector3f(ground.x + 8.f, y, ground.z));
            gfx.drawLine(Vector3f(ground.x, y, ground.z - 8.f), Vector3f(ground.x, y, ground.z + 8.f));
        }
        if (unit.id == rooms.hole) {
            const float y = ground.y + 6.f;
            for (int i = 0; i < 24; ++i) {
                const float a = i * 6.28318530718f / 24.f;
                const float b = (i + 1) * 6.28318530718f / 24.f;
                gfx.drawLine(Vector3f(ground.x + std::cos(a) * half, y, ground.z + std::sin(a) * half),
                             Vector3f(ground.x + std::cos(b) * half, y, ground.z + std::sin(b) * half));
            }
        }
    }
    for (const std::pair<std::string, std::string>& edge : rooms.edges) {
        const P2CaveRoomUnit* from = p2CaveRoomsFind(rooms, edge.first);
        const P2CaveRoomUnit* to = p2CaveRoomsFind(rooms, edge.second);
        if (!from || !to) continue;
        const Vector3f a = unitGround(*from);
        const Vector3f b = unitGround(*to);
        gfx.setColour(Colour(90, 90, 120, 255), true);
        gfx.drawLine(Vector3f(a.x, a.y + 1.f, a.z), Vector3f(b.x, b.y + 1.f, b.z));
    }
    gfx.setLineWidth(oldWidth);
    gfx.setColour(oldColour, true);
    gfx.mAuxiliaryColour = oldAux;
    gfx.setCBlending(oldBlend);
    gfx.useTexture(oldTexture, 0);
    gfx.setLighting(oldLight, nullptr);
}
