"""Bounded sampled-animation clock/event contract (parent #128, issue #431).

Source time is independent of pose-bank density. A family advances this clock in
source frames and reads:

* ``pose_index()`` - a pure projection of the current source frame onto the
  nearest sampled pose (identical selection to ``p2animation::Clip::index``),
  independent of how many events have been dispatched; and
* ``Batch.events`` - the authored ``(frame, key)`` events crossed by that
  advance, in stable source order, exactly once per crossing.

The canonical text form ``P2_ANIM_CLOCK_1`` carries the sampled source frames
*and* the event frames together, so a converted clip round-trips without a
native checkout. Existing ``p2-*-bank.txt`` rows carry only a pose count; they
are reconstructed here by uniform sampling and are flagged as count-only.

This is a contract for sampled pose banks, not a skeletal runtime and not a
second wall clock. Event delivery semantics follow the shared source clock
(``p2source::Clock``, #247): intro events play once, looping repeats
``[loop_begin, loop_end)``, crossing events are emitted ``(old, new]``, and a
one-shot finishes at ``duration`` with ``pose_frame()`` clamped to
``duration - 1``. It does not execute damage, capture, sound or drops.
"""
from dataclasses import dataclass
import math

from experimental.pikmin2_animation import MAX_POSES, sample_frames

CLOCK_MAGIC = 'P2_ANIM_CLOCK_1'
BANK_MAGIC_SUFFIX = '_BANK_1'
MAX_DURATION = 10000
MAX_EVENTS = 4096
MAX_WRAPS = 256


@dataclass(frozen=True)
class SampleClip:
    """Sampled source frames plus authored source events for one clip.

    ``poses`` are the source frames of the baked poses in ascending order.
    ``loop_end == -1`` marks a one-shot; otherwise the clip plays the intro
    ``[0, loop_begin)`` once and repeats ``[loop_begin, loop_end)``.
    """

    name: str
    duration: int
    poses: tuple
    events: tuple = ()
    loop_begin: int = 0
    loop_end: int = -1

    @property
    def looping(self):
        return self.loop_end >= 0

    def validate(self):
        if (not isinstance(self.name, str) or not self.name or len(self.name) > 68
                or any(ch.isspace() for ch in self.name)):
            raise ValueError('Invalid clip name')
        if type(self.duration) is not int or not 1 <= self.duration <= MAX_DURATION:
            raise ValueError('Invalid clip duration')
        if not isinstance(self.poses, tuple) or not 1 <= len(self.poses) <= MAX_POSES:
            raise ValueError('Invalid pose count')
        previous = -1
        for frame in self.poses:
            if type(frame) is not int or not 0 <= frame < self.duration or frame <= previous:
                raise ValueError('Invalid sampled source frame')
            previous = frame
        if not isinstance(self.events, tuple) or len(self.events) > MAX_EVENTS:
            raise ValueError('Invalid event count')
        previous = -1
        for event in self.events:
            if (not isinstance(event, tuple) or len(event) != 2
                    or type(event[0]) is not int or not 0 <= event[0] < self.duration
                    or event[0] < previous or not isinstance(event[1], str) or not event[1]
                    or any(ch.isspace() for ch in event[1])):
                raise ValueError('Invalid source event')
            previous = event[0]
        if self.loop_end == -1:
            if self.loop_begin != 0:
                raise ValueError('One-shot clip must have loop_begin 0')
        elif (type(self.loop_begin) is not int or type(self.loop_end) is not int
                or not 0 <= self.loop_begin < self.loop_end <= self.duration):
            raise ValueError('Invalid loop bounds')
        if self.looping and any(frame >= self.loop_end for frame, _ in self.events):
            raise ValueError('Looping clip cannot carry outro events')
        return self

    def pose_index(self, source_frame):
        """Nearest sampled pose to ``source_frame``; ties keep the lower index."""
        self.validate()
        if not math.isfinite(source_frame):
            raise ValueError('Invalid source frame')
        source = min(max(float(source_frame), 0.0), float(self.duration - 1))
        best = 0
        for index in range(1, len(self.poses)):
            if abs(self.poses[index] - source) < abs(self.poses[best] - source):
                best = index
        return best


@dataclass(frozen=True)
class Occurrence:
    frame: int
    key: str
    cycle: int


@dataclass(frozen=True)
class Batch:
    error: object = None
    generation: int = 0
    events: tuple = ()

    def __bool__(self):
        return self.error is None


