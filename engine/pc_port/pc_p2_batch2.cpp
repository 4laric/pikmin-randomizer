// Family-owned batch-2 P2 visual registration: dweevil (#349), flora (#353),
// ground invertebrates (#346), cannon/projectile (#350) and waterwraith (#352).
//
// Visual-only P1 proxy anchors. Each family's private arena run writes
// `p2-<family>-actors.txt` (P2_<FAMILY>_ACTORS_1, `<generator> <Species>`) and
// `p2-<family>-bank.txt` (per-species clip names/pose counts) plus the sampled
// pose bank `assets/dataDir/courses/pikmin2room/<prefix>_<species>_<clip>_NN.mod`.
// Registration matches the arena's P1 placement vehicles by generator ID and
// verifies the expected native teki type before drawing. No source P2 FSM,
// damage receiver, reward or collision semantics are implemented here; those
// stay tracked on the family issues and #186.
#include "pc_p2_batch2.h"
#include "pc_p2_animation.h"
#include "pc_p2_sokkuri.h"
#include "pc_p2_armor.h"
#include "pc_p2_batch2_clock.h"
#include "pc_p2_elecbug.h"
#include "pc_p2_tamago.h"
#include "pc_p2_imomushi.h"
#include "pc_p2_otakara.h"
#include "pc_p2_pom.h"
#include "pc_p2_campaign_actor.h"
#include "pc_randomizer.h"
#include "pc_bbft.h"
#include "teki.h"
#include "Generator.h"
#include "Shape.h"
#include "Texture.h"
#include "Material.h"
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
// Pose-bank families only. Long Legs (#312) installs bind-pose meshes, not a
// converted .mod pose bank, so it has no native draw path yet.
const FamilyDef FAMILIES[] = {
    {"dweevil", "ota", "p2-dweevil-actors.txt", "p2-dweevil-bank.txt"},
    {"flora", "flora", "p2-flora-actors.txt", "p2-flora-bank.txt"},
    {"ground", "ginv", "p2-ground-actors.txt", "p2-ground-bank.txt"},
    {"cannon", "cannon", "p2-cannon-actors.txt", "p2-cannon-bank.txt"},
    {"waterwraith", "ww", "p2-waterwraith-actors.txt", "p2-waterwraith-bank.txt"},
};
constexpr size_t ClipBytes = 512 * 1024;         // per clip
constexpr size_t TotalBytes = 48 * 1024 * 1024;  // per setup

struct Bank {
    std::map<std::string, std::vector<Shape*>> clips;
    std::map<std::string, p2sampled::Clip> clock;
};
struct ActorClock {
    p2batch2clock::Cursor cursor;
    std::string clip;
};
std::map<std::string, Bank> banks;             // key "family|species"
std::map<BTeki*, std::string> actors;          // actor -> key
std::map<BTeki*, ActorClock> clocks;           // actor -> sampled clock state
size_t bytesTotal = 0;
bool logged[2] = {false, false};
unsigned long long eventCount = 0;

[[noreturn]] void fail(const char* what) {
    std::fprintf(stderr, "P2_BATCH2 %s\n", what);
    std::abort();
}

int expectedType(const std::string& family, const std::string& species) {
    if (family == "cannon") {
        if (species == "Kabuto" || species == "Rkabuto" || species == "Fkabuto") return TEKI_Beatle;
        if (species == "Rock" || species == "Stone") return TEKI_Iwagon;
    }
    return TEKI_Chappy;
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
               std::map<std::string, std::vector<p2batch2clock::Row>>& out) {
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
            out.emplace(species, std::vector<p2batch2clock::Row>());
        } else if (word == "clip") {
            std::string species, name, events, status, marker;
            int frames = 0, poses = 0;
            if (!(in >> species >> name >> frames >> events >> marker >> poses >> status)
                    || marker != "poses" || frames < 0 || poses < 0 || poses > 64
                    || !out.count(species)) fail("invalid bank clip row");
            p2batch2clock::Row row;
            row.name = name;
            row.sourceFrames = frames;
            row.poseCount = poses;
            if (!p2batch2clock::parseEvents(events, row.events)) fail("invalid bank event token");
            out[species].push_back(std::move(row));
        } else {
            fail("invalid bank token");
        }
    }
    return true;
}

