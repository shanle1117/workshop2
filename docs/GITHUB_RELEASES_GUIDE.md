# GitHub Releases Guide

This guide explains how to create and manage GitHub releases for the FAIX Chatbot project.

## Overview

GitHub Releases provide a way to package and distribute specific versions of your project. When you create a release, it automatically:
1. Creates a git tag
2. Publishes the package to GitHub Packages
3. Creates release notes and changelog
4. Makes the version available for installation

## Prerequisites

1. **GitHub CLI** (recommended): Install from https://cli.github.com/
   ```bash
   # Windows (via winget)
   winget install GitHub.cli
   
   # Mac
   brew install gh
   
   # Linux
   sudo apt install gh
   ```

2. **Authentication**: Login to GitHub CLI
   ```bash
   gh auth login
   ```

## Creating a Release

### Method 1: Using the Script (Recommended)

**Windows:**
```cmd
scripts\create-release.bat
```

**Linux/Mac:**
```bash
chmod +x scripts/create-release.sh
./scripts/create-release.sh
```

The script will:
1. Show current version
2. Prompt for new version
3. Update `package.json`
4. Build the package
5. Create git tag
6. Create GitHub release
7. Trigger package publishing

### Method 2: Using GitHub CLI Directly

```bash
# 1. Update version in package.json
npm version 1.0.1 --no-git-tag-version

# 2. Build package
npm run build

# 3. Commit changes
git add package.json
git commit -m "chore: bump version to 1.0.1"

# 4. Create and push tag
git tag -a v1.0.1 -m "Release v1.0.1"
git push origin v1.0.1

# 5. Create release
gh release create v1.0.1 \
  --title "Release v1.0.1" \
  --notes "Release notes here"
```

### Method 3: Using GitHub Web Interface

1. Go to your repository on GitHub
2. Click **"Releases"** → **"Create a new release"**
3. Choose a tag (or create new tag `v1.0.1`)
4. Fill in release title and notes
5. Click **"Publish release"**

The GitHub Actions workflow will automatically:
- Build the package
- Publish to GitHub Packages

### Method 4: Using GitHub Actions Workflow

1. Go to **Actions** tab
2. Select **"Create Release"** workflow
3. Click **"Run workflow"**
4. Enter version number (e.g., `1.0.1`)
5. Optionally add release notes
6. Click **"Run workflow"**

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.0.0 → 2.0.0): Breaking changes
- **MINOR** (1.0.0 → 1.1.0): New features (backward compatible)
- **PATCH** (1.0.0 → 1.0.1): Bug fixes (backward compatible)

### Pre-release Versions

- **Alpha**: `1.0.0-alpha.1`
- **Beta**: `1.0.0-beta.1`
- **RC**: `1.0.0-rc.1`

## Release Notes

### Best Practices

1. **Be Descriptive**: Explain what changed and why
2. **Categorize Changes**:
   - Added: New features
   - Changed: Changes in existing functionality
   - Deprecated: Soon-to-be removed features
   - Removed: Removed features
   - Fixed: Bug fixes
   - Security: Security fixes

3. **Include Links**: Reference issues, PRs, and documentation

### Example Release Notes

```markdown
## Release v1.0.1

### Added
- GitHub Packages integration
- Automated release workflow
- Release creation scripts

### Fixed
- Authentication issues with GitHub Packages
- Build process improvements

### Changed
- Updated dependencies to latest versions

### Installation

```bash
npm install @shanle1117/faix-chatbot@1.0.1
```
```

## Updating CHANGELOG.md

Keep `CHANGELOG.md` updated with each release:

1. Add new entries under `[Unreleased]` as you work
2. When releasing, move entries to version section
3. Update links at bottom of file

Example:
```markdown
## [Unreleased]

### Added
- New feature X

## [1.0.1] - 2025-01-01

### Fixed
- Bug fix Y

[Unreleased]: https://github.com/shanle1117/workshop2/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/shanle1117/workshop2/releases/tag/v1.0.1
```

## Automated Workflows

### Release Workflow

The `.github/workflows/create-release.yml` workflow:
- Triggers on version tags (`v*.*.*`)
- Updates `package.json` version
- Builds the package
- Generates changelog
- Creates GitHub release
- Publishes to GitHub Packages

### Package Publishing

The `.github/workflows/publish-package.yml` workflow:
- Triggers on release creation
- Builds the package
- Publishes to GitHub Packages

## Viewing Releases

1. **GitHub Web**: Go to repository → **Releases** tab
2. **GitHub CLI**:
   ```bash
   gh release list
   gh release view v1.0.1
   ```

## Installing from Releases

Users can install specific versions:

```bash
# Latest version
npm install @shanle1117/faix-chatbot

# Specific version
npm install @shanle1117/faix-chatbot@1.0.1

# Version range
npm install @shanle1117/faix-chatbot@^1.0.0
```

## Troubleshooting

### Release Not Creating Package

**Check:**
1. Workflow ran successfully (check Actions tab)
2. `GITHUB_TOKEN` has correct permissions
3. Package name matches scope (`@shanle1117/faix-chatbot`)

### Tag Already Exists

**Solution:**
```bash
# Delete local tag
git tag -d v1.0.1

# Delete remote tag
git push origin --delete v1.0.1

# Create new tag
git tag -a v1.0.1 -m "Release v1.0.1"
git push origin v1.0.1
```

### Version Mismatch

Ensure `package.json` version matches the release tag:
- Tag: `v1.0.1`
- package.json: `"version": "1.0.1"`

## Best Practices

1. **Always update CHANGELOG.md** before releasing
2. **Test the build** before creating release
3. **Use semantic versioning** consistently
4. **Write clear release notes** for users
5. **Tag releases** with `v` prefix (e.g., `v1.0.1`)
6. **Keep releases organized** with consistent naming

## Quick Reference

```bash
# Create release (script)
./scripts/create-release.sh

# Create release (manual)
npm version 1.0.1 --no-git-tag-version
npm run build
git tag -a v1.0.1 -m "Release v1.0.1"
git push origin v1.0.1
gh release create v1.0.1 --title "Release v1.0.1" --notes "..."

# List releases
gh release list

# View release
gh release view v1.0.1

# Delete release
gh release delete v1.0.1
```

## Additional Resources

- [GitHub Releases Documentation](https://docs.github.com/en/repositories/releasing-projects-on-github)
- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [GitHub CLI Documentation](https://cli.github.com/manual/)

