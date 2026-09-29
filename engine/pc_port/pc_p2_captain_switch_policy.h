#pragma once

// Single-player switching runs once after both Navis update. Keep the edge
// latch outside either Kontroller: changing captain while Up is held must not
// manufacture a second press in the newly selected controller.
class P2CaptainSwitchPress {
    bool held = false;
public:
    bool update(bool enabled, bool down) {
        const bool pressed = enabled && down && !held;
        held = enabled && down;
        return pressed;
    }
    void reset() { held = false; }
};

inline bool p2_captain_switch_safe(bool present, bool alive, bool down,
                                  bool captured, bool holding, bool freeState) {
    return present && alive && !down && !captured && !holding && freeState;
}

inline bool p2_captain_input_owner(bool singlePlayerPair, int captain,
                                  int activeCaptain, int deviceOwner) {
    return captain == (singlePlayerPair ? activeCaptain : deviceOwner);
}

// The shared local pad and mouse/touch drag accumulate in physical player 0,
// even while the camera targets captain 1. Co-op retains a separate stream.
inline int p2_captain_camera_drag_player(bool singlePlayerPair, int targetCaptain) {
    return singlePlayerPair ? 0 : targetCaptain;
}

// PcamCameraManager::startCamera changes only the target. Bind its input too,
// otherwise it continues reading the neutralized old captain's controller.
template<class CameraT, class NaviT>
void p2_captain_bind_camera(CameraT& camera, NaviT& captain) {
    camera.mController = captain.mKontroller;
    camera.startCamera(&captain);
}

// Skipping a poll does not neutralize last frame's stick/buttons. Do not call
// Controller::reset: it also changes freeze/device state. No synthetic release
// edges are sent to inactive AI (which could otherwise throw a held object).
template<class ControllerT>
void p2_captain_neutral_input(ControllerT& c) {
    c.mCurrentInput = c.mPrevInput = c.mInputPressed = c.mInputReleased = 0;
    c.mInputDoublePressed = c.mDoublePressMask = c.mInputDelay = 0;
    c.mMainStickX = c.mMainStickY = c.mSubStickX = c.mSubStickY = 0;
    c.mAnalogA = c.mAnalogB = c.mTriggerL = c.mTriggerR = 0;
}
