# IceSpell_Quest Crash Troubleshooting

## Crash #1 — 2026-07-10 01:38 (majestyhd_crash_2026_7_10T1_38_47C0.mdmp)

**Context:** Game running IceSpell_Quest, spell working normally.

**No specific trigger identified from logs.** The gpl.log showed normal freeze spam behavior. Game may have crashed from accumulated state or an unrelated engine issue.

---

## Crash #2 — 2026-07-10 01:47 (majestyhd_crash_2026_7_10T1_47_46C0.mdmp)

**Context:** Same session/quest. Crash during active gameplay.

**No additional info beyond above.**

---

## Crash #3 — 2026-07-09 22:08 session (latest dump)

**Context:** IceSpell_Quest running. IceElemental#202 was freeze-spamming Ranger#101 (same "already petrified" loop). Player was also casting spells (7x `PLAYER_SPELL_MESSAGE` between frames 5108-5271).

**err.log notable entries:**
```
Error opening, C:\Users\Brandon\Documents\My Games\MajestyHD\Logs\gpl.log (Sharing violation)
Error creating, C:\Users\Brandon\Documents\My Games\MajestyHD\Logs\gpl.log (Sharing violation)
```
The game couldn't write to gpl.log (something else had the file open — editor or external tool). This may or may not be related to the crash.

**gpl.log at time of crash:**
- IceElemental#202 spamming `Ice_Freeze_Begin` on `Ranger#101` every frame
- Every call hits "Target already petrified, returning" guard — no state modification
- This version uses `HasEffectPetrify` check (older GPL that includes `SetAttribute HasEffectPetrify` + `GetProperUnitArt`)
- Log cuts off abruptly mid-loop — no error, just stops

**Possible crash causes:**
1. **Targeting spam overload** — The IceElemental fires Ice_Freeze_Begin every single frame. Even though it returns early, this is hundreds of GPL function calls per second with $DebugOut. The sheer volume of debug output + function dispatches could cause memory/timing issues, especially combined with player spell casts happening simultaneously.
2. **Player spell interaction** — 7 player spells cast in rapid succession (frames 5108-5271) while the ice freeze loop was running. If any player spell targets the same frozen unit, there could be a state conflict.
3. **gpl.log sharing violation** — The engine tries to write debug output but fails. If the engine doesn't handle this gracefully, the write failure could corrupt internal state.
4. **Unrelated engine instability** — The game is old and may have inherent crash bugs unrelated to the mod.

---

## Recommendations for Next Agent

1. **Fix the targeting spam (HIGH PRIORITY)** — This is likely contributing to crashes. The IceElemental should NOT keep casting on an already-frozen target. Options:
   - In the spell action XML: add targeting constraints to only target unfrozen units
   - In GPL: after successful freeze, use `$SpecifyIntent` or `$StopAction` on the caster to prevent immediate re-cast
   - Change the spell's `TimeoutDuration` to add a cooldown between casts

2. **Remove $DebugOut calls** — The massive log spam from every-frame debug output could be causing timing issues. Strip debug logs for stability testing.

3. **Close gpl.log before testing** — Make sure no editors/tools have gpl.log open when running the game. The "Sharing violation" prevents the engine from writing debug output and may cause instability.

4. **Test without Quest_maindata.cam** — To isolate whether the crash is sprite-related or GPL-related, try removing the `<CAM>` line temporarily. If crashes stop, the IMAG data is the cause. If they continue, it's the GPL spam.
