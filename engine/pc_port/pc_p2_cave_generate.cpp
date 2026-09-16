// Retail cave generation provider TU (lane cave-generate-provider, #129).
//
// The implementation is header-inline in pc_p2_cave_generate.h so no
// CMakeLists change is needed in this slice. The integrator wires this TU
// into PC_PORT_SOURCES under #186 review as the follow-on; until then it
// documents the module version and keeps the interface referenced.
#include "pc_p2_cave_generate.h"

const char* kP2CaveGenerateModule =
    "pc_p2_cave_generate v1 (header-inline policy; TU wiring pending #186)";