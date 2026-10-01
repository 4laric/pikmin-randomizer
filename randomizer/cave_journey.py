"""Versioned two-floor developer journey, independent of campaign/AP saves."""
import copy
import hashlib
import json
from pathlib import Path

from randomizer.cave_floor import create_journey_floor, fingerprint, atomic_write
from experimental.pikmin2_cave_lane41_generator import _seed_uint64

POLICY = 'forest1-two-floor-journey-v1'


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON field: '+key)
            result[key] = value
        return result
    return json.loads(Path(path).read_text(),object_pairs_hook=unique)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def create(seed, slot='Player1'):
    return dict(schema='p2-cave-journey/1', policy=POLICY, seed=seed, slot=slot,
                floors=[dict(descriptor=create_journey_floor(seed, slot, n), salt=n-1)
                        for n in (1, 2)])


def validate(journey):
    if type(journey) is not dict or encoded(journey) != encoded(create(journey.get('seed'), journey.get('slot'))):
        raise ValueError('foreign or malformed journey')
    return journey


def identity(journey):
    validate(journey)
    return hashlib.sha256(encoded(journey).encode()).hexdigest()


def zero_buds(manifest):
    table = manifest['table']
    return (f"P2_CAVE_BUD_STATE_1\n{_seed_uint64(table['seed'])} {table['cave_id']} {table['floor']} {len(table['buds'])}\n"
            + ''.join(f"{b['slot_id']} 0\n" for b in table['buds']))


def initial_entry(manifest, squad=None, health=1):
    return dict(schema=1, fingerprint=fingerprint(manifest), health=health,
                squad=copy.deepcopy(squad if squad is not None else [[1, 0]]*20),
                buds=zero_buds(manifest), receipts='P2_RECEIPTS_1\n')


