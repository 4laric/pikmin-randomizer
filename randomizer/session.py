"""Crash-safe check/reward journal. Native campaign saves are a separate concern."""
import json
import os
import time
from collections import Counter
from pathlib import Path
from .catalog import NAMES, ITEM_IDS, UNLOCKS, REPAIR, FLARLIC, FOREST_ACCESS, IMPACT_ACCESS, RED, active_names, item_pool
from .seed import fingerprint, solo_rewards
from .stats import upgrade_counts
from .benefits import benefit_state


def atomic_write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    # Native readers can briefly hold a Windows handle without delete sharing.
    # Retry replacement, never truncate the live journal to work around a lock.
    deadline = time.monotonic() + 1.0
    while True:
        try:
            os.replace(temp, path)
            break
        except PermissionError as exc:
            if os.name != 'nt' or getattr(exc, 'winerror', None) not in (5, 32, 33) or time.monotonic() >= deadline:
                raise
            time.sleep(0.01)


def death_link_summary(manifest, data):
    """One status line; empty when the seed has no DeathLink."""
    if not manifest.get("death_link"):
        return ""
    unit = manifest["death_link_pikmin"]
    deaths = data.get("pikmin_deaths", 0)
    return (f"DeathLink {unit}-Pikmin units: received {data.get('death_links_received', 0)}, "
            f"sent {deaths // unit}, {deaths % unit}/{unit} deaths toward the next")


def initial_session_data(manifest):
    """Fresh ``session.json``/``mirror.json`` payload for a manifest."""
    data = dict(schema=1, fingerprint=fingerprint(manifest), checked=[], received=[], ap_identity=None)
    if manifest.get("goal_mode") == "emperor_bulblax":
        data["emperor_defeated"] = False
    if manifest.get("death_link"):
        data["pikmin_deaths"] = 0
        data["death_links_received"] = 0
    return data


def validate_session_data(manifest, data):
    """Shared ``session.json``/``mirror.json`` schema validation."""
    names = active_names(manifest)
    allowed_items = {ITEM_IDS[n] for n in item_pool(manifest)}
    expected = initial_session_data(manifest)
    if type(data) is not dict or set(data) != set(expected):
        raise ValueError("saved session does not match manifest; refusing to reset it")
    if (type(data["schema"]) is not int or data["schema"] != 1
            or data["fingerprint"] != fingerprint(manifest)):
        raise ValueError("saved session does not match manifest; refusing to reset it")
    if (type(data["checked"]) is not list
            or any(type(n) is not str or n not in names for n in data["checked"])
            or len(data["checked"]) != len(set(data["checked"]))):
        raise ValueError("invalid saved checks")
    if (type(data["received"]) is not list
            or any(type(i) is not int or i not in allowed_items for i in data["received"])):
        raise ValueError("invalid saved received items")
    identity = data["ap_identity"]
    if identity is not None and (type(identity) is not list or len(identity) != 3
            or type(identity[0]) is not str or any(type(v) is not int for v in identity[1:])):
        raise ValueError("invalid AP identity")
    if manifest["mode"] == "solo" and (data["received"] or identity is not None):
        raise ValueError("solo save contains AP state")
    if "emperor_defeated" in data and type(data["emperor_defeated"]) is not bool:
        raise ValueError("invalid emperor state")
    for key in ("pikmin_deaths", "death_links_received"):
        if key in data and (type(data[key]) is not int or data[key] < 0):
            raise ValueError("invalid death link state")
    if data.get("death_links_received", 0) > (1 << 32) - 1:
        raise ValueError("DeathLink inventory exceeds uint32")
    return True


