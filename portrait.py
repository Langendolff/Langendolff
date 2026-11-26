"""Retrato em ASCII a partir de uma foto.

    python3 portrait.py build ~/Pictures/foto.jpg   # gera assets/portrait.json (precisa de ffmpeg)

Só a grade de brilho (46x30) vai para o repositório, não a foto.
"""

import json
import math
import os
import subprocess
import sys

COLS, ROWS = 46, 30
ASPECT = 2.05
OVERSAMPLE = 4
RAMP = " .:-=+*#%@"
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "portrait.json")


def build(photo, crop):
    w, h = COLS * OVERSAMPLE, int(ROWS * ASPECT * OVERSAMPLE)
    vf = f"{crop},scale={w}:{h},format=gray,unsharp=7:7:1.2"
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", photo, "-vf", vf, "-f", "rawvideo", "-"],
                         check=True, capture_output=True).stdout
    px = list(raw)
    grid = []
    for r in range(ROWS):
        row = []
        y0, y1 = round(r * h / ROWS), round((r + 1) * h / ROWS)
        for c in range(COLS):
            x0, x1 = c * OVERSAMPLE, (c + 1) * OVERSAMPLE
            vals = [px[y * w + x] for y in range(y0, y1) for x in range(x0, x1)]
            row.append(sum(vals) / len(vals) / 255)
        grid.append(row)
    # normaliza o contraste só dentro da máscara oval
    inside = [(r, c) for r in range(ROWS) for c in range(COLS) if mask(r, c) > 0]
    vals = sorted(grid[r][c] for r, c in inside)
    lo, hi = vals[len(vals) // 50], vals[-len(vals) // 50]
    out = [[round(max(0.0, min(1.0, (grid[r][c] - lo) / (hi - lo))) * mask(r, c), 3)
            for c in range(COLS)] for r in range(ROWS)]
    os.makedirs(os.path.dirname(DATA), exist_ok=True)
    with open(DATA, "w") as f:
        json.dump(out, f)


def mask(r, c):
    """Oval suave em volta do rosto: 1 dentro, 0 fora."""
    dx = (c + 0.5 - COLS / 2) / (COLS / 2 * 0.98)
    dy = (r + 0.5 - ROWS * 0.5) / (ROWS / 2 * 1.02)
    d = math.hypot(dx, dy)
    return max(0.0, min(1.0, (1.0 - d) / 0.08))


def render(light_mode=False):
    with open(DATA) as f:
        grid = json.load(f)
    lines = []
    for r, row in enumerate(grid):
        line = []
        for c, v in enumerate(row):
            if mask(r, c) <= 0:
                line.append((" ", ""))
                continue
            v = v ** 1.6
            if light_mode:
                v = 1 - v
            line.append((RAMP[round(v * (len(RAMP) - 1))], ""))
        lines.append(line)
    return lines


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "build":
        build(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "crop=iw:iw*1.34:0:ih*0.035")
    for l in render():
        print("".join(ch for ch, _ in l))
