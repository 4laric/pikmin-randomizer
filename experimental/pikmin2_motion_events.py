"""Source-backed event metadata; no playback or gameplay effects."""
import argparse
import hashlib
from pathlib import Path
import re
import struct
from experimental.pikmin2_purple import bca_pose


def registry(raw):
    if len(raw) > 1024 * 1024:
        raise ValueError("Animation registry exceeds budget")
    text = re.sub(r"#[^\r\n]*", "", raw.decode("shift_jis"))
    tokens = iter(re.findall(r"[{}]|[^\s{}]+", text))
    def pop():
        try:
            return next(tokens)
        except StopIteration as exc:
            raise ValueError("Truncated animation registry") from exc
    def integer():
        value = pop()
        if not re.fullmatch(r"-?[0-9]{1,10}", value):
            raise ValueError("Invalid integer")
        return int(value)
    count = integer()
    if not 1 <= count <= 256:
        raise ValueError("Invalid clip count")
    result, names, total = [], set(), 0
    for _ in range(count):
        if pop() != "{":
            raise ValueError("Missing clip block")
        pop()  # Editor path is provenance text, never a filesystem instruction.
        name = pop()
        if not re.fullmatch(r"[a-z0-9_]{1,64}\.bca", name) or name in names:
            raise ValueError("Invalid or duplicate clip name")
        names.add(name)
        events, previous, loop_start = [], -1, None
        while True:
            frame = integer()
            if frame == -1:
                break
            kind = integer()
            if frame < previous or frame < 0 or not 0 <= kind < 1000:
                raise ValueError("Invalid event order/frame/type")
            if kind == 0:
                loop_start = frame
            if kind == 1 and (loop_start is None or frame <= loop_start):
                raise ValueError("Unmatched or empty event loop")
            previous = frame
            events.append((frame, kind))
            total += 1
            if len(events) > 4096 or total > 65536:
                raise ValueError("Event budget exceeded")
        if pop() != "}":
            raise ValueError("Missing clip terminator")
        result.append((name, events))
    if next(tokens, None) is not None:
        raise ValueError("Trailing registry data")
    return result


def encode(directory):
    directory = Path(directory)
    raw = (directory / "enemyanimmgr.txt").read_bytes()
    rows = registry(raw)
    digest = lambda data: hashlib.sha256(data).hexdigest()
    lines = [f"P2_RETAIL_EVENTS_1 {digest(raw)} {len(rows)}"]
    for name, events in rows:
        path = directory / name
        if path.stat().st_size > 16 * 1024 * 1024:
            raise ValueError("BCA exceeds budget")
        data = path.read_bytes()
        if len(data) < 72:
            raise ValueError("Truncated BCA")
        duration, _ = bca_pose(data, 0, struct.unpack_from(">H", data, 44)[0], allow_scale=True)
        if not 1 <= duration <= 10000 or data[40] > 4 or any(frame >= duration for frame, _ in events):
            raise ValueError("Unsupported BCA duration/attribute or event outside clip")
        lines.append(f"{name} {duration} {data[40]} {digest(data)} {len(events)}")
        lines.extend(f"{frame} {kind}" for frame, kind in events)
    return ("\n".join(lines) + "\n").encode("ascii")


def write(directory, output):
    data = encode(directory)  # Validate everything before creating output.
    with Path(output).open("xb") as stream:
        stream.write(data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    write(args.directory, args.output)
