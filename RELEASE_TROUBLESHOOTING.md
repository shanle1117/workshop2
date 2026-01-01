# 🔧 Release Troubleshooting Guide

## Common Errors and Solutions

### Error 1: "tag v1.0.1 exists locally but has not been pushed"

**Problem:**
```
tag v1.0.1 exists locally but has not been pushed to shanle1117/workshop2, 
please push it before continuing or specify the `--target` flag
```

**Solution:**

**Option A: Push the tag first**
```bash
git push origin v1.0.1
gh release create v1.0.1 --title "Release v1.0.1" --notes "Release notes"
```

**Option B: Delete and recreate**
```bash
# Windows
scripts\fix-release-tag.bat 1.0.1

# Linux/Mac
./scripts/fix-release-tag.sh 1.0.1

# Then run release script again
scripts\create-release.bat
```

**Option C: Use --target flag**
```bash
# Get current branch
git rev-parse --abbrev-ref HEAD

# Create release with --target flag
gh release create v1.0.1 --title "Release v1.0.1" --notes "Release notes" --target main
```

### Error 2: "is was unexpected at this time" (Windows Batch)

**Problem:**
Windows batch script syntax error, usually caused by:
- Missing `setlocal enabledelayedexpansion`
- Incorrect variable expansion
- Special characters in variables

**Solution:**
The batch script has been fixed. If you still see this error:

1. **Make sure you're using the latest script:**
   ```cmd
   git pull origin main
   ```

2. **Run with explicit path:**
   ```cmd
   call scripts\create-release.bat
   ```

3. **Check for special characters** in version number (should be like `1.0.1`, not `1.0.1-beta`)

### Error 3: Tag Already Exists Remotely

**Problem:**
```
Error: Release v1.0.1 already exists
```

**Solution:**

**Delete and recreate:**
```bash
# Delete remote release
gh release delete v1.0.1

# Delete remote tag
git push origin --delete v1.0.1

# Delete local tag
git tag -d v1.0.1

# Now create release again
scripts\create-release.bat
```

### Error 4: Authentication Issues

**Problem:**
```
Not authenticated. Please run: gh auth login
```

**Solution:**
```bash
gh auth login
# Follow the prompts to authenticate
```

### Error 5: Build Fails Before Release

**Problem:**
Build fails during release creation.

**Solution:**
1. **Test build manually:**
   ```bash
   npm run build
   ```

2. **Fix build errors** before creating release

3. **Check dependencies:**
   ```bash
   npm install
   ```

## Quick Fix Commands

### Clean up existing tag
```bash
# Windows
scripts\fix-release-tag.bat 1.0.1

# Linux/Mac
./scripts/fix-release-tag.sh 1.0.1
```

### Manual release creation
```bash
# 1. Update version
npm version 1.0.1 --no-git-tag-version

# 2. Build
npm run build

# 3. Commit
git add package.json
git commit -m "chore: bump version to 1.0.1"

# 4. Create and push tag
git tag -a v1.0.1 -m "Release v1.0.1"
git push origin v1.0.1

# 5. Create release
gh release create v1.0.1 --title "Release v1.0.1" --notes "Release notes"
```

### Check tag status
```bash
# Check local tags
git tag -l

# Check remote tags
git ls-remote --tags origin

# Check if tag exists
git rev-parse v1.0.1
```

## Step-by-Step Fix for Your Current Issue

Based on your error, here's what to do:

1. **Clean up the existing tag:**
   ```cmd
   scripts\fix-release-tag.bat 1.0.1
   ```

2. **Or manually:**
   ```cmd
   git tag -d v1.0.1
   git push origin --delete v1.0.1
   ```

3. **Create release again:**
   ```cmd
   scripts\create-release.bat
   ```

4. **When prompted to push tag, choose 'y'** to push it immediately

## Prevention Tips

1. **Always push tags immediately** after creating them
2. **Use the fix script** if tag already exists
3. **Check tag status** before creating release:
   ```bash
   git tag -l | grep v1.0.1
   git ls-remote --tags origin | grep v1.0.1
   ```

## Still Having Issues?

1. Check GitHub Actions logs if using automated workflow
2. Verify GitHub CLI is up to date: `gh --version`
3. Check authentication: `gh auth status`
4. Verify repository access: `gh repo view`

## Additional Resources

- Full release guide: `docs/GITHUB_RELEASES_GUIDE.md`
- Quick start: `GITHUB_RELEASES_QUICK_START.md`

