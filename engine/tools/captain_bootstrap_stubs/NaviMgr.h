#pragma once
// Link-only actors for the engine-free configuration probe. No birth is tested.
class Navi {
public:
    int getNaviIndex() const { return 0; }
};
class NaviMgr {
public:
    bool ensureSecondNaviShapeObject() { return false; }
    Navi* getNavi() { return nullptr; }
    Navi* birth() { return nullptr; }
};
