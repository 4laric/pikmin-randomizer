// Dev tool: fits the body-collision spheres (pc_p2_body_fit.h) to the rest pose of
// every species in a P2 content tree and prints them next to the species'
// retail enemycoll.txt stickable parts. Used to audit which species the shared
// body collision covers and how well the fit matches the drawn mesh.
//
//   p2_body_fit_audit <content-root>
//
// The content layout is <root>/<Family>/<Species>/<prefix>_<Species>_<clip>_NN.mod.
#include "pc_p2_body_fit.h"
#include "pc_p2_pose_bank.h"

#include <algorithm>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <set>
#include <sstream>
#include <string>
#include <vector>

namespace fs = std::filesystem;

static bool readFile(const fs::path& p, std::vector<unsigned char>& out)
{
    std::ifstream in(p, std::ios::binary);
    if (!in) return false;
    out.assign(std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>());
    return !out.empty();
}

// Stickable ('s' first code char) and all parts of a retail enemycoll.txt: "<radius> # radius",
// "{id}", "{code}" triples in file order.
struct SrcPart {
    float radius = 0.f;
    std::string id, code;
};
static std::vector<SrcPart> readEnemyColl(const fs::path& p)
{
    std::vector<SrcPart> parts;
    std::ifstream in(p);
    std::string line;
    SrcPart cur;
    bool haveRadius = false;
    while (std::getline(in, line)) {
        if (line.find("# radius") != std::string::npos) {
            cur = SrcPart();
            cur.radius = std::strtof(line.c_str(), nullptr);
            haveRadius = true;
        } else if (haveRadius && line.find("# id") != std::string::npos) {
            const auto a = line.find('{'), b = line.find('}');
            if (a != std::string::npos && b != std::string::npos) cur.id = line.substr(a + 1, b - a - 1);
        } else if (haveRadius && line.find("# code") != std::string::npos) {
            const auto a = line.find('{'), b = line.find('}');
            if (a != std::string::npos && b != std::string::npos) cur.code = line.substr(a + 1, b - a - 1);
            parts.push_back(cur);
            haveRadius = false;
        }
    }
    return parts;
}

int main(int argc, char** argv)
{
    if (argc < 2) {
        std::fprintf(stderr, "usage: %s <content-root>\n", argv[0]);
        return 2;
    }
    const fs::path root = argv[1];
    std::set<std::string> done;
    for (const auto& fam : fs::directory_iterator(root)) {
        if (!fam.is_directory()) continue;
        for (const auto& sp : fs::directory_iterator(fam.path())) {
            if (!sp.is_directory()) continue;
            const std::string species = sp.path().filename().string();
            if (!done.insert(species + "|" + fam.path().filename().string()).second) continue;
            // Rest clip: first wait-like clip, pose 00.
            fs::path rest;
            for (const char* clip : {"wait1", "wait2", "wait", "wait3", "waitact1", "waitact2"}) {
                for (const auto& f : fs::directory_iterator(sp.path())) {
                    const std::string name = f.path().filename().string();
                    const std::string tail = std::string("_") + species + "_" + clip + "_00.mod";
                    if (name.size() > tail.size() && name.compare(name.size() - tail.size(), tail.size(), tail) == 0) {
                        rest = f.path();
                        break;
                    }
                }
                if (!rest.empty()) break;
            }
            if (rest.empty()) continue;
            std::vector<unsigned char> raw;
            p2pose::Baked baked;
            if (!readFile(rest, raw) || !p2pose::decodeBaked(raw, baked)) {
                std::printf("%s/%s decode_failed\n", fam.path().filename().string().c_str(), species.c_str());
                continue;
            }
            const auto& v = baked.pose.positions;
            p2bodyfit::Table t;
            const bool ok = p2bodyfit::fit(v.size(), [&v](std::size_t i) { return p2bodyfit::V3{v[i].x, v[i].y, v[i].z}; }, t);
            std::printf("%s/%s rest=%s vertices=%zu", fam.path().filename().string().c_str(), species.c_str(),
                        rest.filename().string().c_str(), v.size());
            if (!ok) {
                std::printf(" fit=failed\n");
                continue;
            }
            std::printf(" bounds=%.0f,%.0f,%.0f..%.0f,%.0f,%.0f spheres=%d mean_gap=%.1f max_gap=%.1f fit:",
                        double(t.bounds[0]), double(t.bounds[1]), double(t.bounds[2]), double(t.bounds[3]),
                        double(t.bounds[4]), double(t.bounds[5]), t.count - 1, double(t.meanGap), double(t.maxGap));
            for (int i = 1; i < t.count; ++i)
                std::printf(" r%.0f@(%.0f,%.0f,%.0f)", double(t.spheres[i].radius), double(t.spheres[i].offset.x),
                            double(t.spheres[i].offset.y), double(t.spheres[i].offset.z));
            const fs::path coll = sp.path() / "enemycoll.txt";
            if (fs::exists(coll)) {
                std::printf(" | source enemycoll:");
                for (const SrcPart& p : readEnemyColl(coll)) {
                    if (p.code.empty() || p.code[0] != 's') continue;
                    std::printf(" %s=r%.0f", p.id.c_str(), double(p.radius));
                }
            }
            std::printf("\n");
        }
    }
    return 0;
}
