#!/usr/bin/env python3
"""마치마자 단일 파일 파이프라인 — 예약 실행용 부트스트랩.

data.json 하나로 카드/포스터 + 9:16 영상 + 검수까지 처리합니다.
새 세션에서 이 파일 하나만 있으면 동작합니다.
사용: python3 pipeline.py <콘텐츠폴더>
"""
import sys, json, re, pathlib, subprocess, tempfile, html as H, datetime as dt

ROOT = pathlib.Path(__file__).resolve().parent.parent

T = """:root{--ink:#16202E;--ink-soft:#4A5666;--paper:#FBF8F3;--paper-2:#F2ECE1;
--line:#DED5C6;--cat-health:#2E6B5E;--cat-money:#1F5C8B;--cat-life:#C2703D;
--font:"Noto Sans CJK KR","Noto Sans KR",sans-serif}
*{margin:0;padding:0;box-sizing:border-box;-webkit-font-smoothing:antialiased}
body{font-family:var(--font);background:var(--paper);color:var(--ink)}
"""

CATS = json.loads((pathlib.Path(__file__).resolve().parent.parent /
                   "categories.json").read_text(encoding="utf-8"))["카테고리"]

def cat_color(name, accent=0):
    """카테고리 색. accent 는 그 계열 안의 몇 번째 변주인가입니다.

    같은 카테고리 글이 쌓이면 전부 같은 색이 됩니다 — 건강보험만 65편 계획이라
    그대로 두면 65편이 한 덩어리로 보입니다. 계열 안에서 돌리면
    브랜드는 유지되면서 나란히 놓았을 때 다른 글로 보입니다.

    accent 는 data.json 의 meta.accent 에서 옵니다. 없으면 0 입니다.
    직전 2편과 같으면 lint_sameness 가 경고합니다.
    """
    c = CATS.get(name) or {}
    pal = c.get("강조색")
    if pal:
        return pal[int(accent) % len(pal)]
    return c.get("색", "#2E6B5E")


# 지금 글의 강조색 번호. build_images() 가 data.json 에서 읽어 세웁니다.
ACCENT = 0

# 톤·금칙 패턴은 여기 없습니다 — `lint_tone.py` 가 유일한 출처입니다.
# 위에서 지운 두 번째 게이트가 쓰던 복사본(FAIL_PAT·BANNED·AXES)이 남아 있었습니다.
def esc(s): return H.escape(str(s))
def az(t,b,p,f): return max(f,int(b-len(t)*p))

# ── 채널 핸들 ─────────────────────────────────────────────────────────
# 인스타·쓰레드만 @machi_maza 입니다. machimaza 는 이미 쓰이고 있었습니다.
# 카드는 인스타로 가고 포스터는 블로그로 가므로, 붙는 핸들이 다릅니다.
# 값은 channels.json 한 곳에만 둡니다 — 예전에는 세 파일에 흩어져 있었습니다.
def handle(key=None):
    d = json.loads((ROOT / "channels.json").read_text(encoding="utf-8"))
    if key:
        for c in d["채널"]:
            if c["키"] == key:
                return c["핸들"]
        raise SystemExit(f"channels.json 에 '{key}' 가 없습니다")
    return d["기본핸들"]


def page(body_css, cls, inner, w, h):
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>{T}\n{body_css}'
            f'</style></head><body style="--cat:{cat_color(cls, ACCENT)}">{inner}</body></html>')

