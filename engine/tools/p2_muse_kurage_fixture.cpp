// Muse l58 Kurage57 generated-birth log observer (#498, parent #243).
//
// Additive, dependency-free observer: reads a native.log (file argument or
// stdin) and correlates the SAME generated slot/generator across the three
// birth markers a natural generated Kurage spawn must emit:
//
//   1. P2_SEED_RESOLVE source_id=57 target=<uid>      (genteki.cpp birth)
//   2. P2_GENERATED_PLACEMENT source_id=57 target=<uid> generator=<gen> bound=1
//      (reviewed muse-placement l52/#492, consumed as candidate 558d12af;
//      only the accepted slot 689702860 passes)
//   3. P2_KURAGE_TEKI_READY generator=<gen> +
//      P2_KURAGE_CORPSE_READY generator=<gen> ... receipt=corpse:kurage:<gen>
//
// The verdict is PASS only for the accepted slot (resolve target ==
// placement target == 689702860) with the triple-chain tie (placement
// generator == teki generator == corpse receipt generator).
//
// Exit 0 with KURAGE_GENERATED_BIRTH_PASS on full agreement, exit 1 with
// KURAGE_GENERATED_BIRTH_FAIL plus the exact reason otherwise. The legacy
// p2-kurage-teki.txt sidecar auto-bind (generator 201001, TEKI_READY with no
// resolve/placement markers) is FAIL ("auto-bind"), never a generated
// identity. Any injected/health_zero taint touching the birth markers or the
// correlated slot/generator is FAIL.
//
// This tool observes logs only. It links against nothing, touches no family
// module, and is intentionally NOT registered as an engine replacement-main
// target (shared-hook request to #491 deferred until the marker contract
// stabilizes across the four consumer lanes).
//
// Usage: p2_muse_kurage_fixture [native.log]   (stdin when omitted)
#include <cctype>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <set>
#include <string>
#include <vector>

namespace {

const char* kSourceToken = "source_id=57";
// Reviewed Kurage57 generated slot (muse-placement l52 MUSE_GENERATED_SLOTS).
const char* kAcceptedSlot = "689702860";

bool hasToken(const std::string& line, const char* token) {
    return line.find(token) != std::string::npos;
}

// Extract the unsigned value after key= (digits only). Returns false when the
// key is absent or not followed by digits.
bool fieldValue(const std::string& line, const char* key, std::string& out) {
    std::string k(key);
    k += "=";
    std::string::size_type pos = line.find(k);
    if (pos == std::string::npos) return false;
    pos += k.size();
    std::string::size_type end = pos;
    while (end < line.size() && std::isdigit((unsigned char)line[end])) ++end;
    if (end == pos) return false;
    out = line.substr(pos, end - pos);
    return true;
}

bool tainted(const std::string& line) {
    std::string lower(line);
    for (char& c : lower) c = (char)std::tolower((unsigned char)c);
    return lower.find("injected") != std::string::npos ||
           lower.find("health_zero") != std::string::npos;
}

bool isBirthLine(const std::string& line) {
    return hasToken(line, "P2_SEED_RESOLVE") ||
           hasToken(line, "P2_GENERATED_PLACEMENT") ||
           hasToken(line, "P2_KURAGE_TEKI_READY") ||
           hasToken(line, "P2_KURAGE_CORPSE_READY");
}

void fail(const std::string& reason) {
    std::printf("KURAGE_GENERATED_BIRTH_FAIL %s\n", reason.c_str());
    std::fflush(stdout);
}

}  // namespace

