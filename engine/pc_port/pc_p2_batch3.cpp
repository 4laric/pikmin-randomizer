// Family-owned batch-3 P2 visual registration: aquatic (#374), flying (#375)
// and snagret (#376).
//
// Visual-only P1 proxy anchors. Each family's private arena run writes
// `p2-<family>-actors.txt` (P2_<FAMILY>_ACTORS_1, `<generator> <Species>`) and
// `p2-<family>-bank.txt` (per-species clip names/pose counts) plus the sampled
// pose bank `assets/dataDir/courses/pikmin2room/<prefix>_<species>_<clip>_NN.mod`.
// Registration matches the arena's P1 placement vehicles by generator ID and
// verifies the expected native teki type before drawing. No source P2 FSM,
// damage receiver, reward or collision semantics are implemented here; those
// stay tracked on the family issues and #186.
#include "pc_p2_batch3.h"
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
struct FamilyDef {
    const char* name;
    const char* prefix;
    const char* actors;
    const char* bank;
};
// Pose-bank families only. Prefix is the pose-file prefix from the install
// module: aquatic_/fly_/snake_<Species>_<clip>_NN.mod.
const FamilyDef FAMILIES[] = {
    {"aquatic", "aquatic", "p2-aquatic-actors.txt", "p2-aquatic-bank.txt"},
    {"flying", "fly", "p2-flying-actors.txt", "p2-flying-bank.txt"},
    {"snagret", "snake", "p2-snagret-actors.txt", "p2-snagret-bank.txt"},
};
constexpr size_t ClipBytes = 512 * 1024;         // per clip
constexpr size_t TotalBytes = 48 * 1024 * 1024;  // per setup

struct Bank {
    std::map<std::string, std::vector<Shape*>> clips;
    std::map<std::string, p2animation::Clip> timing;
};
std::map<std::string, Bank> banks;             // key "family|species"
std::map<BTeki*, std::string> actors;          // actor -> key
size_t bytesTotal = 0;
bool logged[2] = {false, false};

[[noreturn]] void fail(const char* what) {
    std::fprintf(stderr, "P2_BATCH3 %s\n", what);
    std::abort();
}

int expectedType(const std::string& family, const std::string& species) {
    if (family == "aquatic") {
        if (species == "Catfish") return TEKI_Namazu;   // P1 Water Dumple ancestor
        if (species == "Tadpole") return TEKI_Otama;    // P1 Wogpole ancestor
    }
    if (family == "flying") {
        if (species == "Mar" || species == "Hanachirashi") return TEKI_Mar;  // P1 Puffy Blowhog
    }
    return TEKI_Chappy;  // Jigumo/UmiMushi/snagrets: no P1 counterpart, placement vehicle only
}

const char* firstClip(const Bank& bank, const char* const* names, int count) {
    for (int i = 0; i < count; ++i)
        if (bank.clips.count(names[i])) return names[i];
    return nullptr;
}

Shape* loadPose(const std::string& prefix, const std::string& species,
                const std::string& clip, int index,
                std::vector<unsigned char>& reference, size_t& clipBytes) {
    char rel[192];
    std::snprintf(rel, sizeof(rel), "assets/dataDir/courses/pikmin2room/%s_%s_%s_%02d.mod",
                  prefix.c_str(), species.c_str(), clip.c_str(), index);
    std::ifstream file(rel, std::ios::binary | std::ios::ate);
    if (!file) fail("missing pose bank");
    const auto size = file.tellg();
    if (size <= 0 || size_t(size) > ClipBytes || clipBytes + size_t(size) > ClipBytes
            || bytesTotal + size_t(size) > TotalBytes) fail("pose bank exceeds budget");
    clipBytes += size_t(size);
    bytesTotal += size_t(size);
    file.seekg(0);
    std::vector<unsigned char> data(size_t(size), 0), resources;
    if (!file.read(reinterpret_cast<char*>(data.data()), size)
            || !p2animation::resources(data, resources)) fail("invalid pose resources");
    if (!reference.empty() && reference != resources) fail("pose resources differ");
    reference = resources;
    char load[160];
    std::snprintf(load, sizeof(load), "courses/pikmin2room/%s_%s_%s_%02d.mod",
                  prefix.c_str(), species.c_str(), clip.c_str(), index);
    Shape* shape = gameflow.loadShape(load, true);
    if (!shape) fail("pose load failed");
    return shape;
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
                || !out.emplace(unsigned(generator), species).second) fail("invalid actor row");
    }
    if (in >> word) fail("trailing actor config data");
    return true;
}

