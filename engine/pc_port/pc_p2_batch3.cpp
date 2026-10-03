#include "pc_p2_umimushi.h"
#include "pc_p2_jigumo.h"
#include "pc_p2_snakejoint.h"
#include "pc_p2_dangomushi.h"
#include "pc_p2_hanachirashi.h"
#include "pc_p2_catfish.h"
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
#include "pc_p2_original_actor.h"
#include "Pellet.h"
#include "pc_p2_campaign_actor.h"
#include "pc_p2_setup_failsafe.h"
#include "pc_randomizer.h"
#include "pc_p2_animation.h"
#include "pc_p2_campaign_actor.h"
#include "pc_p2_tadpole.h"
#include "pc_p2_mar.h"
#include "pc_p2_pose_bank.h"
#include "pc_p2_pose_blend.h"
#include "pc_p2_pose_shape.h"
#include "pc_p2_pose_loader.h"
#include "pc_p2_pose_motion.h"
#include "pc_bbft.h"
#include "teki.h"
#include "Generator.h"
#include "Shape.h"
#include "system.h"
#include "Joint.h"
#include "Texture.h"
#include "Graphics.h"
#include "Camera.h"
#include "gameflow.h"
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include "pc_p2_body_coll.h"
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
// Resident budgets (#895), see pc_p2_pose_loader.h and pc_p2_batch2.cpp.
// #895 budgets (owner-approved 1 MiB per clip), shared with every pose-bank loader.
constexpr size_t PoseFileBytes = p2poseload::PoseFileBytes;  // per pose file
constexpr size_t ClipBytes = p2poseload::ClipBytes;          // resident per clip (1 MiB)
constexpr size_t TotalBytes = p2poseload::TotalBytes;        // resident per setup (48 MiB)

struct ClipRow {
    std::string name;
    int sourceFrames = 0;
    int poseCount = 0;
    std::vector<int> poseFrames;
    bool framesMalformed = false;
};
struct Bank {
    std::map<std::string, std::vector<Shape*>> clips;
    std::map<std::string, p2animation::Clip> timing;
    std::map<std::string, std::vector<p2pose::Baked>> baked;
    std::map<std::string, bool> interp;
    std::map<std::string, bool> seam;  // loop seam continuous (#895)
    std::map<std::string, size_t> hold;  // last visible pose (#895 death clips)
    std::string prefix;
    std::string fileSpecies;
};
struct BlendState {
    p2pose::Track track;
    bool corpse = false;
};
std::map<std::string, Bank> banks;             // key "family|species"
std::map<BTeki*, std::string> actors;          // actor -> key
std::map<BTeki*, BlendState> blends;           // actor -> private deform target
std::map<BTeki*, p2motion::MoveGate> gates;    // actor -> move/wait hysteresis
std::set<std::string> drawnKeys;               // "<corpse>|<key>|<token>" already reported
// Worms lane (#871) round 2: once-per-actor campaign DRAW markers for the
// evidence scorer (bound/drawn/killed/carried/received). Cleared on reset,
// erased on forget so a recycled actor address re-reports.
std::set<BTeki*> wormDrawn;
std::set<BTeki*> wormCorpseDrawn;
bool interpolation = false;
size_t bytesTotal = 0;
bool logged[2] = {false, false};

[[noreturn]] void fail(const char* what);

static bool readBatch3InterpolationFlag() {
    std::ifstream direct("p2-batch3-interpolation.txt");
    if (direct) {
        std::string got, extra;
        if (!(direct >> got) || got != "P2_BATCH3_INTERPOLATION_1" || (direct >> extra))
            fail("invalid interpolation flag");
        return true;
    }
    std::ifstream assets("assets/p2-batch3-interpolation.txt");
    if (assets) {
        std::string got, extra;
        if (!(assets >> got) || got != "P2_BATCH3_INTERPOLATION_1" || (assets >> extra))
            fail("invalid interpolation flag");
        return true;
    }
    // Campaign default: interpolate unless PIKMIN_P2_INTERPOLATION=0 (nearest-pose fallback stays per clip).
    const char* env = std::getenv("PIKMIN_P2_INTERPOLATION");
    return !(env && env[0] == '0');
}

inline bool parseFramesListToken(const std::string& token, std::vector<int>& out) {
    out.clear();
    if (token.empty() || token.size() > 512) return false;
    size_t at = 0;
    while (true) {
        const size_t comma = token.find(',', at);
        const std::string part =
            comma == std::string::npos ? token.substr(at) : token.substr(at, comma - at);
        if (part.empty() || part.size() > 6) return false;
        for (char c : part) {
            if (c < '0' || c > '9') return false;
        }
        long value = 0;
        try {
            value = std::stol(part);
        } catch (...) {
            return false;
        }
        if (value < 0 || value > 10000) return false;
        out.push_back(int(value));
        if (out.size() > 64) return false;
        if (comma == std::string::npos) break;
        at = comma + 1;
    }
    return !out.empty();
}

inline std::vector<int> uniformFramesFor(int count, int duration) {
    std::vector<int> out;
    if (count <= 0 || duration <= 0) return out;
    if (count == 1) {
        out.push_back(0);
        return out;
    }
    for (int i = 0; i < count; ++i) {
        const double v = double(i) * double(duration - 1) / double(count - 1);
        int frame = int(std::floor(v + 0.5));
        if (frame < 0) frame = 0;
        if (frame >= duration) frame = duration - 1;
        out.push_back(frame);
    }
    return out;
}

