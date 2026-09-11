"""Audited campaign species sources and the native families-v1 permutation.

Rows aggregate retail v10 generators by area/species/protection. first_day is
campaign day (1-based); later sources assume the player can advance days.
Protected means personality pellet ID != none or Parameter0 != 0, exactly as
GenObjectTeki::birth. No positions, assets or native runtime state are included.
"""
FAMILY_PAIRS = ((3, 31), (4, 32), (18, 19))
SOURCE_VERSION = 'family-sources-v1'
# stage, original type, protected, earliest campaign day
CAMPAIGN_SOURCES = (
    (0, 10, False, 2),
    (0, 10, True, 1),
    (0, 24, False, 8),
    (1, 3, False, 1),
    (1, 3, True, 1),
    (1, 4, False, 1),
    (1, 11, False, 15),
    (1, 17, False, 1),
    (1, 18, False, 1),
    (1, 19, False, 1),
    (1, 25, False, 1),
    (2, 8, True, 1),
    (2, 9, True, 1),
    (2, 15, False, 1),
    (2, 19, True, 1),
    (2, 20, True, 1),
    (2, 33, False, 1),
    (3, 0, False, 1),
    (3, 0, True, 1),
    (3, 11, False, 5),
    (3, 16, False, 1),
    (3, 16, True, 1),
    (3, 17, True, 1),
    (3, 20, False, 1),
    (3, 25, False, 16),
    (3, 30, False, 1),
    (3, 31, False, 16),
    (3, 32, False, 1),
)


def enemy_type(original, mask, protected=False):
    if not protected:
        for bit, (a, b) in enumerate(FAMILY_PAIRS):
            if mask & (1 << bit):
                if original == a: return b
                if original == b: return a
    return original


def resolve_layout(mask):
    return {'version': SOURCE_VERSION, 'sources': [
        {'stage': stage, 'original': original, 'actual': enemy_type(original, mask, protected),
         'protected': protected, 'first_day': day}
        for stage, original, protected, day in CAMPAIGN_SOURCES]}


def sources_for(layout, species):
    # Clamclamp shell creates the collectable pearl; it is not a separate spawn.
    supplier = 10 if species == 13 else species
    # Do not credit the protected ship-part Clamclamp as a guaranteed pearl.
    return [row for row in layout['sources'] if row['actual'] == supplier
            and (species != 13 or not row['protected'])]
