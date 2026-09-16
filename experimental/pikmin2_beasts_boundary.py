"""Boundary correlation for native diagnostics, not cryptographic attestation."""
import re


def boundary_text(token):
    if not isinstance(token,str) or not re.fullmatch('[0-9a-f]{64}',token):raise ValueError('Invalid Beasts boundary token')
    return f'P2_BEASTS_BOUNDARY_1\n{token}\n'


def validate_boundary(log,token):
    boundary_text(token)
    lines=log.splitlines()
    begin=f'P2_BEASTS_BOUNDARY_BEGIN token={token}'
    end=f'P2_BEASTS_BOUNDARY_END token={token}'
    markers=[line for line in lines if line.startswith('P2_BEASTS_BOUNDARY')]
    if markers!=[begin,end]:raise ValueError('Native boundary markers differ')
    first,last=lines.index(begin),lines.index(end)
    evidence=[i for i,line in enumerate(lines) if line.startswith(('P2_BEASTS_READY ','P2_BEASTS_PARTY ',
              'P2_BEASTS_PARTY_END','P2_BEASTS_SURVIVOR','P2_VIOLET_WITNESS','P2_VIOLET_CONVERT'))]
    passed=[i for i,line in enumerate(lines) if line.startswith('PASS P2_BEASTS_')]
    if not evidence or not all(first<i<last for i in evidence) or len(passed)!=1 or passed[0]<=last:
        raise ValueError('Native evidence outside boundary markers')
