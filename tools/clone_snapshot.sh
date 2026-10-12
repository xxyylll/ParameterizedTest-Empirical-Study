#!/bin/bash
#
# Re-create the analysed source snapshot from corpus/snapshot_commits.csv.
# Each repository is fetched at exactly the HEAD commit that was analysed (shallow, one commit).
#
# Usage:
#   tools/clone_snapshot.sh <dest-dir> [project-list.txt]
#
#   <dest-dir>          where the repositories go, e.g. data/ssd/apache-projects
#                       (that is $PT_SSD/apache-projects, the layout paths.py expects)
#   project-list.txt    optional: one repo_dir per line, e.g. corpus/rq3_corpus_46.txt;
#                       default is all 243 repositories
#
# Afterwards, extract aaa_traces.tar.gz from the data archive into the parent of <dest-dir>
# so that each repository gets its AAA/ directory.

set -e
set -o pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${1:?usage: tools/clone_snapshot.sh <dest-dir> [project-list.txt]}"
LIST="$2"
mkdir -p "$DEST"

tail -n +2 "$ROOT/corpus/snapshot_commits.csv" | while IFS=, read -r repo url commit _date; do
    if [[ -n "$LIST" ]] && ! grep -qix "$repo" "$LIST"; then
        continue
    fi
    dir="$DEST/$repo"
    if [[ -d "$dir/.git" ]] && [[ "$(git -C "$dir" rev-parse HEAD 2>/dev/null)" == "$commit" ]]; then
        echo "ok    $repo"
        continue
    fi
    echo "fetch $repo @ ${commit:0:10}"
    rm -rf "$dir"
    git init -q "$dir"
    git -C "$dir" remote add origin "$url"
    git -C "$dir" fetch -q --depth 1 origin "$commit"
    git -C "$dir" checkout -q FETCH_HEAD
done
