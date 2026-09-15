"""Gatling Groink (MiniHoudai 78 / FminiHoudai 97) carcass recovery / replacement-object revival policy.

Python twin of the native ``pc_p2_groink_carcass`` module. It mirrors the
source ``MiniHoudai::Obj::doBecomeCarcass`` / ``doUpdateCarcass``
(``src/plugProjectNishimuraU/MiniHoudai.cpp:282-325``), exposing the exact host
surface this policy must be drop-in compatible with::

    struct P2GroinkCarcassConfig { float gaugeDelay = 0; float recoverySeconds = 1; float maxHealth = 1; };
    enum class P2GroinkCarcassCommand { ActivateGauge, KillPellet, RequestBirth, DeactivateGauge };
    class P2GroinkCarcass {
        bool become(const Config&);   // validate config; reset timer/health to 0; mark ready
        void reset();                 // clear ready + timer/health
        Step step(float delta, bool pelletAlive, bool gaugeManager, bool activeTick = true);
        bool ready(); float timer(); float health();
    };

Timeline (``doUpdateCarcass`` contract):

* While the carcass pellet is alive the gauge delay elapses first with no health
  change; then health regenerates at ``maxHealth / recoverySeconds`` per second.
* At full health the pellet is killed and a replacement-object birth is
  requested as ``KillPellet`` then ``RequestBirth`` on the same step.
* Health is never clamped to ``maxHealth``, so a single valid step can overshoot;
  once ``health >= maxHealth`` no further command is emitted on later steps.
* A pellet that dies before the gauge delay leaves the carcass dead. A pellet
  that dies after it resets the timer/health and inactivates the gauge once.
"""
from dataclasses import dataclass
from enum import Enum
import math


class Command(Enum):
    """Mirror of ``P2GroinkCarcassCommand`` (values match the native ordering)."""

    ActivateGauge = 0
    KillPellet = 1
    RequestBirth = 2
    DeactivateGauge = 3


@dataclass(frozen=True)
class Birth:
    """Python representation of the native ``P2GroinkCarcassBirth`` payload."""

    position: tuple
    face_dir: float
    existence_length: float
    in_piklopedia: bool


def birth(position=(0, 0, 0), face_dir=0.0, existence_length=-1.0, in_piklopedia=False):
    """Build a typed ``Birth`` host payload (position defaults to the origin)."""
    return Birth(
        position=tuple(position),
        face_dir=float(face_dir),
        existence_length=float(existence_length),
        in_piklopedia=bool(in_piklopedia),
    )


@dataclass(frozen=True)
class Config:
    """Mirror of ``P2GroinkCarcassConfig`` (gaugeDelay, recoverySeconds, maxHealth)."""

    gauge_delay: float = 0.0
    recovery_seconds: float = 1.0
    max_health: float = 1.0


@dataclass
class Step:
    """Result of one ``step`` call: whether it was valid and the emitted commands."""

    valid: bool = False
    commands: tuple = ()


def _as_float(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result


def _valid_config(config):
    """True when the config is finite/nonnegative/<=1e6 and recovery is safe."""
    gauge_delay = _as_float(config.gauge_delay)
    recovery_seconds = _as_float(config.recovery_seconds)
    max_health = _as_float(config.max_health)
    if gauge_delay is None or recovery_seconds is None or max_health is None:
        return False
    if not (math.isfinite(gauge_delay) and math.isfinite(recovery_seconds) and math.isfinite(max_health)):
        return False
    if gauge_delay < 0.0 or recovery_seconds < 0.0 or max_health < 0.0:
        return False
    if gauge_delay > 1e6 or recovery_seconds > 1e6 or max_health > 1e6:
        return False
    if recovery_seconds <= 0.0:
        return False
    if not math.isfinite(max_health / recovery_seconds):
        return False
    return True


class P2GroinkCarcass:
    """Carcass recovery / replacement-object revival state machine."""

    def __init__(self):
        self._ready = False
        self._config = Config()
        self._timer = 0.0
        self._health = 0.0

    def become(self, config):
        """Validate ``config`` and, if valid, reset state and mark ready. No-op on failure."""
        if not _valid_config(config):
            return False
        self._config = Config(
            gauge_delay=float(config.gauge_delay),
            recovery_seconds=float(config.recovery_seconds),
            max_health=float(config.max_health),
        )
        self._timer = 0.0
        self._health = 0.0
        self._ready = True
        return True

    def reset(self):
        """Clear ready plus timer/health."""
        self._ready = False
        self._timer = 0.0
        self._health = 0.0

    @property
    def ready(self):
        return self._ready

    @property
    def timer(self):
        return self._timer

    @property
    def health(self):
        return self._health

    def step(self, delta, pellet_alive, gauge_manager, active_tick=True):
        """Advance one update; returns a ``Step`` with the commands emitted in order."""
        if not self._ready:
            return Step(valid=False)
        if not active_tick:
            return Step(valid=True, commands=())
        if not math.isfinite(delta) or delta < 0.0 or delta > 0.25:
            return Step(valid=False)
        commands = []
        config = self._config
        if pellet_alive:
            if self._timer < config.gauge_delay:
                self._timer += delta
                if gauge_manager and self._timer >= config.gauge_delay:
                    commands.append(Command.ActivateGauge)
            elif self._health < config.max_health:
                self._health += (config.max_health / config.recovery_seconds) * delta
                if self._health >= config.max_health:
                    commands.append(Command.KillPellet)
                    commands.append(Command.RequestBirth)
        else:
            if gauge_manager and self._timer >= config.gauge_delay:
                self._timer = 0.0
                self._health = 0.0
                commands.append(Command.DeactivateGauge)
        return Step(valid=True, commands=tuple(commands))
