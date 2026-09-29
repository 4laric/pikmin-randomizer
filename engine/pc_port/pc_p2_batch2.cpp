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
#include "pc_p2_dweevil_clip.h"
#include "pc_p2_sokkuri.h"
#include "pc_p2_uji.h"
#include "pc_p2_armor.h"
#include "pc_p2_batch2_clock.h"
#include "pc_p2_elecbug.h"
#include "pc_p2_tamago.h"
#include "pc_p2_imomushi.h"
#include "pc_p2_otakara.h"
#include "pc_p2_pom.h"
#include "pc_p2_campaign_actor.h"
#include "pc_p2_campaign_policy.h"
#include "pc_p2_proxy.h"
#include "pc_p2_proxy_pack.h"
#include "pc_p2_pose_bank.h"
#include "pc_p2_pose_blend.h"
#include "pc_p2_pose_shape.h"
#include "pc_randomizer.h"
#include "gl/pc_gfx.h"
#include "pc_bbft.h"
#include "teki.h"
#include "Generator.h"
#include "Shape.h"
#include "system.h"
#include "Joint.h"
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
    {"uji", "uji", "p2-uji-actors.txt", "p2-uji-bank.txt"},
    {"cannon", "cannon", "p2-cannon-actors.txt", "p2-cannon-bank.txt"},
    {"waterwraith", "ww", "p2-waterwraith-actors.txt", "p2-waterwraith-bank.txt"},
    {"proxy", "px", "p2-proxy-actors.txt", "p2-proxy-bank.txt"},
};
constexpr size_t ClipBytes = 512 * 1024;         // per clip
constexpr size_t TotalBytes = 48 * 1024 * 1024;  // per setup

struct Bank {
    std::map<std::string, std::vector<Shape*>> clips;
    std::map<std::string, p2sampled::Clip> clock;
    std::map<std::string, std::vector<p2pose::Baked>> baked;
    std::map<std::string, bool> interp;
    std::string prefix;
    std::string fileSpecies;
};
struct ActorClock {
    p2batch2clock::Cursor cursor;
    std::string clip;
};
struct BlendState {
    Shape* shape = nullptr;
    p2pose::Pose scratch;
    std::string clip;
    float frame = 0.0f;
    bool corpse = false;
};
std::map<std::string, Bank> banks;             // key "family|species"
std::map<BTeki*, std::string> actors;          // actor -> key
std::map<BTeki*, ActorClock> clocks;           // actor -> sampled clock state
std::map<BTeki*, BlendState> blends;           // actor -> private deform target
bool interpolation = false;
size_t bytesTotal = 0;
bool logged[2] = {false, false};
std::set<std::string> proxyDrawn;            // "<corpse>|<key>" already reported
unsigned long long eventCount = 0;
std::set<std::string> proxyShotKeys;          // proxy keys whose shot was scheduled

[[noreturn]] void fail(const char* what) {
    std::fprintf(stderr, "P2_BATCH2 %s\n", what);
    std::abort();
}

static bool readBatch2InterpolationFlag() {
    std::ifstream direct("p2-batch2-interpolation.txt");
    if (direct) {
        std::string got, extra;
        if (!(direct >> got) || got != "P2_BATCH2_INTERPOLATION_1" || (direct >> extra))
            fail("invalid interpolation flag");
        return true;
    }
    std::ifstream assets("assets/p2-batch2-interpolation.txt");
    if (assets) {
        std::string got, extra;
        if (!(assets >> got) || got != "P2_BATCH2_INTERPOLATION_1" || (assets >> extra))
            fail("invalid interpolation flag");
        return true;
    }
    // Campaign default: interpolate unless PIKMIN_P2_INTERPOLATION=0 (nearest-pose fallback stays per clip).
    const char* env = std::getenv("PIKMIN_P2_INTERPOLATION");
    return !(env && env[0] == '0');
}

