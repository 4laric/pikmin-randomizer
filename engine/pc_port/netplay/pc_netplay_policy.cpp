// Netplay sim-visibility policy for M2a view-independent culling (issue #879).
//
// Engine-free TU: only the C library and pc_netplay_det.h. Linked into
// pikmin_pc and into the engine-free pc_netplay_policy_test target.

#include "netplay/pc_netplay_policy.h"
#include "netplay/pc_netplay_det.h"

bool pc_netplay_sim_visible(bool frustumResult)
{
	if (pc_netplay_deterministic()) {
		return true;
	}
	return frustumResult;
}

float pc_netplay_sim_aspect(float liveAspect)
{
	if (pc_netplay_deterministic()) {
		return 16.0f / 9.0f;
	}
	return liveAspect;
}

float pc_netplay_sim_lod_distance(float liveDistance)
{
	if (pc_netplay_deterministic()) {
		return 0.0f;
	}
	return liveDistance;
}
