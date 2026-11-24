#!/usr/bin/env bash
# CI and local checks consume one pinned image and share the host's policy cache.
set -euo pipefail

if [ -z "${BOSUN_REGISTRY_TOKEN:-}" ]; then
  printf 'BOSUN_REGISTRY_TOKEN must permit reading the Bosun image and policy.\n' >&2
  exit 1
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
root="$(git -C "$script_dir" rev-parse --show-toplevel)"
root="$(cd -- "$root" && pwd -P)"
git_common="$(git -C "$root" rev-parse --path-format=absolute --git-common-dir)"
image="$(cat "$root/.github/bosun-image")"
if [[ ! "$image" =~ ^ghcr\.io/pithecene/bosun:[0-9]+\.[0-9]+\.[0-9]+@sha256:[a-f0-9]{64}$ ]]; then
  printf '.github/bosun-image must pin a Bosun release and its image digest.\n' >&2
  exit 1
fi

cache="${XDG_CACHE_HOME:-$HOME/.cache}/bosun"
if [[ "$cache" != /* ]]; then
  printf 'The Bosun cache path must be absolute.\n' >&2
  exit 1
fi
case "$cache" in
  "$root"|"$root"/*)
    printf 'The Bosun cache must lie outside the checkout.\n' >&2
    exit 1
    ;;
esac
mkdir -p "$cache"
cache="$(cd -- "$cache" && pwd -P)"
case "$cache" in
  "$root"|"$root"/*)
    printf 'The Bosun cache must lie outside the checkout.\n' >&2
    exit 1
    ;;
esac

docker_context="$(docker context show)"
# The registry entry prevents Docker from selecting the host's credential store.
docker_config="$(mktemp -d /tmp/bosun-docker.XXXXXX)"
trap 'rm -rf "$docker_config"' EXIT
printf '%s\n' '{"auths":{"ghcr.io":{}}}' > "$docker_config/config.json"
if [ "$docker_context" != default ]; then
  docker context export "$docker_context" - |
    DOCKER_CONFIG="$docker_config" docker context import "$docker_context" - >/dev/null
  DOCKER_CONFIG="$docker_config" docker context use "$docker_context" >/dev/null
fi
printf '%s' "$BOSUN_REGISTRY_TOKEN" |
  DOCKER_CONFIG="$docker_config" docker login ghcr.io --username bosun --password-stdin >/dev/null

mounts=(
  --mount "type=bind,source=$root,target=$root"
  --mount "type=bind,source=$git_common,target=$git_common"
  --mount "type=bind,source=$cache,target=/cache/bosun"
)
if [ -n "${GITHUB_EVENT_PATH:-}" ]; then
  mounts+=(--mount "type=bind,source=$GITHUB_EVENT_PATH,target=$GITHUB_EVENT_PATH,readonly")
fi

DOCKER_CONFIG="$docker_config" docker run --rm \
  --user "$(id -u):$(id -g)" \
  --workdir "$root" \
  --env HOME=/tmp \
  --env XDG_CACHE_HOME=/cache \
  --env BOSUN_REGISTRY_TOKEN \
  --env GITHUB_ACTIONS \
  --env GITHUB_ACTOR \
  --env GITHUB_EVENT_NAME \
  --env GITHUB_EVENT_PATH \
  "${mounts[@]}" "$image" "$@"
