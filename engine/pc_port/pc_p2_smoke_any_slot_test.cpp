// #944: engine-free contract test for the smoke-seed slot bypass predicate.
#include "pc_p2_smoke_any_slot.h"
#include <cassert>
#include <cstdlib>

#ifdef _WIN32
static void setEnv(const char* name, const char* value) { _putenv_s(name, value ? value : ""); }
#else
static void setEnv(const char* name, const char* value)
{
    if (value) setenv(name, value, 1); else unsetenv(name);
}
#endif

int main()
{
    // Inert when unset.
    setEnv("PIKMIN_P2_SMOKE_ANY_SLOT", nullptr);
    pc_p2_smoke_any_slot_reset_for_test();
    assert(!pc_p2_smoke_any_slot());
    // "0" and empty are off; the verdict is cached per process.
    setEnv("PIKMIN_P2_SMOKE_ANY_SLOT", "0");
    pc_p2_smoke_any_slot_reset_for_test();
    assert(!pc_p2_smoke_any_slot());
    setEnv("PIKMIN_P2_SMOKE_ANY_SLOT", "1");
    assert(!pc_p2_smoke_any_slot()); // cached off until reset
    pc_p2_smoke_any_slot_reset_for_test();
    assert(pc_p2_smoke_any_slot());
    assert(pc_p2_smoke_any_slot());
    // Force-off (netplay session / console enforce) wins over the env var and
    // stays latched until reset.
    pc_p2_smoke_any_slot_force_off("netplay");
    assert(!pc_p2_smoke_any_slot());
    pc_p2_smoke_any_slot_force_off("netplay");
    assert(!pc_p2_smoke_any_slot());
    pc_p2_smoke_any_slot_reset_for_test();
    assert(pc_p2_smoke_any_slot());
    // Force-off before first use also holds.
    pc_p2_smoke_any_slot_reset_for_test();
    pc_p2_smoke_any_slot_force_off("early");
    assert(!pc_p2_smoke_any_slot());
    return 0;
}
