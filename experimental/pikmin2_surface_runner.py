"""Resume cave runs against one SurfaceLedger; no native surface renderer."""
import json
from pathlib import Path
import subprocess

from experimental import pikmin2_campaign as cave
from randomizer.session import SessionLock, atomic_write


class NativeContent:
    """Two-floor staging with cave-only identity or opt-in versioned surface binding."""
    def __init__(self, assets, imported, pods, purple, treasure, transitions=None,
                 snow=None, roster=None, transition_assets=None, *, source_import=None, pocket=None):
        from experimental.pikmin2_transitions import read_transitions, read_visuals
        self.assets, self.imported = Path(assets), Path(imported)
        self.pods, self.purple, self.treasure = list(map(Path, pods)), Path(purple), Path(treasure)
        self.snow, self.roster = snow, roster
        self.anchors, self.visuals = read_transitions(transitions), read_visuals(transition_assets)
        if len(self.pods) != 2 or (self.visuals and not self.anchors) or (roster and not snow):
            raise ValueError('Invalid two-floor content options')
        if (source_import is None) != (pocket is None):
            raise ValueError('Surface identity requires source import and pocket together')
        self.identity = cave.content_identity(self.imported, self.pods, self.purple,
                                             self.anchors, snow, roster, self.visuals)
        if source_import is not None:
            from experimental.pikmin2_surface_identity import surface_identity
            self.identity = surface_identity(self.identity, self.treasure, source_import, pocket)

    def stage(self, checkpoint, token, runs):
        from experimental.pikmin2_transitions import install_visuals
        floor = checkpoint['floor']
        run = cave.prepare(self.assets, self.imported, self.treasure, runs,
                           floor=floor, pod=self.pods[floor-1], purple=self.purple,
                           violet=floor == 2, squad=checkpoint['squad'])
        if self.roster:
            from experimental.pikmin2_roster import install
            install(self.roster, run, floor, self.assets, self.imported)
        if self.snow:
            cave.install_snow(self.snow, run)
        (run/'p2-cave-entry.txt').write_text(cave.entry_text(checkpoint, token))
        (run/'p2-economy.txt').write_text(cave.ledger_text(checkpoint['receipts']))
        if self.anchors:
            (run/'p2-cave-transition.txt').write_bytes(self.anchors[floor])
        install_visuals(self.visuals, run, floor)
        return run, cave.allowed_receipts(run, floor)


class SurfaceRunner:
    """Injected content.stage and process permit host tests without game assets.

    pending-handoff.json is a replayable command, never a second checkpoint.
    SurfaceLedger alone validates and commits party, health, and receipts.
    """
    def __init__(self, ledger, content, exe, process=subprocess.run):
        self.ledger, self.content = ledger, content
        self.exe, self.process = str(Path(exe).resolve()), process
        self.pending = ledger.directory/'pending-handoff.json'

    def _consume_pending(self):
        request = json.loads(self.pending.read_text(encoding='utf-8'))
        if set(request) != {'campaign', 'content', 'revision', 'token', 'text', 'receipts', 'allowed'}:
            raise ValueError('Invalid pending handoff')
        if request['campaign'] != self.ledger.campaign or request['content'] != self.ledger.content:
            raise ValueError('Pending handoff belongs to another campaign/content')
        state = self.ledger.apply_floor(request['revision'], request['token'], request['text'],
                                        request['receipts'], request['allowed'])
        self.pending.unlink()
        return state

    def resume(self, *, return_to_surface=True):
        # Read before creating auxiliary files: never initialize a missing save.
        self.ledger.read()
        if self.content.identity != self.ledger.content:
            raise ValueError('Cave content changed; retain the original bundle')
        with SessionLock(self.ledger.directory/'native-runner-lease'):
            state = self._consume_pending() if self.pending.exists() else self.ledger.read()
            while state['phase'] == 'cave':
                trip = state['trip']
                run, allowed = self.content.stage(trip['checkpoint'], trip['token'], self.ledger.directory/'runs')
                with (run/'native.log').open('w') as log:
                    result = self.process([self.exe, '--experimental-pikmin2-room'], cwd=run,
                                          stdout=log, stderr=subprocess.STDOUT)
                if result.returncode != cave.EXIT_TRANSITION:
                    if result.returncode:
                        raise RuntimeError(f'Native exit {result.returncode}; entry preserved; see {run / "native.log"}')
                    return self.ledger.read()
                request = dict(campaign=self.ledger.campaign, content=self.ledger.content,
                               revision=state['revision'], token=trip['token'],
                               text=(run/'p2-cave-transfer.txt').read_text(),
                               receipts=cave.read_ledger(run/'p2-economy.txt'), allowed=allowed)
                # Validate before preserving a command so malformed output cannot poison retries.
                cave.transition(trip['checkpoint'], trip['token'], request['text'], request['receipts'], allowed)
                atomic_write(self.pending, json.dumps(request, indent=2))
                state = self._consume_pending()
            if state['phase'] == 'return_ready' and return_to_surface:
                state = self.ledger.return_to_surface(state['revision'], state['trip']['id'])
            return state
