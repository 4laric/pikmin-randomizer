// Retail cave generation provider TU (lane cave-generator-consumer-landing, #129).
//
// The implementation is header-inline in pc_p2_cave_generate.h; this TU is
// wired into PC_PORT_SOURCES by the consumer landing so the module version
// symbol is linked and the interface stays referenced.
#include "pc_p2_cave_generate.h"

const char* kP2CaveGenerateModule =
    "pc_p2_cave_generate v1 (header-inline policy; TU wired in consumer landing)";
