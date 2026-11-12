#!/usr/bin/env bash
# Copies this scaffold into your existing clone WITHOUT overwriting anything.
# Usage: bash install-into-repo.sh /path/to/your/RUNWAY_X-MSME
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="${1:?Usage: bash install-into-repo.sh /path/to/your/RUNWAY_X-MSME}"
[ -d "$DEST" ] || { echo "Not a directory: $DEST"; exit 1; }

copied=0; skipped=0
while IFS= read -r -d '' f; do
  rel="${f#"$SRC"/}"
  case "$rel" in install-into-repo.sh) continue;; esac
  if [ -e "$DEST/$rel" ]; then
    echo "SKIP (exists): $rel"; skipped=$((skipped+1))
  else
    mkdir -p "$(dirname "$DEST/$rel")"; cp "$f" "$DEST/$rel"
    echo "ADD:           $rel"; copied=$((copied+1))
  fi
done < <(find "$SRC" -type f -not -path '*/node_modules/*' -print0)

echo; echo "Added $copied file(s), skipped $skipped existing. Nothing was committed or pushed."
echo "Review with: cd \"$DEST\" && git status"
