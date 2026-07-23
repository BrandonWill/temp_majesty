# IceSpell Mod — TODO

## Ready (needs game machine)

- [ ] **Compile GPL** — Run `cmd /c MakeGPL.bat` in both `IceSpell/` and `IceSpell_Quest/`
- [ ] **Test in-game** — Load IceSpell_Quest, verify:
  - Projectile travels from Ice Elemental to target
  - Freeze overlay is visible (animated shimmer, 48×64)
  - Thaw burst plays on unfreeze (32×32 shard explosion)
  - Cold stack accumulation works (5 hits to freeze)
  - DOT ticks during freeze
  - Immunity window prevents re-freeze for 5 seconds

## If art needs iteration

- Freeze overlay: increase pixel density or brightness if too subtle in-game
- Projectile: increase to 24×24 if too small to see at game zoom level
- Impact: consider playing on hit (before freeze) as well as on thaw
- Rebuild CAM with `python utility/build_ice_barrage_cam.py`

## Future enhancements

- [ ] Add sound effects (impact + freeze crackle + thaw shatter)
- [ ] Particle system for ambient frost dust while frozen
- [ ] Screen shake or flash on barrage hit (if engine supports)
- [ ] Balance pass: adjust stack count, duration, damage per game testing
