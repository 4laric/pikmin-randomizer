#include "pc_p2_ship_store.h"
#include "pc_p2_campaign_policy.h"
#include "pc_p2_proxy.h"
#include "pc_randomizer.h"
#include "pc_randomizer_catalog.h"
#include "pc_randomizer_spawn_catalog.h"
#include "pc_randomizer_campaign_catalog.h"
#include "pc_randomizer_p2_roster.h"
#include "pc_p2_delivery_host.h"
#include "pc_randomizer_outbox.h"
#include "netplay/pc_netplay_sha256.h"
#include "netplay/pc_netplay_loadguard.h"
#include <unordered_map>
#include <cstdint>
#include <cmath>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <sstream>
#include <string>
#include <set>
#include <thread>
#include <tuple>
#include <vector>
#ifdef _WIN32
#include <io.h>
#else
#include <unistd.h>
#endif

// Netplay M4 lane A session hooks (issue #885). Strong-defined by
// pc_netplay_session.cpp in netplay builds only; null here in the default
// build (and in engine-free harnesses like pc_randomizer_probe), where every
// use below is guarded by a null check and the historical path runs.
#if defined(__GNUC__)
__attribute__((weak)) bool pc_netplay_session_active(void);
__attribute__((weak)) bool pc_netplay_is_host(void);
__attribute__((weak)) bool pc_netplay_randstate_stream_enabled(void);
__attribute__((weak)) void pc_netplay_randstate_publish(const pc_randstate::PcRandState& st);
// Netplay M4 lane B1 (issue #885), same weak pattern: true while a
// synchronized HOLD is requested or in progress (the host I/O side then
// polls state.txt for liveness only and leaves publishing to the RESUME
// snapshot), and the host's queue for kBulkMirrorLedger messages.
__attribute__((weak)) bool pc_netplay_hold_active(void);
__attribute__((weak)) void pc_netplay_mirror_ledger_send(const uint8_t* data, size_t len);
// B1 fix round 1: the frame of the Advance being executed (stamped on each
// outbox entry at push time, so mirror lines carry their event frame).
__attribute__((weak)) uint32_t pc_netplay_current_frame(void);
// Netplay M4 lane B2 (issue #885): the day-end save barrier (bulk only,
// inside the save tick). Fills *hostOk with the host's outcome and
// hostSavHex with the host checkpoint's SHA-256 (64 hex + NUL).
__attribute__((weak)) bool pc_netplay_save_barrier(uint32_t frame, bool localOk, unsigned long long gen,
                                                  const uint8_t* sav, size_t savLen, const uint8_t* block,
                                                  size_t blockLen, bool* hostOk, char hostSavHex[65]);
// B2 fix round 1 (C3, C7, C12): ends the session as a desync (exit 5).
__attribute__((weak)) void pc_netplay_abort_desync(const char* why);
// M4 gap-fix lane S fix round 1 (MJ1): keep-alive network poll between the
// steps of the day-end save (netplay/pc_netplay_loadguard.h, kSiteSave);
// inert outside a netplay session tick.
__attribute__((weak)) void pc_netplay_load_keepalive(int site);
#else
bool pc_netplay_session_active(void);
bool pc_netplay_is_host(void);
bool pc_netplay_randstate_stream_enabled(void);
void pc_netplay_randstate_publish(const pc_randstate::PcRandState& st);
bool pc_netplay_hold_active(void);
void pc_netplay_mirror_ledger_send(const uint8_t* data, size_t len);
uint32_t pc_netplay_current_frame(void);
bool pc_netplay_save_barrier(uint32_t frame, bool localOk, unsigned long long gen, const uint8_t* sav,
                             size_t savLen, const uint8_t* block, size_t blockLen, bool* hostOk,
                             char hostSavHex[65]);
void pc_netplay_abort_desync(const char* why);
void pc_netplay_load_keepalive(int site);
#endif
#if PIKI_NETPLAY_BUILD
// Netplay launch lane (issue #887): defined by pc_netplay_launch.cpp, which
// is linked into every exe compiled with PIKI_NETPLAY_BUILD.
bool pc_netplay_launch_wants_local_state(void);
#endif

