# Snow Day campaign playtest (#342)

Codex implementation owner, shared GitHub account 4laric.

Local launcher: `C:/Users/alari/pikmin-randomizer/output/pikipelago-snow-day-01/Play.cmd`.
The package contains a frozen Python adapter, production executable and resolved
DLL closure. Its private asset overlay references this computer's extracted P1
assets and contains the locally imported Snow models. It is not redistributable.
The player's session is fresh; acceptance runs use separate disposable sessions.

Seed `pikipelago-snow-day-01`: Forest of Hope, red, field cap 10, normal initial
stats, 36 progressive stat upgrades, 30 repair items / 25 required, Emperor
finale. There are 105 checks and five conservative progression spheres. Normal
enemy placement is retained. The manifest fingerprint is
`0714ce446b75fb8dc70bf0200d0fedb64ab715ad2403527c275e84e420b18c7c`.

`scripts.prepare_snow_campaign` reproduces the package from explicit asset,
Snow-bank, executable, DLL-root and objdump paths into a fresh output directory.
It never rewrites an existing seed or source asset. Imported files remain local.

## Runtime contract

`assets/p2-snow-all-dwarfs.txt` with `P2_SNOW_ALL_DWARFS_1` opts a normal campaign
into Snow rendering. The bank and interpolation configs are also read from the
private assets root. Room previews retain their existing run-local configuration
and selected-generator behavior. Combining both modes is rejected.

Normal final setup loads the compatible bank on the application heap, registers
all native `TEKI_Chappy` instances and requires no P2 Pod. Later `newTeki` births
register after native type initialization. Slot reuse revokes the previous
binding first; manager reset revokes the bank and campaign mode. Private model
allocation occurs at registration, never on every draw.

This is a visual replacement: native health, behavior, collision, carrying,
pellet value and Dwarf Bulborb bestiary identity stay intact. Campaign mode does
not read the optional preview health/attack/turn/chase policy files. Other enemy
types are not replaced. Animation uses the previously validated interpolation
path and P1 event clock.

## Evidence

Native commit `3a34693fa594daca0424e64dbf22de1b6528466f`; production build passed.
Packaged production executable SHA-256:
`03b5e8a2f665e1562ac9863c98ad3e1f0b01a13eb18249f90e3bfad706a881f3`.

Production boot and adapter handshake passed in all five normal areas. Initial
Dwarf counts were Forest of Hope 11, Navel 0, Impact 0, Spring 0 and Trial 0;
zero-Dwarf areas load safely and remain ready for later eligible births. A separate
native fixture verified 11 initial Dwarfs registered and 49 other enemies
unchanged, late birth registration, release/reuse as a non-Dwarf, actual live
interpolated geometry (226 positions), reset/rebinding and no Pod. Fixture
SHA-256: `2c4cc389adb66805557d3af6a93920f6aaa22e8859b77918e5e445219c975986`.
Its exit was 0; production smoke processes were deliberately stopped after boot.
Source: `scripts/snow_campaign_fixture.cpp`; host:
`scripts/test_snow_campaign_smoke.py`. Evidence under local `output/snow342`.
Focused regressions passed: 17 tests and 45 subtests.

The real combat/corpse/Pod interpolation acceptance from #327 remains separate
from this normal-area smoke test. Full campaign travel, native Onion delivery
and day-end save/reload with this opt-in remain player acceptance items; no
new save protocol or checkpoint format is introduced.
