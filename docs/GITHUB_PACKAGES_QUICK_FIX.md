# 🔧 Quick Fix: GitHub Packages 403 Error

## The Problem
```
npm error 403 403 Forbidden - PUT https://npm.pkg.github.com/@shanle1117%2ffaix-chatbot
npm error 403 Permission permission_denied: create_package
```

## ✅ Solution Steps

### Step 1: Create/Verify GitHub Token

1. Go to: **https://github.com/settings/tokens**
2. Click **"Generate new token (classic)"**
3. Name it: `GitHub Packages Token`
4. Select these scopes:
   - ✅ **write:packages** (REQUIRED)
   - ✅ **read:packages** (REQUIRED)
   - ✅ **repo** (REQUIRED if repository is private)
   - ✅ **delete:packages** (optional)
5. Click **"Generate token"**
6. **COPY THE TOKEN** (you won't see it again!)

### Step 2: Set Token as Environment Variable

**Windows CMD:**
```cmd
set GITHUB_TOKEN=ghp_your_token_here
```

**Windows PowerShell:**
```powershell
$env:GITHUB_TOKEN="ghp_your_token_here"
```

**Linux/Mac:**
```bash
export GITHUB_TOKEN=ghp_your_token_here
```

**To make it permanent (Windows):**
```cmd
setx GITHUB_TOKEN "ghp_your_token_here"
```

**To make it permanent (Linux/Mac):**
```bash
echo 'export GITHUB_TOKEN=ghp_your_token_here' >> ~/.bashrc
source ~/.bashrc
```

### Step 3: Verify Authentication

**Option A: Use the check script**
```bash
npm run setup:github
```

**Option B: Manual check**
```bash
npm whoami --registry=https://npm.pkg.github.com
```
Should return your GitHub username (e.g., `shanle1117`)

### Step 4: Try Publishing Again

```bash
npm run build
npm run publish:github
```

## 🔍 Alternative: Use npm login

If environment variable doesn't work:

```bash
npm login --scope=@shanle1117 --registry=https://npm.pkg.github.com
```

When prompted:
- **Username**: Your GitHub username (e.g., `shanle1117`)
- **Password**: Your GitHub Personal Access Token (NOT your GitHub password!)
- **Email**: Your GitHub email

Then try publishing:
```bash
npm run publish:github
```

## ❌ Still Not Working?

### Check These:

1. **Token Permissions**
   - Go to https://github.com/settings/tokens
   - Verify token has `write:packages` scope
   - If missing, create a new token

2. **Package Scope**
   - Check `package.json` - name should be `@shanle1117/faix-chatbot`
   - The `@shanle1117` must match your GitHub username exactly

3. **Repository Access**
   - If repo is private, token MUST have `repo` scope
   - Verify you have write access to the repository

4. **Token Format**
   - GitHub tokens start with `ghp_` (classic) or `github_pat_` (fine-grained)
   - Should be 40+ characters long

5. **Environment Variable**
   ```bash
   # Check if set
   echo %GITHUB_TOKEN%  # Windows CMD
   echo $env:GITHUB_TOKEN  # PowerShell
   echo $GITHUB_TOKEN  # Linux/Mac
   ```

## 📝 Quick Test Script

Run this to test everything:
```bash
npm run test-auth
```

Should output your GitHub username if authentication works.

## 🆘 Need More Help?

See full documentation: `docs/GITHUB_PACKAGES_SETUP.md`

