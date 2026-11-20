#!/usr/bin/env python3
"""Generate Andrew Hu's final AH signature and complete route provenance.

Python standard library only. Authored polygons define the letterforms and
counter. The local search visits A, crosses one shortest available bridge,
then visits H. No global optimality is claimed. Run normally to write the
three artifacts in art/, or use --check for byte-for-byte regeneration.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import random
from pathlib import Path
GLYPHS = {
    'A': {
        'width': 100,
        'outer': [
            (0, 140),
            (35, 0),
            (65, 0),
            (100, 140),
            (76, 140),
            (67, 104),
            (33, 104),
            (24, 140),
        ],
        'holes': [
            [(39, 78), (61, 78), (50, 34)],
        ],
    },
    'H': {
        'width': 100,
        'outer': [
            (0, 0),
            (24, 0),
            (24, 58),
            (76, 58),
            (76, 0),
            (100, 0),
            (100, 140),
            (76, 140),
            (76, 82),
            (24, 82),
            (24, 140),
            (0, 140),
        ],
    },
}


def area(poly):
    return abs(sum((a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1])))) / 2


def inside(x, y, poly):
    hit = False
    j = len(poly) - 1
    for i, (xi, yi) in enumerate(poly):
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            hit = not hit
        j = i
    return hit


def place(letter, x, y, width, height):
    original = GLYPHS[letter]
    sx, sy = (width / original['width'], height / 140)
    transform = lambda p: [(round(x + px * sx, 3), round(y + py * sy, 3)) for px, py in p]
    outer = transform(original['outer'])
    holes = [transform(h) for h in original.get('holes', [])]
    return {
        'letter': letter,
        'outer': outer,
        'holes': holes,
        'bounds': [x, y, x + width, y + height],
        'area': area(outer) - sum((area(h) for h in holes)),
    }


def make_layout():
    """The final AH design: two authored glyphs and one constrained bridge."""
    return {
        'size': [840, 260],
        'glyphs': [place('A', 94, 22, 290, 216), place('H', 456, 22, 290, 216)],
        'target': 1600,
        'seed': 202611204,
        'jitter': 0.17,
    }


def samples(layout):
    """One jittered point per lattice cell; reject the points outside glyphs."""
    glyphs = layout['glyphs']
    area_sum = sum((g['area'] for g in glyphs))
    step = math.sqrt(area_sum / layout['target'])
    rng = random.Random(layout['seed'])
    width, height = layout['size']
    points = []
    for iy in range(math.ceil(height / step)):
        for ix in range(math.ceil(width / step)):
            jitter = layout.get('jitter', 0.4)
            x = round((ix + 0.5 + rng.uniform(-jitter, jitter)) * step, 3)
            y = round((iy + 0.5 + rng.uniform(-jitter, jitter)) * step, 3)
            for gi, g in enumerate(glyphs):
                x0, y0, x1, y1 = g['bounds']
                if (
                    x0 <= x <= x1
                    and y0 <= y <= y1
                    and inside(x, y, g['outer'])
                    and not any(inside(x, y, h) for h in g['holes'])
                ):
                    points.append([x, y, gi])
                    break
    return (points, step)


def squared(a, b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


def length(points, route):
    return sum((math.sqrt(squared(points[a], points[b])) for a, b in zip(route, route[1:])))


def neighbors(points, step, k=22):
    cell_size = step * 3
    buckets = {}
    for i, p in enumerate(points):
        buckets.setdefault((int(p[0] // cell_size), int(p[1] // cell_size)), []).append(i)
    result = []
    for i, p in enumerate(points):
        cx, cy = (int(p[0] // cell_size), int(p[1] // cell_size))
        candidates = []
        radius = 1
        while len(candidates) < k + 1:
            candidates = [
                j
                for bx in range(cx - radius, cx + radius + 1)
                for by in range(cy - radius, cy + radius + 1)
                for j in buckets.get((bx, by), [])
                if j != i
            ]
            radius += 1
        result.append(sorted(candidates, key=lambda j: (squared(p, points[j]), j))[:k])
    return result


def solve(points, step, start=None, end=None, long_edges=False):
    n = len(points)
    if start is None:
        start = min(range(n), key=lambda i: (points[i][0], points[i][1]))
    left = set(range(n))
    left.remove(start)
    if end is not None:
        left.remove(end)
    route = [start]
    while left:
        p = points[route[-1]]
        nxt = min(left, key=lambda j: (squared(p, points[j]), j))
        route.append(nxt)
        left.remove(nxt)
    if end is not None:
        route.append(end)
    initial = length(points, route)
    candidates = neighbors(points, step)
    pos = [0] * n
    for i, v in enumerate(route):
        pos[v] = i
    swaps = 0
    passes = 0
    for passes in range(1, 61):
        changed = False
        for i in range(n - 2):
            a, b = (route[i], route[i + 1])
            ab = math.sqrt(squared(points[a], points[b]))
            for c in candidates[a]:
                j = pos[c]
                if j <= i + 1 or j >= n - 1:
                    continue
                d = route[j + 1]
                old = ab + math.sqrt(squared(points[c], points[d]))
                new = math.sqrt(squared(points[a], points[c])) + math.sqrt(squared(points[b], points[d]))
                if new < old - 1e-08:
                    route[i + 1:j + 1] = reversed(route[i + 1:j + 1])
                    for offset in range(i + 1, j + 1):
                        pos[route[offset]] = offset
                    swaps += 1
                    changed = True
                    break
        for i in range(n - 2) if end is None else []:
            a, b, z = (route[i], route[i + 1], route[-1])
            if squared(points[a], points[z]) < squared(points[a], points[b]) - 1e-08:
                route[i + 1:] = reversed(route[i + 1:])
                for offset in range(i + 1, n):
                    pos[route[offset]] = offset
                swaps += 1
                changed = True
        if not changed:
            break
    long_swaps = 0
    long_passes = 0
    if long_edges:
        for long_passes in range(1, 13):
            changed = False
            indices = sorted(
                range(n - 2),
                key=lambda i: squared(points[route[i]], points[route[i + 1]]),
                reverse=True,
            )[:80]
            for i in indices:
                a, b = (route[i], route[i + 1])
                ab = math.sqrt(squared(points[a], points[b]))
                gain, best = (1e-08, None)
                for j in range(i + 2, n - 1):
                    c, d = (route[j], route[j + 1])
                    improvement = (
                        ab
                        + math.sqrt(squared(points[c], points[d]))
                        - math.sqrt(squared(points[a], points[c]))
                        - math.sqrt(squared(points[b], points[d]))
                    )
                    if improvement > gain:
                        gain, best = (improvement, j)
                if best is not None:
                    route[i + 1:best + 1] = reversed(route[i + 1:best + 1])
                    long_swaps += 1
                    changed = True
            if not changed:
                break
    assert len(route) == n and set(route) == set(range(n)), 'Route must visit every sample once'
    assert route[0] == start and (end is None or route[-1] == end), 'Fixed endpoints must remain fixed'
    final = length(points, route)
    assert final <= initial + 1e-07
    return (
        route,
        {
            'nearest_neighbor_length': round(initial, 3),
            'length': round(final, 3),
            'two_opt_swaps': swaps,
            'two_opt_passes': passes,
            'candidate_neighbors': 22,
            'long_edge_all_candidate_swaps': long_swaps,
            'long_edge_all_candidate_passes': long_passes,
        },
    )


def solve_by_glyph(points, step):
    """A typographic constraint: complete A, bridge once, then complete H."""
    groups = [
        [i for i, p in enumerate(points) if p[2] == g]
        for g in sorted(set(p[2] for p in points))
    ]
    bridges = [
        min(
            ((a, b) for a in left for b in right),
            key=lambda pair: squared(points[pair[0]], points[pair[1]]),
        )
        for left, right in zip(groups, groups[1:])
    ]
    route = []
    statistics = []
    for gi, group in enumerate(groups):
        local = {v: i for i, v in enumerate(group)}
        start = local[bridges[gi - 1][1]] if gi else None
        end = local[bridges[gi][0]] if gi < len(groups) - 1 else None
        part, stats = solve([points[i] for i in group], step, start, end, long_edges=True)
        route.extend((group[i] for i in part))
        statistics.append(stats)
    bridge_length = sum((math.sqrt(squared(points[a], points[b])) for a, b in bridges))
    assert len(route) == len(points) and len(set(route)) == len(points)
    return (
        route,
        {
            'nearest_neighbor_length': round(
                sum(s['nearest_neighbor_length'] for s in statistics) + bridge_length,
                3,
            ),
            'length': round(length(points, route), 3),
            'constraint': (
                'visit glyphs in authored order; exactly one shortest available '
                'bridge between each consecutive pair'
            ),
            'bridge_edges': bridges,
            'bridge_length': round(bridge_length, 3),
            'per_glyph': statistics,
        },
    )


def path_data(points, route):
    return 'M' + ' L'.join((f'{points[i][0]:.3f},{points[i][1]:.3f}' for i in route))


def polygon_path(glyph):
    return ' '.join(
        'M' + ' L'.join(f'{x:.3f},{y:.3f}' for x, y in polygon) + ' Z'
        for polygon in [glyph['outer']] + glyph['holes']
    )


def svg_document(layout, points, route, theme):
    """The full route remains visible beneath a short moving accent."""
    colors = {
        'light': {
            'ink': '#202735',
            'gap': '#cad3e1',
            'route': '#ffffff',
            'accent': '#335bde',
            'clipped': '#91afff',
        },
        'dark': {
            'ink': '#edf2fa',
            'gap': '#465469',
            'route': '#0d1117',
            'accent': '#9db9ff',
            'clipped': '#2456db',
        },
    }[theme]
    glyph_paths = [polygon_path(glyph) for glyph in layout['glyphs']]
    # Use physical distances so static renderers and browsers agree, including
    # renderers that ignore SVG pathLength normalization.
    unit = length(points, route) / 1000
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 260" '
        'role="img" aria-labelledby="title description">',
        '  <title id="title">AH — Andrew Hu</title>',
        f'  <desc id="description">One continuous open route through {len(points):,} '
        'sampled points inside two authored geometric letterforms, with one '
        'bridge between A and H. Nearest-neighbor construction and local 2-opt '
        'improve the route; no globally shortest route is claimed. The complete '
        'route remains visible while a blue segment travels along it.</desc>',
        '  <defs>',
        f'    <path id="route" d="{path_data(points, route)}"/>',
        '    <clipPath id="glyph-clip">',
    ]
    for drawing in glyph_paths:
        lines.append(f'      <path d="{drawing}" fill-rule="evenodd" clip-rule="evenodd"/>')
    lines += [
        '    </clipPath>',
        '  </defs>',
        '  <style>',
        '    .travel {',
        f'      stroke-dasharray: {18 * unit:.6f} {982 * unit:.6f};',
        f'      stroke-dashoffset: {-300 * unit:.6f};',
        '      animation: travel 32s linear infinite;',
        '    }',
        '    @keyframes travel {',
        f'      from {{ stroke-dashoffset: {-300 * unit:.6f}; }}',
        f'      to {{ stroke-dashoffset: {-1300 * unit:.6f}; }}',
        '    }',
        '    @media (prefers-reduced-motion: reduce) {',
        '      .travel { animation: none; }',
        '    }',
        '  </style>',
        f'''  <g fill="{colors['ink']}">''',
    ]
    for drawing in glyph_paths:
        lines.append(f'    <path d="{drawing}" fill-rule="evenodd"/>')
    lines += [
        '  </g>',
        '  <g fill="none" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">',
        f'''    <use href="#route" stroke="{colors['gap']}"/>''',
        f'''    <use href="#route" stroke="{colors['route']}" clip-path="url(#glyph-clip)"/>''',
        f'''    <use href="#route" class="travel" stroke="{colors['accent']}"/>''',
        f'    <use href="#route" class="travel" stroke="{colors["clipped"]}" '
        'clip-path="url(#glyph-clip)"/>',
        '  </g>',
        '</svg>',
    ]
    return '\n'.join(lines) + '\n'


def main():
    """Write the final design, or reproduce it in memory with --check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'art')
    parser.add_argument(
        '--check', action='store_true',
        help='Verify existing artifacts against deterministic regeneration',
    )
    args = parser.parse_args()
    layout = make_layout()
    points, step = samples(layout)
    route, statistics = solve_by_glyph(points, step)
    assert len(points) == len({tuple(point[:2]) for point in points})
    assert len(route) == len(points) and set(route) == set(range(len(points)))
    for x, y, glyph_index in points:
        glyph = layout['glyphs'][glyph_index]
        assert math.isfinite(x) and math.isfinite(y)
        assert 0 <= x <= 840 and 0 <= y <= 260
        assert inside(x, y, glyph['outer'])
        assert not any((inside(x, y, hole) for hole in glyph['holes']))
    transitions = [[a, b] for a, b in zip(route, route[1:]) if points[a][2] != points[b][2]]
    assert len(transitions) == 1 and tuple(transitions[0]) == statistics['bridge_edges'][0]
    assert [points[index][2] for index in route] == sorted((points[index][2] for index in route))
    assert round(length(points, route), 3) == statistics['length']
    geometry = json.dumps({'points': points, 'route': route}, separators=(',', ':'))
    data = {
        'version': 1,
        'title': 'AH — Andrew Hu',
        'canvas': layout['size'],
        'coordinate_units': 'SVG user units',
        'seed': layout['seed'],
        'sample_target': layout['target'],
        'sample_count': len(points),
        'sample_spacing': round(step, 6),
        'jitter_fraction': layout['jitter'],
        'algorithm': [
            'Stratified jittered sampling inside authored polygon letterforms',
            'Nearest-neighbor open tour within each glyph',
            'Candidate-limited 2-opt, with free-end suffix moves where permitted',
            'All-candidate 2-opt for the longest edges',
        ],
        'search_parameters': {
            'candidate_neighbors': 22,
            'maximum_local_passes': 60,
            'longest_edges_per_pass': 80,
            'maximum_long_edge_passes': 12,
        },
        'constraints': [
            'Visit all A samples before visiting H samples',
            'Cross once using the shortest available inter-glyph sample pair',
            'Keep both bridge endpoints fixed while improving each glyph tour',
            'The initial A endpoint is its leftmost sample; the final H endpoint is free',
        ],
        'optimality': 'Local heuristic search; no claim of global optimality',
        'closed': False,
        'endpoints': {
            'vertices': [route[0], route[-1]],
            'coordinates': [points[route[0]][:2], points[route[-1]][:2]],
            'glyphs': ['A', 'H'],
        },
        'statistics': statistics,
        'glyphs': layout['glyphs'],
        'point_format': ['x', 'y', 'glyph_index'],
        'points': points,
        'route': route,
        'geometry_sha256': hashlib.sha256(geometry.encode()).hexdigest(),
        'validation': {
            'unique_sample_coordinates': True,
            'every_sample_visited_once': True,
            'every_sample_inside_filled_glyph': True,
            'counters_excluded_from_sampling': True,
            'one_inter_glyph_bridge': True,
            'fixed_bridge_endpoints_preserved': True,
            'reported_length_recomputed': True,
        },
    }
    artifacts = {
        'signature-light.svg': svg_document(layout, points, route, 'light'),
        'signature-dark.svg': svg_document(layout, points, route, 'dark'),
        'route.json': json.dumps(data, indent=2) + '\n',
    }
    if not args.check:
        args.output.mkdir(parents=True, exist_ok=True)
    for name, contents in artifacts.items():
        destination = args.output / name
        encoded = contents.encode('utf-8')
        if args.check:
            if not destination.exists() or destination.read_bytes() != encoded:
                raise SystemExit(f'Generated file differs: {destination}')
        else:
            destination.write_bytes(encoded)
        print(f"{('verified' if args.check else 'wrote')} {destination}")
        print(f'  sha256 {hashlib.sha256(encoded).hexdigest()}')
    print(
        f"{len(points)} samples; route {statistics['length']:.3f} SVG units; "
        f"bridge {statistics['bridge_length']:.3f} SVG units"
    )
if __name__ == '__main__':
    main()
