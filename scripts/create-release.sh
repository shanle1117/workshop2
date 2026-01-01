#!/bin/bash
# Script to create a GitHub release

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}GitHub Release Creator${NC}"
echo -e "${GREEN}========================================${NC}\n"

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}Error: GitHub CLI (gh) is not installed.${NC}"
    echo "Install it from: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo -e "${YELLOW}Not authenticated. Please run: gh auth login${NC}"
    exit 1
fi

# Get current version from package.json
CURRENT_VERSION=$(node -p "require('./package.json').version")
echo "Current version: ${CURRENT_VERSION}"

# Prompt for new version
read -p "Enter new version (current: ${CURRENT_VERSION}): " NEW_VERSION

if [ -z "$NEW_VERSION" ]; then
    echo -e "${RED}Error: Version is required${NC}"
    exit 1
fi

# Validate version format (semver)
if ! [[ $NEW_VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+)?$ ]]; then
    echo -e "${RED}Error: Invalid version format. Use semantic versioning (e.g., 1.0.0)${NC}"
    exit 1
fi

# Prompt for release notes
echo ""
read -p "Enter release notes (optional): " RELEASE_NOTES

# Update package.json version
echo -e "\n${YELLOW}Updating package.json...${NC}"
npm version $NEW_VERSION --no-git-tag-version

# Build package
echo -e "${YELLOW}Building package...${NC}"
npm run build

# Create git tag
echo -e "${YELLOW}Creating git tag v${NEW_VERSION}...${NC}"
git add package.json
git commit -m "chore: bump version to ${NEW_VERSION}" || echo "No changes to commit"
git tag -a "v${NEW_VERSION}" -m "Release v${NEW_VERSION}"

# Push tag
read -p "Push tag to GitHub? (y/n): " PUSH_TAG
if [ "$PUSH_TAG" = "y" ] || [ "$PUSH_TAG" = "Y" ]; then
    echo -e "${YELLOW}Pushing tag...${NC}"
    git push origin "v${NEW_VERSION}"
    git push origin HEAD
fi

# Create release
echo -e "\n${YELLOW}Creating GitHub release...${NC}"

if [ -z "$RELEASE_NOTES" ]; then
    RELEASE_NOTES="Release v${NEW_VERSION}"
fi

gh release create "v${NEW_VERSION}" \
    --title "Release v${NEW_VERSION}" \
    --notes "$RELEASE_NOTES" \
    --target "$(git rev-parse --abbrev-ref HEAD)"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Release created successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Release: https://github.com/shanle1117/workshop2/releases/tag/v${NEW_VERSION}"
echo ""
echo "The package will be automatically published to GitHub Packages."

