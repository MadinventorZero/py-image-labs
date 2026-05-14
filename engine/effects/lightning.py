import math
import random

from PIL import Image, ImageDraw, ImageFilter


def _subdivide_bolt(
    p0: tuple[float, float],
    p1: tuple[float, float],
    roughness: float,
    rng: random.Random,
    depth: int = 5,
) -> list[tuple[float, float]]:
    if depth == 0:
        return [p0, p1]
    mx = (p0[0] + p1[0]) / 2 + rng.gauss(0, roughness)
    my = (p0[1] + p1[1]) / 2
    left  = _subdivide_bolt(p0, (mx, my), roughness * 0.6, rng, depth - 1)
    right = _subdivide_bolt((mx, my), p1, roughness * 0.6, rng, depth - 1)
    return left[:-1] + right


def generate_lightning_bolt(
    canvas_size: tuple[int, int],
    seed: int = 42,
) -> list[list[tuple[float, float]]]:
    w, h  = canvas_size
    rng   = random.Random(seed)
    start = (w * rng.uniform(0.68, 0.80), h * rng.uniform(0.02, 0.10))
    end   = (w * rng.uniform(0.60, 0.88), h * rng.uniform(0.50, 0.65))
    roughness = w * 0.04
    main  = _subdivide_bolt(start, end, roughness, rng, depth=5)
    bolts = [main]

    n_branches = rng.randint(2, 3)
    interior   = main[3:-3]
    fork_points = rng.sample(interior, min(n_branches, len(interior)))
    for fp in fork_points:
        branch_end = (
            fp[0] + rng.uniform(-w * 0.12, w * 0.15),
            fp[1] + h * rng.uniform(0.10, 0.25),
        )
        branch = _subdivide_bolt(fp, branch_end, roughness * 0.45, rng, depth=3)
        bolts.append(branch)

    return bolts


def make_lightning_layer(
    canvas_size: tuple[int, int],
    bolts: list[list[tuple[float, float]]],
    alpha: float,
) -> Image.Image:
    w, _ = canvas_size
    layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    if alpha <= 0:
        return layer

    base_w = max(1, int(w * 0.0015))

    for bolt_idx, points in enumerate(bolts):
        scale = 1.0 if bolt_idx == 0 else 0.45
        segs  = list(zip(points, points[1:]))

        g1 = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        d1 = ImageDraw.Draw(g1)
        for p0, p1 in segs:
            d1.line([p0, p1],
                    fill=(60, 120, 255, int(45 * alpha * scale)),
                    width=max(1, int(base_w * 5 * scale)))
        g1 = g1.filter(ImageFilter.GaussianBlur(radius=max(4, int(w * 0.010))))
        layer = Image.alpha_composite(layer, g1)

        g2 = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        d2 = ImageDraw.Draw(g2)
        for p0, p1 in segs:
            d2.line([p0, p1],
                    fill=(200, 225, 255, int(130 * alpha * scale)),
                    width=max(1, int(base_w * 2 * scale)))
        g2 = g2.filter(ImageFilter.GaussianBlur(radius=max(1, int(w * 0.004))))
        layer = Image.alpha_composite(layer, g2)

        core = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        dc   = ImageDraw.Draw(core)
        for p0, p1 in segs:
            dc.line([p0, p1],
                    fill=(245, 250, 255, int(255 * alpha * scale)),
                    width=max(1, int(base_w * scale)))
        layer = Image.alpha_composite(layer, core)

    return layer


