#ifndef PC_ROUTE_PLANNER_H
#define PC_ROUTE_PLANNER_H

/**
 * @file pc_route_planner.h
 * @brief Shortest-path routines for the "Better Pathfinding" mod.
 *
 * The retail PathFinder is a greedy depth-first walk: at each waypoint it steps
 * to whichever neighbour is closest to the goal in a straight line, and it keeps
 * the first path that arrives. The onion/ship search follows a cost table that
 * is filled from those first paths, so carriers follow estimates rather than
 * distances. This answers the same question exactly, over the same waypoint
 * data and with the same constraints, so the game code can swap it in when the
 * mod is enabled and keep the original search when it is not.
 *
 * Nothing here knows about game types; routeMgr.cpp copies the waypoint graph
 * into PcRouteNode records. That keeps the module testable on its own.
 */

#define PC_ROUTE_MAX_LINKS 8

struct PcRouteNode {
	float x, y, z;
	int links[PC_ROUTE_MAX_LINKS]; // neighbour indices, -1 for an empty slot
	bool open;                     // WayPoint::mIsOpen
	bool water;                    // WayPointFlags::InWater
};

/**
 * @brief Shortest path from @p start to @p dest under PathFinder::selectWay's rules.
 *
 * - A waypoint is only left through its links; self-links are ignored.
 * - A closed neighbour (including @p dest) is skipped unless @p includeBlocked.
 * - With @p avoidWater, a waypoint in water is never expanded (it may still be
 *   reached as the destination), matching the retail check on the current node.
 * - @p start == @p dest succeeds with a single-point path.
 *
 * Writes the waypoint indices from @p start to @p dest into @p outPath and
 * returns how many there are, or 0 when no path exists or it would not fit in
 * @p maxLen. @p outLength, when given, receives the path's length in world units.
 */
int pc_route_shortest_path(const PcRouteNode* nodes, int count, int start, int dest, bool includeBlocked, bool avoidWater, int* outPath,
                           int maxLen, float* outLength = nullptr);

#endif // PC_ROUTE_PLANNER_H
