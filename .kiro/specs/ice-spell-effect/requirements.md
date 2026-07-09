# Requirements Document

## Introduction

An "Ice/Frozen" spell effect for Majesty Gold HD that immobilizes targeted units with a blue/icy visual overlay, dealing cold damage over time. This effect clones the architecture of the existing petrification system (dual effectors, GPL freeze logic, intent override) but replaces the grey stone visual with a blue crystalline ice animation and adds periodic HP drain while frozen. The effect concludes with a unique "shatter/thaw" visual animation when the freeze expires — a feature not present in any existing game effect. The spell is initially assigned to a custom ice monster for easier testing. The feature is packaged as a quest mod using the established SDK structure.

## Glossary

- **Ice_Overlay_Generator**: Python script that produces ice/frozen sprite frames as TILE-format binary data, using only colors available in an existing SPLT palette
- **Thaw_Overlay_Generator**: Python script that produces a "shatter/thaw" end-of-effect animation sequence as TILE-format binary data, showing ice breaking apart
- **Sprite_Injector**: The existing `sprite_injector.py` tool that encodes PNG pixel data into the game's TILE RLE format
- **CAM_Writer**: The existing `cam_writer.py` tool that repacks CAM archives with new or modified TILE entries and IMAG records
- **Quest_CAM**: The custom CAM archive file (e.g., `Quest_maindata.cam`) loaded by the quest's DataConfiguration that contains the ice overlay sprite IMAG and TILE data
- **Freeze_Effector**: The visible overlay unit attached to the target that renders the ice animation on top of the frozen unit
- **Freeze_Icon**: The invisible timer overlay that triggers the `Freeze_End` GPL callback when its duration expires
- **Thaw_Effector**: The visible overlay unit that plays the shatter/thaw animation when the freeze effect ends, then disappears
- **GPL_Compiler**: The `Gplbcc.exe` tool that compiles GPL source into `.bcd` bytecode
- **Effector_System**: The game engine's mechanism for attaching visual overlays and timed callbacks to units via `$createeffector`
- **TILE_Frame**: A single sprite frame stored in the game's 8-bit paletted RLE format with absolute x-positioning per row
- **IMAG_Record**: Animation metadata in `maindata.cam` that groups TILE frames into image sets with frame descriptors
- **SPLT_Palette**: A 256-color RGBA palette in the game's SPLT section; these are read-only and must not be modified
- **Game_Tick**: The game engine's internal timing unit used for effector durations (relationship to real-time seconds varies with game speed)
- **Palette_Quantization**: The process of mapping desired RGB colors to the nearest available colors in an existing SPLT palette
- **Ice_Monster**: A custom monster unit definition with the ice freeze spell assigned via AllowedSpells, used as the initial test vehicle for the effect
- **$NewThread**: GPL builtin that starts a recurring callback on a prototype function field; re-executes at the specified interval until the function returns early or `$KillThread` is called
- **$Freeze_Unit / $UnFreeze_Unit**: Engine builtins that pause/resume all actions on a unit (movement, combat, spellcasting); used by petrify, vines, and now ice freeze
- **$GetProperUnitArt**: Engine builtin that refreshes the unit's visual state based on current attributes and active effectors
- **Prototype Function Field**: A `function` variable declared in a prototype (hero/monster) such as `PlagueScript` or `extrafunction1`; used to store thread handles that can be started with `$NewThread` and stopped with `$KillThread`
- **GPL Expression**: A compile-time constant defined with `expression #Name value` syntax in GPL; used for all tunable parameters (durations, damage values, costs) to keep balance separate from logic

## Requirements

### Requirement 1: Ice Overlay Sprite Generation

**User Story:** As a modder, I want a Python tool that generates ice/frozen overlay sprite frames using existing palette colors, so that I can create the visual effect without manual pixel art skills.

#### Acceptance Criteria

