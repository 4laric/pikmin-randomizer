// Game-linked P2 challenge stage content-loading boot path (#694).
//
// Thin binder, not a loader: it validates the stage-content sidecar, runs the
// integrated cave-generator consumer (#129) over the caller-staged
// p2-cave-generate.txt manifest, verifies staged spawn intents cover the
// stage roster, and exposes read-only liveness probes. It never provisions
// arenas, births actors, writes saves, or touches the economy; species
// behavior belongs downstream (#533/#561/#562). No other lane module is
// modified; every function fails closed on malformed/missing input.
#include "pc_p2_challenge_content_loading.h"
#include "pc_p2_cave_generate.h"
#include "teki.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Generator.h"
#include <cmath>
#include <cstdio>
#include <fstream>
#include <map>

namespace p2_challenge_content {
namespace {

bool nameOk(const std::string& s) {
    if (s.empty() || s.size() > 128) return false;
    for (size_t i = 0; i < s.size(); ++i) {
        char c = s[i];
        bool ok = (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
                  (c >= '0' && c <= '9') || c == '_' || c == '-' || c == '.' ||
                  (c == '$' && i == 0);
        if (!ok) return false;
    }
    return true;
}

bool refuse(const char* reason) {
    std::printf("P2_CHALLENGE_CONTENT_REFUSED reason=%s\n", reason);
    std::fflush(stdout);
    return false;
}

Expectation g_selected;
bool g_hasSelection = false;

} // namespace

void reset() {
    g_selected = Expectation();
    g_hasSelection = false;
}

bool select(const char* sidecarPath, Expectation& out) {
    out = Expectation();
    if (!sidecarPath || !sidecarPath[0]) return refuse("missing-sidecar-path");
    std::ifstream in(sidecarPath);
    if (!in) return refuse("missing-sidecar");
    std::string word;
    if (!(in >> word) || word != "P2_CHALLENGE_CONTENT_1") return refuse("bad-header");
    Expectation e;
    if (!(in >> word) || word != "stage") return refuse("bad-stage");
    int floor = 0;
    if (!(in >> e.caveId >> floor)) return refuse("bad-stage-fields");
    if (!nameOk(e.caveId) || floor < 1 || floor > 64) return refuse("bad-stage-values");
    e.floor = floor;
    if (!(in >> word) || word != "pool") return refuse("bad-pool");
    if (!(in >> e.pool) || !nameOk(e.pool)) return refuse("bad-pool-name");
    while (in >> word) {
        if (word == "anchor") break;
        if (word != "spawn") return refuse("bad-spawn");
        RosterSpawn s;
        if (!(in >> s.id >> s.count)) return refuse("bad-spawn-fields");
        if (!nameOk(s.id) || s.count < 1 || s.count > 10000) return refuse("bad-spawn-values");
        e.roster.push_back(s);
        if (e.roster.size() > 256) return refuse("too-many-spawns");
    }
    if (word != "anchor") return refuse("missing-anchor");
    if (!(in >> e.anchor)) return refuse("bad-anchor");
    if (e.anchor != "hole" && e.anchor != "geyser") return refuse("bad-anchor-kind");
    if (e.roster.empty()) return refuse("empty-roster");
    std::string trailing;
    if (in >> trailing) return refuse("trailing-bytes");
    e.valid = true;
    out = e;
    g_selected = e;
    g_hasSelection = true;
    std::printf("P2_CHALLENGE_CONTENT_SELECTED cave=%s floor=%d pool=%s spawns=%d anchor=%s\n",
                e.caveId.c_str(), e.floor, e.pool.c_str(),
                int(e.roster.size()), e.anchor.c_str());
    std::fflush(stdout);
    return true;
}

bool verifyCoverage(const Expectation& expect) {
    if (!expect.valid) return refuse("no-selection");
    // Minimal spawn-line scan of the staged generator manifest (coverage only;
    // geometry validation stays with the generator, not forked here).
    std::ifstream in("p2-cave-generate.txt");
    if (!in) return refuse("missing-generate-manifest");
    std::map<std::string, int> staged;
    std::string word;
    while (in >> word) {
        if (word != "spawn") {
            std::string rest;
            std::getline(in, rest);
            if (!in && !in.eof()) return refuse("bad-manifest-scan");
            continue;
        }
        std::string id; int count = 0;
        if (!(in >> id >> count)) return refuse("bad-manifest-spawn");
        staged[id] += count;
    }
    for (size_t i = 0; i < expect.roster.size(); ++i) {
        const RosterSpawn& want = expect.roster[i];
        auto it = staged.find(want.id);
        if (it == staged.end() || it->second < want.count) {
            std::printf("P2_CHALLENGE_CONTENT_SPAWN_GAP id=%s want=%d staged=%d\n",
                        want.id.c_str(), want.count,
                        it == staged.end() ? 0 : it->second);
            std::fflush(stdout);
            return refuse("roster-not-covered");
        }
        std::printf("P2_CHALLENGE_CONTENT_SPAWN_COVERED id=%s count=%d\n",
                    want.id.c_str(), want.count);
        std::fflush(stdout);
    }
    return true;
}

int liveSquad() {
    int count = 0;
    if (!pikiMgr) return 0;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (p && p->isAlive()) ++count;
    }
    return count;
}

int liveActors() {
    int count = 0;
    if (!tekiMgr) return 0;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        Teki* a = static_cast<Teki*>(*it);
        if (a && a->isAlive()) ++count;
    }
    return count;
}

bool positionsFinite() {
    if (tekiMgr) {
        Iterator it(tekiMgr);
        CI_LOOP(it) {
            Teki* a = static_cast<Teki*>(*it);
            if (!a) continue;
            const Vector3f pos = a->getPosition();
            if (!std::isfinite(pos.x) || !std::isfinite(pos.y) || !std::isfinite(pos.z))
                return false;
            if (std::fabs(pos.x) > 100000.f || std::fabs(pos.y) > 100000.f || std::fabs(pos.z) > 100000.f)
                return false;
        }
    }
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (!p || !p->isAlive()) continue;
            const Vector3f pos = p->getPosition();
            if (!std::isfinite(pos.x) || !std::isfinite(pos.y) || !std::isfinite(pos.z))
                return false;
        }
    }
    return true;
}

} // namespace p2_challenge_content