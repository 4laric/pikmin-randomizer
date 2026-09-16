// Standalone preflight self-check for lane muse-fixturetools (l67, #507).
//
// Validates the same input contract the Python preflight adapter enforces,
// without engine headers or game linkage:
//
//   p2_muse_fixturetools_fixture <source-dir> <build-dir>
//
// exit 0: source carries CMakeLists.txt + pc_port/pc_main.cpp, and the build
//   directory carries CMakeCache.txt with CMAKE_GENERATOR=Ninja.
// exit 1: any check fails. exit 2: wrong argv.
//
// Markers (stdout, one per line):
//   P2_MUSE_FIXTURETOOLS_CHECK <name> ok=1|0
//   P2_MUSE_FIXTURETOOLS_PREFLIGHT_OK|FAIL
//
// Standalone compile (MinGW, mirrors the l59 gate1-probe pattern):
//   g++ -std=gnu++17 -Wall -Wextra -Werror -DP2_MUSE_FIXTURETOOLS_STANDALONE
//     tools/p2_muse_fixturetools_fixture.cpp -o p2_muse_fixturetools_probe
// Also built through scripts/build_pikmin2_fixture.py (worktree copy with
// the #437 response-file expansion) for provenance; the maintained copy
// predates that support and rejects the production link line.

#include <cstdio>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>

namespace {

bool file_exists(const std::string& path) {
    std::ifstream stream(path.c_str(), std::ios::binary);
    return stream.good();
}

bool cache_has_ninja_generator(const std::string& cache_path) {
    std::ifstream stream(cache_path.c_str());
    if (!stream.good()) {
        return false;
    }
    std::string line;
    while (std::getline(stream, line)) {
        if (line.compare(0, 16, "CMAKE_GENERATOR:") == 0) {
            std::string::size_type eq = line.find('=');
            if (eq != std::string::npos && line.substr(eq + 1) == "Ninja") {
                return true;
            }
            return false;
        }
    }
    return false;
}

int check(const char* name, bool ok) {
    std::printf("P2_MUSE_FIXTURETOOLS_CHECK %s ok=%d\n", name, ok ? 1 : 0);
    return ok ? 0 : 1;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 3) {
        std::fprintf(stderr,
                     "usage: %s <source-dir> <build-dir>\n",
                     argc > 0 ? argv[0] : "p2_muse_fixturetools_fixture");
        return 2;
    }
    const std::string source = argv[1];
    const std::string build = argv[2];
    int failures = 0;
    failures += check("source-cmakelists",
                      file_exists(source + "/CMakeLists.txt"));
    failures += check("source-main",
                      file_exists(source + "/pc_port/pc_main.cpp"));
    const std::string cache = build + "/CMakeCache.txt";
    failures += check("build-cache", file_exists(cache));
    failures += check("generator-ninja",
                      cache_has_ninja_generator(cache));
    if (failures == 0) {
        std::printf("P2_MUSE_FIXTURETOOLS_PREFLIGHT_OK\n");
        return 0;
    }
    std::printf("P2_MUSE_FIXTURETOOLS_PREFLIGHT_FAIL failures=%d\n",
                failures);
    return 1;
}