1. WHEN the Ice_Overlay_Generator is executed with a target SPLT palette index, THE Ice_Overlay_Generator SHALL produce a set of TILE_Frame binary files representing an ice crystalline animation loop
2. THE Ice_Overlay_Generator SHALL use only palette indices present in the specified SPLT_Palette for all pixel data in generated frames
3. WHEN generating ice frames, THE Ice_Overlay_Generator SHALL select blue, white, and cyan-range palette indices via Palette_Quantization from the target SPLT_Palette to create an icy visual appearance
4. THE Ice_Overlay_Generator SHALL produce a minimum of 4 and a maximum of 8 animation frames to form a looping shimmer or pulse effect
5. THE Ice_Overlay_Generator SHALL output each frame in valid TILE RLE format (version 3 header, palette ID reference, row offset table, and RLE-compressed pixel segments with absolute x-positioning)
6. WHEN a generated TILE_Frame is decoded by the Sprite_Injector round-trip verification, THE decoded frame SHALL match the original generated pixel data exactly (round-trip property)
7. THE Ice_Overlay_Generator SHALL produce frames with transparent backgrounds (palette index 0) and ice crystal pixels drawn within a bounding area suitable for overlaying a standard unit sprite (approximately 40x60 pixels)
8. IF the specified SPLT_Palette contains fewer than 3 distinct blue/cyan/white palette entries, THEN THE Ice_Overlay_Generator SHALL report an error identifying the palette limitation

### Requirement 2: Thaw/Shatter End Animation Generation

**User Story:** As a modder, I want a shatter/thaw animation that plays when the ice effect ends, so that the transition back to normal has a unique visual that no existing game effect provides.

#### Acceptance Criteria

1. WHEN the Thaw_Overlay_Generator is executed with a target SPLT palette index, THE Thaw_Overlay_Generator SHALL produce a set of TILE_Frame binary files representing an ice-shattering animation sequence
2. THE Thaw_Overlay_Generator SHALL use only palette indices present in the specified SPLT_Palette for all pixel data
3. THE Thaw_Overlay_Generator SHALL produce between 4 and 6 animation frames showing ice fragments breaking apart and fading
4. THE Thaw_Overlay_Generator SHALL output each frame in valid TILE RLE format matching the same specification as the Ice_Overlay_Generator
5. THE thaw animation frames SHALL use a combination of the ice-blue palette indices (for fragments) and transparent pixels (palette index 0) increasing per frame to create a dissolving effect
6. WHEN a generated thaw TILE_Frame is decoded by the Sprite_Injector round-trip verification, THE decoded frame SHALL match the original generated pixel data exactly (round-trip property)

### Requirement 3: IMAG Record and Quest CAM Assembly

**User Story:** As a modder, I want the ice overlay and thaw sprite frames packaged into a valid Quest_CAM archive with proper IMAG metadata, so that the game engine can load and display both the ice and thaw animations.

#### Acceptance Criteria

1. THE CAM_Writer SHALL produce a Quest_CAM file containing two IMAG_Records: one for the ice overlay animation loop and one for the thaw/shatter animation sequence
2. WHEN the Quest_CAM is assembled, each IMAG_Record SHALL define a single directionless image set containing its respective TILE frames in sequential order
3. THE Quest_CAM SHALL include an SPLT section containing the palette referenced by the TILE frames (copied from the source maindata.cam)
4. WHEN the game engine loads the Quest_CAM via DataConfiguration, THE game engine SHALL resolve both IMAG_Record ImageIDBase values to their respective TILE frames without error
5. IF the CAM_Writer repacks the Quest_CAM and re-reads it, THEN THE re-read IMAG_Records and TILE entries SHALL be byte-identical to the original inputs (round-trip property)

### Requirement 4: Overlay XML Definitions

**User Story:** As a modder, I want XML overlay definitions for the ice effect and thaw animation, so that the game engine can attach the visible ice animation, the expiration timer, and the end-of-effect shatter visual to units.

#### Acceptance Criteria

1. THE Freeze_Effector overlay definition SHALL specify `Info value="Directionless"` and `Info value="DontBlock"` engine properties
2. THE Freeze_Effector overlay definition SHALL reference the ice loop IMAG_Record via its `ImageIDBase` attribute
3. THE Freeze_Icon overlay definition SHALL specify `Info value="Directionless"`, `Info value="DontBlock"`, and `Info value="NotVisibleInISOView"` engine properties
4. THE Freeze_Icon overlay definition SHALL include a `Script` element with `GPLFunction="Freeze_End"` to trigger the end-of-effect callback
5. THE Freeze_Effector SHALL have `StackPriority value="0"` and THE Freeze_Icon SHALL have `StackPriority value="1"`
6. THE Freeze_Effector overlay definition SHALL include `Flags value="TransparentToMouse"` in its Game section
7. THE Thaw_Effector overlay definition SHALL specify `Info value="Directionless"` and `Info value="DontBlock"` engine properties
8. THE Thaw_Effector overlay definition SHALL reference the thaw/shatter IMAG_Record via its `ImageIDBase` attribute