CARD_CSS = """.through{margin-left:auto;background:var(--ink);color:var(--paper);font-size:26px;font-weight:900;padding:10px 22px;border-radius:999px;white-space:nowrap}
/* 채널 워터마크 — 왼쪽 위 모서리. 영상(motion.py)과 같은 자리입니다.
   예전에는 분야칩 줄과 제목 사이에 끼어 있어 둘 사이에 묻혔습니다. */
.brand{position:absolute;top:48px;left:48px;font-size:26px;font-weight:800;
color:var(--ink-soft);letter-spacing:.08em}
.wrap{width:1080px;height:1350px;padding:128px 76px 64px;display:flex;flex-direction:column}
.top{display:flex;align-items:center}.badge{border:2px solid var(--cat);color:var(--cat);background:transparent;font-size:26px;
font-weight:900;padding:10px 22px;border-radius:999px}.pg{margin-left:auto;font-size:26px;
font-weight:800;color:var(--ink-soft)}.dd{margin-left:14px;background:var(--ink);color:var(--paper);
font-size:22px;font-weight:900;padding:8px 16px;border-radius:10px}
.body{flex:1;display:flex;flex-direction:column;justify-content:flex-start;padding-top:20px}
.step{font-family:inherit;font-size:24px;font-weight:800;color:var(--ink-soft);
letter-spacing:.08em;margin-top:26px}
.cv .head{line-height:1.15;margin-bottom:8px}
.cv .desc{font-size:42px;margin-top:22px}
.cv .pts{margin-top:52px}
.cv .pt{padding:24px 2px;font-size:38px}
.cv .pt span{min-width:250px}
.cv .voice{font-size:36px;padding:28px}
.pts{margin-top:30px;border-top:2px solid var(--line);padding-top:6px}
.pt{display:flex;align-items:baseline;gap:20px;padding:16px 2px;
border-bottom:1px solid var(--line);font-size:32px;word-break:keep-all}
.pt span{color:var(--ink-soft);font-weight:700;flex:none;min-width:210px}
.pt b{font-weight:800;color:var(--ink)}
.voice{margin-top:auto;padding:22px 24px;background:var(--paper-2);border-radius:14px;
font-size:32px;font-weight:700;line-height:1.5;color:var(--ink);word-break:keep-all}
.voice::before{content:"짚고 넘어가면 ";color:var(--cat);font-weight:900}
.foot{display:flex;font-size:22px;color:var(--ink-soft);border-top:2px solid var(--line);
padding-top:20px;margin-top:24px}
.fr{margin-left:auto;font-weight:800}
.kicker{font-size:38px;font-weight:800;color:var(--cat);margin-bottom:18px}
.head{font-weight:900;line-height:1.2;letter-spacing:-.035em}
.big{font-size:132px;font-weight:900;color:var(--cat);letter-spacing:-.05em;margin:24px 0}
.desc{margin-top:28px;font-size:36px;font-weight:500;line-height:1.55;color:var(--ink-soft)}
.foot{font-size:22px;color:var(--ink-soft);border-top:2px solid var(--line);padding-top:22px}
.head,.desc,.sub2,.li,.note{word-break:keep-all}
.sub2{margin-top:18px;font-size:34px;font-weight:700;color:var(--ink-soft);line-height:1.45}
.big{white-space:nowrap;font-variant-numeric:tabular-nums}
.lab2{font-size:28px;font-weight:800;color:var(--ink-soft);margin-bottom:8px}
.v2{font-size:66px;font-weight:900;letter-spacing:-.04em;white-space:nowrap;
font-variant-numeric:tabular-nums;margin-bottom:12px}
.bar{height:20px;background:var(--line);border-radius:999px;overflow:hidden}
.bar>i{display:block;height:100%;background:var(--cat);border-radius:999px}
.cmp{display:flex;flex-direction:column;gap:34px;margin-top:26px}
.li{display:flex;align-items:center;gap:18px;font-size:44px;font-weight:800;margin-bottom:20px}
.li b{width:14px;height:14px;border-radius:999px;background:var(--cat);flex:none}
.note{margin-top:24px;font-size:30px;font-weight:700;color:var(--ink-soft);
border-left:5px solid var(--line);padding-left:18px;line-height:1.45}
.tbl2{width:100%;border-collapse:collapse;font-size:32px;font-variant-numeric:tabular-nums}
.tbl2 th{padding:10px;border-bottom:3px solid var(--ink);font-size:26px;font-weight:800;
color:var(--ink-soft);text-align:right}
.tbl2 th:first-child{text-align:left}
.tbl2 td{padding:14px 10px;border-bottom:2px solid var(--line);font-weight:700}
.tbl2 td.c1{text-align:right;color:var(--ink-soft);font-weight:800}
.tbl2 td.c2{text-align:right;color:var(--cat);font-weight:900}"""

