// Standalone probe for the data-driven campaign proxy table (#871).
#include "pc_p2_proxy_table.h"

#include <cstdio>
#include <sstream>
#include <string>

namespace {

int failures = 0;

bool check(bool ok, const char* what) {
    if (!ok) {
        std::fprintf(stderr, "FAIL %s\n", what);
        ++failures;
    }
    return ok;
}

bool allowAll(unsigned) { return true; }
bool reject17(unsigned id) { return id != 17; }

void testValid() {
    std::istringstream in(
        "P2_PROXY_CAMPAIGN_1 3\n"
        "2 Kochappy 3\n"
        "17 Bulborb 4\n"
        "10 Hana 0\n");
    const p2proxy::Table table = p2proxy::parse(in, allowAll, 36);
    check(table.valid, "valid table accepted");
    check(table.rows.size() == 3, "valid table has 3 rows");
    check(table.error.empty(), "valid table has empty error");
    const p2proxy::Row* bySource = p2proxy::bySource(table, 2);
    check(bySource != nullptr && bySource->species == "Kochappy" && bySource->host == 3,
          "bySource 2");
    const p2proxy::Row* bySpecies = p2proxy::bySpecies(table, std::string("Hana"));
    check(bySpecies != nullptr && bySpecies->source == 10 && bySpecies->host == 0,
          "bySpecies Hana");
    check(p2proxy::bySource(table, 99) == nullptr, "bySource unknown null");
    check(p2proxy::bySpecies(table, std::string("Missing")) == nullptr, "bySpecies unknown null");
    const p2proxy::Row* middle = p2proxy::bySource(table, 17);
    check(middle != nullptr && middle->species == "Bulborb" && middle->host == 4,
          "bySource 17");
}

void expectInvalid(const char* what, const std::string& text, const char* expectedError,
                   bool (*bindable)(unsigned) = allowAll) {
    std::istringstream in(text);
    const p2proxy::Table table = p2proxy::parse(in, bindable, 36);
    char message[256];
    std::snprintf(message, sizeof(message), "%s invalid", what);
    check(!table.valid, message);
    std::snprintf(message, sizeof(message), "%s empty rows", what);
    check(table.rows.empty(), message);
    std::snprintf(message, sizeof(message), "%s has error", what);
    check(!table.error.empty(), message);
    std::snprintf(message, sizeof(message), "%s error is '%s'", what, expectedError);
    check(table.error.find(expectedError) != std::string::npos, message);
}

void testViolations() {
    expectInvalid("bad header", "P2_BAD 1\n2 Foo 3\n", "bad header token");
    expectInvalid("count zero", "P2_PROXY_CAMPAIGN_1 0\n", "bad count");
    expectInvalid("count too big", "P2_PROXY_CAMPAIGN_1 65\n", "bad count");
    expectInvalid("fewer rows",
                  "P2_PROXY_CAMPAIGN_1 2\n"
                  "2 Foo 3\n",
                  "fewer rows than count");
    expectInvalid("more rows",
                  "P2_PROXY_CAMPAIGN_1 1\n"
                  "2 Foo 3\n"
                  "10 Bar 4\n",
                  "trailing data");
    expectInvalid("trailing data",
                  "P2_PROXY_CAMPAIGN_1 1\n"
                  "2 Foo 3\n"
                  "extra\n",
                  "trailing data");
    expectInvalid("host negative",
                  "P2_PROXY_CAMPAIGN_1 1\n"
                  "2 Foo -1\n",
                  "bad host type");
    expectInvalid("host too big",
                  "P2_PROXY_CAMPAIGN_1 1\n"
                  "2 Foo 36\n",
                  "bad host type");
    for (int host : {1, 5, 7, 10, 12, 13, 14, 21, 22, 23, 26, 27, 28, 29, 34, 35}) {
        const std::string text = "P2_PROXY_CAMPAIGN_1 1\n2 Foo " + std::to_string(host) + "\n";
        expectInvalid("unsafe host", text, "unsafe host type");
    }
    for (int host : {0, 2, 3, 4, 6, 8, 9, 11, 15, 16, 17, 18, 19, 20, 24, 25, 30, 31, 32, 33})
        check(p2proxy::safeHost(host), "safe host accepted");
    expectInvalid("species leading digit",
                  "P2_PROXY_CAMPAIGN_1 1\n"
                  "2 1Bad 3\n",
                  "bad species");
    expectInvalid("species hyphen",
                  "P2_PROXY_CAMPAIGN_1 1\n"
                  "2 Bad-Name 3\n",
                  "bad species");
    expectInvalid("species too long",
                  "P2_PROXY_CAMPAIGN_1 1\n"
                  "2 Abcdefghijklmnopqrstuvwxyz1234567 3\n",
                  "bad species");
    expectInvalid("species leading underscore",
                  "P2_PROXY_CAMPAIGN_1 1\n"
                  "2 _Foo 3\n",
                  "bad species");
    expectInvalid("duplicate source",
                  "P2_PROXY_CAMPAIGN_1 2\n"
                  "2 Foo 3\n"
                  "2 Bar 4\n",
                  "duplicate source");
    expectInvalid("duplicate species",
                  "P2_PROXY_CAMPAIGN_1 2\n"
                  "2 Foo 3\n"
                  "10 Foo 4\n",
                  "duplicate species");
    expectInvalid("rejected bindable", "P2_PROXY_CAMPAIGN_1 1\n17 Foo 3\n", "source not bindable", reject17);
    expectInvalid("empty input", "", "bad header");
    expectInvalid("bad source id",
                  "P2_PROXY_CAMPAIGN_1 1\n"
                  "99999999999 Foo 3\n",
                  "bad source id");
    // Host range boundary against tekiTypeCount: 33 is the largest safe host,
    // so with tekiTypeCount=34 it is both in-range and safe, while 34 is out
    // of range. (With tekiTypeCount=36, host 35 is in range but unsafe.)
    {
        std::istringstream okIn("P2_PROXY_CAMPAIGN_1 1\n2 Foo 33\n");
        check(p2proxy::parse(okIn, allowAll, 34).valid, "host tekiTypeCount-1 valid");
    }
    {
        std::istringstream badIn("P2_PROXY_CAMPAIGN_1 1\n2 Foo 34\n");
        const p2proxy::Table table = p2proxy::parse(badIn, allowAll, 34);
        check(!table.valid && table.error.find("bad host type") != std::string::npos,
              "host tekiTypeCount invalid");
    }
    {
        std::istringstream badIn("P2_PROXY_CAMPAIGN_1 1\n2 Foo 35\n");
        const p2proxy::Table table = p2proxy::parse(badIn, allowAll, 36);
        check(!table.valid && table.error.find("unsafe host type") != std::string::npos,
              "host 35 unsafe with tekiTypeCount 36");
    }
    // Species length boundary: 32 chars valid, 33 invalid.
    {
        const std::string ok32(32, 'A');
        std::istringstream okIn("P2_PROXY_CAMPAIGN_1 1\n2 " + ok32 + " 3\n");
        check(p2proxy::parse(okIn, allowAll, 36).valid, "32-char species valid");
    }
    // Count boundary: 64 rows valid, 65 invalid (65 already covered above).
    {
        std::string text = "P2_PROXY_CAMPAIGN_1 64\n";
        for (int i = 0; i < 64; ++i)
            text += std::to_string(1000 + i) + " S" + std::to_string(i) + " 3\n";
        std::istringstream okIn(text);
        const p2proxy::Table table = p2proxy::parse(okIn, allowAll, 36);
        check(table.valid && table.rows.size() == 64, "count 64 valid");
    }
    // nullptr bindable rejects everything.
    {
        std::istringstream badIn("P2_PROXY_CAMPAIGN_1 1\n2 Foo 3\n");
        const p2proxy::Table table = p2proxy::parse(badIn, nullptr, 36);
        check(!table.valid && table.error.find("source not bindable") != std::string::npos,
              "nullptr bindable rejects");
    }
    // Source 0 parses when bindable allows it.
    {
        std::istringstream okIn("P2_PROXY_CAMPAIGN_1 1\n0 Foo 3\n");
        check(p2proxy::parse(okIn, allowAll, 36).valid, "source 0 valid with allowAll");
    }
}

void testBindableCallback() {
    std::istringstream okIn(
        "P2_PROXY_CAMPAIGN_1 1\n"
        "2 Foo 3\n");
    check(p2proxy::parse(okIn, reject17, 36).valid, "bindable accepts 2");
    std::istringstream badIn(
        "P2_PROXY_CAMPAIGN_1 1\n"
        "17 Foo 3\n");
    const p2proxy::Table table = p2proxy::parse(badIn, reject17, 36);
    check(!table.valid && table.rows.empty(), "bindable rejects 17");
}

bool isStaticStub(unsigned id) { return id == 54 || id == 9; }

void testStaticFilter() {
    std::istringstream in(
        "P2_PROXY_CAMPAIGN_1 3\n"
        "54 MamutaProxy 24\n"
        "2 Kochappy 3\n"
        "9 KoganeProxy 3\n");
    const p2proxy::Table table = p2proxy::parse(in, allowAll, 36);
    check(table.valid && table.rows.size() == 3, "static filter input valid");
    const p2proxy::Table filtered = p2proxy::withoutStaticSources(table, isStaticStub);
    check(filtered.valid, "static filter stays valid");
    check(filtered.rows.size() == 1, "static filter drops two rows");
    check(filtered.rows.size() == 1 && filtered.rows[0].source == 2
              && filtered.rows[0].species == "Kochappy",
          "static filter keeps non-static row");
    // nullptr predicate leaves the table untouched.
    const p2proxy::Table untouched = p2proxy::withoutStaticSources(table, nullptr);
    check(untouched.valid && untouched.rows.size() == 3, "static filter nullptr passthrough");
}

}  // namespace

int main() {
    testValid();
    testViolations();
    testBindableCallback();
    testStaticFilter();
    if (failures == 0) {
        std::printf("PASS p2_proxy_table\n");
        return 0;
    }
    std::fprintf(stderr, "FAIL p2_proxy_table: %d failures\n", failures);
    return 1;
}
