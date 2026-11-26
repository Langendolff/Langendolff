"""Gera dark_mode.svg e light_mode.svg no estilo neofetch.

Uso local:   GITHUB_TOKEN=$(gh auth token) python3 today.py
No Actions:  roda todo dia pelo workflow .github/workflows/build.yml
"""

import datetime as dt
import json
import os
import time
import urllib.request
from html import escape

import penguin

# "penguin" ou "portrait" (foto em ASCII, gerada por portrait.py a partir de assets/foto.jpg)
ART = os.environ.get("ART", "penguin")

USER = "Langendolff"
# "Uptime" conta a partir desta data. Troque pela sua data de nascimento se quiser.
UPTIME_SINCE = dt.date(2023, 11, 27)  # criação da conta no GitHub
UPTIME_LABEL = "(no GitHub)"

WIDTH = 58  # largura da coluna de informações, em caracteres

INFO = [
    ("title", "lorenzo@langendolff"),
    ("OS", "Arch Linux, Android"),
    ("Uptime", None),  # calculado
    ("Host", "UFSM, Santa Maria, RS"),
    ("Kernel", "Redes de Computadores"),
    ("Mestrado", "Educação Profissional e Tecnológica"),
    ("Shell", "fish"),
    ("", ""),
    ("Languages.Programming", "Rust, TypeScript, Kotlin, Dart"),
    ("Languages.Also", "JavaScript, C#, Python"),
    ("Languages.Real", "Português, English"),
    ("", ""),
    ("Hobbies.Software", "Jogos educativos, Linux"),
    ("Hobbies.Redes", "Segurança, Firewall, IDS"),
    ("", ""),
    ("section", "Projetos"),
    ("TidyFlow", "Organizador de arquivos (Rust)"),
    ("Firewall", "Tower defense educativo"),
    ("Quitado", "Contas a pagar (Flutter)"),
    ("Locadora", "Streaming no seu servidor (Docker)"),
    ("", ""),
    ("section", "Contato"),
    ("GitHub", "github.com/Langendolff"),
    ("", ""),
    ("section", "GitHub Stats"),
    ("stats", None),
]

THEMES = {
    "dark": {"bg": "#161b22", "fg": "#c9d1d9", "key": "#ffa657", "val": "#a5d6ff",
             "dot": "#616e7f", "add": "#3fb950", "del": "#f85149",
             "body": "#6e7681", "white": "#f0f6fc", "orange": "#f2b705", "eye": "#30363d", "glint": "#f0f6fc"},
    "light": {"bg": "#f6f8fa", "fg": "#24292f", "key": "#953800", "val": "#0a3069",
              "dot": "#c2cfde", "add": "#1a7f37", "del": "#cf222e",
              "body": "#24292f", "white": "#afb8c1", "orange": "#d4a000", "eye": "#24292f", "glint": "#afb8c1"},
}


# ---------------------------------------------------------------- GitHub API

