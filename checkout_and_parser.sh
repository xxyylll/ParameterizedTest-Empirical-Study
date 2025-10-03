#!/usr/bin/env bash
set -euo pipefail

SELECTED_RELEASES_DIR="selected_releases"
PARSER_RESULT_DIR="parser_result"
PARSER_JAR="${PARSER_JAR:-/Users/immortal/test-parser/target/test-parser-1.0-SNAPSHOT-jar-with-dependencies.jar}"

# Ensure the parser JAR exists
if [ ! -f "$PARSER_JAR" ]; then
  echo "❌ Parser JAR not found at $PARSER_JAR. Please set PARSER_JAR to the correct path."
  exit 1
fi

mkdir -p "$PARSER_RESULT_DIR"

# Optional first argument: a single project name to process (only its selected file)
PROJECT_ARG="${1:-}"
files=()
if [[ -n "$PROJECT_ARG" ]]; then
  sel="$SELECTED_RELEASES_DIR/select_${PROJECT_ARG}.txt"
  if [[ ! -f "$sel" ]]; then
    echo "⚠️  No selected releases file for project '$PROJECT_ARG' at $sel. Nothing to do."
    exit 0
  fi
  files=("$sel")
else
  files=("$SELECTED_RELEASES_DIR"/select_*.txt)
fi

for selected_file in "${files[@]}"; do
  # skip non-existent globs
  [[ -f "$selected_file" ]] || continue

  project_name=$(basename "$selected_file" | sed 's/^select_//;s/\.txt$//')
  repo_dir="$project_name"

  if [ ! -d "$repo_dir/.git" ]; then
    echo "❌ Repository directory $repo_dir does not exist. Skipping."
    continue
  fi

  echo "Processing project: $project_name"

  # Fetch latest tags
  git -C "$repo_dir" fetch --tags --prune --prune-tags --quiet || true

  # TAG DATE
  while read -r release_id release_date; do
    [ -z "$release_id" ] && continue
    echo "Checking out release $release_id for $project_name..."

    # checkout selected tag
    if ! git -C "$repo_dir" checkout --quiet "$release_id"; then
      echo "❌ Failed to checkout $release_id for $project_name. Skipping."
      continue
    fi

    # structure: parser_result/<project>/<safe_tag>/output.json
    safe_tag="${release_id//\//_}"
    dest_dir="$PARSER_RESULT_DIR/$project_name/$safe_tag"
    mkdir -p "$dest_dir"
    output_file="$dest_dir/output.json"

    echo "Running parser for $project_name at $release_id..."
    if ! java -jar "$PARSER_JAR" "$repo_dir" "$output_file" >"$dest_dir/parser.log" 2>&1; then
      echo "❌ Parser failed for $project_name at $release_id. See $dest_dir/parser.log"
      continue
    fi

    echo "✅ Results saved to $output_file"
  done < "$selected_file"

done

echo "All projects processed."
