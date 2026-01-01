# 🚀 GitHub Releases Quick Start

## Quick Commands

### Create a Release (Easiest)

**Using npm script:**
```bash
npm run release 1.0.1
```

**Using shell script:**
```bash
# Linux/Mac
./scripts/create-release.sh

# Windows
scripts\create-release.bat
```

**Using GitHub CLI:**
```bash
# 1. Update version
npm version 1.0.1 --no-git-tag-version

# 2. Build
npm run build

# 3. Create tag and release
git add package.json
git commit -m "chore: bump version to 1.0.1"
git tag -a v1.0.1 -m "Release v1.0.1"
git push origin v1.0.1
gh release create v1.0.1 --title "Release v1.0.1" --notes "Release notes"
```

### Version Bumping

```bash
# Patch version (1.0.0 → 1.0.1)
npm run version:patch

# Minor version (1.0.0 → 1.1.0)
npm run version:minor

# Major version (1.0.0 → 2.0.0)
npm run version:major
```

## What Happens When You Create a Release?

1. ✅ Version updated in `package.json`
2. ✅ Package built (`npm run build`)
3. ✅ Git tag created (`v1.0.1`)
4. ✅ GitHub release created
5. ✅ Package automatically published to GitHub Packages

## Prerequisites

1. **Install GitHub CLI:**
   ```bash
   # Windows
   winget install GitHub.cli
   
   # Mac
   brew install gh
   
   # Linux
   sudo apt install gh
   ```

2. **Login:**
   ```bash
   gh auth login
   ```

## Release Workflow Options

### Option 1: Manual Script (Recommended)
```bash
npm run release 1.0.1 "Release notes here"
```

### Option 2: GitHub Actions
1. Go to **Actions** → **Create Release**
2. Click **Run workflow**
3. Enter version and notes
4. Click **Run workflow**

### Option 3: Push Tag
```bash
git tag -a v1.0.1 -m "Release v1.0.1"
git push origin v1.0.1
```
This triggers the automated workflow.

## Version Format

Use [Semantic Versioning](https://semver.org/):
- `1.0.0` - Major.Minor.Patch
- `1.0.1` - Bug fix
- `1.1.0` - New feature
- `2.0.0` - Breaking change

## Viewing Releases

```bash
# List all releases
gh release list

# View specific release
gh release view v1.0.1

# Open in browser
gh release view v1.0.1 --web
```

## Installing from Releases

Users can install specific versions:

```bash
# Latest
npm install @shanle1117/faix-chatbot

# Specific version
npm install @shanle1117/faix-chatbot@1.0.1

# Version range
npm install @shanle1117/faix-chatbot@^1.0.0
```

## Troubleshooting

### "gh: command not found"
Install GitHub CLI: https://cli.github.com/

### "Not authenticated"
Run: `gh auth login`

### "Tag already exists"
```bash
git tag -d v1.0.1
git push origin --delete v1.0.1
```

### Release created but package not published
Check GitHub Actions workflow logs for errors.

## Full Documentation

See `docs/GITHUB_RELEASES_GUIDE.md` for complete guide.