def _token():
    return os.environ.get("ACCESS_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""


def _request(url, body=None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-readme"}
    if _token():
        headers["Authorization"] = f"Bearer {_token()}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, (json.loads(r.read() or b"null"))


def graphql(query, **variables):
    _, out = _request("https://api.github.com/graphql", {"query": query, "variables": variables})
    if out.get("errors"):
        raise RuntimeError(out["errors"])
    return out["data"]


def fetch_stats():
    data = graphql("""
    query($login: String!) {
      user(login: $login) {
        createdAt
        followers { totalCount }
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
          totalCount
          nodes { nameWithOwner stargazerCount }
        }
        repositoriesContributedTo(first: 1, contributionTypes: [COMMIT, PULL_REQUEST, REPOSITORY]) {
          totalCount
        }
      }
    }""", login=USER)["user"]
    repos = data["repositories"]["nodes"]
    stats = {
        "repos": data["repositories"]["totalCount"],
        "contributed": data["repositoriesContributedTo"]["totalCount"],
        "stars": sum(r["stargazerCount"] for r in repos),
        "followers": data["followers"]["totalCount"],
    }

    # commits: soma do contributionsCollection ano a ano desde a criação da conta
    start_year = int(data["createdAt"][:4])
    commits = 0
    for year in range(start_year, dt.date.today().year + 1):
        c = graphql("""
        query($login: String!, $from: DateTime!, $to: DateTime!) {
          user(login: $login) { contributionsCollection(from: $from, to: $to) {
            totalCommitContributions restrictedContributionsCount } }
        }""", login=USER, **{"from": f"{year}-01-01T00:00:00Z", "to": f"{year}-12-31T23:59:59Z"})
        cc = c["user"]["contributionsCollection"]
        commits += cc["totalCommitContributions"] + cc["restrictedContributionsCount"]
    stats["commits"] = commits

    # linhas de código: estatísticas de contribuidor de cada repo (a API pode
    # responder 202 enquanto calcula, então tenta de novo algumas vezes)
    add = dele = 0
    for r in repos:
        url = f"https://api.github.com/repos/{r['nameWithOwner']}/stats/contributors"
        for _ in range(6):
            status, out = _request(url)
            if status == 200:
                break
            time.sleep(3)
        else:
            continue
        for contrib in out or []:
            if (contrib.get("author") or {}).get("login", "").lower() == USER.lower():
                add += sum(w["a"] for w in contrib["weeks"])
                dele += sum(w["d"] for w in contrib["weeks"])
    stats["loc_add"], stats["loc_del"] = add, dele
    return stats


# ---------------------------------------------------------------- texto

def uptime(today):
    years = today.year - UPTIME_SINCE.year
    months = today.month - UPTIME_SINCE.month
    days = today.day - UPTIME_SINCE.day
    if days < 0:
        months -= 1
        prev_month = (today.replace(day=1) - dt.timedelta(days=1))
        days += prev_month.day
    if months < 0:
        years -= 1
        months += 12
    plural = lambda n, s, p: f"{n} {s if n == 1 else p}"
    return (f"{plural(years, 'ano', 'anos')}, {plural(months, 'mês', 'meses')}, "
            f"{plural(days, 'dia', 'dias')} {UPTIME_LABEL}")


def kv(key, value, width=WIDTH):
    """Uma linha 'Chave: ...... valor' como lista de (classe, texto)."""
    head = f"{key}:"
    dots = width - len(head) - len(value) - 2
    return [("key", head), ("dot", " " + "." * max(dots, 1) + " "), ("val", value)]


def stat_pair(k1, v1, k2, v2):
    left = kv(k1, v1, 30)
    return left + [("fg", " | ")] + kv(k2, v2, WIDTH - 33)


def build_info(stats, today):
    lines = []
    for key, value in INFO:
        if key == "title":
            lines.append([("key", value), ("fg", " " + "—" * (WIDTH - len(value) - 1))])
        elif key == "section":
            lines.append([("fg", f"— {value} " + "—" * (WIDTH - len(value) - 3))])
        elif key == "Uptime":
            lines.append(kv(key, uptime(today)))
        elif key == "stats":
            n = lambda x: f"{x:,}".replace(",", ".")
            lines.append(stat_pair("Repos", f"{n(stats['repos'])} {{Contrib: {stats['contributed']}}}",
                                   "Stars", n(stats["stars"])))
            lines.append(stat_pair("Commits", n(stats["commits"]), "Followers", n(stats["followers"])))
            total = stats["loc_add"] - stats["loc_del"]
            plus, minus = f"{n(stats['loc_add'])}++", f"{n(stats['loc_del'])}--"
            value = f"{n(total)} ( {plus}, {minus} )"
            line = kv("Lines of Code on GitHub", value)
            line[-1:] = [("val", f"{n(total)} ( "), ("add", plus), ("fg", ", "), ("del", minus), ("fg", " )")]
            lines.append(line)
        elif not key:
            lines.append([])
        else:
            lines.append(kv(key, value))
    return lines


# ---------------------------------------------------------------- SVG

FONT = "ConsolasFallback,Consolas,'DejaVu Sans Mono','Liberation Mono',monospace"


def svg(theme, stats, today):
    t = THEMES[theme]
    if ART == "portrait":
        import portrait
        art = portrait.render(light_mode=(theme == "light"))
    else:
        art = penguin.render(light_mode=(theme == "light"))
    info = build_info(stats, today)

    art_font, art_lh = 13, 17.4
    info_font, info_lh = 16, 20
    pad = 24
    art_w = len(art[0]) * art_font * 0.6
    info_x = pad + art_w + 28
    height = max(len(art) * art_lh, len(info) * info_lh) + pad * 2
    width = info_x + WIDTH * info_font * 0.6 + pad
    art_y0 = pad + (height - pad * 2 - len(art) * art_lh) / 2 + art_font

    out = [
        f'<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" font-family="{FONT}" '
        f'width="{width:.0f}px" height="{height:.0f}px" viewBox="0 0 {width:.0f} {height:.0f}">',
        "<style>",
        f".fg{{fill:{t['fg']}}} .key{{fill:{t['key']}}} .val{{fill:{t['val']}}} .dot{{fill:{t['dot']}}}",
        f".add{{fill:{t['add']}}} .del{{fill:{t['del']}}}",
        "".join(f" .{k}{{fill:{t[k]}}}" for k in ("body", "white", "orange", "eye", "glint")),
        "text,tspan{white-space:pre}",
        "</style>",
        f'<rect width="{width:.0f}" height="{height:.0f}" fill="{t["bg"]}" rx="15"/>',
        f'<text x="{pad}" y="{art_y0:.1f}" class="fg" font-size="{art_font}px">',
    ]
    for i, row in enumerate(art):
        y = art_y0 + i * art_lh
        # agrupa caracteres consecutivos da mesma cor
        runs, cur, buf = [], None, ""
        for ch, k in row:
            k = k or "fg"
            if k != cur and buf:
                runs.append((cur, buf))
                buf = ""
            cur, buf = k, buf + ch
        runs.append((cur, buf.rstrip()))
        parts = "".join(f'<tspan class="{k}">{escape(s)}</tspan>' if k != "fg" else escape(s)
                        for k, s in runs if s)
        out.append(f'<tspan x="{pad}" y="{y:.1f}">{parts}</tspan>')
    out.append("</text>")

    info_y0 = pad + (height - pad * 2 - len(info) * info_lh) / 2 + info_font
    out.append(f'<text x="{info_x:.0f}" y="{info_y0:.1f}" class="fg" font-size="{info_font}px">')
    for i, line in enumerate(info):
        y = info_y0 + i * info_lh
        parts = "".join(f'<tspan class="{k}">{escape(s)}</tspan>' for k, s in line)
        out.append(f'<tspan x="{info_x:.0f}" y="{y:.1f}">{parts}</tspan>')
    out.append("</text></svg>")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    today = dt.date.today()
    stats = fetch_stats()
    print(stats)
    for theme in THEMES:
        with open(f"{theme}_mode.svg", "w", encoding="utf-8") as f:
            f.write(svg(theme, stats, today))
