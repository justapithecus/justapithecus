# Agents

This repository publishes Andrew Hu's GitHub profile and refreshes its release links.

## Governance

Read and apply the pinned [organization guardrails](https://github.com/pithecene/infrastructure/blob/1c6b432b3366985bc8440e54c0e16ddb6fd7d031/agents/AGENTS.md) before changing this repository.
The file `bosun.yaml` pins the shared development process and review criteria.
The file `.github/bosun-image` pins the Bosun release and image digest for local checks and CI.

Apply the release's [prose contract](https://github.com/pithecene/bosun/blob/18590eecd897f0eab32f6bf9e7d87ae90ada5eee/records/contracts/PROSE.md) to documentation, workflow text, commit messages, and pull requests.
The [configuration contract](https://github.com/pithecene/bosun/blob/18590eecd897f0eab32f6bf9e7d87ae90ada5eee/records/contracts/CONFIG.md) defines the supported settings.
Change pins through a reviewed commit, and verify the source release or policy publication for each new digest.

## Profile

Keep the introduction brief and retain Andrew's first-person voice.
Verify technical claims against the project's published documentation.
Keep names, prose, and destination links in native Markdown so they remain readable at narrow widths.
Preserve the artwork's full aspect ratio and describe the scene in its alt text.
Record the selected artwork's provenance and quoted generation brief in `art/README.md`.

## Release Updates

The updater owns the block between `<!-- releases:start -->` and `<!-- releases:end -->`.
Preserve exactly one ordered pair of standalone marker lines and preserve all surrounding content.
Keep project names, release tags, dates, and URLs faithful to the release API.
An API error must leave the README unchanged.
Run verification after regeneration and before publishing a bot commit.
Local regression tests use fixtures and make no network requests.

## Verification

Run the offline updater checks and the pinned Bosun checks from the repository root:

```sh
bash .github/scripts/check.sh
bash .github/scripts/bosun.sh check
```

The Bosun wrapper uses the workstation's Docker engine and registry credentials.
CI supplies the `BOSUN_REGISTRY_TOKEN` repository secret to read the private runtime and policy packages.
The wrapper and CI use the same image pin.
The stage `bosun run verify` runs the registered profile checks and Bosun checks through a host installation.

## Delivery

Use a linked worktree for each change and retain an existing pull request when its goal still holds.
A host installation for verification and delivery must match the release in `.github/bosun-image`.
Run `bosun run local-review`, `bosun run publish`, and `bosun run forge-review` after verification.
Sign commits and preserve published history.
The owner merges pull requests.

Install workstation hooks with `bosun hook install` from a supported host installation.
Repository configuration does not install those hooks.
Keep the workstation hook current under the [hook contract](https://github.com/pithecene/bosun/blob/18590eecd897f0eab32f6bf9e7d87ae90ada5eee/records/contracts/HOOKS.md).
The runtime settings select its installation independently of the repository's check pin.
