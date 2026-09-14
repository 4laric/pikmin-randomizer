"""Gatling Groink (MiniHoudai 78 / FminiHoudai 97) carcass revival policy (#198/#209).

Reference mirror of the source `MiniHoudai::Obj::doBecomeCarcass` /
`doUpdateCarcass` (src/plugProjectNishimuraU/MiniHoudai.cpp:282-325) for the
root-side suite. It is the Python twin of the native `pc_p2_groink_carcass`
module and documents the exact regeneration / replacement-object revival
timeline so independent tests can cross-check the native C++ result.

Source contract (params fp11/fp12):
  - On death (become carcass): health = 0, gauge timer = 0; the object's
    position / face direction / existence length / Piklopedia flag are retained
    for the replacement birth.
  - While the carcass pellet is alive:
      - gauge timer elapses first (no health gain) and the life gauge appears
        when it reaches `health_gauge_timer` (fp11, default 30s);
      - then health regenerates at `max_health / respawn_rate` per second
        (fp12, default 10s) until it reaches max health.
  - At full health the pellet is killed and a NEW same-type object is born at
    the old position / face direction / duration / Piklopedia flag; the old
    object transits to MINIHOUDAI_Rebirth. Replacement object, not revival in
    place.
  - A pellet that dies before the gauge appears leaves the carcass dead: no
    revival and no gauge activity. A pellet that dies after the gauge has
    appeared inactivates and resets the gauge once.
"""
from dataclasses import dataclass, field
from enum import Enum


class Event(str, Enum):
    NONE = 'none'
    GAUGE_ACTIVE = 'gauge_active'
    REVIVE = 'revive'
    GAUGE_INACTIVE = 'gauge_inactive'


@dataclass
class Birth:
    position: tuple
    face_dir: float
    existence_length: float
    in_piklopedia: bool


@dataclass
class Parms:
    max_health: float = 1200.0
    health_gauge_timer: float = 30.0
    respawn_rate: float = 10.0


@dataclass
class StepResult:
    event: str = Event.NONE.value
    birth: Birth = None


@dataclass
class Carcass:
    position: tuple = (0.0, 0.0, 0.0)
    face_dir: float = 0.0
    existence_length: float = -1.0
    in_piklopedia: bool = False
    gauge_timer: float = 0.0
    health: float = 0.0
    pellet_alive: bool = True
    gauge_active: bool = False
    revived: bool = False

    def become(self):
        self.gauge_timer = 0.0
        self.health = 0.0
        self.pellet_alive = True
        self.gauge_active = False
        self.revived = False
        return self

    def step(self, parms, delta):
        out = StepResult()
        if (self.revived or delta <= 0.0 or
                parms.max_health <= 0.0 or parms.health_gauge_timer <= 0.0 or
                parms.respawn_rate <= 0.0):
            return out
        if self.pellet_alive:
            if self.gauge_timer < parms.health_gauge_timer:
                self.gauge_timer += delta
                if self.gauge_timer >= parms.health_gauge_timer:
                    self.gauge_active = True
                    out.event = Event.GAUGE_ACTIVE.value
            elif self.health < parms.max_health:
                self.health += (parms.max_health / parms.respawn_rate) * delta
                if self.health >= parms.max_health:
                    self.health = parms.max_health
                    self.pellet_alive = False
                    self.revived = True
                    out.event = Event.REVIVE.value
                    out.birth = Birth(self.position, self.face_dir,
                                      self.existence_length, self.in_piklopedia)
        elif self.gauge_timer >= parms.health_gauge_timer:
            self.gauge_timer = 0.0
            self.health = 0.0
            self.gauge_active = False
            out.event = Event.GAUGE_INACTIVE.value
        return out


def roaming_parms(max_health=1200.0):
    return Parms(max_health=max_health)


def fixed_parms(max_health=700.0):
    return Parms(max_health=max_health)
