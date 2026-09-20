#pragma once
// CollPart stand-in for the Sarai capture bridge translation unit. The bridge
// only reads isBouncySphereType(); the concrete part type is driven by the test
// so the bouncy/sphere admission gate is exercised directly.
#include "types.h"
#include "Vector.h"

enum CollPartType {
    PART_None = 0,
    PART_BoundSphere,
    PART_Collision,
    PART_Cylinder,
    PART_Tube,
    PART_TubeChild,
    PART_Platform,
    PART_Reference,
};

class CollPart {
public:
    bool isSphereType() const { return mPartType == PART_BoundSphere; }
    bool isCollisionType() const { return mPartType == PART_Collision; }
    bool isBouncySphereType() const { return isSphereType() || isCollisionType(); }

    f32 mRadius = 0.0f;
    Vector3f mCentre;
    u8 mPartType = PART_None;
};
