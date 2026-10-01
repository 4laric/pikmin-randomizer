#include "pc_tev_order.h"

#include <cstdio>

int main()
{
	int failures = 0;
	auto check = [&](bool ok, const char* what) {
		if (!ok) {
			printf("FAIL: %s\n", what);
			++failures;
		}
	};

	// Valid coordinates pass through unchanged.
	for (int coord = 0; coord < 8; ++coord) {
		check(pc_tev_order_texcoord(coord) == coord, "in-range coordinate is kept");
	}
	// GX_TEXCOORD_NULL (0xFF) and other out-of-range values select TEXCOORD0,
	// as GXSetTevOrder does; they must not alias coordinate 3 (the renderer's
	// highest varying slot) or reach a shader as 255.
	check(pc_tev_order_texcoord(0xFF) == 0, "GX_TEXCOORD_NULL selects TEXCOORD0");
	check(pc_tev_order_texcoord(8) == 0, "GX_MAX_TEXCOORD selects TEXCOORD0");
	check(pc_tev_order_texcoord(-1) == 0, "negative coordinate selects TEXCOORD0");

	if (failures == 0) printf("pc_tev_order_test: OK\n");
	return failures == 0 ? 0 : 1;
}
