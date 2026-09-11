# Bomb placement warning regression (#74)

On PC, InteractWarn ignores Pikmin with hasBomb(). ActPutBomb::warnPikis is its only current sender. This prevents another planter from interrupting a carrier and returning it to formation before deployment. Ordinary eligible Pikmin retain their warning reaction. Real explosion damage and player whistle paths are unchanged; non-PC behavior remains original.

Build a completed Windows game, then run tools/verify_bomb_warning_windows.py --build BUILD --output FIXTURE. From the randomizer root run scripts/test_bomb_warning_native.py --exe FIXTURE/preview_bomb_warning.exe --assets ASSETS --output PRIVATE_SESSION.

The fixture dispatches the actual ActPutBomb warning to four live Pikmin and checks multiple held-bomb predicates, ordinary LookAt reaction, pending-recall suppression and reaction after releasing the held predicate. It uses temporary held-creature sentinels synchronously and never ticks them as real bombs. This validates the warning state path, not a full bomb/wall deployment or blast simulation. The unmodified runtime fails with "warning interrupted a bomb carrier".