POST_CSS = """.ptbl{width:100%;border-collapse:collapse;font-size:38px;
font-variant-numeric:tabular-nums;margin-top:8px}
.ptbl th{padding:10px 12px;border-bottom:3px solid var(--ink);font-size:26px;
font-weight:800;color:var(--ink-soft);text-align:right}
.ptbl th:first-child{text-align:left}
.ptbl td{padding:18px 12px;border-bottom:2px solid var(--line);font-weight:800}
.ptbl td.c1{text-align:right;color:var(--ink-soft)}
.ptbl td.c2{text-align:right;color:var(--cat);font-weight:900}
.cmpr{flex:1;display:flex;flex-direction:column;justify-content:center;margin-bottom:26px}
.cmpr .cl{font-size:32px;font-weight:800;color:var(--ink-soft);margin-bottom:6px}
.cmpr .cv{font-size:48px;font-weight:900;color:var(--cat);margin-bottom:10px}
.cmpr .cb{height:16px;background:var(--line);border-radius:999px;overflow:hidden}
.cmpr .cb>i{display:block;height:100%;background:var(--cat);border-radius:999px}
.wrap{width:1080px;height:1350px;padding:128px 72px 64px;display:flex;flex-direction:column}
.top{display:flex;align-items:center;gap:16px;margin-bottom:28px}
.badge{border:2px solid var(--cat);color:var(--cat);background:transparent;font-size:26px;font-weight:800;padding:9px 20px;border-radius:999px}
.through{margin-left:auto;background:var(--ink);color:var(--paper);font-size:26px;font-weight:900;padding:10px 22px;border-radius:999px;white-space:nowrap}
.dd{background:var(--ink);color:var(--paper);font-size:22px;font-weight:900;padding:8px 16px;border-radius:10px}
/* 채널 워터마크 — 왼쪽 위 모서리. 영상(motion.py)과 같은 자리입니다.
   예전에는 분야칩 줄과 제목 사이에 끼어 있어 둘 사이에 묻혔습니다. */
.brand{position:absolute;top:48px;left:48px;font-size:26px;font-weight:800;
color:var(--ink-soft);letter-spacing:.08em}
h1{font-weight:900;line-height:1.18;letter-spacing:-.035em}
.sub{margin-top:18px;font-size:30px;color:var(--ink-soft);line-height:1.45}
.rule{height:6px;background:var(--cat);width:96px;border-radius:3px;margin:32px 0 30px}
.list{display:flex;flex-direction:column;flex:1}
.row{display:flex;align-items:center;gap:22px;background:var(--paper-2);border-radius:20px}
.n{flex:0 0 auto;border-radius:14px;background:var(--cat);color:#fff;font-weight:900;
display:flex;align-items:center;justify-content:center}
.lab{font-weight:800;letter-spacing:-.03em;line-height:1.2}
.val{margin-left:auto;font-weight:900;color:var(--cat);white-space:nowrap}
.foot{margin-top:26px;display:flex;flex-direction:column;gap:16px}
.src{font-size:22px;color:var(--ink-soft);white-space:nowrap;
overflow:hidden;text-overflow:ellipsis}
.cta{background:var(--ink);color:var(--paper);font-size:26px;font-weight:800;
padding:18px 28px;border-radius:14px;text-align:center;word-break:keep-all}"""

# 영상 장면 CSS 는 여기 없습니다 — `motion.py` 가 유일한 영상 렌더러입니다.
# 예전에 SCENE_CSS 라는 복사본이 여기 있었는데, 아무도 쓰지 않으면서
# 여백값만 옛것(150/430)으로 남아 '어느 쪽이 진짜냐'를 흐렸습니다.


def shoot(pages, outdir, w, h):
    from playwright.sync_api import sync_playwright
    outdir.mkdir(parents=True, exist_ok=True); out = []
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width":w,"height":h})
        for name, html in pages:
            pg.set_content(html, wait_until="load"); pg.wait_for_timeout(120)
            f = outdir/name; pg.screenshot(path=str(f), clip={"x":0,"y":0,"width":w,"height":h}); out.append(f)
        b.close()
    return out

