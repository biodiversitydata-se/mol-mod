#!/bin/bash
# Zip datasets under Imported/ for reproducibility.
# Only files in input/ and R scripts (*.R) are included.
# Run from the imports root (the folder containing Imported/), or set
# ASV_IMPORTS_DIR to that folder. Zips are written to <root>/zipped-import/.
# Without arguments: zips all datasets.
# With one argument: zips only that dataset (name under Imported/, or path).
set -euo pipefail

root="$(cd "${ASV_IMPORTS_DIR:-$PWD}" && pwd)"
if [[ ! -d "$root/Imported" ]]; then
  echo "Error: no Imported/ folder in $root. Run from the imports root or set ASV_IMPORTS_DIR." >&2
  exit 1
fi
cd "$root"

mkdir -p zipped-import

zip_one() {
  local d="$1"
  [ -d "$d" ] || { echo "Skipping: folder missing: $d" >&2; return 1; }
  local base dest
  base="$(basename "$d")"
  dest="$root/zipped-import/${base}.zip"

  (
    cd "$d"
    rm -f "$dest"

    # All files in input/ (excluding .DS_Store)
    if [ -d input ]; then
      zip -qr "$dest" input -x '*/.DS_Store'
    else
      echo "Warning: no input/ folder in ${base}" >&2
    fi

    # All R scripts (any depth), except under output/ or .Rproj.user/
    find . -type f -name '*.R' \
      ! -path './output/*' ! -path './.Rproj.user/*' \
      -exec zip -q "$dest" {} +
  )
  echo "Zipped ${base} -> zipped-import/${base}.zip"
}

if [[ $# -eq 0 ]]; then
  # Zip all datasets
  shopt -s nullglob
  for d in Imported/*/ ; do
    zip_one "$d"
  done
elif [[ $# -eq 1 ]]; then
  # Zip a specific dataset (name or path)
  target="$1"
  if [[ -d "Imported/$target" ]]; then
    zip_one "Imported/$target"
  elif [[ -d "$target" ]]; then
    zip_one "$target"
  else
    echo "Error: no dataset '$target' found under Imported/." >&2
    echo "Usage: $0 [datasetName]" >&2
    exit 1
  fi
else
  echo "Usage: $0 [datasetName]" >&2
  exit 2
fi

echo "Done."