int expectedType(const std::string& family, const std::string& species) {
    if (family == "proxy") {
        const p2proxy::Table& table = pc_p2_proxy_table();
        if (!table.valid) return -1;
        const p2proxy::Row* row = p2proxy::bySpecies(table, species);
        return row ? row->host : -1;
    }
    if (family == "cannon") {
        if (species == "Kabuto" || species == "Rkabuto" || species == "Fkabuto") return TEKI_Beatle;
        if (species == "Rock" || species == "Stone") return TEKI_Iwagon;
    }
    if (family == "uji") {
        if (species == "UjiA") return TEKI_KabekuiA;
        if (species == "UjiB") return TEKI_KabekuiB;
        if (species == "Tobi") return TEKI_KabekuiC;
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
                std::vector<unsigned char>& reference, size_t& clipBytes,
                std::string* softError = nullptr,
                std::vector<unsigned char>* rawOut = nullptr) {
    const auto softFail = [&softError](const char* what) -> Shape* {
        if (softError) {
            *softError = what;
            return nullptr;
        }
        fail(what);
    };
    char rel[192];
    std::snprintf(rel, sizeof(rel), "assets/dataDir/courses/pikmin2room/%s_%s_%s_%02d.mod",
                  prefix.c_str(), species.c_str(), clip.c_str(), index);
    std::ifstream file(rel, std::ios::binary | std::ios::ate);
    if (!file) return softFail("missing pose bank");
    const auto size = file.tellg();
    if (size <= 0 || size_t(size) > ClipBytes || clipBytes + size_t(size) > ClipBytes
            || bytesTotal + size_t(size) > TotalBytes) return softFail("pose bank exceeds budget");
    clipBytes += size_t(size);
    bytesTotal += size_t(size);
    file.seekg(0);
    std::vector<unsigned char> data(size_t(size), 0), resources;
    if (!file.read(reinterpret_cast<char*>(data.data()), size)
            || !p2animation::resources(data, resources)) return softFail("invalid pose resources");
    if (!reference.empty() && reference != resources) return softFail("pose resources differ");
    reference = resources;
    if (rawOut) *rawOut = data;
    char load[160];
    std::snprintf(load, sizeof(load), "courses/pikmin2room/%s_%s_%s_%02d.mod",
                  prefix.c_str(), species.c_str(), clip.c_str(), index);
    Shape* shape = gameflow.loadShape(load, true);
    if (!shape) return softFail("pose load failed");
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
               std::map<std::string, std::vector<p2batch2clock::Row>>& out,
               std::string* softError = nullptr) {
    std::ifstream in(path);
    if (!in) return false;
    const auto softFail = [&softError](const char* what) -> bool {
        if (softError) {
            *softError = what;
            return false;
        }
        fail(what);
    };
    std::string word;
    if (!(in >> word) || word.size() < 9 || word.compare(0, 3, "P2_") != 0
            || word.compare(word.size() - 7, 7, "_BANK_1") != 0) return softFail("invalid bank header");
    std::string pending;
    bool havePending = false;
    auto nextToken = [&](std::string& tok) -> bool {
        if (havePending) {
            tok = pending;
            havePending = false;
            return true;
        }
        return bool(in >> tok);
    };
    auto pushBack = [&](const std::string& tok) {
        pending = tok;
        havePending = true;
    };
    while (nextToken(word)) {
        if (word == "species") {
            std::string species;
            unsigned long long id = 0;
            if (!(in >> species >> id)) return softFail("invalid bank species row");
            out.emplace(species, std::vector<p2batch2clock::Row>());
        } else if (word == "clip") {
            std::string species, name, events, status, marker;
            int frames = 0, poses = 0;
            if (!(in >> species >> name >> frames >> events >> marker >> poses >> status)
                    || marker != "poses" || frames < 0 || poses < 0 || poses > 64
                    || !out.count(species)) return softFail("invalid bank clip row");
            p2batch2clock::Row row;
            row.name = name;
            row.sourceFrames = frames;
            row.poseCount = poses;
            if (!p2batch2clock::parseEvents(events, row.events)) return softFail("invalid bank event token");
            std::string nxt;
            if (nextToken(nxt)) {
                if (nxt == "frames") {
                    std::string listTok;
                    if (!nextToken(listTok)) {
                        row.framesMalformed = true;
                    } else if (listTok == "species" || listTok == "clip" || listTok == "frames") {
                        pushBack(listTok);
                        row.framesMalformed = true;
                    } else {
                        std::vector<int> parsed;
                        if (!p2batch2clock::parseFramesList(listTok, parsed)) {
                            row.framesMalformed = true;
                        } else {
                            int duration = frames;
                            if (duration < 2) duration = poses >= 2 ? poses : 2;
                            bool ok = int(parsed.size()) == poses;
                            if (ok) {
                                for (size_t i = 0; i < parsed.size(); ++i) {
                                    if (parsed[i] < 0 || parsed[i] >= duration) {
                                        ok = false;
                                        break;
                                    }
                                    if (i == 0 && parsed[i] != 0) {
                                        ok = false;
                                        break;
                                    }
                                    if (i > 0 && parsed[i] <= parsed[i - 1]) {
                                        ok = false;
                                        break;
                                    }
                                }
                                if (ok && parsed.back() != duration - 1) ok = false;
                            }
                            if (!ok) {
                                row.framesMalformed = true;
                            } else {
                                row.poseFrames = std::move(parsed);
                            }
                        }
                    }
                } else {
                    pushBack(nxt);
                }
            }
            out[species].push_back(std::move(row));
        } else {
            return softFail("invalid bank token");
        }
    }
    return true;
}

Bank loadBank(const FamilyDef& family, const std::string& species,
              const std::vector<p2batch2clock::Row>& rows,
              std::string* softError = nullptr) {
    const auto softFail = [&softError](const char* what) -> Bank {
        if (softError) {
            *softError = what;
            return Bank();
        }
        fail(what);
    };
    Bank bank;
    bank.prefix = family.prefix;
    bank.fileSpecies = species;
    std::vector<unsigned char> reference;
    std::vector<unsigned char> topologyRef;
    bool haveTopologyRef = false;
    Shape* shared = nullptr;
    for (const auto& row : rows) {
        size_t clipBytes = 0;
        p2sampled::Clip clock = p2batch2clock::makeClip(row);
        if (!clock.valid()) return softFail("invalid sampled clock clip");
        bank.clock[row.name] = clock;
        bool allowInterp = interpolation && !row.framesMalformed && row.poseCount >= 2;
        bank.interp[row.name] = allowInterp;
        std::vector<p2pose::Baked> decoded;
        if (allowInterp) decoded.reserve(size_t(row.poseCount));
        for (int i = 0; i < row.poseCount; ++i) {
            std::string poseError;
            std::vector<unsigned char> raw;
            Shape* shape = loadPose(family.prefix, species, row.name, i, reference, clipBytes,
                                    softError ? &poseError : nullptr,
                                    allowInterp ? &raw : nullptr);
            if (!shape) {
                if (softError) {
                    *softError = poseError.empty() ? "pose load failed" : poseError;
                    return Bank();
                }
                fail("pose load failed");
            }
            if (!shared) {
                shared = shape;
                for (int t = 0; t < shape->mTexAttrCount; ++t)
                    if (shape->mTexAttrList[t].mTexture) shape->mTexAttrList[t].mTexture->attach();
            } else {
                if (shape->mMaterialCount != shared->mMaterialCount
                        || shape->mTexAttrCount != shared->mTexAttrCount
                        || shape->mTevInfoCount != shared->mTevInfoCount)
                    return softFail("material framing mismatch");
                for (int j = 0; j < shape->mTotalMatpolyCount; ++j) {
                    auto* poly = shape->mMatpolyList[j];
                    if (!poly || !poly->mMaterial) continue;
                    int material = -1;
                    for (int m = 0; m < shape->mMaterialCount; ++m)
                        if (poly->mMaterial == &shape->mMaterialList[m]) material = m;
                    if (material < 0) return softFail("pose material not found");
                    poly->mMaterial = &shared->mMaterialList[material];
                }
                shape->mMaterialList = shared->mMaterialList;
                shape->mTexAttrList = shared->mTexAttrList;
                shape->mTevInfoList = shared->mTevInfoList;
            }
            bank.clips[row.name].push_back(shape);
            if (allowInterp) {
                p2pose::Baked bakedPose;
                if (!p2pose::decodeBaked(raw, bakedPose)) {
                    allowInterp = false;
                    decoded.clear();
                } else {
                    decoded.push_back(std::move(bakedPose));
                }
            }
        }
        if (allowInterp) {
            bool ok = decoded.size() == size_t(row.poseCount) && !decoded.empty();
            if (ok) {
                const size_t positions = decoded.front().pose.positions.size();
                const size_t normals = decoded.front().pose.normals.size();
                if (positions == 0 || normals == 0) ok = false;
                for (const auto& entry : decoded) {
                    if (entry.pose.positions.size() != positions
                            || entry.pose.normals.size() != normals) {
                        ok = false;
                        break;
                    }
                    if (entry.topology != decoded.front().topology) {
                        ok = false;
                        break;
                    }
                }
                if (ok) {
                    if (haveTopologyRef && decoded.front().topology != topologyRef) ok = false;
                }
            }
            if (!ok) {
                allowInterp = false;
                decoded.clear();
            } else {
                if (!haveTopologyRef) {
                    topologyRef = decoded.front().topology;
                    haveTopologyRef = true;
                }
                bank.baked[row.name] = std::move(decoded);
            }
        }
        bank.interp[row.name] = allowInterp;
        if (!allowInterp) bank.baked.erase(row.name);
    }
    return bank;
}

static bool ensureBlendState(BTeki* actor, const std::string& key) {
    if (!interpolation || blends.count(actor)) return blends.count(actor) != 0;
    auto bankIt = banks.find(key);
    if (bankIt == banks.end()) return false;
    const Bank& bank = bankIt->second;
    const std::vector<p2pose::Baked>* baseBaked = nullptr;
    std::string baseClip;
    for (const auto& entry : bank.baked) {
        auto interpIt = bank.interp.find(entry.first);
        if (interpIt != bank.interp.end() && interpIt->second && !entry.second.empty()) {
            baseBaked = &entry.second;
            baseClip = entry.first;
            break;
        }
    }
    if (!baseBaked) return false;
    auto clipIt = bank.clips.find(baseClip);
    if (clipIt == bank.clips.end() || clipIt->second.empty()) return false;
    Shape* sharedShape = clipIt->second.front();
    if (!sharedShape) return false;
    const p2pose::Pose& base = baseBaked->front().pose;
    char path[192];
    std::snprintf(path, sizeof(path), "courses/pikmin2room/%s_%s_%s_00.mod",
                  bank.prefix.c_str(), bank.fileSpecies.c_str(), baseClip.c_str());
    const int previousHeap = gsys->setHeap(SYSHEAP_App);
    Shape* model = p2pose::privateShape(path, *sharedShape, base);
    gsys->setHeap(previousHeap);
    if (!model) return false;
    for (const auto& entry : blends) {
        if (entry.second.shape
                && (entry.second.shape->mVertexList == model->mVertexList
                    || entry.second.shape->mNormalList == model->mNormalList)) {
            return false;
        }
    }
    BlendState state;
    state.shape = model;
    state.scratch.positions.resize(base.positions.size());
    state.scratch.normals.resize(base.normals.size());
    blends.emplace(actor, std::move(state));
    unsigned generator = 0;
    if (actor && actor->mGenerator) generator = actor->mGenerator->_70;
    std::printf("P2_BATCH2_INTERPOLATION_READY key=%s generator=%u positions=%d normals=%d private_geometry=1 gameplay_clock=P1\n",
                key.c_str(), generator, model->mVertexCount, model->mNormalCount);
    return true;
}

// Erase every binding for one proxy key from all maps (#871 D4). Clocks and
// blend targets are keyed by actor, so dropping actors alone leaves stale
// entries that a recycled BTeki* address would inherit.
static void eraseProxySpecies(const std::string& key) {
    for (auto ait = actors.begin(); ait != actors.end();) {
        if (ait->second == key) {
            clocks.erase(ait->first);
            blends.erase(ait->first);
            ait = actors.erase(ait);
        } else {
            ++ait;
        }
    }
}

// Pre-sum a proxy species' pose bytes without loading (#871 D1). Returns true
// when the species would exceed ClipBytes (per clip) or TotalBytes (running
// total). Missing/unreadable files return false here and surface as
// load_failed from the soft loadBank below instead.
static bool proxyBudgetExceeds(const FamilyDef& family, const std::string& species,
                               const std::vector<p2batch2clock::Row>& clipRows,
                               size_t& speciesBytes) {
    speciesBytes = 0;
    for (const auto& row : clipRows) {
        size_t clipBytes = 0;
        for (int i = 0; i < row.poseCount; ++i) {
            char rel[192];
            std::snprintf(rel, sizeof(rel), "assets/dataDir/courses/pikmin2room/%s_%s_%s_%02d.mod",
                          family.prefix, species.c_str(), row.name.c_str(), i);
            std::ifstream file(rel, std::ios::binary | std::ios::ate);
            if (!file) return false;
            const auto size = file.tellg();
            if (size <= 0) return false;
            clipBytes += size_t(size);
            speciesBytes += size_t(size);
        }
        if (clipBytes > ClipBytes) return true;
    }
    return bytesTotal + speciesBytes > TotalBytes;
}
}

