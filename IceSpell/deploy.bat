@echo off
rem Deploy IceSpell mod to Majesty Gold HD Mods folder

set DEST=C:\Users\Brandon\Documents\My Games\MajestyHD\Mods\IceSpell

echo Deploying IceSpell to %DEST% ...

if NOT EXIST "%DEST%" (
    mkdir "%DEST%"
)
if NOT EXIST "%DEST%\Data" (
    mkdir "%DEST%\Data"
)
if NOT EXIST "%DEST%\GPL" (
    mkdir "%DEST%\GPL"
)

rem Copy mod definition (only IceSpell.mmxml — do NOT deploy Mod.mmxml, causes duplicate ID error)
copy /y "IceSpell.mmxml" "%DEST%\"

rem Clean up stale Mod.mmxml if it exists in destination
if EXIST "%DEST%\Mod.mmxml" (
    del "%DEST%\Mod.mmxml"
    echo Removed stale Mod.mmxml from destination
)

rem Copy data files
copy /y "Data\IceSpell_Actions.xml" "%DEST%\Data\"
copy /y "Data\IceSpell_Characters.xml" "%DEST%\Data\"
copy /y "Data\IceSpell_Overlays.xml" "%DEST%\Data\"
copy /y "Data\IceSpell.bcd" "%DEST%\Data\"
copy /y "Data\Quest_maindata.cam" "%DEST%\Data\"

rem Copy GPL source (needed for Source reference in mmxml)
copy /y "GPL\IceSpell_Globals.dat" "%DEST%\GPL\"

echo.
echo Deploy complete!
echo.
echo Deployed files:
dir /b "%DEST%\IceSpell.mmxml" 2>nul && echo   IceSpell.mmxml
dir /b "%DEST%\Data\IceSpell_Actions.xml" 2>nul && echo   Data\IceSpell_Actions.xml
dir /b "%DEST%\Data\IceSpell_Characters.xml" 2>nul && echo   Data\IceSpell_Characters.xml
dir /b "%DEST%\Data\IceSpell_Overlays.xml" 2>nul && echo   Data\IceSpell_Overlays.xml
dir /b "%DEST%\Data\IceSpell.bcd" 2>nul && echo   Data\IceSpell.bcd
dir /b "%DEST%\GPL\IceSpell_Globals.dat" 2>nul && echo   GPL\IceSpell_Globals.dat

echo.
if NOT EXIST "%DEST%\Data\IceSpell.bcd" (
    echo WARNING: IceSpell.bcd not found! Run MakeGPL.bat first to compile the GPL.
)
