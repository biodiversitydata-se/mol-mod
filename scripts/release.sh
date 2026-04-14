#!/usr/bin/env bash

# Automates releases: builds Docker images, creates a GitHub release,
# and tags/pushes images with a consistent version across services.

set -e

IMAGES="bioatlas/molmod-postgrest bioatlas/molmod-blast bioatlas/molmod"
DRY_RUN=false
ARG=""

if [ "${1:-}" = "--dry-run" ]; then
  DRY_RUN=true
  ARG="${2:-}"
else
  ARG="${1:-}"
fi

LATEST=$(gh release view --json tagName -q .tagName 2>/dev/null || echo "v0.0.0")
LATEST=${LATEST#v}

bump_version() {
  local version=$1
  local part=$2
  IFS='.' read -r major minor patch <<< "$version"

  case "$part" in
    major)
      echo "$((major + 1)).0.0"
      ;;
    minor)
      echo "${major}.$((minor + 1)).0"
      ;;
    patch)
      echo "${major}.${minor}.$((patch + 1))"
      ;;
    *)
      echo "Invalid bump type: $part" >&2
      exit 1
      ;;
  esac
}

if [ -z "$ARG" ]; then
  VERSION=$(bump_version "$LATEST" patch)
elif [ "$ARG" = "major" ] || [ "$ARG" = "minor" ] || [ "$ARG" = "patch" ]; then
  VERSION=$(bump_version "$LATEST" "$ARG")
else
  VERSION=$ARG
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
run_cmd gh release create "v${VERSION}" --generate-notes

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