void pc_p2_batch2_reset() {
    banks.clear();
    actors.clear();
    clocks.clear();
    blends.clear();
    interpolation = false;
    bytesTotal = 0;
    eventCount = 0;
    logged[0] = logged[1] = false;
    proxyDrawn.clear();
    proxyShotKeys.clear();
    // D4: the proxy table is latched per reset, not per process. Stage
    // teardown (pc_p2_reset_all_teki) and TekiMgr::reset() both funnel through
    // here, and the process is reused across stages/sessions, so without this
    // the first session's table (or its absence) would persist.
    pc_p2_proxy_reset();
}

void pc_p2_batch2_forget(BTeki* actor) {
    // Dweevil corpse retention (wf7 dweevil-impl, #871): the pellet corpse
    // (mPellet != nullptr, dead) still needs its visual binding for viewDraw
    // (corpse=true) after the host death funnel. Forgetting here would drop
    // the dead pose and fall through to the native P1 Chappy shape, whose
    // animator is left on an attack/Type1 loop. Retain the binding while a
    // dead corpse pellet exists; it is released on pellet delivery/stage reset.
    if (actor && (actor->mHealth <= 0.0f || actor->mDeadState != 0) && actor->mPellet) {
        auto it = actors.find(actor);
        if (it != actors.end() && it->second.compare(0, 8, "dweevil|") == 0) return;
    }
    actors.erase(actor);
    clocks.erase(actor);
    blends.erase(actor);
}

