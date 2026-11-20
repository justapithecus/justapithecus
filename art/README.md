# A single route

The profile signature connects **1,641 points** inside custom `A` and `H` letterforms with one continuous open path.

The shapes come from polygons, including the counter in the `A`. A fixed seed places one slightly displaced sample in each cell of a grid; samples outside the letters are discarded. The path visits each retained point exactly once.

Within each letter, a nearest-neighbor route is shortened with 2-opt edge exchanges. The two routes meet at one short bridge near the baseline. Letter order and bridge endpoints are design constraints, so the result is an authored route optimized within those choices.

The complete mark is visible from the start. A blue segment follows the same path; it stays still when reduced motion is requested. The SVGs contain no scripts, fonts, or external resources.

## Reproduce

From the repository root, using Python 3.10 or later:

```sh
python3 scripts/generate-signature.py
```

The generator uses only the Python standard library and writes:

- [`signature-light.svg`](signature-light.svg) and [`signature-dark.svg`](signature-dark.svg): the rendered mark in both themes.
- [`route.json`](route.json): the letter geometry, point coordinates, visit order, seed, and route statistics.

The generator checks that every sample belongs to a filled letter, every sample is visited once, the fixed endpoints are preserved, and optimization never increases the initial route length.

[Back to the profile](../README.md)