Bank loadBank(const FamilyDef& family, const std::string& species,
              const std::vector<p2batch2clock::Row>& rows) {
    Bank bank;
    std::vector<unsigned char> reference;
    Shape* shared = nullptr;
    for (const auto& row : rows) {
        size_t clipBytes = 0;
        p2sampled::Clip clock = p2batch2clock::makeClip(row);
        if (!clock.valid()) fail("invalid sampled clock clip");
        bank.clock[row.name] = clock;
        for (int i = 0; i < row.poseCount; ++i) {
            Shape* shape = loadPose(family.prefix, species, row.name, i, reference, clipBytes);
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
            bank.clips[row.name].push_back(shape);
        }
    }
    return bank;
}
}

void pc_p2_batch2_reset() {
    banks.clear();
    actors.clear();
    clocks.clear();
    bytesTotal = 0;
    eventCount = 0;
    logged[0] = logged[1] = false;
}

void pc_p2_batch2_forget(BTeki* actor) {
    actors.erase(actor);
    clocks.erase(actor);
}

// Scan the scene and bind present arena actors. ``strict`` is the startup
// contract (every configured actor must exist); ``false`` is the re-entry path
// after a legitimate family death, where absent actors are tolerated so the
// respawned actor can be re-bound without a stale pointer.
// Generated campaign sessions (the seed bridge) bind by the seed's source id per
// actor, like the behaviour modules, not by the arena sidecar's generator ids.
static void campaignWanted(const FamilyDef& family, std::map<unsigned, std::string>& wanted) {
    static const struct { const char* family; unsigned source; const char* species; } SOURCES[] = {
        {"dweevil", 59, "FireOtakara"}, {"dweevil", 60, "WaterOtakara"},
        {"dweevil", 61, "GasOtakara"}, {"dweevil", 62, "ElecOtakara"},
        {"ground", 79, "Sokkuri"},
    };
    wanted.clear();
    for (const auto& row : SOURCES)
        if (std::string(row.family) == family.name)
            for (unsigned id : pc_p2_campaign_ids(row.source)) wanted[id] = row.species;
}

static void bindFamilies(bool strict) {
    const bool bridge = pc_randomizer_p2_bridge() && !pc_pikipelago_room_preview();
    for (const FamilyDef& family : FAMILIES) {
        std::map<unsigned, std::string> wanted;
        if (!parseActors(family.actors, wanted)) continue;
        if (bridge) {
            campaignWanted(family, wanted);
            if (wanted.empty()) continue;
        }
        std::map<std::string, std::vector<p2batch2clock::Row>> rows;
        if (!parseBank(family.bank, rows)) fail("missing bank for present actor config");

        std::set<unsigned> found;
        std::set<std::string> speciesUsed;
        Iterator it(tekiMgr);
        CI_LOOP(it) {
            Teki* teki = static_cast<Teki*>(*it);
            if (!teki || !teki->mGenerator) continue;
            const unsigned generator = bridge ? pc_p2_campaign_token(teki) : teki->mGenerator->_70;
            auto match = wanted.find(generator);
            if (match == wanted.end()) continue;
            if (teki->mTekiType != expectedType(family.name, match->second)) {
                if (!bridge) fail("native type mismatch");
                std::printf("P2_SETUP_SKIP batch2 %s native_type_mismatch generator=%u\n", family.name, generator);
                continue;
            }
            if (!found.insert(generator).second) fail("duplicate generator in scene");
            actors[teki] = std::string(family.name) + "|" + match->second;
            speciesUsed.insert(match->second);
        }
        if (found.size() != wanted.size()) {
            if (strict) fail("arena actor not present in scene");
            std::printf("P2_BATCH2_MISSING family=%s found=%zu wanted=%zu\n",
                        family.name, found.size(), wanted.size());
        }
        for (const std::string& species : speciesUsed) {
            auto clipRows = rows.find(species);
            if (clipRows == rows.end() || clipRows->second.empty()) fail("species has no bank clips");
            const std::string key = std::string(family.name) + "|" + species;
            if (!banks.count(key)) banks[key] = loadBank(family, species, clipRows->second);
        }
    }
}

static void logBindings() {
    for (const auto& entry : actors)
        std::printf("P2_BATCH2_BIND generator=%u key=%s visual_only=%d native_fsm=%s\n",
                    entry.first->mGenerator ? entry.first->mGenerator->_70 : 0, entry.second.c_str(),
                    (entry.second == "ground|Sokkuri" || entry.second == "ground|Armor" || entry.second == "ground|ElecBug" || entry.second == "ground|TamagoMushi" || entry.second == "ground|Imomushi" || entry.second == "ground|Hana") ? 0 : 1,
                    (entry.second == "ground|Sokkuri" || entry.second == "ground|Armor" || entry.second == "ground|ElecBug" || entry.second == "ground|TamagoMushi" || entry.second == "ground|Imomushi" || entry.second == "ground|Hana") ? "implemented" : "unimplemented");
    std::printf("P2_BATCH2_BANK total_mod_bytes=%zu species=%zu\n", bytesTotal, banks.size());
}

