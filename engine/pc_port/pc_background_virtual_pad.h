#pragma once
// Explicit background fixture seam. Human/physical input and other players do not qualify.
inline bool pc_background_virtual_pad_allowed(int player, bool testBackground, bool sessionReady,
                                              bool explicitlySelected, bool selectedVirtual) {
    return player == 0 && testBackground && sessionReady && explicitlySelected && selectedVirtual;
}
