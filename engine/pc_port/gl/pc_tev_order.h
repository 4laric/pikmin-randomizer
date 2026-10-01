#pragma once

// GXSetTevOrder texture-coordinate selection.
//
// The Dolphin SDK never stores GX_TEXCOORD_NULL (0xFF) for a TEV stage. When
// the coordinate is out of range GXSetTevOrder writes TEXCOORD0 into the TREF
// register instead, and the texture stays enabled whenever the *map* is valid.
// So a stage ordered as (GX_TEXCOORD_NULL, GX_TEXMAPn) still samples map n,
// using coordinate 0. Only (NULL, TEXMAP_NULL) means "no texture".
//
// The Forest of Hope pond material has such a stage: its last TEV stage reads
// the alpha of a soft-edge mask (texture map 2) with a NULL coordinate. Keeping
// the raw 0xFF let the renderer clamp it to coordinate 3, which samples the
// mask at the wrong place and left the water nearly opaque.
inline int pc_tev_order_texcoord(int coord)
{
	return (coord >= 0 && coord < 8) ? coord : 0;
}
