// Family-owned Long Legs bind-pose native draw path (#312, parent #173).
//
// Unlike the batch-2 pose-bank families, the Long Legs lane installs bind-pose
// meshes and `experimental/pikmin2_long_legs_visual.py` bakes each of them into
// a single static engine `.mod` (`longlegs_<species>_bind_00.mod`). This unit
// registers the arena's P1 placement vehicles by generator ID from
// `p2-long-legs-actors.txt` (P2_LONG_LEGS_ACTORS_1) and draws that static bind
// shape, so there is no pose bank and no animation selection. It is a
// visual-only P1 proxy anchor: source FSM, IK leg stability, foot crush,
// Man-at-Legs gun callbacks, damage receivers, rewards and collisions are not
// implemented here. Those remain tracked on #173 and #186.
#include "pc_p2_long_legs.h"
#include "pc_p2_animation.h"
#include "pc_bbft.h"
#include "teki.h"
#include "Generator.h"
#include "Shape.h"
#include "Texture.h"
#include "Graphics.h"
#include "Camera.h"
#include "gameflow.h"
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <set>
#include <string>
#include <vector>

namespace {
struct SpeciesDef {
    const char* name;
    const char* mod;
};
const SpeciesDef SPECIES[] = {
    {"Houdai", "longlegs_Houdai_bind_00.mod"},
    {"BigFoot", "longlegs_BigFoot_bind_00.mod"},
};
constexpr size_t MeshBytes = 4 * 1024 * 1024;    // per species
constexpr size_t TotalBytes = 16 * 1024 * 1024;  // per setup

std::map<BTeki*, std::string> actors;          // actor -> species
std::map<std::string, Shape*> shapes;          // species -> bind shape
size_t bytesTotal = 0;
bool logged[2] = {false, false};

[[noreturn]] void fail(const char* what) {
    std::fprintf(stderr, "P2_LONG_LEGS %s\n", what);
    std::abort();
}

const SpeciesDef* findSpecies(const std::string& name) {
    for (const SpeciesDef& species : SPECIES)
        if (name == species.name) return &species;
    return nullptr;
}

bool parseActors(const std::string& path, std::map<unsigned, std::string>& out) {
    std::ifstream in(path);
    if (!in) return false;  // absent config -> P1 fallback
    std::string header, species, word;
    int count = 0;
    if (!(in >> header >> count) || header.size() < 11
            || header.compare(0, 3, "P2_") != 0
            || header.compare(header.size() - 9, 9, "_ACTORS_1") != 0
            || count < 1 || count > 100) fail("invalid actor config");
    for (int i = 0; i < count; ++i) {
        unsigned long long generator = 0;
        if (!(in >> generator >> species) || generator > 0xffffffffULL
                || !findSpecies(species)
                || !out.emplace(unsigned(generator), species).second) fail("invalid actor row");
    }
    if (in >> word) fail("trailing actor config data");
    return true;
}

Shape* loadBind(const SpeciesDef& species) {
    std::vector<unsigned char> data;
    {
        std::ifstream file(std::string("assets/dataDir/courses/pikmin2room/") + species.mod,
                           std::ios::binary | std::ios::ate);
        if (!file) fail("missing bind mesh");
        const auto size = file.tellg();
        if (size <= 0 || size_t(size) > MeshBytes) fail("bind mesh exceeds per-species budget");
        bytesTotal += size_t(size);
        if (bytesTotal > TotalBytes) fail("bind mesh exceeds total budget");
        file.seekg(0);
        data.assign(size_t(size), 0);
        if (!file.read(reinterpret_cast<char*>(data.data()), size)) fail("unreadable bind mesh");
    }
    std::vector<unsigned char> resources;
    if (!p2animation::resources(data, resources)) fail("invalid bind resources");
    Shape* shape = gameflow.loadShape(
        (std::string("courses/pikmin2room/") + species.mod).c_str(), true);
    if (!shape) fail("bind mesh load failed");
    for (int i = 0; i < shape->mTexAttrCount; ++i)
        if (shape->mTexAttrList[i].mTexture) shape->mTexAttrList[i].mTexture->attach();
    return shape;
}
}

void pc_p2_long_legs_reset() {
    actors.clear();
    shapes.clear();
    bytesTotal = 0;
    logged[0] = logged[1] = false;
}

void pc_p2_long_legs_forget(BTeki* actor) {
    actors.erase(actor);
}

void pc_p2_long_legs_setup() {
    pc_p2_long_legs_reset();
    if (!pc_pikipelago_room_preview() || !tekiMgr) return;
    std::map<unsigned, std::string> wanted;
    if (!parseActors("p2-long-legs-actors.txt", wanted)) return;

    std::set<unsigned> found;
    std::set<std::string> speciesUsed;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        Teki* teki = static_cast<Teki*>(*it);
        if (!teki || !teki->mGenerator) continue;
        const unsigned generator = teki->mGenerator->_70;
        auto match = wanted.find(generator);
        if (match == wanted.end()) continue;
        if (teki->mTekiType != TEKI_Chappy) fail("native type mismatch");
        if (!found.insert(generator).second) fail("duplicate generator in scene");
        actors[teki] = match->second;
        speciesUsed.insert(match->second);
    }
    if (found.size() != wanted.size()) fail("arena actor not present in scene");
    for (const std::string& species : speciesUsed) {
        if (shapes.count(species)) continue;
        const SpeciesDef* def = findSpecies(species);
        if (!def) fail("unknown species in actor config");
        shapes[species] = loadBind(*def);
    }
    for (const auto& entry : actors)
        std::printf("P2_LONG_LEGS_BIND generator=%u species=%s pose=bind visual_only=1 native_fsm=unimplemented\n",
                    entry.first->mGenerator ? entry.first->mGenerator->_70 : 0,
                    entry.second.c_str());
    std::printf("P2_LONG_LEGS_BANK total_mod_bytes=%zu species=%zu pose_bank=0\n",
                bytesTotal, shapes.size());
}

bool pc_p2_long_legs_draw(BTeki* actor, Graphics& gfx, const Matrix4f& matrix, bool corpse) {
    auto entry = actors.find(actor);
    if (entry == actors.end() || !gfx.mCamera) return false;
    auto shapeIt = shapes.find(entry->second);
    if (shapeIt == shapes.end() || !shapeIt->second) return false;
    Shape* shape = shapeIt->second;
    if (!logged[corpse ? 1 : 0]) {
        std::printf("P2_LONG_LEGS_DRAW corpse=%d species=%s pose=bind\n",
                    int(corpse), entry->second.c_str());
        logged[corpse ? 1 : 0] = true;
    }
    shape->updateAnim(gfx, matrix, nullptr, actor);
    shape->drawshape(gfx, *gfx.mCamera, nullptr);
    return true;
}
