#!/usr/bin/env python3
"""
Extract a..z letter paths from an SVG (ids 'a'..'z'), sample them into
polylines, render PNG previews, and emit a single Arduino header with
PROGMEM float coordinates. Polylines are separated by {NAN, NAN}.

Usage:
  python extract_letters_batch.py letters.svg \
      --out all_letters.h \
      --pngdir png_out \
      --step 7 --gap 20 --png-h 256 --stroke 3

Deps (install once):
  pip install svgpathtools lxml pillow
"""

from __future__ import annotations
import argparse
import math
import os
import re
from typing import List, Tuple, Dict

from lxml import etree
from svgpathtools import parse_path

# ----------------------------- Affine utils -----------------------------

def mat(a: float, b: float, c: float, d: float, e: float, f: float) -> List[List[float]]:
    # SVG matrix(a b c d e f) maps (x,y) -> (ax + cy + e, bx + dy + f)
    return [[a, c, e],
            [b, d, f],
            [0, 0, 1]]

def I() -> List[List[float]]:
    return [[1,0,0],[0,1,0],[0,0,1]]

def mul(A: List[List[float]], B: List[List[float]]) -> List[List[float]]:
    return [[sum(A[i][k]*B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]

def apply(M: List[List[float]], x: float, y: float) -> Tuple[float, float]:
    return (M[0][0]*x + M[0][1]*y + M[0][2],
            M[1][0]*x + M[1][1]*y + M[1][2])

_txn_re = re.compile(r'(matrix|translate|scale|rotate|skewX|skewY)\s*\(([^)]*)\)')

def _parse_transform_attr(t: str | None) -> List[List[float]]:
    """Parse an SVG 'transform' attribute into a 3x3 matrix."""
    if not t:
        return I()
    T = I()
    for name, args in _txn_re.findall(t):
        vals = [float(v) for v in re.split(r'[ ,]+', args.strip()) if v]
        if name == "matrix" and len(vals) == 6:
            M = mat(*vals)
        elif name == "translate":
            tx = vals[0]; ty = vals[1] if len(vals) > 1 else 0.0
            M = mat(1,0,0,1, tx,ty)
        elif name == "scale":
            sx = vals[0]; sy = vals[1] if len(vals) > 1 else sx
            M = mat(sx,0,0,sy, 0,0)
        elif name == "rotate":
            # rotate(angle) about origin only (rotate(a cx cy) not handled here)
            r = math.radians(vals[0])
            c, s = math.cos(r), math.sin(r)
            M = mat(c, s, -s, c, 0, 0)
        elif name == "skewX":
            k = math.tan(math.radians(vals[0])); M = [[1,k,0],[0,1,0],[0,0,1]]
        elif name == "skewY":
            k = math.tan(math.radians(vals[0])); M = [[1,0,0],[k,1,0],[0,0,1]]
        else:
            M = I()
        T = mul(T, M)
    return T

def world_transform(node: etree._Element) -> List[List[float]]:
    """Accumulate transforms from node up to root (closest first applied)."""
    chain: List[List[List[float]]] = []
    cur = node
    while cur is not None and isinstance(cur.tag, str):
        chain.append(_parse_transform_attr(cur.get("transform")))
        cur = cur.getparent()
    T = I()
    for M in reversed(chain):
        T = mul(T, M)
    return T

# ---------------------- Sampling & polyline processing -------------------

def sample_path_uniform(path, step: float) -> List[Tuple[float,float]]:
    """Sample an svgpathtools Path at ~uniform arc-length spacing."""
    L = path.length()
    if L <= 0:
        return []
    n = max(1, int(math.ceil(L / step)))
    pts: List[Tuple[float,float]] = []
    for i in range(n + 1):
        s = min(i * step, L)
        try:
            t = path.ilength(s)
        except Exception:
            t = i / n  # fallback
        z = path.point(t)
        pts.append((z.real, z.imag))
    return pts

def split_on_gaps(points: List[Tuple[float,float]], gap: float) -> List[List[Tuple[float,float]]]:
    """Split a point list into polylines whenever distance between consecutive points > gap."""
    if not points:
        return []
    out: List[List[Tuple[float,float]]] = [[points[0]]]
    px, py = points[0]
    for x, y in points[1:]:
        if math.hypot(x - px, y - py) > gap:
            out.append([])
        out[-1].append((x, y))
        px, py = x, y
    return [poly for poly in out if len(poly) > 1]

# ------------------------------- Rendering -------------------------------

def save_png(polylines: List[List[Tuple[float,float]]], png_path: str, img_h: int = 256, stroke: int = 3) -> None:
    """Render polylines to a PNG preview (keeps aspect ratio, Y-up -> screen Y-down)."""
    from PIL import Image, ImageDraw
    if not polylines:
        Image.new("RGB", (256, 256), (255, 255, 255)).save(png_path)
        return

    pts = [p for poly in polylines for p in poly]
    xs = [x for x, _ in pts]; ys = [y for _, y in pts]
    minx, maxx = min(xs), max(xs); miny, maxy = min(ys), max(ys)
    w = max(1e-6, maxx - minx); h = max(1e-6, maxy - miny)
    img_w = max(1, int(round((w / h) * img_h)))

    pad = 12
    W, H = img_w + 2 * pad, img_h + 2 * pad
    im = Image.new("RGB", (W, H), (255, 255, 255))
    dr = ImageDraw.Draw(im)

    s = min((img_w - 1) / w, (img_h - 1) / h)
    ox = pad + (img_w - s * w) * 0.5
    oy = pad + (img_h - s * h) * 0.5

    def map_pt(p: Tuple[float,float]) -> Tuple[float,float]:
        # Y-up (data) -> Y-down (image)
        X = ox + (p[0] - minx) * s
        Y = pad + img_h - (p[1] - miny) * s - (img_h - (s * h))
        return (X, Y)

    for poly in polylines:
        mapped = [map_pt(p) for p in poly]
        dr.line(mapped, fill=(0, 0, 0), width=stroke, joint="curve")

    im.save(png_path)

# ------------------------------ Extraction -------------------------------

def extract_letter_polylines(root: etree._Element, letter_id: str, step: float, gap: float) -> List[List[Tuple[float,float]]]:
    """
    Find an element with id=letter_id, gather descendant <path d="...">,
    apply world transforms, sample uniformly, split on gaps, and flip Y
    within the glyph's local bbox to convert SVG Y-down to Y-up.
    """
    targets = root.xpath(f".//*[@id='{letter_id}']")
    if not targets:
        return []
    holder = targets[0]

    # collect <path> nodes (including the holder itself if it's a path)
    nodes = holder.xpath(".//*[local-name()='path' and @d]")
    if not nodes and etree.QName(holder).localname == "path" and holder.get("d"):
        nodes = [holder]
    if not nodes:
        return []

    polylines: List[List[Tuple[float,float]]] = []
    for nd in nodes:
        T = world_transform(nd)
        path = parse_path(nd.get("d"))
        pts = [apply(T, x, y) for (x, y) in sample_path_uniform(path, step)]
        polylines.extend(split_on_gaps(pts, gap))

    if not polylines:
        return []

    # flip Y within glyph bbox (SVG Y-down -> plotter Y-up)
    xs = [x for poly in polylines for x, _ in poly]
    ys = [y for poly in polylines for _, y in poly]
    miny, maxy = min(ys), max(ys)

    flipped: List[List[Tuple[float,float]]] = []
    for poly in polylines:
        flipped.append([(x, maxy - (y - miny)) for (x, y) in poly])
    return flipped

# --------------------------------- I/O -----------------------------------

def write_header(per_letter: Dict[str, List[List[Tuple[float,float]]]], out_path: str) -> None:
    """Write a single Arduino header with per-letter PROGMEM float coords, NAN separators, and *_len constants."""
    total_written = 0
    letters_present = "".join(sorted(per_letter.keys()))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("// Auto-generated from SVG\n")
        f.write("// Coordinates are Y-up. {NAN,NAN} separates polylines (pen up).\n\n")
        f.write("#pragma once\n#include <avr/pgmspace.h>\n#include <stdint.h>\n#include <math.h>\n\n")

        for lid in sorted(per_letter.keys()):
            polys = per_letter[lid]
            sym = f"letter_{lid}"
            f.write(f"// ----- {lid} -----\n")
            f.write(f"const float {sym}[][2] PROGMEM = {{\n")
            first = True
            count = 0
            for poly in polys:
                if not first:
                    f.write("  {NAN, NAN},\n")
                first = False
                for (x, y) in poly:
                    f.write(f"  {{ {x:.2f}f, {y:.2f}f }},\n")
                    count += 1
            f.write("};\n")
            seps = (len(polys) - 1) if len(polys) > 1 else 0
            f.write(f"const uint16_t {sym}_len = {count + seps};\n\n")
            total_written += count + seps

        f.write(f"// Letters available (flash)\nconst char LETTERS_PRESENT[] PROGMEM = \"{letters_present}\";\n")

    print(f"Wrote {out_path} with {len(per_letter)} glyphs, total points+separators = {total_written}")

# --------------------------------- CLI -----------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Extract a..z glyph paths by id from an SVG -> per-letter PNGs + Arduino header with PROGMEM coords."
    )
    ap.add_argument("svg", help="Input SVG (Plain SVG preferred; each letter must have id 'a'..'z')")
    ap.add_argument("--out", default="letters_all.h", help="Output header file name (default: letters_all.h)")
    ap.add_argument("--pngdir", default="png_out", help="Directory for per-letter PNG previews")
    ap.add_argument("--step", type=float, default=7.0, help="Sampling step along path in SVG units (default: 7)")
    ap.add_argument("--gap", type=float, default=20.0, help="Gap distance to split polylines (pen up) (default: 20)")
    ap.add_argument("--png-h", type=int, default=256, help="PNG height in pixels (default: 256)")
    ap.add_argument("--stroke", type=int, default=3, help="Preview stroke width in pixels (default: 3)")
    args = ap.parse_args()

    if not os.path.isfile(args.svg):
        raise SystemExit(f"SVG not found: {args.svg}")

    os.makedirs(args.pngdir, exist_ok=True)

    root = etree.parse(args.svg).getroot()
    letters = [chr(c) for c in range(ord('a'), ord('z') + 1)]

    per_letter: Dict[str, List[List[Tuple[float,float]]]] = {}
    for lid in letters:
        polys = extract_letter_polylines(root, lid, step=args.step, gap=args.gap)
        if not polys:
            continue
        per_letter[lid] = polys

        png_path = os.path.join(args.pngdir, f"letter_{lid}.png")
        save_png(polys, png_path, img_h=args.png_h, stroke=args.stroke)

    if not per_letter:
        raise SystemExit("No glyphs found. Ensure your SVG has ids 'a'..'z' on groups or paths.")

    write_header(per_letter, args.out)

if __name__ == "__main__":
    main()