bool parseBank(const std::string& path,
               std::map<std::string, std::vector<std::pair<std::string, int>>>& out) {
    std::ifstream in(path);
    if (!in) return false;
    std::string word;
    if (!(in >> word) || word.size() < 9 || word.compare(0, 3, "P2_") != 0
            || word.compare(word.size() - 7, 7, "_BANK_1") != 0) fail("invalid bank header");
    while (in >> word) {
        if (word == "species") {
            std::string species;
            unsigned long long id = 0;
            if (!(in >> species >> id)) fail("invalid bank species row");
            out.emplace(species, std::vector<std::pair<std::string, int>>());
        } else if (word == "clip") {
            std::string species, name, events, status, marker;
            int frames = 0, poses = 0;
            if (!(in >> species >> name >> frames >> events >> marker >> poses >> status)
                    || marker != "poses" || poses < 0 || poses > 64
                    || !out.count(species)) fail("invalid bank clip row");
            out[species].emplace_back(name, poses);
        } else {
            fail("invalid bank token");
        }
    }
    return true;
}

Bank loadBank(const FamilyDef& family, const std::string& species,
              const std::vector<std::pair<std::string, int>>& rows) {
    Bank bank;
    std::vector<unsigned char> reference;
    Shape* shared = nullptr;
    for (const auto& clip : rows) {
        size_t clipBytes = 0;
        p2animation::Clip timing;
        timing.name = clip.first;
        timing.count = clip.second;
        bank.timing[clip.first] = timing;
        for (int i = 0; i < clip.second; ++i) {
            Shape* shape = loadPose(family.prefix, species, clip.first, i, reference, clipBytes);
            if (!shared) {
                shared = shape;
                for (int t = 0; t < shape->mTexAttrCount; ++t)
                    if (shape->mTexAttrList[t].mTexture) shape->mTexAttrList[t].mTexture->attach();
            } else {
                if (shape->mMaterialCount != shared->mMaterialCount
                        || shape->mTexAttrCount != shared->mTexAttrCount
                        || shape->mTevInfoCount != shared->mTevInfoCount) fail("material framing mismatch");
                for (int j = 0; j < shape->mTotalMatpolyCount; ++j) {
                    auto* poly = shape->mMatpolyList[j];
                    if (!poly || !poly->mMaterial) continue;
                    int material = -1;
                    for (int m = 0; m < shape->mMaterialCount; ++m)
                        if (poly->mMaterial == &shape->mMaterialList[m]) material = m;
                    if (material < 0) fail("pose material not found");
                    poly->mMaterial = &shared->mMaterialList[material];
                }
                shape->mMaterialList = shared->mMaterialList;
                shape->mTexAttrList = shared->mTexAttrList;
                shape->mTevInfoList = shared->mTevInfoList;
            }
            bank.clips[clip.first].push_back(shape);
        }
    }
    return bank;
}
}

void pc_p2_batch3_reset() {
    banks.clear();
    actors.clear();
    bytesTotal = 0;
    logged[0] = logged[1] = false;
}

void pc_p2_batch3_forget(BTeki* actor) {
    actors.erase(actor);
}

bool pc_p2_batch3_corpse_drawn() { return logged[1]; }
int pc_p2_batch3_actor_count() { return int(actors.size()); }
int pc_p2_batch3_bank_count() { return int(banks.size()); }

