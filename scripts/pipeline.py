#!/usr/bin/env python3
"""마치마자 단일 파일 파이프라인 — 예약 실행용 부트스트랩.

data.json 하나로 카드/포스터 + 9:16 영상 + 검수까지 처리합니다.
새 세션에서 이 파일 하나만 있으면 동작합니다.
사용: python3 pipeline.py <콘텐츠폴더>
"""
import sys, json, re, pathlib, subprocess, tempfile, html as H, datetime as dt

T = """:root{--ink:#16202E;--ink-soft:#4A5666;--paper:#FBF8F3;--paper-2:#F2ECE1;
--line:#DED5C6;--cat-health:#2E6B5E;--cat-money:#1F5C8B;--cat-life:#C2703D;
--font:"Noto Sans CJK KR","Noto Sans KR",sans-serif}
*{margin:0;padding:0;box-sizing:border-box;-webkit-font-smoothing:antialiased}
body{font-family:var(--font);background:var(--paper);color:var(--ink)}
"""

AXES = {"소득구간","연령대","가구형태","지역","직업형태","생활패턴"}
BANNED = {"자산순위","자산 순위","질병위험도","질병 위험도","외모","체형"}
DISC = {"health":"증상이 지속되거나 우려된다면 의료진과 상담","money":"투자 권유가 아닙니다"}
CATS = json.loads((pathlib.Path(__file__).resolve().parent.parent /
                   "categories.json").read_text(encoding="utf-8"))["카테고리"]

def cat_color(name):
    """카테고리 색은 categories.json 에서 옵니다.

    예전에는 CSS 에 .cat-이름 클래스를 하나씩 박아 뒀습니다.
    카테고리를 추가할 때마다 CSS 세 곳을 고쳐야 했고, 빠뜨리면 색이 없는 채로 렌더됐습니다.
    """
    return (CATS.get(name) or {}).get("색", "#2E6B5E")
_D = r"(암|당뇨|고혈압|혈압|혈당|아토피|치매|관절염|골다공증|비염|위염|간염|통풍|불면증|우울증|탈모|디스크|염증|콜레스테롤)"
_E = r"(치료|완치|낫는|낫습|효능|예방|개선|회복|잡아|없애|제거|낮춰|줄여)"
FAIL_PAT = {"과장 후킹":r"충격|이것만 알면|99%가 모르는|반드시 알아야|절대 놓치",
            "단정 표현":r"100% 보장|무조건 (되|받|낫)|확실히 (낫|오릅)",
            # 식품표시광고법 제8조 (10년 이하/1억)
            "질병+효능 조합":_D+r"[^.。\n]{0,20}"+_E,
            "기능성 표방":r"항암|면역력\s*(강화|증진)|염증\s*(제거|완화)|디톡스|해독\s*작용",
            "의약품 오인":r"복용|약\s*대신",
            "부작용 부인":r"부작용\s*(이\s*)?없|100%\s*안전",
            # 의료법 제56조①·제27조③
            "의료광고·유인":r"(병원|의원|클리닉|한의원)\s*(예약|할인|링크|추천)|전후\s*사진|시술\s*후기",
            # 자본시장법·금소법
            "투자 권유":r"매수하세요|매도하세요|추천\s*종목|지금\s*사세요|목표가",
            "수익 보장":r"원금\s*보장|확정\s*수익|손실\s*없|수익률\s*보장"}
def esc(s): return H.escape(str(s))
def az(t,b,p,f): return max(f,int(b-len(t)*p))

def page(body_css, cls, inner, w, h):
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>{T}\n{body_css}'
            f'</style></head><body style="--cat:{cat_color(cls)}">{inner}</body></html>')

