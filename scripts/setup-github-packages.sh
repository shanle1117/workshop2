#!/bin/bash
# Setup script for GitHub Packages authentication on Linux/Mac

echo "========================================"
echo "GitHub Packages Setup"
echo "========================================"
echo ""

# Check if GITHUB_TOKEN is set
if [ -z "$GITHUB_TOKEN" ]; then
    echo "ERROR: GITHUB_TOKEN environment variable is not set!"
    echo ""
    echo "Please follow these steps:"
    echo "1. Go to: https://github.com/settings/tokens"
    echo "2. Click 'Generate new token (classic)'"
    echo "3. Give it a name like 'GitHub Packages Token'"
    echo "4. Select these scopes:"
    echo "   - write:packages"
    echo "   - read:packages"
    echo "   - delete:packages (optional)"
    echo "   - repo (if repository is private)"
    echo "5. Click 'Generate token'"
    echo "6. Copy the token"
    echo ""
    echo "Then run this command:"
    echo "  export GITHUB_TOKEN=your_token_here"
    echo ""
    echo "Or add to ~/.bashrc or ~/.zshrc:"
    echo "  echo 'export GITHUB_TOKEN=your_token_here' >> ~/.bashrc"
    echo ""
    exit 1
fi

echo "GITHUB_TOKEN is set."
echo ""

# Verify token format (should be 40+ characters)
if [ ${#GITHUB_TOKEN} -lt 40 ]; then
    echo "WARNING: Token seems too short. Please verify it's correct."
    echo ""
fi

echo "Testing authentication..."
npm whoami --registry=https://npm.pkg.github.com
if [ $? -ne 0 ]; then
    echo ""
    echo "Authentication failed. Please check:"
    echo "1. Token has correct permissions (write:packages, read:packages)"
    echo "2. Token is not expired"
    echo "3. Username matches the package scope (@shanle1117)"
    echo ""
    exit 1
fi

echo ""
echo "========================================"
echo "Setup complete! You can now publish with:"
echo "  npm run publish:github"
echo "========================================"