### Requirement 5: Action XML Definition

**User Story:** As a modder, I want an Action XML entry defining the ice spell, so that it can be assigned to the Ice_Monster as a castable attack ability.

#### Acceptance Criteria

1. THE ice spell Action definition SHALL specify `ImageSet value="Cast"` and `CompletionImageSet value="Stand"`
2. THE ice spell Action definition SHALL reference `GPLFunction="Freeze_Begin"` in its Script element
3. THE ice spell Action definition SHALL include `Flags value="IsSpell"` in its Game section
4. THE ice spell Action definition SHALL specify a `SpellType value="Attack"` classification
5. THE ice spell Action definition SHALL specify a `TimeoutDuration` value representing the cooldown period in Game_Ticks

### Requirement 6: GPL Freeze Logic

**User Story:** As a modder, I want GPL functions that immobilize the target, apply the ice visual overlay, deal periodic cold damage, play the thaw animation on expiration, and cleanly remove the effect, so that the ice spell has complete gameplay functionality.

**Implementation Pattern:** This requirement follows the dual-effector architecture proven by `Gorgon_Petrify_Begin`/`Gorgon_Petrify_End` in `GPLMx/TaskModules/Subtasks/mx_Spells.gpl`, combined with the `$NewThread`-based periodic callback pattern from `Ratman_Plague_Active` for damage-over-time. The function signature follows the monster-cast spell pattern: `function Freeze_Begin(agent thisagent, agent target)` where thisagent is the caster and target is the victim.

**Thread Lifecycle:** `$NewThread(target's "FreezeScript", interval, target)` creates a recurring thread that re-executes at the given interval. The thread terminates when the function hits a `return` statement (e.g., on `$IsDead` check or when the freeze flag is cleared). External termination uses `$KillThread(target's "FreezeScript")`. This matches the Ratman Plague pattern where `Ratman_Plague_Active` returns early to end the loop.

**Prototype Field Usage:** The damage thread handle is stored via `$AddAttribute(target, "FreezeScript", "function", $Freeze_Damage_Tick)` followed by `$NewThread(target's "FreezeScript", interval, target)` — matching the `SpecialItemsExample` SDK pattern. The freeze-active flag uses a separate `$AddAttribute(target, "is_frozen_ice", "boolean", TRUE)` or a prototype `extrabool` field. We do NOT reuse `#ATTRIB_HasEffectPetrify` because: (a) `GetProperUnitArt` maps it to grey color, not blue; (b) `UnFreeze_Unit` checks it for freeze-lock release; (c) it would prevent a unit from being both petrified and frozen.

**Override Functions Required:** The mod must provide overridden versions of `Freeze_Unit`, `UnFreeze_Unit`, and `GetProperUnitArt` (all are GPL functions, not engine builtins). Specifically:
- `UnFreeze_Unit` must add our custom freeze attribute to its freeze-lock check (so a unit stays frozen even after petrify/vines wear off)
- `GetProperUnitArt` must add a blue color case for our freeze attribute (so frozen units render blue, not grey)
- These overrides are loaded via the quest's DataConfiguration GPL section, replacing the base implementations

#### Acceptance Criteria