namespace {
bool noSticks = false, emperorGoal = false, emperorDefeated = false;
bool thelynk = false;
unsigned thelynkParts = 0, thelynkBonuses[18] = {}, thelynkUsed[18] = {};
std::set<unsigned> thelynkEnabled;
std::string thelynkNames[330];
const char* thelynkPartNames[30] = {
    "Pikmin: Bowsprit", "Pikmin: Gluon Drive", "Pikmin: Anti-Dioxin Filter", "Pikmin: Eternal Fuel Dynamo",
    "Pikmin: Main Engine", "Pikmin: Whimsical Radar", "Pikmin: Interstellar Radio", "Pikmin: Guard Satellite",
    "Pikmin: Chronos Reactor", "Pikmin: Radiation Canopy", "Pikmin: Geiger Counter", "Pikmin: Sagittarius",
    "Pikmin: Libra", "Pikmin: Omega Stabilizer", "Pikmin: Ionium Jet 1", "Pikmin: Ionium Jet 2",
    "Pikmin: Shock Absorber", "Pikmin: Gravity Jumper", "Pikmin: Pilot's Seat", "Pikmin: Nova Blaster",
    "Pikmin: Automatic Gear", "Pikmin: Zirconium Rotor", "Pikmin: Extraordinary Bolt", "Pikmin: Repair-type Bolt",
    "Pikmin: Space Float", "Pikmin: Massage Machine", "Pikmin: Secret Safe", "Pikmin: Positron Generator",
    "Pikmin: Analog Computer", "Pikmin: UV Lamp"
};
const char* thelynkModels[30] = {
    "ust1", "ust2", "ust3", "ust4", "ust5", "uf01", "uf02", "uf03", "uf04", "uf05",
    "uf06", "uf07", "uf08", "uf09", "uf10", "uf11", "un01", "un02", "un03", "un04",
    "un05", "un06", "un07", "un08", "un09", "un10", "un11", "un12", "un13", "un14"
};
unsigned thelynkId(unsigned index) { return index < 30 ? 71400 + index : 71500 + index - 30; }
int thelynkIndex(unsigned id) {
    return id >= 71400 && id < 71430 ? int(id - 71400) : id >= 71500 && id < 71800 ? int(id - 71500 + 30) : -1;
}
int thelynkModel(unsigned model) {
    for (int i = 0; i < 30; ++i) {
        const auto p = reinterpret_cast<const unsigned char*>(thelynkModels[i]);
        if (model == (unsigned(p[0]) << 24 | unsigned(p[1]) << 16 | unsigned(p[2]) << 8 | p[3])) return i;
    }
    return -1;
}
bool enabled = false, ready = false, goalReported = false, permanentChecks = false, noExploration = false, colorPopulation = false;
unsigned repairs = 0, unlocks = 0, flarlic = 0, schema = 1, checkCount = 30;
int startStage = 1;
int startColor = 1; // Native IDs: blue 0, red 1, yellow 2.
unsigned enemyMask = 0;
bool compactPopulation = false;
bool minibossEnemies = false;
bool slotEnemies = false, campaignEnemies = false;
// P2 enemy bridge: a versioned roster revision with target->source_id bindings.
// Lane 02 enforces admission; the native side only validates identity and revision.
bool p2EnemyBridge = false;
bool p2ProxyTier = false;
std::unordered_map<std::string, unsigned> p2Bindings;
// Versioned manifest-owned native journal order. Empty for all historical seeds.
std::vector<std::string> resolvedCheckNames, legacyCheckNames;
std::unordered_map<unsigned, unsigned> p2CheckIndices;
std::unordered_map<unsigned, std::set<std::pair<unsigned, int>>> p2CheckSources;
unsigned campaignAssignments[72] = {};
bool groupEnemies = false;
unsigned groupAssignments[12] = {};
unsigned adultAssignments[15] = {};
std::unordered_map<const void*, unsigned> generatorIds;
// Lane 06: live P2-bound Teki -> source_id / generator uid, captured at bind time.
// Single-use: consumed by pc_randomizer_p2_corpse_delivered and cleared by
// pc_randomizer_p2_forget_source so a recycled Teki address can never inherit it.
std::unordered_map<const void*, unsigned> p2TekiSources;
std::unordered_map<const void*, unsigned> p2TekiGeneratorUids;
// The randomizer's one ordinary delivery ledger (campaign directory), opened once.
P2DeliveryHostHandle p2DeliveryHost = nullptr;
// bot-v2 gap 1: in-memory copy of granted Onion corpse receipts this process,
// so the TEST-ONLY autoplay bot can sense its own receipt without touching
// the ledger (read-only query via pc_randomizer_p2_receipt_seen).
std::set<unsigned> p2ReceiptGenerators;
unsigned startingFlarlic = 2;
bool configuredFlarlic = false, configuredStats = false, progressiveStats = false, wideStats = false, balancedStats = false, doubledStats = false;
int baseColorStats[3][4] = {{100, 100, 100, 1}, {100, 100, 100, 1}, {100, 100, 100, 1}};
unsigned statUpgrades[3][4] = {};
bool benefitItems = false, bombDeliveries = false, combinedCaptain = false, bombTraps = false, proggTraps = false, prereleaseTraps = false;
unsigned benefits[9] = {}, consumedBenefits[7] = {};
// Level-style rewards: never consumed, only raised by newer state.
bool maturityItems = false;
unsigned maturity[3] = {};
unsigned dayLengthItems = 0, dayLengthStep = 0, dayLength = 0;
// Whistle Pluck item: the seed carries it, and once received it stays on.
bool whistlePluckItem = false, whistlePluck = false;
// DeathLink: the first state value read is the baseline, so links received while
// the game was closed never replay. Pending links are bounded; each applies once.
unsigned deathLinkUnit = 0, deathLinksSeen = 0, deathLinksPending = 0, deathsReported = 0;
bool deathLinkBaseline = false;
std::set<const void*> inducedDeaths;
int consumedIndex(PcBenefit kind) { return kind == PC_BENEFIT_PRERELEASE ? 6 : kind == PC_BENEFIT_PROGG ? 5 : kind == PC_BENEFIT_BOMB_TRAP ? 4 : kind == PC_BENEFIT_BOMBS ? 3 : int(kind); }
std::filesystem::path benefitJournal, campaignDirectory;
std::string campaignBlock;
unsigned long long campaignGeneration = 0;
bool campaignResumed = false;
bool purpleCampaign = false;
bool secondCaptain = false;
int colorStats[3][4] = {{100, 100, 100, 1}, {100, 100, 100, 1}, {100, 100, 100, 1}};
std::set<unsigned> checks;
std::string token, fingerprint, saveRoot;
std::filesystem::path directory;
std::filesystem::file_time_type lastStamp{};
auto lastFresh = std::chrono::steady_clock::now();
const char* items[] = { "Yellow Onion", "Blue Onion", "Pikmin: Forest Navel Access", "Pikmin: Distant Spring Access", "Pikmin: Final Trial Access" };
[[noreturn]] void fail(const char* message) {
    std::fprintf(stderr, "[Pikmin Randomizer] %s\n", message);
    std::exit(2);
}
uint64_t checkpointHash(const std::string& bytes) {
    uint64_t hash = 14695981039346656037ULL;
    for (unsigned char byte : bytes) { hash ^= byte; hash *= 1099511628211ULL; }
    return hash;
}
// Netplay M4 lane B2 (issue #885): the checkpoint rules of the historical
// loadCampaignCheckpoint, split into a side-effect-free scan so the
// handshake's checkpoint info, the joiner's stale-checkpoint set-aside and
// the post-transfer adoption reuse the one parser. loadCampaignCheckpoint()
// keeps its exact behaviour: the same checks in the same order, the same
// fail() messages, and campaignGeneration / campaignBlock /
// consumedBenefits / campaignResumed set only as before.
enum CkptScanStatus { kCkptNone, kCkptOk, kCkptBadName, kCkptMismatch, kCkptDamaged };
struct CkptScan {
    unsigned long long generation = 0; // newest well-named generation (kCkptOk: the checkpoint's)
    std::filesystem::path latest;
    std::string block;
    unsigned used[7] = {};
    p2ship::Store ship;
    unsigned thelynkUsed[18] = {};
};
CkptScanStatus scanCampaignCheckpoint(CkptScan& s) {
    if (!std::filesystem::exists(campaignDirectory)) return kCkptNone;
    for (const auto& entry : std::filesystem::directory_iterator(campaignDirectory)) {
        if (entry.path().extension() != ".sav") continue;
        const auto name = entry.path().stem().string();
        if (name.size() != 20 || name.find_first_not_of("0123456789") != std::string::npos)
            return kCkptBadName;
        const auto generation = std::stoull(name);
        if (generation > s.generation) { s.generation = generation; s.latest = entry.path(); }
    }
    if (s.latest.empty()) return kCkptNone;
    std::ifstream file(s.latest, std::ios::binary);
    std::string header; std::getline(file, header);
    std::istringstream meta(header);
    std::string magic, savedFingerprint, extra;
    unsigned long long generation; uint64_t hash;
    bool valid = bool(meta >> magic >> savedFingerprint >> generation);
    for (int i = 0; i < (prereleaseTraps ? 7 : proggTraps ? 6 : bombTraps ? 5 : bombDeliveries ? 4 : 3); ++i) valid = valid && bool(meta >> s.used[i]) && s.used[i] <= checkCount;
    if (purpleCampaign) valid = valid && s.ship.read(meta) && s.ship.counts[1][0] == 0
        && s.ship.counts[1][1] == 0 && s.ship.counts[1][2] == 0;
    if (thelynk) for (int i = 0; i < 18; ++i) valid = valid && bool(meta >> s.thelynkUsed[i]) && s.thelynkUsed[i] <= 330;
    if (!valid || !(meta >> hash) || magic != (thelynk ? "THELYNK_CAMPAIGN_1" : purpleCampaign ? "PIKMIN_CAMPAIGN_PURPLE_1" : prereleaseTraps ? "PIKMIN_CAMPAIGN_5" : proggTraps ? "PIKMIN_CAMPAIGN_4" : bombTraps ? "PIKMIN_CAMPAIGN_3" : bombDeliveries ? "PIKMIN_CAMPAIGN_2" : "PIKMIN_CAMPAIGN_1")
        || savedFingerprint != fingerprint || generation != s.generation || (meta >> extra))
        return kCkptMismatch;
    s.block.resize(32768);
    file.read(&s.block[0], 32768);
    if (file.gcount() != 32768 || file.peek() != EOF
        || checkpointHash(header.substr(0, header.rfind(' ')) + "\n" + s.block) != hash)
        return kCkptDamaged;
    return kCkptOk;
}
const char* ckptScanReason(CkptScanStatus st) {
    return st == kCkptBadName ? "invalid campaign checkpoint filename"
         : st == kCkptMismatch ? "campaign checkpoint header/seed mismatch; preserve campaign files for recovery"
         : "campaign checkpoint is damaged; preserve campaign files for recovery";
}
void loadCampaignCheckpoint() {
    CkptScan s;
    s.generation = campaignGeneration;
    const CkptScanStatus st = scanCampaignCheckpoint(s);
    campaignGeneration = s.generation;
    if (st == kCkptNone) return;
    if (st != kCkptOk) fail(ckptScanReason(st));
    campaignBlock = s.block;
    for (int i=0; i<7; ++i) consumedBenefits[i] = s.used[i];
    p2ship::stock = s.ship;
    for (int i = 0; i < 18; ++i) thelynkUsed[i] = s.thelynkUsed[i];
    campaignResumed = true;
}
// B2: a netplay session is configured (the session parses argv/env lazily;
// pc_main hands it argv before pc_bbft_init). Weak: always false in the
// default build.
bool netplay_session() {
    return pc_netplay_session_active != nullptr && pc_netplay_session_active();
}
bool netplay_join_mode() {
    return netplay_session() && pc_netplay_is_host != nullptr && !pc_netplay_is_host();
}
// B2, netplay join mode only: when the local checkpoint would be fatal
// (foreign fingerprint, damaged, badly named), rename every *.sav in the
// campaign directory to *.sav.stale-<unix seconds> (never delete) and go on
// as "none". A valid checkpoint (same seed) is left alone: the handshake's
// decision table compares it with the host's.
void set_aside_stale_checkpoint() {
    CkptScan s;
    const CkptScanStatus st = scanCampaignCheckpoint(s);
    if (st == kCkptNone || st == kCkptOk) return;
    const char* reason = st == kCkptBadName ? "badly named checkpoint file"
                       : st == kCkptMismatch ? "foreign or mismatched checkpoint header"
                       : "damaged checkpoint";
    std::printf("[netplay] local campaign checkpoint is stale (%s); setting it aside\n", reason);
    const long long now = (long long)std::chrono::duration_cast<std::chrono::seconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
    std::vector<std::filesystem::path> savs;
    for (const auto& entry : std::filesystem::directory_iterator(campaignDirectory))
        if (entry.path().extension() == ".sav") savs.push_back(entry.path());
    for (const auto& from : savs) {
        std::filesystem::path to = from;
        to += ".stale-" + std::to_string(now);
        for (int n = 1; std::filesystem::exists(to) && n < 1000; ++n) {
            to = from;
            to += ".stale-" + std::to_string(now) + "-" + std::to_string(n);
        }
        std::error_code ec;
        std::filesystem::rename(from, to, ec);
        if (ec) fail("cannot set aside a stale campaign checkpoint; preserve campaign files for recovery");
        std::printf("[netplay] set aside %s -> %s\n", from.filename().string().c_str(), to.filename().string().c_str());
    }
    std::fflush(stdout);
}
// Upper bound on ENEMY_P2 bindings per seed. Bindings live in a std::map, so
// this is a parser sanity limit, not a table size; it must cover every
// ordinary campaign generator (72), the holder slots and the boss arenas the
// root placement document can bind (#948). Root mirrors it in
// experimental/pikmin2_seed_bridge.py (P2_MAX_BINDINGS).
static const unsigned kP2MaxBindings = 256;
bool hex64(const std::string& s) {
    return s.size() == 64 && s.find_first_not_of("0123456789abcdef") == std::string::npos;
}
void expect(std::istream& in, const char* expected) {
    std::string word;
    if (!(in >> word) || word != expected) fail("unsupported or malformed bootstrap");
}
const char* baseCheckName(unsigned i) { return compactPopulation ? (permanentChecks ? randomizerCompactPermanentNames[i] : randomizerCompactCollectionNames[i]) : colorPopulation ? (permanentChecks ? randomizerColorPermanentNames[i] : randomizerColorCollectionNames[i]) : noExploration ? (permanentChecks ? randomizerNoExplorePermanentNames[i] : randomizerNoExploreCollectionNames[i]) : schema >= 9 ? (permanentChecks ? randomizerModernPermanentNames[i] : randomizerModernCollectionNames[i]) : schema >= 8 ? randomizerPermanentNames[i] : schema >= 7 ? randomizerCollectionNames[i] : randomizerCheckNames[i]; }
const char* legacyCheckName(unsigned i) {
    if (!noSticks) return baseCheckName(i);
    unsigned source = 0;
    for (;;) {
        const char* name = baseCheckName(source++);
        if (std::strstr(name, "Climbing Stick")) continue;
        if (i-- == 0) return name;
    }
}
const char* checkName(unsigned i) {
    if (thelynk) return thelynkNames[i].c_str();
    return resolvedCheckNames.empty() ? legacyCheckName(i) : resolvedCheckNames.at(i).c_str();
}
int index(const char* name) {
    if (name) for (unsigned i = 0; i < checkCount; ++i) if (!std::strcmp(name, checkName(i))) return (int)i;
    return -1;
}
bool initTheLynk(std::istream& input, const char* bootstrap) {
    expect(input, "1");
    expect(input, "SESSION"); input >> token;
    expect(input, "FINGERPRINT"); input >> fingerprint;
    if (!hex64(token) || !hex64(fingerprint)) fail("invalid TheLynk identity");
    thelynk = true; schema = 10; checkCount = 330; startStage = 0;
    for (unsigned i = 0; i < 30; ++i) thelynkNames[i] = thelynkPartNames[i];
    const char* colors[] = {"Red", "Yellow", "Blue"};
    for (unsigned c = 0; c < 3; ++c) for (unsigned n = 1; n <= 100; ++n)
        thelynkNames[30 + c * 100 + n - 1] = std::string(colors[c]) + " Pikmin: " + std::to_string(n);
    expect(input, "CHECKS"); unsigned count;
    if (!(input >> count) || count < 30 || count > 330) fail("invalid TheLynk check count");
    for (unsigned i = 0; i < count; ++i) {
        unsigned id; if (!(input >> id)) fail("invalid TheLynk check ID");
        int slot = thelynkIndex(id);
        if (slot < 0 || !thelynkEnabled.insert(unsigned(slot)).second) fail("unknown or duplicate TheLynk check");
    }
    for (unsigned i = 0; i < 30; ++i) if (!thelynkEnabled.count(i)) fail("missing TheLynk ship-part check");
    expect(input, "END"); std::string extra;
    if (input >> extra) fail("trailing TheLynk bootstrap");
    directory = std::filesystem::absolute(bootstrap).parent_path();
    campaignDirectory = directory.parent_path().parent_path() / "campaign";
    saveRoot = (campaignDirectory / "card").generic_string();
    if (std::filesystem::exists(directory / "hello.txt") || std::filesystem::exists(directory / "checks.txt"))
        fail("TheLynk run already used");
    loadCampaignCheckpoint();
    enabled = true; pc_randomizer_update();
    std::ofstream hello(directory / "hello.tmp");
    hello << "THELYNK_HELLO 1 " << token << ' ' << fingerprint << " individual-parts-v1 squad-checks-v1 typed-pikmin-v1 END\n";
    hello.close(); if (!hello) fail("cannot write TheLynk handshake");
    std::filesystem::rename(directory / "hello.tmp", directory / "hello.txt");
    return true;
}
void updateTheLynk(std::istream& input) {
    expect(input, "THELYNK_STATE"); expect(input, "1");
    std::string session; unsigned active, parts;
    if (!(input >> session >> active >> parts) || session != token || active > 1 || parts >= (1u << 30)
        || (parts & thelynkParts) != thelynkParts) fail("invalid/retracted TheLynk inventory");
    expect(input, "CHECKS"); unsigned count;
    if (!(input >> count) || count > thelynkEnabled.size()) fail("invalid TheLynk checked count");
    std::set<unsigned> incoming;
    for (unsigned i = 0; i < count; ++i) {
        unsigned id; if (!(input >> id)) fail("invalid TheLynk checked ID");
        int slot = thelynkIndex(id);
        if (slot < 0 || !thelynkEnabled.count(unsigned(slot)) || !incoming.insert(unsigned(slot)).second)
            fail("unknown or duplicate TheLynk checked ID");
    }
    expect(input, "BONUSES"); unsigned bonus[18];
    for (int i = 0; i < 18; ++i) if (!(input >> bonus[i]) || bonus[i] > thelynkEnabled.size()
        || bonus[i] < thelynkBonuses[i] || bonus[i] < thelynkUsed[i]) fail("invalid/retracted TheLynk bonus");
    unsigned receipts = 0;
    for (unsigned i = 0; i < 30; ++i) if (parts & (1u << i)) ++receipts;
    for (unsigned n : bonus) receipts += n;
    if (receipts > thelynkEnabled.size()) fail("too many TheLynk receipts");
    expect(input, "END"); std::string extra;
    if (input >> extra) fail("trailing TheLynk state");
    thelynkParts = parts;
    repairs = 0; for (unsigned i = 0; i < 30; ++i) if (parts & (1u << i)) ++repairs;
    for (int i = 0; i < 18; ++i) thelynkBonuses[i] = bonus[i];
    checks.insert(incoming.begin(), incoming.end());
    ready = active != 0;
}
// M4 lane A split of pc_randomizer_update (issue #885): the file poll
// (parse_state_stream) is the host I/O side; the sim side is apply_parsed().
// The streamed path uses apply_parsed(); the solo/AP path below retains
// the current complete parser, including its later optional reward sections.
struct ParsedRand {
    unsigned ready = 0, repairs = 0, unlocks = 0, flarlic = 0;
    std::set<unsigned> checks;
    unsigned stats[3][4] = {};
    unsigned benefits[9] = {};
    unsigned emperor = 0, deathLinks = 0;
    unsigned maturity[3] = {}, dayLength = 0, whistlePluck = 0;
    unsigned thelynkParts = 0, thelynkBonuses[18] = {};
};
// Netplay publish generation. The first published snapshot is gen 1; gen 0
// never goes on the wire (the reassembler drops it as stale).
uint32_t sNetGen = 0;
bool sHavePublished = false;
pc_randstate::PcRandState sLastPublished;

// ---- Netplay M4 lane B1 outbox (issue #885) ----
// `outbox active` = netplay session active AND the external-state stream on
// (the same switch as lane A's stream). When inactive, every external write
// site below runs its historical code byte for byte (the negative-control
// PIKMIN_NETPLAY_RANDSTATE_STREAM=0 stays per-peer legacy). When active, a
// site makes its sim-side change immediately and identically on both peers
// and pushes an entry; pc_randomizer_outbox_flush() writes the host journals
// or the client mirror once per Advance. None of the state below is read by
// the sim or hashed: checks (not checksJournaled / mirrorChecked) stays the
// only set the sim reads.
// The containers live in one function-local static (fix round 1, review R4):
// no namespace-scope constructor or atexit destructor is registered for
// them, so a process that never enters outbox mode never constructs them.
struct OutboxIo {
    pc_rand_outbox::Queue queue;
    std::set<unsigned> checksJournaled; // host: slots written to checks.txt this run
    std::set<unsigned> mirrorChecked;   // client: slots written as CHECKED lines
    pc_rand_outbox::ReceivedSequencer mirrorReceived; // client RECEIVED order
};
OutboxIo& outbox_io() {
    static OutboxIo io;
    return io;
}
bool outboxUsed = false; // set by the first push; the flush is a no-op before
bool mirrorEmperor = false;         // client: EMPEROR line written
uint32_t mirrorLastDeathLink = 0;   // client: last DEATHLINK total written
uint32_t mirrorLastFrame = 0;       // client: frames never decrease
uint32_t mirrorDeathsBase = 0;      // client: session.json pikmin_deaths (host ledger)
// Client: DEATHS lines wait for the first host ledger message (it carries
// deathsBase; a line written with base 0 could be a fatal retraction for the
// M4c runner). DEATHS is an absolute total, so only the latest pending one
// is kept; it is written with its own event frame when the ledger arrives.
bool mirrorDeathsPending = false;
uint32_t mirrorDeathsPendingTotal = 0, mirrorDeathsPendingFrame = 0;
bool mirrorDeathsSuppressed = false; // host sent kLedgerBaseUnknown
// Host ledger (runner session.json). deathsBase is fixed once, at session
// start (pc_randomizer_force_net_publish -> ledger_start), before any Advance
// and so before this run's deaths.txt has a line the runner could credit.
// The first ledger message is always sent there, also without session.json
// (base 0) or with an unreadable one (kLedgerBaseUnknown). Afterwards
// ledger_poll re-reads session.json whenever its stamp changes (every
// stream-host poll turn) and sends the receipts from ledgerSent onward.
bool ledgerStarted = false;
uint32_t ledgerDeathsBase = 0;
size_t ledgerSent = 0;
uint64_t ledgerFineStamp = 0;
bool ledgerHaveStamp = false;
// Host link liveness (HOLD source): state.txt readable, parsed, ready=1 and
// its stamp changed within 3 s. Computed on the host I/O side only. The
// freshness clock is linkFreshAt, touched only by a new state.txt stamp
// (stream_host_take) and the RESUME read (fix round 1, review B1-C4): the
// legacy lastFresh is also moved by every applied snapshot. A failed stat
// never clears linkStateOk (B1-C3): a missing or locked file ages out
// through the 3 s window instead of one stat blip HOLDing the session.
bool linkStateOk = false, linkReady = false;
std::chrono::steady_clock::time_point linkFreshAt;
// Stream host only: the fine (100 ns) state.txt stamp (see
// pc_rand_outbox::file_write_stamp); the legacy path keeps lastStamp.
uint64_t lastFineStamp = 0;
bool haveFineStamp = false;
bool outbox_active() {
    return pc_netplay_session_active != nullptr && pc_netplay_session_active()
        && pc_netplay_randstate_stream_enabled != nullptr && pc_netplay_randstate_stream_enabled();
}
bool outbox_host() { return pc_netplay_is_host == nullptr || pc_netplay_is_host(); }
void outbox_push(const pc_rand_outbox::Entry& e) {
    pc_rand_outbox::Entry stamped = e;
    stamped.frame = pc_netplay_current_frame != nullptr ? pc_netplay_current_frame() : 0;
    outboxUsed = true;
    if (!outbox_io().queue.push(stamped)) fail("netplay outbox overflow");
}
// Metadata binds every received state to the already authenticated bootstrap.
uint16_t net_features() {
    return (maturityItems ? 1 : 0) | (dayLengthItems ? 2 : 0) | (whistlePluckItem ? 4 : 0)
        | (p2EnemyBridge ? 8 : 0) | (purpleCampaign ? 16 : 0) | (secondCaptain ? 32 : 0)
        | (progressiveStats ? 64 : 0) | (benefitItems ? 128 : 0) | (deathLinkUnit ? 256 : 0)
        | (emperorGoal ? 512 : 0);
}
void require_net_state_schema() {
    if (checkCount > pc_randstate::kCheckSlots) fail("netplay randomizer catalog exceeds wire capacity");
}
void parse_state_stream(std::istream& input, ParsedRand& out) {
    require_net_state_schema();
    if (thelynk) {
        expect(input, "THELYNK_STATE"); expect(input, "1");
        std::string session; unsigned active, parts;
        if (!(input >> session >> active >> parts) || session != token || active > 1 || parts >= (1u << 30)
            || (parts & thelynkParts) != thelynkParts) fail("invalid/retracted TheLynk inventory");
        expect(input, "CHECKS"); unsigned count;
        if (!(input >> count) || count > thelynkEnabled.size()) fail("invalid TheLynk checked count");
        for (unsigned i = 0; i < count; ++i) {
            unsigned id; if (!(input >> id)) fail("invalid TheLynk checked ID");
            int slot = thelynkIndex(id);
            if (slot < 0 || !thelynkEnabled.count(unsigned(slot)) || !out.checks.insert(unsigned(slot)).second)
                fail("unknown or duplicate TheLynk checked ID");
        }
        expect(input, "BONUSES"); unsigned receipts = 0;
        for (unsigned i = 0; i < 30; ++i) if (parts & (1u << i)) ++out.repairs;
        receipts = out.repairs;
        for (int i = 0; i < 18; ++i) {
            unsigned& n = out.thelynkBonuses[i];
            if (!(input >> n) || n > thelynkEnabled.size() || n < thelynkBonuses[i] || n < thelynkUsed[i])
                fail("invalid/retracted TheLynk bonus");
            receipts += n;
        }
        if (receipts > thelynkEnabled.size()) fail("too many TheLynk receipts");
        expect(input, "END"); std::string extra;
        if (input >> extra) fail("trailing TheLynk state");
        out.thelynkParts = parts; out.ready = active;
        return;
    }
    std::string magic, session, end, extra;
    unsigned version, newReady, newRepairs, newUnlocks, newFlarlic = 0;
    std::set<unsigned> newChecks;
    bool parsed = bool(input >> magic >> version >> session >> newReady >> newRepairs >> newUnlocks);
    if (parsed && schema >= 2) parsed = bool(input >> newFlarlic);
    if (schema >= 8) {
        std::string marker; unsigned count;
        if (!parsed || !(input >> marker >> count) || marker != "CHECKS" || count > checkCount) fail("invalid check set header");
        for (unsigned i = 0; i < count; ++i) {
            unsigned slot;
            if (!(input >> slot) || slot >= checkCount || !newChecks.insert(slot).second) fail("invalid or duplicate check index");
        }
    } else {
        std::uint64_t mask = 0;
        parsed = parsed && bool(input >> mask);
        if (parsed && mask >= (1ull << checkCount)) fail("invalid legacy check mask");
        for (unsigned i = 0; i < checkCount; ++i) if (mask & (1ull << i)) newChecks.insert(i);
    }
    parsed = parsed && bool(input >> end);
    unsigned newStats[3][4] = {};
    if (progressiveStats) {
        if (!parsed || end != "UPGRADES") fail("missing progressive stat state");
        for (int c = 0; c < 3; ++c) for (int stat = 0; stat < 4; ++stat) {
            if (!(input >> newStats[c][stat]) || newStats[c][stat] > (stat == 0 || stat == 3 ? 2u : 1u) * (doubledStats ? 2u : 1u)
                || newStats[c][stat] < statUpgrades[c][stat]) fail("invalid or retracted stat upgrade");
        }
        parsed = bool(input >> end);
    }
    unsigned newBenefits[9] = {};
    if (benefitItems) {
        if (!parsed || end != "BENEFITS") fail("missing benefit state");
        for (int kind = 0; kind < (prereleaseTraps ? 9 : proggTraps ? 8 : bombTraps ? 7 : bombDeliveries ? 6 : 5); ++kind)
            if (!(input >> newBenefits[kind]) || newBenefits[kind] > (kind < 3 || kind >= 5 ? checkCount : 2u)
                || newBenefits[kind] < benefits[kind] || ((kind < 3 || kind >= 5) && newBenefits[kind] < consumedBenefits[consumedIndex(static_cast<PcBenefit>(kind))]))
                fail("invalid or retracted benefit receipt");
        parsed = bool(input >> end);
    }
    unsigned newMaturity[3] = {};
    if (maturityItems) {
        if (!parsed || end != "MATURITY") fail("missing maturity state");
        for (int c = 0; c < 3; ++c)
            if (!(input >> newMaturity[c]) || newMaturity[c] > 2 || newMaturity[c] < maturity[c]) fail("invalid or retracted maturity");
        parsed = bool(input >> end);
    }
    unsigned newDayLength = 0;
    if (dayLengthItems) {
        if (!parsed || end != "DAYLENGTH" || !(input >> newDayLength) || newDayLength > dayLengthItems || newDayLength < dayLength)
            fail("invalid or retracted day length");
        parsed = bool(input >> end);
    }
    unsigned newWhistlePluck = 0;
    if (whistlePluckItem) {
        if (!parsed || end != "WHISTLEPLUCK" || !(input >> newWhistlePluck) || newWhistlePluck > 1 || (whistlePluck && !newWhistlePluck))
            fail("invalid or retracted whistle pluck");
        parsed = bool(input >> end);
    }
    unsigned newEmperor = 0;
    if (emperorGoal) {
        if (!parsed || end != "EMPEROR" || !(input >> newEmperor) || newEmperor > 1 || (newEmperor && newRepairs < 25)) fail("invalid Emperor state");
        parsed = bool(input >> end);
    }
    unsigned newDeathLinks = 0;
    if (deathLinkUnit) {
        if (!parsed || end != "DEATHLINK" || !(input >> newDeathLinks)) fail("invalid DeathLink state");
        parsed = bool(input >> end);
    }
    if (!parsed || magic != "PIKMIN_STATE" || version != schema || session != token || newReady > 1
        || newRepairs > 25 || newUnlocks > (schema >= 5 ? 255u : schema == 4 ? 127u : schema == 3 ? 63u : 31u) || newFlarlic > 10 - startingFlarlic
        || end != "END" || (input >> extra))
        fail("invalid state: identity, version or range mismatch");
    // Inventory is monotonic within this authenticated run.
    if (newRepairs < repairs || (newUnlocks & unlocks) != unlocks || newFlarlic < flarlic)
        fail("state attempted to retract received progression");
    if (deathLinkBaseline && newDeathLinks < deathLinksSeen) fail("retracted DeathLinks");
    out.ready = newReady;
    out.repairs = newRepairs;
    out.unlocks = newUnlocks;
    out.flarlic = newFlarlic;
    out.checks = newChecks;
    for (int c = 0; c < 3; ++c) for (int stat = 0; stat < 4; ++stat) out.stats[c][stat] = newStats[c][stat];
    for (int kind = 0; kind < 9; ++kind) out.benefits[kind] = newBenefits[kind];
    for (int c = 0; c < 3; ++c) out.maturity[c] = newMaturity[c];
    out.dayLength = newDayLength; out.whistlePluck = newWhistlePluck;
    out.emperor = newEmperor;
    out.deathLinks = newDeathLinks;
}
void apply_parsed(const ParsedRand& p) {
    // All parsing and monotonic validation finished before any sim-side write.
    if (thelynk) {
        thelynkParts = p.thelynkParts;
        for (int i = 0; i < 18; ++i) thelynkBonuses[i] = p.thelynkBonuses[i];
    }
    for (int c = 0; c < 3; ++c) maturity[c] = p.maturity[c];
    dayLength = p.dayLength; whistlePluck = p.whistlePluck != 0;
    if (progressiveStats) for (int c = 0; c < 3; ++c) for (int stat = 0; stat < 4; ++stat) {
        if (statUpgrades[c][stat] != p.stats[c][stat])
            std::printf("[Pikmin Randomizer] STAT_UPGRADE color=%d stat=%d tier=%u\n", c, stat, p.stats[c][stat]);
        statUpgrades[c][stat] = p.stats[c][stat];
        colorStats[c][stat] = baseColorStats[c][stat] + (stat == 3 ? p.stats[c][stat] : 25 * p.stats[c][stat]);
    }
    for (int kind = 0; kind < 9; ++kind) benefits[kind] = p.benefits[kind];
    // B1: in outbox mode a streamed latch or DeathLink rise also becomes a
    // client mirror event (EMPEROR / DEATHLINK). Sim state is untouched.
    const bool outbox = outbox_active();
    if (outbox && !emperorDefeated && p.emperor != 0) {
        pc_rand_outbox::Entry e; e.kind = pc_rand_outbox::Kind::EmperorApplied; outbox_push(e);
    }
    emperorDefeated = emperorDefeated || p.emperor != 0;
    if (deathLinkUnit) {
        if (!deathLinkBaseline) {
            deathLinksSeen = p.deathLinks; deathLinkBaseline = true;
            if (outbox && p.deathLinks > 0) {
                std::printf("[Pikmin Randomizer] DEATHLINK_TOTAL %u\n", p.deathLinks);
                pc_rand_outbox::Entry e; e.kind = pc_rand_outbox::Kind::DeathLink; e.total = p.deathLinks; outbox_push(e);
            }
        }
        else if (p.deathLinks < deathLinksSeen) fail("state retracted received DeathLinks");
        else {
            if (outbox && p.deathLinks > deathLinksSeen) {
                std::printf("[Pikmin Randomizer] DEATHLINK_TOTAL %u\n", p.deathLinks);
                pc_rand_outbox::Entry e; e.kind = pc_rand_outbox::Kind::DeathLink; e.total = p.deathLinks; outbox_push(e);
            }
            deathLinksPending = std::min(3u, deathLinksPending + std::min(3u, p.deathLinks - deathLinksSeen));
            deathLinksSeen = p.deathLinks;
        }
    }
    ready = p.ready != 0;
    repairs = p.repairs;
    unlocks = p.unlocks;
    if (flarlic != p.flarlic) std::printf("[Pikmin Randomizer] CAPACITY %u\n", 10 * (startingFlarlic + p.flarlic));
    flarlic = p.flarlic;
    if (outbox) {
        // B1: a streamed CHECKS apply that adds a slot is logged on both
        // peers and mirrored by the client as CHECKED (insert order is the
        // set order, identical on both peers).
        for (unsigned slot : p.checks) {
            if (!checks.insert(slot).second) continue;
            std::printf("[Pikmin Randomizer] CHECK_APPLIED %u %s\n", slot, checkName(slot));
            pc_rand_outbox::Entry e; e.kind = pc_rand_outbox::Kind::CheckApplied; e.slot = slot; outbox_push(e);
        }
    } else {
        checks.insert(p.checks.begin(), p.checks.end());
    }
    if (pc_randomizer_goal() && !goalReported) {
        goalReported = true;
        std::puts("[Pikmin Randomizer] GOAL: Seed complete.");
    }
}
void net_from_parsed(const ParsedRand& p, uint32_t gen, pc_randstate::PcRandState& st) {
    require_net_state_schema();
    st = pc_randstate::PcRandState();
    st.mode = thelynk ? 2 : 1;
    st.features = net_features(); st.checkCount = uint16_t(checkCount);
    st.schema = thelynk ? 1 : uint8_t(schema);
    st.dayLength = uint8_t(p.dayLength); st.whistlePluck = uint8_t(p.whistlePluck);
    for (int c = 0; c < 3; ++c) st.maturity[c] = uint8_t(p.maturity[c]);
    st.thelynkParts = p.thelynkParts;
    for (int i = 0; i < 18; ++i) st.thelynkBonuses[i] = uint16_t(p.thelynkBonuses[i]);
    st.ready = (uint8_t)(p.ready != 0 ? 1 : 0);
    st.repairs = (uint8_t)p.repairs;
    st.unlocks = (uint8_t)p.unlocks;
    st.flarlic = (uint8_t)p.flarlic;
    st.emperor = (uint8_t)(p.emperor != 0 ? 1 : 0);
    st.deathLinks = p.deathLinks;
    for (size_t i = 0; i < pc_randstate::kCheckBytes; ++i) st.checks[i] = 0;
    for (unsigned slot : p.checks) {
        // Single shared width (pc_randstate::kCheckBytes): encoder and
        // decoder agree, and every current catalog fits the 512-slot bound.
        if (slot >= pc_randstate::kCheckSlots) fail("netplay state stream check slot exceeds wire bitset");
        st.checks[slot / 8] |= (uint8_t)(1u << (slot % 8));
    }
    for (int c = 0; c < 3; ++c) for (int s = 0; s < 4; ++s) st.stats[c * 4 + s] = (uint8_t)p.stats[c][s];
    for (int kind = 0; kind < 9; ++kind) st.benefits[kind] = (uint16_t)p.benefits[kind];
    st.gen = gen; // stamped by the publisher (0 = unstamped)
    st.crc = 0;   // computed by encode()
}
}

