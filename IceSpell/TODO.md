# IceSpell Mod — TODO / Troubleshooting

## Status: Mod loads, but IceElemental fails to spawn

The mod IS recognized and loaded by the game (confirmed in logs). GPL compiles and runs.
The Ice Cave lair attempts to spawn an IceElemental but fails at runtime.

---

## Issue 1: GUID must be generated properly

**Background:** The original `IceSpell.mmxml` was created by an AI agent with a hand-crafted fake GUID (`{F1CE0001-ICE1-4A2B-B3C4-FREEZESPELL01}`). The game did NOT recognize the mod with this GUID.

The user manually created `Mod.mmxml` using RGSEditor, which generated a valid GUID (`{2A7F2E17-5B54-40B4-88C3-9E15927B9865}`). The user then copied this GUID into `IceSpell.mmxml`, after which the game DID load the mod.

**The "duplicate ID" error in err.log** happened because both `Mod.mmxml` and `IceSpell.mmxml` were deployed with the same GUID — expected behavior since one was copied from the other.

**TODO for next agent:** Investigate how RGSEditor generates GUIDs. Determine if the game validates GUIDs in a specific way (standard UUID v4? registry-based? checksum?) or if the fake GUID was rejected for another reason (e.g., filename convention, XML element order, missing `<Name>` tag). Replicate valid GUID generation in the toolchain so we don't need RGSEditor for this step.

**Reference — working `Mod.mmxml` (RGSEditor-generated):**
```xml
<Majesty>
	<Mod id="{2A7F2E17-5B54-40B4-88C3-9E15927B9865}">
		<DataConfiguration>
			...
		</DataConfiguration>
		<DisplayName lang="en_US">IceSpell</DisplayName>
		<Description lang="en_US">
			<Short>...</Short>
			<Long/>
		</Description>
	</Mod>
</Majesty>
```

Note differences from our `IceSpell.mmxml`:
- No `<Name>` element
- `<DataConfiguration>` comes BEFORE `<DisplayName>`/`<Description>`
- The AI_Takeover working mod (`MyAI.mmxml`) DOES have `<Name>` and puts it first — so element order may not matter

---

## Issue 2: IceElemental has no initialization data

**Error from gpl.log:**
```
MakeAgent() couldn't create an agent of type IceElemental: Reason: couldn't find initialization data.
```

**What this means:** The GPL lair spawn code calls `MakeAgent("IceElemental")` but the engine can't find a complete unit definition with that ID. The `IceSpell_Characters.xml` file WAS loaded (confirmed in err.log), so the XML is being read — but the character definition is missing something.

**TODO:** Compare `IceSpell_Characters.xml` against a working monster definition from the base game. Likely missing required fields. See Issue 3 for a specific missing attribute.

---

## Issue 3: BirthScript attribute missing

**Error from err.log:**
```
GplDispatcherHandle script error:
 Call Sequence was:
$NewUnitInit( 0 ) - line 288 : Tried to access non-existent attribute BirthScript in agent#13, ().
```

**What this means:** When a unit spawns, `$NewUnitInit` reads a `BirthScript` attribute. The IceElemental definition in `IceSpell_Characters.xml` doesn't define this.

**TODO:** Add the missing `birthScript` field (and any other required attributes) to the IceElemental definition. Use a working monster (Yeti/Ice Dragon) as a template.

---

## Issue 4 (resolved): Backslash paths + GPL `<Target>`/`<Source>` structure

Fixed. `IceSpell.mmxml` now uses backslashes and the structured GPL format matching the working AI_Takeover mod. Game confirmed loading all files correctly.

---

## Log Evidence (2026-07-09 17:09)

### err.log — confirms mod loaded successfully:
```
Adding Mod C:\Users\Brandon\Documents\My Games\MajestyHD\Mods\IceSpell\IceSpell.mmxml
Loaded GPL bytecode: ...\IceSpell\Data\IceSpell.bcd
Description file added: ...\IceSpell\Data\IceSpell_Actions.xml
Description file added: ...\IceSpell\Data\IceSpell_Characters.xml
Description file added: ...\IceSpell\Data\IceSpell_Overlays.xml
```

### err.log — duplicate ID warning (because both mmxml files have same GUID):
```
Mod definition ...\Mod.mmxml uses a duplicate ID.  Make new IDs for mods with a GUID creator!
```

### err.log — runtime spawn failure:
```
GplDispatcherHandle script error:
 $NewUnitInit( 0 ) - line 288 : Tried to access non-existent attribute BirthScript in agent#13, ().
```

### gpl.log — spawn failure:
```
MakeAgent() couldn't create an agent of type IceElemental: Reason: couldn't find initialization data.
```

---

## Next Steps (for next agent session)

1. Fix `IceSpell_Characters.xml` — add missing `birthScript` and other required attributes by comparing against working monster definitions
2. Investigate GUID generation — can we produce valid GUIDs without RGSEditor?
3. Remove `Mod.mmxml` from deployed folder (only `IceSpell.mmxml` should be there)
4. Re-deploy and re-test
