#include "pc_p2_pom_actor.h"

#include <cstdio>

bool p2_pom_actor_handle_valid(P2PomActorHandle handle)
{
    return handle.generation != 0 && handle.slot < P2_POM_ACTOR_POOL;
}

bool p2_pom_actor_source_colored(std::uint32_t source_id)
{
    return source_id >= P2_POM_SOURCE_FIRST && source_id <= P2_POM_SOURCE_LAST;
}

bool p2_pom_actor_is_base(std::uint32_t source_id)
{
    return source_id == P2_POM_BASE_ID;
}

bool p2_pom_actor_resolve(std::uint32_t generator, std::uint32_t source_id,
                          P2PomActorRecord* out)
{
    if (out == nullptr || generator == 0) return false;
    if (!p2_pom_actor_source_colored(source_id)) return false;
    out->generator = generator;
    out->source_id = source_id;
    out->parent_id = P2_POM_PARENT_ID;
    return true;
}

void p2_pom_actor_pool_init(P2PomActorPool* pool)
{
    if (pool == nullptr) return;
    for (std::uint32_t i = 0; i < P2_POM_ACTOR_POOL; ++i) {
        pool->slots[i].phase = P2PomActorPhase::Free;
        pool->slots[i].generation = 0;
        pool->slots[i].record = P2PomActorRecord();
    }
}

static bool slot_live(const P2PomActorPool* pool, P2PomActorHandle handle)
{
    if (pool == nullptr || !p2_pom_actor_handle_valid(handle)) return false;
    const P2PomActorSlot& slot = pool->slots[handle.slot];
    return slot.generation == handle.generation &&
           slot.phase != P2PomActorPhase::Free;
}

P2PomActorHandle p2_pom_actor_bind(P2PomActorPool* pool,
                                   const P2PomActorRecord* record)
{
    P2PomActorHandle bad = P2PomActorHandle();
    if (pool == nullptr || record == nullptr) return bad;
    if (!p2_pom_actor_source_colored(record->source_id)) return bad;
    if (record->parent_id != P2_POM_PARENT_ID) return bad;
    for (std::uint32_t i = 0; i < P2_POM_ACTOR_POOL; ++i) {
        if (pool->slots[i].phase == P2PomActorPhase::Free) continue;
        if (pool->slots[i].record.generator == record->generator) return bad;
    }
    for (std::uint32_t i = 0; i < P2_POM_ACTOR_POOL; ++i) {
        P2PomActorSlot& slot = pool->slots[i];
        if (slot.phase != P2PomActorPhase::Free) continue;
        if (slot.generation == 0) slot.generation = 1;
        slot.phase = P2PomActorPhase::Bound;
        slot.record = *record;
        P2PomActorHandle handle;
        handle.slot = i;
        handle.generation = slot.generation;
        return handle;
    }
    return bad;
}

bool p2_pom_actor_record_birth(P2PomActorPool* pool, P2PomActorHandle handle)
{
    if (!slot_live(pool, handle)) return false;
    P2PomActorSlot& slot = pool->slots[handle.slot];
    if (slot.phase != P2PomActorPhase::Bound) return false;
    slot.phase = P2PomActorPhase::Born;
    return true;
}

bool p2_pom_actor_release(P2PomActorPool* pool, P2PomActorHandle handle)
{
    if (!slot_live(pool, handle)) return false;
    P2PomActorSlot& slot = pool->slots[handle.slot];
    slot.phase = P2PomActorPhase::Free;
    slot.record = P2PomActorRecord();
    ++slot.generation;
    if (slot.generation == 0) slot.generation = 1;
    return true;
}

int p2_pom_actor_format_birth(char* out, std::size_t capacity,
                              const P2PomActorRecord* record,
                              P2PomActorHandle handle)
{
    if (out == nullptr || capacity == 0 || record == nullptr) return -1;
    if (!p2_pom_actor_source_colored(record->source_id)) return -1;
    if (record->parent_id != P2_POM_PARENT_ID) return -1;
    if (!p2_pom_actor_handle_valid(handle)) return -1;
    int written = std::snprintf(out, capacity,
        "P2_POM_ACTOR_BIRTH generator=%u source_id=%u parent_id=%u slot=%u gen=%u",
        record->generator, record->source_id, record->parent_id,
        handle.slot, handle.generation);
    if (written < 0 || static_cast<std::size_t>(written) >= capacity) return -1;
    return written;
}

int p2_pom_actor_format_base_refusal(char* out, std::size_t capacity,
                                     std::uint32_t generator)
{
    if (out == nullptr || capacity == 0 || generator == 0) return -1;
    int written = std::snprintf(out, capacity,
        "P2_POM_BASE_REJECTED generator=%u source_id=82", generator);
    if (written < 0 || static_cast<std::size_t>(written) >= capacity) return -1;
    return written;
}