bool pc_randomizer_init(int argc, char** argv) {
    const char* bootstrap = nullptr;
    bool bbft = std::getenv("BBFT_PORT") && *std::getenv("BBFT_PORT");
    for (int i = 1; i < argc; ++i) {
        if (!std::strcmp(argv[i], "--bbft-port")) bbft = true;
        if (!std::strcmp(argv[i], "--randomizer-seed")) {
            if (bootstrap || ++i >= argc) fail("--randomizer-seed requires one bootstrap file");
            bootstrap = argv[i];
        }
    }
    if (!bootstrap) return false;
    if (bbft) fail("standalone and BBFT modes cannot be combined");
    p2ProxyTier = false;
    std::ifstream input(bootstrap);
    if (!input) fail("cannot open standalone bootstrap");
    std::string magic; input >> magic;
    if (magic == "PIKMIN_THELYNK") return initTheLynk(input, bootstrap);
    if (magic != "PIKMIN_RANDOMIZER") fail("unsupported bootstrap contract");
    std::string version; input >> version;
    if (version != "1" && version != "2" && version != "3" && version != "4" && version != "5" && version != "6" && version != "7" && version != "8" && version != "9") fail("unsupported bootstrap version");
    schema = (unsigned)(version[0] - '0');
    checkCount = schema >= 8 ? unsigned(sizeof(randomizerPermanentNames)/sizeof(*randomizerPermanentNames)) : schema >= 5 ? 58 : schema >= 2 ? 55 : 30;
    expect(input, "SESSION"); input >> token;
    expect(input, "FINGERPRINT"); input >> fingerprint;
    if (!hex64(token) || !hex64(fingerprint)) fail("invalid session or manifest fingerprint");
    expect(input, "PROFILE");
    std::string profile; input >> profile;
    if (profile == "navel-day2" && schema >= 3) startStage = 2;
    else if (profile == "impact-day2" && schema >= 5) startStage = 0;
    else if (profile == "spring-day2" && schema >= 5) startStage = 3;
    else if (profile == "trial-day2" && schema >= 5) startStage = 4;
    else if (profile != "foh-day2") fail("unsupported start profile");
    expect(input, "CATALOG"); expect(input, schema == 9 ? "gameplay-checks-v9" : schema == 8 ? "gameplay-checks-v8" : schema == 7 ? "gameplay-checks-v7" : schema == 6 ? "gameplay-checks-v6" : schema == 5 ? "gameplay-checks-v5" : schema == 4 ? "gameplay-checks-v4" : schema == 3 ? "gameplay-checks-v3" : schema == 2 ? "gameplay-checks-v2" : "vanilla-sites-v1");
    expect(input, "PLACEMENT"); expect(input, "identity-v1");
    expect(input, "GOAL"); std::string goalType; input >> goalType;
    if (goalType != "25" && !(schema == 9 && goalType == "emperor25")) fail("invalid goal");
    emperorGoal = goalType == "emperor25";
    expect(input, "DAYS"); expect(input, "repeat-day29-v1");
    if (schema >= 4) {
        expect(input, "COLOR"); std::string color; input >> color;
        if (color == "red") startColor = 1;
        else if (color == "yellow") startColor = 2;
        else if (color == "blue") startColor = 0;
        else fail("unsupported starting color");
    }
    permanentChecks = schema == 8;
    if (schema >= 9) {
        expect(input, "CHECKSET"); int value;
        if (!(input >> value) || (value < 0 || value > 31 || ((value & 4) && !(value & 2)) || ((value & 8) && !(value & 4)))) fail("invalid check set");
        noSticks = (value & 16) != 0;
        permanentChecks = (value & 1) != 0;
        noExploration = (value & 2) != 0;
        colorPopulation = (value & 4) != 0;
        compactPopulation = (value & 8) != 0;
        checkCount = compactPopulation ? (permanentChecks ? sizeof(randomizerCompactPermanentNames)/sizeof(*randomizerCompactPermanentNames) : sizeof(randomizerCompactCollectionNames)/sizeof(*randomizerCompactCollectionNames)) : colorPopulation ? (permanentChecks ? sizeof(randomizerColorPermanentNames)/sizeof(*randomizerColorPermanentNames) : sizeof(randomizerColorCollectionNames)/sizeof(*randomizerColorCollectionNames)) : noExploration ? (permanentChecks ? sizeof(randomizerNoExplorePermanentNames)/sizeof(*randomizerNoExplorePermanentNames) : sizeof(randomizerNoExploreCollectionNames)/sizeof(*randomizerNoExploreCollectionNames)) : permanentChecks ? sizeof(randomizerModernPermanentNames)/sizeof(*randomizerModernPermanentNames)
            : sizeof(randomizerModernCollectionNames)/sizeof(*randomizerModernCollectionNames);
        if (noSticks) {
            unsigned retired = 0;
            for (unsigned i = 0; i < checkCount; ++i)
                if (std::strstr(baseCheckName(i), "Climbing Stick")) ++retired;
            checkCount -= retired;
        }
    }
    if (schema >= 6) {
        expect(input, "ENEMIES");
        if (!(input >> enemyMask) || (schema == 6 && enemyMask < 1) || enemyMask > 7) fail("invalid enemy permutation");
    }
    std::string end; input >> end;
    if (end == "STARTING_FLARLIC") {
        configuredFlarlic = true;
        if (schema < 2 || !(input >> startingFlarlic) || startingFlarlic < 1 || startingFlarlic > 10) fail("invalid starting Flarlic");
        input >> end;
    }
    if (end == "COLOR_STATS" || end == "COLOR_STATS_WIDE" || end == "COLOR_STATS_BALANCED") {
        wideStats = end == "COLOR_STATS_WIDE";
        balancedStats = end == "COLOR_STATS_BALANCED";
        if (schema < 5) fail("color stats require all-area catalog");
        configuredStats = true;
        const char* colors[] = {"blue", "red", "yellow"};
        for (int c = 0; c < 3; ++c) {
            expect(input, colors[c]);
            for (int stat = 0; stat < 4; ++stat) {
                int value;
                if (!(input >> value)) fail("malformed color stats");
                const int minimum = stat == 3 ? 1 : balancedStats ? 25 : wideStats ? (stat == 0 ? 25 : 50) : stat == 0 ? 50 : 75;
                const int maximum = balancedStats ? (stat == 3 ? 1 : 100) : wideStats ? (stat == 3 ? 5 : stat == 0 ? 200 : 150) : stat == 0 ? 150 : stat == 3 ? 3 : 125;
                if (value < minimum || value > maximum || (stat != 3 && value % 25)) fail("invalid color stats");
                baseColorStats[c][stat] = colorStats[c][stat] = value;
            }
        }
        input >> end;
    }
    if (end == "PROGRESSIVE_STATS") {
        unsigned mode;
        if (schema < 7 || !(input >> mode) || (mode != 1 && mode != 2)) fail("invalid progressive stats mode");
        progressiveStats = true;
        doubledStats = mode == 2;
        input >> end;
    }
    if (end == "BENEFITS") {
        unsigned mode;
        if (!colorPopulation || !(input >> mode) || (mode < 1 || mode > 32)) fail("invalid benefit mode");
        benefitItems = true;
        bombDeliveries = ((mode - 1) & 1) != 0;
        combinedCaptain = ((mode - 1) & 2) != 0;
        bombTraps = ((mode - 1) & 4) != 0;
        proggTraps = ((mode - 1) & 8) != 0;
        prereleaseTraps = ((mode - 1) & 16) != 0;
        input >> end;
    }
    if (end == "MATURITY") {
        unsigned version;
        if (!benefitItems || !(input >> version) || version != 1) fail("invalid maturity mode");
        maturityItems = true;
        input >> end;
    }
    if (end == "DAY_LENGTH") {
        if (!benefitItems || !(input >> dayLengthItems >> dayLengthStep) || dayLengthItems < 1 || dayLengthItems > 10
            || dayLengthStep < 10 || dayLengthStep > 100 || dayLengthStep % 5) fail("invalid day length mode");
        input >> end;
    }
    if (end == "WHISTLE_PLUCK") {
        unsigned version;
        if (!benefitItems || !(input >> version) || version != 1) fail("invalid whistle pluck mode");
        whistlePluckItem = true;
        input >> end;
    }
    if (end == "DEATHLINK") {
        if (schema != 9 || !(input >> deathLinkUnit) || deathLinkUnit < 1 || deathLinkUnit > 100) fail("invalid DeathLink unit");
        input >> end;
    }
    if (end == "ENEMY_P2") {
        unsigned protocol, count; std::string revision;
        if (schema != 9 || enemyMask || slotEnemies || campaignEnemies || groupEnemies)
            fail("P2 enemy bridge cannot mix other enemy layouts");
        if (!(input >> protocol >> revision >> count) || protocol != 1
            || revision != randomizerP2RosterRevision || count == 0 || count > kP2MaxBindings)
            fail("incompatible P2 enemy roster or protocol version");
        for (unsigned i = 0; i < count; ++i) {
            std::string target; unsigned sourceId;
            if (!(input >> target >> sourceId) || target.empty() || target.size() > 64
                || !randomizerP2IsBindable(sourceId) || !p2Bindings.emplace(target, sourceId).second)
                fail("invalid P2 enemy binding");
        }
        p2EnemyBridge = true;
        p2ProxyTier = false;
        input >> end;
        if (end == "P2_PROXY_TIER") {
            unsigned tier = 0;
            if (!(input >> tier) || tier != 1) fail("invalid P2 proxy tier");
            p2ProxyTier = true;
            input >> end;
        }
        if (end == "ENEMY_CHECKS") {
            unsigned version, count;
            if (!(input >> version >> count) || version != 1 || count == 0 || count > checkCount + 102)
                fail("invalid resolved enemy check catalog");
            for (unsigned i = 0; i < checkCount; ++i) legacyCheckNames.emplace_back(legacyCheckName(i));
            std::set<unsigned> retained;
            for (unsigned i = 0; i < count; ++i) {
                std::string kind; unsigned value;
                if (!(input >> kind >> value)) fail("truncated resolved enemy check catalog");
                if (kind == "L") {
                    if (value >= legacyCheckNames.size() || !retained.insert(value).second)
                        fail("invalid resolved legacy check index");
                    resolvedCheckNames.push_back(legacyCheckNames[value]);
                } else if (kind == "P") {
                    unsigned sources;
                    if (!pc_randomizer_p2_bound(value) || value == 9 || value == 10 || value == 11 || value == 16
                        || !p2CheckIndices.emplace(value, i).second || !(input >> sources)
                        || sources == 0 || sources > kP2MaxBindings)
                        fail("invalid resolved P2 check identity");
                    for (unsigned j = 0; j < sources; ++j) {
                        unsigned uid; int stage;
                        if (!(input >> uid >> stage) || !uid || stage < 0 || stage > 4
                            || !p2CheckSources[value].insert({uid, stage}).second)
                            fail("invalid resolved P2 check source");
                    }
                    resolvedCheckNames.push_back("P2:" + std::to_string(value));
                } else fail("unknown resolved enemy check kind");
            }
            // Only bestiary locations may be removed from the legacy catalog.
            // Parts, population and permanent checks keep their original identity.
            for (unsigned i = 0; i < legacyCheckNames.size(); ++i)
                if (legacyCheckNames[i].find("Bestiary:") != 0 && !retained.count(i))
                    fail("resolved catalog omits non-enemy check");
            checkCount = count;
            input >> end;
        }
        if (end != "END" && end != "PURPLE" && end != "CAPTAINS") fail("P2 enemy bridge cannot mix other enemy layouts");
    }
    if (end == "ENEMY_CAMPAIGN") {
        unsigned version, count, miniboss; std::string catalog;
        if (schema != 9 || enemyMask || !(input >> version >> catalog >> count >> miniboss)
            || version != 1 || catalog != randomizerCampaignHash || count != 72 || miniboss != 1)
            fail("incompatible campaign enemy catalog");
        unsigned heavies[5] = {};
        for (unsigned i=0; i<count; ++i) {
            unsigned uid, species; const auto& row = randomizerCampaignSlots[i];
            if (!(input >> uid >> species) || uid != row.uid || species >= 35 || !(row.minibossAllowed & (1ULL << species)))
                fail("unsupported campaign enemy assignment");
            if (species == 9 || species == 17 || species == 24) ++heavies[row.stage];
            campaignAssignments[i] = species;
        }
        if (heavies[0] || heavies[1] != 1 || heavies[2] != 1 || heavies[3] != 1 || heavies[4])
            fail("campaign enemy heavy encounter budget exceeded");
        campaignEnemies = minibossEnemies = true;
        input >> end;
        if (end != "END") fail("campaign enemy mode cannot mix legacy layouts");
    }
    if (end == "ENEMY_MINIBOSSES") {
        int version;
        if (schema != 9 || !(input >> version) || version != 1) fail("invalid miniboss adapter version");
        minibossEnemies = true;
        input >> end;
        if (end != "ENEMY_SLOTS") fail("miniboss adapters require owned slots");
    }
    if (end == "ENEMY_SLOTS") {
        std::string catalog; unsigned count;
        if (schema != 9 || enemyMask || !(input >> catalog >> count) || catalog != randomizerSpawnCatalogHash || count != 15)
            fail("incompatible enemy slot catalog");
        unsigned bulborbs = 0, puffstools = 0, beetles = 0, mamutas = 0;
        for (unsigned i = 0; i < 15; ++i) {
            unsigned uid, species;
            if (!(input >> uid >> species) || uid != randomizerAdultSlots[i] || (species != 4 && species != 32 && !(minibossEnemies && (species == 9 || species == 17 || species == 24))))
                fail("invalid enemy slot assignment");
            adultAssignments[i] = species;
            bulborbs += species == 4;
            puffstools += species == 9; beetles += species == 17; mamutas += species == 24;
        }
        if (minibossEnemies ? (puffstools != 1 || beetles != 1 || mamutas != 1) : bulborbs != 9) fail("invalid enemy slot species totals");
        slotEnemies = true;
        input >> end;
    }
    if (end == "ENEMY_GROUPS") {
        std::string catalog; unsigned count;
        if (!slotEnemies || !(input >> catalog >> count) || catalog != randomizerSpawnCatalogHash || count != 12)
            fail("incompatible enemy group catalog");
        for (unsigned i=0; i<12; ++i) {
            unsigned uid, species;
            if (!(input >> uid >> species) || uid != randomizerGroupSlots[i] ||
                (randomizerGroupOriginals[i] == 3 || randomizerGroupOriginals[i] == 31 ? species != 3 && species != 31 : species != 18 && species != 19))
                fail("invalid enemy group assignment");
            groupAssignments[i] = species;
        }
        groupEnemies = true;
        input >> end;
    }
    if (end == "PURPLE") {
        unsigned version;
        if (!p2EnemyBridge || !(input >> version) || version != 1) fail("Purple requires P2 campaign bridge version 1");
        purpleCampaign = true;
        input >> end;
    }
    if (end == "CAPTAINS") {
        std::string count;
        if (!p2EnemyBridge || !(input >> count) || count != "2")
            fail("two captains require P2 campaign bridge and count 2");
        secondCaptain = true;
        input >> end;
    }
    if (end != "END") fail("unsupported or malformed bootstrap");
    std::string extra;
    if (input >> extra) fail("trailing bootstrap data");
    directory = std::filesystem::absolute(bootstrap).parent_path();
    campaignDirectory = directory.parent_path().parent_path() / "campaign";
    saveRoot = (campaignDirectory / "card").generic_string();
    if (std::filesystem::exists(directory / "hello.txt") || std::filesystem::exists(directory / "checks.txt"))
        fail("run directory already used; launch a new session run");
    // Consumption belongs to the saved world, not to the latest abandoned day.
    benefitJournal = directory / "benefits-used.txt";
    // Netplay M4 lane B2 (issue #885): in netplay join mode only, a stale
    // local checkpoint (foreign fingerprint, damaged or badly named) is not
    // fatal: the host's checkpoint replaces it during the handshake's
    // transfer phase, so it is set aside (never deleted) and the joiner
    // continues as "none". The host, and every non-netplay run, keep the
    // historical fatal behaviour below.
    if (netplay_join_mode()) set_aside_stale_checkpoint();
    loadCampaignCheckpoint();
    if (campaignResumed && netplay_session()) {
        std::printf("[Pikmin Randomizer] CAMPAIGN_RESUMED generation=%llu\n", campaignGeneration);
        std::fflush(stdout);
    }
    enabled = true;
#if PIKI_NETPLAY_BUILD
    // Netplay launch lane (issue #887): a one-command netplay session has no
    // Archipelago, so the launcher asks for a static ready state next to its
    // fresh run bootstrap: ready, no repairs, the run_pair.py unlock mask
    // (127, capped to the schema), no Flarlic, no checks, and zero for every
    // optional section this bootstrap enables. Written in this seed's own
    // format, so any bootstrap the launcher accepts gets a valid state.
    if (pc_netplay_launch_wants_local_state() && !std::filesystem::exists(directory / "state.txt")) {
        const unsigned maxUnlocks = schema >= 5 ? 255u : schema == 4 ? 127u : schema == 3 ? 63u : 31u;
        std::ostringstream line;
        line << "PIKMIN_STATE " << schema << ' ' << token << " 1 0 " << std::min(127u, maxUnlocks);
        if (schema >= 2) line << " 0";
        line << (schema >= 8 ? " CHECKS 0" : " 0");
        if (progressiveStats) { line << " UPGRADES"; for (int i = 0; i < 12; ++i) line << " 0"; }
        if (benefitItems) {
            line << " BENEFITS";
            const int kinds = prereleaseTraps ? 9 : proggTraps ? 8 : bombTraps ? 7 : bombDeliveries ? 6 : 5;
            for (int i = 0; i < kinds; ++i) line << " 0";
        }
        if (maturityItems) line << " MATURITY 0 0 0";
        if (dayLengthItems) line << " DAYLENGTH 0";
        if (whistlePluckItem) line << " WHISTLEPLUCK 0";
        if (emperorGoal) line << " EMPEROR 0";
        if (deathLinkUnit) line << " DEATHLINK 0";
        line << " END\n";
        std::ofstream state(directory / "state.txt");
        state << line.str();
        state.close();
        if (!state) fail("cannot write the netplay launcher's state.txt");
        std::printf("[Pikmin Randomizer] netplay launcher state (no Archipelago): %s", line.str().c_str());
    }
#endif
    pc_randomizer_update(); // Validate initial state before creating a handshake.
    std::ofstream hello(directory / "hello.tmp");
    hello << "PIKMIN_HELLO " << schema << ' ' << token << ' ' << fingerprint
          << " identity-placement-v1 " << (schema >= 3 ? "random-start-v1" : "foh-day2-v1") << " repair-goal-v1 repeat-day29-v1";
    if (schema >= 2) hello << (schema >= 7 ? " flarlic-v1 exploration-v1" : " flarlic-v1 population-v1 bestiary-v1 exploration-v1");
    if (schema >= 4) hello << " starting-color-v1";
    if (schema >= 5) hello << " all-areas-v1";
    if (schema >= 6) hello << " enemy-families-v1";
    if (schema >= 7) hello << " total-population-v1 corpse-delivery-v1";
    if (permanentChecks) hello << " permanent-checks-v1";
    if (schema >= 8) hello << " check-set-v1";
    if (schema >= 9) hello << (noExploration ? " bestiary-v2 no-exploration-v1" : " bestiary-v2 landing-only-v1");
    if (colorPopulation) hello << " color-population-v1";
    if (compactPopulation) hello << " compact-population-v1";
    if (configuredFlarlic) hello << " starting-flarlic-v1";
    if (configuredStats) hello << (balancedStats ? " color-stats-v3" : wideStats ? " color-stats-v2" : " color-stats-v1");
    if (progressiveStats) hello << (doubledStats ? " progressive-color-stats-v2" : " progressive-color-stats-v1");
    if (benefitItems) hello << " benefit-items-v1";
    if (combinedCaptain) hello << " combined-captain-v1";
    if (bombDeliveries) hello << " bomb-delivery-v1";
    if (bombTraps) hello << " bomb-ambush-v1";
    if (proggTraps) hello << " progg-ambush-v1";
    if (prereleaseTraps) hello << " prerelease-trap-v1";
    if (maturityItems) hello << " progressive-maturity-v1";
    if (dayLengthItems) hello << " progressive-day-length-v1";
    if (whistlePluckItem) hello << " whistle-pluck-item-v1";
    if (slotEnemies) hello << " enemy-slots-v1";
    if (groupEnemies) hello << " enemy-groups-v1";
    if (campaignEnemies) hello << " enemy-campaign-v1";
    if (minibossEnemies) hello << " miniboss-slots-v1";
    if (emperorGoal) hello << " emperor-goal-v1";
    if (deathLinkUnit) hello << " death-link-v1";
    if (p2EnemyBridge) hello << " p2-enemy-bridge-v1";
    if (p2ProxyTier) hello << " p2-proxy-tier-v1";
    if (!resolvedCheckNames.empty()) hello << " resolved-enemy-checks-v1";
    if (secondCaptain) hello << " p2-second-captain-v1";
    hello << " END\n";
    hello.close();
    if (!hello) fail("cannot write native handshake");
    std::filesystem::rename(directory / "hello.tmp", directory / "hello.txt");
    std::printf("[Pikmin Randomizer] initialized; identity placements, 25 repair goal\n");
    return true;
}

