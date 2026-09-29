#include "pc_route_planner.h"

#include <cmath>
#include <functional>
#include <queue>
#include <utility>
#include <vector>

namespace {

typedef std::pair<float, int> QueueEntry; // (distance, node), smallest first
typedef std::priority_queue<QueueEntry, std::vector<QueueEntry>, std::greater<QueueEntry>> MinQueue;

float edgeLength(const PcRouteNode& a, const PcRouteNode& b)
{
	const float dx = b.x - a.x;
	const float dy = b.y - a.y;
	const float dz = b.z - a.z;
	return std::sqrt(dx * dx + dy * dy + dz * dz);
}

bool validLink(int link, int count)
{
	return link >= 0 && link < count;
}

} // namespace

int pc_route_shortest_path(const PcRouteNode* nodes, int count, int start, int dest, bool includeBlocked, bool avoidWater, int* outPath,
                           int maxLen, float* outLength)
{
	if (outLength) {
		*outLength = 0.0f;
	}
	if (!nodes || !outPath || maxLen <= 0 || start < 0 || start >= count || dest < 0 || dest >= count) {
		return 0;
	}
	if (start == dest) {
		outPath[0] = start;
		return 1;
	}

	std::vector<float> dist(count, -1.0f);
	std::vector<int> prev(count, -1);
	std::vector<char> done(count, 0);

	MinQueue queue;
	dist[start] = 0.0f;
	queue.push(QueueEntry(0.0f, start));
	while (!queue.empty()) {
		const float d = queue.top().first;
		const int v   = queue.top().second;
		queue.pop();
		if (done[v]) {
			continue;
		}
		done[v] = 1;
		if (v == dest) {
			break;
		}
		if (avoidWater && nodes[v].water) {
			continue;
		}
		for (int k = 0; k < PC_ROUTE_MAX_LINKS; k++) {
			const int n = nodes[v].links[k];
			if (!validLink(n, count) || n == v || done[n]) {
				continue;
			}
			if (!includeBlocked && !nodes[n].open) {
				continue;
			}
			const float nd = d + edgeLength(nodes[v], nodes[n]);
			if (dist[n] < 0.0f || nd < dist[n]) {
				dist[n] = nd;
				prev[n] = v;
				queue.push(QueueEntry(nd, n));
			}
		}
	}

	if (!done[dest]) {
		return 0;
	}

	int length = 0;
	for (int v = dest; v != -1; v = prev[v]) {
		length++;
	}
	if (length > maxLen) {
		return 0;
	}
	int i = length - 1;
	for (int v = dest; v != -1; v = prev[v]) {
		outPath[i--] = v;
	}
	if (outLength) {
		*outLength = dist[dest];
	}
	return length;
}