CARD_CSS = """.through{margin-left:auto;background:var(--ink);color:var(--paper);font-size:26px;font-weight:900;padding:10px 22px;border-radius:999px;white-space:nowrap}
.wrap{width:1080px;height:1350px;padding:90px 80px;display:flex;flex-direction:column}
.top{display:flex;align-items:center}.badge{border:2px solid var(--cat);color:var(--cat);background:transparent;font-size:26px;
font-weight:900;padding:10px 22px;border-radius:999px}.pg{margin-left:auto;font-size:26px;
font-weight:800;color:var(--ink-soft)}.dd{margin-left:14px;background:var(--ink);color:var(--paper);
font-size:22px;font-weight:900;padding:8px 16px;border-radius:10px}
.body{flex:1;display:flex;flex-direction:column;justify-content:center}
.kicker{font-size:34px;font-weight:800;color:var(--cat);margin-bottom:22px}
.head{font-weight:900;line-height:1.2;letter-spacing:-.035em}
.big{font-size:120px;font-weight:900;color:var(--cat);letter-spacing:-.05em;margin:24px 0}
.desc{margin-top:30px;font-size:34px;font-weight:500;line-height:1.55;color:var(--ink-soft)}
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
.tbl2 td:nth-child(2){text-align:right;color:var(--ink-soft);font-weight:800}
.tbl2 td:last-child{text-align:right;color:var(--cat);font-weight:900}"""

POST_CSS = """.wrap{width:1080px;height:1350px;padding:76px 72px 64px;display:flex;flex-direction:column}
.top{display:flex;align-items:center;gap:16px;margin-bottom:28px}
.badge{border:2px solid var(--cat);color:var(--cat);background:transparent;font-size:26px;font-weight:800;padding:9px 20px;border-radius:999px}
.through{margin-left:auto;background:var(--ink);color:var(--paper);font-size:26px;font-weight:900;padding:10px 22px;border-radius:999px;white-space:nowrap}
.dd{background:var(--ink);color:var(--paper);font-size:22px;font-weight:900;padding:8px 16px;border-radius:10px}
.brand{font-size:24px;font-weight:800;color:var(--ink-soft);margin:6px 0 2px}
h1{font-weight:900;line-height:1.18;letter-spacing:-.035em}
.sub{margin-top:18px;font-size:30px;color:var(--ink-soft);line-height:1.45}
.rule{height:6px;background:var(--cat);width:96px;border-radius:3px;margin:32px 0 30px}
.list{display:flex;flex-direction:column;flex:1}
.row{display:flex;align-items:center;gap:22px;background:var(--paper-2);border-radius:20px}
.n{flex:0 0 auto;border-radius:14px;background:var(--cat);color:#fff;font-weight:900;
display:flex;align-items:center;justify-content:center}
.lab{font-weight:800;letter-spacing:-.03em;line-height:1.2}
.val{margin-left:auto;font-weight:900;color:var(--cat);white-space:nowrap}
.foot{margin-top:26px;display:flex;align-items:flex-end;gap:20px}
.src{font-size:20px;color:var(--ink-soft);flex:1}
.cta{background:var(--ink);color:var(--paper);font-size:24px;font-weight:800;padding:16px 26px;border-radius:14px}"""