def render_session_state(manifest, names, inventory, data, token, ready):
    """Shared ``state.txt`` rendering for host sessions and netplay mirrors."""
    unlocks = sum(1 << i for i, name in enumerate(UNLOCKS) if inventory[name])
    if manifest['schema'] >= 3 and inventory[FOREST_ACCESS]:
        unlocks |= 32
    if manifest['schema'] >= 4 and inventory[RED]:
        unlocks |= 64
    if manifest['schema'] >= 5 and inventory[IMPACT_ACCESS]:
        unlocks |= 128
    checks = sum(1 << i for i, name in enumerate(names) if name in data["checked"])
    if manifest['schema'] >= 8:
        indices = [str(i) for i, n in enumerate(names) if n in data['checked']]
        checks = 'CHECKS ' + str(len(indices)) + (' ' + ' '.join(indices) if indices else '')
    emperor = (" EMPEROR " + str(int(data["emperor_defeated"]))) if manifest.get("goal_mode") == "emperor_bulblax" else ""
    # The native game treats the first value it reads as its baseline, so
    # links received while the game was closed are never replayed.
    death_link = (" DEATHLINK " + str(data["death_links_received"])) if manifest.get("death_link") else ""
    repairs = min(inventory[REPAIR], manifest["goal"])
    if manifest["schema"] >= 2:
        flarlic = min(10 - manifest.get("starting_flarlic", 2), inventory[FLARLIC])
        return (f"PIKMIN_STATE {manifest['schema']} {token} {int(ready)} {repairs} {unlocks} {flarlic} "
                f"{checks}{upgrade_counts(manifest, inventory)}{benefit_state(manifest, inventory)}"
                f"{emperor}{death_link} END\n")
    return f"PIKMIN_STATE 1 {token} {int(ready)} {repairs} {unlocks} {checks} END\n"


