"""Crash-safe check/reward journal. Native campaign saves are a separate concern."""
import json
import os
from collections import Counter
from pathlib import Path
from .catalog import NAMES, ITEM_IDS, UNLOCKS, REPAIR, FLARLIC, FOREST_ACCESS, IMPACT_ACCESS, RED, active_names, item_pool
from .seed import fingerprint, solo_rewards


def atomic_write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


class Session:
    def __init__(self, manifest, directory):
        self.manifest = manifest
        self.fingerprint = fingerprint(manifest)
        self.names = active_names(manifest)
        self.allowed_items = {ITEM_IDS[n] for n in item_pool(manifest)}
        self.directory = Path(directory)
        self.path = self.directory / "session.json"
        self.rewards = solo_rewards(manifest) if manifest["mode"] == "solo" else {}
        self.data = dict(schema=1, fingerprint=self.fingerprint, checked=[], received=[], ap_identity=None)
        if self.path.exists():
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            if (type(loaded) is not dict or set(loaded) != set(self.data)
                    or type(loaded["schema"]) is not int or loaded["schema"] != 1 or loaded["fingerprint"] != self.fingerprint):
                raise ValueError("saved session does not match manifest; refusing to reset it")
            if (type(loaded["checked"]) is not list or any(type(n) is not str or n not in self.names for n in loaded["checked"])
                    or len(loaded["checked"]) != len(set(loaded["checked"]))):
                raise ValueError("invalid saved checks")
            if type(loaded["received"]) is not list or any(type(i) is not int or i not in self.allowed_items for i in loaded["received"]):
                raise ValueError("invalid saved received items")
            identity = loaded["ap_identity"]
            if identity is not None and (type(identity) is not list or len(identity) != 3
                    or type(identity[0]) is not str or any(type(v) is not int for v in identity[1:])):
                raise ValueError("invalid AP identity")
            if manifest["mode"] == "solo" and (loaded["received"] or identity is not None):
                raise ValueError("solo save contains AP state")
            self.data = loaded
        # Native delivery is fsynced before the runner sees it. Recover complete
        # records from older runs if the runner was interrupted before its save.
        recovered = False
        for journal in self.directory.glob("runs/*/checks.txt"):
            bootstrap = journal.parent / "bootstrap.txt"
            if not bootstrap.exists():
                raise ValueError("orphaned native check journal")
            fields = bootstrap.read_text(encoding="ascii").split()
            if len(fields) != (21 if manifest['schema'] >= 6 else 19 if manifest['schema'] >= 4 else 17) or fields[:2] != ["PIKMIN_RANDOMIZER", str(manifest["schema"])] or fields[2:4] != ["SESSION", journal.parent.name] or fields[4:6] != ["FINGERPRINT", self.fingerprint]:
                raise ValueError("native journal belongs to an incompatible manifest")
            data = journal.read_bytes()
            for line in data[:data.rfind(b"\n") + 1].splitlines():
                if not line.isdigit() or not 0 <= int(line) < len(self.names):
                    raise ValueError("corrupt persisted native check journal")
                name = self.names[int(line)]
                if name not in self.data["checked"]:
                    self.data["checked"].append(name)
                    recovered = True
        if recovered:
            self.save()

    def save(self):
        atomic_write(self.path, json.dumps(self.data, indent=2) + "\n")

    def collect(self, name):
        if name not in self.names:
            raise ValueError("unknown native check: " + str(name))
        if name not in self.data["checked"]:
            self.data["checked"].append(name)
            self.save()
            return True
        return False

    def bind_ap(self, seed_name, team, slot):
        if self.manifest["mode"] != "ap" or type(seed_name) is not str or any(type(v) is not int for v in (team, slot)):
            raise ValueError("invalid AP identity")
        identity = [seed_name, team, slot]
        if self.data["ap_identity"] not in (None, identity):
            raise ValueError("AP room/team/slot mismatch; refusing to merge sessions")
        self.data["ap_identity"] = identity
        self.save()

    def receive(self, index, items):
        if self.manifest["mode"] != "ap" or self.data["ap_identity"] is None:
            raise ValueError("received items before AP authentication")
        old = self.data["received"]
        if type(index) is not int or index < 0 or index > len(old):
            raise ValueError("AP item stream gap; request full Sync")
        if type(items) is not list or any(type(i) is not int or i not in self.allowed_items for i in items):
            raise ValueError("unknown item in standalone AP stream")
        overlap = min(len(old) - index, len(items))
        if old[index:index + overlap] != items[:overlap]:
            raise ValueError("AP item stream conflicts with persisted receipts")
        old.extend(items[overlap:])
        self.save()

    @property
    def inventory(self):
        if self.manifest["mode"] == "solo":
            return Counter(self.rewards[n] for n in self.data["checked"])
        names = {v: k for k, v in ITEM_IDS.items()}
        return Counter(names[i] for i in self.data["received"])

    @property
    def goal(self):
        return self.inventory[REPAIR] >= self.manifest["goal"]

    def native_state(self, token, ready):
        inventory = self.inventory
        unlocks = sum(1 << i for i, name in enumerate(UNLOCKS) if inventory[name])
        if self.manifest['schema'] >= 3 and inventory[FOREST_ACCESS]:
            unlocks |= 32
        if self.manifest['schema'] >= 4 and inventory[RED]:
            unlocks |= 64
        if self.manifest['schema'] >= 5 and inventory[IMPACT_ACCESS]:
            unlocks |= 128
        checks = sum(1 << i for i, name in enumerate(self.names) if name in self.data["checked"])
        repairs = min(inventory[REPAIR], self.manifest["goal"])
        if self.manifest["schema"] >= 2:
            flarlic = min(8, inventory[FLARLIC])
            return f"PIKMIN_STATE {self.manifest['schema']} {token} {int(ready)} {repairs} {unlocks} {flarlic} {checks} END\n"
        return f"PIKMIN_STATE 1 {token} {int(ready)} {repairs} {unlocks} {checks} END\n"


class SessionLock:
    """OS-owned lock, released even after a crash; do not delete another runner's file."""
    def __init__(self, directory):
        self.directory = Path(directory)
        self.file = None

    def __enter__(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        self.file = (self.directory / "runner.lock").open("a+b")
        self.file.seek(0, 2)
        if self.file.tell() == 0:
            self.file.write(b"0");self.file.flush()
        self.file.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.file.close()
            raise ValueError("another runner owns this session directory") from exc
        return self

    def __exit__(self, *args):
        self.file.close()
