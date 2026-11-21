#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
for script in "$script_dir"/*.sh; do
  bash -n "$script"
done
bash "$script_dir/test-update-releases.sh"
