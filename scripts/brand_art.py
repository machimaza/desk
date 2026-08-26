#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""채널 대표이미지·배너를 그립니다.

    python3 scripts/brand_art.py            # 세 안 전부
    python3 scripts/brand_art.py --pick b   # 고른 안만 최종 크기로

왜 코드로 그리나 — 여섯 채널이 같은 그림을 써야 하는데, 손으로 만든 파일은
어느 것이 최신인지 금방 흐려집니다. 색은 brand/tokens.css 하나에서만 옵니다.

규격 (2026-08 확인)
    프로필   800×800     · 플랫폼이 원형으로 자릅니다 → 원 밖은 장식만
    유튜브   2560×1440   · 모두에게 보이는 자리는 가운데 1546×423 뿐입니다
                          글자는 전부 그 안에 둡니다
    허브 OG  1200×630
"""
import pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "brand" / "art"


def tokens():
    """brand/tokens.css 가 색의 유일한 출처입니다."""
    css = (ROOT / "brand" / "tokens.css").read_text(encoding="utf-8")
    return dict(re.findall(r"--([a-z0-9-]+)\s*:\s*(#[0-9A-Fa-f]{6})", css))


T = tokens()
INK, PAPER, AMBER = T["ink"], T["paper"], T["accent"]
# 다채로움은 새 색이 아니라 우리가 이미 쓰는 카테고리 색에서 나옵니다.
# 새 색을 지어내면 tokens.css 와 어긋나고 test_brand.py 가 멈춥니다.
SPECTRUM = [T["cat-health"], T["health-2"], T["money-2"], T["cat-money"],
            T["pension"], T["employ"], T["grant-0"], T["cat-life"],
            T["grant-1"], T["warn"]]

FONT = '"Noto Sans CJK KR","Noto Sans KR",sans-serif'


def sq(x, y, w, h, r, fill, op=1.0):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}"'
            f' fill="{fill}" opacity="{op}"/>')


def hangul(x, y, size, fill, text="마", weight=900, anchor="middle"):
    return (f'<text x="{x}" y="{y}" font-family={FONT!r} font-size="{size}"'
            f' font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"'
            f' dominant-baseline="central">{text}</text>')


# ── 마크 — 네 조각에 네 글자 ────────────────────────────────────────
# 해는 뺐습니다. 쓰던 그림이 해라서 이어받았을 뿐, '마침맞다(꼭 알맞다)' 와
# 아무 상관이 없었습니다.
# 2×2 조각에 마·치·마·자 한 글자씩. 이름이 그대로 마크가 되고,
# 조각이 빈틈없이 맞물린 모양이 '꼭 알맞다' 를 그립니다.
# 색 조합만 다른 세 안입니다 — 배치는 같습니다.

LETTERS = ["마", "치", "마", "자"]

PALETTES = {
    # 1) 카테고리 대표색 그대로. 우리 글·영상에서 이미 쓰는 네 색입니다.
    "1": ([T["cat-health"], T["cat-money"], T["grant-0"], T["cat-life"]], PAPER, INK),
    # 2) 대비를 키운 조합. 앰버(시그니처)를 넣어 가장 눈에 띕니다.
    "2": ([T["health-2"], T["money-2"], AMBER, T["warn"]], PAPER, INK),
    # 3) 어두운 바탕. 피드에서 흰 배경 계정들 사이에 섞이지 않습니다.
    "3": ([T["health-1"], T["cat-money"], AMBER, T["employ"]], INK, PAPER),
}


def mark(kind, S, _dark=None):
    """정사각 안 2×2. 원형으로 잘려도 네 글자가 남게 안쪽에 둡니다."""
    colors, _bg, _fg = PALETTES[kind]
    c = S / 2
    g = S * .225          # 조각 한 변
    gapp = S * .028       # 조각 사이
    ox = oy = c - (g * 2 + gapp) / 2
    out = []
    for i, ch in enumerate(LETTERS):
        row, col = divmod(i, 2)
        x, y = ox + col * (g + gapp), oy + row * (g + gapp)
        out.append(sq(x, y, g, g, S * .05, colors[i]))
        out.append(hangul(x + g / 2, y + g / 2, g * .66, PAPER, ch))
    return "".join(out)


def profile(kind, S=800):
    _, bg, _ = PALETTES[kind]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{S}" height="{S}"'
            f' viewBox="0 0 {S} {S}">'
            f'<rect width="{S}" height="{S}" fill="{bg}"/>{mark(kind, S)}</svg>')


# ── 배너 ────────────────────────────────────────────────────────────

def banner(kind, W=2560, H=1440):
    """유튜브 배너.

    **가운데 띠 안에서 끝나야 합니다.** 2560×1440 을 올리지만 데스크톱은
    가운데 2560×423 만, 모바일은 가운데 1546×423 만 보여줍니다.
    처음에 그림을 아래쪽에 뒀더니 TV 말고는 아무 데서도 안 보였습니다.
    """
    colors, bg_c, ink = PALETTES[kind]
    cx, cy = W / 2, H / 2
    band, safe_w = 423.0, 1546.0
    sub = "#B9C2CE" if bg_c == INK else T["ink-soft"]

    m = band * .96
    gap = band * .20
    name_size, slo_size = band * .30, band * .105
    text_w = name_size * 4 * .92
    grp = m + gap + text_w
    mx = cx - grp / 2
    tx = mx + m + gap

    # 띠 밖은 같은 색 조각이 흐르게 둡니다 — TV 에서만 보이는 자리입니다.
    strips = "".join(
        sq(i * (W / 20), cy - band * (1.3 if i % 2 else 1.62),
           W / 20 * .8, band * (.46 if i % 2 else .3), band * .06,
           colors[i % 4], .16) for i in range(20))
    strips += "".join(
        sq(i * (W / 20) + W / 40, cy + band * (.92 if i % 2 else 1.18),
           W / 20 * .8, band * (.4 if i % 2 else .52), band * .06,
           colors[(i + 1) % 4], .16) for i in range(20))

    # 보이는 띠 안에도 색 한 줄. 띠 밖만으로는 데스크톱에서 글자만 남습니다.
    barw = safe_w * .90
    bar = "".join(
        sq(cx - barw / 2 + i * (barw / 4), cy + band * .40,
           barw / 4 * .93, band * .035, band * .018, colors[i], .95)
        for i in range(4))

    body = (f'<rect width="{W}" height="{H}" fill="{bg_c}"/>{strips}{bar}'
            f'<g transform="translate({mx} {cy - m/2})">{mark(kind, m)}</g>'
            f'<text x="{tx}" y="{cy - band*.13}" font-family={FONT!r}'
            f' font-size="{name_size}" font-weight="900" fill="{ink}"'
            f' dominant-baseline="central" letter-spacing="{name_size*.02}">마치마자</text>'
            f'<text x="{tx}" y="{cy + band*.20}" font-family={FONT!r}'
            f' font-size="{slo_size}" font-weight="800" fill="{sub}"'
            f' dominant-baseline="central">마침 필요한 정보를, 알맞게</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}"'
            f' viewBox="0 0 {W} {H}">{body}</svg>'), (cx - safe_w/2, cy - band/2, safe_w, band)


def wide(kind, W, H, tight=False):
    """가로형 공용 — 허브 OG · 네이버 타이틀 · 티스토리 커버.

    유튜브만 '가운데 띠' 제약이 있고 나머지는 판 전체가 보입니다.
    그래서 같은 구성을 판 크기에 맞춰 키우기만 합니다.
    """
    colors, bg_c, ink = PALETTES[kind]
    cx, cy = W / 2, H / 2
    sub = "#B9C2CE" if bg_c == INK else T["ink-soft"]
    band = H * (.52 if tight else .60)     # 구성이 놓일 높이

    m = band * .96
    gap = band * .20
    name_size, slo_size = band * .30, band * .105
    grp = m + gap + name_size * 4 * .92
    if grp > W * .88:                       # 좁은 판에서는 줄여 맞춥니다
        k = W * .88 / grp
        band, m, gap, name_size, slo_size = (band*k, m*k, gap*k, name_size*k, slo_size*k)
        grp = W * .88
    mx = cx - grp / 2
    tx = mx + m + gap

    barw = min(W * .86, grp * 1.02)
    bar = "".join(
        sq(cx - barw / 2 + i * (barw / 4), cy + band * .40,
           barw / 4 * .93, band * .035, band * .018, colors[i], .95)
        for i in range(4))
    deco = "".join(
        sq(i * (W / 14), cy - band * (1.15 if i % 2 else 1.42),
           W / 14 * .78, band * (.4 if i % 2 else .26), band * .06,
           colors[i % 4], .16) for i in range(14))
    deco += "".join(
        sq(i * (W / 14) + W / 28, cy + band * (.85 if i % 2 else 1.08),
           W / 14 * .78, band * (.34 if i % 2 else .46), band * .06,
           colors[(i + 1) % 4], .16) for i in range(14))

    body = (f'<rect width="{W}" height="{H}" fill="{bg_c}"/>{deco}{bar}'
            f'<g transform="translate({mx} {cy - m/2})">{mark(kind, m)}</g>'
            f'<text x="{tx}" y="{cy - band*.13}" font-family={FONT!r}'
            f' font-size="{name_size}" font-weight="900" fill="{ink}"'
            f' dominant-baseline="central" letter-spacing="{name_size*.02}">마치마자</text>'
            f'<text x="{tx}" y="{cy + band*.20}" font-family={FONT!r}'
            f' font-size="{slo_size}" font-weight="800" fill="{sub}"'
            f' dominant-baseline="central">마침 필요한 정보를, 알맞게</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}"'
            f' viewBox="0 0 {W} {H}">{body}</svg>')


def portrait(kind, W=1080, H=1300):
    """네이버 블로그 **모바일 앱 커버** (1080×1300, 세로형).

    가로형과 다른 점이 하나 있습니다 — 네이버가 이 그림 **위에** 블로그명과
    프로필 사진을 얹습니다(커버 스타일에 따라 자리가 다릅니다).
    그래서 아래쪽 35% 는 비워 둡니다. 거기까지 그림을 채우면
    네이버가 얹는 글씨와 우리 글씨가 겹칩니다.
    """
    colors, bg_c, ink = PALETTES[kind]
    cx = W / 2
    sub = "#B9C2CE" if bg_c == INK else T["ink-soft"]
    cy = H * .30                       # 구성의 세로 중심 — 위쪽에 둡니다
    m = W * .32                        # 마크 한 변
    # 슬로건 아래끝이 H*.62 를 넘지 않아야 네이버가 얹는 글씨와 안 겹칩니다.
    # 처음 잡은 값(.34/.34)은 슬로건이 67% 에 놓여 겹쳤습니다.
    name_size, slo_size = W * .105, W * .042

    deco = "".join(
        sq(W * (.04 + .16 * (i % 6)), H * (.03 + .022 * (i // 6)),
           W * .105, H * .018, H * .009,
           colors[i % 4], .18) for i in range(12))
    deco += "".join(
        sq(W * (.06 + .16 * (i % 6)), H * (.86 + .028 * (i // 6)),
           W * .105, H * .018, H * .009,
           colors[(i + 2) % 4], .18) for i in range(12))

    barw = W * .56
    bar = "".join(
        sq(cx - barw / 2 + i * (barw / 4), cy + m * .92,
           barw / 4 * .92, H * .009, H * .005, colors[i], .95)
        for i in range(4))

    body = (f'<rect width="{W}" height="{H}" fill="{bg_c}"/>{deco}'
            f'<g transform="translate({cx - m/2} {cy - m*.62})">{mark(kind, m)}</g>'
            f'<text x="{cx}" y="{cy + m*.55}" font-family={FONT!r}'
            f' font-size="{name_size}" font-weight="900" fill="{ink}"'
            f' text-anchor="middle" dominant-baseline="central"'
            f' letter-spacing="{name_size*.03}">마치마자</text>{bar}'
            f'<text x="{cx}" y="{cy + m*1.16}" font-family={FONT!r}'
            f' font-size="{slo_size}" font-weight="800" fill="{sub}"'
            f' text-anchor="middle" dominant-baseline="central">'
            f'마침 필요한 정보를, 알맞게</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}"'
            f' viewBox="0 0 {W} {H}">{body}</svg>')


def shoot(pages):
    from playwright.sync_api import sync_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--force-device-scale-factor=1"])
        for name, svg, w, h in pages:
            pg = b.new_page(viewport={"width": w, "height": h})
            pg.set_content(
                f'<style>html,body{{margin:0;padding:0;background:transparent}}'
                f'svg{{display:block}}</style>{svg}', wait_until="load")
            pg.wait_for_timeout(120)
            pg.screenshot(path=str(OUT / name),
                          clip={"x": 0, "y": 0, "width": w, "height": h})
            pg.close()
        b.close()


# 채널별 크기 (2026-08 확인)
CHANNEL_SIZES = [
    ("profile.png",        "square", 800,  800,  "유튜브·인스타·쓰레드·틱톡·티스토리 프로필"),
    ("profile_naver.png",  "square", 286,  286,  "네이버 블로그 프로필 (161~286 중 상한)"),
    ("banner_youtube.png", "yt",     2560, 1440, "유튜브 배너 — 가운데 1546×423 만 모두에게 보임"),
    ("naver_title.png",    "wide",   966,  400,  "네이버 블로그 타이틀 (가로 966 고정)"),
    ("cover_wide.png",     "wide",   1600, 900,  "티스토리 커버 등 가로형"),
    ("naver_mobile.png",   "tall",   1080, 1300, "네이버 블로그 모바일 앱 커버 — 아래 35% 는 네이버가 덮습니다"),
    ("og.png",             "wide",   1200, 630,  "허브·공유 미리보기 (og:image)"),
]


def main(argv):
    pick = None
    if "--pick" in argv:
        pick = argv[argv.index("--pick") + 1]
    if not pick:
        pages = []
        for k in PALETTES:
            pages.append((f"profile_{k}.png", profile(k), 800, 800))
            pages.append((f"banner_{k}.png", banner(k)[0], 2560, 1440))
        shoot(pages)
        for name, *_ in pages:
            f = OUT / name
            print(f"[art] {f.relative_to(ROOT)}  {f.stat().st_size//1024}KB")
        print("\n고른 뒤:  python3 scripts/brand_art.py --pick 3")
        return 0

    if pick not in PALETTES:
        print(f"색 조합은 {list(PALETTES)} 중 하나입니다")
        return 1
    pages = []
    for name, how, w, h, _why in CHANNEL_SIZES:
        svg = (profile(pick, w) if how == "square"
               else banner(pick, w, h)[0] if how == "yt"
               else portrait(pick, w, h) if how == "tall"
               else wide(pick, w, h, tight=(h / w < .38)))
        pages.append((name, svg, w, h))
    shoot(pages)
    for (name, how, w, h, why), _ in zip(CHANNEL_SIZES, pages):
        f = OUT / name
        print(f"[art] {str(f.relative_to(ROOT)):32s} {w}×{h}  {f.stat().st_size//1024:>4}KB  {why}")
    print(f"\n색 조합 {pick} 번으로 뽑았습니다. 채널소개.md 의 순서대로 올리세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