// Scan the scene and bind present arena actors. ``strict`` is the startup
// contract (every configured actor must exist); ``false`` is the re-entry path
// after a legitimate family death, where absent actors are tolerated so the
// respawned actor can be re-bound without a stale pointer.
// Generated campaign sessions (the seed bridge) bind by the seed's source id per
// actor, like the behaviour modules, not by the arena sidecar's generator ids.
static bool proxyPoseAvailable(const FamilyDef& family, const std::string& species,
                               const std::vector<p2batch2clock::Row>& clipRows) {
    for (const auto& row : clipRows) {
        for (int i = 0; i < row.poseCount; ++i) {
            char rel[192];
            std::snprintf(rel, sizeof(rel), "assets/dataDir/courses/pikmin2room/%s_%s_%s_%02d.mod",
                          family.prefix, species.c_str(), row.name.c_str(), i);
            std::ifstream probe(rel, std::ios::binary);
            if (!probe) return false;
        }
    }
    return true;
}

static void campaignWanted(const FamilyDef& family, std::map<unsigned, std::string>& wanted) {
    static const struct { const char* family; unsigned source; const char* species; } SOURCES[] = {
        {"dweevil", 59, "FireOtakara"}, {"dweevil", 60, "WaterOtakara"},
        {"dweevil", 61, "GasOtakara"}, {"dweevil", 62, "ElecOtakara"},
        {"dweevil", 93, "BombOtakara"},
        {"ground", 79, "Sokkuri"},
        {"ground", 28, "ElecBug"},
        {"ground", 68, "TamagoMushi"},
        {"uji", 12, "UjiA"}, {"uji", 13, "UjiB"}, {"uji", 14, "Tobi"},
        // inst-worms lane (#871) round 2: Ravenous Whiskerpillar (65) draws
        // its P2 model through the ground family in bridge mode.
        {"ground", 65, "Imomushi"},
        {"ground", 84, "Hana"},
        // frogs4 (#871): Cloaking Burrow-nit (15) draws its P2 model through
        // the ground family in bridge mode (union with the integ rows above;
        // the Armor stager merges its p2-ground-*.txt rows with the other
        // ground species, so this row is safe to keep unconditionally).
        {"ground", 15, "Armor"},
    };
    wanted.clear();
    for (const auto& row : SOURCES)
        if (std::string(row.family) == family.name)
            for (unsigned id : pc_p2_campaign_ids(row.source)) wanted[id] = row.species;
    if (std::string(family.name) == "proxy") {
        // Finding 4: without the tier handshake the proxy family binds
        // nothing, so a stray p2-proxy-campaign.txt cannot affect a non-tier
        // seed (the spawn path already returns -1 via pc_p2_proxy_host).
        if (!pc_randomizer_p2_proxy_tier()) return;
        const p2proxy::Table& table = pc_p2_proxy_table();
        if (!table.valid) return;
        for (const auto& prow : table.rows) {
            // D2: static-host sources are untouchable by the visual path too.
            // hasStaticHost covers every hostType switch case (9,12-14,23,28,
            // 44,54,57,59-62,68,78,79,94 plus inst-chappy 2,33,35,43,53,67,76),
            // which includes batch2's own static SOURCES above.
            if (p2campaign::hasStaticHost(prow.source)) continue;
            for (unsigned id : pc_p2_campaign_ids(prow.source)) wanted[id] = prow.species;
        }
    }
}