namespace {
// B1 mirror ledger, host I/O side: the runner's session.json at
// directory/../../session.json (root session.py, json.dumps(indent=2)) feeds
// kBulkMirrorLedger messages with every receipt from ledgerSent onward. The
// mirror is never sim state: nothing here is ever fatal.
//
// Fix round 1 (review B1-C5 / R2 / B1-C6 / R7):
// * ledger_start runs once, at session start (before any Advance, so this
//   run's deaths.txt is still empty and session.json's pikmin_deaths cannot
//   include any of this run's deaths). It fixes deathsBase and ALWAYS sends
//   one message, so the client never has to guess between "no ledger" and
//   "ledger not arrived yet": base 0 without session.json; the file's
//   pikmin_deaths when it reads; kLedgerBaseUnknown when it exists but stays
//   unreadable over 10 attempts 10 ms apart (the client then writes no DEATHS
//   lines, never a wrong absolute total).
// * ledger_poll runs on every stream-host poll turn: whenever session.json's
//   fine stamp changes it re-reads the file and sends the new receipts, so a
//   receipt that leaves state.txt unchanged still reaches the mirror. A file
//   locked mid-replace is retried next turn; a malformed one is logged and
//   skipped until its next rewrite. deathsBase never changes after start.
// Ledger messages still queued in the session (or in flight on the bulk
// channel) when the process exits are lost; the next session re-sends from
// index 0 and the client's RECEIVED sequencer ignores what it already wrote.
std::filesystem::path ledger_path() {
    return directory.parent_path().parent_path() / "session.json";
}
// 0 = no session.json, 1 = parsed into `out`, 2 = cannot open (transient),
// 3 = malformed or too large (`reason` says why).
int ledger_read(pc_rand_outbox::SessionLedger& out, std::string& reason) {
    std::error_code ec;
    const std::filesystem::path path = ledger_path();
    if (!std::filesystem::exists(path, ec)) return 0;
    std::string text;
    FILE* file = std::fopen(path.string().c_str(), "rb");
    if (!file) { reason = "cannot open"; return 2; }
    char buf[65536];
    size_t n = 0;
    bool tooBig = false;
    while ((n = std::fread(buf, 1, sizeof(buf), file)) > 0) {
        if (text.size() + n > pc_rand_outbox::kMaxSessionJson) { tooBig = true; break; }
        text.append(buf, n);
    }
    std::fclose(file);
    if (tooBig) { reason = "too large"; return 3; }
    out = pc_rand_outbox::SessionLedger();
    if (!pc_rand_outbox::scan_session_json(text.data(), text.size(), out, reason)) return 3;
    return 1;
}
void ledger_send_from(const pc_rand_outbox::SessionLedger& ledger, bool always) {
    if (ledger.received.size() < ledgerSent) {
        std::printf("[netplay] mirror ledger: session.json received shrank (%zu < %zu); ignored\n",
                    ledger.received.size(), ledgerSent);
        std::fflush(stdout);
        return;
    }
    if (!always && ledger.received.size() == ledgerSent) return;
    do {
        const size_t count = std::min<size_t>(pc_rand_outbox::kLedgerMaxCount, ledger.received.size() - ledgerSent);
        const std::vector<uint8_t> msg = pc_rand_outbox::encode_ledger(ledgerDeathsBase, (uint32_t)ledgerSent,
            count ? ledger.received.data() + ledgerSent : nullptr, (uint32_t)count);
        pc_netplay_mirror_ledger_send(msg.data(), msg.size());
        std::printf("[netplay] mirror ledger: sent deathsBase=%u first=%zu count=%zu\n",
                    ledgerDeathsBase, ledgerSent, count);
        ledgerSent += count;
    } while (ledgerSent < ledger.received.size());
    std::fflush(stdout);
}
void ledger_start() {
    if (ledgerStarted || pc_netplay_mirror_ledger_send == nullptr || directory.empty()) return;
    ledgerStarted = true;
    pc_rand_outbox::SessionLedger ledger;
    std::string reason;
    uint64_t fine = 0;
    bool haveFine = pc_rand_outbox::file_write_stamp(ledger_path(), &fine);
    int got = ledger_read(ledger, reason);
    for (int attempt = 1; (got == 2 || got == 3) && attempt < 10; ++attempt) {
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
        haveFine = pc_rand_outbox::file_write_stamp(ledger_path(), &fine);
        got = ledger_read(ledger, reason);
    }
    if (got == 1) {
        ledgerDeathsBase = ledger.pikminDeaths;
        if (haveFine) { ledgerFineStamp = fine; ledgerHaveStamp = true; }
        std::printf("[netplay] mirror ledger: session start deathsBase=%u received=%zu\n",
                    ledgerDeathsBase, ledger.received.size());
        ledger_send_from(ledger, true);
        return;
    }
    if (got == 0) {
        ledgerDeathsBase = 0;
        std::printf("[netplay] mirror ledger: no session.json at session start (deathsBase 0, no RECEIVED yet)\n");
    } else {
        ledgerDeathsBase = pc_rand_outbox::kLedgerBaseUnknown;
        std::printf("[netplay] mirror ledger: session.json unreadable at session start: %s; deathsBase unknown, "
                    "client DEATHS suppressed\n", reason.c_str());
    }
    ledger_send_from(pc_rand_outbox::SessionLedger(), true);
}
void ledger_poll() {
    if (!ledgerStarted || pc_netplay_mirror_ledger_send == nullptr || directory.empty()) return;
    uint64_t fine = 0;
    if (!pc_rand_outbox::file_write_stamp(ledger_path(), &fine)) return; // absent: nothing new
    if (ledgerHaveStamp && fine == ledgerFineStamp) return;
    pc_rand_outbox::SessionLedger ledger;
    std::string reason;
    const int got = ledger_read(ledger, reason);
    if (got == 2) return; // locked mid-replace: retry next turn
    ledgerFineStamp = fine;
    ledgerHaveStamp = true;
    if (got == 3) {
        std::printf("[netplay] mirror ledger: session.json unreadable: %s\n", reason.c_str());
        std::fflush(stdout);
        return;
    }
    if (got == 1) ledger_send_from(ledger, false);
}
// Stream host, after a successful parse: link liveness, publish on content
// change only (the run_pair refresher rewrites state.txt every 0.1 s with
// identical bytes, and a rewrite alone must not bump the generation: each
// generation costs 16 submits). While a HOLD is requested or in progress
// nothing is published here; the RESUME snapshot
// (pc_randomizer_resume_snapshot) carries the latest content with a fresh
// generation instead.
void stream_host_take(const ParsedRand& parsed) {
    linkStateOk = true;
    linkReady = parsed.ready != 0;
    lastFresh = std::chrono::steady_clock::now();
    linkFreshAt = lastFresh;
    pc_randstate::PcRandState st;
    net_from_parsed(parsed, 0, st);
    const bool holding = pc_netplay_hold_active != nullptr && pc_netplay_hold_active();
    if (holding || (sHavePublished && pc_randstate::payload_equal(st, sLastPublished))) return;
    if (++sNetGen == 0) fail("randomizer snapshot generation wrapped");
    st.gen = sNetGen; // first published generation is 1
    sLastPublished = st;
    sHavePublished = true;
    if (pc_netplay_randstate_publish != nullptr) pc_netplay_randstate_publish(st);
}
} // namespace

void pc_randomizer_update() {
    if (!enabled) return;
    // Netplay M4 lane A (issue #885): when the session is active and the
    // external-state stream is enabled, file polling changes meaning. The
    // host I/O side polls state.txt exactly as today but never applies: on
    // content change it bumps `gen` and hands a fresh PcRandState to the
    // session, which streams it to both peers for same-tick apply. The
    // client never reads state.txt: its state comes only from the stream.
    // With the stream disabled (or no session), the historical path below
    // runs byte-identically through the shared apply_parsed().
    const bool netActive = pc_netplay_session_active != nullptr && pc_netplay_session_active();
    const bool stream = netActive && pc_netplay_randstate_stream_enabled != nullptr
        && pc_netplay_randstate_stream_enabled();
    const bool isHost = !stream || pc_netplay_is_host == nullptr || pc_netplay_is_host();
    if (stream) require_net_state_schema();
    if (stream && !isHost) return; // client: stream only
    if (stream) {
        // B1: the stream host detects every rewrite with the fine stamp, so
        // changes inside one second are never coalesced or lost. A failed
        // stat (missing, or a transient delete-pending / AV lock) changes
        // nothing: liveness ages out through the 3 s freshness window
        // (fix round 1, B1-C3). The runner's session.json is polled on the
        // same turn (B1-C6).
        ledger_poll();
        uint64_t fine = 0;
        if (!pc_rand_outbox::file_write_stamp(directory / "state.txt", &fine)) return;
        if (haveFineStamp && fine == lastFineStamp) return;
        std::ifstream input(directory / "state.txt");
        if (!input.is_open()) return; // replace in progress: retry next turn
        ParsedRand parsed;
        parse_state_stream(input, parsed); // fail-closed, exactly as before
        lastFineStamp = fine;
        haveFineStamp = true;
        stream_host_take(parsed);
        return;
    }
    std::error_code error;
    const auto stamp = std::filesystem::last_write_time(directory / "state.txt", error);
    // Legacy (no stream) poll from here on. The stream host above never
    // mutates sim-visible state (not even ready=false on errors): the host
    // sim changes only through stream applies, so both peers stay
    // identical; its poll feeds the link liveness (pc_randomizer_link_live)
    // that drives the synchronized HOLD/RESUME instead.
    if (error) { ready = false; return; }
    if (stamp == lastStamp) {
        if (std::chrono::steady_clock::now() - lastFresh > std::chrono::seconds(3)) ready = false;
        return;
    }
    std::ifstream input(directory / "state.txt");
    // Windows may briefly deny opening a file being atomically replaced.
    // Pause and retry; an opened but malformed record still fails closed.
    if (!input.is_open()) { ready = false; return; }
    if (thelynk) {
        updateTheLynk(input);
        lastStamp = stamp; lastFresh = std::chrono::steady_clock::now();
        return;
    }
    std::string magic, session, end, extra;
    unsigned version, newReady, newRepairs, newUnlocks, newFlarlic = 0;
    std::set<unsigned> newChecks;
    bool parsed = bool(input >> magic >> version >> session >> newReady >> newRepairs >> newUnlocks);
    if (parsed && schema >= 2) parsed = bool(input >> newFlarlic);
    if (schema >= 8) {
        std::string marker; unsigned count;
        if (!parsed || !(input >> marker >> count) || marker != "CHECKS" || count > checkCount) fail("invalid check set header");
        for (unsigned i = 0; i < count; ++i) {
            unsigned slot;
            if (!(input >> slot) || slot >= checkCount || !newChecks.insert(slot).second) fail("invalid or duplicate check index");
        }
    } else {
        std::uint64_t mask = 0;
        parsed = parsed && bool(input >> mask);
        if (parsed && mask >= (1ull << checkCount)) fail("invalid legacy check mask");
        for (unsigned i = 0; i < checkCount; ++i) if (mask & (1ull << i)) newChecks.insert(i);
    }
    parsed = parsed && bool(input >> end);
    unsigned newStats[3][4] = {};
    if (progressiveStats) {
        if (!parsed || end != "UPGRADES") fail("missing progressive stat state");
        for (int c = 0; c < 3; ++c) for (int stat = 0; stat < 4; ++stat) {
            if (!(input >> newStats[c][stat]) || newStats[c][stat] > (stat == 0 || stat == 3 ? 2u : 1u) * (doubledStats ? 2u : 1u)
                || newStats[c][stat] < statUpgrades[c][stat]) fail("invalid or retracted stat upgrade");
        }
        parsed = bool(input >> end);
    }
    unsigned newBenefits[9] = {};
    if (benefitItems) {
        if (!parsed || end != "BENEFITS") fail("missing benefit state");
        for (int kind = 0; kind < (prereleaseTraps ? 9 : proggTraps ? 8 : bombTraps ? 7 : bombDeliveries ? 6 : 5); ++kind)
            if (!(input >> newBenefits[kind]) || newBenefits[kind] > (kind < 3 || kind >= 5 ? checkCount : 2u)
                || newBenefits[kind] < benefits[kind] || ((kind < 3 || kind >= 5) && newBenefits[kind] < consumedBenefits[consumedIndex(static_cast<PcBenefit>(kind))]))
                fail("invalid or retracted benefit receipt");
        parsed = bool(input >> end);
    }
    unsigned newMaturity[3] = {};
    if (maturityItems) {
        if (!parsed || end != "MATURITY") fail("missing maturity state");
        for (int c = 0; c < 3; ++c)
            if (!(input >> newMaturity[c]) || newMaturity[c] > 2 || newMaturity[c] < maturity[c]) fail("invalid or retracted maturity");
        parsed = bool(input >> end);
    }
    unsigned newDayLength = 0;
    if (dayLengthItems) {
        if (!parsed || end != "DAYLENGTH" || !(input >> newDayLength) || newDayLength > dayLengthItems || newDayLength < dayLength)
            fail("invalid or retracted day length");
        parsed = bool(input >> end);
    }
    unsigned newWhistlePluck = 0;
    if (whistlePluckItem) {
        if (!parsed || end != "WHISTLEPLUCK" || !(input >> newWhistlePluck) || newWhistlePluck > 1 || (whistlePluck && !newWhistlePluck))
            fail("invalid or retracted whistle pluck");
        parsed = bool(input >> end);
    }
    unsigned newEmperor = 0;
    if (emperorGoal) {
        if (!parsed || end != "EMPEROR" || !(input >> newEmperor) || newEmperor > 1 || (newEmperor && newRepairs < 25)) fail("invalid Emperor state");
        parsed = bool(input >> end);
    }
    unsigned newDeathLinks = 0;
    if (deathLinkUnit) {
        if (!parsed || end != "DEATHLINK" || !(input >> newDeathLinks)) fail("invalid DeathLink state");
        parsed = bool(input >> end);
    }
    if (!parsed || magic != "PIKMIN_STATE" || version != schema || session != token || newReady > 1
        || newRepairs > 25 || newUnlocks > (schema >= 5 ? 255u : schema == 4 ? 127u : schema == 3 ? 63u : 31u) || newFlarlic > 10 - startingFlarlic
        || end != "END" || (input >> extra))
        fail("invalid state: identity, version or range mismatch");
    // Inventory is monotonic within this authenticated run.
    if (newRepairs < repairs || (newUnlocks & unlocks) != unlocks || newFlarlic < flarlic)
        fail("state attempted to retract received progression");
    if (progressiveStats) for (int c = 0; c < 3; ++c) for (int stat = 0; stat < 4; ++stat) {
        if (statUpgrades[c][stat] != newStats[c][stat])
            std::printf("[Pikmin Randomizer] STAT_UPGRADE color=%d stat=%d tier=%u\n", c, stat, newStats[c][stat]);
        statUpgrades[c][stat] = newStats[c][stat];
        colorStats[c][stat] = baseColorStats[c][stat] + (stat == 3 ? newStats[c][stat] : 25 * newStats[c][stat]);
    }
    for (int kind = 0; kind < 9; ++kind) benefits[kind] = newBenefits[kind];
    for (int c = 0; c < 3; ++c) {
        if (maturity[c] != newMaturity[c]) std::printf("[Pikmin Randomizer] MATURITY color=%d tier=%u\n", c, newMaturity[c]);
        maturity[c] = newMaturity[c];
    }
    if (dayLength != newDayLength) std::printf("[Pikmin Randomizer] DAY_LENGTH count=%u percent=%u\n", newDayLength, 100 + dayLengthStep * newDayLength);
    dayLength = newDayLength;
    if (!whistlePluck && newWhistlePluck) std::printf("[Pikmin Randomizer] WHISTLE_PLUCK received\n");
    whistlePluck = newWhistlePluck != 0;
    emperorDefeated = emperorDefeated || newEmperor != 0;
    if (deathLinkUnit) {
        if (!deathLinkBaseline) { deathLinksSeen = newDeathLinks; deathLinkBaseline = true; }
        else if (newDeathLinks < deathLinksSeen) fail("state retracted received DeathLinks");
        else {
            deathLinksPending = std::min(3u, deathLinksPending + std::min(3u, newDeathLinks - deathLinksSeen));
            deathLinksSeen = newDeathLinks;
        }
    }
    ready = newReady != 0;
    repairs = newRepairs;
    unlocks = newUnlocks;
    if (flarlic != newFlarlic) std::printf("[Pikmin Randomizer] CAPACITY %u\n", 10 * (startingFlarlic + newFlarlic));
    flarlic = newFlarlic;
    checks.insert(newChecks.begin(), newChecks.end());
    lastStamp = stamp;
    lastFresh = std::chrono::steady_clock::now();
    if (pc_randomizer_goal() && !goalReported) {
        goalReported = true;
        std::puts("[Pikmin Randomizer] GOAL: Seed complete.");
    }
}

