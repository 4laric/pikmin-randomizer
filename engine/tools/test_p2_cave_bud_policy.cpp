// Lane 38 cave bud slot placement policy gate (#477; cave wave #468).
//
// Pins the fourth slot class: seeded Candypop bud slots in a segment, the
// never-behind-its-own-type generation constraint, N (conversion count)
// exposure to the logic consumer, and the strict P2_CAVE_BUD_1 sidecar.
// Follows tools/test_p2_cave_transfer.cpp; engine-free, header-only policy.
#include "pc_p2_cave_bud_policy.h"

#include <cassert>
#include <cstdio>
#include <sstream>
#include <string>
#include <vector>

namespace {

using p2cavebud::BudSlot;
using p2cavebud::Violation;

constexpr int Blue   = 0;
constexpr int Red    = 1;
constexpr int Yellow = 2;
constexpr int Purple = 3;
constexpr int White  = 4;

// Floor: 4 segments. Entering segment 1 needs water (blue); entering segment 2
// needs elec (yellow); segments 0 and 3 are ungated trunks.
std::vector<int> floorGates()
{
	std::vector<int> gates(4, 0);
	gates[1] = p2cavebud::colourBit(Blue);
	gates[2] = p2cavebud::colourBit(Yellow);
	return gates;
}

bool has(const std::vector<Violation>& violations, Violation wanted)
{
	for (Violation violation : violations) {
		if (violation == wanted) {
			return true;
		}
	}
	return false;
}

}  // namespace

int main()
{
	const std::vector<int> gates = floorGates();

	// 1. Accumulated requirement is the union of the chokes on the path.
	const std::vector<int> required = p2cavebud::segmentRequirements(gates);
	assert(required[0] == 0);
	assert(required[1] == p2cavebud::colourBit(Blue));
	assert(required[2] == (p2cavebud::colourBit(Blue) | p2cavebud::colourBit(Yellow)));
	assert(required[3] == required[2]);

	// 2. A purple bud before every gate is legal and keys later requirements.
	const std::vector<BudSlot> purple = {{0, Purple, 5}};
	assert(p2cavebud::validatePlacement(purple, gates).empty());
	assert(p2cavebud::requirementSatisfied(2, Purple, 0, purple, 5));
	assert(!p2cavebud::requirementSatisfied(2, Purple, 0, purple, 4));  // too few Pikmin
	assert(p2cavebud::requirementSatisfied(2, Purple, p2cavebud::colourBit(Purple), purple, 0));
	assert(!p2cavebud::requirementSatisfied(2, Red, 0, purple, 5));      // colour not provided
	// A bud only keys gates strictly after its own segment.
	assert(!p2cavebud::requirementSatisfied(0, Purple, 0, purple, 5));

	// 3. Never seed a bud behind the colour it provides.
	const std::vector<Violation> behind = p2cavebud::validatePlacement({{1, Blue, 5}}, gates);
	assert(behind.size() == 1 && behind[0] == Violation::BehindOwnType);
	// Segment 2 is reachable only through water then elec, so both blue and
	// yellow are "own type" there; a colour not on the path (red) is fine.
	assert(p2cavebud::validatePlacement({{2, Red, 5}}, gates).empty());
	for (int colour : {Blue, Yellow}) {
		const std::vector<Violation> own = p2cavebud::validatePlacement({{2, colour, 5}}, gates);
		assert(own.size() == 1 && own[0] == Violation::BehindOwnType);
	}
	// And a yellow bud before the water gate is legal (it keys segment 2).
	assert(p2cavebud::validatePlacement({{1, Yellow, 5}}, gates).empty());

	// 4. Duplicate segment, bad conversion count and out-of-range segment.
	const std::vector<BudSlot> bad = {{0, Purple, 5}, {0, White, 5}, {9, White, 5}, {1, Red, 0}};
	const std::vector<Violation> badViolations = p2cavebud::validatePlacement(bad, gates);
	assert(has(badViolations, Violation::DuplicateSegment));
	assert(has(badViolations, Violation::SegmentOutOfRange));
	assert(has(badViolations, Violation::InvalidConversionCount));

	// 5. N exposure follows the seeded table, not a hardcoded 5.
	const std::vector<BudSlot> seeded = {{0, White, 3}};
	assert(p2cavebud::requirementSatisfied(3, White, 0, seeded, 3));
	assert(!p2cavebud::requirementSatisfied(3, White, 0, seeded, 2));

	// 6. Strict P2_CAVE_BUD_1 sidecar round trip.
	std::istringstream good("P2_CAVE_BUD_1 4 2\n0 3 5\n3 4 5\n");
	const std::vector<BudSlot> parsed = p2cavebud::readBudTable(good);
	assert(parsed.size() == 2);
	assert(parsed[0].segment == 0 && parsed[0].colour == Purple && parsed[0].conversionCount == 5);
	assert(parsed[1].segment == 3 && parsed[1].colour == White && parsed[1].conversionCount == 5);
	assert(p2cavebud::validatePlacement(parsed, gates).empty());

	// 7. Malformed sidecars are rejected.
	for (const char* text : {"P2_CAVE_BUD_X 4 1\n0 3 5\n",   // unknown header
	                         "P2_CAVE_BUD_1 4 1\n4 3 5\n",    // segment out of range
	                         "P2_CAVE_BUD_1 4 1\n0 9 5\n",    // unknown colour
	                         "P2_CAVE_BUD_1 4 1\n0 3 0\n",    // non-positive count
	                         "P2_CAVE_BUD_1 4 2\n0 3 5\n0 4 5\n",  // duplicate segment
	                         "P2_CAVE_BUD_1 4 1\n0 3 5\n7\n"}) {   // trailing data
		std::istringstream in(text);
		bool threw = false;
		try {
			p2cavebud::readBudTable(in);
		}
		catch (const std::runtime_error&) {
			threw = true;
		}
		assert(threw);
	}

	std::puts("PASS P2_CAVE_BUD_POLICY");
	return 0;
}