def build_images(d, base):
    global ACCENT
    ACCENT = d["meta"].get("accent", 0)
    m, items = d["meta"], d["items"]; n = len(items); total = n+2
    dd = f'<div class="dd">{esc(m["dday"])}</div>' if m.get("dday") else ""
    # meta.layout 이 포스터 구성을 정합니다.
    # 오랫동안 이 필드는 선언만 되고 아무도 읽지 않았습니다 — 그래서 모든 글의
    # 포스터가 똑같이 나왔고, CLAUDE.md 3장의 '3종 로테이션'은 종이 위에만 있었습니다.
    lay = m.get("layout", "list")
    gap,pad,nw,nf,lf,vf = (18,22,74,38,44,46) if n<=6 else (12,15,62,32,36,38)
    if lay == "table":
        # 값이 두 개 이상일 때 (연도 대비 등). 번호를 빼고 표로 읽힙니다.
        two = any(it.get("value_2026") or it.get("employed") for it in items)
        head = ("<tr><th>구간</th><th>" + esc(m.get("col1","기준")) + "</th><th>"
                + esc(m.get("col2","비교")) + "</th></tr>") if two else ""
        rows = f'<table class="ptbl">{head}' + "".join(
            f'<tr><td>{esc(it["label"])}</td>'
            + (f'<td class="c2">{esc(it["value"])}</td>' if two else "")
            + (f'<td class="c1">{esc(it.get("value_2026") or it.get("employed"))}</td>'
               if two else f'<td class="c2">{esc(it["value"])}</td>')
            + '</tr>' for it in items) + '</table>'
    elif lay == "compare":
        # 막대 길이는 금액의 비율입니다.
        # 예전에는 여기서 len(문자열)을 비교했습니다 — 게다가 두 곳의 정규식이
        # 서로 달라서("[^\d]" 와 "^\d") 어떤 값을 넣어도 전부 100% 가 나왔습니다.
        # compare 레이아웃을 처음 쓰는 글에서야 드러났습니다.
        # 막대가 다 같으면 이 레이아웃을 고른 이유가 사라집니다.
        def _amt(v):
            s = re.sub(r"[^\d]", "", v)
            return int(s) if s else 0
        mx = max((_amt(it["value"]) for it in items), default=0) or 1
        rows = "".join(
            f'<div class="cmpr"><div class="cl">{esc(it["label"])}</div>'
            f'<div class="cv">{esc(it["value"])}</div>'
            f'<div class="cb"><i style="width:{min(100, _amt(it["value"]) / mx * 100):.0f}%"></i></div></div>'
            for it in items)
    else:
        rows = "".join(f'<div class="row" style="padding:{pad}px 26px;margin-bottom:{gap}px">'
            f'<div class="n" style="width:{nw}px;height:{nw}px;font-size:{nf}px">{it.get("rank",i+1)}</div>'
            f'<div class="lab" style="font-size:{lf}px">{esc(it["label"])}</div>'
            f'<div class="val" style="font-size:{vf}px">{esc(it["value"])}</div></div>'
            for i,it in enumerate(items))
    # 기관명이 '국민건강보험공단'과 '국민건강보험공단 법령정보'처럼 갈라져
    # 같은 기관이 두 번 찍히고 세 줄로 깨졌습니다. 앞부분 기준으로 합칩니다.
    _iss = []
    for _s in d["sources"]:
        base_name = _s["issuer"].split()[0]
        if base_name not in _iss:
            _iss.append(base_name)
    src = " · ".join(_iss)
    poster = page(POST_CSS, m["category"], f'''<div class="brand">{handle("tistory")}</div>
<div class="wrap">
<div class="top"><div class="badge">{m["category"]}</div>{("<div class='through'>"+esc(m["throughline"])+"</div>") if m.get("throughline") else ""}{dd}</div>
<h1 style="font-size:{az(m["title"],76,0.9,52)}px">{esc(m["title"])}</h1>
<div class="sub">{esc(m.get("subtitle",d["summary"])[:70])}</div><div class="rule"></div>
<div class="list">{rows}</div><div class="foot"><div class="src">출처 · {esc(src)} ({m["publish_date"]} 기준)</div>
<div class="cta">{esc(d.get("cta","저장해두세요"))}</div></div></div>''', 1080, 1350)
    # 카드는 영상과 같은 flow 를 그립니다.
    # 예전에는 items 를 그대로 카드로 찍어서, 카드 다섯 장이 전부 가격표였습니다.
    # 영상에서 고친 문제(자격·기한·신청 방법이 없음)가 카드에도 똑같이 있었습니다.
    _src1 = (d["sources"][0]["issuer"].split()[0] if d.get("sources") else "")
    _basis = m.get("basis") or f'{m["publish_date"][:4]}년 기준'

    def shell(body, foot, step=None, voice=None, points=None, cover=False):
        """카드는 소리가 없습니다. 영상이 음성으로 말하는 것을 글로 넣어야 합니다.

        예전 뼈대는 본문을 세로 가운데 정렬해서, 세 줄짜리 카드가 1350px 한가운데
        떠 있었습니다. 잉크 비율 4.2% — 화면의 95%가 빈 공간이었습니다.
        위에서부터 채우고, 해석 문장과 근거를 함께 싣습니다.
        """
        th = (f"<div class='through'>{esc(m['throughline'])}</div>"
              if m.get("throughline") else "")
        pg = f'<div class="step">{step}</div>' if step else ""
        vo = f'<div class="voice">{esc(voice)}</div>' if voice else ""
        pts = ""
        if points:
            pts = '<div class="pts">' + "".join(
                f'<div class="pt"><span>{esc(k)}</span><b>{esc(v)}</b></div>'
                for k, v in points) + '</div>'
        return page(CARD_CSS, m["category"], f'''<div class="brand">{handle("instagram")}</div>
<div class="wrap{' cv' if cover else ''}">
<div class="top"><div class="badge">{esc(m["category"])}</div>{th}</div>
{pg}<div class="body">{body}{pts}{vo}</div>
<div class="foot">{esc(_basis)} · {esc(_src1)}<span class="fr">{foot}</span></div>
</div>''', 1080, 1350)

    def card_for(sc, idx, last):
        # 마지막 장에는 핸들로 서명합니다 — 캐러셀 마지막 장이 캡처되는 자리입니다
        ty, foot = sc["type"], (handle("instagram") if last else "넘겨서 →")
        step = f'{idx+1} / {len(scenes)}'
        voice = sc.get("voice")
        points = sc.get("points")
        cap = f'<div class="desc">{esc(sc.get("screen",""))}</div>'
        if ty == "hook":
            # 표지는 스크롤이 멈추는 자리입니다. 본문 카드와 같은 크기로 두면
            # 넘길 이유를 주지 못합니다. 제목과 요점을 키웁니다.
            return shell(f'<div class="cover"><div class="head" '
                         f'style="font-size:{az(m["title"],104,1.1,64)}px">{esc(m["title"])}</div>'
                         f'{cap}</div>', foot, step, voice, points, cover=True)
        if ty == "fact":
            sub = f'<div class="sub2">{esc(sc["sub"])}</div>' if sc.get("sub") else ""
            return shell(f'<div class="kicker">{esc(sc["label"])}</div>'
                         f'<div class="big" style="font-size:{max(72, 128 - len(sc["big"]) * 5)}px">'
                         f'{esc(sc["big"])}</div>{sub}{cap}', foot, step, voice, points)
        if ty == "compare":
            b, a = sc["before"], sc["after"]
            nb = re.sub(r"[^\d]", "", b["value"]); na = re.sub(r"[^\d]", "", a["value"])
            r = (int(na) / int(nb) * 100) if nb and int(nb) else 100
            return shell(
                f'<div class="head" style="font-size:56px">{esc(sc["label"])}</div><div class="cmp">'
                f'<div><div class="lab2">{esc(b["label"])}</div>'
                f'<div class="v2" style="color:var(--ink-soft)">{esc(b["value"])}</div>'
                f'<div class="bar"><i style="width:100%;background:var(--line)"></i></div></div>'
                f'<div><div class="lab2">{esc(a["label"])}</div>'
                f'<div class="v2" style="color:var(--cat)">{esc(a["value"])}</div>'
                f'<div class="bar"><i style="width:{r:.1f}%"></i></div></div></div>{cap}', foot, step, voice, points)
        if ty == "list":
            lis = "".join(f'<div class="li"><b></b><span>{esc(x)}</span></div>' for x in sc["items"])
            note = f'<div class="note">{esc(sc["note"])}</div>' if sc.get("note") else ""
            return shell(f'<div class="head" style="font-size:56px">{esc(sc["label"])}</div>'
                         f'<div style="margin-top:34px">{lis}</div>{note}{cap}', foot, step, voice, points)
        if ty == "table":
            cols = sc.get("columns") or ["구간", "금액"]
            head = "".join(f"<th>{esc(c)}</th>" for c in cols)
            # rows 가 있으면 그대로 그립니다.
            # items 에서 열을 추측하다가 2025년·2026년 열에 같은 값이 들어간 사고가 있었습니다.
            if sc.get("rows"):
                # accent_col — 어느 열이 '지금 봐야 할 값'인지 작성자가 정합니다.
                # 기본값(마지막 열)에 맡겼더니 설명은 2025년을 가리키는데
                # 강조색은 2026년에 붙어 눈과 글이 따로 놀았습니다.
                ac = sc.get("accent_col", len(cols) - 1)
                body = "".join(
                    "<tr>" + "".join(
                        f'<td class="{"c2" if k == ac else ("c1" if k else "")}">{esc(c)}</td>'
                        for k, c in enumerate(r)) + "</tr>"
                    for r in sc["rows"])
            else:
                body = "".join(
                    f'<tr><td>{esc(i["label"].replace("월급 ", ""))}</td>'
                    + (f'<td>{esc(i.get("employed", i["value"]))}</td>' if len(cols) > 2 else "")
                    + f'<td>{esc(i["value"])}</td></tr>' for i in items)
            note = f'<div class="note">{esc(sc["note"])}</div>' if sc.get("note") else ""
            return shell(f'<table class="tbl2"><tr>{head}</tr>{body}</table>{note}{cap}', foot, step, voice, points)
        raise ValueError(f"카드로 그릴 수 없는 장면 유형: {ty}")

    scenes = d.get("flow", {}).get("scenes")
    pages = [("poster.png", poster)]
    if scenes:
        for i, sc in enumerate(scenes):
            pages.append((f"card_{i+1:02d}.png", card_for(sc, i, i == len(scenes) - 1)))
    else:
        raise ValueError("data.json 에 flow.scenes 가 없습니다 — 카드를 items 로 찍던 방식은 폐기했습니다")

    w = shoot(pages, base/"images", 1080, 1350)
    alt = [f'poster.png\t{m["category"]} 정보 카드. {m["title"]}.']
    for i, sc in enumerate(scenes):
        t = sc.get("label") or m["title"]
        alt.append(f'card_{i+1:02d}.png\t{t}. {sc.get("screen","")}')
    (base/"images"/"alt.txt").write_text("\n".join(alt), encoding="utf-8")
    print(f"[images] {len(w)}장 + alt.txt")
    import motion
    motion.stamp(base, "images")

