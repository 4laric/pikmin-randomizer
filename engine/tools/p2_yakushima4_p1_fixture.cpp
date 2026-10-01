// yakushima_4 P1 floor-1 staging writer + boot-observation checker (#161).
//
// Engine-independent, stdlib-only, standalone. It is never added to a game
// target: the lane builds it directly with the same MinGW toolchain used for
// the private engine build. Two modes:
//   stage <floor> <survivors> <health> <token> <out>  -> write the native
//     P2_CAVE_ENTRY_1 line consumed by pc_p2_cave.cpp (bounds-validated).
//   check <native.log> -> verify a real floor-1 boot (P2_CAVE_READY floor=1
//     plus a P2_CAVE_NAV sample with the captain walking inside the anchor).
// It never infers unit staging from nav lines.
#include <cstdio>
#include <filesystem>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#include "pc_p2_cave_generate.h"

namespace {
const char* const kEntryVersion = "P2_CAVE_ENTRY_1";

std::string field(const std::string& line, const char* key)
{
    const std::string needle = std::string(key) + "=";
    const size_t at = line.find(needle);
    if (at == std::string::npos) {
        return std::string();
    }
    const size_t from = at + needle.size();
    size_t to = from;
    while (to < line.size() && line[to] != ' ' && line[to] != '\t') {
        ++to;
    }
    return line.substr(from, to - from);
}

int fail(const std::string& reason)
{
    std::printf("FAIL P2_YAKUSHIMA4_P1 %s\n", reason.c_str());
    return 1;
}
} // namespace

static int stage(int argc, char** argv)
{
    if (argc != 7) {
        std::fprintf(stderr, "usage: %s stage <floor> <survivors> <health> <token> <out>\n", argv[0]);
        return 2;
    }
    const int floor = std::atoi(argv[2]);
    const int survivors = std::atoi(argv[3]);
    const double health = std::atof(argv[4]);
    const std::string token = argv[5];
    if (floor != 1 && floor != 2) {
        return fail("entry floor must be 1 or 2");
    }
    if (survivors < 1 || survivors > 100) {
        return fail("entry survivors must be 1..100");
    }
    if (!(health > 0.0 && health <= 1.0)) {
        return fail("entry health must be in (0, 1]");
    }
    if (token.empty() || token.find_first_of(" \t") != std::string::npos) {
        return fail("entry token must be a single nonempty word");
    }
    std::FILE* out = std::fopen(argv[6], "w");
    if (!out) {
        std::fprintf(stderr, "cannot write %s\n", argv[6]);
        return 2;
    }
    std::fprintf(out, "%s %s %d %.9g %d\n", kEntryVersion, token.c_str(), floor, health, survivors);
    std::fclose(out);
    std::printf("PASS P2_YAKUSHIMA4_P1 stage floor=%d survivors=%d health=%.9g token=%s\n",
                floor, survivors, health, token.c_str());
    return 0;
}

static int check(int argc, char** argv)
{
    if (argc != 3) {
        std::fprintf(stderr, "usage: %s check <native.log>\n", argv[0]);
        return 2;
    }
    std::FILE* file = std::fopen(argv[2], "r");
    if (!file) {
        std::fprintf(stderr, "cannot open %s\n", argv[2]);
        return 2;
    }
    bool ready = false;
    bool readyFloor1 = false;
    int survivors = 0;
    int navFloor1 = 0;
    int walkInside = 0;
    char buffer[8192];
    while (std::fgets(buffer, sizeof(buffer), file)) {
        std::string line(buffer);
        while (!line.empty() && (line.back() == '\n' || line.back() == '\r')) {
            line.pop_back();
        }
        if (line.find("P2_CAVE_READY") != std::string::npos) {
            ready = true;
            const int floor = std::atoi(field(line, "floor").c_str());
            survivors = std::atoi(field(line, "survivors").c_str());
            if (floor == 1) {
                readyFloor1 = true;
            }
        } else if (line.find("P2_CAVE_NAV") != std::string::npos) {
            if (std::atoi(field(line, "floor").c_str()) == 1) {
                ++navFloor1;
                if (field(line, "inside") == "1" && field(line, "walk") == "1") {
                    ++walkInside;
                }
            }
        }
    }
    std::fclose(file);
    if (!ready) {
        return fail("no P2_CAVE_READY boot marker");
    }
    if (!readyFloor1) {
        return fail("boot marker is not floor 1");
    }
    if (survivors < 1 || survivors > 100) {
        return fail("boot survivor count out of range");
    }
    if (navFloor1 == 0) {
        return fail("no P2_CAVE_NAV floor-1 samples");
    }
    if (walkInside == 0) {
        return fail("captain never walked inside the floor-1 anchor");
    }
    std::printf("PASS P2_YAKUSHIMA4_P1 check floor=1 survivors=%d nav=%d walk_inside=%d "
                "collision_routes=observed unit_staging=NOT_OBSERVED\n",
                survivors, navFloor1, walkInside);
    return 0;
}

static int generate(int argc, char** argv)
{
    if (argc != 3) {
        std::fprintf(stderr, "usage: %s generate <p2-cave-generate.txt>\n", argv[0]);
        return 2;
    }
    const std::filesystem::path sidecar(argv[2]);
    if (!std::filesystem::is_regular_file(sidecar)) {
        std::fprintf(stderr, "cannot find %s\n", argv[2]);
        return 2;
    }
    std::error_code error;
    const std::filesystem::path previous = std::filesystem::current_path();
    std::filesystem::current_path(sidecar.parent_path(), error);
    if (error) {
        std::fprintf(stderr, "cannot enter %s\n", sidecar.parent_path().string().c_str());
        return 2;
    }
    const bool ok = pc_p2_cave_generate_run();
    std::filesystem::current_path(previous, error);
    if (!ok) {
        std::printf("FAIL P2_YAKUSHIMA4_P1 generator refused the sidecar\n");
        return 1;
    }
    std::printf("PASS P2_YAKUSHIMA4_P1 generator staged real unit pool\n");
    return 0;
}

int main(int argc, char** argv)
{
    if (argc >= 2 && std::strcmp(argv[1], "stage") == 0) {
        return stage(argc, argv);
    }
    if (argc >= 2 && std::strcmp(argv[1], "check") == 0) {
        return check(argc, argv);
    }
    if (argc >= 2 && std::strcmp(argv[1], "generate") == 0) {
        return generate(argc, argv);
    }
    std::fprintf(stderr, "usage: %s stage|check|generate ...\n", argv[0]);
    return 2;
}
