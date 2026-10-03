#pragma once
struct EquipmentPlayState {
    unsigned opened = 1;
    void openStage(int id) { opened |= 1u << id; }
};
struct EquipmentGameflow { EquipmentPlayState mPlayState; };
extern EquipmentGameflow gameflow;