[[noreturn]] void fail(const char* what) {
    std::fprintf(stderr, "P2_BATCH3 %s\n", what);
    std::abort();
}

int expectedType(const std::string& family, const std::string& species) {
    if (family == "aquatic") {
        if (species == "Catfish") return TEKI_Namazu;   // P1 Water Dumple ancestor
        if (species == "Tadpole") return TEKI_Otama;    // P1 Wogpole ancestor
        if (species == "Jigumo") return TEKI_Chappy;    // Hermit Crawmad: no P1 counterpart, placement vehicle only
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

bool parseBank(const std::string& path, std::map<std::string, std::vector<ClipRow>>& out, std::string* error=nullptr) {
    auto reject=[&](const char* why)->bool {if(error){*error=why;return false;}fail(why);};
    std::ifstream in(path);
    if (!in) return false;
    std::string word;
    if (!(in >> word) || word.size() < 9 || word.compare(0, 3, "P2_") != 0
            || word.compare(word.size() - 7, 7, "_BANK_1") != 0) return reject("invalid bank header");
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
            std::string species, identity;
            if (!(in >> species >> identity)) return reject("invalid bank species row");
            // Batch-3 families currently differ: aquatic/snagret write the
            // numeric enemy id, the flying install writes `clips <count>`.
            if (identity == "clips") {
                int clips = 0;
                if (!(in >> clips) || clips < 0) return reject("invalid bank species row");
            } else {
                char* end = nullptr;
                std::strtoull(identity.c_str(), &end, 10);
                if (end == identity.c_str() || *end != '\0') return reject("invalid bank species row");
            }
            out.emplace(species, std::vector<ClipRow>());
        } else if (word == "clip") {
            std::string species, name, events, status, marker, value;
            int frames = 0, poses = 0;
            if (!(in >> species >> name >> frames >> events >> marker >> poses)
                    || marker != "poses" || poses < 0 || poses > 64
                    || !out.count(species)) return reject("invalid bank clip row");
            // The flying install writes a literal `status` token before the
            // value; aquatic/snagret write the value directly.
            if (!(in >> value)) return reject("invalid bank clip row");
            if (value != "status") status = value;
            else if (!(in >> status)) return reject("invalid bank clip row");
            ClipRow row;
            row.name = name;
            row.sourceFrames = frames;
            row.poseCount = poses;
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
                        if (!parseFramesListToken(listTok, parsed)) {
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
            return reject("invalid bank token");
        }
    }
    return true;
}

Bank loadBank(const FamilyDef& family, const std::string& species,
              const std::vector<ClipRow>& rows, std::string* outError=nullptr) {
    Bank bank;
    bank.prefix = family.prefix;
    bank.fileSpecies = species;
    p2poseload::Shared shared;
    const p2poseload::Limits limits{PoseFileBytes, ClipBytes, TotalBytes};
    for (const auto& clip : rows) {
        p2animation::Clip timing;
        timing.name = clip.name;
        timing.count = clip.poseCount;
        int duration = clip.sourceFrames;
        if (duration < 2) duration = clip.poseCount >= 2 ? clip.poseCount : 2;
        timing.duration = duration;
        if (!clip.framesMalformed && !clip.poseFrames.empty()
                && int(clip.poseFrames.size()) == clip.poseCount) {
            bool ok = true;
            for (size_t i = 0; i < clip.poseFrames.size(); ++i) {
                if (clip.poseFrames[i] < 0 || clip.poseFrames[i] >= duration) {
                    ok = false;
                    break;
                }
                if (i == 0 && clip.poseFrames[i] != 0) {
                    ok = false;
                    break;
                }
                if (i > 0 && clip.poseFrames[i] <= clip.poseFrames[i - 1]) {
                    ok = false;
                    break;
                }
            }
            if (ok && clip.poseFrames.back() != duration - 1) ok = false;
            if (ok) timing.frames = clip.poseFrames;
        }
        bank.timing[clip.name] = timing;
        p2poseload::Clip loaded;
        std::string error;
        if (!p2poseload::loadClip(family.prefix, species, clip.name, clip.poseCount, limits, shared,
                                  bytesTotal, loaded, error))
        {
            if (outError) { *outError=error.empty()?"pose load failed":error; return bank; }
            fail(error.empty() ? "pose load failed" : error.c_str());
        }
        if (!loaded.shapes.empty()) bank.clips[clip.name] = loaded.shapes;  // 0-pose rows stay undrawable
        bank.interp[clip.name] = interpolation && !clip.framesMalformed && clip.poseCount >= 2;
        if (loaded.vectors) {
            std::vector<int> frames = timing.frames;
            if (frames.empty()) frames = uniformFramesFor(clip.poseCount, timing.duration);
            bank.seam[clip.name] = p2poseload::seamOf(loaded.baked, frames);
            const p2motion::HoldPick holdPick = p2motion::holdPick(
                loaded.baked.size(), [&loaded](size_t i) -> const p2pose::Pose& { return loaded.baked[i].pose; });
            bank.hold[clip.name] = holdPick.index;
            if (holdPick.adjusted)
                std::printf("P2_POSE_HOLD_ADJUST species=%s clip=%s legacy=%zu held=%zu first_bad=%zu ratio_high=%.2f "
                            "ratio_low=%.2f poses=%zu\n",
                            species.c_str(), clip.name.c_str(), holdPick.legacy, holdPick.index, holdPick.firstBad,
                            double(holdPick.worstHigh), double(holdPick.worstLow), loaded.baked.size());
            bank.baked[clip.name] = std::move(loaded.baked);
        }
    }
    return bank;
}

static bool ensureBlendState(BTeki* actor, const std::string& key) {
    if (blends.count(actor)) return true;
    auto bankIt = banks.find(key);
    if (bankIt == banks.end()) return false;
    const Bank& bank = bankIt->second;
    pc_p2_body_coll_register_bank(key, bank.baked);  // shared body collision fit (rest pose)
    const std::vector<p2pose::Baked>* baseBaked = nullptr;
    std::string baseClip;
    for (const auto& entry : bank.baked) {
        if (!entry.second.empty()) {
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
    std::snprintf(path, sizeof(path), "courses/pikmin2room/%s_%s_%s_00.mod", bank.prefix.c_str(),
                  bank.fileSpecies.c_str(), baseClip.c_str());
    const int previousHeap = gsys->setHeap(SYSHEAP_App);
    Shape* model = p2pose::privateShape(path, *sharedShape, base);
    gsys->setHeap(previousHeap);
    if (!model) return false;
    for (const auto& entry : blends) {
        if (entry.second.track.shape
                && (entry.second.track.shape->mVertexList == model->mVertexList
                    || entry.second.track.shape->mNormalList == model->mNormalList))
            return false;
    }
    BlendState state;
    state.track.shape = model;
    state.track.size(base);
    blends.emplace(actor, std::move(state));
    unsigned generator = 0;
    if (actor && actor->mGenerator) generator = actor->mGenerator->_70;
    const p2motion::Tunables& tune = p2motion::tunables();
    std::printf("P2_BATCH3_INTERPOLATION_READY key=%s generator=%u positions=%d normals=%d private_geometry=1 "
                "lerp=%d crossfade_ms=%d gameplay_clock=P1\n",
                key.c_str(), generator, model->mVertexCount, model->mNormalCount, int(interpolation),
                int(tune.crossfadeSeconds * 1000.f + .5f));
    return true;
}
}

void pc_p2_batch3_reset() {
    banks.clear();
    actors.clear();
    blends.clear();
    gates.clear();
    drawnKeys.clear();
    wormDrawn.clear();
    wormCorpseDrawn.clear();
    interpolation = false;
    bytesTotal = 0;
    logged[0] = logged[1] = false;
}

void pc_p2_batch3_forget(BTeki* actor) {
    actors.erase(actor);
    blends.erase(actor);
    gates.erase(actor);
    wormDrawn.erase(actor);
    wormCorpseDrawn.erase(actor);
}

void pc_p2_batch3_update(BTeki* actor, float seconds) {
    if (!actor) return;
    auto boundKey = actors.find(actor);
    if (boundKey == actors.end()) return;
    pc_p2_body_coll_assign(actor, boundKey->second);
    const p2motion::Tunables& tune = p2motion::tunables();
    const float speed = actor->mVelocity.x * actor->mVelocity.x + actor->mVelocity.z * actor->mVelocity.z;
    gates[actor].update(speed, seconds, tune);
    auto blendIt = blends.find(actor);
    if (blendIt != blends.end()) blendIt->second.track.advance(seconds);
}

bool pc_p2_batch3_corpse_drawn() { return logged[1]; }
int pc_p2_batch3_actor_count() { return int(actors.size()); }
int pc_p2_batch3_bank_count() { return int(banks.size()); }

static void campaignWantedSnagret(std::map<unsigned, std::string>& wanted) {
    // Campaign-identity snagret species bound in bridge mode (#871 inst-bugs):
    // Segmented Crawbster (DangoMushi, 94). Mirrors pc_p2_batch2.cpp
    // campaignWanted SOURCES; other snagrets stay proxy-only.
    wanted.clear();
    for (unsigned id : pc_p2_campaign_ids(94)) wanted[id] = "DangoMushi";
}

// Bridge-mode campaign binding for the identity snagret species (DangoMushi,
// 94). Batch-3 is otherwise a room-preview-only visual path; this binds the
// staged p2-snagret-actors/bank sidecars in a live campaign so the P2 corpse
// model draws and the delivery bind can mint onion:p2:94. Soft: missing
// sidecars or no bound ids are a no-op; mismatches skip with a log line,
// never abort (campaign actors span areas/days).
void pc_p2_batch3_setup_bridge() {
    if (!tekiMgr) return;
    std::map<unsigned, std::string> fileActors;
    if (!parseActors("p2-snagret-actors.txt", fileActors)) return;
    std::map<unsigned, std::string> wanted;
    campaignWantedSnagret(wanted);
    if (wanted.empty()) return;
    std::map<std::string, std::vector<ClipRow>> rows;
    {
        std::ifstream probe("p2-snagret-bank.txt");
        if (!probe) {
            std::printf("P2_SETUP_SKIP batch3 snagret missing_bank\n");
            return;
        }
    }
    if (!parseBank("p2-snagret-bank.txt", rows)) {
        std::printf("P2_SETUP_SKIP batch3 snagret bad_bank\n");
        return;
    }
    std::set<unsigned> found;
    std::set<std::string> speciesUsed;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        Teki* teki = static_cast<Teki*>(*it);
        if (!teki || !teki->mGenerator) continue;
        const unsigned token = pc_p2_campaign_token(teki);
        auto match = wanted.find(token);
        if (match == wanted.end()) continue;
        // Campaign vehicle for the identity Crawbster is TEKI_Swallow (proxy
        // row host_teki 4); the room-preview arena keeps the Chappy vehicle,
        // so expectedType (preview) is not reused here.
        if (teki->mTekiType != TEKI_Swallow) {
            std::printf("P2_SETUP_SKIP batch3 snagret native_type_mismatch generator=%u\n", token);
            continue;
        }
        if (!found.insert(token).second) {
            std::printf("P2_SETUP_SKIP batch3 snagret duplicate generator=%u\n", token);
            continue;
        }
        actors[teki] = std::string("snagret|") + match->second;
        speciesUsed.insert(match->second);
    }
    if (found.size() != wanted.size()) {
        std::printf("P2_BATCH3_MISSING family=snagret found=%zu wanted=%zu\n",
                    found.size(), wanted.size());
    }
    for (const std::string& species : speciesUsed) {
        auto clipRows = rows.find(species);
        if (clipRows == rows.end() || clipRows->second.empty()) {
            std::printf("P2_SETUP_SKIP batch3 snagret no_bank_clips species=%s\n", species.c_str());
            continue;
        }
        const std::string key = std::string("snagret|") + species;
        if (!banks.count(key)) banks[key] = loadBank({"snagret", "snake",
                                                      "p2-snagret-actors.txt", "p2-snagret-bank.txt"},
                                                     species, clipRows->second);
    }
    for (const auto& entry : actors)
        if (entry.second == "snagret|DangoMushi")
            std::printf("P2_BATCH3_BIND generator=%u key=%s visual_only=0 native_fsm=implemented token=%u\n",
                        entry.first->mGenerator ? entry.first->mGenerator->_70 : 0, entry.second.c_str(),
                        pc_p2_campaign_token(entry.first));
    std::printf("P2_BATCH3_BANK total_mod_bytes=%zu species=%zu\n", bytesTotal, banks.size());
}

// Worms lane (#871) round 2 bridge visuals: the snagret pair (34/70) and the
// bloyster pair (71/101) draw their P2 pose banks in campaign (bridge) mode.
// Narrow and additive: builds wanted strictly from live campaign sources for
// these four species, binds only TEKI_Chappy placement vehicles, loads only
// their banks (Blind reuses the UmiMushi bank as in preview), and is a no-op
// for campaigns without worms. All other species and the preview path are
// untouched.
static void setupBridgeWorms() {
    struct WormRow {
        const char* family;
        const char* species;
        unsigned source;
        const char* bankSpecies;
    };
    static const WormRow ROWS[] = {
        {"snagret", "SnakeCrow", 34, "SnakeCrow"},
        {"snagret", "SnakeWhole", 70, "SnakeWhole"},
        {"aquatic", "UmiMushi", 71, "UmiMushi"},
        {"aquatic", "UmiMushiBlind", 101, "UmiMushi"},
    };
    std::map<unsigned, std::pair<std::string, std::string>> wanted; // token -> (key, bankSpecies)
    std::map<std::string, std::string> bankSpeciesFor;              // key -> bankSpecies
    for (const auto& row : ROWS) {
        for (unsigned id : pc_p2_campaign_ids(row.source)) {
            const std::string key = std::string(row.family) + "|" + row.species;
            wanted[id] = {key, row.bankSpecies};
            bankSpeciesFor[key] = row.bankSpecies;
        }
    }
    if (wanted.empty()) return;
    std::map<std::string, std::map<std::string, std::vector<ClipRow>>> rowsByFamily;
    for (const FamilyDef& family : FAMILIES) {
        std::map<std::string, std::vector<ClipRow>> rows;
        if (parseBank(family.bank, rows)) rowsByFamily[family.name] = std::move(rows);
    }
    std::set<unsigned> found;
    std::set<std::string> speciesUsed;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        Teki* teki = static_cast<Teki*>(*it);
        if (!teki || !teki->mGenerator) continue;
        const unsigned token = pc_p2_campaign_token(teki);
        auto match = wanted.find(token);
        if (match == wanted.end()) continue;
        if (teki->mTekiType != TEKI_Chappy) {
            std::printf("P2_SETUP_SKIP batch3 %s native_type_mismatch generator=%u\n",
                        match->second.first.c_str(), token);
            std::fflush(stdout);
            continue;
        }
        actors[teki] = match->second.first;
        speciesUsed.insert(match->second.first);
        found.insert(token);
    }
    if (found.size() != wanted.size()) {
        std::printf("P2_BATCH3_MISSING_BRIDGE found=%zu wanted=%zu\n", found.size(), wanted.size());
        std::fflush(stdout);
    }
    if (found.empty()) return;
    for (const std::string& key : speciesUsed) {
        const size_t bar = key.find('|');
        const std::string family = key.substr(0, bar);
        const std::string bankSpecies = bankSpeciesFor[key];
        auto famRows = rowsByFamily.find(family);
        if (famRows == rowsByFamily.end()) {
            std::printf("P2_SETUP_SKIP batch3 bridge missing_bank family=%s key=%s\n",
                        family.c_str(), key.c_str());
            std::fflush(stdout);
            for (auto ai = actors.begin(); ai != actors.end();) {
                if (ai->second == key) ai = actors.erase(ai);
                else ++ai;
            }
            continue;
        }
        auto clipRows = famRows->second.find(bankSpecies);
        if (clipRows == famRows->second.end() || clipRows->second.empty()) {
            std::printf("P2_SETUP_SKIP batch3 bridge no_bank_clips key=%s\n", key.c_str());
            std::fflush(stdout);
            for (auto ai = actors.begin(); ai != actors.end();) {
                if (ai->second == key) ai = actors.erase(ai);
                else ++ai;
            }
            continue;
        }
        const FamilyDef* famDef = nullptr;
        for (const FamilyDef& f : FAMILIES)
            if (family == f.name) { famDef = &f; break; }
        if (!famDef) continue;
        // Bridge-safe pose pre-check: loadBank fail()s on a missing pose,
        // which must degrade to a visual skip in campaign, never an abort.
        // Probe every staged pose file the bank rows reference first.
        bool posesReady = true;
        for (const ClipRow& row : clipRows->second) {
            for (int i = 0; i < row.poseCount; ++i) {
                char rel[192];
                std::snprintf(rel, sizeof(rel),
                              "assets/dataDir/courses/pikmin2room/%s_%s_%s_%02d.mod",
                              famDef->prefix, bankSpecies.c_str(), row.name.c_str(), i);
                std::ifstream probe(rel, std::ios::binary);
                if (!probe) { posesReady = false; break; }
            }
            if (!posesReady) break;
        }
        if (!posesReady) {
            std::printf("P2_SETUP_SKIP batch3 bridge missing_pose key=%s\n", key.c_str());
            std::fflush(stdout);
            for (auto ai = actors.begin(); ai != actors.end();) {
                if (ai->second == key) ai = actors.erase(ai);
                else ++ai;
            }
            continue;
        }
        banks[key] = loadBank(*famDef, bankSpecies, clipRows->second);
    }
    if (actors.empty()) return;
    for (const auto& entry : actors) {
        std::printf("P2_BATCH3_BIND generator=%u key=%s visual_only=0 native_fsm=implemented token=%u\n",
                    entry.first->mGenerator ? entry.first->mGenerator->_70 : 0u,
                    entry.second.c_str(), pc_p2_campaign_token(entry.first));
    }
    std::printf("P2_BATCH3_BANK total_mod_bytes=%zu species=%zu\n", bytesTotal, banks.size());
    std::fflush(stdout);
    for (const auto& entry : actors) ensureBlendState(entry.first, entry.second);
}

