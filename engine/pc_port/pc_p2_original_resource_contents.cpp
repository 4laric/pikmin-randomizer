#include "pc_p2_original_resource_contents.h"
#include <cmath>
#include <tuple>

namespace p2originalresource {
namespace {
constexpr float pi = 3.14159265358979323846f, tau = 2.0f * pi;
bool finite(const P2EggVec3& p) { return std::isfinite(p.x) && std::isfinite(p.y) && std::isfinite(p.z); }
bool validIdentity(const SourceIdentity& id) {
    if (id.fingerprint.size() != 64 || id.uid == 0 || id.activation == 0) return false;
    for (char c : id.fingerprint) if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) return false;
    return true;
}
P2EggDropType select(float r, const P2EggConfig& c) {
    float t = c.singleNectarChance;
    if (r < t) return P2EggDropType::SingleNectar;
    t += c.doubleNectarChance; if (r < t) return P2EggDropType::DoubleNectar;
    t += c.mititesChance; if (r < t) return P2EggDropType::Mitites;
    t += c.spicyChance; if (r < t) return P2EggDropType::Spicy;
    t += c.bitterChance; if (r < t) return P2EggDropType::Bitter;
    return P2EggDropType::SingleNectar;
}
bool validConfig(const P2EggConfig& c) {
    const float values[] = {c.singleNectarChance, c.doubleNectarChance, c.mititesChance, c.spicyChance, c.bitterChance};
    for (float v : values) if (!std::isfinite(v) || v < 0 || v > 1) return false;
    return c.forcedDropType >= 0 && c.forcedDropType <= 7;
}
bool validShape(const ContentsRecord& r) {
    if (r.children.empty()) return false;
    const auto& a = r.children[0];
    switch (r.type) {
    case P2EggDropType::OnePellets:
    case P2EggDropType::FivePellets:
        return r.children.size() == 1 && a.identity.slot == 0 && a.kind ==
            (r.type == P2EggDropType::OnePellets ? ChildKind::PelletOne : ChildKind::PelletFive);
    case P2EggDropType::SingleNectar:
    case P2EggDropType::Spicy:
    case P2EggDropType::Bitter:
        return r.children.size() == 1 && a.identity.slot == 0 && a.kind ==
            (r.type == P2EggDropType::SingleNectar ? ChildKind::Nectar : r.type == P2EggDropType::Spicy ? ChildKind::Spicy : ChildKind::Bitter);
    case P2EggDropType::DoubleNectar:
        return r.children.size() == 2 && a.identity.slot == 0 && a.kind == ChildKind::Nectar &&
            r.children[1].identity.slot == 1 && r.children[1].kind == ChildKind::Nectar;
    case P2EggDropType::Mitites:
        if (r.children.size() == 1) return (a.identity.slot == 1 && a.kind == ChildKind::Nectar) ||
            (a.identity.slot == 0 && a.kind == ChildKind::MititeGroup && a.born);
        return a.identity.slot == 0 && a.kind == ChildKind::MititeGroup && !a.born &&
            r.children[1].identity.slot == 1 && r.children[1].kind == ChildKind::Nectar;
    }
    return false;
}
}
bool SourceIdentity::operator<(const SourceIdentity& b) const {
    return std::tie(fingerprint, uid, ordinal, epoch, activation) < std::tie(b.fingerprint, b.uid, b.ordinal, b.epoch, b.activation);
}
bool SourceIdentity::operator==(const SourceIdentity& b) const { return !(*this < b) && !(b < *this); }
bool EmissionIdentity::operator<(const EmissionIdentity& b) const {return std::tie(kind,emissionOrdinal,member)<std::tie(b.kind,b.emissionOrdinal,b.member);}
bool EmissionIdentity::operator==(const EmissionIdentity& b) const {return !(*this<b)&&!(b<*this);}
bool ChildIdentity::operator<(const ChildIdentity& b) const {return std::tie(source,ancestry,slot)<std::tie(b.source,b.ancestry,b.slot);}
bool ChildIdentity::operator==(const ChildIdentity& b) const {return !(*this<b)&&!(b<*this);}
bool validChildIdentity(const ChildIdentity& id) {
    if(!validIdentity(id.source)||id.slot>1||id.ancestry.size()>1)return false;
    if(id.ancestry.empty())return true;
    const auto& emission=id.ancestry.front();
    return id.slot==0&&emission.emissionOrdinal==0&&
      ((emission.kind==EmitterKind::PlantSpectralid&&emission.member<5)||
       (emission.kind==EmitterKind::EggMitite&&emission.member<10));
}