// Netplay M4 lane A fix round 1 (M5): force a publish on session activation,
// whatever the stamp says. The boot-time update may have latched lastStamp
// before the session existed (CLI mode), so a runner that rewrites only on
// change would otherwise never stream gen 1. Clearing the stamp makes the
// next update re-read; when the content is new (or nothing was ever
// published) it bumps gen and queues the snapshot before the first submit.
// When the content is unchanged and already queued, this is a no-op.
// B1: returns false only on the stream host when state.txt could not be read
// and parsed by this forced poll (the session then HOLDs from its first
// input, so the neutral gate never waits silently); true otherwise. The
// forced poll also reads the mirror ledger (session start).
// Fix round 1 (B1-C3): a transient open/stat failure is retried up to 10
// times 10 ms apart before the missing-state HOLD is chosen, and the mirror
// ledger's session-start message always goes out (ledger_start).
bool pc_randomizer_force_net_publish() {
    if (!enabled) return true;
    const bool netActive = pc_netplay_session_active != nullptr && pc_netplay_session_active();
    const bool stream = netActive && pc_netplay_randstate_stream_enabled != nullptr
        && pc_netplay_randstate_stream_enabled();
    const bool isHost = !stream || pc_netplay_is_host == nullptr || pc_netplay_is_host();
    if (!stream || !isHost) return true;
    lastStamp = std::filesystem::file_time_type{};
    haveFineStamp = false; // B1: the stream host polls the fine stamp
    linkStateOk = false; // proven again by this poll
    pc_randomizer_update();
    for (int attempt = 1; !linkStateOk && attempt < 10; ++attempt) {
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
        haveFineStamp = false;
        pc_randomizer_update();
    }
    ledger_start();
    return linkStateOk;
}

// B1 host link liveness: state.txt readable and parsed, its ready field 1,
// and its stamp changed within 3 s (the historical staleness threshold).
// Launcher sessions write a static state.txt that is never rewritten and
// have no Archipelago link, so they are always live. Host I/O side only.
bool pc_randomizer_link_live() {
    if (!enabled) return true;
#if PIKI_NETPLAY_BUILD
    if (pc_netplay_launch_wants_local_state()) return true;
#endif
    return linkStateOk && linkReady
        && std::chrono::steady_clock::now() - linkFreshAt <= std::chrono::seconds(3);
}

// B1 RESUME snapshot (host I/O side): a fresh read of state.txt with a new
// generation. Clears the stamp so the next ordinary poll re-reads, records
// the content as published (no duplicate generation afterwards) and
// refreshes the mirror ledger. Returns false when state.txt cannot be read
// now (the session retries on a later turn); a malformed record fails
// closed like every other poll.
bool pc_randomizer_resume_snapshot(pc_randstate::PcRandState* out) {
    if (!enabled || out == nullptr) return false;
    uint64_t fine = 0;
    if (!pc_rand_outbox::file_write_stamp(directory / "state.txt", &fine)) return false;
    std::ifstream input(directory / "state.txt");
    if (!input.is_open()) return false;
    ParsedRand parsed;
    parse_state_stream(input, parsed);
    pc_randstate::PcRandState st;
    net_from_parsed(parsed, 0, st);
    if (++sNetGen == 0) fail("randomizer snapshot generation wrapped");
    st.gen = sNetGen;
    sLastPublished = st;
    sHavePublished = true;
    linkStateOk = true;
    linkReady = parsed.ready != 0;
    lastFineStamp = fine;
    haveFineStamp = true;
    lastFresh = std::chrono::steady_clock::now();
    linkFreshAt = lastFresh;
    ledger_poll();
    *out = st;
    return true;
}

bool pc_randomizer_apply_net_state(const pc_randstate::PcRandState& st) {
    if (!enabled) return false;
    require_net_state_schema();
    if (st.ver != pc_randstate::kVersion || st.mode != (thelynk ? 2 : 1)
        || st.schema != (thelynk ? 1 : schema) || st.features != net_features() || st.checkCount != checkCount)
        fail("net randomizer state differs from authenticated bootstrap");
    // Render the authenticated wire inventory through the same complete parser
    // used by the host. This validates all monotonic/range/consumption rules
    // without a second, weaker client parser. No state is mutated until complete.
    std::ostringstream text;
    if (thelynk) text << "THELYNK_STATE 1 " << token << ' ' << unsigned(st.ready) << ' ' << st.thelynkParts;
    else {
        text << "PIKMIN_STATE " << schema << ' ' << token << ' ' << unsigned(st.ready) << ' '
             << unsigned(st.repairs) << ' ' << unsigned(st.unlocks);
        if (schema >= 2) text << ' ' << unsigned(st.flarlic);
    }
    std::set<unsigned> incoming;
    for (unsigned slot = 0; slot < pc_randstate::kCheckSlots; ++slot)
        if (st.checks[slot / 8] & (1u << (slot % 8))) {
            if (slot >= checkCount) fail("invalid net check index");
            incoming.insert(slot);
        }
    if (thelynk || schema >= 8) {
        text << " CHECKS " << incoming.size();
        for (unsigned slot : incoming) text << ' ' << (thelynk ? thelynkId(slot) : slot);
    } else {
        uint64_t mask = 0; for (unsigned slot : incoming) mask |= uint64_t(1) << slot;
        text << ' ' << mask;
    }
    if (thelynk) {
        text << " BONUSES";
        for (unsigned n : st.thelynkBonuses) text << ' ' << n;
    } else {
        if (progressiveStats) { text << " UPGRADES"; for (unsigned n : st.stats) text << ' ' << n; }
        if (benefitItems) {
            text << " BENEFITS";
            int count = prereleaseTraps ? 9 : proggTraps ? 8 : bombTraps ? 7 : bombDeliveries ? 6 : 5;
            for (int i = 0; i < count; ++i) text << ' ' << st.benefits[i];
        }
        if (maturityItems) { text << " MATURITY"; for (unsigned n : st.maturity) text << ' ' << n; }
        if (dayLengthItems) text << " DAYLENGTH " << unsigned(st.dayLength);
        if (whistlePluckItem) text << " WHISTLEPLUCK " << unsigned(st.whistlePluck);
        if (emperorGoal) text << " EMPEROR " << unsigned(st.emperor);
        if (deathLinkUnit) text << " DEATHLINK " << st.deathLinks;
    }
    text << " END";
    std::istringstream input(text.str()); ParsedRand parsed;
    parse_state_stream(input, parsed);
    pc_randstate::PcRandState canonical; net_from_parsed(parsed, st.gen, canonical);
    // Reject values in disabled/reserved mode fields, rather than ignoring them.
    if (!pc_randstate::payload_equal(st, canonical)) fail("noncanonical net randomizer state");
    apply_parsed(parsed);
    lastFresh = std::chrono::steady_clock::now();
    return true;
}

bool pc_randomizer_get_net_state(pc_randstate::PcRandState* out) {
    if (!enabled || out == nullptr) return false;
    ParsedRand p;
    p.ready = ready; p.repairs = repairs; p.unlocks = unlocks; p.flarlic = flarlic;
    p.emperor = emperorDefeated; p.deathLinks = deathLinksSeen; p.checks = checks;
    p.dayLength = dayLength; p.whistlePluck = whistlePluck; p.thelynkParts = thelynkParts;
    for (int c = 0; c < 3; ++c) {
        p.maturity[c] = maturity[c];
        for (int i = 0; i < 4; ++i) p.stats[c][i] = statUpgrades[c][i];
    }
    for (int i = 0; i < 9; ++i) p.benefits[i] = benefits[i];
    for (int i = 0; i < 18; ++i) p.thelynkBonuses[i] = thelynkBonuses[i];
    net_from_parsed(p, 0, *out); // publisher stamps a positive generation
    return true;
}

uint64_t pc_randomizer_hash() {
    if (!enabled) return 0;
    uint64_t h = 14695981039346656037ULL;
    const auto mix = [&](uint64_t v) {
        for (int i = 0; i < 8; ++i) { h ^= (uint8_t)((v >> (i * 8)) & 0xFF); h *= 1099511628211ULL; }
    };
    mix(thelynk ? 2 : 1); mix(thelynk ? 1 : schema); mix(net_features()); mix(checkCount);
    mix(ready); mix(repairs); mix(unlocks); mix(flarlic); mix(emperorDefeated);
    mix(deathLinksSeen); mix(deathLinksPending); mix(deathsReported);
    mix(checks.size()); for (unsigned slot : checks) mix(slot);
    for (int c = 0; c < 3; ++c) {
        mix(maturity[c]);
        for (int i = 0; i < 4; ++i) mix(statUpgrades[c][i]);
    }
    mix(dayLength); mix(whistlePluck); mix(thelynkParts);
    for (unsigned n : benefits) mix(n);
    for (unsigned n : consumedBenefits) mix(n);
    for (int i = 0; i < 18; ++i) { mix(thelynkBonuses[i]); mix(thelynkUsed[i]); }
    mix(thelynkEnabled.size()); for (unsigned slot : thelynkEnabled) mix(slot);
    for (int color = 0; color < 2; ++color) for (int stage = 0; stage < 3; ++stage)
        mix(p2ship::stock.counts[color][stage]);
    mix(campaignGeneration); mix(campaignResumed);
    return h;
}

bool pc_randomizer_prerelease_traps() { return enabled && prereleaseTraps; }
int pc_randomizer_maturity(int color) {
    return enabled && maturityItems && color >= 0 && color < 3 ? int(maturity[color]) : 0;
}
int pc_randomizer_whistle_pluck() {
    if (!enabled || !whistlePluckItem) return -1;
    return whistlePluck ? 1 : 0;
}
float pc_randomizer_day_length_multiplier() {
    return enabled && dayLengthItems ? 1.0f + 0.01f * float(dayLengthStep * dayLength) : 1.0f;
}
bool pc_randomizer_progg_traps() { return enabled && proggTraps; }
bool pc_randomizer_benefit_pending(PcBenefit kind) {
    return enabled && benefitItems && ready && ((kind >= 0 && kind < 3) || (kind == PC_BENEFIT_BOMBS && bombDeliveries) || (kind == PC_BENEFIT_BOMB_TRAP && bombTraps) || (kind == PC_BENEFIT_PROGG && proggTraps) || (kind == PC_BENEFIT_PRERELEASE && prereleaseTraps)) && benefits[kind] > consumedBenefits[consumedIndex(kind)];
}
bool pc_randomizer_consume_benefit(PcBenefit kind) {
    if (!pc_randomizer_benefit_pending(kind)) return false;
    if (outbox_active()) {
        // B1 outbox mode (issue #885). Both peers consume in the same tick;
        // the host journals the line in pc_randomizer_outbox_flush at the
        // end of this same Advance, i.e. before the next tick runs and
        // before any campaign save (a save happens in a later tick, and the
        // B2 save barrier flushes the outbox before it writes). Persist-
        // before-apply still holds where it matters: if the process dies
        // between this apply and the flush, the unsaved day is lost with it,
        // and consumption belongs to the saved world (consumedBenefits is
        // restored from the campaign checkpoint at relaunch), so the benefit
        // is never granted twice.
        ++consumedBenefits[consumedIndex(kind)];
        std::printf("[Pikmin Randomizer] BENEFIT_USED kind=%d count=%u\n", int(kind), consumedBenefits[consumedIndex(kind)]);
        pc_rand_outbox::Entry e;
        e.kind = pc_rand_outbox::Kind::Benefit;
        e.benefitKind = int(kind);
        e.count = consumedBenefits[consumedIndex(kind)];
        outbox_push(e);
        return true;
    }
    // Persist before applying a non-transactional native effect: never duplicate it on replay.
    FILE* file = std::fopen(benefitJournal.string().c_str(), "a");
    if (!file) fail("cannot open benefit consumption journal");
    bool ok = std::fprintf(file, "%s %d %u\n", fingerprint.c_str(), int(kind), consumedBenefits[consumedIndex(kind)] + 1) > 0 && std::fflush(file) == 0;
#ifdef _WIN32
    ok = ok && _commit(_fileno(file)) == 0;
#else
    ok = ok && fsync(fileno(file)) == 0;
#endif
    if (std::fclose(file) != 0 || !ok) fail("cannot persist benefit consumption");
    ++consumedBenefits[consumedIndex(kind)];
    std::printf("[Pikmin Randomizer] BENEFIT_USED kind=%d count=%u\n", int(kind), consumedBenefits[consumedIndex(kind)]);
    return true;
}
float pc_randomizer_captain_movement_multiplier() {
    return combinedCaptain ? pc_randomizer_benefit_multiplier(PC_BENEFIT_PLUCK) : 1.0f;
}
float pc_randomizer_benefit_multiplier(PcBenefit kind) {
    return enabled && benefitItems && (kind == PC_BENEFIT_WHISTLE || kind == PC_BENEFIT_PLUCK) ? 1.0f + 0.25f * benefits[kind] : 1.0f;
}
bool pc_randomizer_enabled() { return enabled; }
int pc_randomizer_start_stage() { return startStage; }
int pc_randomizer_start_color() { return startColor; }
bool pc_randomizer_spawn_slots() { return enabled && (slotEnemies || campaignEnemies); }
bool pc_randomizer_group_slots() { return enabled && groupEnemies; }
bool pc_randomizer_p2_bridge() { return p2EnemyBridge; }
bool pc_randomizer_p2_proxy_tier() { return p2EnemyBridge && p2ProxyTier; }
unsigned pc_randomizer_p2_source(const char* target) {
    if (!p2EnemyBridge || !target) return 0;
    const auto it = p2Bindings.find(target);
    return it == p2Bindings.end() ? 0 : it->second;
}
unsigned pc_randomizer_p2_binding_count() {
    return p2EnemyBridge ? static_cast<unsigned>(p2Bindings.size()) : 0;
}
bool pc_randomizer_p2_bound(unsigned source_id) {
    if (!p2EnemyBridge || !source_id) return false;
    for (const auto& binding : p2Bindings) if (binding.second == source_id) return true;
    return false;
}
void pc_randomizer_p2_bind_source(const void* tekiview, unsigned sourceId, unsigned generatorUid) {
    if (!tekiview || !sourceId) return;
    if (!randomizerP2IsBindable(sourceId)) {
        std::printf("[Pikmin Randomizer] P2_DELIVERY_BIND_REJECTED source=%u\n", sourceId);
        return;
    }
    p2TekiSources[tekiview] = sourceId;
    p2TekiGeneratorUids[tekiview] = generatorUid;
}
unsigned pc_randomizer_p2_source_for(const void* tekiview) {
    const auto it = p2TekiSources.find(tekiview);
    return it == p2TekiSources.end() ? 0 : it->second;
}
unsigned pc_randomizer_p2_generator_for(const void* tekiview) {
    const auto it = p2TekiGeneratorUids.find(tekiview);
    return it == p2TekiGeneratorUids.end() ? 0 : it->second;
}
void pc_randomizer_p2_forget_source(const void* tekiview) {
    if (!tekiview) return;
    p2TekiSources.erase(tekiview);
    p2TekiGeneratorUids.erase(tekiview);
}
void pc_randomizer_p2_delivery_reset() {
    if (p2DeliveryHost) {
        pc_p2_delivery_host_close(p2DeliveryHost);
        p2DeliveryHost = nullptr;
    }
    p2ReceiptGenerators.clear();
}
bool pc_randomizer_p2_receipt_seen(unsigned generatorUid)
{
    return generatorUid != 0 && p2ReceiptGenerators.count(generatorUid) != 0;
}
bool pc_randomizer_resolved_checks() { return !resolvedCheckNames.empty(); }
namespace {
// Shared body of the corpse delivery and the kill receipt (#1088). `encounter`
// is the durable ledger tag ("corpse" or "kill"); `marker` the log line name.
bool p2SourceReceipt(const void* tekiview, int type, int stage, bool gameplay, const char* encounter,
                     const char* marker);
}
bool pc_randomizer_p2_corpse_delivered(const void* tekiview, int type, int stage, bool gameplay) {
    return p2SourceReceipt(tekiview, type, stage, gameplay, "corpse", "P2_ORDINARY_P2_RECEIPT");
}
bool pc_randomizer_p2_killed(const void* tekiview, int type, int stage, bool gameplay) {
    return p2SourceReceipt(tekiview, type, stage, gameplay, "kill", "P2_KILL_P2_RECEIPT");
}
namespace {
bool p2SourceReceipt(const void* tekiview, int type, int stage, bool gameplay, const char* encounter,
                     const char* marker) {
    if (!enabled || !ready || !gameplay || !tekiview) return false;
    const unsigned sourceId = pc_randomizer_p2_source_for(tekiview);
    if (!sourceId) return false;
    const unsigned generatorUid = pc_randomizer_p2_generator_for(tekiview);
    if (!generatorUid) {
        std::printf("[Pikmin Randomizer] P2_ORDINARY_DELIVERY SKIP source=%u no_generator_uid\n", sourceId);
        pc_randomizer_p2_forget_source(tekiview);
        return false;
    }
    if (!resolvedCheckNames.empty() && p2CheckIndices.count(sourceId)) {
        if (!p2CheckSources[sourceId].count({generatorUid, stage}))
            fail("P2 delivery differs from resolved source catalog");
        // Persist the AP event before the secondary receipt ledger. A runner or
        // game crash between the two writes cannot lose an earned AP check.
        pc_randomizer_check(resolvedCheckNames[p2CheckIndices[sourceId]].c_str());
    }
    if (outbox_active()) {
        // B1 outbox mode: the return value and the receipt set must not
        // depend on host-only ledger I/O (a different sim branch on one
        // peer). Both peers treat a bound source with a generator uid as
        // Granted; the host opens the ledger and delivers at the end of this
        // Advance (an open failure there is fatal, never a silent false).
        // The client never opens the ledger.
        p2ReceiptGenerators.insert(generatorUid);
        // Peer-neutral sim-side line on both peers (fix round 1, R6); the
        // host's P2_ORDINARY_P2_RECEIPT line at flush time is host-only (it
        // reports the ledger's result, which only the host has).
        std::printf("[Pikmin Randomizer] P2_ORDINARY_DELIVERY source=%u type=%d stage=%d generator=%u\n",
            sourceId, type, stage, generatorUid);
        pc_rand_outbox::Entry e;
        e.kind = pc_rand_outbox::Kind::P2Delivery;
        e.p2Source = sourceId;
        e.p2Type = type;
        e.p2Stage = stage;
        e.p2Generator = generatorUid;
        outbox_push(e);
        pc_randomizer_p2_forget_source(tekiview);
        return true;
    }
    // Open the durable ordinary receipt ledger once per process, at a path stable
    // across a save + process restart (the session campaign directory).
    if (!p2DeliveryHost) {
        const std::filesystem::path path = campaignDirectory.empty()
            ? directory / "p2-delivery-receipts.txt"
            : campaignDirectory / "p2-delivery-receipts.txt";
        p2DeliveryHost = pc_p2_delivery_host_open(path.string().c_str());
        if (!p2DeliveryHost) {
            std::printf("[Pikmin Randomizer] P2_ORDINARY_DELIVERY host open failed\n");
            pc_randomizer_p2_forget_source(tekiview);
            return false;
        }
    }
    // `fingerprint` is the seed-manifest-level identity, stable across process
    // restarts of the same seed; `token` is the run-instance identity fallback.
    const std::string& seed = fingerprint.empty() ? token : fingerprint;
    const P2DeliveryHostResult result = pc_p2_delivery_host_deliver(p2DeliveryHost, seed.c_str(), sourceId, type, stage, generatorUid, encounter);
    std::printf("[Pikmin Randomizer] %s seed=%s id=onion:p2:%u:%d generator=%u new=%d\n", marker,
        seed.c_str(), sourceId, stage, generatorUid, int(result == P2DeliveryHostResult::Granted));
    if (result == P2DeliveryHostResult::Granted || result == P2DeliveryHostResult::Duplicate) {
        p2ReceiptGenerators.insert(generatorUid);
    }
    // Single-use: consume the binding so the address can be safely recycled.
    pc_randomizer_p2_forget_source(tekiview);
    return true;
}
}
unsigned pc_randomizer_p2_source_for_id(unsigned long generator_id) {
    if (!p2EnemyBridge || !generator_id) return 0;
    char target[24];
    std::snprintf(target, sizeof(target), "%lu", generator_id);
    return pc_randomizer_p2_source(target);
}
unsigned pc_randomizer_generator_id(const void* generator) {
    auto it = generatorIds.find(generator);
    return it == generatorIds.end() ? 0 : it->second;
}
void pc_randomizer_set_generator_id(const void* generator, unsigned uid) {
    if (!uid) { generatorIds.erase(generator); return; }
    // Populate under the P2 enemy bridge too: ENEMY_P2 forbids the P1 slot
    // layouts, so pc_randomizer_spawn_slots() is false and generatorIds would
    // otherwise stay empty (the seed bindings key on the spawn-slot uid).
    if (!pc_randomizer_spawn_slots() && !pc_randomizer_p2_bridge()) return;
    for (const auto& row : randomizerSpawnSlots) if (row.uid == uid) {
        generatorIds[generator] = uid; return;
    }
    fail("unknown saved generator ID");
}
void pc_randomizer_dev_set_generator_id(const void* generator, unsigned uid) {
    if (!generator || !uid) return;
    generatorIds[generator] = uid;
}
unsigned pc_randomizer_placement_slot_uid(unsigned sourceId70) {
    // Lane-04 catalog join: generator _70 -> placement slot uid (crc32), read
    // from the staged p2-placement-slots.txt sidecar. Only consulted under the
    // P2 bridge for room-course generators absent from randomizerSpawnSlots.
    static std::unordered_map<unsigned, unsigned> slotBy70;
    static bool loaded = false;
    if (!loaded) {
        loaded = true;
        std::ifstream sidecar("p2-placement-slots.txt");
        if (sidecar) {
            std::string magic;
            if ((sidecar >> magic) && magic == "P2_PLACEMENT_SLOTS_1") {
                unsigned generator = 0, slot = 0;
                while (sidecar >> generator >> slot) slotBy70[generator] = slot;
            }
        }
    }
    const auto it = slotBy70.find(sourceId70);
    return it == slotBy70.end() ? 0 : it->second;
}