void pc_p2_batch3_setup() {
    for(const auto& actor:actors) if([&](){unsigned source=0,token=0;return p2original::originalActors().query(static_cast<Creature*>(actor.first),source,token);}()) return;
    pc_p2_batch3_reset();
    interpolation = readBatch3InterpolationFlag();
    if (interpolation) std::printf("P2_BATCH3_INTERPOLATION_READY interpolation=1 gameplay_clock=P1\n");
    if (!tekiMgr) return;
    const bool bridge = pc_randomizer_p2_bridge() && !pc_pikipelago_room_preview();
    const bool preview = pc_pikipelago_room_preview();
    // Bridge mode: bind every lane's visuals. setup_bridge covers the
    // snagret Crawbster (94); setupBridgeWorms covers the worms snagret pair
    // (34/70) + bloyster pair (71/101); the aquatic family loop below covers
    // Catfish/Tadpole/Jigumo/UmiMushi (26/27/63/71).
    if (bridge) pc_p2_batch3_setup_bridge();
    if (bridge) setupBridgeWorms();
    if (!preview && !bridge) return;
    for (const FamilyDef& family : FAMILIES) {
        const bool isAquatic = std::string(family.name) == "aquatic";
        // Bridge support is aquatic-only (inst-legs lane #871: Jigumo 63 and
        // its three family siblings). Flying/snagret stay preview-only.
        if (bridge && !isAquatic) continue;
        std::map<unsigned, std::string> wanted;
        const bool haveActors = parseActors(family.actors, wanted);
        if (bridge) {
            // Seed-bridge identity overrides the sidecar placeholders (like
            // batch2 campaignWanted). The sidecar must still stage the bank;
            // actors without bank poses degrade below instead of aborting.
            wanted.clear();
            if (isAquatic) {
                for (unsigned id : pc_p2_campaign_ids(26)) wanted[id] = "Catfish";
                for (unsigned id : pc_p2_campaign_ids(27)) wanted[id] = "Tadpole";
                for (unsigned id : pc_p2_campaign_ids(63)) wanted[id] = "Jigumo";
                for (unsigned id : pc_p2_campaign_ids(71)) wanted[id] = "UmiMushi";
            }
            if (wanted.empty()) continue;
        } else {
            if (!haveActors) continue;
        }
        std::map<std::string, std::vector<ClipRow>> rows;
        if (bridge) {
            if (!parseBank(family.bank, rows)) {
                std::printf("P2_SETUP_SKIP batch3 %s missing_bank\n", family.name);
                continue;
            }
        } else {
            if (!parseBank(family.bank, rows)) fail("missing bank for present actor config");
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
                if (bridge) {
                    std::printf("P2_SETUP_SKIP batch3 %s native_type_mismatch generator=%u\n",
                                family.name, generator);
                    continue;
                }
                fail("native type mismatch");
            }
            if (!found.insert(generator).second) {
                // Water slots are Wogpole/Dumple PACK generators: one campaign
                // token, several live hosts. The behaviour modules bind every
                // member; skipping the extra members here left them drawing as
                // the P1 host model (wave 3 mechanics probe, Catfish/Tadpole
                // b26/b27). In bridge mode every member is bound and the token
                // counts once; found.size() below still compares tokens.
                if (!bridge) fail("duplicate generator in scene");
            }
            actors[teki] = std::string(family.name) + "|" + match->second;
            speciesUsed.insert(match->second);
        }
        if (found.size() != wanted.size()) {
            if (bridge) {
                std::printf("P2_BATCH3_MISSING family=%s found=%zu wanted=%zu\n",
                            family.name, found.size(), wanted.size());
                if (found.empty()) {
                    for (auto ait = actors.begin(); ait != actors.end();) {
                        if (ait->second.compare(0, 8, "aquatic|") == 0) ait = actors.erase(ait);
                        else ++ait;
                    }
                    continue;
                }
            } else fail("arena actor not present in scene");
        }
        for (const std::string& species : speciesUsed) {
            // Blind UmiMushi (101) has no converted visual bank of its own; the
            // source import manifest only ships the ordinary UmiMushi (71)
            // poses. Reuse that bank explicitly as a stand-in so the actor is
            // observable (draw override keyed aquatic|UmiMushiBlind), never as
            // fabricated Blind provenance.
            const std::string bankSpecies =
                (std::string(family.name) == "aquatic" && species == "UmiMushiBlind")
                    ? "UmiMushi" : species;
            auto clipRows = rows.find(bankSpecies);
            if (clipRows == rows.end() || clipRows->second.empty()) {
                if (bridge) {
                    std::printf("P2_SETUP_SKIP batch3 %s no_bank_clips species=%s\n",
                                family.name, species.c_str());
                    for (auto ait = actors.begin(); ait != actors.end();) {
                        if (ait->second == std::string(family.name) + "|" + species)
                            ait = actors.erase(ait);
                        else ++ait;
                    }
                    continue;
                }
                fail("species has no bank clips");
            }
            if (bridge) {
                // Probe pose availability so a missing bank degrades instead of
                // fail() aborting the campaign mid-setup (mirrors batch2 soft).
                bool posesOk = true;
                for (const auto& row : clipRows->second) {
                    for (int i = 0; i < row.poseCount; ++i) {
                        char rel[192];
                        std::snprintf(rel, sizeof(rel),
                                      "assets/dataDir/courses/pikmin2room/%s_%s_%s_%02d.mod",
                                      family.prefix, bankSpecies.c_str(),
                                      row.name.c_str(), i);
                        std::ifstream probe(rel, std::ios::binary);
                        if (!probe) { posesOk = false; break; }
                    }
                    if (!posesOk) break;
                }
                if (!posesOk) {
                    std::printf("P2_SETUP_SKIP batch3 %s missing_pose species=%s\n",
                                family.name, species.c_str());
                    for (auto ait = actors.begin(); ait != actors.end();) {
                        if (ait->second == std::string(family.name) + "|" + species)
                            ait = actors.erase(ait);
                        else ++ait;
                    }
                    continue;
                }
            }
            banks[std::string(family.name) + "|" + species] =
                loadBank(family, bankSpecies, clipRows->second);
        }
    }
    for (const auto& entry : actors) ensureBlendState(entry.first, entry.second);
    for (const auto& entry : actors) {
        const unsigned gen = (bridge && entry.first && entry.first->mGenerator)
            ? pc_p2_campaign_token(entry.first)
            : (entry.first->mGenerator ? entry.first->mGenerator->_70 : 0);
        if (entry.second == "aquatic|Tadpole" || entry.second == "flying|Mar" || entry.second == "aquatic|UmiMushi" || entry.second == "aquatic|UmiMushiBlind" || entry.second == "aquatic|Jigumo" || entry.second == "snagret|SnakeCrow" || entry.second == "snagret|SnakeWhole" || entry.second == "snagret|DangoMushi" || entry.second == "flying|Hanachirashi" || entry.second == "aquatic|Catfish")
            std::printf("P2_BATCH3_BIND generator=%u key=%s visual_only=0 native_fsm=implemented token=%u\n",
                        gen, entry.second.c_str(), gen);
        else
            std::printf("P2_BATCH3_BIND generator=%u key=%s visual_only=1 native_fsm=unimplemented token=%u\n",
                        gen, entry.second.c_str(), gen);
    }
    std::printf("P2_BATCH3_BANK total_mod_bytes=%zu species=%zu\n", bytesTotal, banks.size());
}

