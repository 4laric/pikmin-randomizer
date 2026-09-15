# Violet same-color capacity refund (#279)

Owner: Codex using shared 4laric account. The Violet proxy now counts only
non-Purple inputs against its five conversion slots. Previously a Purple input
produced a replacement Purple sprout but also spent a slot, leaving only four
Red conversions available afterward.

Source evidence: the read-only P2 research `Pom.cpp`, `Obj::shotPikmin`, lines
297–299, decrements used slots for a same-color input to a non-Queen flower.
The audited file SHA256 is
`dc160e17dd2f9b19bd2a3309198ccda7641014d9b98056c0d79eba08dc566ebc`.
The normal slot budget is five as documented in the Beasts lifecycle audit.

`pc_p2_convert_violet` now distinguishes replacements from slots used. It
returns slots used to `PomAi`, while retaining replacement counts in diagnostic
logs. Purple replacements consume no slot. Allocation still occurs before
input consumption, and rejected/failed allocations spend no slot. The ordinary
P1 path retains its existing sentinel and behavior.

The opt-in `--refund` runtime fixture marks one of its twenty engineering
starting Pikmin Purple, giving nineteen Reds and one Purple. It throws that
Purple into generator 62000 and waits for its replacement sprout before throwing
five Reds into the same flower. Five further Reds go to generator 62001. Native
throws, conversion, sprout creation and plucking remain exercised by the
scripted driver. This is not manual-play acceptance.

The host requires eleven ordered witnesses: one Purple and five Reds from the
first flower, then five Reds from the second. It verifies the Purple-only cycle
precedes Red throws, original input deaths, six/five replacement counts and the
final nine Reds/eleven Purples. No population multiplication occurs.

Native candidate: `b02f6261a1135f37ddad5d40c22ac67516095fea` (gameplay fix
`483735721ce2dc2203dc262b8afa35c347b7770f`). Private Release production build
passed. The first fixture compile exposed a missing stream include, fixed in
the final candidate. Final fixture build reports no pending build work before
and after linking. Executable SHA256:
`dff949b56a970c98ad990530c11c783ff174a431ccf023f3b94d393a6784ef29`.

Mixed-input run:
`output/beasts279-final/refund/7984ea81f1ff40d0a00a2c89081c4083/acceptance.json`.
Passed with replacement batches 1, 4, 1, 5; a missed Red throw was retried through
the ordinary fixture controller. Eleven witnesses confirmed five Red uses on
each flower. Final nine Reds/eleven Purples, zero cargo/Pokos, unchanged repairs
and unchanged input/executable hashes. Log SHA256:
`fa4b1b3ebd2d40c0ef52cde2e44526df3fe08a8b1dade4905608ae64513a1d3a`.
The completed log also passed the final stricter cycle-order validator.

Ordinary twenty-Red regression:
`output/beasts279-final/ordinary/e37e898769af4b75981585ca74e3eadf/acceptance.json`.
Passed with ten Red-input witnesses and ten Reds/ten Purples, zero cargo/Pokos,
unchanged repairs and input/executable hashes. Log SHA256:
`82de8f4b6a92542313b18156209cbca6a3f183822cfb97a6054d2f06de812260`.

```powershell
python -m experimental.pikmin2_beasts_floor2_runtime --root ../.. --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets --exe output/beasts279-final/linked/fixture.exe --output output/beasts279-repeat --global-purple-count 19 --refund
```

Omit `--refund` for the ordinary twenty-Red regression. The declared generation
count must include the fixture's incoming Purple and remain below twenty for
the refund scenario. Global storage collection is not implemented here.

Focused validation: 38 tests and 83 subtests passed across the runtime,
generation, checkpoint/lifecycle references and fixture builder. Full P2 Pom
FSM parity, repeated same-color cycles, allocation-pressure runtime testing,
authenticated conversion identities and persistent campaign resume remain open.