static void bindFamilies(bool strict) {
    const bool bridge = pc_randomizer_p2_bridge() && !pc_pikipelago_room_preview();
    for (const FamilyDef& family : FAMILIES) {
        const bool isProxy = std::string(family.name) == "proxy";
        const bool soft = bridge && isProxy;
        std::map<unsigned, std::string> wanted;
        if (soft) {
            // D3: the proxy family never reads p2-proxy-actors.txt in bridge
            // mode; campaign identity comes from the table via campaignWanted.
            // A stale or half-written actors sidecar must not abort the campaign.
            campaignWanted(family, wanted);
            if (wanted.empty()) continue;
        } else {
            const bool haveActors = parseActors(family.actors, wanted);
            if (bridge) {
                // Bridge mode: campaign identity comes from the seed via
                // campaignWanted; a missing preview actors sidecar must not
                // block the campaign bind (mirrors the worms FSM setups).
                campaignWanted(family, wanted);
                if (wanted.empty()) continue;
            } else {
                if (!haveActors) continue;
            }
        }
        std::map<std::string, std::vector<p2batch2clock::Row>> rows;
        bool haveBank = false;
        if (soft) {
            std::ifstream bankProbe(family.bank);
            if (!bankProbe) {
                haveBank = false;
            } else {
                // D3: a present-but-malformed bank degrades to a single
                // bad_bank skip (every proxy actor stays a plain host) instead
                // of fail(). parseBank reports the reason via softError and
                // never calls fail() on this path.
                std::string bankError;
                if (!parseBank(family.bank, rows, &bankError)) {
                    std::printf("P2_SETUP_SKIP batch2 proxy bad_bank\n");
                    continue;
                }
                haveBank = true;
            }
        } else {
            if (!parseBank(family.bank, rows)) {
                if (bridge) {
                    std::printf("P2_SETUP_SKIP batch2 %s missing_bank\n", family.name);
                    continue;
                }
                fail("missing bank for present actor config");
            }
            haveBank = true;
        }

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
            // Finding 5: pack generators share one campaign token across
            // members. The proxy family in bridge mode binds EVERY live
            // member and counts the token once (found already holds it, so
            // repeats fall through to the bind below with no second insert).
            // The Uji and ground families share this tolerance in bridge mode:
            // P1 KabekuiA/B/C vehicles group-spawn (a Sheargrub burrow pours
            // several Teki from one generator) and Mitite (TamagoMushi) nest
            // as swarms, so repeats are pack members, not a scene mismatch.
            // All other families keep the duplicate-generator abort.
            const std::string famName = family.name;
            const bool packTolerant =
                soft || (bridge && (famName == "uji" || famName == "ground"));
            if (p2proxy::tokenAction(packTolerant, !found.insert(generator).second)
                    == p2proxy::TokenAction::Fail) {
                char msg[256];
                std::snprintf(msg, sizeof(msg), "duplicate generator=%u family=%s in scene",
                              generator, family.name);
                fail(msg);
            }
            actors[teki] = std::string(family.name) + "|" + match->second;
            speciesUsed.insert(match->second);
            // bot-v7 (wf10): lane-06 ordinary-delivery source for proxy
            // campaign actors. Visual-only proxies never bound one (only
            // Sokkuri/Kogane/ElecBug/Sarai bind), so a hauled proxy corpse
            // could never grant onion:p2: GoalItem::suckMe found no source
            // for the pellet view, fell through to the P1 bestiary CHECK,
            // and no P2_ORDINARY_P2_RECEIPT ever fired (v6b-1: Chappy and
            // Tadpole corpses reached the Onion with crews attached, yet the
            // bot could never score received=1). Bridge mode only: bind
            // (actor -> (source, token)); Teki IS-A PelletView (teki.h:
            // NTeki : BTeki : PelletView), so this is the same subobject
            // address suckMe looks up. Single-use (consumed on delivery),
            // cleared on the corpse-less death funnel (BTeki::doKill ->
            // pc_p2_forget_teki) and on pool-slot reuse (TekiMgr::newTeki),
            // while corpse-leaving deaths skip doKill so the binding survives
            // to the Onion. Tokens with no seed source keep today's P1 path.
            if (bridge && std::string(family.name) == "proxy") {
                const unsigned source = pc_randomizer_p2_source_for_id(generator);
                if (source != 0) {
                    pc_randomizer_p2_bind_source(static_cast<PelletView*>(teki), source, generator);
                    std::printf("P2_PROXY_DELIVERY_BIND generator=%u source_id=%u key=proxy|%s\n",
                                generator, source, match->second.c_str());
                    std::fflush(stdout);
                }
            }
        }
        if (found.size() != wanted.size()) {
            if (strict) fail("arena actor not present in scene");
            std::printf("P2_BATCH2_MISSING family=%s found=%zu wanted=%zu\n",
                        family.name, found.size(), wanted.size());
        }
        if (soft && !haveBank) {
            for (const std::string& species : speciesUsed) {
                std::printf("P2_SETUP_SKIP batch2 proxy missing_bank species=%s\n", species.c_str());
                eraseProxySpecies(std::string(family.name) + "|" + species);
            }
            continue;
        }
        // speciesUsed is a std::set, so iteration is sorted by species name:
        // budget outcomes are reproducible regardless of scene order.
        for (const std::string& species : speciesUsed) {
            auto clipRows = rows.find(species);
            if (clipRows == rows.end() || clipRows->second.empty()) {
                if (soft) {
                    std::printf("P2_SETUP_SKIP batch2 proxy no_bank_clips species=%s\n", species.c_str());
                    eraseProxySpecies(std::string(family.name) + "|" + species);
                    continue;
                }
                if (bridge) {
                    // Bridge mode: a bound campaign actor without staged bank
                    // clips keeps its P2 behaviour (FSM setups bind sources)
                    // and skips only the P2 visual. Unbinds this species key.
                    std::printf("P2_SETUP_SKIP batch2 %s no_bank_clips species=%s\n",
                                family.name, species.c_str());
                    for (auto ai = actors.begin(); ai != actors.end();) {
                        if (ai->second == std::string(family.name) + "|" + species)
                            ai = actors.erase(ai);
                        else
                            ++ai;
                    }
                    continue;
                }
                fail("species has no bank clips");
            }
            if (soft && !proxyPoseAvailable(family, species, clipRows->second)) {
                std::printf("P2_SETUP_SKIP batch2 proxy missing_pose species=%s\n", species.c_str());
                eraseProxySpecies(std::string(family.name) + "|" + species);
                continue;
            }
            const std::string key = std::string(family.name) + "|" + species;
            if (soft && !banks.count(key)) {
                // D1: pre-sum pose bytes before loadBank so a full-proxy area
                // degrades to a budget skip instead of fail() aborting the
                // campaign mid-setup.
                size_t speciesBytes = 0;
                if (proxyBudgetExceeds(family, species, clipRows->second, speciesBytes)) {
                    std::printf("P2_SETUP_SKIP batch2 proxy budget species=%s bytes=%zu total=%zu\n",
                                species.c_str(), speciesBytes, bytesTotal);
                    eraseProxySpecies(key);
                    continue;
                }
                // D1/D3: any other loadBank/loadPose failure (resource
                // mismatch, unreadable pose, bad clock, material mismatch)
                // degrades to load_failed + erase, not fail(). The softError
                // out-param leaves loadBank/loadPose behaviour for the five
                // existing families EXACTLY as today (they pass nullptr and
                // still fail()); see the handoff for why soft-param was chosen
                // over exceptions even though the target builds with
                // exceptions enabled (gnu++17, no -fno-exceptions).
                const size_t bytesBefore = bytesTotal;
                std::string loadError;
                Bank bank = loadBank(family, species, clipRows->second, &loadError);
                if (!loadError.empty()) {
                    bytesTotal = bytesBefore;
                    std::printf("P2_SETUP_SKIP batch2 proxy load_failed species=%s reason=%s\n",
                                species.c_str(), loadError.c_str());
                    eraseProxySpecies(key);
                    continue;
                }
                banks[key] = std::move(bank);
            } else if (!banks.count(key)) {
                if (bridge) {
                    // Bridge mode: a pose-load failure degrades to a visual
                    // skip (behaviour still bound), never a campaign abort.
                    const size_t bytesBefore = bytesTotal;
                    std::string loadError;
                    Bank bank = loadBank(family, species, clipRows->second, &loadError);
                    if (!loadError.empty()) {
                        bytesTotal = bytesBefore;
                        std::printf("P2_SETUP_SKIP batch2 %s load_failed species=%s reason=%s\n",
                                    family.name, species.c_str(), loadError.c_str());
                        for (auto ai = actors.begin(); ai != actors.end();) {
                            if (ai->second == key)
                                ai = actors.erase(ai);
                            else
                                ++ai;
                        }
                        continue;
                    }
                    banks[key] = std::move(bank);
                } else {
                    banks[key] = loadBank(family, species, clipRows->second);
                }
            }
        }
    }
    if (interpolation) {
        for (const auto& entry : actors) ensureBlendState(entry.first, entry.second);
    }
}

