#pragma once
// Engine-free doubles for the Sarai campaign capture/teardown test. The real
// pc_p2_sarai_capture_bridge.cpp compiles against these stand-ins so the exact
// shipped track/detach logic is exercised without an engine build.
#include <cmath>
#include <cstdint>
typedef float f32;
typedef double f64;
typedef unsigned char u8;
typedef signed char s8;
typedef unsigned short u16;
typedef signed short s16;
typedef unsigned int u32;
typedef signed int s32;
typedef std::uint64_t u64;
typedef std::int64_t s64;
// The real engine header defines immut as a const-matching macro; mirror that so
// the shipped bridge's `immut Interaction&` parameter spells the same type.
#define immut const
