#pragma once
// Engine-free double for the Sarai lifecycle test: minimal 3D vector.
// Only what pc_p2_sarai_manager.cpp uses (construction, .set, member read,
// copy, mSRT.t assignment) is provided.
struct Vector3f {
    float x = 0.0f, y = 0.0f, z = 0.0f;
    Vector3f() = default;
    Vector3f(float x_, float y_, float z_) : x(x_), y(y_), z(z_) {}
    void set(float x_, float y_, float z_) { x = x_; y = y_; z = z_; }
};

struct SRT {
    Vector3f t;
};