class Session:
    """Caller holds the OS session lock through recovery, launch and commit."""
    def __init__(self, directory, journey, placements):
        self.directory = Path(directory).resolve()
        self.journey = validate(journey)
        self.fingerprint = identity(journey)
        self.placements = placements
        self.manifests = {n: journey['floors'][n-1]['descriptor'] for n in (1, 2)}
        for n, manifest in self.manifests.items():
            placement = placements[n]
            expected = {(f"item:{t['slot_id']}:0",t['slot_id'],t['treasure_id']) for t in manifest['table']['treasures']}
            actual = {(v['slot_id'],v['host'],v['item']) for v in placement['items']}
            if (placement['floor'] != n or placement['cave'] != 'forest_1'
                    or placement['seed'] != _seed_uint64(manifest['table']['seed'])
                    or actual != expected or len(placement['items']) != len(expected)):
                raise ValueError('floor placement identity differs from journey')
        self.state_path = self.directory/'state.json'
        self.pending_path = self.directory/'pending.json'

    def ledger_path(self, floor):
        return self.directory/f'floor-{floor}-receipts.txt'

    def ledger(self, floor):
        from scripts.play_pikmin2_cave import receipts
        path = self.ledger_path(floor)
        if not path.is_file():
            raise ValueError('missing durable floor ledger; refusing reset')
        text = path.read_text()
        receipts(text, self.placements[floor])
        return text

    def initialize(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        if self.state_path.exists():
            return self.load()
        if self.pending_path.exists():
            raise ValueError('lost journey state; refusing starter reset')
        for n in (1, 2):
            p = self.ledger_path(n)
            if p.exists() and p.read_text() != 'P2_RECEIPTS_1\n':
                raise ValueError('lost journey state with existing receipts')
            if not p.exists():
                atomic_write(p, 'P2_RECEIPTS_1\n')
        state = dict(schema=1, journey=self.fingerprint, floor=1, revision=0,
                     entry=initial_entry(self.manifests[1]), boundary=None)
        atomic_write(self.state_path, encoded(state)+'\n')
        return self.load()

    def run_path(self, value):
        path = Path(value).resolve()
        if path.parent != (self.directory/'runs').resolve() or not path.is_dir():
            raise ValueError('foreign journey run')
        return path

    def source_boundary(self, run):
        from scripts.play_pikmin2_cave import checkpoint
        transfer = (run/'p2-cave-transfer.txt').read_text()
        buds = (run/'p2-cave-bud-transfer.txt').read_text()
        ledger = self.ledger(1)
        saved = checkpoint(transfer, buds, ledger, self.manifests[1], self.placements[1])
        boundary = dict(run=str(run), transfer=transfer, buds=buds, receipts=ledger,
                        hashes={name:hashlib.sha256(text.encode()).hexdigest()
                                for name,text in [('transfer',transfer),('buds',buds),('receipts',ledger)]})
        return saved, boundary

    def destination(self, source):
        entry = initial_entry(self.manifests[2], source['squad'], source['health'])
        if self.ledger(2) != 'P2_RECEIPTS_1\n':
            raise ValueError('destination ledger predates floor transition')
        return entry

    def load(self):
        state = read_json(self.state_path)
        if (type(state) is not dict or set(state) != {'schema','journey','floor','revision','entry','boundary'}
                or type(state['schema']) is not int or state['schema'] != 1
                or state['journey'] != self.fingerprint or type(state['floor']) is not int
                or state['floor'] not in (1, 2) or type(state['revision']) is not int
                or state['revision'] != state['floor']-1):
            raise ValueError('foreign or malformed journey state')
        self.ledger(1); self.ledger(2)
        if state['floor'] == 1:
            expected = initial_entry(self.manifests[1])
            if state['boundary'] is not None:
                raise ValueError('unexpected source boundary')
        else:
            boundary = state['boundary']
            if type(boundary) is not dict or set(boundary) != {'run','transfer','buds','receipts','hashes'}:
                raise ValueError('missing source boundary')
            run = self.run_path(boundary['run'])
            source, actual = self.source_boundary(run)
            if encoded(actual) != encoded(boundary):
                raise ValueError('source boundary bytes changed')
            expected = initial_entry(self.manifests[2], source['squad'], source['health'])
        if encoded(state['entry']) != encoded(expected):
            raise ValueError('incoming squad or floor identity changed')
        return state

    def begin(self, run, state):
        if self.pending_path.exists():
            raise RuntimeError('pending journey child must be recovered first')
        if encoded(self.load()) != encoded(state):
            raise ValueError('stale journey state')
        run = self.run_path(run)
        if encoded(read_json(run/'cave.json')) != encoded(self.manifests[state['floor']]):
            raise ValueError('staged descriptor differs from journey')
        expected_entry = state['entry']
        words = (run/'p2-cave-entry.txt').read_text().split()
        expected = (['P2_CAVE_ENTRY_1', expected_entry['fingerprint'][:32], str(state['floor']),
                     str(expected_entry['health']), str(len(expected_entry['squad']))]
                    + [str(v) for row in expected_entry['squad'] for v in row])
        if words != expected:
            raise ValueError('staged entry differs from incoming boundary')
        pending = dict(schema=1, journey=self.fingerprint, floor=state['floor'], revision=state['revision'],
                       run=str(run), inputs={n: hashlib.sha256((run/n).read_bytes()).hexdigest()
                           for n in ('cave.json','p2-cave-entry.txt','layout.json','nectar.exe')})
        atomic_write(self.pending_path, encoded(pending)+'\n')

    def recover(self, live_paths=()):
        state = self.load()
        if not self.pending_path.exists():
            return state, False
        p = read_json(self.pending_path)
        if (type(p) is not dict or set(p) != {'schema','journey','floor','revision','run','inputs'}
                or type(p['schema']) is not int or p['schema'] != 1 or p['journey'] != self.fingerprint
                or type(p['floor']) is not int or p['floor'] not in (1,2)
                or type(p['revision']) is not int or p['revision'] != p['floor']-1
                or type(p['inputs']) is not dict
                or set(p['inputs']) != {'cave.json','p2-cave-entry.txt','layout.json','nectar.exe'}):
            raise ValueError('foreign pending journey')
        run = self.run_path(p['run'])
        if (run/'nectar.exe').resolve() in {Path(v).resolve() for v in live_paths}:
            raise RuntimeError('same-session child is still running')
        for n, digest in p['inputs'].items():
            if hashlib.sha256((run/n).read_bytes()).hexdigest() != digest:
                raise ValueError('pending journey input changed: '+n)
        if (run/'p2-cave-transfer.txt').exists():
            if p['floor'] != 1:
                raise ValueError('terminal floor2 transfer/return is outside this journey version')
            source, boundary = self.source_boundary(run)
            if state['floor'] == 1:
                if state['revision'] != p['revision']:
                    raise ValueError('stale transition')
                state = dict(schema=1, journey=self.fingerprint, floor=2, revision=1,
                             entry=self.destination(source), boundary=boundary)
                atomic_write(self.state_path, encoded(state)+'\n')
            elif encoded(state['boundary']) != encoded(boundary):
                raise ValueError('duplicate or foreign committed transition')
            self.pending_path.unlink()
            return self.load(), True
        if state['floor'] != p['floor'] or state['revision'] != p['revision']:
            raise ValueError('committed transition lost its source transfer')
        if (run/'p2-cave-transfer.tmp').exists() or (run/'p2-cave-bud-transfer.txt').exists():
            raise ValueError('incomplete native boundary; refusing rollback/reset')
        # No native boundary: retain the prior floor-boundary squad and budgets.
        self.pending_path.unlink()
        return state, False
