#!/usr/bin/env bash
# Rewrite the block between the releases markers in README.md with the newest
# published release of each public repository that an owner in OWNERS holds,
# newest first. Drafts and prereleases are left out. Needs gh and jq, with
# GH_TOKEN set.
set -euo pipefail

owners="${OWNERS:-pithecene}"
limit="${LIMIT:-8}"
readme="${README:-README.md}"

rows="$(
  for owner in $owners; do
    gh api --paginate "users/${owner}/repos?type=owner&per_page=100" \
      --jq '.[] | select(.private | not) | select(.archived | not) | .full_name'
  done | while read -r repo; do
    gh api "repos/${repo}/releases?per_page=20" \
      --jq "[.[] | select((.draft or .prerelease) | not)] | first // empty
        | [.published_at, \"${repo##*/}\", .tag_name, .html_url] | @tsv"
  done | sort -r | head -n "$limit"
)"

block="$(printf '%s\n' "$rows" | awk -F'\t' 'NF == 4 {
  printf "- [%s %s](%s) · %s\n", $2, $3, $4, substr($1, 1, 10)
}')"
if [ -z "$block" ]; then
  echo "no releases found; leaving ${readme} unchanged" >&2
  exit 0
fi

# Replace everything between the markers, keeping the markers.
BLOCK="$block" awk '
  /<!-- releases:start -->/ { print; print ENVIRON["BLOCK"]; skip = 1; next }
  /<!-- releases:end -->/   { skip = 0 }
  !skip
' "$readme" > "${readme}.tmp"
mv "${readme}.tmp" "$readme"
