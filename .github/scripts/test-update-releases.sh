#!/usr/bin/env bash
# Exercise the updater offline with real jq and a mock gh executable.
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
updater="$script_dir/update-releases.sh"
work="$(mktemp -d)"
trap 'rm -rf -- "$work"' EXIT
mkdir "$work/bin"

export PATH="$work/bin:$PATH" GH_TOKEN=offline-test OWNERS=fixture
export README="$work/Profile README.md" MOCK_DATA="$work/data.json"
export MOCK_LOG="$work/calls" MOCK_FAIL='' MOCK_EMPTY=0
unset LIMIT

jq -n '
  def release($name; $date): {
    draft: false, prerelease: false, tag_name: "v1.0.0",
    published_at: ($date + "T12:00:00Z"),
    html_url: ("https://example.test/" + $name + "/v1.0.0")
  };
  {
    repos: ((["third", "oldest", "newest", "second"] | map({
      full_name: ("fixture/" + .), private: false, archived: false
    })) + [
      {full_name: "fixture/private", private: true, archived: false},
      {full_name: "fixture/archived", private: false, archived: true}
    ]),
    releases: {
      third: [release("third"; "2025-02-01")],
      oldest: [release("oldest"; "2025-01-01")],
      newest: [
        (release("newest"; "2025-06-01") | .draft = true),
        (release("newest"; "2025-05-01") | .prerelease = true),
        release("newest"; "2025-04-01"),
        release("newest"; "2025-01-01")
      ],
      second: [release("second"; "2025-03-01")]
    }
  }
' > "$MOCK_DATA"

cat > "$work/bin/gh" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$MOCK_LOG"
[[ "${1:-}" == api ]] || exit 64
shift
if [[ "${1:-}" == --paginate ]]; then shift; fi
[[ $# == 3 && "$2" == --jq ]] || exit 64
endpoint="$1"
filter="$3"
[[ "$endpoint" != "$MOCK_FAIL" ]] || exit 1
case "$endpoint" in
  'users/fixture/repos?type=owner&per_page=100')
    jq '.repos' "$MOCK_DATA"
    ;;
  repos/fixture/*/releases\?*)
    name="${endpoint#repos/fixture/}"
    name="${name%%/*}"
    if [[ "$MOCK_EMPTY" == 1 ]]; then
      printf '[]\n'
    else
      jq -e --arg name "$name" '.releases[$name] // error("unexpected repository")' "$MOCK_DATA"
    fi
    ;;
  *) exit 64 ;;
esac | jq -r "$filter"
MOCK
chmod +x "$work/bin/gh"

cat > "$work/original" <<'README'
Profile introduction.
<!-- releases:start -->
Existing releases.
<!-- releases:end -->
Profile footer.
README

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  cat "$work/output" >&2
  exit 1
}

run_updater() {
  "$updater" > "$work/output" 2>&1
}

expect_failure() {
  cp "$README" "$work/before"
  if run_updater; then fail "$1 unexpectedly succeeded"; fi
  cmp -s "$README" "$work/before" || fail "$1 changed the README"
}

cp "$work/original" "$README"
chmod 640 "$README"
run_updater || fail 'ordinary update'
cat > "$work/expected" <<'README'
Profile introduction.
<!-- releases:start -->
- [newest v1.0.0](https://example.test/newest/v1.0.0) · 2025-04-01
- [second v1.0.0](https://example.test/second/v1.0.0) · 2025-03-01
- [third v1.0.0](https://example.test/third/v1.0.0) · 2025-02-01
<!-- releases:end -->
Profile footer.
README
cmp -s "$README" "$work/expected" || fail 'newest three stable releases and surrounding text'
mode="$(stat -c '%a' "$README" 2>/dev/null || stat -f '%Lp' "$README")"
[[ "$mode" == 640 ]] || fail 'README mode preservation'
run_updater || fail 'second update'
cmp -s "$README" "$work/expected" || fail 'idempotence'

cp "$work/original" "$README"
MOCK_EMPTY=1 run_updater || fail 'empty release list'
cmp -s "$README" "$work/original" || fail 'empty releases changed the README'

for MOCK_FAIL in \
  'users/fixture/repos?type=owner&per_page=100' \
  'repos/fixture/third/releases?per_page=20' \
  'repos/fixture/second/releases?per_page=20'; do
  expect_failure "API failure at $MOCK_FAIL"
done
MOCK_FAIL=''

start='<!-- releases:start -->'
end='<!-- releases:end -->'
for marker_case in missing-start missing-end duplicate-start duplicate-end reversed; do
  case "$marker_case" in
    missing-start) printf '%s\n' "$end" ;;
    missing-end) printf '%s\n' "$start" ;;
    duplicate-start) printf '%s\n' "$start" "$start" "$end" ;;
    duplicate-end) printf '%s\n' "$start" "$end" "$end" ;;
    reversed) printf '%s\n' "$end" "$start" ;;
  esac > "$README"
  : > "$MOCK_LOG"
  expect_failure "$marker_case markers"
  [[ ! -s "$MOCK_LOG" ]] || fail "$marker_case markers reached gh"
done

printf 'PASS: release rendering, filtering, idempotence, mode, API errors and marker guards\n'
