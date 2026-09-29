// Checks the improved-routing planner against brute force on small graphs.
#include "pc_route_planner.h"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <vector>

static int sFailures = 0;

#define CHECK(cond, ...)                                  \
	do {                                                  \
		if (!(cond)) {                                    \
			std::fprintf(stderr, "FAIL %s:%d: ", __FILE__, __LINE__); \
			std::fprintf(stderr, __VA_ARGS__);            \
			std::fprintf(stderr, "\n");                   \
			sFailures++;                                  \
		}                                                 \
	} while (0)

static PcRouteNode makeNode(float x, float z)
{
	PcRouteNode n;
	n.x = x;
	n.y = 0.0f;
	n.z = z;
	for (int k = 0; k < PC_ROUTE_MAX_LINKS; k++) {
		n.links[k] = -1;
	}
	n.open  = true;
	n.water = false;
	return n;
}

static void link(std::vector<PcRouteNode>& g, int a, int b)
{
	for (int k = 0; k < PC_ROUTE_MAX_LINKS; k++) {
		if (g[a].links[k] == b) {
			return;
		}
		if (g[a].links[k] == -1) {
			g[a].links[k] = b;
			return;
		}
	}
}

static void link2(std::vector<PcRouteNode>& g, int a, int b)
{
	link(g, a, b);
	link(g, b, a);
}

static float len(const PcRouteNode& a, const PcRouteNode& b)
{
	const float dx = b.x - a.x, dy = b.y - a.y, dz = b.z - a.z;
	return std::sqrt(dx * dx + dy * dy + dz * dz);
}

// ---- brute force -------------------------------------------------------------

// Shortest float-weighted simple path under selectWay's rules.
static float bruteRouteDist(const std::vector<PcRouteNode>& g, int v, int dest, bool includeBlocked, bool avoidWater,
                            std::vector<char>& onPath)
{
	if (v == dest) {
		return 0.0f;
	}
	if (avoidWater && g[v].water) {
		return -1.0f;
	}
	float best = -1.0f;
	onPath[v]  = 1;
	for (int k = 0; k < PC_ROUTE_MAX_LINKS; k++) {
		const int n = g[v].links[k];
		if (n < 0 || n == v || onPath[n]) {
			continue;
		}
		if (!includeBlocked && !g[n].open) {
			continue;
		}
		const float rest = bruteRouteDist(g, n, dest, includeBlocked, avoidWater, onPath);
		if (rest >= 0.0f) {
			const float total = len(g[v], g[n]) + rest;
			if (best < 0.0f || total < best) {
				best = total;
			}
		}
	}
	onPath[v] = 0;
	return best;
}

// ---- checks ------------------------------------------------------------------

static void checkPathValid(const std::vector<PcRouteNode>& g, const int* path, int length, int start, int dest, bool includeBlocked,
                           bool avoidWater, float expected)
{
	CHECK(path[0] == start, "path starts at %d, want %d", path[0], start);
	CHECK(path[length - 1] == dest, "path ends at %d, want %d", path[length - 1], dest);
	float total = 0.0f;
	for (int i = 0; i + 1 < length; i++) {
		const int a = path[i], b = path[i + 1];
		bool linked = false;
		for (int k = 0; k < PC_ROUTE_MAX_LINKS; k++) {
			linked = linked || g[a].links[k] == b;
		}
		CHECK(linked, "step %d->%d is not a link", a, b);
		CHECK(includeBlocked || g[b].open, "step into closed %d", b);
		CHECK(!avoidWater || !g[a].water, "expanded water node %d", a);
		total += len(g[a], g[b]);
	}
	CHECK(std::fabs(total - expected) < 0.01f, "path length %.3f, brute force %.3f", total, expected);
}

