"""Shared single-species staging core for the batch-2 ground sidecars.

Several campaign-identity species share the two ground text-bank slots the
native setups open directly:

* ``p2-ground-actors.txt`` (``P2_GROUND_ACTORS_1`` + ``<generator> <Species>``
  rows; parsed by ``engine/pc_port/pc_p2_batch2.cpp:122-138`` ``parseActors``
  and filtered per species by ``pc_p2_sokkuri.cpp`` /
  ``pc_p2_elecbug.cpp:495-501`` / ``pc_p2_tamago.cpp:413-419``), and
* ``p2-ground-bank.txt`` (``P2_GROUND_BANK_1`` + ``species`` / ``clip`` rows;
  parsed by ``engine/pc_port/pc_p2_batch2.cpp:140-170`` ``parseBank`` with
  event tokens in the ``engine/pc_port/pc_p2_batch2_clock.h:102-136``
  ``parseEvents`` shape, and filtered per species by ``pc_p2_sokkuri.cpp`` /
  ``pc_p2_elecbug.cpp:460-494`` / ``pc_p2_tamago.cpp:378-412``).

The legacy shared installer (``experimental.pikmin2_ground_inverts_install``)
owns these files all-or-nothing and refuses a second install, so two identity
species bound in one seed (e.g. Sokkuri + ElecBug) could never stage together.
This module lets each identity species stage ONLY its own rows and MERGE them
with rows other ground-identity species already staged:

* actor rows merge as an order-preserving union keyed by generator id; a
  generator bound to two different species refuses fail-closed;
* bank species blocks merge in the canonical family order
  (``Armor, ElecBug, Imomushi, TamagoMushi, Sokkuri, Hana`` per
  ``experimental.pikmin2_batch2_families.GROUND``); a restaged own-species
  block must be byte-identical to what is already there, otherwise the run is
  refused before any write.

Every writer renders the canonical
``experimental.pikmin2_batch2_core.bank_text`` / ``actors_text`` shape, so a
merged file re-renders byte-identically no matter how many species stage, in
any order. A malformed pre-existing file is refused, never repaired. Mesh
files (``ginv_<Species>_<clip>_%02d.mod``) keep the strict rule: byte-identical
is a no-op, anything else refuses.
"""
from experimental.pikmin2_staging import StagingError

ACTORS_TXT = 'p2-ground-actors.txt'
BANK_TXT = 'p2-ground-bank.txt'
ACTORS_HEADER = 'P2_GROUND_ACTORS_1'
BANK_HEADER = 'P2_GROUND_BANK_1'

# Canonical family order (experimental.pikmin2_batch2_families.GROUND); merged
# bank blocks follow it so the bytes are independent of staging order.
GROUND_SPECIES_ORDER = ('Armor', 'ElecBug', 'Imomushi', 'TamagoMushi', 'Sokkuri', 'Hana')
GROUND_SPECIES_IDS = {'Armor': 15, 'ElecBug': 28, 'Imomushi': 65,
                      'TamagoMushi': 68, 'Sokkuri': 79, 'Hana': 84}

# Native bank clip-row budget (pc_p2_batch2.cpp:152-155): poses in 0..64.
MAX_BANK_POSES = 64
# Native actor-row budget (pc_p2_batch2.cpp:122-138): 1..100 rows.
MAX_ACTORS = 100


def _check_events_token(token):
    """Mirror ``parseEvents`` (pc_p2_batch2_clock.h:102-136) for one token."""
    if token == '-':
        return
    for item in token.split(','):
        head, sep, _tail = item.partition(':')
        if not sep or not head or not head.isascii() or not head.isdigit():
            raise StagingError(f'ground bank event token rejected by the native grammar: {token!r}')
        if int(head) > 100000:
            raise StagingError(f'ground bank event frame outside the native range: {token!r}')


def parse_actors(data):
    """Parse staged actors bytes to ``[(generator, species)]``; fail closed.

    Strict mirror of ``parseActors`` (pc_p2_batch2.cpp:122-138): exact
    ``P2_GROUND_ACTORS_1`` header, 1..100 ``<uint32 generator> <species>``
    rows, unique generators, no trailing data.
    """
    try:
        text = data.decode('ascii')
    except (UnicodeDecodeError, AttributeError) as error:
        raise StagingError('ground actors sidecar is not ASCII') from error
    tokens = text.split()
    if len(tokens) < 2 or tokens[0] != ACTORS_HEADER:
        raise StagingError('ground actors sidecar header mismatch')
    try:
        count = int(tokens[1])
    except ValueError as error:
        raise StagingError('ground actors sidecar count is not an int') from error
    if count < 1 or count > MAX_ACTORS or len(tokens) != 2 + 2 * count:
        raise StagingError('ground actors sidecar row count mismatch')
    rows, seen = [], set()
    for index in range(2, len(tokens), 2):
        try:
            generator = int(tokens[index])
        except ValueError as error:
            raise StagingError('ground actors sidecar generator is not an int') from error
        species = tokens[index + 1]
        if not 0 < generator <= 0xFFFFFFFF or generator in seen:
            raise StagingError('ground actors sidecar generator out of native range')
        if not species or species not in GROUND_SPECIES_IDS:
            raise StagingError(f'ground actors sidecar names no ground species: {species!r}')
        seen.add(generator)
        rows.append((generator, species))
    return rows


def render_actors(rows):
    """Render actor rows in the canonical ``actors_text`` shape."""
    lines = [ACTORS_HEADER, str(len(rows))]
    lines.extend(f'{generator} {species}' for generator, species in rows)
    return ('\n'.join(lines) + '\n').encode('ascii')


