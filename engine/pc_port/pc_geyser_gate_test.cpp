// Host test for the co-op geyser launch gate (issue #1035). No game needed.

#include "pc_geyser_gate.h"

#include <cstdio>

namespace {
int failures = 0;
void check(bool ok, const char* what)
{
	if (!ok) {
		std::printf("FAIL: %s\n", what);
		failures++;
	}
}
} // namespace

int main()
{
	using pc_geyser_gate::shouldLaunch;
	// Single captain: unchanged, whatever the distance.
	check(shouldLaunch(1, 0, 0, 0, 0), "single captain on the geyser");
	check(shouldLaunch(1, 5000, -3000, 0, 0), "single captain far away still launches");
	check(shouldLaunch(0, 5000, 5000, 0, 0), "no-captain count keeps the legacy behaviour");
	// Two captains: only the one within 80 units.
	check(shouldLaunch(2, 10, 10, 0, 0), "co-op captain on the geyser launches");
	check(shouldLaunch(2, 80, 0, 0, 0), "co-op captain exactly 80 away launches");
	check(shouldLaunch(2, 0, -80, 0, 0), "negative axis, 80 away launches");
	check(!shouldLaunch(2, 80.01f, 0, 0, 0), "co-op captain just past 80 does not launch");
	check(!shouldLaunch(2, 60, 60, 0, 0), "diagonal 84.8 away does not launch");
	check(shouldLaunch(2, 50, 50, 0, 0), "diagonal 70.7 away launches");
	check(!shouldLaunch(2, 1000, 1000, 0, 0), "far captain not launched");
	// The geyser is not at the origin.
	check(shouldLaunch(2, 1010, 2005, 1000, 2000), "offset geyser, near captain launches");
	check(!shouldLaunch(2, 1000, 2200, 1000, 2000), "offset geyser, far captain not launched");
	// Pair: captain 1 on it, captain 2 far.
	check(shouldLaunch(2, 5, 5, 0, 0) && !shouldLaunch(2, 400, 0, 0, 0), "pair: only captain 1 launched");
	if (failures == 0) {
		std::printf("pc_geyser_gate_test: all passed\n");
	}
	return failures == 0 ? 0 : 1;
}
