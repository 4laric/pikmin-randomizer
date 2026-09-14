#include "pc_p2_kabuto_binding.h"

#include <atomic>
#include <cmath>
#include <utility>

namespace {
// Neutral FSM policy values: the per-tick host snapshot supplies the real health
// and target facts; the config only has to be valid (finite, health > 0) so the
// FSM accepts events. The host that owns the actor may tighten these through its
// own policy later; they never reach gameplay state from this module.
constexpr P2KabutoCannonConfig kNeutralConfig = { 0.0f, 1.0f };
} // namespace

P2KabutoBindingToken P2KabutoBindingTable::fresh()
{
    static std::atomic<P2KabutoBindingToken> next{ 1 };
    P2KabutoBindingToken n = next.load();
    do {
        if (n == UINT64_MAX) {
            return 0;
        }
    } while (!next.compare_exchange_weak(n, n + 1));
    return n;
}

P2KabutoBindingTable::Entry* P2KabutoBindingTable::find(P2KabutoBindingToken token)
{
    if (!token) {
        return nullptr;
    }
    for (Entry& entry : mEntries) {
        if (entry.used && entry.token == token) {
            return &entry;
        }
    }
    return nullptr;
}

const P2KabutoBindingTable::Entry* P2KabutoBindingTable::find(P2KabutoBindingToken token) const
{
    if (!token) {
        return nullptr;
    }
    for (const Entry& entry : mEntries) {
        if (entry.used && entry.token == token) {
            return &entry;
        }
    }
    return nullptr;
}

std::size_t P2KabutoBindingTable::size() const
{
    std::size_t count = 0;
    for (const Entry& entry : mEntries) {
        if (entry.used) {
            ++count;
        }
    }
    return count;
}

P2KabutoBindingToken P2KabutoBindingTable::bind(std::uint64_t identity,
                                                P2KabutoSpecies species,
                                                std::shared_ptr<const p2attach::Bank> bank)
{
    if (!bank || !p2attach::checked(*bank)) {
        return 0;
    }
    P2KabutoMouthBinding mouth;
    if (!p2_kabuto_mouth_resolve(*bank, species, mouth)) {
        return 0;
    }
    P2KabutoMuzzle muzzle;
    if (!muzzle.bind(*bank, species)) {
        return 0;
    }
    Entry* slot = nullptr;
    for (Entry& entry : mEntries) {
        if (!entry.used) {
            slot = &entry;
            break;
        }
    }
    if (!slot) {
        return 0; // bounded: fail closed at capacity
    }

    slot->clear();
    slot->attachToken = slot->instance.bind(bank);
    if (!slot->attachToken) {
        slot->clear();
        return 0;
    }
    const P2KabutoBindingToken token = fresh();
    if (!token) {
        slot->clear();
        return 0;
    }
    slot->used = true;
    slot->token = token;
    slot->identity = identity;
    slot->species = species;
    slot->bank = std::move(bank);
    slot->mouth = mouth;
    slot->muzzle = muzzle;
    slot->cannon.reset(kNeutralConfig, species);
    if (!slot->cannon.start()) {
        slot->clear();
        return 0;
    }
    return token;
}

P2KabutoBindingToken P2KabutoBindingTable::rebind(P2KabutoBindingToken token,
                                                  P2KabutoSpecies species,
                                                  std::shared_ptr<const p2attach::Bank> bank)
{
    Entry* entry = find(token);
    if (!entry || !bank || !p2attach::checked(*bank)) {
        return 0;
    }
    P2KabutoMouthBinding mouth;
    if (!p2_kabuto_mouth_resolve(*bank, species, mouth)) {
        return 0;
    }
    P2KabutoMuzzle muzzle;
    if (!muzzle.bind(*bank, species)) {
        return 0;
    }

    // Validation is complete; drop the previous owner state and re-key the same
    // handle. A failure past this point tombstones the handle (fail closed).
    const std::uint64_t keptIdentity = entry->identity;
    const P2KabutoBindingToken keptToken = entry->token;
    entry->clear();
    entry->attachToken = entry->instance.bind(bank);
    if (!entry->attachToken) {
        entry->clear();
        return 0;
    }
    entry->used = true;
    entry->token = keptToken;
    entry->identity = keptIdentity;
    entry->species = species;
    entry->bank = std::move(bank);
    entry->mouth = mouth;
    entry->muzzle = muzzle;
    entry->cannon.reset(kNeutralConfig, species);
    if (!entry->cannon.start()) {
        entry->clear();
        return 0;
    }
    return keptToken;
}

