#!/usr/bin/env bash
set -euo pipefail

while read -r name url; do
  [[ -z "${name:-}" || "${name:0:1}" == "#" ]] && continue

  echo "=== $name ==="

  if [[ -z "${url:-}" ]]; then
    echo "⚠️  No URL provided for project '$name'. Skipping."
    continue
  fi

  echo "Cloning $name from $url ..."
  rm -rf "$name"
  # show clone progress/errors so user can see activity
  if ! git clone "$url" "$name"; then
    echo "❌ clone $name failed"
    continue
  fi

  ./release_generator.sh "$name"           # 产出 releases/$name.txt
  python3 select_release.py                # selected_releases/select_*.txt
  ./checkout_and_parser.sh "$name"         # run parser，parser_result/<name>/<tag>/output.json

  rm -rf "$name"                           # delect repo to save space
done < projects.txt

python3 analyzer.py                        # summary + trend charts
echo "✅ all done"
