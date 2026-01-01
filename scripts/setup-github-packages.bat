@echo off
REM Setup script for GitHub Packages authentication on Windows
echo ========================================
echo GitHub Packages Setup
echo ========================================
echo.

REM Check if GITHUB_TOKEN is set
if "%GITHUB_TOKEN%"=="" (
    echo ERROR: GITHUB_TOKEN environment variable is not set!
    echo.
    echo Please follow these steps:
    echo 1. Go to: https://github.com/settings/tokens
    echo 2. Click "Generate new token (classic)"
    echo 3. Give it a name like "GitHub Packages Token"
    echo 4. Select these scopes:
    echo    - write:packages
    echo    - read:packages
    echo    - delete:packages (optional)
    echo    - repo (if repository is private)
    echo 5. Click "Generate token"
    echo 6. Copy the token
    echo.
    echo Then run this command:
    echo   set GITHUB_TOKEN=your_token_here
    echo.
    echo Or set it permanently:
    echo   setx GITHUB_TOKEN "your_token_here"
    echo.
    pause
    exit /b 1
)

echo GITHUB_TOKEN is set.
echo.

REM Verify token format (should be 40+ characters)
if "%GITHUB_TOKEN:~40,1%"=="" (
    echo WARNING: Token seems too short. Please verify it's correct.
    echo.
)

echo Testing authentication...
npm whoami --registry=https://npm.pkg.github.com
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Authentication failed. Please check:
    echo 1. Token has correct permissions (write:packages, read:packages)
    echo 2. Token is not expired
    echo 3. Username matches the package scope (@shanle1117)
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Setup complete! You can now publish with:
echo   npm run publish:github
echo ========================================
pause