SCENE_CSS = """.wrap{width:1080px;height:1920px;padding:210px 190px 430px 100px;display:flex;flex-direction:column}
.top{display:flex;align-items:center;gap:16px;margin-bottom:50px}
.badge{border:3px solid var(--cat);color:var(--cat);background:transparent;font-size:32px;font-weight:800;padding:11px 26px;border-radius:999px}
.through{margin-left:auto;background:var(--ink);color:var(--paper);font-size:32px;font-weight:900;padding:13px 28px;border-radius:999px;white-space:nowrap}
.pg{margin-left:auto;font-size:34px;font-weight:800;color:var(--ink-soft)}
.body{flex:1;display:flex;flex-direction:column;justify-content:center}
.kicker{font-size:52px;font-weight:800;color:var(--cat);margin-bottom:30px}
.head{font-weight:900;line-height:1.18;letter-spacing:-.035em}
.big{font-size:150px;font-weight:900;color:var(--cat);letter-spacing:-.05em;margin:36px 0}
.tbl{width:100%;border-collapse:collapse;font-size:36px}
.tbl td{padding:16px 12px;border-bottom:2px solid var(--line);font-weight:700}
.tbl td:last-child{text-align:right;color:var(--cat);font-weight:900}
.dd{position:absolute;top:210px;right:100px;background:var(--ink);color:var(--paper);
font-size:30px;font-weight:900;padding:12px 22px;border-radius:12px}
.cap{position:absolute;left:100px;right:190px;bottom:460px;font-size:46px;font-weight:800;
line-height:1.35;border-left:8px solid var(--cat);padding-left:26px}
.brand{position:absolute;left:100px;bottom:625px;font-size:26px;font-weight:800;color:var(--ink-soft)}"""

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
    m, items = d["meta"], d["items"]; n = len(items); total = n+2
    dd = f'<div class="dd">{esc(m["dday"])}</div>' if m.get("dday") else ""
    gap,pad,nw,nf,lf,vf = (18,22,74,38,44,46) if n<=6 else (12,15,62,32,36,38)
    rows = "".join(f'<div class="row" style="padding:{pad}px 26px;margin-bottom:{gap}px">'
        f'<div class="n" style="width:{nw}px;height:{nw}px;font-size:{nf}px">{it.get("rank",i+1)}</div>'
        f'<div class="lab" style="font-size:{lf}px">{esc(it["label"])}</div>'
        f'<div class="val" style="font-size:{vf}px">{esc(it["value"])}</div></div>'
        for i,it in enumerate(items))
    src = " · ".join(dict.fromkeys(s["issuer"] for s in d["sources"]))
    poster = page(POST_CSS, m["category"], f'''<div class="wrap">
<div class="top"><div class="badge">{m["category"]}</div>{("<div class='through'>"+esc(m["throughline"])+"</div>") if m.get("throughline") else ""}{dd}</div>
<div class="brand">@machimaza</div>
<h1 style="font-size:{az(m["title"],76,0.9,52)}px">{esc(m["title"])}</h1>
<div class="sub">{esc(m.get("subtitle",d["summary"])[:70])}</div><div class="rule"></div>
<div class="list">{rows}</div><div class="foot"><div class="src">출처 · {esc(src)} ({m["publish_date"]} 기준)</div>
<div class="cta">{esc(d.get("cta","저장해두세요"))}</div></div></div>''', 1080, 1350)
    def card(pg_no, kicker, head, big, desc, foot, hf):
        return page(CARD_CSS, m["category"], f'''<div class="wrap">
<div class="top"><div class="badge">{m["category"]}</div>{("<div class='through'>"+esc(m["throughline"])+"</div>") if m.get("throughline") else ""}</div>
<div class="body">{kicker}<div class="head" style="font-size:{hf}px">{head}</div>{big}{desc}</div>
<div class="foot"><b>마치마자</b> · {foot}</div></div>''', 1080, 1350)
    # 카드는 영상과 같은 flow 를 그립니다.
    # 예전에는 items 를 그대로 카드로 찍어서, 카드 다섯 장이 전부 가격표였습니다.
    # 영상에서 고친 문제(자격·기한·신청 방법이 없음)가 카드에도 똑같이 있었습니다.
    def shell(body, foot):
        th = (f"<div class='through'>{esc(m['throughline'])}</div>"
              if m.get("throughline") else "")
        return page(CARD_CSS, m["category"], f'''<div class="wrap">
<div class="top"><div class="badge">{esc(m["category"])}</div>{th}</div>
<div class="body">{body}</div>
<div class="foot"><b>마치마자</b> · {foot}</div></div>''', 1080, 1350)

    def card_for(sc, idx, last):
        ty, foot = sc["type"], ("@machimaza" if last else "넘겨서 확인하세요 →")
        cap = f'<div class="desc">{esc(sc.get("screen",""))}</div>'
        if ty == "hook":
            return shell(f'<div class="head" style="font-size:{az(m["title"],92,1.1,58)}px">'
                         f'{esc(m["title"])}</div>{cap}', foot)
        if ty == "fact":
            sub = f'<div class="sub2">{esc(sc["sub"])}</div>' if sc.get("sub") else ""
            return shell(f'<div class="kicker">{esc(sc["label"])}</div>'
                         f'<div class="big" style="font-size:{max(72, 128 - len(sc["big"]) * 5)}px">'
                         f'{esc(sc["big"])}</div>{sub}{cap}', foot)
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
                f'<div class="bar"><i style="width:{r:.1f}%"></i></div></div></div>{cap}', foot)
        if ty == "list":
            lis = "".join(f'<div class="li"><b></b><span>{esc(x)}</span></div>' for x in sc["items"])
            note = f'<div class="note">{esc(sc["note"])}</div>' if sc.get("note") else ""
            return shell(f'<div class="head" style="font-size:56px">{esc(sc["label"])}</div>'
                         f'<div style="margin-top:34px">{lis}</div>{note}{cap}', foot)
        if ty == "table":
            cols = sc.get("columns") or ["구간", "금액"]
            head = "".join(f"<th>{esc(c)}</th>" for c in cols)
            body = "".join(
                f'<tr><td>{esc(i["label"].replace("월급 ", ""))}</td>'
                + (f'<td>{esc(i.get("employed", i["value"]))}</td>' if len(cols) > 2 else "")
                + f'<td>{esc(i["value"])}</td></tr>' for i in items)
            note = f'<div class="note">{esc(sc["note"])}</div>' if sc.get("note") else ""
            return shell(f'<table class="tbl2"><tr>{head}</tr>{body}</table>{note}{cap}', foot)
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