void pc_randomizer_bind_generator(const void* generator, int stage, const char* file, int offset, unsigned sourceId70) {
    pc_randomizer_set_generator_id(generator, 0);
    if ((!pc_randomizer_spawn_slots() && !pc_randomizer_p2_bridge()) || !file) return;
    for (const auto& row : randomizerSpawnSlots)
        if (row.stage == stage && row.offset == offset && !std::strcmp(row.file, file)) {
            pc_randomizer_set_generator_id(generator, row.uid); return;
        }
    if (pc_randomizer_p2_bridge() && sourceId70) {
        const unsigned uid = pc_randomizer_placement_slot_uid(sourceId70);
        if (uid) pc_randomizer_set_generator_id(generator, uid);
    }
}

bool pc_randomizer_p2_room_bootstrap(const char* path) {
    // Feed the room preview the seed's ENEMY_P2 bindings without a full session:
    // a full session sets `enabled` (which holds/freezes the preview) but the
    // bridge only needs p2Bindings + p2EnemyBridge to resolve room generators.
    std::ifstream input(path);
    std::string word;
    while (input >> word) {
        if (word != "ENEMY_P2") continue;
        unsigned protocol, count; std::string revision;
        if (!(input >> protocol >> revision >> count) || protocol != 1
            || revision != randomizerP2RosterRevision || count == 0 || count > kP2MaxBindings)
            fail("incompatible P2 enemy roster or protocol version");
        for (unsigned i = 0; i < count; ++i) {
            std::string target; unsigned sourceId;
            if (!(input >> target >> sourceId) || target.empty() || target.size() > 64
                || !randomizerP2IsBindable(sourceId) || !p2Bindings.emplace(target, sourceId).second)
                fail("invalid P2 enemy binding");
        }
        // Finding 4: skip the optional P2_PROXY_TIER pair the same way as the
        // full-session reader so a tier seed's bootstrap parses here too. The
        // room preview never takes the campaign tier; the flag is left alone.
        std::string tierWord;
        if (input >> tierWord) {
            if (tierWord == "P2_PROXY_TIER") {
                unsigned tier = 0;
                if (!(input >> tier) || tier != 1) fail("invalid P2 proxy tier");
            }
        }
        p2EnemyBridge = true;
        return true;
    }
    return false;
}
int pc_randomizer_enemy_for_generator(int original, bool protectedSpawn, const void* generator) {
    if (pc_randomizer_p2_bridge()) {
        const unsigned source = pc_randomizer_p2_source_for_id(pc_randomizer_generator_id(generator));
        if (protectedSpawn || p2campaign::hasStaticHost(source))
            return p2campaign::hostType(source, original, protectedSpawn);
        const int proxy = pc_p2_proxy_host(source);
        if (proxy >= 0) return proxy;
        return original;
    }
    if (!pc_randomizer_spawn_slots()) return pc_randomizer_enemy_type(original, protectedSpawn);
    if (campaignEnemies) {
        const unsigned uid = pc_randomizer_generator_id(generator);
        for (unsigned i=0; i<72; ++i) if (randomizerCampaignSlots[i].uid == uid) {
            if (protectedSpawn || randomizerCampaignSlots[i].original != original) fail("campaign enemy source changed");
            return campaignAssignments[i];
        }
        // Bosses, hazards, named drops and unlisted special personalities stay pinned.
        return original;
    }
    if (groupEnemies && (original == 3 || original == 31 || original == 18 || original == 19)) {
        if (protectedSpawn) return original;
        unsigned uid = pc_randomizer_generator_id(generator);
        for (unsigned i=0; i<12; ++i) if (randomizerGroupSlots[i] == uid) {
            if (randomizerGroupOriginals[i] != original) fail("enemy group source changed");
            return groupAssignments[i];
        }
        fail("unprotected family group has no supported generator ID");
    }
    if (original != 4 && original != 32) return original;
    unsigned uid = pc_randomizer_generator_id(generator);
    for (unsigned i = 0; i < 15; ++i) if (randomizerAdultSlots[i] == uid) {
        for (const auto& row : randomizerSpawnSlots) if (row.uid == uid && (row.species != original || protectedSpawn))
            fail("enemy slot source changed");
        return adultAssignments[i];
    }
    fail("adult enemy has no supported generator ID");
}
void pc_randomizer_bad_spawn_cache() { fail("incompatible enemy slot cache record"); }
bool pc_randomizer_enemy_shuffle() { return enabled && schema >= 6 && (enemyMask != 0 || slotEnemies || campaignEnemies); }
int pc_randomizer_enemy_type(int original, bool protectedSpawn) {
    if (!pc_randomizer_enemy_shuffle() || protectedSpawn) return original;
    const int pairs[3][2] = {{3, 31}, {4, 32}, {18, 19}};
    for (unsigned i = 0; i < 3; ++i) if (enemyMask & (1u << i)) {
        if (original == pairs[i][0]) return pairs[i][1];
        if (original == pairs[i][1]) return pairs[i][0];
    }
    return original;
}
bool pc_randomizer_ready() { return ready; }
bool pc_randomizer_goal() { return enabled && repairs == (thelynk ? 30u : 25u) && (!emperorGoal || emperorDefeated); }
bool pc_randomizer_emperor_available() { return !enabled || !emperorGoal || (ready && repairs == 25); }
void pc_randomizer_emperor_defeated() {
    if (!enabled || !emperorGoal || !ready || repairs != 25 || emperorDefeated) return;
    if (outbox_active()) {
        // B1 outbox mode: latch and report on both peers now; the host
        // writes emperor.tmp -> emperor.txt at the end of this Advance.
        emperorDefeated = true;
        std::puts("[Pikmin Randomizer] GOAL: Emperor Bulblax defeated!");
        pc_rand_outbox::Entry e;
        e.kind = pc_rand_outbox::Kind::Emperor;
        outbox_push(e);
        return;
    }
    FILE* file = std::fopen((directory / "emperor.tmp").string().c_str(), "w");
    if (!file) fail("cannot persist Emperor defeat");
    bool ok = std::fprintf(file, "EMPEROR_DEFEATED %s %s\n", token.c_str(), fingerprint.c_str()) > 0 && std::fflush(file) == 0;
#ifdef _WIN32
    ok = ok && _commit(_fileno(file)) == 0;
#else
    ok = ok && fsync(fileno(file)) == 0;
#endif
    ok = std::fclose(file) == 0 && ok;
    if (!ok) fail("Emperor defeat persistence failed");
    std::filesystem::rename(directory / "emperor.tmp", directory / "emperor.txt");
    emperorDefeated = true;
    std::puts("[Pikmin Randomizer] GOAL: Emperor Bulblax defeated!");
}
int pc_randomizer_deathlink_casualties() {
    return enabled && deathLinkUnit && ready && deathLinksPending ? int(deathLinkUnit) : 0;
}
#if PIKI_NETPLAY_BUILD
// B1 TEST-ONLY knob (netplay builds only): PIKMIN_NETPLAY_TEST_DEATHLINK_AS_ORDINARY=1
// makes deathlink_induce a no-op, so DeathLink kills are journaled as
// ordinary deaths (exact-count evidence). It changes sim state
// (deathsReported is hashed), so the session hashes it into the handshake
// config and run_pair scrubs it. Fix round 1 (B1-C8 / R5): it is honoured
// only while the outbox is active (a netplay session with the stream on),
// so a netplay build running solo or AP behaves as without the variable
// (no DeathLink feedback loop through deaths.txt); logged once when honoured.
bool pc_randomizer_test_deathlink_as_ordinary() {
    static int cached = -1;
    if (cached < 0) {
        const char* v = std::getenv("PIKMIN_NETPLAY_TEST_DEATHLINK_AS_ORDINARY");
        cached = (v && v[0] == '1' && v[1] == '\0') ? 1 : 0;
    }
    return cached == 1;
}
namespace {
bool test_deathlink_as_ordinary_now() {
    if (!pc_randomizer_test_deathlink_as_ordinary() || !outbox_active()) return false;
    static bool logged = false;
    if (!logged) {
        logged = true;
        std::printf("[netplay] TEST knob PIKMIN_NETPLAY_TEST_DEATHLINK_AS_ORDINARY honoured: DeathLink kills count as ordinary deaths\n");
    }
    return true;
}
} // namespace
#endif
void pc_randomizer_deathlink_induce(const void* piki) {
#if PIKI_NETPLAY_BUILD
    if (test_deathlink_as_ordinary_now()) return;
#endif
    if (piki) inducedDeaths.insert(piki);
}
void pc_randomizer_deathlink_consume(int killed) {
    if (!deathLinksPending) return;
    // Fewer than a full unit on the field is not banked against future Pikmin.
    --deathLinksPending;
    std::printf("[Pikmin Randomizer] DEATHLINK_APPLIED killed=%d pending=%u\n", killed, deathLinksPending);
}
void pc_randomizer_observe_pikmin_death(const void* piki) {
    if (!enabled || !deathLinkUnit) return;
    if (outbox_active()) {
        // B1 outbox mode: count on both peers now, visible in both logs; the
        // host appends the running total to deaths.txt at the end of this
        // Advance and the client mirrors it as DEATHS.
        if (piki && inducedDeaths.erase(piki)) {
            std::printf("[Pikmin Randomizer] PIKMIN_DEATH induced\n");
            return;
        }
        ++deathsReported;
        std::printf("[Pikmin Randomizer] PIKMIN_DEATH ordinary total=%u\n", deathsReported);
        pc_rand_outbox::Entry e;
        e.kind = pc_rand_outbox::Kind::Death;
        e.total = deathsReported;
        outbox_push(e);
        return;
    }
    if (piki && inducedDeaths.erase(piki)) return; // Induced casualties never feed the outgoing threshold.
    FILE* file = std::fopen((directory / "deaths.txt").string().c_str(), "a");
    if (!file) fail("cannot open Pikmin death journal");
    // Each line is this run's running total; the runner credits the difference.
    bool ok = std::fprintf(file, "%u\n", deathsReported + 1) > 0 && std::fflush(file) == 0;
    ok = std::fclose(file) == 0 && ok;
    if (!ok) fail("Pikmin death journal write failed");
    ++deathsReported;
}
int pc_randomizer_repairs() { return (int)repairs; }
const char* pc_randomizer_save_root() { return saveRoot.c_str(); }
int pc_randomizer_next_day(int day) {
    if (pc_randomizer_thelynk()) return day >= 29 ? 2 : day + 1;
    return enabled && day >= 28 ? 29 : day + 1;
}
bool pc_randomizer_has(const char* name) {
    if (!enabled || !name) return false;
    if (thelynk) {
        if (!std::strcmp(name, "Pikmin: Impact Site Access") || !std::strcmp(name, "Red Onion")) return true;
        if (!std::strcmp(name, "Pikmin Access") || !std::strcmp(name, "Pikmin: Forest of Hope Access") || !std::strcmp(name, "Yellow Onion")) return repairs >= 1;
        if (!std::strcmp(name, "Pikmin: Forest Navel Access") || !std::strcmp(name, "Blue Onion")) return repairs >= 5;
        if (!std::strcmp(name, "Pikmin: Distant Spring Access")) return repairs >= 12;
        if (!std::strcmp(name, "Pikmin: Final Trial Access")) return repairs >= 29;
        return false;
    }
    if (!std::strcmp(name, "Red Onion")) return startColor == 1 || (unlocks & 64u);
    if (startColor == 0 && !std::strcmp(name, "Blue Onion")) return true;
    if (startColor == 2 && !std::strcmp(name, "Yellow Onion")) return true;
    if (!std::strcmp(name, "Pikmin Access")) return true;
    if (!std::strcmp(name, "Pikmin: Forest of Hope Access")) return startStage == 1 || (unlocks & 32u);
    if (startStage == 2 && !std::strcmp(name, "Pikmin: Forest Navel Access")) return true;
    if (startStage == 3 && !std::strcmp(name, "Pikmin: Distant Spring Access")) return true;
    if (startStage == 4 && !std::strcmp(name, "Pikmin: Final Trial Access")) return true;
    if (!std::strcmp(name, "Pikmin: Impact Site Access")) return schema >= 5 && (startStage == 0 || (unlocks & 128u));
    for (unsigned i = 0; i < 5; ++i)
        if (!std::strcmp(name, items[i])) return (unlocks & (1u << i)) != 0;
    return false;
}
bool pc_randomizer_checked(const char* name) {
    const int slot = index(name);
    if (thelynk && slot >= 0 && !thelynkEnabled.count(unsigned(slot))) return false;
    return slot >= 0 && checks.count(unsigned(slot)) != 0;
}
void pc_randomizer_check(const char* name) {
    if (!enabled || !ready) return;
    const int slot = index(name);
    if (thelynk && slot >= 0 && !thelynkEnabled.count(unsigned(slot))) return;
    if (slot < 0) {
        // Main Engine is the synthetic tutorial completion, not a standalone check.
        if (name && !std::strcmp(name, "Pikmin: Main Engine")) return;
        if (!resolvedCheckNames.empty() && name && std::strstr(name, "Bestiary:") == name) {
            for (const auto& original : legacyCheckNames)
                if (original == name) return; // a removed P1 species has no AP location
        }
        fail("unknown native collection identity");
    }
    if (checks.count(unsigned(slot))) return;
    if (outbox_active()) {
        // B1 outbox mode: the sim set changes on both peers now; the host
        // appends the slot to checks.txt at the end of this Advance (once,
        // via checksJournaled) and the client mirrors it as CHECKED.
        checks.insert(unsigned(slot));
        std::printf("[Pikmin Randomizer] CHECK %d %s\n", slot, name);
        pc_rand_outbox::Entry e;
        e.kind = pc_rand_outbox::Kind::Check;
        e.slot = unsigned(slot);
        outbox_push(e);
        return;
    }
    FILE* file = std::fopen((directory / "checks.txt").string().c_str(), "a");
    if (!file) fail("cannot persist native collection");
    bool ok = std::fprintf(file, "%u\n", thelynk ? thelynkId(unsigned(slot)) : unsigned(slot)) > 0 && std::fflush(file) == 0;
#ifdef _WIN32
    ok = ok && _commit(_fileno(file)) == 0;
#else
    ok = ok && fsync(fileno(file)) == 0;
#endif
    ok = std::fclose(file) == 0 && ok;
    if (!ok) fail("native collection persistence failed");
    checks.insert(unsigned(slot));
    std::printf("[Pikmin Randomizer] CHECK %d %s\n", slot, name);
}

