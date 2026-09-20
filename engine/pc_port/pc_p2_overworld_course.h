#pragma once
// Shared overworld course boot flag (private candidate, issue #767).
// Additive module: selects one overworld course id and exposes it plus a
// registration helper for the shared stage-table path. No behavior change
// when unselected. pc_bbft_init argv wiring is a serialized follow-on
// (after staged scope challenge-pc-bbft-followon #755) via #186 review +
// integrator; this module never edits pc_bbft.cpp, pc_bbft.h or
// CMakeLists.txt.
void pc_pikipelago_overworld_course_parse(int argc, char** argv);
int pc_pikipelago_overworld_course();
const char* pc_pikipelago_overworld_course_id();
bool pc_pikipelago_overworld_course_register();