bool requirements(const P2EggConfig& c,ContentsRequirements& out,std::string& error) {
    if(!validConfig(c)){error="invalid original Egg source outcome parameters";return false;}
    ContentsRequirements next;
    auto add=[&](P2EggDropType type){switch(type){
    case P2EggDropType::OnePellets:next.pelletOne=true;break;
    case P2EggDropType::FivePellets:next.pelletFive=true;break;
    case P2EggDropType::SingleNectar:case P2EggDropType::DoubleNectar:next.nectar=true;break;
    case P2EggDropType::Mitites:next.mitites=next.nectar=true;break;
    case P2EggDropType::Spicy:next.spicy=true;if(c.checkHasSpray)next.nectar=true;break;
    case P2EggDropType::Bitter:next.bitter=true;if(c.checkHasSpray)next.nectar=true;break;
    }};
    if(c.forcedDropType)add(static_cast<P2EggDropType>(c.forcedDropType-1));
    else {
        float lower=0;
        const float chance[]={c.singleNectarChance,c.doubleNectarChance,c.mititesChance,c.spicyChance,c.bitterChance};
        const P2EggDropType type[]={P2EggDropType::SingleNectar,P2EggDropType::DoubleNectar,P2EggDropType::Mitites,P2EggDropType::Spicy,P2EggDropType::Bitter};
        for(unsigned i=0;i<5;++i){const float upper=lower+chance[i];if(lower<1&&upper>lower)add(type[i]);lower=upper;}
        if(lower<1)add(P2EggDropType::SingleNectar);
    }
    out=next;error.clear();return true;
}