static void logBindings() {
    const bool bridge = pc_randomizer_p2_bridge() && !pc_pikipelago_room_preview();
    for (const auto& entry : actors)
        std::printf("P2_BATCH2_BIND generator=%u key=%s visual_only=%d native_fsm=%s token=%u\n",
                    entry.first->mGenerator ? entry.first->mGenerator->_70 : 0, entry.second.c_str(),
                     (entry.second == "ground|Sokkuri" || entry.second == "ground|Armor" || entry.second == "ground|ElecBug" || entry.second == "ground|TamagoMushi" || entry.second == "ground|Imomushi" || entry.second == "ground|Hana" || entry.second == "uji|UjiA" || entry.second == "uji|UjiB" || entry.second == "uji|Tobi") ? 0 : 1,
                     (entry.second == "ground|Sokkuri" || entry.second == "ground|Armor" || entry.second == "ground|ElecBug" || entry.second == "ground|TamagoMushi" || entry.second == "ground|Imomushi" || entry.second == "ground|Hana" || entry.second == "uji|UjiA" || entry.second == "uji|UjiB" || entry.second == "uji|Tobi") ? "implemented" : "unimplemented",
                    bridge ? pc_p2_campaign_token(entry.first) : (entry.first->mGenerator ? entry.first->mGenerator->_70 : 0));
    std::printf("P2_BATCH2_BANK total_mod_bytes=%zu species=%zu\n", bytesTotal, banks.size());
}

void pc_p2_batch2_setup() {
    pc_p2_batch2_reset();
    interpolation = readBatch2InterpolationFlag();
    if (interpolation) std::printf("P2_BATCH2_INTERPOLATION_READY interpolation=1 gameplay_clock=P1\n");
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
    if (!(pc_pikipelago_room_preview() || pc_randomizer_p2_bridge()) || !tekiMgr) {
        // D4: no rebind means every clock is stale; the next draw re-creates
        // entries on demand.
        clocks.clear();
        blends.clear();
        return;
    }
    bindFamilies(false);
    // D4: drop clocks for actors that did not rebind (freed actors whose
    // address may be recycled); survivors keep their cursors.
    for (auto cit = clocks.begin(); cit != clocks.end();) {
        if (actors.count(cit->first) == 0)
            cit = clocks.erase(cit);
        else
            ++cit;
    }
    for (auto bit = blends.begin(); bit != blends.end();) {
        if (actors.count(bit->first) == 0)
            bit = blends.erase(bit);
        else
            ++bit;
    }
    logBindings();
}

