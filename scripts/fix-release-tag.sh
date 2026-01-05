#!/bin/bash
# Quick script to fix release tag issues

if [ -z "$1" ]; then
    echo "Usage: ./fix-release-tag.sh <version>"
    echo "Example: ./fix-release-tag.sh 1.0.1"
    exit 1
fi

VERSION=$1

echo "========================================"
echo "Fix Release Tag"
echo "========================================"
echo ""
echo "Fixing tag v${VERSION}..."
echo ""

# Delete local tag if exists
echo "Deleting local tag..."
if git rev-parse "v${VERSION}" >/dev/null 2>&1; then
    git tag -d "v${VERSION}"
    echo "Deleted local tag v${VERSION}"
else
    echo "Local tag v${VERSION} doesn't exist"
fi

# Delete remote tag if exists
echo ""
echo "Deleting remote tag..."
if git ls-remote --tags origin "v${VERSION}" >/dev/null 2>&1; then
    git push origin --delete "v${VERSION}"
    echo "Deleted remote tag v${VERSION}"
else
    echo "Remote tag v${VERSION} doesn't exist or already deleted"
fi

echo ""
echo "========================================"
echo "Tag cleanup complete!"
echo "========================================"
echo ""
echo "You can now:"
echo "1. Run: ./scripts/create-release.sh"
echo "2. Or manually create tag: git tag -a v${VERSION} -m \"Release v${VERSION}\""
echo "3. Push tag: git push origin v${VERSION}"
echo ""