void pc_p2_batch2_setup() {
    pc_p2_batch2_reset();
    if (!tekiMgr) return;
    if (pc_pikipelago_room_preview()) {
        bindFamilies(true);
    } else if (pc_randomizer_p2_bridge()) {
        bindFamilies(false);  // campaign: missing actors (other areas/days) are expected
    } else {
        return;
    }
    logBindings();
}

void pc_p2_batch2_rebind() {
    // Rebind within this scene without reallocating the immutable model banks.
    actors.clear();
    if (!(pc_pikipelago_room_preview() || pc_randomizer_p2_bridge()) || !tekiMgr) return;
    bindFamilies(false);
    logBindings();
}

bool pc_p2_batch2_draw(BTeki* actor, Graphics& gfx, const Matrix4f& matrix, bool corpse) {
    auto entry = actors.find(actor);
    if (entry == actors.end() || !gfx.mCamera || !actor->mTekiAnimator) return false;
    auto bankIt = banks.find(entry->second);
    if (bankIt == banks.end()) return false;
    const Bank& bank = bankIt->second;
    static const char* const deadClips[] = {"dead", "dead1", "pdead1", "kagebozu_dead"};
    static const char* const attackClips[] = {"attack1", "attack", "attack2", "charge",
                                              "hit_start", "kagebozu_flick", "kagebozu_flick2"};
    static const char* const moveClips[] = {"move1", "move", "move2", "run1", "walk",
                                            "tyre_move", "kagebozu_move", "kagebozu_walk", "kagebozu_run"};
    static const char* const waitClips[] = {"wait1", "wait", "wait2", "kagebozu_wait", "kagebozu_wait2"};
    const int motion = actor->mTekiAnimator->getCurrentMotionIndex();
    const char* name = nullptr;
    float forcedPhase = -1.0f;
    const char* forcedClip = nullptr;
    // Family-owned source behavior: a registered Skitter Leaf forces the exact
    // source clip/phase for its FSM state instead of the generic P1-velocity pick.
    if (!corpse) {
        const char* forced = nullptr;
        float phase = 0.0f;
        if ((pc_p2_sokkuri_clip(actor, forced, phase) || pc_p2_armor_clip(actor, forced, phase)
                || pc_p2_elecbug_clip(actor, forced, phase) || pc_p2_tamago_clip(actor, forced, phase)
                || pc_p2_imomushi_clip(actor, forced, phase) || pc_p2_hana_clip(actor, forced, phase)
                || pc_p2_otakara_clip(actor, forced, phase) || pc_p2_pom_clip(actor, forced, phase))
                && bank.clips.count(forced)) {
            name = forced;
            forcedPhase = phase;
            forcedClip = forced;
        }
    }
    if (corpse) {
        name = firstClip(bank, deadClips, int(sizeof(deadClips) / sizeof(deadClips[0])));
    } else if (!name && (motion == TekiMotion::Damage || motion >= TekiMotion::Type1)) {
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
    const float phase = forcedPhase >= 0.0f ? forcedPhase
        : (frames > 1 ? actor->mTekiAnimator->getCounter() / (frames - 1) : 0.f);
    const p2sampled::Clip& clock = bank.clock.at(name);
    ActorClock& state = clocks[actor];
    if (state.clip != name) {
        if (!state.cursor.start(clock)) return false;
        state.clip = name;
    }
    const double sourceFrame = double(phase) * double(clock.poses.duration - 1);
    p2batch2clock::Step step = state.cursor.stepTo(sourceFrame);
    if (!step.ok) return false;
    for (const p2sampled::Occurrence& event : step.events) {
        ++eventCount;
        if (eventCount <= 16u) {
            std::printf("P2_BATCH2_EVENT key=%s clip=%s frame=%d event=%s cycle=%llu\n",
                        entry->second.c_str(), name, event.frame, event.key.c_str(),
                        static_cast<unsigned long long>(event.cycle));
        }
    }
    const size_t index = corpse ? poses.size() - 1
                               : (step.pose < poses.size() ? step.pose : poses.size() - 1);
    Shape* shape = poses.at(index);
    if (!logged[corpse ? 1 : 0]) {
        std::printf("P2_BATCH2_DRAW corpse=%d key=%s clip=%s\n", int(corpse), entry->second.c_str(), name);
        logged[corpse ? 1 : 0] = true;
    }
    // Per-species tint (#207): the converter bakes every dweevil species from
    // the shared-base model, so multiply the species tint over each material
    // channel the converted model may sample (polygon colour, TEV colour
    // register, konst colour). Saved per material and restored before return
    // so the pose-shared list is never polluted; untinted keys skip without
    // touching materials. Pattern follows pc_p2_kogane's karada konst write.
    p2batch2tint::Tint tint;
    const bool tinted =
        p2batch2tint::tintForKey(entry->second, tint) && shape->mMaterialList
        && shape->mMaterialCount > 0;
    struct SavedMaterial {
        Material* material;
        Colour poly;
        Colour konst;
        int regR, regG, regB, regA;
        bool hasTev;
    };
    std::vector<SavedMaterial> saved;
    auto mul = [](unsigned char base, unsigned char t) {
        return (unsigned char)((unsigned)base * (unsigned)t / 255u);
    };
    if (tinted) {
        saved.reserve(size_t(shape->mMaterialCount));
        for (int m = 0; m < shape->mMaterialCount; ++m) {
            Material& material = shape->mMaterialList[m];
            SavedMaterial entry_saved;
            entry_saved.material = &material;
            entry_saved.poly = material.mColourInfo.mColour;
            entry_saved.hasTev = material.mTevInfo != nullptr;
            if (entry_saved.hasTev) {
                entry_saved.konst = material.mTevInfo->mKonstColors[0];
                entry_saved.regR = material.mTevInfo->mTevColRegs[0].mAnimatedColor.r;
                entry_saved.regG = material.mTevInfo->mTevColRegs[0].mAnimatedColor.g;
                entry_saved.regB = material.mTevInfo->mTevColRegs[0].mAnimatedColor.b;
                entry_saved.regA = material.mTevInfo->mTevColRegs[0].mAnimatedColor.a;
                material.mTevInfo->mKonstColors[0].set(
                    mul(entry_saved.konst.r, tint.r), mul(entry_saved.konst.g, tint.g),
                    mul(entry_saved.konst.b, tint.b), entry_saved.konst.a);
                material.mTevInfo->mTevColRegs[0].mAnimatedColor.r =
                    entry_saved.regR * tint.r / 255;
                material.mTevInfo->mTevColRegs[0].mAnimatedColor.g =
                    entry_saved.regG * tint.g / 255;
                material.mTevInfo->mTevColRegs[0].mAnimatedColor.b =
                    entry_saved.regB * tint.b / 255;
            }
            material.mColourInfo.mColour.set(mul(entry_saved.poly.r, tint.r),
                                             mul(entry_saved.poly.g, tint.g),
                                             mul(entry_saved.poly.b, tint.b), entry_saved.poly.a);
            saved.push_back(entry_saved);
        }
        static std::set<std::string> tintLogged;
        if (tinted && tintLogged.insert(entry->second).second) {
            std::printf("P2_BATCH2_TINT key=%s tint=%u,%u,%u materials=%d\n",
                        entry->second.c_str(), tint.r, tint.g, tint.b, shape->mMaterialCount);
        }
    }
    shape->updateAnim(gfx, matrix, nullptr, actor);
    // Report a Pom draw only now: the forced clip survived every bank/clock/pose
    // guard above and is the clip about to be rendered, so a P2_POM_DRAW claims
    // a pose the draw chain actually drew, not merely a candidate clip name.
    if (name == forcedClip) pc_p2_pom_report_draw(actor);
    shape->drawshape(gfx, *gfx.mCamera, nullptr);
    for (const SavedMaterial& entry_saved : saved) {
        entry_saved.material->mColourInfo.mColour = entry_saved.poly;
        if (entry_saved.hasTev) {
            entry_saved.material->mTevInfo->mKonstColors[0] = entry_saved.konst;
            entry_saved.material->mTevInfo->mTevColRegs[0].mAnimatedColor.r = entry_saved.regR;
            entry_saved.material->mTevInfo->mTevColRegs[0].mAnimatedColor.g = entry_saved.regG;
            entry_saved.material->mTevInfo->mTevColRegs[0].mAnimatedColor.b = entry_saved.regB;
            entry_saved.material->mTevInfo->mTevColRegs[0].mAnimatedColor.a = entry_saved.regA;
        }
    }
    return true;
}

bool pc_p2_batch2_any_drawn() {
    return logged[0] || logged[1];
}

unsigned long pc_p2_batch2_count() { return (unsigned long)actors.size(); }
bool pc_p2_batch2_registered(BTeki* actor) { return actors.count(actor) != 0; }
unsigned long long pc_p2_batch2_event_count() {
    return eventCount;
}