def merge_actors(existing, species, generators):
    """Merge one species' generator rows into staged actors bytes.

    ``existing`` is the current file bytes or ``None``; returns the merged
    payload. Order-preserving union: pre-existing rows keep their order, new
    rows append. A generator already bound to a different species refuses.
    """
    for generator in generators:
        if type(generator) is not int or not 0 < generator <= 0xFFFFFFFF:
            raise StagingError(f'ground actor generator out of native range: {generator!r}')
    if len(set(generators)) != len(generators):
        raise StagingError('ground actor generators are not unique')
    rows = parse_actors(existing) if existing is not None else []
    bound = dict(rows)
    for generator in generators:
        if generator in bound and bound[generator] != species:
            raise StagingError(
                f'ground actor generator {generator} already bound to {bound[generator]!r}')
        if generator not in bound:
            rows.append((generator, species))
    if not rows:
        raise StagingError('ground install requires at least one generator')
    if len(rows) > MAX_ACTORS:
        raise StagingError('ground actors exceed the native budget')
    return render_actors(rows)


def parse_bank(data):
    """Parse staged bank bytes to ``[(species, id, [(name, frames, events, poses, status)])``].

    Strict mirror of ``parseBank`` (pc_p2_batch2.cpp:140-170): exact
    ``P2_GROUND_BANK_1`` header, ``species <Species> <id>`` rows before
    ``clip <Species> <name> <frames> <events> poses <poses> <status>`` rows
    with 0..64 poses. Returns blocks in file order.
    """
    try:
        text = data.decode('ascii')
    except (UnicodeDecodeError, AttributeError) as error:
        raise StagingError('ground bank sidecar is not ASCII') from error
    tokens = text.split()
    if not tokens or tokens[0] != BANK_HEADER:
        raise StagingError('ground bank sidecar header mismatch')
    blocks, current, pos = [], None, 1
    while pos < len(tokens):
        word = tokens[pos]
        if word == 'species':
            if pos + 2 >= len(tokens):
                raise StagingError('ground bank species row truncated')
            species, enemy_id = tokens[pos + 1], tokens[pos + 2]
            if species not in GROUND_SPECIES_IDS or enemy_id != str(GROUND_SPECIES_IDS[species]):
                raise StagingError(f'ground bank species row mismatch: {species} {enemy_id}')
            if any(species == name for name, _, _ in blocks):
                raise StagingError(f'ground bank species block duplicated: {species}')
            blocks.append((species, enemy_id, []))
            current = blocks[-1][2]
            pos += 3
        elif word == 'clip':
            if current is None or pos + 7 >= len(tokens):
                raise StagingError('ground bank clip row misplaced or truncated')
            _species, name = tokens[pos + 1], tokens[pos + 2]
            try:
                frames, poses = int(tokens[pos + 3]), int(tokens[pos + 6])
            except ValueError as error:
                raise StagingError('ground bank clip row frames/poses not ints') from error
            events, marker, status = tokens[pos + 4], tokens[pos + 5], tokens[pos + 7]
            if marker != 'poses' or poses < 0 or poses > MAX_BANK_POSES or frames < 0:
                raise StagingError(f'ground bank clip row outside the native range: {name!r}')
            _check_events_token(events)
            if not name or not status:
                raise StagingError('ground bank clip row names no clip')
            current.append((name, frames, events, poses, status))
            pos += 8
        else:
            raise StagingError(f'ground bank token rejected by the native grammar: {word!r}')
    return blocks


def render_bank(blocks):
    """Render bank blocks in the canonical ``bank_text`` shape."""
    lines = [BANK_HEADER]
    for species, enemy_id, clips in blocks:
        lines.append(f'species {species} {enemy_id}')
        for name, frames, events, poses, status in clips:
            lines.append(f'clip {species} {name} {frames} {events} poses {poses} {status}')
    return ('\n'.join(lines) + '\n').encode('ascii')


def merge_bank(existing, species, source_id, clip_rows):
    """Merge one species' bank block into staged bank bytes.

    ``clip_rows`` is the species' ``[(name, frames, events, poses, status)]``
    in manifest order; returns the merged payload with blocks in canonical
    family order. A restaged own-species block must equal what is already
    there, otherwise the run refuses.
    """
    if species not in GROUND_SPECIES_IDS or source_id != GROUND_SPECIES_IDS[species]:
        raise StagingError(f'ground bank species identity mismatch: {species} {source_id}')
    for _name, frames, events, poses, status in clip_rows:
        if type(frames) is not int or frames < 0:
            raise StagingError(f'ground bank clip frames outside the native range: {_name!r}')
        if type(poses) is not int or poses < 0 or poses > MAX_BANK_POSES:
            raise StagingError(f'ground bank clip poses outside the native range: {_name!r}')
        if not status:
            raise StagingError(f'ground bank clip row names no status: {_name!r}')
        _check_events_token(events)
    blocks = parse_bank(existing) if existing is not None else []
    own = (species, str(source_id), list(clip_rows))
    for index, (name, _id, _clips) in enumerate(blocks):
        if name == species:
            if (name, _id, _clips) != own:
                raise StagingError(
                    f'Refusing conflicting ground bank block for {species}')
            break
    else:
        blocks.append(own)
    blocks.sort(key=lambda block: GROUND_SPECIES_ORDER.index(block[0]))
    return render_bank(blocks)