def build_video(d, base, target=None):
    """영상은 motion.py 가 담당합니다.

    예전에는 여기서 정지 이미지에 zoompan(느린 확대)을 걸었습니다.
    그 방식은 CLAUDE.md 9장에서 폐기했습니다 — AI 양산 콘텐츠의 서명이라
    플랫폼이 잡아내는 바로 그 신호이기 때문입니다.
    """
    import motion
    out, dur, has_narr = motion.render(d, base)
    print(f"[video] {out.name} · {dur:.1f}초 · 구조 {d['meta'].get('video_structure','countdown')} "
          f"· 음성 {'있음' if has_narr else '없음(무음)'}")
    return out


# 게이트는 여기 없습니다 — `verify.py` 가 유일한 검수 게이트입니다.
#
# 예전에 이 자리에 verify() 라는 두 번째 게이트가 있었습니다. verify.py 와
# 같은 항목(고지문구·텍스트 표·이미지 수·본문 길이·H2·톤)을 각자 검사했고,
# 그 중 하나(CAT2KEY)는 아예 정의되지 않아 실행하면 NameError 로 죽었습니다.
# 아무도 안 돌려서 아무도 몰랐습니다. 게이트가 둘이면 어느 쪽이 진짜인지
# 알 수 없고, 죽은 쪽은 조용히 썩습니다. 하나만 둡니다.


if __name__ == "__main__":
    base = pathlib.Path(sys.argv[1])
    d = json.loads((base/"data.json").read_text(encoding="utf-8"))
    build_images(d, base)
    build_video(d, base)
    print("\n검수는 게이트가 합니다:  python3 scripts/verify.py " + str(base))