bool pc_randomizer_expanded() { return enabled && !thelynk && schema >= 2; }
bool pc_randomizer_color_stats() { return enabled && (configuredStats || progressiveStats); }
namespace {
// bot-v4 power mode (TEST-ONLY): PIKMIN_RANDOMIZER_AUTOPLAY_POWER scales Pikmin
// attack power through the EXISTING color-multiplier lever. Off by default and
// ONLY meaningful when the autoplay gate is already on; inert in normal play
// (autoplay gate closed => normal 1.0x path, no matter what POWER is set to).
// A numeric POWER value configures the multiplier, otherwise x10.
bool autoplayPowerOn()
{
    const char* gate = std::getenv("PIKMIN_RANDOMIZER_AUTOPLAY");
    if (!gate || !gate[0] || !std::strcmp(gate, "0")) return false;
    const char* v = std::getenv("PIKMIN_RANDOMIZER_AUTOPLAY_POWER");
    return v && v[0] && std::strcmp(v, "0") != 0;
}
float autoplayPowerDamageMult() {
    if (!autoplayPowerOn()) return 1.0f;
    const char* v = std::getenv("PIKMIN_RANDOMIZER_AUTOPLAY_POWER");
    char* end = nullptr;
    const double d = std::strtod(v, &end);
    if (end && end != v && *end == 0 && d > 0.0 && d < 1000000.0) return float(d);
    return 10.0f;
}
}
float pc_randomizer_color_multiplier(int color, PcPikminStat stat) {
    if (stat == PC_PIKI_DAMAGE) {
        const float power = autoplayPowerDamageMult();
        if (power != 1.0f) return power;
    }
    return pc_randomizer_color_stats() && color >= 0 && color < 3 && stat >= 0 && stat < 3 ? colorStats[color][stat] / 100.0f : 1.0f;
}
int pc_randomizer_carry_strength(int color) {
    return pc_randomizer_color_stats() && color >= 0 && color < 3 ? colorStats[color][3] : 1;
}
int pc_randomizer_field_capacity()
{
    // bot-v4b power mode (TEST-ONLY): the campaign field cap is 10xFlarlic
    // (20-40 at campaign start), which binds the withdraw menu (DrawContainer
    // squad caps), the Onion exit queue, and the birth pool below the power
    // squad. Lift to 100 while power mode is on (BOTH gates, same as the
    // damage lever); inert otherwise, so probe asserts on 20 still hold.
    if (autoplayPowerOn()) return 100;
    return pc_randomizer_expanded() ? 10 * (int)(startingFlarlic + flarlic) : 100;
}
namespace {
bool accessibleStage(int stage) {
    return (stage == 0 && pc_randomizer_has("Pikmin: Impact Site Access")) || (stage == 1 && pc_randomizer_has("Pikmin: Forest of Hope Access")) || (stage == 2 && pc_randomizer_has("Pikmin: Forest Navel Access"))
        || (stage == 3 && pc_randomizer_has("Pikmin: Distant Spring Access"))
        || (stage == 4 && pc_randomizer_has("Pikmin: Final Trial Access"));
}
}
void pc_randomizer_observe_population(int activePikmin, bool gameplay) {
    if (schema >= 7 || !pc_randomizer_expanded() || !gameplay || !ready || activePikmin < 0
        || activePikmin > pc_randomizer_field_capacity()) return;
    for (int i = 0; i < 9; ++i)
        if (activePikmin >= 20 + 10 * i) pc_randomizer_check(randomizerCheckNames[30 + i]);
}
void pc_randomizer_enemy_defeated(int type, int stage, bool healthDepleted, bool gameplay) {
    if (!thelynk && schema >= 9 && type == 16 && healthDepleted && gameplay && ready && accessibleStage(stage))
        pc_randomizer_check("Bestiary: Defeat Puffy Blowhog");
    if (schema >= 7 || !pc_randomizer_expanded() || !healthDepleted || !gameplay || !ready || !accessibleStage(stage)) return;
    for (int i = 0; i < 8; ++i)
        if (type == randomizerEnemyTypes[i]) pc_randomizer_check(randomizerCheckNames[39 + i]);
}
bool pc_randomizer_collection_checks() { return enabled && !thelynk && schema >= 7; }
void pc_randomizer_observe_color_population(int color, int totalPikmin, bool gameplay) {
    if (!enabled || !colorPopulation || !gameplay || !ready || color < 0 || color > 2 || totalPikmin < 0) return;
    const char* colors[] = {"Blue", "Red", "Yellow"};
    const char* onions[] = {"Blue Onion", "Red Onion", "Yellow Onion"};
    if (!pc_randomizer_has(onions[color])) return;
    static const int compactThresholds[] = {10, 25, 50, 100};
    const int* thresholds = compactPopulation ? compactThresholds : permanentChecks ? randomizerFinePopulation : randomizerTotalPopulation;
    const int length = compactPopulation ? 4 : permanentChecks ? 19 : 9;
    for (int i = 0; i < length; ++i) if (totalPikmin >= thresholds[i]) {
        char name[80]; std::snprintf(name, sizeof(name), "Population: %d total %s Pikmin", thresholds[i], colors[color]);
        pc_randomizer_check(name);
    }
}
void pc_randomizer_observe_total_population(int totalPikmin, bool gameplay) {
    if (colorPopulation || !pc_randomizer_collection_checks() || !gameplay || !ready || totalPikmin < 0) return;
    if (permanentChecks) {
        for (int count : randomizerFinePopulation) if (totalPikmin >= count) {
            char name[80]; std::snprintf(name, sizeof(name), "Population: %d total Pikmin", count);
            pc_randomizer_check(name);
        }
        return;
    }
    for (int i = 0; i < 9; ++i)
        if (totalPikmin >= randomizerTotalPopulation[i]) pc_randomizer_check(legacyCheckName(30 + i));
}
void pc_randomizer_corpse_delivered(int type, int stage, bool gameplay) {
    if (!pc_randomizer_collection_checks() || !gameplay || !ready || !accessibleStage(stage)) return;
    for (int i = 0; i < 8; ++i)
        // Population variants shift catalog positions; resolve the stable name
        // from the original collection catalog in the active check set.
        if (type == randomizerEnemyTypes[i]) pc_randomizer_check(randomizerCollectionNames[39 + i]);
    if (schema >= 9 && type != 16) for (const auto& entry : randomizerNewBestiary)
        if (entry.type == type) pc_randomizer_check(entry.name);
}
void pc_randomizer_observe_exploration(int stage, float dx, float dz, bool grounded, bool gameplay) {
    if (noExploration || !pc_randomizer_expanded() || !grounded || !gameplay || !ready || !accessibleStage(stage)
        || !std::isfinite(dx) || !std::isfinite(dz)) return;
    const int landIndex = stage == 0 ? 55 : 47 + (stage - 1) * 2;
    pc_randomizer_check(randomizerCheckNames[landIndex]);
    if (schema < 9 && dx * dx + dz * dz >= 600.0f * 600.0f)
        pc_randomizer_check(randomizerCheckNames[landIndex + 1]);
}

void pc_randomizer_validate_part_weight(int part, int minimum) {
    if (pc_randomizer_expanded() && (part < 0 || part >= 30 || randomizerPartWeights[part] != minimum))
        fail("loaded part weight differs from seed logic catalog");
}

void pc_randomizer_observe_obstacle(int stage, int kind, float x, float z, bool complete, bool gameplay) {
    if (!enabled || !ready || !gameplay || !accessibleStage(stage) || !std::isfinite(x) || !std::isfinite(z)) return;
    static std::set<std::tuple<int,int,int,int>> logged;
    const int px = int(std::round(x)), pz = int(std::round(z));
    if (permanentChecks && complete && !(noSticks && kind == 100)) {
        const RandomizerObstacle* match = nullptr;
        for (const auto& obstacle : randomizerObstacles)
            if (obstacle.stage == stage && obstacle.kind == kind && std::abs(obstacle.x - px) <= 1 && std::abs(obstacle.z - pz) <= 1) {
                if (match) fail("ambiguous obstacle identity");
                match = &obstacle;
            }
        // Campaign save positions truncate fractions; retain identity across a one-unit shift.
        if (match) pc_randomizer_check(match->name);
    }
    if (logged.emplace(stage, kind, px, pz).second)
        std::printf("[Pikmin Randomizer] OBSTACLE_INSTANCE stage=%d kind=%d x=%d z=%d complete=%d\n", stage, kind, px, pz, int(complete));
}

// Immutable generations keep the last committed day intact if a write is interrupted.
bool pc_randomizer_purple_campaign() { return enabled && purpleCampaign; }
bool pc_randomizer_second_captain() { return enabled && secondCaptain; }
bool pc_randomizer_resumed() { return enabled && campaignResumed; }
bool pc_randomizer_load_campaign(void* destination) {
    if (!pc_randomizer_resumed()) return false;
    std::memcpy(destination, campaignBlock.data(), 32768);
    return true;
}
namespace {
// Writes the campaign checkpoint for `generation` (tmp + fsync + rename).
// fatal (every non-netplay save and the netplay host): any failure is fail(),
// exactly as before. Non-fatal (the netplay client's mirror checkpoint,
// M4 lane B2): a failure returns false and leaves no .sav behind.
// suffix (fix round 1, C2): the client writes `<name>.sav.pending`, which no
// checkpoint scan reads, and renames it to `.sav` only after the host's ok.
bool write_campaign_checkpoint(const void* source, unsigned long long generation, bool fatal,
                               std::string* bytesOut, std::filesystem::path* finalOut,
                               const char* suffix = nullptr) {
    if (fatal) std::filesystem::create_directories(campaignDirectory);
    else {
        std::error_code ec;
        std::filesystem::create_directories(campaignDirectory, ec);
        if (ec) return false;
    }
    std::ostringstream meta;
    meta << (thelynk ? "THELYNK_CAMPAIGN_1 " : purpleCampaign ? "PIKMIN_CAMPAIGN_PURPLE_1 " : prereleaseTraps ? "PIKMIN_CAMPAIGN_5 " : proggTraps ? "PIKMIN_CAMPAIGN_4 " : bombTraps ? "PIKMIN_CAMPAIGN_3 " : bombDeliveries ? "PIKMIN_CAMPAIGN_2 " : "PIKMIN_CAMPAIGN_1 ") << fingerprint << ' ' << generation;
    for (int i = 0; i < (prereleaseTraps ? 7 : proggTraps ? 6 : bombTraps ? 5 : bombDeliveries ? 4 : 3); ++i) meta << ' ' << consumedBenefits[i];
    if (purpleCampaign) p2ship::stock.write(meta);
    if (thelynk) for (int i = 0; i < 18; ++i) meta << ' ' << thelynkUsed[i];
    std::string block(static_cast<const char*>(source), 32768);
    const auto hash = checkpointHash(meta.str() + "\n" + block);
    std::string bytes = meta.str() + " " + std::to_string(hash) + "\n" + block;
    char name[32]; std::snprintf(name, sizeof(name), "%020llu.sav", generation);
    auto final = campaignDirectory / name;
    if (suffix != nullptr) final += suffix;
    auto temporary = campaignDirectory / (token + ".tmp");
    FILE* file = std::fopen(temporary.string().c_str(), "wb");
    if (!file) {
        if (fatal) fail("cannot create campaign checkpoint");
        return false;
    }
    bool ok = std::fwrite(bytes.data(), 1, bytes.size(), file) == bytes.size() && std::fflush(file) == 0;
#ifdef _WIN32
    if (ok) ok = _commit(_fileno(file)) == 0;
#else
    if (ok) ok = fsync(fileno(file)) == 0;
#endif
    if (std::fclose(file) != 0) ok = false;
    if (!ok) {
        if (fatal) fail("cannot flush campaign checkpoint");
        std::error_code ec;
        std::filesystem::remove(temporary, ec);
        return false;
    }
    if (fatal) std::filesystem::rename(temporary, final);
    else {
        std::error_code ec;
        std::filesystem::rename(temporary, final, ec);
        if (ec) return false;
    }
    if (bytesOut != nullptr) *bytesOut = bytes;
    if (finalOut != nullptr) *finalOut = final;
    return true;
}
} // namespace

void pc_randomizer_save_campaign(const void* source) {
    if (!enabled) return;
    // Netplay M4 lane B1 fix round 1 (review B1-C9): journal lines queued in
    // this tick land before the checkpoint that records their sim state, so a
    // crash between the two can never leave a check or consumed benefit in
    // the checkpoint but not in checks.txt / benefits-used.txt. No-op outside
    // outbox mode. (One line in B2's function; B2 keeps it at its barrier.)
    pc_randomizer_outbox_flush(0);
    const auto generation = campaignGeneration + 1;
    write_campaign_checkpoint(source, generation, true, nullptr, nullptr);
    campaignGeneration = generation;
    std::printf("[Pikmin Randomizer] CAMPAIGN_SAVED generation=%llu\n", generation);
    std::fflush(stdout);
}

bool pc_randomizer_thelynk() { return enabled && thelynk; }
bool pc_randomizer_thelynk_part(unsigned model, bool received) {
    int i = thelynkModel(model);
    return pc_randomizer_thelynk() && i >= 0 && (received ? (thelynkParts & (1u << i)) != 0 : checks.count(unsigned(i)) != 0);
}
void pc_randomizer_thelynk_collect(unsigned model) {
    int i = thelynkModel(model);
    if (!pc_randomizer_thelynk() || i < 0) return;
    pc_randomizer_check(thelynkPartNames[i]);
}
void pc_randomizer_thelynk_squad(int color, int followers, bool gameplay) {
    if (!pc_randomizer_thelynk() || !ready || !gameplay || color < 0 || color > 2 || followers < 0 || followers > 100) return;
    const int c = color == 1 ? 0 : color == 2 ? 1 : 2;
    for (int n = 1; n <= followers; ++n) {
        const unsigned slot = 30 + unsigned(c) * 100 + unsigned(n) - 1;
        if (thelynkEnabled.count(slot)) pc_randomizer_check(thelynkNames[slot].c_str());
    }
}
int pc_randomizer_thelynk_bonus(int kind) {
    return pc_randomizer_thelynk() && ready && kind >= 0 && kind < 18 && thelynkBonuses[kind] > thelynkUsed[kind]
        ? (kind % 2 ? 5 : 1) : 0;
}
void pc_randomizer_thelynk_consume(int kind) {
    if (pc_randomizer_thelynk_bonus(kind)) ++thelynkUsed[kind];
}

// ---- Netplay M4 lane B2: day-end save barrier (issue #885) ----
// True in a netplay session with the external-state stream on (the outbox
// mode) and the session's barrier hook linked: memoryCard.cpp then takes
// pc_randomizer_save_campaign_netplay instead of the legacy statements.
bool pc_randomizer_netplay_save_barrier_active() {
    return enabled && outbox_active() && pc_netplay_save_barrier != nullptr;
}
bool pc_randomizer_netplay_agreed_saves() {
    return enabled && outbox_active();
}

// Inside the day-end save tick, after writeOneGameFile + waitPolling. Both
// peers run it at the same Advance (lockstep). The host writes its real
// checkpoint, the client its mirror checkpoint in its own campaign/; the
// session exchanges SAVE_RESULT / SAVE_ACK over the bulk channel only and
// returns the host's outcome, which both peers then use as mDidSaveFail. The
// generation both peers count on is advanced only on the agreed outcome, so
// the next day's generation numbers agree even when the peers' local
// results differ.
namespace {
// B2 fix round 1 (C2): the client's mirror checkpoint written for the save
// in progress (`<name>.sav.pending`), until the barrier confirms or retracts it.
std::filesystem::path netplayPendingCheckpoint;
// Renames a checkpoint file to `<final>.unconfirmed` (or -<n>), never deleting.
std::filesystem::path retract_checkpoint(const std::filesystem::path& from, const std::filesystem::path& final) {
    std::filesystem::path to = final;
    to += ".unconfirmed";
    for (int n = 1; std::filesystem::exists(to) && n < 1000; ++n) {
        to = final;
        to += ".unconfirmed-" + std::to_string(n);
    }
    std::error_code ec;
    std::filesystem::rename(from, to, ec);
    if (ec) fail("cannot retract an unconfirmed campaign checkpoint; preserve campaign files for recovery");
    return to;
}
std::filesystem::path pending_final(const std::filesystem::path& pending) {
    std::filesystem::path final = pending;
    final.replace_extension(); // drops ".pending"
    return final;
}
} // namespace

// B2 fix round 1 (C2): the session calls this (weakly) just before it exits
// from inside the barrier (exit 5 desync or exit 6 timeout). The client's
// unconfirmed checkpoint for this save is retracted, never deleted, so the
// next session sees the generation both peers last agreed on.
void pc_randomizer_netplay_barrier_abandoned() {
    if (netplayPendingCheckpoint.empty()) return;
    const std::filesystem::path final = pending_final(netplayPendingCheckpoint);
    const std::filesystem::path to = retract_checkpoint(netplayPendingCheckpoint, final);
    std::printf("[netplay] save barrier abandoned; retracted %s -> %s (generation stays %llu)\n",
                netplayPendingCheckpoint.filename().string().c_str(), to.filename().string().c_str(),
                campaignGeneration);
    std::fflush(stdout);
    netplayPendingCheckpoint.clear();
}

bool pc_randomizer_save_campaign_netplay(const void* source, bool localCardOk) {
    if (!enabled) return localCardOk;
    const uint32_t frame = pc_netplay_current_frame != nullptr ? pc_netplay_current_frame() : 0;
    // Lane S fix round 1 (MJ1): each step of this save (journal flush,
    // checkpoint write) is file I/O inside the save tick; between the steps
    // the session polls the network (rate-limited, no Advance, no sim state).
    const auto keepalive = []() {
        if (pc_netplay_load_keepalive != nullptr) pc_netplay_load_keepalive(pc_netplay_loadguard::kSiteSave);
    };
    // Flush first: this tick's journal lines land before the checkpoint.
    pc_randomizer_outbox_flush(frame);
    keepalive();
    const bool host = outbox_host();
    const unsigned long long generation = campaignGeneration + 1;
    std::string bytes;
    std::filesystem::path written;
    bool localOk = localCardOk;
#if PIKI_NETPLAY_BUILD
    // TEST ONLY (netplay builds): PIKMIN_NETPLAY_TEST_HOST_DIE_AT_BARRIER=1 makes
    // the HOST exit abruptly (_Exit 7, no cleanup) at its day-end save, before
    // it writes its checkpoint or answers the barrier, so a pair shows the
    // client's barrier timeout (exit 6) and its retraction (fix round 1, C2).
    if (host) {
        const char* knob = std::getenv("PIKMIN_NETPLAY_TEST_HOST_DIE_AT_BARRIER");
        if (knob != nullptr && knob[0] == '1' && knob[1] == '\0') {
            std::printf("[netplay] test: host dies at the day-end save (before its checkpoint)\n");
            std::fflush(stdout);
            std::_Exit(7);
        }
    }
#endif
#if PIKI_NETPLAY_BUILD
    // TEST ONLY (netplay builds): PIKMIN_NETPLAY_TEST_HOST_SAVE_FAIL=1 makes the
    // HOST's day-end save report a failure (as if its card write failed), so a
    // pair exercises the client's retract / SAVE_FAIL path at runtime. Both
    // peers follow the host's outcome, so the sim stays identical; the knob is
    // ignored on the client.
    if (host && localOk) {
        const char* knob = std::getenv("PIKMIN_NETPLAY_TEST_HOST_SAVE_FAIL");
        if (knob != nullptr && knob[0] == '1' && knob[1] == '\0') {
            localOk = false;
            std::printf("[netplay] test: host day-end save forced to fail\n");
        }
    }
#endif
    if (localOk) {
        // The host writes its real checkpoint; the client writes its mirror
        // as <name>.sav.pending (fix round 1, C2) and publishes it as .sav
        // only after the host's ok, so a barrier that ends in exit 5/6, or a
        // client killed mid-barrier, never leaves an unconfirmed .sav behind.
        localOk = write_campaign_checkpoint(source, generation, host, &bytes, &written, host ? nullptr : ".pending");
        keepalive();
        if (localOk && host) std::printf("[Pikmin Randomizer] CAMPAIGN_SAVED generation=%llu\n", generation);
        else if (localOk) netplayPendingCheckpoint = written;
        else std::printf("[netplay] save barrier: cannot write the local mirror checkpoint %020llu.sav\n", generation);
        std::fflush(stdout);
    }
    bool hostOk = localOk;
    char hostSavHex[65] = {};
    const bool agreed = pc_netplay_save_barrier != nullptr
                     && pc_netplay_save_barrier(frame, localOk, generation,
                                                reinterpret_cast<const uint8_t*>(bytes.data()), bytes.size(),
                                                static_cast<const uint8_t*>(source), 32768, &hostOk, hostSavHex);
    // Fix round 1 (C7): the barrier only returns false outside a running
    // session, which cannot happen while the barrier is active; never go on
    // with this peer's local outcome as if it were the agreed one.
    if (!agreed) {
        pc_randomizer_netplay_barrier_abandoned();
        if (pc_netplay_abort_desync != nullptr)
            pc_netplay_abort_desync("save barrier: no running session to agree the day-end save with");
        fail("netplay save barrier without a running session");
    }
    if (host) {
        if (hostOk) campaignGeneration = generation;
        return hostOk;
    }
    netplayPendingCheckpoint.clear();
    if (hostOk) {
        if (localOk) {
            // Publish the mirror checkpoint under its real name.
            const std::filesystem::path final = pending_final(written);
            std::error_code ec;
            std::filesystem::rename(written, final, ec);
            if (ec) {
                localOk = false;
                std::printf("[netplay] save barrier: cannot publish %s as %s (%s)\n",
                            written.filename().string().c_str(), final.filename().string().c_str(),
                            ec.message().c_str());
            } else {
                std::printf("[Pikmin Randomizer] CAMPAIGN_SAVED generation=%llu\n", generation);
            }
        }
        if (!localOk) std::printf("[netplay] save barrier: local mirror save failed; following the host\n");
        std::fflush(stdout);
        campaignGeneration = generation;
        pc_randomizer_mirror_save_result(frame, generation, hostSavHex);
    } else {
        if (localOk) {
            // The host's save failed: the day is abandoned there, so this
            // mirror checkpoint must not stand. Renamed, never deleted.
            const std::filesystem::path to = retract_checkpoint(written, pending_final(written));
            std::printf("[netplay] save barrier: host save failed; retracted %s -> %s (generation stays %llu)\n",
                        written.filename().string().c_str(), to.filename().string().c_str(), campaignGeneration);
            std::fflush(stdout);
        }
        pc_randomizer_mirror_save_fail(frame, generation);
    }
    return hostOk;
}

