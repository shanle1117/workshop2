# GitHub Packages Setup Guide

This guide explains how to publish and use the FAIX Chatbot package via GitHub Packages.

## Prerequisites

1. A GitHub account
2. Node.js and npm installed
3. A GitHub Personal Access Token (PAT) with `write:packages` and `read:packages` permissions

## Setup

### 1. Create GitHub Personal Access Token

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate a new token with the following permissions:
   - `write:packages` - Upload packages to GitHub Packages
   - `read:packages` - Download packages from GitHub Packages
   - `delete:packages` - Delete packages (optional)
   - `repo` - Full control of private repositories (if your repo is private)

### 2. Configure npm Authentication

#### Option A: Using .npmrc file (Recommended for local development)

The `.npmrc` file is already configured. You just need to set your GitHub token:

**On Windows (PowerShell):**
```powershell
$env:GITHUB_TOKEN="your_github_token_here"
```

**On Windows (CMD):**
```cmd
set GITHUB_TOKEN=your_github_token_here
```

**On Linux/Mac:**
```bash
export GITHUB_TOKEN=your_github_token_here
```

#### Option B: Using npm login

```bash
npm login --scope=@shanle1117 --registry=https://npm.pkg.github.com
```

When prompted:
- Username: Your GitHub username
- Password: Your GitHub Personal Access Token (not your GitHub password)
- Email: Your GitHub email

### 3. Verify Configuration

Check that your `.npmrc` file exists and contains:
```
@shanle1117:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=${GITHUB_TOKEN}
```

## Publishing the Package

### Manual Publishing

1. **Update version** in `package.json`:
   ```json
   "version": "1.0.1"
   ```

2. **Build the package**:
   ```bash
   npm run build
   ```

3. **Publish to GitHub Packages**:
   ```bash
   npm publish
   ```
   
   Or use the npm script:
   ```bash
   npm run publish:github
   ```

### Automated Publishing via GitHub Actions

The package will automatically publish when:
- A new GitHub Release is created
- The workflow is manually triggered via GitHub Actions

To trigger manually:
1. Go to Actions tab in GitHub
2. Select "Publish Package to GitHub Packages"
3. Click "Run workflow"
4. Enter the version number
5. Click "Run workflow"

## Installing the Package

### In Another Project

1. **Create/update `.npmrc`** in your project root:
   ```
   @shanle1117:registry=https://npm.pkg.github.com
   //npm.pkg.github.com/:_authToken=${GITHUB_TOKEN}
   ```

2. **Set your GitHub token** (same as above)

3. **Install the package**:
   ```bash
   npm install @shanle1117/faix-chatbot
   ```

### Using in package.json

```json
{
  "dependencies": {
    "@shanle1117/faix-chatbot": "^1.0.0"
  }
}
```

## Package Structure

The published package includes:
- Built React component (`frontend/dist/chatbot-react.js`)
- Source files
- Package metadata

## Version Management

Follow [Semantic Versioning](https://semver.org/):
- **MAJOR** (1.0.0): Breaking changes
- **MINOR** (0.1.0): New features (backward compatible)
- **PATCH** (0.0.1): Bug fixes (backward compatible)

## Troubleshooting

### Error: "You must provide a GitHub Personal Access Token"

**Solution**: Make sure `GITHUB_TOKEN` environment variable is set:
```bash
echo $GITHUB_TOKEN  # Linux/Mac
echo %GITHUB_TOKEN% # Windows CMD
```

### Error: "403 Forbidden" or "Permission permission_denied: create_package"

This is the most common error. Try these solutions:

**Solution 1: Verify Token Permissions**
- Go to https://github.com/settings/tokens
- Check that your token has these scopes:
  - ✅ `write:packages` (required)
  - ✅ `read:packages` (required)
  - ✅ `repo` (required if repository is private)
- If missing, create a new token with all required permissions

**Solution 2: Verify Token is Set**
```bash
# Windows CMD
echo %GITHUB_TOKEN%

# Windows PowerShell
echo $env:GITHUB_TOKEN

# Linux/Mac
echo $GITHUB_TOKEN
```
If empty, set it:
```bash
# Windows CMD
set GITHUB_TOKEN=your_token_here

# Windows PowerShell
$env:GITHUB_TOKEN="your_token_here"

# Linux/Mac
export GITHUB_TOKEN=your_token_here
```

**Solution 3: Test Authentication**
```bash
npm whoami --registry=https://npm.pkg.github.com
```
Should return your GitHub username. If not, token is invalid or not set.

**Solution 4: Use npm login Instead**
If environment variable doesn't work, try interactive login:
```bash
npm login --scope=@shanle1117 --registry=https://npm.pkg.github.com
```
- Username: Your GitHub username
- Password: Your GitHub Personal Access Token (NOT your GitHub password)
- Email: Your GitHub email

**Solution 5: Check Package Scope**
Ensure package name in `package.json` matches your GitHub username:
```json
"name": "@shanle1117/faix-chatbot"
```
The `@shanle1117` must match your GitHub username exactly.

**Solution 6: Repository Access**
If your repository is private, ensure:
- Token has `repo` scope
- You have write access to the repository

### Error: "404 Not Found"

**Solution**:
- Verify the package name in `package.json` starts with `@shanle1117/`
- Check that the repository exists and you have access
- Ensure `.npmrc` is configured correctly

### Package Not Found After Publishing

**Solution**:
- Wait a few minutes for GitHub Packages to index
- Check the Packages tab on your GitHub profile
- Verify the package name and version

## Viewing Published Packages

1. Go to your GitHub profile
2. Click on "Packages" tab
3. Find `@shanle1117/faix-chatbot`

## CI/CD Integration

The GitHub Actions workflow automatically:
- Builds the package on push/PR
- Publishes to GitHub Packages on release

See `.github/workflows/publish-package.yml` for details.

## Security Best Practices

1. **Never commit tokens** to version control
2. **Use environment variables** for tokens
3. **Use GitHub Secrets** in Actions workflows
4. **Rotate tokens** regularly
5. **Use least privilege** - only grant necessary permissions

## Additional Resources

- [GitHub Packages Documentation](https://docs.github.com/en/packages)
- [npm Configuration Guide](https://docs.npmjs.com/cli/v8/configuring-npm/npmrc)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