// A proxy actor that binds but cannot draw leaves the plain host visible, which
// is safe but silent. Name the early return once per (key, reason) so a probe
// log says why a species never rendered (#871).
static bool proxySkip(const std::string& key, const char* reason, int motion, bool corpse) {
    if (key.compare(0, 6, "proxy|") == 0 && proxyDrawn.insert(std::string("skip|") + reason + "|" + key).second)
        std::printf("P2_PROXY_DRAW_SKIP key=%s reason=%s motion=%d corpse=%d\n", key.c_str(), reason, motion, int(corpse));
    return false;
}

bool pc_p2_batch2_draw(BTeki* actor, Graphics& gfx, const Matrix4f& matrix, bool corpse) {
    auto entry = actors.find(actor);
    if (entry == actors.end() || !gfx.mCamera || !actor->mTekiAnimator) return false;
    auto bankIt = banks.find(entry->second);
    if (bankIt == banks.end()) return proxySkip(entry->second, "no_bank", -1, corpse);
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
        if ((pc_p2_sokkuri_clip(actor, forced, phase) || pc_p2_uji_clip(actor, forced, phase)
                || pc_p2_armor_clip(actor, forced, phase)
                || pc_p2_elecbug_clip(actor, forced, phase) || pc_p2_tamago_clip(actor, forced, phase)
                || pc_p2_imomushi_clip(actor, forced, phase) || pc_p2_hana_clip(actor, forced, phase)
                || pc_p2_otakara_clip(actor, forced, phase) || pc_p2_pom_clip(actor, forced, phase))
                && bank.clips.count(forced)) {
            name = forced;
            forcedPhase = phase;
            forcedClip = forced;
        }
    }
    // Dweevil death-clip guarantee (wf7 dweevil-impl, #871): a dead dweevil
    // plays its death clip then holds the dead pose, never attack1. While
    // alive the visual follows the Otakara FSM only, so the generic P1-motion
    // attack fallback must never independently animate a dweevil (no actor
    // animated by two P2 layers). Covers all four species 59-62 via key.
    const bool isDweevil = p2dweevilclip::isDweevilKey(entry->second);
    const bool dead = (actor->mHealth <= 0.0f || actor->mDeadState != 0);
    if (isDweevil) {
        const bool hasForced = (name != nullptr);
        const std::string forcedName = hasForced ? std::string(name) : std::string();
        const bool hasDead = firstClip(bank, deadClips, int(sizeof(deadClips) / sizeof(deadClips[0]))) != nullptr;
        const std::string chosen = p2dweevilclip::choose(entry->second, corpse, dead,
                                                         hasForced, forcedName, hasDead, true);
        if (!chosen.empty()) {
            if (chosen == "dead") {
                name = firstClip(bank, deadClips, int(sizeof(deadClips) / sizeof(deadClips[0])));
                // After the Otakara binding is forgotten the sidecar phase is
                // gone; hold the final dead pose instead of sampling a stale
                // attack counter.
                if (forcedPhase < 0.0f) forcedPhase = 1.0f;
            } else {
                // Forced Otakara clip (wait/move/attack/dead while registered).
                // name already holds it; keep its phase.
            }
        } else {
            // Live dweevil without a forced clip: fall through to wait/move
            // below, never the motion-based attack pick.
            name = nullptr;
        }
    }
    if (corpse) {
        if (!isDweevil) name = firstClip(bank, deadClips, int(sizeof(deadClips) / sizeof(deadClips[0])));
        else if (!name) name = firstClip(bank, deadClips, int(sizeof(deadClips) / sizeof(deadClips[0])));
    } else if (!name && !isDweevil && (motion == TekiMotion::Damage || motion >= TekiMotion::Type1)) {
        name = firstClip(bank, attackClips, int(sizeof(attackClips) / sizeof(attackClips[0])));
    }
    if (!name) {
        const f32 speed = actor->mVelocity.x * actor->mVelocity.x + actor->mVelocity.z * actor->mVelocity.z;
        name = speed > 1.f
            ? firstClip(bank, moveClips, int(sizeof(moveClips) / sizeof(moveClips[0])))
            : firstClip(bank, waitClips, int(sizeof(waitClips) / sizeof(waitClips[0])));
    }
    if (!name) name = firstClip(bank, waitClips, int(sizeof(waitClips) / sizeof(waitClips[0])));
    if (!name) return proxySkip(entry->second, "no_clip", motion, corpse);
    const auto& poses = bank.clips.at(name);
    if (poses.empty()) return proxySkip(entry->second, "empty_poses", motion, corpse);
    const int frames = actor->mTekiAnimator->getFrameCount();
    const float phase = forcedPhase >= 0.0f ? forcedPhase
        : (frames > 1 ? actor->mTekiAnimator->getCounter() / (frames - 1) : 0.f);
    const p2sampled::Clip& clock = bank.clock.at(name);
    ActorClock& state = clocks[actor];
    if (state.clip != name) {
        if (!state.cursor.start(clock)) return proxySkip(entry->second, "clock_start", motion, corpse);
        state.clip = name;
    }
    const double sourceFrame = double(phase) * double(clock.poses.duration - 1);
    p2batch2clock::Step step = state.cursor.stepTo(sourceFrame);
    if (!step.ok) return proxySkip(entry->second, "clock_step", motion, corpse);
    for (const p2sampled::Occurrence& event : step.events) {
        ++eventCount;
        if (eventCount <= 16u) {
            const unsigned token = pc_p2_campaign_token(actor);
            std::printf("P2_BATCH2_EVENT key=%s clip=%s frame=%d event=%s cycle=%llu token=%u\n",
                        entry->second.c_str(), name, event.frame, event.key.c_str(),
                        static_cast<unsigned long long>(event.cycle), token);
        }
    }
    const size_t index = (corpse || (isDweevil && dead)) ? poses.size() - 1
                               : (step.pose < poses.size() ? step.pose : poses.size() - 1);
    Shape* shape = poses.at(index);
    if (interpolation && !corpse) {
        auto interpIt = bank.interp.find(name);
        auto bakedIt = bank.baked.find(name);
        if (interpIt != bank.interp.end() && interpIt->second && bakedIt != bank.baked.end()
                && !bakedIt->second.empty() && bakedIt->second.size() == poses.size()) {
            std::vector<int> frames = bank.clock.at(name).poses.frames;
            if (frames.empty())
                frames = p2batch2clock::uniformFrames(int(poses.size()), bank.clock.at(name).poses.duration);
            p2pose::Interval span;
            if (frames.size() == poses.size() && p2pose::bracket(frames, float(sourceFrame), span)
                    && span.left < bakedIt->second.size() && span.right < bakedIt->second.size()) {
                if (!blends.count(actor)) ensureBlendState(actor, entry->second);
                auto blendIt = blends.find(actor);
                if (blendIt != blends.end() && blendIt->second.shape) {
                    const auto& bakedVec = bakedIt->second;
                    const auto& left = bakedVec[span.left].pose;
                    const auto& right = bakedVec[span.right].pose;
                    if (left.positions.size() == size_t(blendIt->second.shape->mVertexCount)
                            && left.normals.size() == size_t(blendIt->second.shape->mNormalCount)
                            && left.positions.size() == right.positions.size()
                            && left.normals.size() == right.normals.size()
                            && p2pose::apply(*blendIt->second.shape, left, right, span.weight,
                                             blendIt->second.scratch)) {
                        shape = blendIt->second.shape;
                        if (blendIt->second.clip != name || blendIt->second.corpse != corpse) {
                            std::printf(
                                "P2_BATCH2_BLEND key=%s clip=%s corpse=%d source_frame=%.5f left=%zu "
                                "right=%zu weight=%.5f\n",
                                entry->second.c_str(), name, int(corpse), sourceFrame, span.left,
                                span.right, span.weight);
                        }
                        blendIt->second.clip = name;
                        blendIt->second.frame = float(sourceFrame);
                        blendIt->second.corpse = corpse;
                    }
                }
            }
        }
    }
    if (!logged[corpse ? 1 : 0]) {
        std::printf("P2_BATCH2_DRAW corpse=%d key=%s clip=%s\n", int(corpse), entry->second.c_str(), name);
        logged[corpse ? 1 : 0] = true;
    }
    // Campaign-identity families report per key (once per key+corpse+token),
    // so bot-campaign evidence cites each species' own draw line instead of
    // racing the run-global single line above. Bounded: one line per species
    // per session, exactly like the proxy per-key lines below.
    if (entry->second.compare(0, 6, "proxy|") != 0 && !isDweevil) {
        unsigned drawToken = pc_p2_campaign_token(actor);
        if (!drawToken && actor->mGenerator) drawToken = actor->mGenerator->_70;
        if (proxyDrawn.insert(std::string(corpse ? "1|" : "0|") + entry->second + "|" + std::to_string(drawToken)).second) {
            std::printf("P2_BATCH2_DRAW corpse=%d key=%s clip=%s generator=%u token=%u\n", int(corpse), entry->second.c_str(), name, drawToken, drawToken);
            std::fflush(stdout);
        }
    }
    // Dweevil per-corpse evidence (wf7 dweevil-impl, #871): first dead draw per
    // campaign token, so headless can prove the corpse holds clip=dead from
    // the first dead frame with no later attack1 event for that actor.
    if (isDweevil && (corpse || dead)) {
        const unsigned token = pc_p2_campaign_token(actor);
        const unsigned logToken = token ? token : (actor->mGenerator ? actor->mGenerator->_70 : 0);
        if (proxyDrawn.insert(std::string("dweevil|") + (corpse ? "1|" : "0|") + entry->second + "|" + std::to_string(logToken) + "|" + name).second) {
            std::printf("P2_DWEEVIL_CORPSE_DRAW token=%u key=%s clip=%s corpse=%d dead=%d\n",
                        logToken, entry->second.c_str(), name, int(corpse), int(dead));
            std::fflush(stdout);
        }
    }
    // inst-worms lane (#871) round 2: per-actor campaign DRAW markers for
    // ground|Imomushi (the global P2_BATCH2_DRAW above fires once per session
    // and may belong to another family). Once per actor, corpse separately.
    if (entry->second == "ground|Imomushi") {
        const unsigned token = pc_p2_campaign_token(actor);
        const std::string memo =
            std::string(corpse ? "1|" : "0|") + entry->second + "|" + std::to_string(token);
        if (proxyDrawn.insert(memo).second)
            std::printf("P2_IMOMUSHI_DRAW corpse=%d key=%s clip=%s token=%u generator=%u\n",
                        int(corpse), entry->second.c_str(), name, token, token);
    }
    // Proxy species are probed per species, so each proxy key reports its first
    // live and first corpse draw (#871); the families above keep the single line.
    if (entry->second.compare(0, 6, "proxy|") == 0) {        const unsigned token = pc_p2_campaign_token(actor);
        if (proxyDrawn.insert(std::string(corpse ? "1|" : "0|") + entry->second + "|" + std::to_string(token)).second)
            std::printf("P2_PROXY_DRAW corpse=%d key=%s clip=%s token=%u\n", int(corpse), entry->second.c_str(), name, token);
        // Probe screenshot hook (#871): the FIRST live draw per key (not per
        // token) schedules a capture 30 frames later. The gfx side is
        // env-gated, so without PIKMIN_P2_PROXY_SHOT this is one set insert
        // per key per session plus one disabled branch.
        if (!corpse && proxyShotKeys.insert(entry->second).second)
            pc_gfx_proxy_shot_notify(entry->second.c_str());
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