// B2 fix round 1 (C12): the client's own card write failed while the host's
// save succeeded, and memoryCard.cpp rewrote the game file from the same
// in-memory block. If that failed too, this peer's card no longer matches
// the host's, and later card reads could branch the sim: end the session.
void pc_randomizer_netplay_card_rewrite_result(bool ok) {
    if (ok) {
        std::printf("[netplay] save barrier: local card write failed; rewrote the game file from the agreed block\n");
        std::fflush(stdout);
        return;
    }
    if (pc_netplay_abort_desync != nullptr)
        pc_netplay_abort_desync("save barrier: this peer cannot write the agreed game file to its memory card");
    fail("netplay: cannot write the agreed game file to the memory card");
}

// B2 fix round 1 (C3): the options write after an agreed save is local I/O
// only; its outcome must not reach the sim (memoryCard.cpp restores the
// agreed mDidSaveFail after it). Logged when it failed here.
void pc_randomizer_netplay_options_result(bool ok) {
    if (ok) return;
    std::printf("[netplay] save barrier: this peer's options write failed (local only; the agreed save "
                "outcome stands)\n");
    std::fflush(stdout);
}

// B2 fix round 1 (C5/E1): a resumed netplay session starts its first stage
// through MapSelect, not the direct-boot path that prints START_STAGE; the
// deterministic day reseed (GameCoreSection) reports that stage start here
// so both peers log `START_STAGE <stage> day=<d> resumed=1`. Netplay
// sessions only, once per process, resumed campaigns only.
void pc_randomizer_netplay_stage_start(int day, int stage) {
    static bool printed = false;
    if (printed || !enabled || !campaignResumed || !netplay_session()) return;
    printed = true;
    std::printf("[Pikmin Randomizer] START_STAGE %d day=%d resumed=1 generation=%llu\n", stage, day,
                campaignGeneration);
    std::fflush(stdout);
}

// ---- Netplay M4 lane B2: checkpoint info, adoption (issue #885) ----
// The handshake's checkpoint info: the newest valid checkpoint under the
// loadCampaignCheckpoint rules (the same scan) and the SHA-256 of its file
// bytes. gen 0 and zeros = none. False when the randomizer is disabled.
bool pc_randomizer_checkpoint_info(uint64_t* gen, uint8_t sha[32]) {
    if (gen != nullptr) *gen = 0;
    if (sha != nullptr) std::memset(sha, 0, 32);
    if (!enabled) return false;
    CkptScan s;
    if (scanCampaignCheckpoint(s) != kCkptOk) return true;
    std::ifstream file(s.latest, std::ios::binary);
    std::string bytes((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
    if (gen != nullptr) *gen = s.generation;
    if (sha != nullptr) pc_netplay_sha::sha256(bytes.data(), bytes.size(), sha);
    return true;
}

// The derived campaign directory (absolute), "" when disabled.
const char* pc_randomizer_campaign_dir() {
    static std::string dir;
    dir = enabled ? campaignDirectory.string() : std::string();
    return dir.c_str();
}

// Joiner, after the transfer phase wrote the host's checkpoint and card
// files: re-runs the loadCampaignCheckpoint rules from scratch, so
// campaignBlock, consumedBenefits, campaignGeneration and campaignResumed
// are exactly what a boot over these files would have set.
bool pc_randomizer_adopt_checkpoint() {
    if (!enabled) return false;
    campaignGeneration = 0;
    campaignResumed = false;
    campaignBlock.clear();
    for (unsigned& used : consumedBenefits) used = 0;
    for (unsigned& used : thelynkUsed) used = 0;
    p2ship::stock = p2ship::Store();
    loadCampaignCheckpoint();
    if (campaignResumed) {
        std::printf("[Pikmin Randomizer] CAMPAIGN_RESUMED generation=%llu\n", campaignGeneration);
        std::fflush(stdout);
    }
    return campaignResumed;
}

// ---- Netplay M4 lane B1: outbox flush, client mirror, ledger (issue #885) ----
namespace {
uint32_t mirror_frame(uint32_t frame) {
    if (frame < mirrorLastFrame) frame = mirrorLastFrame; // frames never decrease
    mirrorLastFrame = frame;
    return frame;
}
// Client only. Binary append ("ab"): text mode on Windows would write CRLF
// and the reference parser rejects a carriage return. One fflush per batch,
// no fsync. Each line is echoed to stdout as `[netplay] mirror <line>`.
void mirror_append(const std::vector<std::string>& lines) {
    if (lines.empty()) return;
    FILE* file = std::fopen((directory / "mirror-events.txt").string().c_str(), "ab");
    if (!file) fail("cannot open netplay mirror-events.txt");
    bool ok = true;
    for (const std::string& line : lines) {
        ok = ok && std::fwrite(line.data(), 1, line.size(), file) == line.size() && std::fputc(0x0A, file) != EOF;
        std::printf("[netplay] mirror %s\n", line.c_str());
    }
    ok = std::fflush(file) == 0 && ok;
    ok = std::fclose(file) == 0 && ok;
    if (!ok) fail("netplay mirror-events.txt write failed");
    std::fflush(stdout);
}
// Host: every entry in push order, each with its historical format and
// durability; any write failure is fail() (exit 2), exactly as before.
void outbox_flush_host(const std::vector<pc_rand_outbox::Entry>& entries) {
    for (const pc_rand_outbox::Entry& e : entries) {
        switch (e.kind) {
        case pc_rand_outbox::Kind::Check: {
            // A slot is journaled once per run; streamed slots never enter
            // checksJournaled (AP-originated checks are not native).
            if (!outbox_io().checksJournaled.insert(e.slot).second) break;
            FILE* file = std::fopen((directory / "checks.txt").string().c_str(), "a");
            if (!file) fail("cannot persist native collection");
            bool ok = std::fprintf(file, "%u\n", thelynk ? thelynkId(unsigned(e.slot)) : unsigned(e.slot)) > 0 && std::fflush(file) == 0;
#ifdef _WIN32
            ok = ok && _commit(_fileno(file)) == 0;
#else
            ok = ok && fsync(fileno(file)) == 0;
#endif
            ok = std::fclose(file) == 0 && ok;
            if (!ok) fail("native collection persistence failed");
            break;
        }
        case pc_rand_outbox::Kind::Benefit: {
            FILE* file = std::fopen(benefitJournal.string().c_str(), "a");
            if (!file) fail("cannot open benefit consumption journal");
            bool ok = std::fprintf(file, "%s %d %u\n", fingerprint.c_str(), int(e.benefitKind), e.count) > 0 && std::fflush(file) == 0;
#ifdef _WIN32
            ok = ok && _commit(_fileno(file)) == 0;
#else
            ok = ok && fsync(fileno(file)) == 0;
#endif
            if (std::fclose(file) != 0 || !ok) fail("cannot persist benefit consumption");
            break;
        }
        case pc_rand_outbox::Kind::Emperor: {
            FILE* file = std::fopen((directory / "emperor.tmp").string().c_str(), "w");
            if (!file) fail("cannot persist Emperor defeat");
            bool ok = std::fprintf(file, "EMPEROR_DEFEATED %s %s\n", token.c_str(), fingerprint.c_str()) > 0 && std::fflush(file) == 0;
#ifdef _WIN32
            ok = ok && _commit(_fileno(file)) == 0;
#else
            ok = ok && fsync(fileno(file)) == 0;
#endif
            ok = std::fclose(file) == 0 && ok;
            if (!ok) fail("Emperor defeat persistence failed");
            std::filesystem::rename(directory / "emperor.tmp", directory / "emperor.txt");
            break;
        }
        case pc_rand_outbox::Kind::Death: {
            FILE* file = std::fopen((directory / "deaths.txt").string().c_str(), "a");
            if (!file) fail("cannot open Pikmin death journal");
            bool ok = std::fprintf(file, "%u\n", e.total) > 0 && std::fflush(file) == 0;
            ok = std::fclose(file) == 0 && ok;
            if (!ok) fail("Pikmin death journal write failed");
            break;
        }
        case pc_rand_outbox::Kind::P2Delivery: {
            if (!p2DeliveryHost) {
                const std::filesystem::path path = campaignDirectory.empty()
                    ? directory / "p2-delivery-receipts.txt"
                    : campaignDirectory / "p2-delivery-receipts.txt";
                p2DeliveryHost = pc_p2_delivery_host_open(path.string().c_str());
                // Fatal on the host in outbox mode: the sim already took the
                // Granted branch on both peers, so a silent skip would lose
                // the receipt.
                if (!p2DeliveryHost) fail("P2 ordinary delivery ledger open failed");
            }
            const std::string& seed = fingerprint.empty() ? token : fingerprint;
            const P2DeliveryHostResult result = pc_p2_delivery_host_deliver(p2DeliveryHost, seed.c_str(),
                e.p2Source, e.p2Type, e.p2Stage, e.p2Generator, "corpse");
            std::printf("[Pikmin Randomizer] P2_ORDINARY_P2_RECEIPT seed=%s id=onion:p2:%u:%d generator=%u new=%d\n",
                seed.c_str(), e.p2Source, e.p2Stage, e.p2Generator, int(result == P2DeliveryHostResult::Granted));
            if (result == P2DeliveryHostResult::Error) fail("P2 ordinary delivery ledger write failed");
            break;
        }
        case pc_rand_outbox::Kind::CheckApplied:
        case pc_rand_outbox::Kind::EmperorApplied:
        case pc_rand_outbox::Kind::DeathLink:
            break; // mirror-only events: the host runner reads its own state
        }
    }
}
bool mirrorLedgerSeen = false;
// Client: one DEATHS line for an absolute run total, or (before the first
// ledger message) keep it pending: only the latest total matters.
void mirror_deaths_line(std::vector<std::string>& lines, uint32_t frame, uint32_t total) {
    if (mirrorDeathsSuppressed) return;
    if (!mirrorLedgerSeen) {
        mirrorDeathsPending = true;
        mirrorDeathsPendingTotal = total;
        mirrorDeathsPendingFrame = frame;
        std::printf("[netplay] mirror DEATHS %u pending: no ledger message yet\n", total);
        return;
    }
    const uint64_t absolute = (uint64_t)mirrorDeathsBase + total;
    const std::string line = absolute > pc_rand_outbox::kMaxTotal ? std::string()
        : pc_rand_outbox::mirror_deaths(mirror_frame(frame), (uint32_t)absolute);
    if (line.empty()) std::printf("[netplay] mirror skip DEATHS %llu: out of range\n", (unsigned long long)absolute);
    else lines.push_back(line);
}
// Client: no journal at all; mirror-events.txt lines in the root grammar,
// each with its entry's own push frame (fix round 1, review R9).
void outbox_flush_client(const std::vector<pc_rand_outbox::Entry>& entries) {
    std::vector<std::string> lines;
    for (const pc_rand_outbox::Entry& e : entries) {
        const uint32_t frame = e.frame;
        switch (e.kind) {
        case pc_rand_outbox::Kind::Check:
        case pc_rand_outbox::Kind::CheckApplied: {
            if (!outbox_io().mirrorChecked.insert(e.slot).second) break;
            const char* name = e.slot < checkCount ? checkName(e.slot) : nullptr;
            // External location names belong only to the client mirror protocol.
            static const char* const thelynkMirrorPartNames[30] = {
                "TDS - Bowsprit",
                "TDS - Gluon Drive",
                "TFN - Anti-Dioxin Filter",
                "TFoH - Eternal Fuel Dynamo",
                "TIS - Main Engine",
                "TFoH - Whimsical Radar",
                "TDS - Interstellar Radio",
                "TFN - Guard Satellite",
                "TDS - Chronos Reactor",
                "TFoH - Radiation Canopy",
                "TFoH - Geiger Counter",
                "TFoH - Sagittarius",
                "TFN - Libra",
                "TFN - Omega Stabilizer",
                "TFN - #1 Ionium Jet",
                "TDS - #2 Ionium Jet",
                "TFoH - Shock Absorber",
                "TFN - Gravity Jumper",
                "TDS - Pilot's Seat",
                "TFoH - Nova Blaster",
                "TFN - Automatic Gear",
                "TDS - Zirconium Rotor",
                "TFoH - Extraordinary Bolt",
                "TDS - Repair-type Bolt",
                "TFN - Space Float",
                "TDS - Massage Machine",
                "TFT - Secret Safe",
                "TIS - Positron Generator",
                "TFN - Analog Computer",
                "TDS - UV Lamp",
            };
            if (thelynk && e.slot < 30) name = thelynkMirrorPartNames[e.slot];
            const std::string line = pc_rand_outbox::mirror_checked(mirror_frame(frame), name);
            if (line.empty()) std::printf("[netplay] mirror skip CHECKED slot=%u: name not expressible\n", e.slot);
            else lines.push_back(line);
            break;
        }
        case pc_rand_outbox::Kind::Emperor:
        case pc_rand_outbox::Kind::EmperorApplied:
            if (mirrorEmperor) break;
            mirrorEmperor = true;
            lines.push_back(pc_rand_outbox::mirror_emperor(mirror_frame(frame)));
            break;
        case pc_rand_outbox::Kind::Death:
            mirror_deaths_line(lines, frame, e.total);
            break;
        case pc_rand_outbox::Kind::DeathLink: {
            if (e.total <= mirrorLastDeathLink) break;
            const std::string line = pc_rand_outbox::mirror_deathlink(mirror_frame(frame), e.total);
            if (line.empty()) { std::printf("[netplay] mirror skip DEATHLINK %u: out of range\n", e.total); break; }
            mirrorLastDeathLink = e.total;
            lines.push_back(line);
            break;
        }
        case pc_rand_outbox::Kind::Benefit:
        case pc_rand_outbox::Kind::P2Delivery:
            break; // host journals only; no mirror tag
        }
    }
    mirror_append(lines);
}
} // namespace

// Once per Advance (pc_netplay_session.cpp, after pc_state_hash_tick_end and
// before the exit-after check), and at the top of pc_randomizer_save_campaign
// (so a save inside a tick never checkpoints state whose journal lines are
// still queued). `frame` is the caller's current frame and is not used for
// the lines: every entry carries its own push frame. A no-op outside outbox
// mode (nothing is ever queued there; the queue is not even constructed).
void pc_randomizer_outbox_flush(uint32_t frame) {
    (void)frame;
    if (!enabled || !outboxUsed || outbox_io().queue.size() == 0) return;
    std::vector<pc_rand_outbox::Entry> entries;
    outbox_io().queue.take(entries);
    if (outbox_host()) outbox_flush_host(entries);
    else outbox_flush_client(entries);
    std::fflush(stdout);
}

// Client: one kBulkMirrorLedger message from the host. The first message
// fixes deathsBase; RECEIVED lines follow in index order without gaps at the
// client's current frame (bulk delivery is unordered; the sequencer holds a
// message that would leave a gap).
void pc_randomizer_mirror_ledger_receive(const uint8_t* data, size_t len, uint32_t frame) {
    if (!enabled || !outbox_active() || outbox_host()) return;
    pc_rand_outbox::LedgerMsg msg;
    if (!pc_rand_outbox::decode_ledger(data, len, msg)) {
        std::printf("[netplay] mirror ledger: malformed message (len=%zu) dropped\n", len);
        std::fflush(stdout);
        return;
    }
    std::vector<std::string> lines;
    if (!mirrorLedgerSeen) {
        // The host sends its first message at session start, always; the
        // base never changes afterwards. A DEATHS total that waited for it
        // is written now, with its own event frame.
        mirrorLedgerSeen = true;
        if (msg.deathsBase == pc_rand_outbox::kLedgerBaseUnknown) {
            mirrorDeathsSuppressed = true;
            std::printf("[netplay] mirror ledger: deathsBase unknown (host session.json unreadable at start); "
                        "DEATHS lines suppressed\n");
        } else {
            mirrorDeathsBase = msg.deathsBase;
            std::printf("[netplay] mirror ledger: deathsBase=%u\n", mirrorDeathsBase);
        }
        if (mirrorDeathsPending) {
            mirrorDeathsPending = false;
            mirror_deaths_line(lines, mirrorDeathsPendingFrame, mirrorDeathsPendingTotal);
        }
    }
    std::vector<std::pair<uint32_t, uint32_t>> fresh;
    if (!outbox_io().mirrorReceived.offer(msg.firstIndex, msg.ids, fresh))
        std::printf("[netplay] mirror ledger: too many held messages; first=%u dropped\n", msg.firstIndex);
    for (const auto& r : fresh) {
        const std::string line = pc_rand_outbox::mirror_received(mirror_frame(frame), r.first, r.second);
        if (line.empty()) std::printf("[netplay] mirror skip RECEIVED %u %u: out of range\n", r.first, r.second);
        else lines.push_back(line);
    }
    mirror_append(lines);
    std::fflush(stdout);
}

// B2 writer API: the day-end save barrier reports its outcome to the client
// mirror. Client + outbox mode only; a no-op on the host and outside netplay.
void pc_randomizer_mirror_save_result(uint32_t frame, unsigned long long gen, const char* shaHex) {
    if (!enabled || !outbox_active() || outbox_host()) return;
    const std::string line = pc_rand_outbox::mirror_save_result(mirror_frame(frame), gen, shaHex);
    if (line.empty()) { std::printf("[netplay] mirror skip SAVE_RESULT gen=%llu: not expressible\n", gen); return; }
    mirror_append(std::vector<std::string>{ line });
}
void pc_randomizer_mirror_save_fail(uint32_t frame, unsigned long long gen) {
    if (!enabled || !outbox_active() || outbox_host()) return;
    const std::string line = pc_rand_outbox::mirror_save_fail(mirror_frame(frame), gen);
    if (line.empty()) { std::printf("[netplay] mirror skip SAVE_FAIL gen=%llu: not expressible\n", gen); return; }
    mirror_append(std::vector<std::string>{ line });
}
