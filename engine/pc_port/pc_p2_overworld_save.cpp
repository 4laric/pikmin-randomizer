// Overworld session save serializer (#736).
//
// Real engine save/load for an overworld session record with deterministic
// output and strict, size-guarded, fail-closed parsing, per the #712
// round-trip and size-guard rules. Squad census is counted live from pikiMgr;
// area/day/highscore/unlock come only from explicit fixture context. No
// invented values, no state mutation beyond the module's own observation
// flags, no save-format claims beyond this file's documented grammar.
#include "pc_p2_overworld_save.h"
#include "Creature.h"
#include "Node.h"
#include "Piki.h"
#include "PikiMgr.h"
#include <cmath>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>

namespace p2overworldsave {
namespace {

const char* kHeader = "P2_OVERWORLD_SAVE_1";
const size_t kDefaultMaxBytes = 4096;

char sArea[64] = {0};
bool sHasContext = false;
int sDay = 0;
int sHighscore = 0;
int sUnlocked = 0;

bool sSupported = false;
char sLastPath[260] = {0};
bool sPollDone = false;

bool validAreaToken(const char* area) {
    if (area == nullptr || area[0] == '\0') return false;
    size_t len = std::strlen(area);
    if (len > 63) return false;
    for (size_t i = 0; i < len; ++i) {
        const char c = area[i];
        const bool ok = (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z')
            || (c >= '0' && c <= '9') || c == '_';
        if (!ok) return false;
    }
    return true;
}

bool parseInt(const std::string& tok, int& out, int lo, int hi) {
    if (tok.empty() || tok.size() > 11) return false;
    size_t i = 0;
    bool neg = false;
    if (tok[0] == '-') {
        neg = true;
        i = 1;
        if (tok.size() == 1) return false;
    }
    long v = 0;
    for (; i < tok.size(); ++i) {
        if (tok[i] < '0' || tok[i] > '9') return false;
        v = v * 10 + (tok[i] - '0');
        if (v > 1000000000L) return false;
    }
    if (neg) v = -v;
    if (v < lo || v > hi) return false;
    out = static_cast<int>(v);
    return true;
}

std::vector<std::string> splitWords(const std::string& line) {
    std::vector<std::string> out;
    std::string cur;
    for (size_t i = 0; i <= line.size(); ++i) {
        const char c = (i < line.size()) ? line[i] : ' ';
        if (c == ' ' || c == '\t' || c == '\r') {
            if (!cur.empty()) {
                out.push_back(cur);
                cur.clear();
            }
        } else {
            cur.push_back(c);
        }
    }
    return out;
}

} // namespace

bool validSession(const Session& s) {
    if (!validAreaToken(s.area)) return false;
    if (s.day < 0 || s.day > 1000000) return false;
    long sum = 0;
    for (int i = 0; i < 8; ++i) {
        if (s.squad[i] < 0 || s.squad[i] > 1000000) return false;
        sum += s.squad[i];
    }
    if (s.other < 0 || s.other > 1000000) return false;
    if (s.total < 0 || s.total > 1000000) return false;
    if (sum + s.other != s.total) return false;
    if (s.highscore < 0 || s.highscore > 1000000000) return false;
    if (s.unlocked != 0 && s.unlocked != 1) return false;
    return true;
}

bool sessionEqual(const Session& a, const Session& b) {
    if (std::strcmp(a.area, b.area) != 0) return false;
    if (a.day != b.day || a.other != b.other || a.total != b.total) return false;
    if (a.highscore != b.highscore || a.unlocked != b.unlocked) return false;
    for (int i = 0; i < 8; ++i)
        if (a.squad[i] != b.squad[i]) return false;
    return true;
}

bool setContext(const char* area, int day, int highscore, int unlocked) {
    if (!validAreaToken(area)) return false;
    if (day < 0 || day > 1000000) return false;
    if (highscore < 0 || highscore > 1000000000) return false;
    if (unlocked != 0 && unlocked != 1) return false;
    std::strncpy(sArea, area, sizeof(sArea) - 1);
    sArea[sizeof(sArea) - 1] = '\0';
    sDay = day;
    sHighscore = highscore;
    sUnlocked = unlocked;
    sHasContext = true;
    return true;
}

bool hasContext() { return sHasContext; }

bool collectLiveSession(Session& out) {
    if (!sHasContext) return false;
    if (!pikiMgr) return false;
    std::memset(&out, 0, sizeof(out));
    std::strncpy(out.area, sArea, sizeof(out.area) - 1);
    out.day = sDay;
    out.highscore = sHighscore;
    out.unlocked = sUnlocked;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Creature* raw = static_cast<Creature*>(*it);
        if (raw == nullptr || !raw->isAlive()) continue;
        const Piki* piki = static_cast<const Piki*>(raw);
        const unsigned color = static_cast<unsigned>(piki->mColor);
        if (color < 8)
            ++out.squad[color];
        else
            ++out.other;
        ++out.total;
    }
    return validSession(out);
}

bool saveSession(const char* path, const Session& s) {
    if (path == nullptr || path[0] == '\0') return false;
    if (!validSession(s)) {
        std::printf("[Pikipelago] P2_OVERWORLD_SAVE_REFUSED reason=invalid-session\n");
        std::fflush(stdout);
        return false;
    }
    std::ofstream out(path, std::ios::binary | std::ios::trunc);
    if (!out) {
        std::printf("[Pikipelago] P2_OVERWORLD_SAVE_REFUSED reason=cannot-open\n");
        std::fflush(stdout);
        return false;
    }
    out << kHeader << "\n";
    out << "area " << s.area << "\n";
    out << "day " << s.day << "\n";
    out << "squad";
    for (int i = 0; i < 8; ++i) out << " " << s.squad[i];
    out << " other " << s.other << " total " << s.total << "\n";
    out << "highscore " << s.highscore << "\n";
    out << "unlocked " << s.unlocked << "\n";
    out.flush();
    if (!out) {
        std::printf("[Pikipelago] P2_OVERWORLD_SAVE_REFUSED reason=write-failed\n");
        std::fflush(stdout);
        return false;
    }
    out.close();
    std::ifstream check(path, std::ios::binary | std::ios::ate);
    const long bytes = check ? static_cast<long>(check.tellg()) : -1L;
    std::printf("[Pikipelago] P2_OVERWORLD_SAVE_SAVED path=%s bytes=%ld\n", path, bytes);
    std::fflush(stdout);
    return bytes > 0;
}

bool loadSession(const char* path, Session& out, size_t maxBytes) {
    if (path == nullptr || path[0] == '\0' || maxBytes == 0) return false;
    std::ifstream in(path, std::ios::binary | std::ios::ate);
    if (!in) {
        std::printf("[Pikipelago] P2_OVERWORLD_SAVE_REFUSED reason=cannot-open\n");
        std::fflush(stdout);
        return false;
    }
    const long size = static_cast<long>(in.tellg());
    if (size <= 0 || static_cast<size_t>(size) > maxBytes) {
        std::printf("[Pikipelago] P2_OVERWORLD_SAVE_REFUSED reason=size-guard\n");
        std::fflush(stdout);
        return false;
    }
    in.seekg(0);
    std::string text(static_cast<size_t>(size), '\0');
    in.read(&text[0], size);
    if (!in) {
        std::printf("[Pikipelago] P2_OVERWORLD_SAVE_REFUSED reason=read-failed\n");
        std::fflush(stdout);
        return false;
    }
    std::vector<std::string> lines;
    {
        std::string cur;
        for (size_t i = 0; i <= text.size(); ++i) {
            const char c = (i < text.size()) ? text[i] : '\n';
            if (c == '\n') {
                if (!cur.empty() || !lines.empty()) lines.push_back(cur);
                cur.clear();
            } else if (c != '\r') {
                cur.push_back(c);
            }
        }
        while (!lines.empty() && lines.back().empty()) lines.pop_back();
    }
    Session s;
    std::memset(&s, 0, sizeof(s));
    bool ok = (lines.size() == 6) && (lines[0] == kHeader);
    std::vector<std::string> w;
    if (ok) {
        w = splitWords(lines[1]);
        ok = (w.size() == 2) && (w[0] == "area") && validAreaToken(w[1].c_str());
        if (ok) std::strncpy(s.area, w[1].c_str(), sizeof(s.area) - 1);
    }
    if (ok) {
        w = splitWords(lines[2]);
        ok = (w.size() == 2) && (w[0] == "day") && parseInt(w[1], s.day, 0, 1000000);
    }
    if (ok) {
        w = splitWords(lines[3]);
        ok = (w.size() == 13) && (w[0] == "squad") && (w[9] == "other") && (w[11] == "total");
        for (int i = 0; ok && i < 8; ++i) ok = parseInt(w[1 + i], s.squad[i], 0, 1000000);
        if (ok) ok = parseInt(w[10], s.other, 0, 1000000) && parseInt(w[12], s.total, 0, 1000000);
    }
    if (ok) {
        w = splitWords(lines[4]);
        ok = (w.size() == 2) && (w[0] == "highscore") && parseInt(w[1], s.highscore, 0, 1000000000);
    }
    if (ok) {
        w = splitWords(lines[5]);
        ok = (w.size() == 2) && (w[0] == "unlocked") && parseInt(w[1], s.unlocked, 0, 1);
    }
    if (ok) ok = validSession(s);
    if (!ok) {
        std::printf("[Pikipelago] P2_OVERWORLD_SAVE_REFUSED reason=malformed\n");
        std::fflush(stdout);
        return false;
    }
    out = s;
    std::printf("[Pikipelago] P2_OVERWORLD_SAVE_LOADED path=%s bytes=%ld\n", path, size);
    std::fflush(stdout);
    return true;
}

bool verifyRoundTrip(const char* path, const Session& s) {
    Session back;
    std::memset(&back, 0, sizeof(back));
    if (!saveSession(path, s)) return false;
    if (!loadSession(path, back, kDefaultMaxBytes)) return false;
    if (!sessionEqual(s, back)) {
        std::printf("[Pikipelago] P2_OVERWORLD_SAVE_REFUSED reason=round-trip-mismatch\n");
        std::fflush(stdout);
        return false;
    }
    sSupported = true;
    std::strncpy(sLastPath, path != nullptr ? path : "", sizeof(sLastPath) - 1);
    std::printf("[Pikipelago] P2_OVERWORLD_SAVE_SUPPORTED area=%s squad=%d highscore=%d unlocked=%d\n",
                s.area, s.total, s.highscore, s.unlocked);
    std::fflush(stdout);
    return true;
}

bool supported() { return sSupported; }

const char* lastPath() { return sLastPath; }

void reset() {
    sSupported = false;
    sLastPath[0] = '\0';
    sPollDone = false;
}

} // namespace p2overworldsave

void pc_p2_overworld_save_poll() {
    using namespace p2overworldsave;
    if (sPollDone) return;
    if (!hasContext() || !pikiMgr) return;
    Session session;
    std::memset(&session, 0, sizeof(session));
    if (!collectLiveSession(session)) return;
    sPollDone = true;
    (void)verifyRoundTrip("p2-overworld-save.txt", session);
}