bool pc_p2_batch3_draw(BTeki* actor, Graphics& gfx, const Matrix4f& matrix, bool corpse) {
    auto entry = actors.find(actor);
    if (entry == actors.end() || !gfx.mCamera || !actor->mTekiAnimator) return false;
    auto bankIt = banks.find(entry->second);
    if (bankIt == banks.end()) return false;
    const Bank& bank = bankIt->second;
    // Buried snagret (StateStay sets EB_ModelHidden): draw nothing.
    if (!corpse && pc_p2_snakejoint_model_hidden(actor)) return true;
    static const char* const deadClips[] = {"dead", "dead1", "pdead1", "kagebozu_dead"};
    static const char* const attackClips[] = {"attack1", "attack", "attack2", "attack_2",
                                              "sattack1", "hit", "hit_near", "hit_far", "charge",
                                              "hit_start", "kagebozu_flick", "kagebozu_flick2"};
    static const char* const moveClips[] = {"move1", "move", "move2", "run1", "walk", "walk1",
                                            "wrun1", "tyre_move", "kagebozu_move", "kagebozu_walk", "kagebozu_run"};
    static const char* const waitClips[] = {"wait1", "wait", "wait2", "kagebozu_wait", "kagebozu_wait2"};
    const int motion = actor->mTekiAnimator->getCurrentMotionIndex();
    const char* name = nullptr;
    float forcedPhase = -1.0f;
    // Family-owned source behavior: a registered Tadpole forces the exact source
    // clip/phase for its FSM state instead of the generic P1-velocity pick.
    if (!corpse) {
        const char* forced = nullptr;
        float phase = 0.0f;
        if ((pc_p2_tadpole_clip(actor, forced, phase) || pc_p2_mar_clip(actor, forced, phase) || pc_p2_umimushi_clip(actor, forced, phase) || pc_p2_jigumo_clip(actor, forced, phase) || pc_p2_snakejoint_clip(actor, forced, phase) || pc_p2_dangomushi_clip(actor, forced, phase) || pc_p2_hanachirashi_clip(actor, forced, phase) || pc_p2_catfish_clip(actor, forced, phase)) && bank.clips.count(forced)) {
            name = forced;
            forcedPhase = phase;
        }
    }
    if (corpse) {
        name = firstClip(bank, deadClips, int(sizeof(deadClips) / sizeof(deadClips[0])));
    } else if (!name && (motion == TekiMotion::Damage || motion >= TekiMotion::Type1)) {
        name = firstClip(bank, attackClips, int(sizeof(attackClips) / sizeof(attackClips[0])));
    }
    if (!name) {
        // Move/wait with hysteresis + dwell (#895), advanced in pc_p2_batch3_update.
        const f32 speed = actor->mVelocity.x * actor->mVelocity.x + actor->mVelocity.z * actor->mVelocity.z;
        auto gate = gates.find(actor);
        const bool moving = gate != gates.end() ? gate->second.moving() : speed > p2motion::tunables().moveEnter;
        name = moving
            ? firstClip(bank, moveClips, int(sizeof(moveClips) / sizeof(moveClips[0])))
            : firstClip(bank, waitClips, int(sizeof(waitClips) / sizeof(waitClips[0])));
    }
    if (!name) name = firstClip(bank, waitClips, int(sizeof(waitClips) / sizeof(waitClips[0])));
    if (!name) return false;
    if (corpse && entry->second == "snagret|DangoMushi") {
        // #897 carry check: the corpse draw matrix must follow the pellet.
        static unsigned corpseDraws = 0;
        if (corpseDraws++ % 60u == 0u) {
            // matrix is the pellet's model-view matrix (its translation is
            // camera-relative); the pellet's own world position is beside it.
            const Vector3f at = actor->mPellet ? actor->mPellet->mSRT.t : Vector3f(0.0f, 0.0f, 0.0f);
            std::printf("P2_DANGOMUSHI_CORPSE_DRAW draws=%u pellet=%d px=%.2f py=%.2f pz=%.2f "
                        "view_z=%.2f\n", corpseDraws, int(actor->mPellet != nullptr), at.x, at.y, at.z,
                        matrix.mMtx[2][3]);
        }
    }
    const auto& poses = bank.clips.at(name);
    if (poses.empty()) return false;
    const int frames = actor->mTekiAnimator->getFrameCount();
    const float phase = forcedPhase >= 0.0f ? forcedPhase
        : (frames > 1 ? actor->mTekiAnimator->getCounter() / (frames - 1) : 0.f);
    const p2animation::Clip& timing = bank.timing.at(name);
    // Death clips stop at their last visible pose (#895, p2motion::isDeathClip).
    auto holdIt = bank.hold.find(name);
    const size_t holdIndex = holdIt != bank.hold.end() && holdIt->second < poses.size() ? holdIt->second : poses.size() - 1;
    size_t index = timing.index(phase, corpse);
    if ((corpse || p2motion::isDeathClip(name)) && index > holdIndex) index = holdIndex;
    Shape* shape = poses.at(index < poses.size() ? index : poses.size() - 1);
    // Decoded pose vectors drive the draw (#895); see pc_p2_batch2.cpp.
    auto bakedIt = bank.baked.find(name);
    if (bakedIt != bank.baked.end() && bakedIt->second.size() == poses.size()) {
        std::vector<int> frames = timing.frames;
        if (frames.empty()) frames = uniformFramesFor(int(poses.size()), timing.duration);
        if (!blends.count(actor)) ensureBlendState(actor, entry->second);
        auto blendIt = blends.find(actor);
        if (blendIt != blends.end() && blendIt->second.track.shape) {
            p2motion::Tunables tune = p2motion::tunables();
            auto interpIt = bank.interp.find(name);
            tune.lerp = interpIt != bank.interp.end() && interpIt->second;
            const float clampedPhase =
                phase != phase ? 0.0f : (phase < 0.0f ? 0.0f : (phase > 1.0f ? 1.0f : phase));
            float drawFrame = corpse ? float(timing.duration - 1)
                                     : clampedPhase * float(timing.duration - 1);
            if ((corpse || p2motion::isDeathClip(name)) && holdIndex < frames.size()
                    && drawFrame > float(frames[holdIndex]))
                drawFrame = float(frames[holdIndex]);
            const auto& bakedVec = bakedIt->second;
            auto seamIt = bank.seam.find(name);
            const bool seamOk = seamIt == bank.seam.end() || seamIt->second;
            const p2pose::Presented shown = p2pose::present(
                blendIt->second.track, name, bakedVec.size(),
                [&bakedVec](size_t i) -> const p2pose::Pose& { return bakedVec[i].pose; }, frames, drawFrame, tune,
                seamOk);
            if (shown.ok) {
                shape = blendIt->second.track.shape;
                static unsigned crossfadeLogs = 0;
                if ((shown.crossfadeStarted || shown.wrapBlend) && crossfadeLogs < 64u) {
                    ++crossfadeLogs;
                    std::printf("P2_BATCH3_CROSSFADE key=%s clip=%s ms=%d cause=%s\n", entry->second.c_str(), name,
                                int(tune.crossfadeSeconds * 1000.f + .5f), shown.wrapBlend ? "loop_seam" : "clip_change");
                }
                if (blendIt->second.corpse != corpse
                        || drawnKeys.insert(std::string("blend|") + entry->second + "|" + name).second) {
                    std::printf("P2_BATCH3_BLEND key=%s clip=%s corpse=%d source_frame=%.5f left=%zu "
                                "right=%zu weight=%.5f poses=%zu lerp=%d\n",
                                entry->second.c_str(), name, int(corpse), double(drawFrame), shown.span.left,
                                shown.span.right, shown.span.weight, bakedVec.size(), int(tune.lerp));
                }
                blendIt->second.corpse = corpse;
            }
        }
    }
    if (!logged[corpse ? 1 : 0]) {
        std::printf("P2_BATCH3_DRAW corpse=%d key=%s clip=%s\n", int(corpse), entry->second.c_str(), name);
        logged[corpse ? 1 : 0] = true;
    }
    // Per-key draw evidence for campaign-identity species (mirrors the
    // batch-2 identity per-key lines): one line per key+corpse+token so the
    // bot-campaign scorer cites the species' own draw, not the run-global
    // first-draw race above.
    {
        // generator= carries the campaign token (pack members share it), so
        // the bot-campaign scorer attributes the draw to the bound slot.
        unsigned drawToken = pc_p2_campaign_token(actor);
        if (!drawToken && actor->mGenerator) drawToken = actor->mGenerator->_70;
        if (drawnKeys.insert(std::string(corpse ? "1|" : "0|") + entry->second + "|" + std::to_string(drawToken)).second) {
            std::printf("P2_BATCH3_DRAW corpse=%d key=%s clip=%s generator=%u token=%u\n", int(corpse), entry->second.c_str(), name, drawToken, drawToken);
            std::fflush(stdout);
        }
    }
    // Worms lane (#871) round 2: per-actor campaign DRAW markers for the
    // evidence scorer (drawn = P2 model actually rendered for this token).
    // Once per actor (corpse separately); no-op for all other keys.
    {
        const std::string& key = entry->second;
        const bool isSnagret = (key == "snagret|SnakeCrow" || key == "snagret|SnakeWhole");
        const bool isBloyster =
            (key == "aquatic|UmiMushi" || key == "aquatic|UmiMushiBlind");
        if (isSnagret || isBloyster) {
            const unsigned tok = pc_p2_campaign_token(actor);
            const char* mod = isSnagret ? "SNAKEJOINT" : "UMIMUSHI";
            if (!corpse && wormDrawn.insert(actor).second) {
                std::printf("P2_%s_DRAW generator=%u key=%s clip=%s\n", mod, tok,
                            key.c_str(), name);
                std::fflush(stdout);
            } else if (corpse && wormCorpseDrawn.insert(actor).second) {
                std::printf("P2_%s_CORPSE_DRAW generator=%u key=%s clip=%s\n", mod, tok,
                            key.c_str(), name);
                std::fflush(stdout);
            }
        }
    }
    shape->updateAnim(gfx, matrix, nullptr, actor);
    shape->drawshape(gfx, *gfx.mCamera, nullptr);
    return true;
}

