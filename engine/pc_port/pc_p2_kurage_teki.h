#pragma once
class BTeki;
class Graphics;
class Matrix4f;
void pc_p2_kurage_teki_setup();
void pc_p2_kurage_teki_tick(BTeki*);
void pc_p2_kurage_teki_forget(BTeki*);
void pc_p2_kurage_teki_reset();
// Read-only lifecycle probe for the native runtime fixture.  Binding remains
// owned by GameCoreSection::finalSetup and the Teki lifecycle hooks.
bool pc_p2_kurage_teki_is_bound(const BTeki*);
bool pc_p2_kurage_teki_draw(BTeki*, Graphics&, const Matrix4f&, bool corpse = false);