class Clock:
    """Advance a :class:`SampleClip` in source frames and expose crossed events.

    The clock owns source position only. Family receivers translate event keys;
    pose selection reads ``pose_index()`` independently of dispatched events.
    """

    def __init__(self):
        self._clip = None
        self._frame = 0.0
        self._cycle = 0
        self._generation = 0
        self._active = False
        self._entry = False
        self._paused = False

    def start(self, clip):
        clip.validate()
        self._clip = clip
        self._generation += 1
        self._frame = 0.0
        self._cycle = 0
        self._active = True
        self._entry = True
        self._paused = False
        return True

    def restart(self):
        return self._active and self.start(self._clip)

    def seek(self, frame):
        clip = self._clip
        if not self._active or not math.isfinite(frame) or frame < 0:
            return False
        limit = clip.loop_end if clip.looping else clip.duration
        if (clip.looping and frame >= clip.loop_end) or (not clip.looping and frame > limit):
            return False
        self._generation += 1
        self._frame = float(frame)
        self._cycle = 0
        self._entry = False
        return True

    def cancel(self):
        self._active = False
        self._entry = False

    def pause(self, paused):
        self._paused = bool(paused)

    def current(self, batch):
        return self._active and bool(batch) and batch.generation == self._generation

    def frame(self):
        return self._frame

    def pose_frame(self):
        if not self._active:
            return 0.0
        return min(self._frame, float(self._clip.duration - 1))

    def pose_index(self):
        return self._clip.pose_index(self.pose_frame()) if self._active else 0

    def cycle(self):
        return self._cycle

    def generation(self):
        return self._generation

    def finished(self):
        return self._active and not self._clip.looping and self._frame == self._clip.duration

    def advance(self, delta):
        if not self._active:
            return self._failure('inactive')
        if not math.isfinite(delta) or delta < 0:
            return self._failure('invalid')
        out = Batch(generation=self._generation)
        if self._paused or delta == 0:
            return out
        clip = self._clip
        pos = self._frame
        remaining = float(delta)
        cycle = self._cycle
        wraps = 0
        emitted = []

        def emit(start, end, include_start):
            for frame, key in clip.events:
                if (frame > start or (include_start and frame == start)) and frame <= end:
                    if len(emitted) == MAX_EVENTS:
                        return False
                    emitted.append(Occurrence(frame, key, cycle))
            return True

        if self._entry and not emit(pos, pos, True):
            return self._failure('budget')
        while remaining > 0:
            end = clip.loop_end if clip.looping else clip.duration
            distance = end - pos
            if remaining < distance:
                if not emit(pos, pos + remaining, False):
                    return self._failure('budget')
                pos += remaining
                remaining = 0.0
            else:
                if not emit(pos, end, False):
                    return self._failure('budget')
                remaining -= distance
                if not clip.looping:
                    pos = float(end)
                    break
                wraps += 1
                if wraps > MAX_WRAPS:
                    return self._failure('budget')
                cycle += 1
                pos = float(clip.loop_begin)
                if not emit(pos, pos, True):
                    return self._failure('budget')
        self._frame = pos
        self._cycle = cycle
        self._entry = False
        return Batch(generation=self._generation, events=tuple(emitted))

    def _failure(self, error):
        return Batch(error=error, generation=self._generation)


def manifest_clip(clip, loop_begin=0, loop_end=-1):
    """Build a :class:`SampleClip` from one schema-1 manifest clip record."""
    name = clip['name']
    duration = clip['source_frames']
    poses = clip.get('poses') or ()
    frames = [pose['frame'] for pose in poses if isinstance(pose, dict) and 'frame' in pose]
    if len(frames) != len(poses) or not frames:
        if not poses:
            raise ValueError('Manifest clip has no sampled poses')
        generated = sample_frames(duration, min(MAX_POSES, max(2, len(poses))))
        frames = generated[:len(poses)]
    events = []
    for event in clip.get('events', ()):
        if isinstance(event, dict):
            events.append((int(event['frame']), str(event.get('type', event.get('key')))))
        else:
            events.append((int(event[0]), str(event[1])))
    return SampleClip(name, duration, tuple(frames), tuple(events), loop_begin, loop_end)


