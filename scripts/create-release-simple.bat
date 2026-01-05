@echo off
REM Simplified release script that avoids complex parsing

echo ========================================
echo GitHub Release Creator (Simple)
echo ========================================
echo.

REM Check if gh CLI is installed
where gh >nul 2>nul
if errorlevel 1 (
    echo Error: GitHub CLI (gh) is not installed.
    echo Install it from: https://cli.github.com/
    pause
    exit /b 1
)

REM Check if authenticated
gh auth status >nul 2>&1
if errorlevel 1 (
    echo Not authenticated. Please run: gh auth login
    pause
    exit /b 1
)

REM Get version from user
set /p NEW_VERSION="Enter version number (e.g., 1.0.1): "

if "%NEW_VERSION%"=="" (
    echo Error: Version is required
    pause
    exit /b 1
)

REM Update package.json using npm
echo.
echo Updating package.json...
call npm version %NEW_VERSION% --no-git-tag-version
if errorlevel 1 (
    echo Error updating version
    pause
    exit /b 1
)

REM Build package
echo Building package...
call npm run build
if errorlevel 1 (
    echo Error building package
    pause
    exit /b 1
)

REM Get release notes
set /p RELEASE_NOTES="Enter release notes (optional): "
if "%RELEASE_NOTES%"=="" (
    set RELEASE_NOTES=Release v%NEW_VERSION%
)

REM Create git tag
echo.
echo Creating git tag...
git add package.json
git commit -m "chore: bump version to %NEW_VERSION%" 2>nul

REM Delete local tag if exists
git tag -d v%NEW_VERSION% 2>nul

REM Create tag
git tag -a v%NEW_VERSION% -m "Release v%NEW_VERSION%"
if errorlevel 1 (
    echo Error creating tag
    pause
    exit /b 1
)

REM Get branch name
for /f %%b in ('git rev-parse --abbrev-ref HEAD') do set BRANCH=%%b
if "%BRANCH%"=="" set BRANCH=main

REM Push tag
echo.
set /p PUSH="Push tag to GitHub? (y/n): "
if /i "%PUSH%"=="y" (
    echo Pushing tag...
    git push origin v%NEW_VERSION%
    git push origin %BRANCH%
)

REM Create release
echo.
echo Creating GitHub release...
gh release create v%NEW_VERSION% --title "Release v%NEW_VERSION%" --notes "%RELEASE_NOTES%" --target %BRANCH%

if errorlevel 1 (
    echo.
    echo Error creating release. Tag may need to be pushed first.
    echo Try: git push origin v%NEW_VERSION%
    pause
    exit /b 1
)

echo.
echo ========================================
echo Release created successfully!
echo ========================================
echo.
echo Release: https://github.com/shanle1117/workshop2/releases/tag/v%NEW_VERSION%
echo.
pause