bool EggContents::generate(const SourceIdentity& id, const P2EggConfig& c,
                          const P2EggVec3& origin, Engine& e, ContentsRecord& out, std::string& error) {
    error.clear();
    auto old = mRecords.find(id);
    if (old != mRecords.end()) {
        out = old->second;
        if (!out.complete) { error = "original Egg contents generation pending"; return false; }
        return true;
    }
    if (!validIdentity(id) || !finite(origin) || !validConfig(c)) {
        error = "invalid original Egg identity, position or source parameters"; return false;
    }
    // Stable map storage also makes same-source reentrant callbacks idempotent.
    ContentsRecord& record = mRecords[id]; record.source = id;
    record.type = select(e.randFloat(), c); // egg.cpp Obj::genItem 0x8034C2AC
    if (c.forcedDropType) record.type = static_cast<P2EggDropType>(c.forcedDropType - 1);
    if (c.checkHasSpray) {
        if (record.type == P2EggDropType::Spicy && !e.sprayMade(HoneyKind::Spicy)) record.type = P2EggDropType::SingleNectar;
        else if (record.type == P2EggDropType::Bitter && !e.sprayMade(HoneyKind::Bitter)) record.type = P2EggDropType::SingleNectar;
    }
    P2EggVec3 pos = origin; pos.y += 2.0f;
    P2EggVec3 velocity = {0, 250, 0};
    auto honey = [&](unsigned slot, HoneyKind kind, P2EggVec3 vel) {
        ChildOutcome child; child.identity = {id, slot}; child.position = pos; child.velocity = vel;
        child.kind = kind == HoneyKind::Nectar ? ChildKind::Nectar : kind == HoneyKind::Spicy ? ChildKind::Spicy : ChildKind::Bitter;
        child.attempted = true;
        record.children.push_back(child);
        const unsigned i = static_cast<unsigned>(record.children.size() - 1);
        record.children[i].born = e.birthHoney(kind, child);
    };
    switch (record.type) {
    case P2EggDropType::OnePellets:
    case P2EggDropType::FivePellets: {
        ChildOutcome child; child.identity = {id, 0}; child.position = pos; child.velocity = velocity;
        child.kind = record.type == P2EggDropType::OnePellets ? ChildKind::PelletOne : ChildKind::PelletFive;
        child.pelletColor = e.randInt(3); child.attempted = true;
        record.children.push_back(child); record.children[0].born = e.birthPellet(child); break;
    }
    case P2EggDropType::SingleNectar: honey(0, HoneyKind::Nectar, velocity); break;
    case P2EggDropType::DoubleNectar: {
        const float angle = tau * e.randFloat();
        for (unsigned i = 0; i < 2; ++i) {
            const float theta = pi * static_cast<float>(i) + angle;
            honey(i, HoneyKind::Nectar, {50.0f * std::sin(theta), 250, 50.0f * std::cos(theta)});
        }
        break;
    }
    case P2EggDropType::Mitites: {
        bool born = false;
        if (e.mititeManagerAvailable()) {
            ChildOutcome child; child.identity = {id, 0}; child.kind = ChildKind::MititeGroup;
            child.position = origin; child.facing = tau * e.randFloat();
            velocity.y = 200; child.velocity = velocity; child.mititeCount = 10; child.attempted = true;
            record.children.push_back(child); born = e.birthMititeGroup(child); record.children[0].born = born;
        }
        if (!born) honey(1, HoneyKind::Nectar, velocity);
        break;
    }
    case P2EggDropType::Spicy: honey(0, HoneyKind::Spicy, velocity); break;
    case P2EggDropType::Bitter: honey(0, HoneyKind::Bitter, velocity); break;
    }
    record.complete = true; out = record; return true;
}
const ContentsRecord* EggContents::find(const SourceIdentity& id) const {
    auto record=mRecords.find(id);return record==mRecords.end()?nullptr:&record->second;
}
std::vector<ContentsRecord> EggContents::snapshot() const {
    std::vector<ContentsRecord> result; for (const auto& row : mRecords) result.push_back(row.second); return result;
}
bool EggContents::restore(const std::vector<ContentsRecord>& rows, std::string& error) {
    error.clear(); std::map<SourceIdentity, ContentsRecord> next;
    for (const auto& r : rows) {
        if (!validIdentity(r.source) || static_cast<int>(r.type) < 0 || static_cast<int>(r.type) > 6 || r.children.size() > 2 || !r.complete || !validShape(r)) {
            error = "invalid or incomplete Egg contents record"; return false;
        }
        unsigned mask = 0;
        for (const auto& c : r.children) {
            if (!(c.identity.source == r.source) || !c.identity.ancestry.empty() || c.identity.slot > 1 || (mask & (1u << c.identity.slot)) || !c.attempted || (c.consumed && !c.born)
                || !finite(c.position) || !finite(c.velocity) || !std::isfinite(c.facing) || static_cast<int>(c.kind) < 0 || static_cast<int>(c.kind) > 5
                || c.pelletColor < 0 || c.pelletColor > 2 || c.mititeCount != (c.kind == ChildKind::MititeGroup ? 10 : 0)) {
                error = "invalid Egg child identity or outcome"; return false;
            }
            mask |= 1u << c.identity.slot;
        }
        if (!next.emplace(r.source, r).second) { error = "duplicate Egg contents source"; return false; }
    }
    mRecords.swap(next); return true;
}
bool EggContents::consume(const ChildIdentity& id, std::string& error) {
    if(!id.ancestry.empty()){error="resource child is not an original Egg outcome";return false;}
    error.clear(); auto r = mRecords.find(id.source);
    if (r != mRecords.end()) for (auto& c : r->second.children) if (c.identity.slot == id.slot && c.born) { c.consumed = true; return true; }
    error = "resource consumption has no successful original child birth"; return false;
}
}
