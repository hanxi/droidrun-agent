#!/usr/bin/env bash
# Usage:
#   ./bump_version.sh          # bump patch version (0.1.0 -> 0.1.1)
#   ./bump_version.sh minor    # bump minor version (0.1.0 -> 0.2.0)
#   ./bump_version.sh major    # bump major version (0.1.0 -> 1.0.0)

set -euo pipefail

BUMP_TYPE="${1:-patch}"
PYPROJECT="pyproject.toml"

# Extract current version from pyproject.toml
current_version=$(grep -E '^version = ' "$PYPROJECT" | sed 's/version = "\(.*\)"/\1/')

if [[ -z "$current_version" ]]; then
  echo "Error: could not find version in $PYPROJECT" >&2
  exit 1
fi

IFS='.' read -r major minor patch <<< "$current_version"

case "$BUMP_TYPE" in
  major)
    major=$((major + 1))
    minor=0
    patch=0
    ;;
  minor)
    minor=$((minor + 1))
    patch=0
    ;;
  patch)
    patch=$((patch + 1))
    ;;
  *)
    echo "Error: unknown bump type '$BUMP_TYPE'. Use: patch | minor | major" >&2
    exit 1
    ;;
esac

new_version="${major}.${minor}.${patch}"
new_tag="v${new_version}"

echo "Bumping version: $current_version -> $new_version"

# Update version in pyproject.toml
sed -i.bak "s/^version = \"${current_version}\"/version = \"${new_version}\"/" "$PYPROJECT"
rm -f "${PYPROJECT}.bak"

# Commit and push the version bump
git add "$PYPROJECT"
git commit -m "chore: bump version to $new_version"
git push

# Create and push the tag
git tag "$new_tag"
git push origin "$new_tag"

echo "Done! Tag $new_tag pushed — GitHub Actions will publish to PyPI."