1. WHEN Freeze_Begin is called with `(agent thisagent, agent target)`, THE GPL function SHALL call `$createeffector(target, "freeze_effector", 0)` to attach the visible ice overlay with infinite duration (duration 0 = persistent until deleted)
2. WHEN Freeze_Begin is called on a target, THE GPL function SHALL call `$createeffector(target, "freeze_icon", duration)` to start the expiration timer, where duration is `#Freeze_Duration` (potentially halved by magic resistance check)
3. WHEN Freeze_Begin is called on a target, THE GPL function SHALL call the `Freeze_Unit(target)` GPL function (which internally calls `$StopMoving(target)`, `$SuspendThread(target's "ActiveScript")`, and `$SetAttribute(target, #ATTRIB_IsFrozen, 1)`) followed by `$SpecifyIntent(target, #intent_petrified)` to immobilize the unit
4. WHEN Freeze_Begin is called on a target, THE GPL function SHALL call `$GetProperUnitArt(target)` after freezing to apply the frozen visual state
5. WHEN Freeze_Begin is called on a target, THE GPL function SHALL set the freeze-active tracking flag via `$AddAttribute(target, "is_frozen_ice", "boolean", TRUE)` (or set a prototype extrabool field) — this is a custom attribute independent from `#ATTRIB_HasEffectPetrify` to allow both effects to coexist on the same unit
6. IF Freeze_Begin is called on a target that already has the freeze-active flag (`target's "is_frozen_ice"`) equal to TRUE, THEN THE GPL function SHALL return without applying a duplicate effect (checked via `$HasAttribute("is_frozen_ice", target)` and value test)
7. WHEN Freeze_Begin is called, THE GPL function SHALL start the damage-over-time thread by assigning `$Freeze_Damage_Tick` to a prototype function field on target and calling `$NewThread(target's "FreezeScript", #Freeze_DamageInterval, target)` — this thread auto-repeats at the interval until it returns early
8. THE `Freeze_Damage_Tick` function SHALL check `$IsDead(thisagent)` as its first statement and return immediately if true (this terminates the auto-repeating thread cleanly when the unit dies)
9. THE `Freeze_Damage_Tick` function SHALL call `$AdjustAttribute(thisagent, #ATTRIB_HP, -#Freeze_DamagePerTick)` to apply cold damage each tick (unlike Ratman Plague, the ice spell CAN kill — no HP floor is applied)
10. WHEN Freeze_End is called (triggered by freeze_icon expiration via its `GPLFunction` Script element), THE GPL function SHALL set `target's "is_frozen_ice" = FALSE`, call `$KillThread(thisagent's "FreezeScript")` to stop damage ticks, call `$GetProperUnitArt(thisagent)` to restore visuals (which will now return "none" color since the freeze flag is cleared), and call `$UnFreeze_Unit(thisagent)` to resume unit actions (which will check all freeze-lock attributes including ours)
11. WHEN Freeze_End is called, THE GPL function SHALL call `$createeffector(thisagent, "thaw_effector", #Freeze_ThawDuration)` to play the shatter/thaw animation (the effector auto-removes itself after its duration expires)
12. THE Freeze_Begin function SHALL guard against invalid targets by returning immediately if: `$IsDead(target)` is true, OR `Target's "Type" == "Building"`, OR `Target's "Type" == "Lair"`
13. IF `$isRunning(target's "FreezeScript")` is available and returns true when Freeze_End is called, THE function SHOULD use it as a defensive check before calling `$KillThread` (matches the `Palace_Death` defensive pattern)
14. THE mod SHALL provide an overridden `UnFreeze_Unit` function that adds the ice freeze attribute check to the freeze-lock condition alongside `#ATTRIB_HasEffectPetrify`, `#ATTRIB_HasEffectVines`, `#ATTRIB_HasEffectParalyticGaze`, and `#ATTRIB_HasEffectLevelLeach` — so that a unit is NOT unfrozen while ice effect is active
15. THE mod SHALL NOT override `GetProperUnitArt` — the ice overlay sprite provides sufficient visual clarity without a unit tint color change (unlike petrify which uses a grey tint because its overlay is subtle)
16. THE mod SHALL provide an overridden `Freeze_Unit` function (or reuse the existing one unchanged) that calls `$StopMoving`, `$SuspendThread(ThisAgent's "ActiveScript")`, and sets `#ATTRIB_IsFrozen = 1`

### Requirement 7: Ice Monster Character Definition

**User Story:** As a modder, I want a custom ice monster unit with the freeze spell assigned as its attack ability, so that I can spawn it in-game to test the ice effect without needing a temple or hero casting system.

#### Acceptance Criteria

