#pragma once
// lane38 cave Candypop bud slot placement policy (#477; cave wave #468).
//
// The fourth slot class of the frozen cave model: a *seeded* Candypop bud slot
// in a segment is a local key for the chokes/leaves that follow it. A colour
// requirement is met either by holding the colour outright, or by a matching
// bud strictly before the segment when the party can pay the conversion count:
//
//     colour OR (matching bud before the segment AND pikmin_count >= N)
//
// N is the bud's conversion count (5 vanilla, p2pom::IpTtlBudget). The seed
// fixes each bud's segment, colour and N; geometry may reroll but the table may
// not. This header is the generation-time placement/constraint routine: it
// places each seeded bud in its seeded segment, rejects a table that seeds a
// bud behind the very colour it provides (so the floor generator retries,
// acceptance item 6), and exposes N to the logic consumer (lane 39).
//
// Engine-free and header-only. Candypop conversion/refund behavior stays lane
// 23 (p2pom); species capabilities stay lane 11. Colour space is the port's
// p2pom::speciesColour space: 0 blue, 1 red, 2 yellow, 3 purple, 4 white, with
// hazards mapped by lane 11/34 (water->blue, elec->yellow, fire->red,
// poison->white).
#include "pc_p2_pom_policy.h"  // p2pom::IpTtlBudget (N = 5)

#include <istream>
#include <stdexcept>
#include <string>
#include <vector>

