"""Strict bounded cave wire adapter derived from native species/schema headers.

Native wire1 includes Purple3; wire2 adds White4. Bulbmin/schema3 and tutorial
ENTRY4 admission are intentionally outside this two-floor adapter.
"""
import math
import re

MAX_SPECIES = {1: 3, 2: 4}
INTEGER = re.compile(r'[+-]?[0-9]+\Z')
NUMBER = re.compile(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z')


def validate_party(squad, health, schema):
    if type(schema) is not int or schema not in MAX_SPECIES:
        raise ValueError('unsupported bounded cave wire schema')
    if (type(health) not in (int, float) or not math.isfinite(health)
            or not 0 < health <= 1 or type(squad) not in (list, tuple)
            or not 1 <= len(squad) <= 100):
        raise ValueError('invalid cave health or survivor count')
    for row in squad:
        if (type(row) not in (list, tuple) or len(row) != 2
                or any(type(value) is not int for value in row)
                or not 0 <= row[0] <= MAX_SPECIES[schema] or not 0 <= row[1] <= 2):
            raise ValueError('species/maturity incompatible with cave wire')


def wire_schema(party):
    # Retain native wire2 capability even if its White population becomes zero.
    validate_party(party['squad'], party['health'], 2)
    schema = party.get('wire_schema', 2 if any(row[0] == 4 for row in party['squad']) else 1)
    validate_party(party['squad'], party['health'], schema)
    return schema


def identity(token, floor):
    if (not isinstance(token, str) or not re.fullmatch('[0-9a-f]{32}', token)
            or type(floor) is not int or floor not in (1, 2)):
        raise ValueError('invalid bounded cave identity')


def entry_text(token, floor, party):
    identity(token, floor); schema = wire_schema(party)
    return (f"P2_CAVE_ENTRY_{schema} {token} {floor} {party['health']} {len(party['squad'])}\n"
            + ''.join(f'{species} {maturity}\n' for species, maturity in party['squad']))


def transfer_text(token, floor, party):
    identity(token, floor); schema = wire_schema(party)
    return (f"P2_CAVE_TRANSFER_{schema}\n{token}\n{floor} {party['health']} {len(party['squad'])}\n"
            + ''.join(f'{species} {maturity}\n' for species, maturity in party['squad']))


def read_transfer(text, token, floor):
    identity(token, floor); words = text.split()
    if (len(words) < 5 or words[0] not in ('P2_CAVE_TRANSFER_1', 'P2_CAVE_TRANSFER_2')
            or words[1] != token or words[2] != str(floor)
            or not NUMBER.fullmatch(words[3]) or not INTEGER.fullmatch(words[4])):
        raise ValueError('foreign or unsupported cave transfer')
    schema = int(words[0][-1]); health = float(words[3]); count = int(words[4])
    if not 1 <= count <= 100 or len(words) != 5 + count * 2:
        raise ValueError('cave failed or invalid squad; refusing fresh starter reset')
    if any(not INTEGER.fullmatch(word) for word in words[5:]):
        raise ValueError('invalid native survivor integer')
    squad = [[int(words[i]), int(words[i + 1])] for i in range(5, len(words), 2)]
    validate_party(squad, health, schema)
    return dict(health=health, squad=squad, **({'wire_schema': schema} if schema != 1 else {}))