bool P2KabutoBindingTable::release(P2KabutoBindingToken token)
{
    Entry* entry = find(token);
    if (!entry) {
        return false;
    }
    entry->clear();
    return true;
}

void P2KabutoBindingTable::reset()
{
    for (Entry& entry : mEntries) {
        entry.clear();
    }
}

bool P2KabutoBindingTable::beginAttack(P2KabutoBindingToken token)
{
    Entry* entry = find(token);
    if (!entry) {
        return false;
    }
    if (entry->attackActive) {
        return true;
    }
    if (!entry->mouth.valid() || !entry->bank) {
        return false;
    }
    const int clip = entry->mouth.clip;
    if (clip < 0 || static_cast<std::size_t>(clip) >= entry->bank->clips.size()) {
        return false;
    }
    const p2attach::Clip& source = entry->bank->clips[static_cast<std::size_t>(clip)];

    const bool began = entry->species == P2KabutoSpecies::Fkabuto
        ? entry->cannon.beginFixAttack()
        : entry->cannon.beginAttack();
    if (!began) {
        return false;
    }
    const p2sampled::Clip clock =
        p2_kabuto_attack_clip(source.duration, entry->mouth.fireFrame, source.name.c_str(), "key2");
    if (!entry->adapter.begin(clock)) {
        return false;
    }
    entry->attackActive = true;
    return true;
}

bool P2KabutoBindingTable::advance(P2KabutoBindingToken token, const p2attach::Affine& owner,
                                   double sourceFrameDelta, std::uint64_t tick, float faceDir,
                                   const P2KabutoHostState& host, P2KabutoAdvanceOut& out)
{
    out = P2KabutoAdvanceOut{};
    Entry* entry = find(token);
    if (!entry) {
        return false;
    }
    if (!std::isfinite(sourceFrameDelta) || sourceFrameDelta < 0.0 || !p2attach::valid(owner)
        || !std::isfinite(faceDir) || !std::isfinite(host.health)
        || !std::isfinite(host.targetAngle)) {
        return false;
    }
    if (entry->sampled && tick < entry->lastTick) {
        return false; // per-handle monotonic source tick
    }
    entry->lastTick = tick;
    entry->sampled = true;

    if (!entry->attackActive || !entry->adapter.active()) {
        out.accepted = true;
        return true;
    }

    P2KabutoEvent events[kMaxEvents];
    int count = 0;
    if (!entry->adapter.advance(sourceFrameDelta, events, kMaxEvents, count)) {
        return false; // shared clock refused the batch; nothing committed
    }
    for (int i = 0; i < count; ++i) {
        const P2KabutoAction action = entry->cannon.onEvent(events[i], host);
        ++out.events;
        out.action = action;
        if (events[i] == P2KabutoEvent::Key2) {
            out.key2 = true;
            if (action == P2KabutoAction::FireStone) {
                P2KabutoStoneBirth birth;
                // takeBirth consumes the pending FireStone only on success, so a
                // failed sample retries rather than duplicating or dropping it.
                if (entry->muzzle.takeBirth(entry->cannon, entry->instance, entry->attachToken,
                                            owner, tick, faceDir, birth)) {
                    out.fired = true;
                    out.birth = birth;
                }
            }
        } else if (events[i] == P2KabutoEvent::End) {
            out.end = true;
            entry->attackActive = false;
        }
    }
    out.accepted = true;
    return true;
}

P2KabutoPhase P2KabutoBindingTable::phase(P2KabutoBindingToken token) const
{
    const Entry* entry = find(token);
    return entry ? entry->cannon.phase() : P2KabutoPhase::Inactive;
}

bool P2KabutoBindingTable::attackActive(P2KabutoBindingToken token) const
{
    const Entry* entry = find(token);
    return entry ? entry->attackActive : false;
}

std::uint64_t P2KabutoBindingTable::identity(P2KabutoBindingToken token) const
{
    const Entry* entry = find(token);
    return entry ? entry->identity : 0;
}

const P2KabutoMouthBinding* P2KabutoBindingTable::mouthBinding(P2KabutoBindingToken token) const
{
    const Entry* entry = find(token);
    return entry ? &entry->mouth : nullptr;
}
