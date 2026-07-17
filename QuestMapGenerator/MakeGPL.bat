@echo off

rem Where the source files are located
set SRC=GPL
rem Where the compiled code will go
set DEST=GPL
rem The name of the compiled GPL byte code
set OUTPUTNAME=default_quest.bcd
rem The project file that defines what files will be compiled
set GPLPROJECTFILE=default_quest.gplproj

set GPLBCC="C:\Program Files (x86)\Steam\steamapps\common\Majesty HD\SDK\gplbcc.exe"

rem Check to make sure the compiler is available
if NOT EXIST %GPLBCC% goto missingCompiler

:foundCompiler

echo Using GPL compiler at %GPLBCC%
call :buildit %GPLPROJECTFILE% %OUTPUTNAME%

if NOT EXIST "%SRC%\%OUTPUTNAME%" goto buildFailed

echo Build successful!
goto :EOF

rem ************************************************
:buildit

pushd %SRC%
if EXIST %2 del %2
echo Building %1, output as %2
%GPLBCC% -in %1 -out %2 -stdout
popd

goto :EOF

rem ************************************************
:missingCompiler
echo ERROR: Unable to find the GPL compiler at %GPLBCC%
echo Set the path to gplbcc.exe in this script.
goto :EOF

rem ************************************************
:buildFailed
echo ERROR: Compile failed.
goto :EOF
