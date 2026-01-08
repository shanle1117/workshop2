@echo off
REM Quick script to fix release tag issues

echo ========================================
echo Fix Release Tag
echo ========================================
echo.

if "%1"=="" (
    echo Usage: fix-release-tag.bat ^<version^>
    echo Example: fix-release-tag.bat 1.0.1
    pause
    exit /b 1
)

set VERSION=%1

echo Fixing tag v%VERSION%...
echo.

REM Delete local tag if exists
echo Deleting local tag...
git tag -d v%VERSION% 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Deleted local tag v%VERSION%
) else (
    echo Local tag v%VERSION% doesn't exist
)

REM Delete remote tag if exists
echo.
echo Deleting remote tag...
git push origin --delete v%VERSION% 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Deleted remote tag v%VERSION%
) else (
    echo Remote tag v%VERSION% doesn't exist or already deleted
)

echo.
echo ========================================
echo Tag cleanup complete!
echo ========================================
echo.
echo You can now:
echo 1. Run: scripts\create-release.bat
echo 2. Or manually create tag: git tag -a v%VERSION% -m "Release v%VERSION%"
echo 3. Push tag: git push origin v%VERSION%
echo.
pause












