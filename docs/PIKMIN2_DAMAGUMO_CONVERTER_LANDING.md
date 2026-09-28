# Damagumo converter artifact landing (#685)

Lane damagumo-converter-artifact-landing, issue #685. Lands the committed #670
converter artifacts (955be0ec, 1848a8ee) for consumer #173 via handoff plus
integration-ready packet. Tooling only: no family/shared edits, no runtime,
no ADMIT. All six runtime gates UNTESTED.

## Re-verified pins

Re-ran the committed #670 CLI against the real ISO bytes; all three hashes
reproduce exactly:

- damagumo-family.json f9ec5030890d72fba0c890b41407aa8788b6fac53223dd62f231a3259f68ef94
- Demon/enemy.bmd 8fc0ac7fd6c7585113cf10da12ecd7faccf807896d2d642ab0f80019fff2a961
- damagumo-slot-312004.json 61019a39bf255442e49cd5d03db6f16581ab5370ab401a346341f8d077c4e37c

On-disk JSON carries CRLF from write_text; pins are LF-canonical hashes, so the
landing adapter hashes the CRLF-normalized form and records both digests.

## Contract and interface

#678 hash gate: slot 312004, enemy 56, 15 joints, 4 textures, animation rows
with maxima landing 69 / wait 75 / flick 69, profile/mesh/slot prefixes.
#638 arena staging interface: arena_binding "312004 Damagumo",
source 56, slot schema 1.

## Adapter, tests and packet

experimental/pikmin2_damagumo_converter_landing.py verifies pins, checks
contract and interface fail-closed, and emits the packet (build_packet CLI).
tests/test_pikmin2_damagumo_converter_landing.py: 8 focused tests (pins,
hash/CRLF handling, missing/mismatch rejection, contract and interface
drift, missing-file packet refusal).

Downstream consumer #173 gates 1-4/6. Integrator lands the packet; never
merge tooling history into content lines.