class Session:
    def __init__(self, manifest, directory):
        self.manifest = manifest
        self.fingerprint = fingerprint(manifest)
        self.names = active_names(manifest)
        self.allowed_items = {ITEM_IDS[n] for n in item_pool(manifest)}
        self.directory = Path(directory)
        self.path = self.directory / "session.json"
        self.rewards = solo_rewards(manifest) if manifest["mode"] == "solo" else {}
        self.data = initial_session_data(manifest)
        if self.path.exists():
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            validate_session_data(manifest, loaded)
            self.data = loaded
        # Native delivery is fsynced before the runner sees it. Recover complete
        # records from older runs if the runner was interrupted before its save.
        recovered = False
        for journal in self.directory.glob("runs/*/checks.txt"):
            bootstrap = journal.parent / "bootstrap.txt"
            if not bootstrap.exists():
                raise ValueError("orphaned native check journal")
            fields = bootstrap.read_text(encoding="ascii").split()
            # The seed-bound captain extension is last, after optional Purple.
            # Never infer opt-in from a journal belonging to a legacy manifest.
            if manifest.get('p2_second_captain'):
                if fields[-3:] != ['CAPTAINS', '2', 'END']:
                    raise ValueError('native journal second-captain mode mismatch')
                fields = fields[:-3] + ['END']
            if 'CAPTAINS' in fields:
                raise ValueError('native journal second-captain mode mismatch')
            # White flags are part of the validated seed fingerprint. Normalize
            # only the exact enabled suffix, in native order, before legacy checks.
            if manifest.get('p2_white_treasure_campaign'):
                if fields[-3:] != ['WHITE_TREASURE', '1', 'END']:
                    raise ValueError('native journal White treasure mode mismatch')
                fields = fields[:-3] + ['END']
            if 'WHITE_TREASURE' in fields:
                raise ValueError('native journal White treasure mode mismatch')
            if manifest.get('p2_white_campaign'):
                if fields[-3:] != ['WHITE', '1', 'END']:
                    raise ValueError('native journal White mode mismatch')
                fields = fields[:-3] + ['END']
                if fields[-3:] != ['PURPLE', '1', 'END']:
                    raise ValueError('native journal White requires Purple mode')
            if 'WHITE' in fields:
                raise ValueError('native journal White mode mismatch')
            # Purple is a pinned session option, not a seed schema extension.
            # Normalize only its exact native suffix before the legacy count
            # check; unknown modes and non-P2 seeds must still fail closed.
            if 'p2_layout' in manifest and fields[-3:] == ['PURPLE', '1', 'END']:
                fields = fields[:-3] + ['END']
            if 'enemy_catalog' in manifest:
                from .enemy_catalog import bootstrap as catalog_bootstrap
                extension = catalog_bootstrap(manifest).split()
                if fields[-len(extension)-1:-1] != extension:
                    raise ValueError('native journal check catalog mismatch')
                fields = fields[:-len(extension)-1] + ['END']
            if manifest.get('enemy_composition'):
                from .enemy_slots import bootstrap_slots
                extension = bootstrap_slots(manifest).split()
                # Validate the complete ordered P1/P2 block before removing its
                # composition header for the legacy field-count check below.
                if fields.count('ENEMY_COMPOSITION') != 1:
                    raise ValueError('native journal enemy composition mismatch')
                start = fields.index('ENEMY_COMPOSITION')
                if fields[start:-1] != extension:
                    raise ValueError('native journal enemy composition mismatch')
                fields = fields[:start] + fields[start + 3:]
            elif 'ENEMY_COMPOSITION' in fields:
                raise ValueError('native journal enemy composition mismatch')
            if manifest.get('p2_proxy_tier'):
                if fields[-3:] != ['P2_PROXY_TIER', '1', 'END']:
                    raise ValueError('native journal proxy tier mismatch')
                fields = fields[:-3] + ['END']
            if len(fields) != ((23 if manifest['schema'] >= 9 else 21 if manifest['schema'] >= 6 else 19 if manifest['schema'] >= 4 else 17) + (2 if 'starting_flarlic' in manifest else 0) + (16 if 'color_stats' in manifest else 0) + (2 if manifest.get('progressive_color_stats') else 0) + (2 if manifest.get('benefit_items') else 0) + (2 if manifest.get('progressive_maturity') else 0) + (3 if manifest.get('progressive_day_length') else 0) + (2 if manifest.get('whistle_pluck_item') else 0) + (33 if 'spawn_layout' in manifest else 0) + (27 if 'group_layout' in manifest else 0) + (2 if manifest.get('miniboss_enemies') and 'campaign_layout' not in manifest else 0) + (5 + 2 * len(manifest['campaign_layout']['assignments']) if 'campaign_layout' in manifest else 0) + (2 if manifest.get('death_link') else 0) + (4 + 2 * len(manifest['p2_layout']['bindings']) if 'p2_layout' in manifest else 0)) or fields[:2] != ["PIKMIN_RANDOMIZER", str(manifest["schema"])] or fields[2:4] != ["SESSION", journal.parent.name] or fields[4:6] != ["FINGERPRINT", self.fingerprint]:
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
        for journal in self.directory.glob("runs/*/emperor.txt"):
            self.recover_emperor(journal.parent)

    def recover_emperor(self, directory):
        path = Path(directory) / "emperor.txt"
        if not path.exists(): return
        text = path.read_text(encoding="ascii")
        if not text.endswith("\n"): return
        expected = f"EMPEROR_DEFEATED {Path(directory).name} {self.fingerprint}\n"
        if self.manifest.get("goal_mode") != "emperor_bulblax" or text != expected:
            raise ValueError("foreign or invalid Emperor journal")
        if self.inventory[REPAIR] < 25: raise ValueError("Emperor defeated before repair gate")
        if not self.data["emperor_defeated"]:
            self.data["emperor_defeated"] = True
            self.save()

    def save(self):
        atomic_write(self.path, json.dumps(self.data, indent=2) + "\n")

    @property
    def death_link_unit(self):
        return self.manifest["death_link_pikmin"] if self.manifest.get("death_link") else 0

    def record_deaths(self, count):
        """Ordinary (non-induced) Pikmin deaths reported by the native game."""
        if not self.death_link_unit or type(count) is not int or count < 0:
            raise ValueError("invalid death report")
        if count:
            self.data["pikmin_deaths"] += count
            self.save()

    def receive_death_link(self):
        if not self.death_link_unit:
            raise ValueError("death link disabled for this seed")
        self.data["death_links_received"] += 1
        self.save()

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
        return self.inventory[REPAIR] >= self.manifest["goal"] and (self.manifest.get("goal_mode") != "emperor_bulblax" or self.data["emperor_defeated"])

    def native_state(self, token, ready):
        return render_session_state(self.manifest, self.names, self.inventory, self.data, token, ready)


def resolve_session_file(directory):
    """Return the session file overlay/tracker readers should open.

    The host layout stores ``session.json``; a netplay client mirror stores
    ``mirror.json`` with the same schema. Pointing ``--session-dir`` at a
    mirror directory reads the mirror. When ``session.json`` exists it wins,
    so host behaviour is unchanged.
    """
    directory = Path(directory)
    primary = directory / "session.json"
    if primary.exists():
        return primary
    mirror = directory / "mirror.json"
    if mirror.exists():
        return mirror
    return primary


def load_session_data(directory):
    """Parse the resolved session/mirror file for overlay/tracker readers."""
    return json.loads(resolve_session_file(directory).read_text(encoding="utf-8"))


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