int main(int argc, char** argv) {
    std::vector<std::string> lines;
    if (argc > 1) {
        FILE* f = std::fopen(argv[1], "rb");
        if (!f) {
            std::printf("KURAGE_GENERATED_BIRTH_FAIL cannot open %s\n", argv[1]);
            return 1;
        }
        char buf[4096];
        std::string cur;
        size_t n;
        while ((n = std::fread(buf, 1, sizeof(buf), f)) > 0) {
            for (size_t i = 0; i < n; ++i) {
                if (buf[i] == '\n') { lines.push_back(cur); cur.clear(); }
                else if (buf[i] != '\r') { cur += buf[i]; }
            }
        }
        if (!cur.empty()) lines.push_back(cur);
        std::fclose(f);
    } else {
        std::string cur;
        char c;
        while (std::cin.get(c)) {
            if (c == '\n') { lines.push_back(cur); cur.clear(); }
            else if (c != '\r') { cur += c; }
        }
        if (!cur.empty()) lines.push_back(cur);
    }
    if (lines.empty()) { fail("empty log: no generated-birth markers"); return 1; }

    std::set<std::string> resolveTargets, placementTargets, tekiGens, corpseGens;
    std::set<std::string> placedGens;
    std::vector<std::string> taintedBirth;
    bool placementRefused = false;
    std::string refusedTarget;

    for (size_t li = 0; li < lines.size(); ++li) {
        const std::string& line = lines[li];
        std::string v;
        if (hasToken(line, "P2_SEED_RESOLVE") && hasToken(line, kSourceToken)) {
            if (tainted(line)) { taintedBirth.push_back(line); continue; }
            if (fieldValue(line, "target", v)) resolveTargets.insert(v);
        }
        if (hasToken(line, "P2_GENERATED_PLACEMENT") && hasToken(line, kSourceToken)) {
            if (tainted(line)) { taintedBirth.push_back(line); continue; }
            std::string target, bound, placedGen;
            fieldValue(line, "target", target);
            fieldValue(line, "bound", bound);
            // Reviewed contract carries generator= between target and bound;
            // pre-contract markers omit it (fallback below).
            fieldValue(line, "generator", placedGen);
            if (bound == "1") {
                placementTargets.insert(target);
                if (!placedGen.empty()) placedGens.insert(placedGen);
            } else { placementRefused = true; refusedTarget = target; }
        }
        if (hasToken(line, "P2_KURAGE_TEKI_READY")) {
            if (tainted(line)) { taintedBirth.push_back(line); continue; }
            if (fieldValue(line, "generator", v)) tekiGens.insert(v);
        }
        if (hasToken(line, "P2_KURAGE_CORPSE_READY")) {
            if (tainted(line)) { taintedBirth.push_back(line); continue; }
            std::string gen, receipt;
            // Receipt token is "receipt=corpse:kurage:<id>" (colon, not '=').
            std::string::size_type rp = line.find("receipt=corpse:kurage:");
            if (rp != std::string::npos) {
                std::string::size_type rs = rp + std::strlen("receipt=corpse:kurage:");
                std::string::size_type re = rs;
                while (re < line.size() && std::isdigit((unsigned char)line[re])) ++re;
                if (re > rs) receipt = line.substr(rs, re - rs);
            }
            if (fieldValue(line, "generator", gen) && !receipt.empty()) {
                if (gen != receipt) {
                    fail("corpse receipt generator=" + gen +
                         " disagrees with receipt id=" + receipt);
                    return 1;
                }
                corpseGens.insert(gen);
            }
        }
    }

    if (!taintedBirth.empty()) {
        fail("injected-birth taint on birth markers: " +
             taintedBirth[0].substr(0, 160));
        return 1;
    }
    if (resolveTargets.empty()) {
        if (!tekiGens.empty() || !corpseGens.empty()) {
            std::string gen = tekiGens.empty() ? *corpseGens.begin() : *tekiGens.begin();
            fail("auto-bind without generated markers: Kurage binding present "
                 "(generator=" + gen + ") but no P2_SEED_RESOLVE source_id=57; "
                 "legacy sidecar binds (e.g. generator 201001) are not generated "
                 "identities");
            return 1;
        }
        fail("missing P2_SEED_RESOLVE source_id=57");
        return 1;
    }
    if (placementTargets.empty()) {
        if (placementRefused) {
            fail("generated placement refused source_id=57 target=" + refusedTarget +
                 " (bound=0)");
            return 1;
        }
        fail("missing P2_GENERATED_PLACEMENT source_id=57 bound=1 "
             "(expected from reviewed muse-placement l52 bind)");
        return 1;
    }
    if (tekiGens.empty()) { fail("missing P2_KURAGE_TEKI_READY generator marker"); return 1; }
    if (corpseGens.empty()) { fail("missing P2_KURAGE_CORPSE_READY receipt marker"); return 1; }

    std::set<std::string> slots(resolveTargets.begin(), resolveTargets.end());
    slots.insert(placementTargets.begin(), placementTargets.end());
    if (slots.size() > 1) {
        fail("resolve/placement slot disagreement");
        return 1;
    }
    const std::string& slot = *slots.begin();
    if (slot != kAcceptedSlot) {
        fail(std::string("slot-not-accepted: slot=") + slot +
             " is not the reviewed Kurage57 generated slot " + kAcceptedSlot);
        return 1;
    }
    std::set<std::string> gens(tekiGens.begin(), tekiGens.end());
    gens.insert(corpseGens.begin(), corpseGens.end());
    if (gens.size() > 1) {
        fail("Kurage binding generator disagreement");
        return 1;
    }
    const std::string& gen = *gens.begin();
    if (!placedGens.empty()) {
        if (placedGens.size() > 1) {
            fail("placement generator disagreement");
            return 1;
        }
        if (*placedGens.begin() != gen) {
            fail("actor disagreement: placement generator=" + *placedGens.begin() +
                 " Kurage generator=" + gen + "; same spawned actor required");
            return 1;
        }
    } else if (slot != gen) {
        fail("slot/generator disagreement: seed slot=" + slot +
             " Kurage generator=" + gen + "; same spawned actor required");
        return 1;
    }
    for (size_t li = 0; li < lines.size(); ++li) {
        const std::string& line = lines[li];
        if (tainted(line) &&
            (isBirthLine(line) || line.find(slot) != std::string::npos)) {
            fail("injected-birth taint on correlated slot/generator " + slot + ": " +
                 line.substr(0, 160));
            return 1;
        }
    }

    std::printf("KURAGE_GENERATED_BIRTH_PASS slot=%s generator=%s "
                "resolve+placement+teki+corpse agree\n", slot.c_str(), gen.c_str());
    std::fflush(stdout);
    return 0;
}
