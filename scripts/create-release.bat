@echo off
setlocal enabledelayedexpansion
REM Script to create a GitHub release on Windows

echo ========================================
echo GitHub Release Creator
echo ========================================
echo.

REM Check if gh CLI is installed
where gh >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: GitHub CLI (gh) is not installed.
    echo Install it from: https://cli.github.com/
    pause
    exit /b 1
)

REM Check if authenticated
gh auth status >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Not authenticated. Please run: gh auth login
    pause
    exit /b 1
)

REM Get current version from package.json
echo Reading current version...
node -p "require('./package.json').version" > temp_version.txt 2>nul
if exist temp_version.txt (
    set /p CURRENT_VERSION=<temp_version.txt
    del temp_version.txt
) else (
    set CURRENT_VERSION=unknown
)
if "%CURRENT_VERSION%"=="" set CURRENT_VERSION=unknown
echo Current version: %CURRENT_VERSION%

REM Prompt for new version
set /p NEW_VERSION="Enter new version (current: %CURRENT_VERSION%): "

if "%NEW_VERSION%"=="" (
    echo Error: Version is required
    pause
    exit /b 1
)

REM Update package.json version
echo.
echo Updating package.json...
call npm version %NEW_VERSION% --no-git-tag-version

REM Build package
echo Building package...
call npm run build

REM Prompt for release notes
set /p RELEASE_NOTES="Enter release notes (optional): "

REM Create git tag
echo.
echo Creating git tag v%NEW_VERSION%...
git add package.json
git commit -m "chore: bump version to %NEW_VERSION%" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo No changes to commit
)

REM Check if tag already exists locally
git rev-parse "v%NEW_VERSION%" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Tag v%NEW_VERSION% already exists locally.
    set /p DELETE_TAG="Delete and recreate? (y/n): "
    if /i "!DELETE_TAG!"=="y" (
        git tag -d "v%NEW_VERSION%" 2>nul
    )
)

REM Create tag if it doesn't exist
git rev-parse "v%NEW_VERSION%" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    git tag -a "v%NEW_VERSION%" -m "Release v%NEW_VERSION%"
    echo Created tag v%NEW_VERSION%
)

REM Get current branch name
git rev-parse --abbrev-ref HEAD > temp_branch.txt 2>nul
if exist temp_branch.txt (
    set /p CURRENT_BRANCH=<temp_branch.txt
    del temp_branch.txt
) else (
    set CURRENT_BRANCH=main
)
if "%CURRENT_BRANCH%"=="" set CURRENT_BRANCH=main

REM Push tag
echo.
set /p PUSH_TAG="Push tag to GitHub? (y/n): "
if /i "%PUSH_TAG%"=="y" (
    echo Pushing tag and commits...
    git push origin "v%NEW_VERSION%"
    git push origin %CURRENT_BRANCH%
)

REM Create release
echo.
echo Creating GitHub release...

if "%RELEASE_NOTES%"=="" (
    set RELEASE_NOTES=Release v%NEW_VERSION%
)

REM Use --target flag to specify branch, or push tag first
gh release create "v%NEW_VERSION%" --title "Release v%NEW_VERSION%" --notes "!RELEASE_NOTES!" --target "%CURRENT_BRANCH%"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error creating release. Trying without --target flag...
    gh release create "v%NEW_VERSION%" --title "Release v%NEW_VERSION%" --notes "!RELEASE_NOTES!"
)

echo.
echo ========================================
echo Release created successfully!
echo ========================================
echo.
echo Release: https://github.com/shanle1117/workshop2/releases/tag/v%NEW_VERSION%
echo.
echo The package will be automatically published to GitHub Packages.
pause

