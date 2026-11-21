#!/usr/bin/env bash
# Rewrite the block between the releases markers in README.md with the newest
# published release of each public repository that an owner in OWNERS holds,
# newest first. Drafts and prereleases are left out. Needs gh and jq, with
# GH_TOKEN set.
set -euo pipefail

owners="${OWNERS:-pithecene}"
limit="${LIMIT:-3}"
readme="${README:-README.md}"

# A damaged marker pair must never consume the rest of the profile.
if ! awk '
  /^<!-- releases:start -->$/ { starts++; start = NR }
  /^<!-- releases:end -->$/   { ends++; end = NR }
  END { exit !(starts == 1 && ends == 1 && start < end) }
' "$readme"; then
  printf 'expected exactly one ordered releases marker pair in %s\n' "$readme" >&2
  exit 1
fi

rows="$(
  for owner in $owners; do
    gh api --paginate "users/${owner}/repos?type=owner&per_page=100" \
      --jq '.[] | select(.private | not) | select(.archived | not) | .full_name' || exit 1
  done | while read -r repo; do
    gh api "repos/${repo}/releases?per_page=20" \
      --jq "[.[] | select((.draft or .prerelease) | not)] | first // empty
        | [.published_at, \"${repo##*/}\", .tag_name, .html_url] | @tsv" || exit 1
  done | sort -r | head -n "$limit"
)"

block="$(printf '%s\n' "$rows" | awk -F'\t' 'NF == 4 {
  printf "- [%s %s](%s) · %s\n", $2, $3, $4, substr($1, 1, 10)
}')"
if [ -z "$block" ]; then
  echo "no releases found; leaving ${readme} unchanged" >&2
  exit 0
fi

# A sibling temporary file keeps replacement atomic and preserves the mode.
temp_readme="$(mktemp "${readme}.tmp.XXXXXX")"
trap 'rm -f "$temp_readme"' EXIT
cp -p "$readme" "$temp_readme"

# Replace everything between the validated markers, keeping the markers.
BLOCK="$block" awk '
  /^<!-- releases:start -->$/ { print; print ENVIRON["BLOCK"]; skip = 1; next }
  /^<!-- releases:end -->$/   { skip = 0 }
  !skip
' "$readme" > "$temp_readme"
mv "$temp_readme" "$readme"
trap - EXIT