namespace p2cavebud {

inline constexpr int DefaultConversionCount = p2pom::IpTtlBudget;  // 5
inline constexpr int MaxSegments = 64;
inline constexpr int MaxBuds = 16;
inline constexpr int ColourCount = 5;
inline constexpr int MaxConversionCount = 64;

inline bool validColour(int colour)
{
	return colour >= 0 && colour < ColourCount;
}

inline int colourBit(int colour)
{
	if (!validColour(colour)) {
		throw std::runtime_error("unknown bud colour");
	}
	return 1 << colour;
}

// One seeded bud slot: the seed fixes all three fields.
struct BudSlot {
	int segment         = 0;
	int colour          = 0;
	int conversionCount = DefaultConversionCount;
};

// Violations a seeded table can carry at generation time. None is never
// returned in a list; an empty list means the floor may place its buds.
enum class Violation {
	None = 0,
	DuplicateSegment,
	InvalidConversionCount,
	SegmentOutOfRange,
	BehindOwnType,
};

inline const char* violationName(Violation violation)
{
	switch (violation) {
	case Violation::None:
		return "none";
	case Violation::DuplicateSegment:
		return "duplicate_segment";
	case Violation::InvalidConversionCount:
		return "invalid_conversion_count";
	case Violation::SegmentOutOfRange:
		return "segment_out_of_range";
	case Violation::BehindOwnType:
		return "bud_behind_own_type";
	}
	throw std::runtime_error("unknown violation");
}

// gates[s] is the bitmask of colours required to enter segment s (the choke
// or leaf gate between segment s-1 and s, empty for the entry segment).
// Returns the accumulated requirement to reach each segment: the union of the
// gates on segments 0..s, matching the frozen "union of chokes 1..k".
inline std::vector<int> segmentRequirements(const std::vector<int>& gates)
{
	if (gates.size() > static_cast<std::size_t>(MaxSegments)) {
		throw std::runtime_error("too many cave segments");
	}
	std::vector<int> accumulated;
	accumulated.reserve(gates.size());
	int running = 0;
	for (int gate : gates) {
		running |= gate;
		accumulated.push_back(running);
	}
	return accumulated;
}

// Validate a seeded bud table against the floor's gate table. The returned
// violations are ordered by the bud index they came from, then rule name, so
// the report is deterministic. A colour that appears in the accumulated
// requirement to reach the bud's own segment means the bud can only be
// obtained by already having the colour it provides (BehindOwnType).
inline std::vector<Violation> validatePlacement(const std::vector<BudSlot>& buds,
                                                const std::vector<int>& gates)
{
	const std::vector<int> required = segmentRequirements(gates);
	const int segmentCount = static_cast<int>(required.size());
	std::vector<Violation> violations;
	if (buds.size() > static_cast<std::size_t>(MaxBuds)) {
		throw std::runtime_error("too many cave buds");
	}
	std::vector<int> seenSegments;
	seenSegments.reserve(buds.size());
	for (const BudSlot& bud : buds) {
		if (bud.segment < 0 || bud.segment >= segmentCount) {
			violations.push_back(Violation::SegmentOutOfRange);
		}
		if (bud.conversionCount <= 0 || bud.conversionCount > MaxConversionCount) {
			violations.push_back(Violation::InvalidConversionCount);
		}
		if (!validColour(bud.colour)) {
			throw std::runtime_error("unknown bud colour");
		}
		bool duplicate = false;
		for (int seen : seenSegments) {
			if (seen == bud.segment) {
				duplicate = true;
				break;
			}
		}
		if (duplicate) {
			violations.push_back(Violation::DuplicateSegment);
		}
		else {
			seenSegments.push_back(bud.segment);
		}
		if (bud.segment >= 0 && bud.segment < segmentCount
		    && (required[bud.segment] & colourBit(bud.colour)) != 0) {
			violations.push_back(Violation::BehindOwnType);
		}
	}
	return violations;
}

// N exposure + alternate key. True when the party can open a requirement for
// `requiredColour` at `segment`: it already holds the colour (heldColourMask),
// or some seeded bud provides that colour strictly before `segment` with a
// positive conversion count <= pikminCount. A bud in the same segment as the
// gate is never its own key.
inline bool requirementSatisfied(int segment, int requiredColour, int heldColourMask,
                                 const std::vector<BudSlot>& buds, int pikminCount)
{
	if (requiredColour < 0) {
		return true;
	}
	if (!validColour(requiredColour)) {
		throw std::runtime_error("unknown required colour");
	}
	if (segment < 0 || pikminCount < 0) {
		throw std::runtime_error("invalid requirement query");
	}
	if ((heldColourMask & (1 << requiredColour)) != 0) {
		return true;
	}
	for (const BudSlot& bud : buds) {
		if (bud.colour != requiredColour) {
			continue;
		}
		if (bud.segment < 0 || bud.segment >= segment) {
			continue;
		}
		if (bud.conversionCount <= 0) {
			continue;
		}
		if (pikminCount >= bud.conversionCount) {
			return true;
		}
	}
	return false;
}

// Strict P2_CAVE_BUD_1 sidecar: "<segmentCount> <budCount>" then
// "<segment> <colour> <count>" rows, one per seeded bud. Malformed input,
// duplicate segments and out-of-range values throw; the parsed table is still
// subject to validatePlacement against the floor gates.
inline std::vector<BudSlot> readBudTable(std::istream& in)
{
	std::string header;
	int segmentCount = 0;
	int budCount     = 0;
	if (!(in >> header >> segmentCount >> budCount) || header != "P2_CAVE_BUD_1"
	    || segmentCount < 1 || segmentCount > MaxSegments || budCount < 0 || budCount > MaxBuds) {
		throw std::runtime_error("invalid P2_CAVE_BUD_1 header");
	}
	std::vector<BudSlot> buds;
	buds.reserve(static_cast<std::size_t>(budCount));
	for (int i = 0; i < budCount; ++i) {
		int segment = 0;
		int colour  = 0;
		int count   = 0;
		if (!(in >> segment >> colour >> count) || segment < 0 || segment >= segmentCount
		    || colour < 0 || colour >= ColourCount || count < 1 || count > MaxConversionCount) {
			throw std::runtime_error("invalid P2_CAVE_BUD_1 row");
		}
		for (const BudSlot& other : buds) {
			if (other.segment == segment) {
				throw std::runtime_error("duplicate P2_CAVE_BUD_1 segment");
			}
		}
		BudSlot bud;
		bud.segment         = segment;
		bud.colour          = colour;
		bud.conversionCount = count;
		buds.push_back(bud);
	}
	std::string trailing;
	if (in >> trailing) {
		throw std::runtime_error("trailing P2_CAVE_BUD_1 data");
	}
	return buds;
}

}  // namespace p2cavebud
