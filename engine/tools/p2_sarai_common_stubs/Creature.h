#pragma once
// Shared canonical base for Sarai roster, capture and lifecycle doubles.
class Generator;
class Creature {
public:
    Generator* mGenerator = nullptr;
    virtual ~Creature() = default;
};
