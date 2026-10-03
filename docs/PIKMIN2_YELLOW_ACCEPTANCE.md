# Yellow field acceptance (#1263)

Implementation owner: Codex through the shared GitHub account `4laric`.
Native change: [PR 172](https://github.com/4laric/Open-Nectar---Pikmin-Native-PC-Port/pull/172),
trajectory commit `63a72cec7f8c21515bfe6e89e210af1cd48c47e2`, followed by
factory-capacity correction at `745ce74925936005a789257400761000deed6443`.

## Bounded trajectory check

The registered fixture `pikmin_ci_fixture_original_yellow_throw` explicitly
replaces one baseline Red with a source-authorized debug Yellow before controller
play starts. It retains 20 live Pikmin, a centered 960x540 window, and the
captain-down guard immediately after each engine idle. It then gathers, selects,
throws, and observes the actual Flying-to-ground landing using ordinary virtual
controller input. The measured phase does not write actor position, velocity or
state.

The assertion checks the original retail Yellow launch impulse and apex, actual
ground contact, and population conservation. Its result is **staged trajectory
evidence only**. It does not establish original acquisition, electric immunity,
an elevated receiver, campaign progression, or save/resume.

After downloading the executable and its dependencies from the exact source
build, use its independently verified SHA-256:

```powershell
py -3.12 scripts/run_pikmin2_yellow_throw.py --exe <fixture.exe> --expected-exe-sha256 <sha256>
py -3.12 scripts/run_pikmin2_yellow_throw.py --exe <fixture.exe> --expected-exe-sha256 <sha256> --captain-down
```

Each invocation stages a fresh private scene under ignored `output/p2-yellow-1263`,
uses private settings and saves, clears inherited game overrides, and supervises
only its own child for at most 60 seconds. The negative must stop with exit 86,
the captain-down marker, and no PASS marker. The launcher emits the evidence path.

## Original acquisition and human acceptance

The original Perplexing Pool (`yakushima`) wild Yellow records are
`defaultgen.txt#5..9`, around X=-1140, Z=-1330, at their authored elevated tree
positions. The initial Yellow Onion is around (-1100,89,-950). Debug Yellow
`initgen.txt#3` and Golden Candypop outputs must not substitute for these records.
Source GenPiki deliberately disables random horizontal offsets for wild Yellow.
For the diagnostic acquisition fixture, retain the starting 20 Reds before
actual source attempts. The five authored wild Yellow births then yield 25
field actors; do not reduce the baseline or delete source bodies to force the
staged trajectory fixture's constant population. A whole original session
must use its actual source calendar and is a separate qualification.

The following 30–90 second script is for a qualified playable source scene;
the course owner must first supply its launch command and safe approach route:

1. Approach the five authored wild Yellow bodies and whistle them into the party.
   Record the source identities, Yellow count, and actual recruitment event.
2. Select a recruited Yellow with ordinary controls. Throw onto the specified
   elevated receiver; observe the landing and receiver interaction.
3. Approach the specified live electric emitter. Observe the same Yellow survive
   its real discharge, with a separately staged vulnerable Red control.
4. Use the actual save interaction, quit, and resume in a fresh process. Confirm
   Yellow recruitment/container progression and the preserved party, then repeat
   the throw and electric interaction.

This script remains unqualified until the source scene, receiver, emitter and
save transport are actually exercised. Source review, unit tests, build success,
and synthetic flags cannot supply those results.

## Bounded electric contact check

[Native PR 178](https://github.com/4laric/Open-Nectar---Pikmin-Native-PC-Port/pull/178)
adds explicitly staged Yellow and separate synthetic Red control modes to the
existing ElecBug contact fixture. Each replaces one of the 20 baseline Reds
near the captain before the encounter; the Red control still has 20 Reds.
The engineered pair's natural discharge and ordinary throw must dispatch the
actual electric receiver for the exact staged Yellow. The witness requires its
rejection without changing Flying state, followed by actual grounded survival
and 20 living Pikmin. Held, flying, drowning and death states cannot qualify
the final survivor. Run a separate fresh vulnerable Red control:

```powershell
py -3.12 scripts/run_pikmin2_yellow_electric.py --exe <contact-fixture.exe> --expected-exe-sha256 <sha256> --content <private-ElecBug-bank> --mode yellow-electric
py -3.12 scripts/run_pikmin2_yellow_electric.py --exe <contact-fixture.exe> --expected-exe-sha256 <sha256> --content <private-ElecBug-bank> --mode red-electric
py -3.12 scripts/run_pikmin2_yellow_electric.py --exe <contact-fixture.exe> --expected-exe-sha256 <sha256> --content <private-ElecBug-bank> --captain-down
```

Each launch is hash checked, privately staged and supervised for at most 60
seconds. A process candidate marker alone cannot pass: the launcher correlates
the exact actor through the actual receiver/contact/recovery log sequence.
The Red control establishes an accepted DenkiDying reaction, not final death.
Its distinct synthetic catalog identity is disclosed and must match the exact
held, thrown and electrocuted pointer; it cannot claim an original Red birth.
Neither run establishes original acquisition, source campaign placement, or
save/resume. The Linux staged Yellow run passed the exact receiver and grounded
survival witness in 36.092 seconds at native `e0a1fabe1`, with 20 living Pikmin.
The separate Red contact control remains unqualified; its failed runs are
preserved. The latest Windows build and original-scene gameplay remain pending.