namespace {
bool originalProfile(unsigned source,const FamilyDef*& family,const char*& species) {
    const char* name=nullptr;
    switch(source) {case 26:name="aquatic";species="Catfish";break;case 34:name="snagret";species="SnakeCrow";break;case 55:name="flying";species="Hanachirashi";break;default:return false;}
    for(const auto& f:FAMILIES)if(std::string(f.name)==name){family=&f;return true;}
    return false;
}
}
bool pc_p2_batch3_original_resources(unsigned source,std::string& error) {
    error.clear();
    const FamilyDef* family=nullptr;const char* species=nullptr;
    if(!gsys||!originalProfile(source,family,species)){error="original batch3 concrete profile unavailable";return false;}
    const std::string key=std::string(family->name)+"|"+species;
    if(banks.count(key)){error.clear();return true;}
    std::map<std::string,std::vector<ClipRow>> table;
    if(!parseBank(family->bank,table,&error)){if(error.empty())error="original batch3 bank missing";return false;}
    auto found=table.find(species);
    if(found==table.end()||found->second.empty()){error="original batch3 species clips missing";return false;}
    std::set<std::string> names;
    for(const auto& row:found->second){
        if(row.sourceFrames<2||row.poseCount<1||row.framesMalformed||!names.insert(row.name).second){error="original batch3 malformed or undrawable authored clip";return false;}
    }
    interpolation=readBatch3InterpolationFlag();
    const int heap=gsys->setHeap(SYSHEAP_App);
    Bank staged=loadBank(*family,species,found->second,&error);
    gsys->setHeap(heap);
    if(!error.empty())return false;
    if(staged.baked.size()!=found->second.size()){error="original batch3 requires deformable source geometry";return false;}
    banks.emplace(key,std::move(staged));error.clear();return true;
}
bool pc_p2_batch3_original_birth(BTeki* actor,unsigned source,std::string& error) {
    const FamilyDef* family=nullptr;const char* species=nullptr;
    if(!actor||!originalProfile(source,family,species)||static_cast<Teki*>(actor)->mTekiType!=expectedType(family->name,species)||actors.count(actor)){error="original batch3 unique chassis profile mismatch";return false;}
    const std::string key=std::string(family->name)+"|"+species;
    if(!banks.count(key)){error="original batch3 birth without prepared bank";return false;}
    actors.emplace(actor,key);
    if(!ensureBlendState(actor,key)){pc_p2_batch3_forget(actor);error="original batch3 private geometry allocation failed";return false;}
    pc_p2_body_coll_assign(actor,key);error.clear();return true;
}
