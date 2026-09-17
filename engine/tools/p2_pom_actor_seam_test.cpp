// Engine-free seam test for the Pom actor-birth provider (issue #448).
// Compiles with -Ipc_port only; no engine, no runtime, no I/O fixtures.
// Exit 0 with PASS printed only when every check holds.
#include <cstdio>
#include <cstring>

#include "pc_p2_pom_actor.h"

static int failures = 0;
static int checks = 0;

static void check(bool cond, const char* name)
{
    ++checks;
    if (!cond) {
        ++failures;
        std::printf("FAIL %s\n", name);
    }
}

int main()
{
    // Colored ids resolve to the Pom-family record via the parent-id rule.
    for (std::uint32_t id = P2_POM_SOURCE_FIRST; id <= P2_POM_SOURCE_LAST; ++id) {
        P2PomActorRecord record;
        char name[64];
        std::snprintf(name, sizeof(name), "resolve_colored_%u", id);
        check(p2_pom_actor_resolve(700 + id, id, &record), name);
        check(record.generator == 700 + id && record.source_id == id &&
              record.parent_id == P2_POM_PARENT_ID, "record_fields_parent82");
    }
    // Base 82 and every out-of-range id refuse fail-closed.
    P2PomActorRecord sink;
    check(!p2_pom_actor_resolve(1, 82, &sink), "refuse_base_82");
    check(!p2_pom_actor_resolve(1, 0, &sink), "refuse_zero");
    check(!p2_pom_actor_resolve(1, 2, &sink), "refuse_below_range");
    check(!p2_pom_actor_resolve(1, 9, &sink), "refuse_above_range");
    check(!p2_pom_actor_resolve(1, 100, &sink), "refuse_other");
    check(!p2_pom_actor_resolve(0, 4, &sink), "refuse_zero_generator");
    check(!p2_pom_actor_resolve(1, 4, nullptr), "refuse_null_out");
    check(p2_pom_actor_is_base(82) && !p2_pom_actor_is_base(4),
          "is_base_predicate");
    check(p2_pom_actor_source_colored(3) && p2_pom_actor_source_colored(8) &&
          !p2_pom_actor_source_colored(82), "colored_predicate");

    // Ownership machine: single-use binding, exactly-once birth, recycle-safe.
    P2PomActorPool pool;
    p2_pom_actor_pool_init(&pool);
    P2PomActorRecord rec;
    check(p2_pom_actor_resolve(11, 4, &rec), "resolve_for_bind");
    P2PomActorHandle h = p2_pom_actor_bind(&pool, &rec);
    check(p2_pom_actor_handle_valid(h), "bind_valid_handle");
    check(!p2_pom_actor_handle_valid(P2PomActorHandle()), "null_handle_invalid");
    // Second bind of the same generator while bound fails.
    P2PomActorRecord rec2;
    check(p2_pom_actor_resolve(11, 5, &rec2), "resolve_same_generator");
    check(!p2_pom_actor_handle_valid(p2_pom_actor_bind(&pool, &rec2)),
          "rebind_same_generator_fails");
    // Exactly-once birth.
    check(p2_pom_actor_record_birth(&pool, h), "birth_once");
    check(!p2_pom_actor_record_birth(&pool, h), "birth_twice_fails");
    check(!p2_pom_actor_record_birth(&pool, P2PomActorHandle()),
          "birth_null_handle_fails");
    // Release recycles; the stale handle stays invalid.
    check(p2_pom_actor_release(&pool, h), "release_ok");
    check(!p2_pom_actor_record_birth(&pool, h), "stale_handle_dead");
    check(!p2_pom_actor_release(&pool, h), "double_release_fails");
    P2PomActorHandle h2 = p2_pom_actor_bind(&pool, &rec2);
    check(p2_pom_actor_handle_valid(h2) && h2.generation != h.generation,
          "rebind_after_release_new_generation");
    // Bind rejects records that do not carry the parent rule.
    P2PomActorRecord forged;
    forged.generator = 12;
    forged.source_id = 4;
    forged.parent_id = 7;
    check(!p2_pom_actor_handle_valid(p2_pom_actor_bind(&pool, &forged)),
          "bind_forged_parent_fails");
    P2PomActorRecord base_rec;
    base_rec.generator = 13;
    base_rec.source_id = 82;
    base_rec.parent_id = 82;
    check(!p2_pom_actor_handle_valid(p2_pom_actor_bind(&pool, &base_rec)),
          "bind_base_record_fails");

    // Marker grammar: exact strings, truncation refused.
    char buf[256];
    check(p2_pom_actor_format_birth(buf, sizeof(buf), &rec, h) > 0,
          "format_birth_ok");
    check(std::strcmp(buf, "P2_POM_ACTOR_BIRTH generator=11 source_id=4 "
                           "parent_id=82 slot=0 gen=1") == 0,
          "birth_marker_exact");
    char tiny[16];
    check(p2_pom_actor_format_birth(tiny, sizeof(tiny), &rec, h) < 0,
          "birth_truncation_refused");
    check(p2_pom_actor_format_birth(buf, sizeof(buf), &base_rec, h) < 0,
          "birth_base_record_refused");
    char rbuf[128];
    check(p2_pom_actor_format_base_refusal(rbuf, sizeof(rbuf), 11) > 0,
          "format_refusal_ok");
    check(std::strcmp(rbuf, "P2_POM_BASE_REJECTED generator=11 source_id=82") == 0,
          "refusal_marker_exact");
    check(p2_pom_actor_format_base_refusal(rbuf, sizeof(rbuf), 0) < 0,
          "refusal_zero_generator_fails");

    if (failures == 0) std::printf("PASS p2_pom_actor_seam %d checks\n", checks);
    return failures == 0 ? 0 : 1;
}
