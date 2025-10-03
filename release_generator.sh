#!/usr/bin/env bash
set -euo pipefail

name="$1"                 # project name
OUTDIR="${2:-releases}"   # output dir with default "releases"
mkdir -p "$OUTDIR"

echo "Extracting tags for $name ..."
(
  cd "$name"
  git for-each-ref --sort=-creatordate \
    --format='%(refname:short) %(creatordate:short)' refs/tags \
  | awk 'BEGIN{IGNORECASE=1}
         $1 !~ /(alpha|beta|rc|snapshot|milestone|test|dev|preview)/ &&
         $1 ~ /(^|[\/-])v?[0-9]+(\.[0-9]+){1,3}(-incubating)?$/'
) > "$OUTDIR/$name.txt"

echo "✅ $OUTDIR/$name.txt"
