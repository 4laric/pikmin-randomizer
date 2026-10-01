# Complete external state for online co-op (#1148)

Owner: Codex through shared account4laric. Work is isolated in the issue1148 private root/native lane. Current implementation and tests are candidates; paired gameplay and complete acceptance remain pending.

The native session uses protocol4 and randomizer codec3. The16-byte input record and252-byte Hello layout remain stable, so earlier protocol versions can be refused from the header. Seeds, P1/TheLynk file protocols, campaign formats and durable kill/corpse journal aliases retain their existing identities.

The168-byte little-endian snapshot carries512 check bits, bootstrap mode/schema/features/check count, ordinary progression,12 stat tiers,9 uint16 benefit counts,3 maturity tiers, day-length and whistle-pluck receipts, uint32 DeathLink count, TheLynk30 part bits and18 uint16 typed bonus counts. Generation is at160 and CRC32 at164. Reserved bytes are zero. Forty-two four-byte fragments use the existing spare input bytes with a six-bit index; the first application barrier is frame64. Incoming inventory is parsed completely and checked against the authenticated bootstrap before applying simulation changes.

Consumption, Purple/White ship stock and agreed campaign generation stay simulation/checkpoint state rather than overwritable receipt inventory. The simulation hash includes these quantities separately. Host filesystem stamps, journals, tokens and paths do not enter the simulation hash.

The real Python mirror consumer is imported additively from the historical7c8fda70eb507f520661a3cb6b5a18c36449e676 source. The current naming-crosswalk command remains present. Tracker and overlay resolve a host session first, then a client mirror. TheLynk uses its original patch fingerprint, hello/state protocols, external numeric location IDs and typed reward inventory.

Native ICE launch defaults remain local. Explicit --netplay-external-state chooses Python/AP authority; --netplay-run-root selects a private writable run base. The native launcher creates and stamps the bootstrap, token, assets and checkpoint. Python --attach-native-run attaches to that existing session/runs/token directory, checks its identity and does not launch or terminate the native process or overwrite its bootstrap. Host attachment uses the native session root as --session-dir; client attachment never contacts AP.

Validation so far:12 existing Python mirror tests,2 new TheLynk/attachment tests and12 packaged compatibility fills passed. Native codec/consumer tests, production compilation, old-peer refusal and real paired AP/P2/TheLynk gameplay are not yet validated for this candidate. Test-only state/receipt injection in unit tests is distinct from ordinary gameplay acceptance.

All eight issue1148 criteria remain the final acceptance contract. Human game feel, physical manual reset and full campaign completion are unverified.
