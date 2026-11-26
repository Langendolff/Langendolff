"""Pinguim original em ASCII, colorido por região (corpo, branco, laranja, olho).

As formas são elipses num grid de 46 colunas; cada célula é amostrada 4x4
vezes. Células da borda (cobertura parcial) usam caracteres mais leves e o
miolo usa caracteres cheios. Retorna linhas de (char, classe).
"""

import math

COLS, ROWS = 46, 30
ASPECT = 2.05  # altura de uma célula / largura
SS = 4
EDGE = " .,:;i"
FILL = {"body": "8", "white": "8", "orange": "8", "eye": "@", "glint": "o"}
CX = 23.0


def ell(px, py, cx, cy, rx, ry, a=0.0):
    dx, dy = px - cx, py - cy
    if a:
        c, s = math.cos(a), math.sin(a)
        dx, dy = dx * c + dy * s, -dx * s + dy * c
    return (dx / rx) ** 2 + (dy / ry) ** 2 <= 1.0


def region(px, py):
    for side in (-1, 1):  # pés largos e achatados
        if ell(px, py, CX + side * 8.5, 57.0, 8.2, 3.0, side * 0.08):
            return "orange"
    if ell(px, py, CX, 20.6, 5.0, 1.6) or ell(px, py, CX, 22.6, 3.6, 1.4):  # bico
        return "orange"
    for side in (-1, 1):  # olhos
        ex = CX + side * 3.2
        if ell(px, py, ex + side * 0.6 - 0.6, 13.0, 0.7, 0.9):
            return "glint"
        if ell(px, py, ex + side * 0.6, 14.0, 1.5, 2.3):
            return "eye"
        if ell(px, py, ex, 14.2, 2.8, 4.0):
            return "white"
    if ell(px, py, CX, 39.0, 11.0, 16.0) or ell(px, py, CX, 27.0, 7.0, 6.0):  # barriga
        return "white"
    if (ell(px, py, CX, 13.5, 10.0, 11.5) or ell(px, py, CX, 39.0, 15.5, 18.5)
            or ell(px, py, CX, 27.0, 11.5, 10.0)
            or ell(px, py, CX - 14.0, 39.0, 3.2, 12.5, 0.45)
            or ell(px, py, CX + 14.0, 39.0, 3.2, 12.5, -0.45)):
        return "body"
    return None


def render(light_mode=False):
    lines = []
    for row in range(ROWS):
        line = []
        for col in range(COLS):
            counts = {}
            for sy in range(SS):
                for sx in range(SS):
                    r = region(col + (sx + 0.5) / SS, (row + (sy + 0.5) / SS) * ASPECT)
                    if r:
                        counts[r] = counts.get(r, 0) + 1
            hits = sum(counts.values())
            if not hits:
                line.append((" ", ""))
                continue
            k = max(counts, key=counts.get)
            cover = hits / SS**2
            ch = FILL[k] if cover >= 0.85 else EDGE[max(1, round(cover * (len(EDGE) - 1)))]
            line.append((ch, k))
        lines.append(line)
    return lines


if __name__ == "__main__":
    for l in render():
        print("".join(c for c, _ in l))
