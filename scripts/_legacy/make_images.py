"""data.json -> images/  (format: poster | carousel | hybrid)"""
import sys, pathlib, html as H
from render import fill, shoot, autosize, load

def esc(s): return H.escape(str(s))

def poster_html(d):
    m, items = d["meta"], d["items"]
    n = len(items)
    gap, pad, nw, nf = (18, 22, 74, 38) if n <= 6 else (12, 15, 62, 32)
    lf = 44 if n <= 6 else 36
    vf = 46 if n <= 6 else 38
    rows = "".join(
        f'<div class="row"><div class="n">{it.get("rank", i+1)}</div>'
        f'<div class="lab">{esc(it["label"])}</div>'
        f'<div class="val">{esc(it["value"])}</div></div>'
        for i, it in enumerate(items))
    src = " · ".join(dict.fromkeys(s["issuer"] for s in d["sources"]))
    return fill("poster.html", {
        "CAT": m["category"], "TITLE": esc(m["title"]),
        "SUB": esc(m.get("subtitle", d["summary"])[:70]),
        "H1": autosize(m["title"], 76, 0.9, 52),
        "GAP": gap, "PAD": pad, "NW": nw, "NF": nf, "LF": lf, "VF": vf,
        "ROWS": rows, "SRC": f"출처 · {esc(src)} ({m['publish_date']} 기준)",
        "CTA": esc(d.get("cta", "저장해두세요")),
    })

def card_pages(d):
    m, items = d["meta"], d["items"]
    total = len(items) + 2
    out = []
    # 1) 표지
    out.append(("card_01.png", fill("card.html", {
        "CAT": m["category"], "PG": f"1/{total}",
        "KICKER": f'<div class="kicker">{esc(d["hook"])}</div>',
        "HEAD": f'<div class="head">{esc(m["title"])}</div>',
        "DESC": f'<div class="desc">{esc(d["summary"])}</div>',
        "HF": autosize(m["title"], 92, 1.1, 60), "DF": 34,
        "FOOT": "넘겨서 확인하세요 →"})))
    # 2) 항목
    for i, it in enumerate(items):
        out.append((f"card_{i+2:02d}.png", fill("card.html", {
            "CAT": m["category"], "PG": f"{i+2}/{total}",
            "KICKER": f'<div class="kicker">{it.get("rank", i+1)}</div>',
            "HEAD": f'<div class="head">{esc(it["label"])}</div>',
            "BIG": f'<div class="big">{esc(it["value"])}</div>',
            "DESC": f'<div class="desc">{esc(it["detail"])}</div>',
            "HF": autosize(it["label"], 78, 1.4, 52), "DF": 34,
            "FOOT": esc(next(s["issuer"] for s in d["sources"] if s["id"] == it["source_id"]))})))
    # 3) 마무리
    out.append((f"card_{total:02d}.png", fill("card.html", {
        "CAT": m["category"], "PG": f"{total}/{total}",
        "KICKER": '<div class="kicker">정리하면</div>',
        "HEAD": f'<div class="head">{esc(d["summary"])}</div>',
        "DESC": f'<div class="desc">{esc(d.get("cta",""))}<br>전문은 프로필 링크에서 확인하세요.</div>',
        "HF": autosize(d["summary"], 74, 0.85, 46), "DF": 34,
        "FOOT": "@machimaza"})))
    return out

def alt_texts(d, names):
    m, items = d["meta"], d["items"]
    ax = m.get("axis", {}).get("type", "")
    out = []
    for n in names:
        if n == "poster.png":
            out.append((n, f'{m["category"]} 정보 카드. {m["title"]}. '
                           f'{ax + "별 " if ax else ""}{len(items)}개 항목 표.'))
        elif n == "card_01.png":
            out.append((n, f'{m["title"]} 표지 카드. {d["hook"]}'))
        else:
            try:
                i = int(n.split("_")[1].split(".")[0]) - 2
                it = items[i]
                out.append((n, f'{it["label"]} {it["value"]}. {it["detail"][:60]}'))
            except (IndexError, ValueError):
                out.append((n, f'{m["title"]} 요약 카드. {d["summary"][:60]}'))
    return out

if __name__ == "__main__":
    base = pathlib.Path(sys.argv[1])
    d = load(base / "data.json")
    fmt = d["meta"]["format"]
    pages = []
    if fmt in ("poster", "hybrid"):
        pages.append(("poster.png", poster_html(d)))
    if fmt in ("carousel", "hybrid"):
        pages += card_pages(d)
    w = shoot(pages, base / "images", 1080, 1350)
    # 대체 텍스트 — 인스타 업로드 시 붙입니다. 접근성 + 내부 검색 노출.
    alt = [f"{n}\t{a}" for n, a in alt_texts(d, [x.name for x in w])]
    (base / "images" / "alt.txt").write_text("\n".join(alt), encoding="utf-8")
    print(f"[images] {len(w)}장 생성 → {base/'images'}")
    for p in w: print("  -", p.name)
    print(f"[images] alt.txt 생성 ({len(alt)}줄)")
