#include "pc_randomizer.h"
#include "pc_randomizer_catalog.h"
#include "pc_randomizer_spawn_catalog.h"
#include "pc_randomizer_campaign_catalog.h"
#include <unordered_map>
#include <cstdint>
#include <cmath>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>
#include <set>
#include <tuple>
#ifdef _WIN32
#include <io.h>
#else
#include <unistd.h>
#endif

namespace {
bool noSticks = false, emperorGoal = false, emperorDefeated = false;
bool enabled = false, ready = false, goalReported = false, permanentChecks = false, noExploration = false, colorPopulation = false;
unsigned repairs = 0, unlocks = 0, flarlic = 0, schema = 1, checkCount = 30;
int startStage = 1;
int startColor = 1; // Native IDs: blue 0, red 1, yellow 2.
unsigned enemyMask = 0;
bool compactPopulation = false;
bool minibossEnemies = false;
bool slotEnemies = false, campaignEnemies = false;
unsigned campaignAssignments[72] = {};
bool groupEnemies = false;
unsigned groupAssignments[12] = {};
unsigned adultAssignments[15] = {};
std::unordered_map<const void*, unsigned> generatorIds;
unsigned startingFlarlic = 2;
bool configuredFlarlic = false, configuredStats = false, progressiveStats = false, wideStats = false, balancedStats = false, doubledStats = false;
int baseColorStats[3][4] = {{100, 100, 100, 1}, {100, 100, 100, 1}, {100, 100, 100, 1}};
unsigned statUpgrades[3][4] = {};
bool benefitItems = false, bombDeliveries = false, combinedCaptain = false;
unsigned benefits[6] = {}, consumedBenefits[4] = {};
// DeathLink: the first state value read is the baseline, so links received while
// the game was closed never replay. Pending links are bounded; each applies once.
unsigned deathLinkUnit = 0, deathLinksSeen = 0, deathLinksPending = 0, deathsReported = 0;
bool deathLinkBaseline = false;
std::set<const void*> inducedDeaths;
int consumedIndex(PcBenefit kind) { return kind == PC_BENEFIT_BOMBS ? 3 : int(kind); }
std::filesystem::path benefitJournal, campaignDirectory;
std::string campaignBlock;
unsigned long long campaignGeneration = 0;
bool campaignResumed = false;
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
void loadCampaignCheckpoint() {
    if (!std::filesystem::exists(campaignDirectory)) return;
    std::filesystem::path latest;
    for (const auto& entry : std::filesystem::directory_iterator(campaignDirectory)) {
        if (entry.path().extension() != ".sav") continue;
        const auto name = entry.path().stem().string();
        if (name.size() != 20 || name.find_first_not_of("0123456789") != std::string::npos)
            fail("invalid campaign checkpoint filename");
        const auto generation = std::stoull(name);
        if (generation > campaignGeneration) { campaignGeneration = generation; latest = entry.path(); }
    }
    if (latest.empty()) return;
    std::ifstream file(latest, std::ios::binary);
    std::string header; std::getline(file, header);
    std::istringstream meta(header);
    std::string magic, savedFingerprint, extra;
    unsigned long long generation; uint64_t hash;
    unsigned used[4] = {};
    bool valid = bool(meta >> magic >> savedFingerprint >> generation);
    for (int i = 0; i < (bombDeliveries ? 4 : 3); ++i) valid = valid && bool(meta >> used[i]) && used[i] <= checkCount;
    if (!valid || !(meta >> hash) || magic != (bombDeliveries ? "PIKMIN_CAMPAIGN_2" : "PIKMIN_CAMPAIGN_1")
        || savedFingerprint != fingerprint || generation != campaignGeneration || (meta >> extra))
        fail("campaign checkpoint header/seed mismatch; preserve campaign files for recovery");
    campaignBlock.resize(32768);
    file.read(&campaignBlock[0], 32768);
    if (file.gcount() != 32768 || file.peek() != EOF
        || checkpointHash(header.substr(0, header.rfind(' ')) + "\n" + campaignBlock) != hash)
        fail("campaign checkpoint is damaged; preserve campaign files for recovery");
    for (int i=0; i<4; ++i) consumedBenefits[i] = used[i];
    campaignResumed = true;
}
bool hex64(const std::string& s) {
    return s.size() == 64 && s.find_first_not_of("0123456789abcdef") == std::string::npos;
}
void expect(std::istream& in, const char* expected) {
    std::string word;
    if (!(in >> word) || word != expected) fail("unsupported or malformed bootstrap");
}
const char* baseCheckName(unsigned i) { return compactPopulation ? (permanentChecks ? randomizerCompactPermanentNames[i] : randomizerCompactCollectionNames[i]) : colorPopulation ? (permanentChecks ? randomizerColorPermanentNames[i] : randomizerColorCollectionNames[i]) : noExploration ? (permanentChecks ? randomizerNoExplorePermanentNames[i] : randomizerNoExploreCollectionNames[i]) : schema >= 9 ? (permanentChecks ? randomizerModernPermanentNames[i] : randomizerModernCollectionNames[i]) : schema >= 8 ? randomizerPermanentNames[i] : schema >= 7 ? randomizerCollectionNames[i] : randomizerCheckNames[i]; }
const char* checkName(unsigned i) {
    if (!noSticks) return baseCheckName(i);
    unsigned source = 0;
    for (;;) {
        const char* name = baseCheckName(source++);
        if (std::strstr(name, "Climbing Stick")) continue;
        if (i-- == 0) return name;
    }
}
int index(const char* name) {
    if (name) for (unsigned i = 0; i < checkCount; ++i) if (!std::strcmp(name, checkName(i))) return (int)i;
    return -1;
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
    std::ifstream input(bootstrap);
    if (!input) fail("cannot open standalone bootstrap");
    expect(input, "PIKMIN_RANDOMIZER");
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
        if (!colorPopulation || !(input >> mode) || (mode < 1 || mode > 4)) fail("invalid benefit mode");
        benefitItems = true;
        bombDeliveries = mode == 2 || mode == 4;
        combinedCaptain = mode >= 3;
        input >> end;
    }
    if (end == "DEATHLINK") {
        if (schema != 9 || !(input >> deathLinkUnit) || deathLinkUnit < 1 || deathLinkUnit > 100) fail("invalid DeathLink unit");
        input >> end;
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
    loadCampaignCheckpoint();
    enabled = true;
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
    if (slotEnemies) hello << " enemy-slots-v1";
    if (groupEnemies) hello << " enemy-groups-v1";
    if (campaignEnemies) hello << " enemy-campaign-v1";
    if (minibossEnemies) hello << " miniboss-slots-v1";
    if (emperorGoal) hello << " emperor-goal-v1";
    if (deathLinkUnit) hello << " death-link-v1";
    hello << " END\n";
    hello.close();
    if (!hello) fail("cannot write native handshake");
    std::filesystem::rename(directory / "hello.tmp", directory / "hello.txt");
    std::printf("[Pikmin Randomizer] initialized; identity placements, 25 repair goal\n");
    return true;
}

void pc_randomizer_update() {
    if (!enabled) return;
    std::error_code error;
    const auto stamp = std::filesystem::last_write_time(directory / "state.txt", error);
    if (error) { ready = false; return; }
    if (stamp == lastStamp) {
        if (std::chrono::steady_clock::now() - lastFresh > std::chrono::seconds(3)) ready = false;
        return;
    }
    std::ifstream input(directory / "state.txt");
    // Windows may briefly deny opening a file being atomically replaced.
    // Pause and retry; an opened but malformed record still fails closed.
    if (!input.is_open()) { ready = false; return; }
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
    unsigned newBenefits[6] = {};
    if (benefitItems) {
        if (!parsed || end != "BENEFITS") fail("missing benefit state");
        for (int kind = 0; kind < (bombDeliveries ? 6 : 5); ++kind)
            if (!(input >> newBenefits[kind]) || newBenefits[kind] > (kind < 3 || kind == 5 ? checkCount : 2u)
                || newBenefits[kind] < benefits[kind] || ((kind < 3 || kind == 5) && newBenefits[kind] < consumedBenefits[consumedIndex(static_cast<PcBenefit>(kind))]))
                fail("invalid or retracted benefit receipt");
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
    for (int kind = 0; kind < 6; ++kind) benefits[kind] = newBenefits[kind];
    emperorDefeated = emperorDefeated || newEmperor != 0;
    if (deathLinkUnit) {
        if (!deathLinkBaseline) { deathLinksSeen = newDeathLinks; deathLinkBaseline = true; }
        else if (newDeathLinks < deathLinksSeen) fail("state retracted received DeathLinks");
        else {
            deathLinksPending = std::min(3u, deathLinksPending + (newDeathLinks - deathLinksSeen));
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

bool pc_randomizer_benefit_pending(PcBenefit kind) {
    return enabled && benefitItems && ready && ((kind >= 0 && kind < 3) || (kind == PC_BENEFIT_BOMBS && bombDeliveries)) && benefits[kind] > consumedBenefits[consumedIndex(kind)];
}
bool pc_randomizer_consume_benefit(PcBenefit kind) {
    if (!pc_randomizer_benefit_pending(kind)) return false;
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
unsigned pc_randomizer_generator_id(const void* generator) {
    auto it = generatorIds.find(generator);
    return it == generatorIds.end() ? 0 : it->second;
}
void pc_randomizer_set_generator_id(const void* generator, unsigned uid) {
    if (!uid) { generatorIds.erase(generator); return; }
    if (!pc_randomizer_spawn_slots()) return;
    for (const auto& row : randomizerSpawnSlots) if (row.uid == uid) {
        generatorIds[generator] = uid; return;
    }
    fail("unknown saved generator ID");
}
void pc_randomizer_bind_generator(const void* generator, int stage, const char* file, int offset) {
    pc_randomizer_set_generator_id(generator, 0);
    if (!pc_randomizer_spawn_slots() || !file) return;
    for (const auto& row : randomizerSpawnSlots)
        if (row.stage == stage && row.offset == offset && !std::strcmp(row.file, file)) {
            pc_randomizer_set_generator_id(generator, row.uid); return;
        }
}
int pc_randomizer_enemy_for_generator(int original, bool protectedSpawn, const void* generator) {
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
bool pc_randomizer_goal() { return enabled && repairs == 25 && (!emperorGoal || emperorDefeated); }
bool pc_randomizer_emperor_available() { return !enabled || !emperorGoal || (ready && repairs == 25); }
void pc_randomizer_emperor_defeated() {
    if (!enabled || !emperorGoal || !ready || repairs != 25 || emperorDefeated) return;
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
void pc_randomizer_deathlink_induce(const void* piki) {
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
int pc_randomizer_next_day(int day) { return enabled && day >= 28 ? 29 : day + 1; }
bool pc_randomizer_has(const char* name) {
    if (!enabled || !name) return false;
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
    return slot >= 0 && checks.count(unsigned(slot)) != 0;
}
void pc_randomizer_check(const char* name) {
    if (!enabled || !ready) return;
    const int slot = index(name);
    if (slot < 0) {
        // Main Engine is the synthetic tutorial completion, not a standalone check.
        if (name && !std::strcmp(name, "Pikmin: Main Engine")) return;
        fail("unknown native collection identity");
    }
    if (checks.count(unsigned(slot))) return;
    FILE* file = std::fopen((directory / "checks.txt").string().c_str(), "a");
    if (!file) fail("cannot persist native collection");
    bool ok = std::fprintf(file, "%d\n", slot) > 0 && std::fflush(file) == 0;
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

bool pc_randomizer_expanded() { return enabled && schema >= 2; }
bool pc_randomizer_color_stats() { return enabled && (configuredStats || progressiveStats); }
float pc_randomizer_color_multiplier(int color, PcPikminStat stat) {
    return pc_randomizer_color_stats() && color >= 0 && color < 3 && stat >= 0 && stat < 3 ? colorStats[color][stat] / 100.0f : 1.0f;
}
int pc_randomizer_carry_strength(int color) {
    return pc_randomizer_color_stats() && color >= 0 && color < 3 ? colorStats[color][3] : 1;
}
int pc_randomizer_field_capacity() { return pc_randomizer_expanded() ? 10 * (int)(startingFlarlic + flarlic) : 100; }
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
    if (schema >= 9 && type == 16 && healthDepleted && gameplay && ready && accessibleStage(stage))
        pc_randomizer_check("Bestiary: Defeat Puffy Blowhog");
    if (schema >= 7 || !pc_randomizer_expanded() || !healthDepleted || !gameplay || !ready || !accessibleStage(stage)) return;
    for (int i = 0; i < 8; ++i)
        if (type == randomizerEnemyTypes[i]) pc_randomizer_check(randomizerCheckNames[39 + i]);
}
bool pc_randomizer_collection_checks() { return enabled && schema >= 7; }
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
        if (totalPikmin >= randomizerTotalPopulation[i]) pc_randomizer_check(checkName(30 + i));
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
bool pc_randomizer_resumed() { return enabled && campaignResumed; }
bool pc_randomizer_load_campaign(void* destination) {
    if (!pc_randomizer_resumed()) return false;
    std::memcpy(destination, campaignBlock.data(), 32768);
    return true;
}
void pc_randomizer_save_campaign(const void* source) {
    if (!enabled) return;
    std::filesystem::create_directories(campaignDirectory);
    const auto generation = campaignGeneration + 1;
    std::ostringstream meta;
    meta << (bombDeliveries ? "PIKMIN_CAMPAIGN_2 " : "PIKMIN_CAMPAIGN_1 ") << fingerprint << ' ' << generation;
    for (int i = 0; i < (bombDeliveries ? 4 : 3); ++i) meta << ' ' << consumedBenefits[i];
    std::string block(static_cast<const char*>(source), 32768);
    const auto hash = checkpointHash(meta.str() + "\n" + block);
    std::string bytes = meta.str() + " " + std::to_string(hash) + "\n" + block;
    char name[32]; std::snprintf(name, sizeof(name), "%020llu.sav", generation);
    auto final = campaignDirectory / name;
    auto temporary = campaignDirectory / (token + ".tmp");
    FILE* file = std::fopen(temporary.string().c_str(), "wb");
    if (!file) fail("cannot create campaign checkpoint");
    bool ok = std::fwrite(bytes.data(), 1, bytes.size(), file) == bytes.size() && std::fflush(file) == 0;
#ifdef _WIN32
    if (ok) ok = _commit(_fileno(file)) == 0;
#else
    if (ok) ok = fsync(fileno(file)) == 0;
#endif
    if (std::fclose(file) != 0) ok = false;
    if (!ok) fail("cannot flush campaign checkpoint");
    std::filesystem::rename(temporary, final);
    campaignGeneration = generation;
    std::printf("[Pikmin Randomizer] CAMPAIGN_SAVED generation=%llu\n", generation);
    std::fflush(stdout);
}