void pc_p2_batch3_setup() {
    pc_p2_batch3_reset();
    if (!pc_pikipelago_room_preview() || !tekiMgr) return;
    for (const FamilyDef& family : FAMILIES) {
        std::map<unsigned, std::string> wanted;
        if (!parseActors(family.actors, wanted)) continue;
        std::map<std::string, std::vector<std::pair<std::string, int>>> rows;
        if (!parseBank(family.bank, rows)) fail("missing bank for present actor config");

        std::set<unsigned> found;
        std::set<std::string> speciesUsed;
        Iterator it(tekiMgr);
        CI_LOOP(it) {
            Teki* teki = static_cast<Teki*>(*it);
            if (!teki || !teki->mGenerator) continue;
            const unsigned generator = teki->mGenerator->_70;
            auto match = wanted.find(generator);
            if (match == wanted.end()) continue;
            if (teki->mTekiType != expectedType(family.name, match->second)) fail("native type mismatch");
            if (!found.insert(generator).second) fail("duplicate generator in scene");
            actors[teki] = std::string(family.name) + "|" + match->second;
            speciesUsed.insert(match->second);
        }
        if (found.size() != wanted.size()) fail("arena actor not present in scene");
        for (const std::string& species : speciesUsed) {
            auto clipRows = rows.find(species);
            if (clipRows == rows.end() || clipRows->second.empty()) fail("species has no bank clips");
            banks[std::string(family.name) + "|" + species] =
                loadBank(family, species, clipRows->second);
        }
    }
    for (const auto& entry : actors)
        std::printf("P2_BATCH3_BIND generator=%u key=%s visual_only=1 native_fsm=unimplemented\n",
                    entry.first->mGenerator ? entry.first->mGenerator->_70 : 0, entry.second.c_str());
    std::printf("P2_BATCH3_BANK total_mod_bytes=%zu species=%zu\n", bytesTotal, banks.size());
}

bool pc_p2_batch3_draw(BTeki* actor, Graphics& gfx, const Matrix4f& matrix, bool corpse) {
    auto entry = actors.find(actor);
    if (entry == actors.end() || !gfx.mCamera || !actor->mTekiAnimator) return false;
    auto bankIt = banks.find(entry->second);
    if (bankIt == banks.end()) return false;
    const Bank& bank = bankIt->second;
    static const char* const deadClips[] = {"dead", "dead1", "pdead1", "kagebozu_dead"};
    static const char* const attackClips[] = {"attack1", "attack", "attack2", "attack_2",
                                              "sattack1", "hit", "hit_near", "hit_far", "charge",
                                              "hit_start", "kagebozu_flick", "kagebozu_flick2"};
    static const char* const moveClips[] = {"move1", "move", "move2", "run1", "walk", "walk1",
                                            "wrun1", "tyre_move", "kagebozu_move", "kagebozu_walk", "kagebozu_run"};
    static const char* const waitClips[] = {"wait1", "wait", "wait2", "kagebozu_wait", "kagebozu_wait2"};
    const int motion = actor->mTekiAnimator->getCurrentMotionIndex();
    const char* name = nullptr;
    if (corpse) {
        name = firstClip(bank, deadClips, int(sizeof(deadClips) / sizeof(deadClips[0])));
    } else if (motion == TekiMotion::Damage || motion >= TekiMotion::Type1) {
        name = firstClip(bank, attackClips, int(sizeof(attackClips) / sizeof(attackClips[0])));
    }
    if (!name) {
        const f32 speed = actor->mVelocity.x * actor->mVelocity.x + actor->mVelocity.z * actor->mVelocity.z;
        name = speed > 1.f
            ? firstClip(bank, moveClips, int(sizeof(moveClips) / sizeof(moveClips[0])))
            : firstClip(bank, waitClips, int(sizeof(waitClips) / sizeof(waitClips[0])));
    }
    if (!name) name = firstClip(bank, waitClips, int(sizeof(waitClips) / sizeof(waitClips[0])));
    if (!name) return false;
    const auto& poses = bank.clips.at(name);
    if (poses.empty()) return false;
    const int frames = actor->mTekiAnimator->getFrameCount();
    const float phase = frames > 1 ? actor->mTekiAnimator->getCounter() / (frames - 1) : 0.f;
    const p2animation::Clip& timing = bank.timing.at(name);
    const size_t index = timing.index(phase, corpse);
    Shape* shape = poses.at(index < poses.size() ? index : poses.size() - 1);
    if (!logged[corpse ? 1 : 0]) {
        std::printf("P2_BATCH3_DRAW corpse=%d key=%s clip=%s\n", int(corpse), entry->second.c_str(), name);
        logged[corpse ? 1 : 0] = true;
    }
    shape->updateAnim(gfx, matrix, nullptr, actor);
    shape->drawshape(gfx, *gfx.mCamera, nullptr);
    return true;
}
