#pragma once
class BTeki;
class Graphics;
class Matrix4f;
// Private bounded OniKurage (Greater Spotted Jellyfloat, ID 72) binding.
// Mirrors pc_p2_kurage_teki: an opt-in sidecar (`p2-onikurage-teki.txt`) selects
// the generated actor to own the shared Pikmin receiver and the two captain
// mouth slots. No production manager registration, no direct fixture calls.
void pc_p2_onikurage_teki_setup();
void pc_p2_onikurage_teki_tick(BTeki*);
void pc_p2_onikurage_teki_forget(BTeki*);
void pc_p2_onikurage_teki_reset();
bool pc_p2_onikurage_teki_is_bound(const BTeki*);
bool pc_p2_onikurage_teki_draw(BTeki*, Graphics&, const Matrix4f&, bool corpse = false);
// Read-only probes for the native runtime fixture.
int pc_p2_onikurage_teki_mouth_slots();
int pc_p2_onikurage_teki_bound_count();
