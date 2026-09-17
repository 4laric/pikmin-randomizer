"""Silent-run audio policy and log checker for automated P2 preview fixtures.

Tooling only (issue #116). Automated fixture launches must not open a real
audio device; the established launcher convention is SDL_AUDIODRIVER=dummy
(see scripts/test_native_startup.py and the test_*_native.py launchers).
This module computes and validates that silent-run environment and classifies
a captured run log as silent-verified, audio-device-open, or unknown.

It NEVER claims the native sustained dial-tone fault is fixed: muting (even
via the dummy driver) is a capture workaround, and the root cause stays
tracked separately in #116. A silent-verified verdict means "this log shows
no audio-device activity", not "the fault is gone".
"""
import re

SILENT_POLICY_VERSION = 1
SILENT_AUDIO_DRIVER = 'dummy'
BACKGROUND_MARKER = 'PIKMIN_RANDOMIZER_TEST_BACKGROUND'

_LAUNCH_SILENT_ACK = (
    re.compile(r'SDL_AUDIODRIVER\s*=\s*dummy', re.IGNORECASE),
    re.compile(r'SDL audio driver:\s*dummy', re.IGNORECASE),
    re.compile(r'using dummy audio', re.IGNORECASE),
)
_DEVICE_OPEN = (
    re.compile(r'WASAPI', re.IGNORECASE),
    re.compile(r'DirectSound', re.IGNORECASE),
    re.compile(r'SDL_OpenAudio', re.IGNORECASE),
    re.compile(r'opened?\s+audio\s+device', re.IGNORECASE),
    re.compile(r'audio\s+device\s+open', re.IGNORECASE),
    re.compile(r'dial[\s-]*tone', re.IGNORECASE),
    re.compile(r'continuous\s+tone', re.IGNORECASE),
)
_RUN_END = (
    re.compile(r'\bexit\s+code\b', re.IGNORECASE),
    re.compile(r'\brun\s+complete\b', re.IGNORECASE),
    re.compile(r'\bfixture\s+complete\b', re.IGNORECASE),
    re.compile(r'\bcompleted\b', re.IGNORECASE),
    re.compile(r'\bPASSED\b|\bFAILED\b|\bpassed\b|\bfailed\b'),
)


class PolicyRejected(ValueError):
    """Malformed policy input or unclassifiable evidence; never a placement."""


def silent_run_environ(base=None):
    """Return a launch environment with the silent audio driver enforced.

    `base` may be None (fresh from os.environ semantics: empty mapping) or a
    str->str mapping; anything else fails closed. Never mutates the input.
    """
    if base is None:
        merged = {}
    elif isinstance(base, dict) and all(isinstance(k, str) and isinstance(v, str)
                                        for k, v in base.items()):
        merged = dict(base)
    else:
        raise PolicyRejected('base must be None or a str->str mapping')
    merged['SDL_AUDIODRIVER'] = SILENT_AUDIO_DRIVER
    return merged


def validate_silent_environ(env):
    """Require the silent driver; return a normalized copy or raise.

    The dummy driver is a capture workaround, not a fault fix; see #116.
    """
    if not isinstance(env, dict) or not all(isinstance(k, str) and isinstance(v, str)
                                            for k, v in env.items()):
        raise PolicyRejected('env must be a str->str mapping')
    driver = env.get('SDL_AUDIODRIVER')
    if driver != SILENT_AUDIO_DRIVER:
        raise PolicyRejected(
            'silent runs require SDL_AUDIODRIVER=%r, got %r' % (SILENT_AUDIO_DRIVER, driver))
    return dict(env)


def classify_run_log(text):
    """Classify a captured run log.

    - audio-device-open: any device-open marker present (wins over silence
      markers; a run that opened a device is never silent-verified).
    - silent-verified: a silent-launch ack marker AND a run-end marker are
      present AND no device-open marker is present.
    - unknown: everything else, including empty/missing logs. Fail-closed.
    """
    if not isinstance(text, str) or not text.strip():
        raise PolicyRejected('run log text required')
    if any(pattern.search(text) for pattern in _DEVICE_OPEN):
        return 'audio-device-open'
    ack = any(pattern.search(text) for pattern in _LAUNCH_SILENT_ACK)
    ended = any(pattern.search(text) for pattern in _RUN_END)
    if ack and ended:
        return 'silent-verified'
    return 'unknown'


def describe():
    """Machine-readable policy summary for packets and docs."""
    return dict(schema=1, policy_version=SILENT_POLICY_VERSION,
                silent_audio_driver=SILENT_AUDIO_DRIVER,
                background_marker=BACKGROUND_MARKER,
                verdicts=('silent-verified', 'audio-device-open', 'unknown'),
                fault_note=('dummy audio is a capture workaround; the native '
                            'sustained dial-tone root cause is tracked in #116 '
                            'and is NOT fixed by this policy'))