1. THE Ice_Monster character definition SHALL specify `CanUse value="Monster"` to classify it as a spawnable enemy
2. THE Ice_Monster character definition SHALL include an `AllowedSpells` section with the ice freeze action as its primary spell
3. THE Ice_Monster character definition SHALL reference an existing monster's `ImageIDBase` for its visual appearance (sprite reuse for initial testing)
4. THE Ice_Monster character definition SHALL specify `AttackRange` with a `max` value greater than 1 to enable ranged spell casting
5. THE Ice_Monster character definition SHALL include standard monster attributes (MaxHP, Speed, SightRange, Experience) with values suitable for mid-game encounters

### Requirement 8: Quest Mod Packaging

**User Story:** As a modder, I want the ice spell packaged as a complete quest mod with all required files referenced in the DataConfiguration, so that it loads correctly when the quest is selected.

#### Acceptance Criteria

1. THE quest `.mqxml` file SHALL include a `DataConfiguration` section that loads the Quest_CAM, overlay XML, action XML, and compiled GPL bytecode
2. WHEN the game loads the quest, THE DataConfiguration SHALL specify `base="Majesty"` to inherit all base game data before applying custom definitions
3. THE quest package SHALL include a compiled `.bcd` bytecode file produced by the GPL_Compiler from the freeze GPL source
4. THE quest package SHALL contain all files in the expected directory structure: `.mqxml` at root, data files under `Data/`, GPL source under `GPL/`
5. WHEN the quest is loaded by the game, THE custom overlay definitions SHALL override or extend the base overlay list without conflicting with existing overlay IDs

### Requirement 9: Palette Color Selection and Validation

**User Story:** As a modder, I want a palette analysis tool that identifies suitable blue/ice colors from existing SPLT palettes, so that I can select the best palette for the ice overlay without trial-and-error.

#### Acceptance Criteria

1. WHEN the palette analyzer is run against a maindata.cam file, THE analyzer SHALL enumerate all SPLT palettes and rank them by number of blue/cyan/white color entries available
2. THE palette analyzer SHALL classify colors as "ice-suitable" when their RGB values have a blue channel dominant over red (B > R) and saturation below a configurable threshold for white detection
3. WHEN a palette is selected, THE analyzer SHALL output the specific palette indices suitable for ice sprite generation
4. THE analyzer SHALL report the total count of ice-suitable colors per palette to guide palette selection
5. IF no palette contains at least 3 ice-suitable colors, THEN THE analyzer SHALL report that limitation and suggest the closest available palettes

### Requirement 10: Freeze Duration and Damage Configuration

**User Story:** As a modder, I want configurable duration and damage parameters defined as GPL expressions, so that the ice spell can be balanced through simple value changes without modifying logic code.

**Implementation Pattern:** This follows the established `expression` keyword pattern used in `mx_Globals.gpl` (e.g., `expression #Deathmatch_Rage_Krolm_Duration 45000`, `expression #SpellCost_Petrify 1500`, `expression #Dwarfeh_AI_Ratman_Plague_Callback_Time 1000`). All tunable values are declared as named expressions in a globals GPL file included by the `.gplproj`, keeping balance tweaks separate from logic.

#### Acceptance Criteria

1. THE GPL source SHALL define the freeze duration as a named expression `expression #Freeze_Duration <value>` in the globals file, where value is in Game_Ticks (comparable to petrify's 19000)
2. THE GPL source SHALL define the cold damage-per-tick amount as a named expression `expression #Freeze_DamagePerTick <value>` (comparable to Ratman Plague's random 1-6 HP per tick)
3. THE GPL source SHALL define the damage tick interval as a named expression `expression #Freeze_DamageInterval <value>` in Game_Ticks (comparable to `#Dwarfeh_AI_Ratman_Plague_Callback_Time` at 1000)
4. THE GPL source SHALL define the thaw animation duration as a named expression `expression #Freeze_ThawDuration <value>` controlling how long the shatter visual plays
5. WHEN a target has magic resistance, THE Freeze_Begin function SHALL check `$randomnumber(100) <= $getattribute(target, #ATTRIB_MagicResistance)` and if true, halve the freeze duration (matching the exact pattern used by `Gorgon_Petrify_Begin`)
6. THE GPL source SHALL define the spell cooldown as the `TimeoutDuration` value in the Action XML definition (not as a GPL expression, matching existing spell conventions like `Gorgon_Petrify` with `TimeoutDuration value="90000"`)
