#pragma once
#include <atomic>
#include <cstdint>
namespace pc_midday {
namespace construction_detail {
inline std::atomic<bool> rewardsBlocked{false};
inline std::atomic<uint64_t> blockedCommands{0};
}
inline uint64_t suppressedConstructionRewards(){return construction_detail::blockedCommands.load();}
}
// Inert outside the physical ConstructorFence. Writers call this before looking
// up a check, mutating its consumed set or appending an outbox/durable journal.
inline bool pc_midday_construction_rewards_suppressed(){
 if(!pc_midday::construction_detail::rewardsBlocked.load())return false;
 pc_midday::construction_detail::blockedCommands.fetch_add(1);return true;
}
