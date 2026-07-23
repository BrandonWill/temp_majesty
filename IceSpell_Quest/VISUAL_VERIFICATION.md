# Ice Barrage — Visual Verification Checklist

## Current Build (July 2026)

**Architecture:** Cast → Projectile → Hit → Cold Stacks → Freeze + DOT → Thaw

**Assets in Quest_maindata.cam (15 KB):**
| ID | Name | Frames | Size | Purpose |
|----|------|--------|------|---------|
| IR01 | freeze_effector | 8 | 48×64 | Animated ice shimmer overlay on frozen unit |
| IR02 | freeze_icon | 1 | 1×1 | Invisible timer (calls Ice_Freeze_End) |
| IR03 | thaw_effector | 5 | 32×32 | Shard burst when freeze ends |
| IR04 | ice_projectile | 4 | 20×20 | Icy bolt travelling to target |

**Palette:** Custom ice-blue gradient (indices 1-9: white → deep blue)

## Before Testing: Compile GPL

Run `cmd /c MakeGPL.bat` from `IceSpell_Quest/` folder on game machine.
This compiles the new `Ice_Freeze_Cast` + `Ice_Freeze_Begin` functions.

## What to Look For

### 1. Projectile Travel
- Ice Elemental does Cast animation
- A small (20×20) blue/white bolt should fly from caster to target
- Uses "fast missile" movement speed

### 2. Cold Stack Accumulation (no visual until threshold)
- Each hit deals 8 damage
- No freeze overlay until 5 stacks

### 3. Freeze Application (at 5 stacks)
- Target turns grey (petrify shader)
- 48×64 animated ice shimmer overlay appears on unit
- Overlay should have visible icicles/crystals around edges with sparkle animation
- Unit stops moving (intent_petrified)
- DOT: 5 damage every 2 seconds

### 4. Thaw (after 10 seconds)
- Ice overlay removed
- 32×32 shard burst appears briefly (2 seconds)
- Unit resumes activity
- 5-second immunity window (stacks set to -1)

## Troubleshooting

**Projectile not visible:**
- Check IceSpell_Projectiles.xml is loaded (in Quest.mqxml)
- Verify IR04 IMAG exists in CAM (`python sprite_extractor.py --cam IceSpell_Quest/Data/Quest_maindata.cam --list`)

**Freeze overlay not visible:**
- Overlay is 48×64 — look for subtle ice border around the grey unit
- If too subtle, the pixel art may need more density/brightness

**Crash on cast:**
- `$CreateMissile("ice_freeze_missile", ...)` needs the projectile XML loaded
- Verify GPL compiled successfully (check IceSpell_Quest.bcd exists and is recent)

**No thaw animation:**
- IR03 thaw_effector must exist in CAM
- `$createeffector(ThisAgent, "thaw_effector", 2000)` in Ice_Freeze_End
