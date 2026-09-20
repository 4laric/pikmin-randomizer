#pragma once
// Minimal Vector3f stand-in for the Sarai capture bridge translation unit.
#include "types.h"
#include <cmath>

struct Vector3f {
    f32 x = 0.0f, y = 0.0f, z = 0.0f;
    Vector3f() = default;
    Vector3f(f32 a, f32 b, f32 c) : x(a), y(b), z(c) {}
    void set(f32 a, f32 b, f32 c) { x = a; y = b; z = c; }
    void set(f32 value) { x = y = z = value; }
    f32 length() const { return std::sqrt(x * x + y * y + z * z); }
    Vector3f operator-(const Vector3f& rhs) const { return Vector3f(x - rhs.x, y - rhs.y, z - rhs.z); }
};