def verify(d, base):
    E, W = [], []
    today = dt.date.today()
    sids = {s["id"] for s in d["sources"]}
    for it in d["items"]:
        if it["source_id"] not in sids: E.append(f"'{it['label']}' 출처 미연결")
    ax = d["meta"].get("axis")
    if not ax: W.append("axis 없음")
    elif ax.get("type") in BANNED: E.append(f"금지 축 '{ax['type']}'")
    elif ax.get("type") not in AXES: E.append(f"허용 안 된 축 '{ax.get('type')}'")
    for s in d["sources"]:
        if s.get("tier",4) >= 4: E.append(f"{s['id']} tier 4 (사용 불가)")
        u = s.get("url","")
        if not re.match(r"^https?://", u): E.append(f"{s['id']} 링크 없음")
        elif s.get("tier",4) <= 2 and not re.search(r"\.(go|or|re)\.kr", u):
            E.append(f"{s['id']} tier{s['tier']} 인데 공공 도메인 아님: {u}")
        try:
            if (today - dt.date.fromisoformat(s["effective_date"])).days > 730:
                W.append(f"{s['id']} 시행일 2년 초과")
        except Exception: W.append(f"{s['id']} 시행일 형식 오류")
    key = CAT2KEY[d["meta"]["category"]]
    b = base/"blog.md"
    if not b.exists(): E.append("blog.md 없음")
    else:
        t = b.read_text(encoding="utf-8")
        if key != "none" and DISC[key] not in t: E.append("고지 문구 누락")
        if not re.search(r"^\|.+\|\s*$", t, re.M): E.append("텍스트 표 없음")
        n_img = len(re.findall(r"!\[[^\]]*\]\([^)]+\)", t))
        if n_img < 5: E.append(f"블로그 본문 이미지 {n_img}장 (5장 이상 필요)")
        if "마치마자 ·" not in t: W.append("저자 서명 없음 (E-E-A-T 신호)")
        if len(t) < 4000: W.append(f"본문 {len(t)}자 — 목표 8,000자 미달")
        if t.count("\n## ") < 5: W.append(f"H2 {t.count(chr(10)+'## ')}개 — 목표 7~9개")
        for nm,p in FAIL_PAT.items():
            if re.search(p,t): E.append(f"톤 위반({nm})")
    v = base/"video.mp4"
    if v.exists():
        a = subprocess.run(["ffprobe","-v","error","-select_streams","a","-show_entries",
            "stream=codec_name","-of","csv=p=0",str(v)],capture_output=True,text=True).stdout.strip()
        if not a: E.append("오디오 스트림 없음")
        dur = float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
            "-of","default=nw=1:nk=1",str(v)],capture_output=True,text=True).stdout.strip())
        if not 60 <= dur <= 90: E.append(f"영상 {dur:.1f}초 (60~90 아님)")
    else: E.append("video.mp4 없음")
    if not d["meta"].get("dday"): W.append("dday 없음")
    for x in W: print("  ⚠", x)
    for x in E: print("  ✗", x)
    print(("🟢 게이트 통과 — 발행 가능" if not E else "🔴 발행 불가"))
    return 1 if E else 0

if __name__ == "__main__":
    base = pathlib.Path(sys.argv[1])
    d = json.loads((base/"data.json").read_text(encoding="utf-8"))
    build_images(d, base); build_video(d, base)
    sys.exit(verify(d, base))
