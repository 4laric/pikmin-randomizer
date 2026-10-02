#pragma once

// Netplay co-op issue #1035: a geyser (Mizu) launches only the captains that
// are standing on it. naviGeyzerJump used to stimulate every captain, so with
// two captains the one far away was thrown to the geyser's target position
// too (getThrowVelocity sent it to the sky). Ported from the upstream Open
// Nectar 0.9 MizuAi::naviGeyzerJump fix.
//
// With a single captain the gate is open for any distance, so single-player
// behaviour is unchanged. Pure arithmetic over sim positions: no RNG, no
// clock, the same answer on both lockstep peers.

namespace pc_geyser_gate {

// Horizontal launch radius, in world units (upstream value).
constexpr float kLaunchRadius = 80.0f;

// True when the captain at (naviX, naviZ) should be launched by the geyser at
// (geyserX, geyserZ). naviCount is the number of captains in the stage.
inline bool shouldLaunch(int naviCount, float naviX, float naviZ, float geyserX, float geyserZ)
{
	if (naviCount <= 1) {
		return true;
	}
	const float dx = naviX - geyserX;
	const float dz = naviZ - geyserZ;
	return dx * dx + dz * dz <= kLaunchRadius * kLaunchRadius;
}

} // namespace pc_geyser_gate