def bank_clips(text):
    """Reconstruct :class:`SampleClip` records from a ``p2-*-bank.txt`` body.

    The legacy row carries only a pose count, so sampled frames are uniform and
    the result is a lossy reconstruction; ``P2_ANIM_CLOCK_1`` is authoritative
    for exact sampled frames. Authored events are preserved exactly.
    """
    tokens = text.split()
    if not tokens or not tokens[0].startswith('P2_') or not tokens[0].endswith(BANK_MAGIC_SUFFIX):
        raise ValueError('Invalid bank header')
    result = {}
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token == 'species':
            if index + 2 >= len(tokens):
                raise ValueError('Truncated bank species row')
            index += 3
        elif token == 'clip':
            if index + 7 >= len(tokens):
                raise ValueError('Truncated bank clip row')
            species = tokens[index + 1]
            name = tokens[index + 2]
            duration = int(tokens[index + 3])
            events_token = tokens[index + 4]
            if tokens[index + 5] != 'poses':
                raise ValueError('Invalid bank clip marker')
            poses = int(tokens[index + 6])
            index += 8
            events = ()
            if events_token != '-':
                pairs = []
                for chunk in events_token.split(','):
                    frame, _, key = chunk.partition(':')
                    pairs.append((int(frame), key))
                events = tuple(pairs)
            frames = tuple(sample_frames(duration, min(MAX_POSES, max(2, poses)))[:poses]) if poses else ()
            result.setdefault(species, []).append(
                SampleClip(name, duration, frames, events))
        else:
            raise ValueError('Invalid bank token')
    return result


def render_clock_bank(clips):
    """Serialize clips to the canonical ``P2_ANIM_CLOCK_1`` text (LF, ASCII)."""
    clips = list(clips)
    rows = [f'{CLOCK_MAGIC} {len(clips)}']
    for clip in clips:
        clip.validate()
        rows.append(f'clip {clip.name} {clip.duration} {clip.loop_begin} {clip.loop_end} '
                    f'{len(clip.poses)} {len(clip.events)}')
        rows.append('poses ' + ' '.join(str(frame) for frame in clip.poses))
        for frame, key in clip.events:
            rows.append(f'event {frame} {key}')
    return ('\n'.join(rows) + '\n').encode('ascii')


def parse_clock_bank(text):
    """Parse canonical ``P2_ANIM_CLOCK_1`` text back into clips (round-trip)."""
    tokens = text.split()
    if len(tokens) < 2 or tokens[0] != CLOCK_MAGIC:
        raise ValueError('Invalid clock bank header')
    count = int(tokens[1])
    if count < 0:
        raise ValueError('Invalid clock bank count')
    index = 2
    result = []
    for _ in range(count):
        if index >= len(tokens) or tokens[index] != 'clip':
            raise ValueError('Expected clip record')
        name = tokens[index + 1]
        duration = int(tokens[index + 2])
        loop_begin = int(tokens[index + 3])
        loop_end = int(tokens[index + 4])
        pose_count = int(tokens[index + 5])
        event_count = int(tokens[index + 6])
        index += 7
        if tokens[index] != 'poses':
            raise ValueError('Expected pose record')
        poses = tuple(int(token) for token in tokens[index + 1:index + 1 + pose_count])
        index += 1 + pose_count
        events = []
        for _ in range(event_count):
            if tokens[index] != 'event':
                raise ValueError('Expected event record')
            events.append((int(tokens[index + 1]), tokens[index + 2]))
            index += 3
        result.append(SampleClip(name, duration, poses, tuple(events),
                                 loop_begin, loop_end).validate())
    if index != len(tokens):
        raise ValueError('Trailing clock bank data')
    return result


CONSUMERS = {
    'pc_p2_batch2': {
        'source': 'p2-<family>-bank.txt (P2_*_BANK_1)',
        'adopts': 'source-frame pose index and event stream for the five pose-bank families',
        'replaces': 'per-draw phase from the P1 animator counter plus Clip::index',
    },
    'pc_p2_batch3': {
        'source': 'p2-<family>-bank.txt (P2_*_BANK_1)',
        'adopts': 'the same shared helper; removes the duplicated batch2 draw math',
        'replaces': 'copied nearest-pose selection with no event timing',
    },
    'pc_p2_hardlanes': {
        'source': 'p2-bigtreasure-visual.txt events plus pose frames',
        'adopts': 'unifies the floor pose index and p2retail event player onto one cursor',
        'replaces': 'pc_p2_bigtreasure_visual_pose_index + retail player split',
    },
    'pc_p2_long_legs': {
        'source': 'bind-pose mesh only (no bank)',
        'adopts': 'nothing this batch; the contract is named but not applicable',
        'replaces': 'n/a',
    },
    'pc_p2_mamuta': {
        'source': 'sampled bank plus motion anchor',
        'adopts': 'optional migration off bespoke counter math',
        'replaces': 'p2mamuta::anchor frame math',
    },
    'pc_p2_breadbug_actor': {
        'source': 'cargo pose bank with authored events',
        'adopts': 'optional migration off select()/counter math',
        'replaces': 'p2breadbugcargo::select',
    },
}
