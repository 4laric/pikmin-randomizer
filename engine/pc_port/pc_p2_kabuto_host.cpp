#include "pc_p2_kabuto_host.h"

#include <cmath>

namespace {

// Resolved authored duration (source frames) of the species attack clip inside
// the bound bank. 0 means the mouth binding was unresolved, so the feed cannot
// be scaled and fails closed.
int sourceDurationOf(const P2KabutoBindingTable& table, P2KabutoBindingToken token,
                     const p2attach::Bank& bank)
{
    const P2KabutoMouthBinding* mouth = table.mouthBinding(token);
    if (!mouth || mouth->clip < 0 || static_cast<std::size_t>(mouth->clip) >= bank.clips.size()) {
        return 0;
    }
    return bank.clips[static_cast<std::size_t>(mouth->clip)].duration;
}

// Live animation phase in [0,1]; a single-frame clip has no phase span.
double phaseOf(double counter, long frameCount)
{
    const double span = frameCount > 1 ? double(frameCount - 1) : 1.0;
    double phase = counter / span;
    if (phase < 0.0) {
        phase = 0.0;
    }
    if (phase > 1.0) {
        phase = 1.0;
    }
    return phase;
}

} // namespace

bool P2KabutoHost::species_for_source(unsigned source, P2KabutoSpecies& out)
{
    switch (source) {
    case 75:
        out = P2KabutoSpecies::Kabuto;
        return true;
    case 95:
        out = P2KabutoSpecies::Rkabuto;
        return true;
    case 96:
        out = P2KabutoSpecies::Fkabuto;
        return true;
    default:
        return false;
    }
}

const char* P2KabutoHost::species_name(P2KabutoSpecies species)
{
    switch (species) {
    case P2KabutoSpecies::Kabuto:
        return "Kabuto";
    case P2KabutoSpecies::Rkabuto:
        return "Rkabuto";
    case P2KabutoSpecies::Fkabuto:
        return "Fkabuto";
    }
    return "?";
}

P2KabutoHost::Entry* P2KabutoHost::find(std::uint64_t identity)
{
    if (!identity) {
        return nullptr;
    }
    for (Entry& entry : mEntries) {
        if (entry.token && entry.identity == identity) {
            return &entry;
        }
    }
    return nullptr;
}

const P2KabutoHost::Entry* P2KabutoHost::find(std::uint64_t identity) const
{
    if (!identity) {
        return nullptr;
    }
    for (const Entry& entry : mEntries) {
        if (entry.token && entry.identity == identity) {
            return &entry;
        }
    }
    return nullptr;
}

std::size_t P2KabutoHost::size() const
{
    std::size_t count = 0;
    for (const Entry& entry : mEntries) {
        if (entry.token) {
            ++count;
        }
    }
    return count;
}

P2KabutoBindingToken P2KabutoHost::bind(std::uint64_t identity, P2KabutoSpecies species,
                                        std::shared_ptr<const p2attach::Bank> bank)
{
    if (!identity || !bank || !p2attach::checked(*bank)) {
        return 0;
    }
    if (Entry* existing = find(identity)) {
        // Same owner: re-resolve species/bank in place, keeping the handle.
        const P2KabutoBindingToken rebound = mTable.rebind(existing->token, species, bank);
        if (!rebound) {
            return 0;
        }
        existing->speciesKind = species;
        existing->sourceDuration = sourceDurationOf(mTable, rebound, *bank);
        if (existing->sourceDuration < 2) {
            mTable.release(rebound);
            existing->token = 0;
            existing->identity = 0;
            existing->bank.reset();
            return 0;
        }
        existing->bank = std::move(bank);
        existing->last = P2KabutoHostAnimator{};
        existing->sampled = false;
        return rebound;
    }

    Entry* slot = nullptr;
    for (Entry& entry : mEntries) {
        if (!entry.token) {
            slot = &entry;
            break;
        }
    }
    if (!slot) {
        return 0; // bounded: fail closed at capacity
    }
    const P2KabutoBindingToken token = mTable.bind(identity, species, bank);
    if (!token) {
        return 0;
    }
    const int duration = sourceDurationOf(mTable, token, *bank);
    if (duration < 2) {
        mTable.release(token);
        return 0;
    }
    slot->identity = identity;
    slot->token = token;
    slot->speciesKind = species;
    slot->sourceDuration = duration;
    slot->bank = std::move(bank);
    slot->last = P2KabutoHostAnimator{};
    slot->sampled = false;
    slot->tick = 0;
    return token;
}

