#include "pc_p2_original_resource_contents.h"
#include <cassert>
#include <cmath>
#include <iostream>
using namespace p2originalresource;
struct Fake : Engine {
    std::string calls;
    bool manager = false, group = false, honey = true, pellet = true, spray = false;
    float roll = 0.25f;
    bool failFirstHoney = false, checkedPending = false;
    unsigned honeyAttempts = 0;
    EggContents* reentrant = nullptr;
    std::vector<ChildOutcome> births;
    float randFloat() noexcept override { calls += "F"; return roll; }
    int randInt(int count) noexcept override { assert(count == 3); calls += "I"; return 2; }
    bool sprayMade(HoneyKind) noexcept override { calls += "S"; return spray; }
    bool mititeManagerAvailable() noexcept override { calls += "M"; return manager; }
    bool birthPellet(const ChildOutcome& c) noexcept override { calls += "P"; births.push_back(c); return pellet; }
    bool birthHoney(HoneyKind, const ChildOutcome& c) noexcept override {
        calls += "H"; births.push_back(c);
        if (reentrant) {
            ContentsRecord pending; std::string error;
            const auto before = calls;
            assert(!reentrant->generate(c.identity.source, P2EggConfig{}, {}, *this, pending, error));
            assert(!pending.complete && error == "original Egg contents generation pending" && calls == before);
            checkedPending = true;
        }
        const bool success = honey && !(failFirstHoney && honeyAttempts == 0);
        ++honeyAttempts;
        if (success) (void)randFloat(); // actual ItemHoney::init(nullptr), before type overwrite
        return success;
    }
    bool birthMititeGroup(const ChildOutcome& c) noexcept override { calls += "G"; births.push_back(c); return group; }
};
int main() {
    SourceIdentity id{std::string(64, 'a'), 19, 0, 7, 4};
    P2EggConfig cfg; cfg.forcedDropType = 5; // Mitites, after mandatory roll
    EggContents journal; Fake e; ContentsRecord r; std::string error;
    assert(journal.generate(id, cfg, {1, 2, 3}, e, r, error));
    assert(e.calls == "FMHF" && r.type == P2EggDropType::Mitites);
    assert(r.children.size() == 1 && r.children[0].identity.slot == 1);
    assert(r.children[0].velocity.y == 250 && r.children[0].position.y == 4);
    assert(journal.generate(id, cfg, {}, e, r, error) && e.calls == "FMHF");
    // Existing manager calls group before fallback, and changes backup velocity.
    id.ordinal = 1; e = Fake{}; e.manager = true;
    assert(journal.generate(id, cfg, {1, 2, 3}, e, r, error));
    assert(e.calls == "FMFGHF" && r.children.size() == 2);
    assert(!r.children[0].born && r.children[1].born);
    assert(r.children[0].position.y == 2 && r.children[0].mititeCount == 10);
    assert(std::fabs(r.children[0].facing - 1.5707963f) < 0.00001f);
    assert(r.children[1].velocity.y == 200);
    assert(!journal.consume(r.children[0].identity, error));
    assert(journal.consume(r.children[1].identity, error));
    assert(journal.consume(r.children[1].identity, error));
    // Successful native group never substitutes nectar.
    id.ordinal = 2; e = Fake{}; e.manager = e.group = true;
    assert(journal.generate(id, cfg, {}, e, r, error));
    assert(e.calls == "FMFG" && r.children.size() == 1 && r.children[0].born);
    // Double nectar still attempts second birth when first fails.
    id.ordinal = 3; cfg.forcedDropType = 4; e = Fake{}; e.honey = false;
    assert(journal.generate(id, cfg, {}, e, r, error));
    assert(e.calls == "FFHH" && !r.children[0].born && !r.children[1].born);
    assert(std::fabs(r.children[0].velocity.x - 50) < 0.00001f);
    assert(std::fabs(r.children[1].velocity.x + 50) < 0.00001f);
    auto saved = journal.snapshot(); EggContents resumed;
    assert(resumed.restore(saved, error));
    const auto restored = resumed.snapshot();
    assert(restored[1].children[1].consumed);
    e = Fake{};
    assert(resumed.generate(id, cfg, {}, e, r, error) && e.calls.empty());
    assert(!r.children[0].born && !r.children[1].born);
    // Fresh epoch, activation, fingerprint and UID are independent identities.
    SourceIdentity next = id; next.epoch++;
    assert(resumed.generate(next, cfg, {}, e, r, error) && e.calls == "FFHFHF");
    // Real successful ItemHoney init consumes RNG between double births.
    SourceIdentity doubleId = id; doubleId.ordinal = 90;
    e = Fake{}; e.reentrant = &resumed;
    assert(resumed.generate(doubleId, cfg, {}, e, r, error));
    assert(e.calls == "FFHFHF" && e.checkedPending && r.children[0].born && r.children[1].born);
    doubleId.ordinal++; e = Fake{}; e.failFirstHoney = true;
    assert(resumed.generate(doubleId, cfg, {}, e, r, error));
    assert(e.calls == "FFHHF" && !r.children[0].born && r.children[1].born);
    next = id; next.activation++; e = Fake{};
    assert(resumed.generate(next, cfg, {}, e, r, error) && e.calls == "FFHFHF");
    next = id; next.fingerprint[0] = 'b'; e = Fake{};
    assert(resumed.generate(next, cfg, {}, e, r, error) && e.calls == "FFHFHF");
    next = id; next.uid++; e = Fake{};
    assert(resumed.generate(next, cfg, {}, e, r, error) && e.calls == "FFHFHF");
    // Forced pellet still consumes float roll, then randInt before native birth.
    next = id; next.ordinal = 4; cfg.forcedDropType = 2; e = Fake{}; e.pellet = false;
    assert(resumed.generate(next, cfg, {}, e, r, error));
    assert(e.calls == "FIP" && r.children[0].pelletColor == 2 && !r.children[0].born);
    assert(resumed.generate(next, cfg, {}, e, r, error) && e.calls == "FIP");
    // Source playData check is live and selective, never cached config flags.
    next.ordinal++; cfg.forcedDropType = 6; e = Fake{};
    assert(resumed.generate(next, cfg, {}, e, r, error));
    assert(e.calls == "FSHF" && r.children[0].kind == ChildKind::Nectar);
    next.ordinal++; e = Fake{}; e.spray = true;
    assert(resumed.generate(next, cfg, {}, e, r, error));
    assert(e.calls == "FSHF" && r.children[0].kind == ChildKind::Spicy);
    next.ordinal++; cfg.checkHasSpray = false; e = Fake{};
    assert(resumed.generate(next, cfg, {}, e, r, error));
    assert(e.calls == "FHF" && r.children[0].kind == ChildKind::Spicy);
    // Invalid restore is atomic; no accidental old-source replay after failure.
    auto corrupt = saved; corrupt[0].children[0].identity.source.uid++;
    assert(!resumed.restore(corrupt, error)); e = Fake{};
    assert(resumed.generate(id, cfg, {}, e, r, error) && e.calls.empty());
    corrupt = saved; corrupt.push_back(corrupt[0]); assert(!resumed.restore(corrupt, error));
    corrupt = saved; corrupt[0].complete = false; assert(!resumed.restore(corrupt, error));
    corrupt = saved; corrupt[0].children.clear(); assert(!resumed.restore(corrupt, error));
    corrupt = saved; corrupt[2].children[0].born = false; assert(!resumed.restore(corrupt, error));
    for (unsigned i = 0; i < 5; ++i) {
        SourceIdentity invalid = id;
        if (i == 0) invalid.fingerprint.resize(63);
        if (i == 1) invalid.fingerprint[0] = 'A';
        if (i == 2) invalid.fingerprint[0] = 'g';
        if (i == 3) invalid.uid = 0;
        if (i == 4) invalid.activation = 0;
        e = Fake{};
        assert(!resumed.generate(invalid, cfg, {}, e, r, error) && e.calls.empty());
        corrupt = saved; corrupt[0].source = invalid;
        corrupt[0].children[0].identity.source = invalid;
        assert(!resumed.restore(corrupt, error));
    }
    next = id; next.ordinal = 99; next.epoch = 0; e = Fake{};
    assert(resumed.generate(next, cfg, {}, e, r, error)); // source epoch zero is valid
    // Uncovered roll remainder retains source default SingleNectar.
    next.ordinal++; cfg = P2EggConfig{}; e = Fake{};
    assert(resumed.generate(next, cfg, {}, e, r, error));
    assert(e.calls == "FHF" && r.type == P2EggDropType::SingleNectar);
    // Literal cumulative comparisons use strict < at each threshold.
    cfg.singleNectarChance = 0.5f; cfg.doubleNectarChance = 0.25f;
    cfg.mititesChance = 0.125f; cfg.spicyChance = 0.0625f; cfg.bitterChance = 0.0625f;
    const float boundaries[] = {0.499f, 0.5f, 0.75f, 0.875f, 0.9375f};
    const P2EggDropType types[] = {P2EggDropType::SingleNectar, P2EggDropType::DoubleNectar,
        P2EggDropType::Mitites, P2EggDropType::Spicy, P2EggDropType::Bitter};
    for (unsigned i = 0; i < 5; ++i) {
        next.ordinal++; e = Fake{}; e.roll = boundaries[i]; e.spray = true;
        assert(resumed.generate(next, cfg, {}, e, r, error) && r.type == types[i]);
    }
    std::cout << "P2_ORIGINAL_EGG_CONTENTS_PASS\n";
}
