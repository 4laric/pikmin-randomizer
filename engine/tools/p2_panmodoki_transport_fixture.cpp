// PanModoki (source 38) contested-cargo transport + receipt log checker (#220).
//
// Standalone stdlib-only checker: reads a native.log captured from the
// breadbug contest bridge (pc_p2_breadbug_actor + pc_p2_breadbug_contest_host)
// and verifies the natural tug plus the durable exactly-once receipt, refusing
// injected carries, injected receipts and duplicate deliveries. It builds with
// -Wall -Wextra -Werror and no engine dependency, so a gate script can run it
// against any captured run without linking the natives.
//
// Usage: p2_panmodoki_transport_fixture <native.log>
// Exit: 0 PASS, 1 contract violation, 2 usage/IO error.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <map>
#include <string>
#include <vector>

namespace {
const int kSource = 186081;
const char* const kIdentityPrefix = "onion:p2:38";

struct Event {
    std::string kind;
    int generator = 0;
    int line = 0;
    int carriers = -1;
    int granted = -1;
    int duplicate = 0;
    bool injected = false;
    std::string identity;
    std::string behavior;
};

bool starts_with(const std::string& value, const char* prefix)
{
    const size_t n = std::strlen(prefix);
    return value.size() >= n && value.compare(0, n, prefix) == 0;
}

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

bool has(const std::string& line, const char* token)
{
    return line.find(token) != std::string::npos;
}

void parse_line(const std::string& line, int number, std::vector<Event>& out)
{
    if (line.find("P2_BREADBUG_") == std::string::npos) {
        return;
    }
    Event event;
    event.line = number;
    const std::string gen = field(line, "generator");
    event.generator = gen.empty() ? 0 : std::atoi(gen.c_str());
    if (has(line, "P2_BREADBUG_ACTOR_READY")) {
        event.kind = "ready";
        event.behavior = field(line, "behavior");
    } else if (has(line, "P2_BREADBUG_CONTEST_PROBE")) {
        event.kind = "probe";
        event.carriers = std::atoi(field(line, "carriers").c_str());
        event.injected = field(line, "injected") == "1";
    } else if (has(line, "P2_BREADBUG_CONTEST_GRANT")) {
        event.kind = "grant";
        event.granted = std::atoi(field(line, "granted").c_str());
        const std::string duplicate = field(line, "duplicate");
        event.duplicate = duplicate.empty() ? 0 : std::atoi(duplicate.c_str());
        event.identity = field(line, "identity");
    } else if (has(line, "P2_BREADBUG_CONTEST_STOLEN")) {
        event.kind = "stolen";
        event.carriers = std::atoi(field(line, "carriers").c_str());
    } else if (has(line, "P2_BREADBUG_CONTEST_UPDATE")) {
        event.kind = "update";
        event.carriers = std::atoi(field(line, "carriers").c_str());
        event.behavior = field(line, "outcome");
    } else if (has(line, "P2_BREADBUG_CONTEST_BEGIN")) {
        event.kind = "begin";
        event.identity = field(line, "identity");
    } else if (has(line, "P2_BREADBUG_CONTEST ")) {
        event.kind = "carry";
        event.carriers = std::atoi(field(line, "carriers").c_str());
    } else {
        return;
    }
    out.push_back(event);
}

int fail(const std::string& reason)
{
    std::printf("FAIL P2_PANMODOKI_TRANSPORT %s\n", reason.c_str());
    return 1;
}
} // namespace

int main(int argc, char** argv)
{
    if (argc != 2) {
        std::fprintf(stderr, "usage: %s <native.log>\n", argv[0]);
        return 2;
    }
    std::FILE* file = std::fopen(argv[1], "r");
    if (!file) {
        std::fprintf(stderr, "cannot open %s\n", argv[1]);
        return 2;
    }
    std::vector<Event> events;
    char buffer[4096];
    int number = 0;
    while (std::fgets(buffer, sizeof(buffer), file)) {
        ++number;
        std::string line(buffer);
        while (!line.empty() && (line.back() == '\n' || line.back() == '\r')) {
            line.pop_back();
        }
        parse_line(line, number, events);
    }
    std::fclose(file);

    std::vector<Event> scoped;
    for (const Event& event : events) {
        if (event.generator == kSource) {
            scoped.push_back(event);
        }
    }

    const Event* ready = nullptr;
    const Event* firstCarry = nullptr;
    const Event* firstHeldDrag = nullptr;
    const Event* firstStolen = nullptr;
    const Event* firstGrant = nullptr;
    const Event* firstDuplicate = nullptr;
    std::map<std::string, int> grantedByIdentity;
    int injectedProbes = 0;

    for (const Event& event : scoped) {
        if (event.kind == "ready" && !ready) {
            ready = &event;
        } else if (event.kind == "carry" && event.carriers >= 1 && !firstCarry) {
            firstCarry = &event;
        } else if (event.kind == "update" && event.behavior == "held" &&
                   event.carriers >= 1 && !firstHeldDrag) {
            firstHeldDrag = &event;
        } else if (event.kind == "stolen" && !firstStolen) {
            firstStolen = &event;
        } else if (event.kind == "probe" && event.injected) {
            ++injectedProbes;
        } else if (event.kind == "grant") {
            if (event.granted == 1) {
                if (!firstGrant) {
                    firstGrant = &event;
                }
                grantedByIdentity[event.identity] += 1;
            } else if (event.granted == 0 && event.duplicate == 1 && !firstDuplicate) {
                firstDuplicate = &event;
            }
        }
    }

    if (!ready) {
        return fail("missing P2_BREADBUG_ACTOR_READY bind");
    }
    if (ready->behavior != "P1_Collec_proxy") {
        return fail("unexpected source-38 behavior: " + ready->behavior);
    }
    if (!firstCarry) {
        return fail("no natural carry latch (carriers>=1)");
    }
    if (!firstHeldDrag) {
        return fail("no sustained drag/held tug with carriers>=1");
    }
    if (!firstStolen) {
        return fail("no stolen tug (unresolved contest)");
    }
    if (!firstGrant) {
        return fail("no durable receipt (granted=1)");
    }
    if (firstStolen->line > firstGrant->line) {
        return fail("injected receipt: grant precedes any stolen tug");
    }
    if (!starts_with(firstGrant->identity, kIdentityPrefix)) {
        return fail("receipt identity is not source 38: " + firstGrant->identity);
    }
    for (const std::pair<const std::string, int>& entry : grantedByIdentity) {
        if (entry.second > 1) {
            return fail("duplicate delivery: identity granted more than once: " + entry.first);
        }
    }
    if (!firstDuplicate) {
        return fail("missing exactly-once negative (duplicate=1)");
    }
    if (firstDuplicate->line <= firstGrant->line) {
        return fail("duplicate refusal must follow the first grant");
    }

    std::printf("PASS P2_PANMODOKI_TRANSPORT generator=%d identity=%s carry_line=%d "
                "drag_line=%d stolen_line=%d grant_line=%d duplicate_line=%d injected_probes=%d\n",
                kSource, firstGrant->identity.c_str(), firstCarry->line, firstHeldDrag->line,
                firstStolen->line, firstGrant->line, firstDuplicate->line, injectedProbes);
    return 0;
}
