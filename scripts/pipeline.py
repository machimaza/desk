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
.cat-건강보험료{--cat:var(--cat-health)}.cat-재테크{--cat:var(--cat-money)}.cat-생활꿀팁{--cat:var(--cat-life)}"""

AXES = {"소득구간","연령대","가구형태","지역","직업형태","생활패턴"}
BANNED = {"자산순위","자산 순위","질병위험도","질병 위험도","외모","체형"}
DISC = {"health":"증상이 지속되거나 우려된다면 의료진과 상담","money":"투자 권유가 아닙니다"}
CAT2KEY = {"건강보험료":"health","재테크":"money","생활꿀팁":"none"}
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
            f'</style></head><body class="cat-{cls}">{inner}</body></html>')

CARD_CSS = """.wrap{width:1080px;height:1350px;padding:90px 80px;display:flex;flex-direction:column}
.top{display:flex;align-items:center}.badge{background:var(--cat);color:#fff;font-size:26px;
font-weight:900;padding:10px 22px;border-radius:999px}.pg{margin-left:auto;font-size:26px;
font-weight:800;color:var(--ink-soft)}.dd{margin-left:14px;background:var(--ink);color:var(--paper);
font-size:22px;font-weight:900;padding:8px 16px;border-radius:10px}
.body{flex:1;display:flex;flex-direction:column;justify-content:center}
.kicker{font-size:34px;font-weight:800;color:var(--cat);margin-bottom:22px}
.head{font-weight:900;line-height:1.2;letter-spacing:-.035em}
.big{font-size:120px;font-weight:900;color:var(--cat);letter-spacing:-.05em;margin:24px 0}
.desc{margin-top:30px;font-size:34px;font-weight:500;line-height:1.55;color:var(--ink-soft)}
.foot{font-size:22px;color:var(--ink-soft);border-top:2px solid var(--line);padding-top:22px}"""

POST_CSS = """.wrap{width:1080px;height:1350px;padding:76px 72px 64px;display:flex;flex-direction:column}
.top{display:flex;align-items:center;gap:16px;margin-bottom:28px}
.badge{background:var(--cat);color:#fff;font-size:26px;font-weight:900;padding:10px 22px;border-radius:999px}
.dd{background:var(--ink);color:var(--paper);font-size:22px;font-weight:900;padding:8px 16px;border-radius:10px}
.brand{margin-left:auto;font-size:24px;font-weight:800;color:var(--ink-soft)}
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
.badge{background:var(--cat);color:#fff;font-size:34px;font-weight:900;padding:14px 30px;border-radius:999px}
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
<div class="top"><div class="badge">{m["category"]}</div>{dd}<div class="brand">@machimaza</div></div>
<h1 style="font-size:{az(m["title"],76,0.9,52)}px">{esc(m["title"])}</h1>
<div class="sub">{esc(m.get("subtitle",d["summary"])[:70])}</div><div class="rule"></div>
<div class="list">{rows}</div><div class="foot"><div class="src">출처 · {esc(src)} ({m["publish_date"]} 기준)</div>
<div class="cta">{esc(d.get("cta","저장해두세요"))}</div></div></div>''', 1080, 1350)
    def card(pg_no, kicker, head, big, desc, foot, hf):
        return page(CARD_CSS, m["category"], f'''<div class="wrap">
<div class="top"><div class="badge">{m["category"]}</div><div class="pg">{pg_no}/{total}</div>{dd}</div>
<div class="body">{kicker}<div class="head" style="font-size:{hf}px">{head}</div>{big}{desc}</div>
<div class="foot"><b>마치마자</b> · {foot}</div></div>''', 1080, 1350)
    pages = [("poster.png", poster)]
    pages.append(("card_01.png", card(1, f'<div class="kicker">{esc(d["hook"])}</div>',
        esc(m["title"]), "", f'<div class="desc">{esc(d["summary"])}</div>',
        "넘겨서 확인하세요 →", az(m["title"],92,1.1,60))))
    for i,it in enumerate(items):
        iss = next(s["issuer"] for s in d["sources"] if s["id"]==it["source_id"])
        pages.append((f"card_{i+2:02d}.png", card(i+2, f'<div class="kicker">{it.get("rank",i+1)}</div>',
            esc(it["label"]), f'<div class="big">{esc(it["value"])}</div>',
            f'<div class="desc">{esc(it["detail"])}</div>', esc(iss), az(it["label"],78,1.4,52))))
    pages.append((f"card_{total:02d}.png", card(total, '<div class="kicker">정리하면</div>',
        esc(d["summary"]), "", f'<div class="desc">{esc(d.get("cta",""))}<br>전문은 프로필 링크에서.</div>',
        "@machimaza", az(d["summary"],74,0.85,46))))
    w = shoot(pages, base/"images", 1080, 1350)
    alt = []
    for f in w:
        if f.name=="poster.png": alt.append(f'{f.name}\t{m["category"]} 정보 카드. {m["title"]}.')
        elif f.name=="card_01.png": alt.append(f'{f.name}\t{m["title"]} 표지. {d["hook"]}')
        else:
            try:
                it = items[int(f.name.split("_")[1].split(".")[0])-2]
                alt.append(f'{f.name}\t{it["label"]} {it["value"]}. {it["detail"][:60]}')
            except Exception: alt.append(f'{f.name}\t{m["title"]} 요약. {d["summary"][:60]}')
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
