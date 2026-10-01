#pragma once

// Pom::Obj::shotPikmin refunds same-species slots for non-Queen buds.
// Track completed births separately from lifetime slots: a failed birth must
// neither destroy an input nor spend capacity.
struct P2IvoryBudget {
    int remaining;
    int slots = 0;
    int births = 0;

    bool accepts(bool alreadyWhite) const {
        return remaining > 0 && (alreadyWhite || slots < remaining);
    }
    void completed(bool alreadyWhite) {
        ++births;
        if (!alreadyWhite) ++slots;
    }
};
