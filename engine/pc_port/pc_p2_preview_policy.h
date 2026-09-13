#pragma once
#include <istream>
#include <stdexcept>
#include <string>

inline void p2ReadCargoFree(std::istream& input) {
    std::string token, trailing;
    if (!(input >> token) || token != "P2_CARGO_FREE_1" || (input >> trailing) || input.bad())
        throw std::runtime_error("invalid cargo-free preview config");
}

inline void p2ValidatePreviewCargo(bool cargoFree, bool hasCargoConfig, bool hasTreasure) {
    if (cargoFree && (hasCargoConfig || hasTreasure))
        throw std::runtime_error("cargo-free preview forbids cargo config and treasure actors");
    if (!cargoFree && !hasTreasure)
        throw std::runtime_error("treasure generator missing");
}
