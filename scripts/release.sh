#!/usr/bin/env bash

# ------------------------------------------------------------------------------
# Release script
#
# Usage:
#   ./release.sh [major|minor|patch|<version>] [--notes "text"] [--notes-file FILE] [--dry-run]
#
# Examples:
#   ./release.sh                 # bump patch version
#   ./release.sh minor           # bump minor version
#   ./release.sh 2.1.0           # set explicit version
#
#   ./release.sh minor --notes "Short release summary"
#   ./release.sh minor --notes-file RELEASE_NOTES.md
#
#   ./release.sh minor --dry-run
#
# Notes:
# - Always builds from master branch
# - Uses docker-compose.prod.yml for building images
# - --notes overrides auto-generated notes
# - --notes-file is recommended for longer release notes
# ------------------------------------------------------------------------------

set -e

IMAGES="bioatlas/molmod-postgrest bioatlas/molmod-blast bioatlas/molmod"
DRY_RUN=false
BUMP_ARG=""
NOTES=""
NOTES_FILE=""

# Parse args
while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --notes)
      NOTES="$2"
      shift 2
      ;;
    --notes-file)
      NOTES_FILE="$2"
      shift 2
      ;;
    major|minor|patch)
      BUMP_ARG="$1"
      shift
      ;;
    *)
      # explicit version
      BUMP_ARG="$1"
      shift
      ;;
  esac
done

LATEST=$(gh release view --json tagName -q .tagName 2>/dev/null || echo "v0.0.0")
LATEST=${LATEST#v}

bump_version() {
  local version=$1
  local part=$2
  IFS='.' read -r major minor patch <<< "$version"

  case "$part" in
    major) echo "$((major + 1)).0.0" ;;
    minor) echo "${major}.$((minor + 1)).0" ;;
    patch) echo "${major}.${minor}.$((patch + 1))" ;;
    *) echo "Invalid bump type: $part" >&2; exit 1 ;;
  esac
}

if [ -z "$BUMP_ARG" ]; then
  VERSION=$(bump_version "$LATEST" patch)
elif [[ "$BUMP_ARG" =~ ^(major|minor|patch)$ ]]; then
  VERSION=$(bump_version "$LATEST" "$BUMP_ARG")
else
  VERSION=$BUMP_ARG
fi

run_cmd() {
  echo "+ $*"
  if [ "$DRY_RUN" = false ]; then
    "$@"
  fi
}

echo "Latest release: $LATEST"
echo "New release: $VERSION"

run_cmd git checkout master
run_cmd git pull
run_cmd docker compose -f docker-compose.prod.yml build --no-cache

# Build release command
RELEASE_CMD=(gh release create "v${VERSION}" --generate-notes)

if [ -n "$NOTES" ]; then
  RELEASE_CMD+=(--notes "$NOTES")
elif [ -n "$NOTES_FILE" ]; then
  RELEASE_CMD+=(--notes-file "$NOTES_FILE")
fi

run_cmd "${RELEASE_CMD[@]}"

for img in $IMAGES; do
  echo "Processing $img..."
  run_cmd docker tag "${img}:latest" "${img}:${VERSION}"
  run_cmd docker push "${img}:latest"
  run_cmd docker push "${img}:${VERSION}"
done

if [ "$DRY_RUN" = true ]; then
  echo "Dry run complete. No release was created and no images were pushed."
else
  echo "Release $VERSION done"
fi