bool P2KabutoHost::release(std::uint64_t identity)
{
    Entry* entry = find(identity);
    if (!entry) {
        return false;
    }
    mTable.release(entry->token);
    *entry = Entry{};
    return true;
}

void P2KabutoHost::reset()
{
    mTable.reset();
    for (Entry& entry : mEntries) {
        entry = Entry{};
    }
}

bool P2KabutoHost::bound(std::uint64_t identity) const
{
    return find(identity) != nullptr;
}

P2KabutoBindingToken P2KabutoHost::token(std::uint64_t identity) const
{
    const Entry* entry = find(identity);
    return entry ? entry->token : 0;
}

P2KabutoSpecies P2KabutoHost::species(std::uint64_t identity) const
{
    const Entry* entry = find(identity);
    return entry ? entry->speciesKind : P2KabutoSpecies::Kabuto;
}

P2KabutoPhase P2KabutoHost::phase(std::uint64_t identity) const
{
    const Entry* entry = find(identity);
    return entry ? mTable.phase(entry->token) : P2KabutoPhase::Inactive;
}

P2KabutoHostFeed P2KabutoHost::feed(const P2KabutoHostAnimator& previous,
                                    const P2KabutoHostAnimator& current,
                                    int sourceDuration)
{
    P2KabutoHostFeed result;
    if (sourceDuration < 2 || !std::isfinite(current.counter) || current.counter < 0.0) {
        return result;
    }
    if (!current.attackMotion) {
        // Leaving attack is always usable, even if the idle motion has <2 frames:
        // the host only needs to drop an unfinished source clock.
        result.valid = true;
        result.leave = previous.attackMotion;
        return result;
    }
    if (current.frameCount < 2) {
        return result; // cannot phase an attack motion with fewer than two frames
    }
    result.valid = true;
    const double sourceSpan = double(sourceDuration);

    const double currentPhase = phaseOf(current.counter, current.frameCount);
    if (!previous.attackMotion) {
        result.begin = true;
        result.sourceFrameDelta = currentPhase * sourceSpan;
        return result;
    }

    // A smaller counter or a changed frame count means the live motion restarted;
    // restart the source clock at the new phase instead of forwarding a huge
    // wrap delta.
    if (current.frameCount != previous.frameCount || current.counter < previous.counter) {
        result.restart = true;
        result.sourceFrameDelta = currentPhase * sourceSpan;
        return result;
    }

    const double previousPhase = phaseOf(previous.counter, previous.frameCount);
    result.sourceFrameDelta = (currentPhase - previousPhase) * sourceSpan;
    if (result.sourceFrameDelta < 0.0) {
        result.sourceFrameDelta = 0.0;
    }
    return result;
}

bool P2KabutoHost::advance(std::uint64_t identity, const P2KabutoHostAnimator& animator,
                           const p2attach::Affine& owner, float faceDir,
                           const P2KabutoHostState& host, P2KabutoAdvanceOut& out)
{
    out = P2KabutoAdvanceOut{};
    Entry* entry = find(identity);
    if (!entry || entry->sourceDuration < 2) {
        return false;
    }

    P2KabutoHostAnimator previous = entry->last;
    if (!entry->sampled) {
        previous = P2KabutoHostAnimator{};
        previous.frameCount = animator.frameCount;
    }
    const P2KabutoHostFeed stamped = feed(previous, animator, entry->sourceDuration);
    if (!stamped.valid) {
        return false;
    }

    if (stamped.leave) {
        // The live attack motion ended. Drop any unfinished source clock so the
        // next attack starts from the family FSM wait/buried entry and can never
        // inherit the previous motion's KEYEVENT_2.
        if (mTable.attackActive(entry->token)
            && !mTable.rebind(entry->token, entry->speciesKind, entry->bank)) {
            return false;
        }
        entry->last = animator;
        entry->sampled = true;
        out.accepted = true;
        return true;
    }

    if (stamped.begin || stamped.restart) {
        if (mTable.attackActive(entry->token)
            && !mTable.rebind(entry->token, entry->speciesKind, entry->bank)) {
            return false;
        }
        if (!mTable.beginAttack(entry->token)) {
            return false;
        }
    }

    const std::uint64_t tick = ++entry->tick;
    const bool accepted = mTable.advance(entry->token, owner, stamped.sourceFrameDelta, tick,
                                         faceDir, host, out);
    entry->last = animator;
    entry->sampled = true;
    return accepted;
}