static void randomGraphs()
{
	std::srand(12345);
	for (int trial = 0; trial < 400; trial++) {
		const int count = 3 + std::rand() % 7;
		std::vector<PcRouteNode> g;
		for (int i = 0; i < count; i++) {
			g.push_back(makeNode(float(std::rand() % 1000), float(std::rand() % 1000)));
			g.back().y     = float(std::rand() % 60);
			g.back().open  = (std::rand() % 5) != 0;
			g.back().water = (std::rand() % 6) == 0;
		}
		const int links = count + std::rand() % (count * 2);
		for (int i = 0; i < links; i++) {
			const int a = std::rand() % count, b = std::rand() % count;
			if (std::rand() % 4 == 0) {
				link(g, a, b); // some one-way links
			} else {
				link2(g, a, b);
			}
		}

		// Constrained shortest path against brute force.
		for (int mode = 0; mode < 4; mode++) {
			const bool includeBlocked = mode & 1;
			const bool avoidWater     = (mode & 2) != 0;
			const int start = std::rand() % count, dest = std::rand() % count;
			std::vector<int> path(count);
			const int length = pc_route_shortest_path(&g[0], count, start, dest, includeBlocked, avoidWater, &path[0], count);
			std::vector<char> onPath(count, 0);
			const float want = (start == dest) ? 0.0f : bruteRouteDist(g, start, dest, includeBlocked, avoidWater, onPath);
			if (want < 0.0f) {
				CHECK(length == 0, "trial %d: found a %d-point path brute force says cannot exist", trial, length);
			} else {
				CHECK(length > 0, "trial %d mode %d: no path %d->%d, brute force %.2f", trial, mode, start, dest, want);
				if (length > 0) {
					checkPathValid(g, &path[0], length, start, dest, includeBlocked, avoidWater, want);
					float reported = -1.0f;
					pc_route_shortest_path(&g[0], count, start, dest, includeBlocked, avoidWater, &path[0], count, &reported);
					CHECK(std::fabs(reported - want) < 0.01f, "reported length %.3f, brute force %.3f", reported, want);
				}
			}
		}
	}
}

// A detour the retail greedy search gets wrong: the neighbour nearest the goal
// in a straight line leads into a long corridor that swings far out.
static void greedyTrap()
{
	std::vector<PcRouteNode> g;
	g.push_back(makeNode(0, 0));      // 0 start
	g.push_back(makeNode(90, 0));     // 1 looks closest to the goal...
	g.push_back(makeNode(90, 400));   // 2 ...but the corridor swings far out
	g.push_back(makeNode(100, 400));  // 3
	g.push_back(makeNode(0, -50));    // 4 short way round
	g.push_back(makeNode(100, -50));  // 5
	g.push_back(makeNode(100, 0));    // 6 goal
	link2(g, 0, 1);
	link2(g, 1, 2);
	link2(g, 2, 3);
	link2(g, 3, 6);
	link2(g, 0, 4);
	link2(g, 4, 5);
	link2(g, 5, 6);
	link(g, 0, 0); // self-links are ignored

	int path[7];
	const int length = pc_route_shortest_path(&g[0], 7, 0, 6, false, false, path, 7);
	CHECK(length == 4, "greedy trap: %d points", length);
	if (length == 4) {
		CHECK(path[1] == 4 && path[2] == 5, "greedy trap: went via %d,%d", path[1], path[2]);
	}

	// Path that does not fit the buffer is rejected rather than truncated.
	CHECK(pc_route_shortest_path(&g[0], 7, 0, 6, false, false, path, 3) == 0, "overlong path was not rejected");
}

// Water: a land-only Pikmin cannot cross a water waypoint but may end on one.
static void waterRules()
{
	std::vector<PcRouteNode> g;
	g.push_back(makeNode(0, 0));
	g.push_back(makeNode(100, 0));
	g.push_back(makeNode(200, 0));
	link2(g, 0, 1);
	link2(g, 1, 2);
	g[1].water = true;
	int path[3];
	CHECK(pc_route_shortest_path(&g[0], 3, 0, 2, false, true, path, 3) == 0, "crossed water while avoiding it");
	CHECK(pc_route_shortest_path(&g[0], 3, 0, 1, false, true, path, 3) == 2, "could not end on water");
	CHECK(pc_route_shortest_path(&g[0], 3, 0, 2, false, false, path, 3) == 3, "blue path through water failed");
	g[2].open = false;
	CHECK(pc_route_shortest_path(&g[0], 3, 0, 2, false, false, path, 3) == 0, "entered a closed destination");
	CHECK(pc_route_shortest_path(&g[0], 3, 0, 2, true, false, path, 3) == 3, "blocked path not allowed when included");
	CHECK(pc_route_shortest_path(&g[0], 3, 2, 2, false, true, path, 3) == 1, "start == dest");
}

int main()
{
	randomGraphs();
	greedyTrap();
	waterRules();
	if (sFailures) {
		std::fprintf(stderr, "%d failure(s)\n", sFailures);
		return 1;
	}
	std::printf("pc_route_planner_test: all passed\n");
	return 0;
}