def generate_ground_strike(
    canvas_size: tuple[int, int],
    seed: int,
    origin_x_frac: float = 0.5,
    depth: int = 4,
    roughness_frac: float = 0.035,
    fork_concentration: int = 3,
    subbranch_length: float = 0.40,
) -> tuple[list[dict], tuple[float, float]]:
    w, h      = canvas_size
    rng       = random.Random(seed)
    roughness = w * roughness_frac
    start     = (w * origin_x_frac, h * rng.uniform(0.0, 0.06))
    end       = (w * origin_x_frac + rng.uniform(-w * 0.07, w * 0.07),
                 h * rng.uniform(0.84, 0.96))
    segments: list[dict] = []

    def recurse(p0, p1, level, r):
        chain = _subdivide_bolt(p0, p1, r, rng, depth=5)
        segments.append({"path": chain, "level": level})
        if level <= 1:
            return
        n_forks  = max(1, min(fork_concentration,
                               rng.randint(1, fork_concentration + 1) - (depth - level)))
        guard    = max(1, len(chain) // 6)
        interior = chain[guard:-guard]
        if not interior:
            return
        fork_pts = rng.sample(interior, min(n_forks, len(interior)))
        for fp in fork_pts:
            angle      = rng.uniform(math.radians(20), math.radians(70))
            sign       = rng.choice([-1, 1])
            length     = math.dist(p0, p1) * rng.uniform(
                             subbranch_length * 0.5, subbranch_length)
            branch_end = (fp[0] + math.sin(angle) * sign * length,
                          fp[1] + math.cos(angle) * length)
            recurse(fp, branch_end, level - 1, r * 0.55)

    recurse(start, end, depth, roughness)
    return segments, end


def generate_atmospheric_intracloud(
    canvas_size: tuple[int, int],
    seed: int,
    n_spines: int = 3,
    depth: int = 4,
    roughness_frac: float = 0.042,
    fork_concentration: int = 3,
    subbranch_length: float = 0.40,
) -> tuple[list[dict], list]:
    w, h      = canvas_size
    rng       = random.Random(seed)
    roughness = w * roughness_frac
    ox = w * rng.uniform(0.32, 0.68)
    oy = h * rng.uniform(0.16, 0.40)
    origin    = (ox, oy)
    segments: list[dict] = []

    angle_step = 2 * math.pi / n_spines
    base_angle = rng.uniform(0, 2 * math.pi)

    for i in range(n_spines):
        spine_angle = base_angle + i * angle_step + rng.gauss(0, math.radians(14))
        spine_len = w * rng.uniform(0.22, 0.54)
        cos_a, sin_a = math.cos(spine_angle), math.sin(spine_angle)
        end = (ox + cos_a * spine_len,
               oy + sin_a * spine_len * 0.58)

        def recurse(p0, p1, level, r, parent_angle, _rng=rng):
            chain = _subdivide_bolt(p0, p1, r, _rng, depth=5)
            segments.append({"path": chain, "level": level})
            if level <= 1:
                return
            n_forks = max(1, min(fork_concentration,
                                  _rng.randint(1, fork_concentration + 1)
                                  - max(0, depth - level - 1)))
            guard    = max(1, len(chain) // 5)
            interior = chain[guard:-guard]
            if not interior:
                return
            fork_pts = _rng.sample(interior, min(n_forks, len(interior)))
            for fp in fork_pts:
                fork_angle = parent_angle + _rng.choice([-1, 1]) * _rng.uniform(
                                 math.radians(38), math.radians(105))
                sub_len = math.dist(p0, p1) * _rng.uniform(
                              subbranch_length * 0.45, subbranch_length)
                branch_end = (fp[0] + math.cos(fork_angle) * sub_len,
                              fp[1] + math.sin(fork_angle) * sub_len * 0.60)
                recurse(fp, branch_end, level - 1, r * 0.60, fork_angle)

        recurse(origin, end, depth, roughness, spine_angle)

    return segments, []


def generate_full_storm(
    canvas_size: tuple[int, int],
    seed: int,
    n_ground_strikes: int = 2,
    depth: int = 4,
    roughness_frac: float = 0.037,
    fork_concentration: int = 3,
    subbranch_length: float = 0.40,
) -> tuple[list[dict], list[tuple[float, float]]]:
    w, h = canvas_size
    rng  = random.Random(seed)

    n_spines = max(2, n_ground_strikes + 1)
    atm_segs, _ = generate_atmospheric_intracloud(
        canvas_size, seed=seed + 7, n_spines=n_spines, depth=depth,
        roughness_frac=roughness_frac * 1.05,
        fork_concentration=fork_concentration,
        subbranch_length=subbranch_length,
    )

    all_segs   = list(atm_segs)
    ground_pts = []

    for i in range(n_ground_strikes):
        ox = rng.uniform(0.22, 0.78)
        gs, gpt = generate_ground_strike(
            canvas_size, seed=seed + 100 + i * 41,
            origin_x_frac=ox, depth=max(2, depth - 1),
            roughness_frac=roughness_frac,
            fork_concentration=fork_concentration,
            subbranch_length=subbranch_length,
        )
        all_segs.extend(gs)
        ground_pts.append(gpt)

    return all_segs, ground_pts


def make_ground_contact_glow(
    canvas_size: tuple[int, int],
    ground_points: list[tuple[float, float]],
    alpha: float,
) -> Image.Image:
    w, h  = canvas_size
    layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    if alpha <= 0 or not ground_points:
        return layer

    r_base = max(10, int(w * 0.026))

    for pt in ground_points:
        x, y = int(pt[0]), int(pt[1])
        if not (-r_base * 4 < x < w + r_base * 4 and
                -r_base * 2 < y < h + r_base * 2):
            continue

        for radius, color, opacity in [
            (r_base * 4, (120, 160, 255),  18),
            (r_base * 2, (200, 220, 255),  50),
            (r_base,     (240, 248, 255), 130),
        ]:
            ring = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
            d    = ImageDraw.Draw(ring)
            ry = max(1, radius // 2)
            d.ellipse([x - radius, y - ry, x + radius, y + ry],
                      fill=color + (int(opacity * alpha),))
            ring = ring.filter(ImageFilter.GaussianBlur(radius=max(2, radius // 3)))
            layer = Image.alpha_composite(layer, ring)

        core = ImageDraw.Draw(layer)
        core.ellipse([x - 6, y - 3, x + 6, y + 3],
                     fill=(255, 255, 255, int(255 * alpha)))

    return layer


def make_atmospheric_lightning_layer(
    canvas_size: tuple[int, int],
    bolt_trees: list[dict],
    alpha: float,
    max_depth: int = 4,
) -> Image.Image:
    w, _ = canvas_size
    layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    if alpha <= 0:
        return layer

    base_w = max(1, int(w * 0.0015))
    md     = max(1, max_depth)

    for seg in bolt_trees:
        lv    = seg["level"]
        scale = lv / md
        pts   = seg["path"]
        segs  = list(zip(pts, pts[1:]))

        if scale > 0.5:
            g1 = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
            d1 = ImageDraw.Draw(g1)
            for p0, p1 in segs:
                d1.line([p0, p1],
                        fill=(80, 140, 255, int(40 * alpha * scale)),
                        width=max(1, int(base_w * 4 * scale)))
            g1 = g1.filter(ImageFilter.GaussianBlur(radius=max(3, int(w * 0.009))))
            layer = Image.alpha_composite(layer, g1)

        g2 = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        d2 = ImageDraw.Draw(g2)
        for p0, p1 in segs:
            d2.line([p0, p1],
                    fill=(200, 220, 255, int(100 * alpha * scale)),
                    width=max(1, int(base_w * 2 * scale)))
        g2 = g2.filter(ImageFilter.GaussianBlur(radius=max(1, int(w * 0.003))))
        layer = Image.alpha_composite(layer, g2)

        core = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        dc   = ImageDraw.Draw(core)
        for p0, p1 in segs:
            dc.line([p0, p1],
                    fill=(232, 244, 255, int(220 * alpha * (0.3 + scale * 0.7))),
                    width=max(1, int(base_w * max(0.35, scale))))
        layer = Image.alpha_composite(layer, core)

    return layer
