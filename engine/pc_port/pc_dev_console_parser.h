#pragma once
// Engine-free command parser for the in-game dev console (#942).
//
// The console itself (pc_dev_console.cpp) is engine-coupled; everything that
// can be unit-tested without the engine lives here: the command grammar, the
// P2 species table (source id <-> names <-> P1 host vehicle) and the dev
// target-uid scheme shared with the root launcher
// (randomizer/dev_console.py DEV_TARGET_BASE).
//
// Dev target uids: a dev session's seed binds every staged species to the
// synthetic generator uid 0xDE000000 + source_id. No real generator carries
// such a uid, so a normal seed never resolves one; the console's `spawn`
// creates a runtime generator registered under it so every family binder,
// sidecar and delivery path keys off the same token the placement path uses.
#include "pc_p2_campaign_policy.h"
#include <cstdlib>
#include <cstring>
#include <cstdio>

namespace devconsole {

constexpr unsigned kDevTargetBase = 0xDE000000u;
inline unsigned devTargetUid(unsigned source) { return kDevTargetBase + source; }
inline bool isDevTargetUid(unsigned uid) { return uid > kDevTargetBase && uid < kDevTargetBase + 0x10000u; }
inline unsigned devTargetSource(unsigned uid) { return isDevTargetUid(uid) ? uid - kDevTargetBase : 0u; }

struct Species {
    unsigned source;
    const char* enumName;
    const char* commonName;
};

// Playable pool mirror of randomizer/seed.py PLAYABLE_P2_SPECIES (order kept).
// Host vehicles come from p2campaign::hostType so the table cannot drift from
// the placement path. tests/test_dev_console.py keeps this list in sync.
static const Species kSpecies[] = {
    {44, "BlueKochappy", "Dwarf Orange Bulborb"},
    {54, "Miulin", "Mamuta"},
    {59, "FireOtakara", "Fiery Dweevil"},
    {60, "WaterOtakara", "Caustic Dweevil"},
    {61, "GasOtakara", "Munge Dweevil"},
    {62, "ElecOtakara", "Anode Dweevil"},
    {23, "Sarai", "Swooping Snitchbug"},
    {79, "Sokkuri", "Skitter Leaf"},
    {2, "Chappy", "Red Bulborb"},
    {33, "FireChappy", "Fiery Bulblax"},
    {35, "KumaChappy", "Spotty Bulbear"},
    {43, "YellowChappy", "Hairy Bulborb"},
    {53, "KingChappy", "Emperor Bulblax"},
    {67, "LeafChappy", "Bulbmin"},
    {76, "KumaKochappy", "Dwarf Bulbear"},
    {12, "UjiA", "Female Sheargrub"},
    {13, "UjiB", "Male Sheargrub"},
    {14, "Tobi", "Shearwig"},
    {28, "ElecBug", "Anode Beetle"},
    {94, "DangoMushi", "Segmented Crawbster"},
    {68, "TamagoMushi", "Mitite"},
    {17, "Frog", "Yellow Wollywog"},
    {18, "MaroFrog", "Wollywog"},
    {24, "Tank", "Fiery Blowhog"},
    {75, "Kabuto", "Armored Cannon Beetle Larva"},
    {56, "Damagumo", "Beady Long Legs"},
    {63, "Jigumo", "Hermit Crawmad"},
    {69, "BigFoot", "Raging Long Legs"},
    {34, "SnakeCrow", "Burrowing Snagret"},
    {70, "SnakeWhole", "Pileated Snagret"},
    {65, "Imomushi", "Ravenous Whiskerpillar"},
    {71, "UmiMushi", "Toady Bloyster"},
    {101, "UmiMushiBlind", "Ranging Bloyster"},
    {25, "Wtank", "Watery Blowhog"},
    {15, "Armor", "Cloaking Burrow-nit"},
    {78, "MiniHoudai", "Gatling Groink"},
    {73, "BigTreasure", "Titan Dweevil"},
    {32, "Demon", "Bumbling Snitchbug"},
    {38, "PanModoki", "Breadbug"},
    {41, "Fuefuki", "Antenna Beetle"},
    {58, "BombSarai", "Careening Dirigibug"},
};
constexpr int kSpeciesCount = int(sizeof(kSpecies) / sizeof(kSpecies[0]));

inline int hostTypeFor(unsigned source) { return p2campaign::hostType(source, -1, false); }

inline bool ieq(const char* a, const char* b)
{
    if (!a || !b) return false;
    while (*a && *b) {
        char ca = *a, cb = *b;
        if (ca >= 'A' && ca <= 'Z') ca = char(ca - 'A' + 'a');
        if (cb >= 'A' && cb <= 'Z') cb = char(cb - 'A' + 'a');
        if (ca != cb) return false;
        ++a; ++b;
    }
    return *a == *b;
}

// Resolve a species token: decimal source id, enum name or common name
// (case-insensitive; common names may be written with '_' for spaces).
inline const Species* findSpecies(const char* token)
{
    if (!token || !*token) return nullptr;
    char* end = nullptr;
    const unsigned long id = std::strtoul(token, &end, 10);
    if (end && *end == '\0' && end != token) {
        for (const Species& s : kSpecies) if (s.source == id) return &s;
        return nullptr;
    }
    for (const Species& s : kSpecies) if (ieq(s.enumName, token)) return &s;
    char buf[64];
    for (const Species& s : kSpecies) {
        std::snprintf(buf, sizeof(buf), "%s", s.commonName);
        for (char* p = buf; *p; ++p) if (*p == ' ') *p = '_';
        if (ieq(buf, token)) return &s;
    }
    return nullptr;
}

// P1 boss arena centres (randomizer/p2_boss_arenas.py P1_BOSS_ARENAS); the
// root sync test fails on drift. Stage: 0 Impact, 1 Hope, 2 Navel, 3 Spring, 4 Trial.
struct Arena {
    const char* id;
    int stage;
    float x, y, z;
};
static const Arena kArenas[] = {
    {"impact_goolix", 0, -815.7f, 20.0f, 654.3f},
    {"hope_snagret_pit", 1, -867.4f, -17.5f, 3901.8f},
    {"hope_snagret_part", 1, -460.0f, -17.2f, 3708.6f},
    {"navel_beady_long_legs", 2, 1543.1f, -195.1f, 618.9f},
    {"navel_puffstool", 2, 1394.5f, -267.8f, 1784.6f},
    {"spring_cannon_beetle", 3, -450.9f, 89.0f, -941.4f},
    {"last_emperor", 4, 0.0f, -25.0f, 2700.0f},
};
constexpr int kArenaCount = int(sizeof(kArenas) / sizeof(kArenas[0]));

inline const Arena* findArena(const char* id)
{
    for (const Arena& a : kArenas) if (ieq(a.id, id)) return &a;
    return nullptr;
}

enum class Cmd {
    None,     // empty line
    Help,
    List,
    Spawn,    // spawn <species|p1 teki name> [count] [norebind]
    Kill,     // kill [all]
    KillAll,
    Hurt,     // hurt [fraction] : damage every live campaign P2 actor by a fraction of its max health
    Pikmin,   // pikmin <red|yellow|blue> <n>
    Day,      // day <n>
    Time,     // time <hours 0..24 | 0..1 fraction>
    Tp,       // tp <x> <z> | tp <arena_id>
    Pos,      // print captain position
    Rebind,   // rerun the stage P2 family setups
    Bomb,     // bomb [n] : n lit P1 bomb rocks (BOMB_Set) in front of the captain, for comparisons
    Unknown,
};

// Pikmin colours as the engine numbers them (Piki.h): Blue 0, Red 1, Yellow 2.
enum { kColourBlue = 0, kColourRed = 1, kColourYellow = 2 };

struct Command {
    Cmd kind = Cmd::None;
    char token[48] = {0};     // spawn species token / tp arena id / raw word
    const Species* species = nullptr; // resolved P2 species, or null for a P1 name
    int count = 1;
    bool stored = false;      // hurt: queue the damage in mStoredDamage (families that own health drain it)
    bool rebind = true;       // spawn: rerun the family setup when no dynamic binder exists
    int colour = -1;
    int day = 0;
    float time = 0.0f;
    float x = 0.0f, z = 0.0f;
    const Arena* arena = nullptr;
    char error[96] = {0};
};

inline int splitWords(const char* line, char words[][48], int maxWords)
{
    int n = 0;
    const char* p = line;
    while (*p && n < maxWords) {
        while (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n') ++p;
        if (!*p) break;
        int len = 0;
        while (*p && *p != ' ' && *p != '\t' && *p != '\r' && *p != '\n') {
            if (len < 47) words[n][len++] = *p;
            ++p;
        }
        words[n][len] = '\0';
        ++n;
    }
    return n;
}

inline int parseColour(const char* w)
{
    if (ieq(w, "red") || ieq(w, "r")) return kColourRed;
    if (ieq(w, "yellow") || ieq(w, "y")) return kColourYellow;
    if (ieq(w, "blue") || ieq(w, "b")) return kColourBlue;
    return -1;
}

inline bool parseInt(const char* w, int& out)
{
    char* end = nullptr;
    const long v = std::strtol(w, &end, 10);
    if (!end || end == w || *end) return false;
    out = int(v);
    return true;
}

inline bool parseFloat(const char* w, float& out)
{
    char* end = nullptr;
    const double v = std::strtod(w, &end);
    if (!end || end == w || *end) return false;
    out = float(v);
    return true;
}

inline Command parse(const char* line)
{
    Command c;
    if (!line) return c;
    if (const char* hash = std::strchr(line, '#')) {
        // Comment lines in script files.
        if (hash == line) return c;
    }
    char words[6][48];
    const int n = splitWords(line, words, 6);
    if (n == 0) return c;
    const char* w = words[0];
    std::snprintf(c.token, sizeof(c.token), "%s", w);
    if (ieq(w, "help") || ieq(w, "?")) { c.kind = Cmd::Help; return c; }
    if (ieq(w, "list") || ieq(w, "ls")) { c.kind = Cmd::List; return c; }
    if (ieq(w, "pos") || ieq(w, "where")) { c.kind = Cmd::Pos; return c; }
    if (ieq(w, "bomb")) {
        c.kind = Cmd::Bomb;
        c.count = 1;
        if (n >= 2 && (!parseInt(words[1], c.count) || c.count < 1 || c.count > 5))
            std::snprintf(c.error, sizeof(c.error), "usage: bomb [1..5]");
        return c;
    }
    if (ieq(w, "rebind")) { c.kind = Cmd::Rebind; return c; }
    if (ieq(w, "hurt")) {
        c.kind = Cmd::Hurt;
        c.time = 0.4f;
        if (n >= 3 && ieq(words[2], "stored")) c.stored = true;
        if (n >= 2 && (!parseFloat(words[1], c.time) || c.time <= 0.0f || c.time >= 1.0f))
            std::snprintf(c.error, sizeof(c.error), "usage: hurt [fraction 0..1, default 0.4]");
        return c;
    }
    if (ieq(w, "killall")) { c.kind = Cmd::KillAll; return c; }
    if (ieq(w, "kill")) {
        c.kind = (n >= 2 && ieq(words[1], "all")) ? Cmd::KillAll : Cmd::Kill;
        return c;
    }
    if (ieq(w, "spawn")) {
        c.kind = Cmd::Spawn;
        if (n < 2) { std::snprintf(c.error, sizeof(c.error), "usage: spawn <species|p1_name> [count] [norebind]"); return c; }
        std::snprintf(c.token, sizeof(c.token), "%s", words[1]);
        c.species = findSpecies(words[1]);
        for (int i = 2; i < n; ++i) {
            int v = 0;
            if (ieq(words[i], "norebind")) c.rebind = false;
            else if (parseInt(words[i], v)) c.count = v;
            else { std::snprintf(c.error, sizeof(c.error), "bad argument: %s", words[i]); return c; }
        }
        if (c.count < 1 || c.count > 16) { std::snprintf(c.error, sizeof(c.error), "count must be 1..16"); }
        return c;
    }
    if (ieq(w, "pikmin") || ieq(w, "piki")) {
        c.kind = Cmd::Pikmin;
        if (n < 2) { std::snprintf(c.error, sizeof(c.error), "usage: pikmin <red|yellow|blue> [n]"); return c; }
        c.colour = parseColour(words[1]);
        if (c.colour < 0) { std::snprintf(c.error, sizeof(c.error), "unknown colour: %s", words[1]); return c; }
        c.count = 5;
        if (n >= 3 && (!parseInt(words[2], c.count) || c.count < 1 || c.count > 100))
            std::snprintf(c.error, sizeof(c.error), "count must be 1..100");
        return c;
    }
    if (ieq(w, "day")) {
        c.kind = Cmd::Day;
        if (n < 2 || !parseInt(words[1], c.day) || c.day < 1 || c.day > 99)
            std::snprintf(c.error, sizeof(c.error), "usage: day <1..99>");
        return c;
    }
    if (ieq(w, "time")) {
        c.kind = Cmd::Time;
        if (n < 2 || !parseFloat(words[1], c.time) || c.time < 0.0f || c.time > 24.0f) {
            std::snprintf(c.error, sizeof(c.error), "usage: time <hours 0..24 | fraction 0..1>");
            return c;
        }
        // A fraction of the day (0..1) is accepted as well as clock hours.
        if (c.time <= 1.0f) c.time *= 24.0f;
        return c;
    }
    if (ieq(w, "tp") || ieq(w, "teleport")) {
        c.kind = Cmd::Tp;
        if (n >= 3 && parseFloat(words[1], c.x) && parseFloat(words[2], c.z)) return c;
        if (n >= 2 && (c.arena = findArena(words[1])) != nullptr) {
            std::snprintf(c.token, sizeof(c.token), "%s", words[1]);
            c.x = c.arena->x;
            c.z = c.arena->z;
            return c;
        }
        std::snprintf(c.error, sizeof(c.error), "usage: tp <x> <z> | tp <arena_id>");
        return c;
    }
    c.kind = Cmd::Unknown;
    std::snprintf(c.error, sizeof(c.error), "unknown command: %s (try help)", w);
    return c;
}

inline const char* helpText()
{
    return "spawn <id|Enum|Common_Name|p1 teki name> [count] [norebind] | kill [all] | killall | hurt [fraction [stored]] | "
           "pikmin <red|yellow|blue> [n] | day <n> | time <hours|0..1> | tp <x> <z> | tp <arena> | pos | bomb [n] | list | rebind | help";
}

} // namespace devconsole
