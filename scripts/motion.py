#!/usr/bin/env python3
"""9:16 영상 렌더러 — 실제 모션.

왜 이렇게 만들었나
  정지 이미지에 느린 확대(zoompan)를 걸고 TTS를 얹는 것은
  AI 양산 콘텐츠의 대표 서명입니다. 그게 정확히 플랫폼이 잡아내는 신호라
  CLAUDE.md 9장은 "실제 모션 구현 전에는 영상 트랙 시작 안 함"으로 막아뒀습니다.

방식
  CSS 애니메이션을 '재생'하지 않습니다. 프레임마다 window.draw(t) 로
  그 시점의 상태를 직접 그린 뒤 스크린샷합니다. t 를 넣으면 화면이 나오는
  순수 함수이므로 타이밍이 결정적이고, CI에서도 같은 결과가 나옵니다.

  움직이는 구간만 프레임을 찍고, 멈춰 있는 구간은 마지막 프레임을 늘립니다.
  (전 구간을 찍으면 45초에 1350장 — 낭비입니다.)

구조 3종 (data.json meta.video_structure)
  countdown  구간을 역순으로 하나씩 — 숫자 카운트업 + 막대 성장
  compare    같은 항목의 두 값을 나란히 — 양쪽 막대가 동시에 자람
  step       순서가 있는 절차 — 단계 번호와 문장이 차례로 등장

음성
  콘텐츠 폴더에 narration.mp3(.m4a/.wav) 가 있으면 합성합니다.
  없으면 무음 트랙으로 진행합니다 (게이트가 오디오 스트림 존재를 요구하므로).
"""
import json, re, sys, math, pathlib, subprocess, tempfile, html as H

FPS = 30
W, HGT = 1080, 1920
# 플랫폼 UI 가림 영역 — CLAUDE.md 7장 실측값
SAFE_TOP, SAFE_BOTTOM, SAFE_RIGHT, PAD_LEFT = 210, 430, 190, 100

CSS = """
:root{
  --ink:#16202E; --ink-soft:#4A5666; --paper:#FBF8F3; --line:#DED5C6;
  --cat-health:#2E6B5E; --cat-money:#1F5C8B; --cat-life:#C2703D;
  --font:"Noto Sans CJK KR","Noto Sans KR",sans-serif;
}
*{margin:0;padding:0;box-sizing:border-box;-webkit-font-smoothing:antialiased}
body{font-family:var(--font);background:var(--paper);color:var(--ink);
  width:1080px;height:1920px;overflow:hidden}
/* 좌우 여백은 같아야 합니다. 예전에 왼쪽 100 / 오른쪽 190 이라
   글이 왼쪽으로 밀려 보였습니다. 오른쪽을 넓게 뒀던 건 쇼츠의
   좋아요·공유 버튼을 피하려던 것인데, 150 이면 충분히 비켜갑니다.
   아래 720 은 제목·설명이 덮는 자리라 그대로 둡니다. */
.wrap{width:1080px;height:1920px;padding:210px 150px 720px 150px;
  display:flex;flex-direction:column}
.top{display:flex;align-items:center;gap:16px;margin-bottom:50px}
/* 좌: 분야 — 조용한 테두리. 우: 관통 단어 — 진한 배경. 오른쪽이 더 중요합니다. */
.badge{border:3px solid var(--cat);color:var(--cat);background:transparent;
  font-size:32px;font-weight:800;padding:11px 26px;border-radius:999px}
.through{margin-left:auto;background:var(--ink);color:var(--paper);
  font-size:32px;font-weight:900;padding:13px 28px;border-radius:999px;
  white-space:nowrap}
.pg{margin-left:auto;font-size:34px;font-weight:800;color:var(--ink-soft)}
.body{flex:1;display:flex;flex-direction:column;justify-content:center}
.kicker{font-size:52px;font-weight:800;color:var(--cat);margin-bottom:30px}
.head{font-weight:900;line-height:1.18;letter-spacing:-.035em;
  word-break:keep-all;text-align:center}
/* 자릿수가 길어져도 단위가 줄바꿈되지 않도록 — 프로토타입에서 발견한 버그 */
.big{font-size:132px;font-weight:900;color:var(--cat);letter-spacing:-.05em;
  margin:30px 0 18px;white-space:nowrap;font-variant-numeric:tabular-nums;
  text-align:center}
.unit{font-size:64px;font-weight:800;margin-left:6px}
.bar{height:26px;background:var(--line);overflow:hidden;border-radius:999px}
.fill{height:100%;background:var(--cat);border-radius:999px}
.cmp{display:flex;flex-direction:column;gap:44px;margin-top:20px}
.cmp .lab2{font-size:40px;font-weight:800;color:var(--ink-soft);margin-bottom:14px}
.cmp .v2{font-size:84px;font-weight:900;letter-spacing:-.04em;white-space:nowrap;
  font-variant-numeric:tabular-nums;margin-bottom:16px}
.pts{margin-top:30px;border-top:2px solid var(--line)}
.pt{display:flex;align-items:baseline;gap:22px;padding:16px 2px;
  border-bottom:1px solid var(--line);font-size:38px;word-break:keep-all}
.pt span{color:var(--ink-soft);font-weight:700;flex:none;min-width:250px}
.pt b{font-weight:800}
.sub{font-size:44px;font-weight:700;color:var(--ink-soft);
  margin-top:10px;word-break:keep-all;line-height:1.4;text-align:center}
.cmp .lab2{font-size:38px;font-weight:800;color:var(--ink-soft);margin-bottom:12px;
  word-break:keep-all}
/* 항목 글자는 왼쪽 정렬을 지킵니다. 여러 줄을 가운데로 맞추면
   줄마다 시작점이 달라져 눈이 매번 새로 찾아야 합니다.
   대신 묶음 전체를 가운데에 놓습니다. */
.li{display:flex;align-items:center;gap:24px;font-size:56px;font-weight:800;
  margin-bottom:26px;word-break:keep-all;justify-content:flex-start}
.li .dot{width:18px;height:18px;border-radius:999px;background:var(--cat);flex:none}
/* 메모는 세로선을 떼고 가운데로. 선이 있으면 가운데 정렬이 어색합니다. */
.note{margin-top:28px;font-size:40px;font-weight:800;color:var(--ink-soft);
  padding:14px 20px 0;word-break:keep-all;text-align:center;
  border-top:2px solid var(--line)}
.note.warn{color:#A03A28;border-top-color:#A03A28}
.stepno{width:104px;height:104px;border-radius:999px;background:var(--cat);color:#fff;
  font-size:56px;font-weight:900;display:flex;align-items:center;justify-content:center;
  margin-bottom:34px}
.steptx{font-size:62px;font-weight:800;line-height:1.35;letter-spacing:-.03em;word-break:keep-all}
.tbl{width:100%;border-collapse:collapse;font-size:36px}
.tbl td{padding:16px 12px;border-bottom:2px solid var(--line);font-weight:700}
.tbl td.c1{text-align:right;color:var(--ink-soft);font-weight:800}
.tbl td.c2{text-align:right;color:var(--cat);font-weight:900}
.tbl th{padding:12px;border-bottom:3px solid var(--ink);font-size:30px;
  font-weight:800;color:var(--ink-soft);text-align:right}
.tbl th:first-child{text-align:left}
.tbl td.same{text-align:right;color:var(--ink-soft);font-weight:800}
.tbl{font-variant-numeric:tabular-nums}
.dd{position:absolute;top:210px;right:150px;background:var(--ink);color:var(--paper);
  font-size:30px;font-weight:900;padding:12px 22px;border-radius:12px}
/* 자막·출처·진행바도 좌우를 같게 둡니다. 본문만 가운데로 맞추고
   이것들을 왼쪽에 두면 화면이 다시 기울어 보입니다. */
.cap{position:absolute;left:150px;right:150px;bottom:460px;font-size:46px;font-weight:800;
  line-height:1.35;word-break:keep-all;text-align:center}
.brand{position:absolute;left:150px;right:150px;bottom:625px;font-size:26px;
  font-weight:800;color:var(--ink-soft);text-align:center}
.basis{position:absolute;left:150px;right:150px;bottom:672px;font-size:28px;
  font-weight:700;color:var(--ink-soft);letter-spacing:-.01em;text-align:center}
.prog{position:absolute;left:150px;right:150px;top:322px;height:6px;
  background:var(--line);border-radius:999px;overflow:hidden}
.prog>i{display:block;height:100%;background:var(--cat);border-radius:999px}
"""

JS = """
// 모든 움직임은 t 의 함수입니다. 재생되는 것은 없습니다.
function clamp(x){return x<0?0:(x>1?1:x)}
function easeOut(x){return 1-Math.pow(1-x,3)}          // 빠르게 시작해 부드럽게 멈춤
function easeOutBack(x){const c=1.7;return 1+ (c+1)*Math.pow(x-1,3)+c*Math.pow(x-1,2)}
function seg(t,start,dur){return clamp((t-start)/dur)}  // 구간별 진행도

// 요소 등장: 아래에서 올라오며 나타남
function enter(el,p){
  if(!el) return;
  el.style.opacity = p;
  el.style.transform = 'translateY(' + ((1-p)*38).toFixed(2) + 'px)';
}
function setNum(el,target,p,unit,step){
  if(!el) return;
  const s = step || 1;
  const v = Math.floor(target*easeOut(p)/s)*s;
  el.innerHTML = v.toLocaleString('ko-KR') + (unit ? '<span class="unit">'+unit+'</span>' : '');
}
function setBar(el,ratio,p){
  if(!el) return;
  el.style.width = (ratio*easeOut(p)*100).toFixed(2) + '%';
}
"""


CATS = json.loads((pathlib.Path(__file__).resolve().parent.parent /
                   "categories.json").read_text(encoding="utf-8"))["카테고리"]


def cat_color(name):
    return (CATS.get(name) or {}).get("색", "#2E6B5E")


def bottom_bar(m, d=None):
    """바닥에 근거를 답니다 — 무슨 해 기준이고 어디서 왔는지.

    안전영역(890×1280) 안에서 본문이 가운데 정렬돼 있어 위아래가 비었습니다.
    빈 곳을 장식으로 채우지 않고, 영상에 없던 신뢰 정보를 넣습니다.
    """
    basis = m.get("basis") or f'{m["publish_date"][:4]}년 기준'
    src = ""
    if d and d.get("sources"):
        src = " · " + esc(d["sources"][0]["issuer"].split()[0])
    return f'<div class="basis">{esc(basis)}{src}</div>'


def prog_bar(i, n):
    return (f'<div class="prog"><i style="width:{(i+1)/n*100:.1f}%"></i></div>'
            if n > 1 else "")


def top_bar(m):
    """좌측 = 분야, 우측 = 관통 단어.

    관통 단어는 '공단에 전화해서 말해야 하는 단어' 입니다.
    분야만 있으면 무슨 얘긴지 모르고, 관통 단어만 있으면 어느 제도인지 모릅니다.
    """
    cat = esc(m["category"])
    th = m.get("throughline")
    return (f'<div class="top"><div class="badge">{cat}</div>'
            + (f'<div class="through">{esc(th)}</div>' if th else "")
            + '</div>')


def esc(s):
    return H.escape(str(s))


def parse_amount(v):
    """'89,870원' → (89870, '원'). 숫자를 못 찾으면 (None, 원문)."""
    m = re.search(r"([\d,]+)", str(v))
    if not m:
        return None, str(v)
    num = int(m.group(1).replace(",", ""))
    unit = str(v)[m.end():].strip()
    return num, unit


def page(cat, inner, script):
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8">'
            f'<style>{CSS}</style></head><body style="--cat:{cat_color(cat)}">{inner}'
            f'<script>{JS}\n{script}</script></body></html>')


# ── 장면 정의 ──────────────────────────────────────────────────────────
# 각 장면은 (html, 움직이는 시간, 멈춰 있는 시간, 자막) 입니다.

def scene_title(m, hook, dd):
    inner = f'''<div class="wrap">
{top_bar(m)}<!--PRG-->
<div class="body">
  <div class="head" id="h" style="font-size:{max(52, 108 - len(m["title"]))}px">{esc(m["title"])}</div>
</div></div>{dd}<div class="cap" id="c">{esc(hook)}</div>
<div class="brand">@machimaza</div><!--BOT-->'''
    js = '''window.draw=(t)=>{
  enter(document.getElementById('h'), easeOut(seg(t,0.05,0.7)));
  enter(document.getElementById('c'), easeOut(seg(t,0.8,0.6)));
};'''
    return page(m["category"], inner, js), 1.6, 3.0


def scene_value(m, it, pg, ratio, dd):
    num, unit = parse_amount(it["value"])
    inner = f'''<div class="wrap">
{top_bar(m)}<!--PRG-->
<div class="body">
  <div class="head" id="l" style="font-size:{max(58, 100 - len(it["label"]) * 2)}px">{esc(it["label"])}</div>
  <div class="big" id="n">0</div>
  <div class="bar"><div class="fill" id="b" style="width:0%"></div></div>
</div></div>{dd}<div class="cap" id="c">{esc(it.get("caption") or it["detail"])[:60]}</div>
<div class="brand">@machimaza</div><!--BOT-->'''
    js = f'''window.draw=(t)=>{{
  enter(document.getElementById('l'), easeOut(seg(t,0.0,0.45)));
  const p = seg(t,0.3,1.5);
  setNum(document.getElementById('n'), {num if num is not None else 0}, p, {json.dumps(unit)}, 10);
  setBar(document.getElementById('b'), {ratio:.4f}, p);
  enter(document.getElementById('c'), easeOut(seg(t,1.1,0.5)));
}};'''
    return page(m["category"], inner, js), 2.0, 3.9


def scene_compare(m, it, pg, base_num, dd):
    """같은 항목의 두 값을 나란히 — 깎이기 전과 깎인 뒤."""
    num, unit = parse_amount(it["value"])
    gross = base_num if base_num else (num * 2 if num else 0)
    inner = f'''<div class="wrap">
{top_bar(m)}<!--PRG-->
<div class="body">
  <div class="head" id="l" style="font-size:{max(56, 96 - len(it["label"]) * 2)}px">{esc(it["label"])}</div>
  <div class="cmp">
    <div>
      <div class="lab2">깎기 전</div>
      <div class="v2" id="n1" style="color:var(--ink-soft)">0</div>
      <div class="bar"><div class="fill" id="b1" style="width:0%;background:var(--line)"></div></div>
    </div>
    <div>
      <div class="lab2">실제 내는 금액</div>
      <div class="v2" id="n2" style="color:var(--cat)">0</div>
      <div class="bar"><div class="fill" id="b2" style="width:0%"></div></div>
    </div>
  </div>
</div></div>{dd}<div class="cap" id="c">{esc(it.get("caption") or it["detail"])[:60]}</div>
<div class="brand">@machimaza</div><!--BOT-->'''
    ratio2 = (num / gross) if gross else 1.0
    js = f'''window.draw=(t)=>{{
  enter(document.getElementById('l'), easeOut(seg(t,0.0,0.45)));
  const p1 = seg(t,0.3,1.1), p2 = seg(t,0.9,1.3);
  setNum(document.getElementById('n1'), {gross}, p1, {json.dumps(unit)}, 10);
  setBar(document.getElementById('b1'), 1.0, p1);
  setNum(document.getElementById('n2'), {num if num is not None else 0}, p2, {json.dumps(unit)}, 10);
  setBar(document.getElementById('b2'), {ratio2:.4f}, p2);
  enter(document.getElementById('c'), easeOut(seg(t,1.6,0.5)));
}};'''
    return page(m["category"], inner, js), 2.4, 3.6


def scene_step(m, it, pg, no, dd):
    tx = (it.get("caption") or it["detail"])[:70]
    inner = f'''<div class="wrap">
{top_bar(m)}<!--PRG-->
<div class="body">
  <div class="stepno" id="s">{no}</div>
  <div class="steptx" id="l">{esc(it["label"])}</div>
  <div class="big" id="n" style="font-size:96px">0</div>
</div></div>{dd}<div class="cap" id="c">{esc(tx)}</div>
<div class="brand">@machimaza</div><!--BOT-->'''
    num, unit = parse_amount(it["value"])
    js = f'''window.draw=(t)=>{{
  const sp = seg(t,0.0,0.45);
  const s = document.getElementById('s');
  s.style.opacity = sp; s.style.transform = 'scale('+(0.6+0.4*easeOutBack(sp)).toFixed(3)+')';
  enter(document.getElementById('l'), easeOut(seg(t,0.3,0.5)));
  setNum(document.getElementById('n'), {num if num is not None else 0}, seg(t,0.7,1.2), {json.dumps(unit)}, 10);
  enter(document.getElementById('c'), easeOut(seg(t,1.2,0.5)));
}};'''
    return page(m["category"], inner, js), 2.0, 3.9


def points_block(sc):
    """장면의 요점 — 카드와 영상이 함께 씁니다.

    영상에서 fact 장면은 라벨·숫자·한 줄뿐이라 안전영역의 대부분이 비었습니다
    (잉크 3.6% 프레임까지 나왔습니다). 정지 구간이 3~4초이므로
    짧은 세 줄은 충분히 읽힙니다. 빈 곳을 정보로 채웁니다.
    """
    ps = sc.get("points")
    if not ps:
        return ""
    return ('<div class="pts" id="pts">' + "".join(
        f'<div class="pt" style="opacity:0"><span>{esc(k)}</span><b>{esc(v)}</b></div>'
        for k, v in ps) + '</div>')


def scene_fact(m, sc, dd):
    """하나의 사실만 크게 — 자격·기한처럼 숫자가 아닌 핵심."""
    pts = points_block(sc)
    inner = f'''<div class="wrap">
{top_bar(m)}<!--PRG-->
<div class="body">
  <div class="head" id="l" style="font-size:56px;color:var(--ink-soft)">{esc(sc["label"])}</div>
  <div class="big" id="b" style="font-size:{max(84, 150 - len(sc["big"]) * 6)}px">{esc(sc["big"])}</div>
  <div class="sub" id="s">{esc(sc.get("sub",""))}</div>
  {pts}
</div></div>{dd}<div class="cap" id="c">{esc(sc["screen"])}</div>
<div class="brand">@machimaza</div><!--BOT-->'''
    js = '''window.draw=(t)=>{
  enter(document.getElementById('l'), easeOut(seg(t,0.0,0.45)));
  const p = easeOut(seg(t,0.35,0.6));
  const b = document.getElementById('b');
  b.style.opacity = p; b.style.transform = 'scale('+(0.86+0.14*p).toFixed(3)+')';
  enter(document.getElementById('s'), easeOut(seg(t,0.8,0.5)));
  document.querySelectorAll('.pt').forEach((e,i)=>{
    enter(e, easeOut(seg(t, 1.05+0.18*i, 0.45)));
  });
  enter(document.getElementById('c'), easeOut(seg(t,1.3,0.5)));
};'''
    return page(m["category"], inner, js), 2.2, 3.9


def scene_list(m, sc, dd):
    """항목이 하나씩 등장 — 신청 방법처럼 '그래서 뭘 하나'에 답하는 장면."""
    lis = "".join(f'<div class="li" style="opacity:0"><span class="dot"></span>'
                  f'<span>{esc(x)}</span></div>' for x in sc["items"])
    nk = " warn" if sc.get("note_kind") == "warn" else ""
    note = f'<div class="note{nk}" id="n">{esc(sc["note"])}</div>' if sc.get("note") else ""
    inner = f'''<div class="wrap">
{top_bar(m)}<!--PRG-->
<div class="body">
  <div class="head" id="l" style="font-size:62px">{esc(sc["label"])}</div>
  <div style="margin-top:44px">{lis}</div>{note}
</div></div>{dd}<div class="cap" id="c">{esc(sc["screen"])}</div>
<div class="brand">@machimaza</div><!--BOT-->'''
    js = '''window.draw=(t)=>{
  enter(document.getElementById('l'), easeOut(seg(t,0.0,0.45)));
  const ls = document.querySelectorAll('.li');
  ls.forEach((e,i)=>{ enter(e, easeOut(seg(t, 0.35+0.22*i, 0.45))); });
  const n = document.getElementById('n');
  if(n) enter(n, easeOut(seg(t, 0.35+0.22*ls.length, 0.5)));
  enter(document.getElementById('c'), easeOut(seg(t, 0.5+0.22*ls.length, 0.5)));
};'''
    return page(m["category"], inner, js), 0.55 * len(sc["items"]) + 1.5, 3.0


def scene_compare2(m, sc, dd):
    """두 값을 나란히. 라벨을 데이터에서 그대로 받습니다.

    이전 버전은 '깎기 전 / 실제 내는 금액' 이라고만 썼는데,
    무엇을 깎기 전인지 화면 어디에도 없었습니다. 산식이 라벨에 보여야 합니다.
    """
    b, a = sc["before"], sc["after"]
    nb, ub = parse_amount(b["value"])
    na, ua = parse_amount(a["value"])
    inner = f'''<div class="wrap">
{top_bar(m)}<!--PRG-->
<div class="body">
  <div class="head" id="l" style="font-size:62px">{esc(sc["label"])}</div>
  <div class="cmp">
    <div>
      <div class="lab2">{esc(b["label"])}</div>
      <div class="v2" id="n1" style="color:var(--ink-soft)">0</div>
      <div class="bar"><div class="fill" id="b1" style="width:0%;background:var(--line)"></div></div>
    </div>
    <div>
      <div class="lab2">{esc(a["label"])}</div>
      <div class="v2" id="n2" style="color:var(--cat)">0</div>
      <div class="bar"><div class="fill" id="b2" style="width:0%"></div></div>
    </div>
  </div>
</div></div>{dd}<div class="cap" id="c">{esc(sc["screen"])}</div>
<div class="brand">@machimaza</div><!--BOT-->'''
    ratio = (na / nb) if nb else 1.0
    js = f'''window.draw=(t)=>{{
  enter(document.getElementById('l'), easeOut(seg(t,0.0,0.45)));
  const p1 = seg(t,0.3,1.1), p2 = seg(t,0.95,1.3);
  setNum(document.getElementById('n1'), {nb or 0}, p1, {json.dumps(ub)}, 10);
  setBar(document.getElementById('b1'), 1.0, p1);
  setNum(document.getElementById('n2'), {na or 0}, p2, {json.dumps(ua)}, 10);
  setBar(document.getElementById('b2'), {ratio:.4f}, p2);
  enter(document.getElementById('c'), easeOut(seg(t,1.7,0.5)));
}};'''
    return page(m["category"], inner, js), 2.5, 3.4


def scene_table(m, items, dd, cap="지금 캡처해두세요. 신청할 때 다시 필요합니다.", sc=None):
    cols = (sc or {}).get("columns")
    if sc and sc.get("rows"):
        # 명시된 행을 그대로 그립니다 (열 추측 금지)
        head = "".join(f'<th>{esc(c)}</th>' for c in (cols or []))
        ac = sc.get("accent_col", len(cols or []) - 1)
        rows = (f'<tr class="r" style="opacity:0">{head}</tr>' if head else "") + "".join(
            '<tr class="r" style="opacity:0">' + "".join(
                f'<td class="{"c2" if k == ac else ("c1" if k else "")}">{esc(c)}</td>'
                for k, c in enumerate(r)) + '</tr>'
            for r in sc["rows"])
    elif cols:
        head = "".join(f'<th>{esc(c)}</th>' for c in cols)
        rows = f'<tr class="r" style="opacity:0">{head}</tr>' + "".join(
            f'<tr class="r" style="opacity:0"><td>{esc(i["label"].replace("월급 ",""))}</td>'
            f'<td class="same">{esc(i.get("employed", i["value"]))}</td>'
            f'<td>{esc(i["value"])}</td></tr>' for i in items)
    else:
        rows = "".join(
            f'<tr class="r" style="opacity:0"><td>{esc(i["label"])}</td>'
            f'<td>{esc(i["value"])}</td></tr>' for i in items)
    note = (f'<div class="note" id="tn">{esc(sc["note"])}</div>'
            if sc and sc.get("note") else "")
    inner = f'''<div class="wrap">
{top_bar(m)}<!--PRG-->
<div class="body"><table class="tbl">{rows}</table>{note}</div>
</div>{dd}<div class="cap" id="c">{esc(cap)}</div>
<div class="brand">@machimaza</div><!--BOT-->'''
    js = '''window.draw=(t)=>{
  const rs = document.querySelectorAll('.r');
  rs.forEach((r,i)=>{ enter(r, easeOut(seg(t, 0.12*i, 0.45))); });
  enter(document.getElementById('c'), easeOut(seg(t, 0.12*rs.length+0.2, 0.5)));
};'''
    return page(m["category"], inner, js), 1.8, 4.4


# 도입부 — 벨이 울리고 "집중시키는 말"이 나갈 자리입니다.
# 첫 장면(제목 카드)을 이만큼 더 붙잡아 둡니다.
# 이걸 안 두면 벨과 첫 대사가 겹쳐서 둘 다 안 들립니다.
LEAD_IN = 4.2


# ── 렌더 ───────────────────────────────────────────────────────────────

def build_scenes(d):
    m, items = d["meta"], d["items"]
    def dday_for(sc=None):
        """기한 배지는 장면이 dday:true 로 요청할 때만 뜹니다.
        모든 장면에 띄우면 세 번째 장면부터는 아무도 읽지 않습니다."""
        txt = m.get("dday")
        return f'<div class="dd">{esc(txt)}</div>' if (txt and sc and sc.get("dday")) else ""
    dd = ""
    struct = m.get("video_structure", "countdown")

    # flow — 영상을 items 에서 파생시키지 않고 data.json 의 video.scenes 대로 그립니다.
    # 블로그는 '전부'를 담고 영상은 '판단 순서'를 담습니다. 하는 일이 다릅니다.
    if struct == "flow":
        S = []
        for sc in d["flow"]["scenes"]:
            ty = sc["type"]
            if ty == "hook":
                page, anim, hold = scene_title(m, sc["screen"], dday_for(sc))
                if d["flow"].get("opener"):
                    hold += LEAD_IN     # 도입부 대사가 나갈 동안 제목을 붙잡습니다
                S.append((page, anim, hold))
            elif ty == "fact":
                S.append(scene_fact(m, sc, dday_for(sc)))
            elif ty == "compare":
                S.append(scene_compare2(m, sc, dday_for(sc)))
            elif ty == "list":
                S.append(scene_list(m, sc, dday_for(sc)))
            elif ty == "table":
                S.append(scene_table(m, items, dday_for(sc), sc["screen"], sc))
            else:
                raise ValueError(f"모르는 장면 유형: {ty}")
        return S
    nums = [parse_amount(i["value"])[0] or 0 for i in items]
    mx = max(nums) or 1
    S = [scene_title(m, d["hook"], dd)]
    seq = list(reversed(items)) if struct == "countdown" else items
    for idx, it in enumerate(seq):
        n = parse_amount(it["value"])[0] or 0
        if struct == "compare":
            # detail 안의 "A × B% = C" 에서 깎기 전 금액을 읽습니다.
            mm = re.search(r"=\s*([\d,]+)", it.get("detail", ""))
            gross = int(mm.group(1).replace(",", "")) if mm else n * 2
            S.append(scene_compare(m, it, it.get("rank", idx + 1), gross, dd))
        elif struct == "step":
            S.append(scene_step(m, it, it.get("rank", idx + 1), idx + 1, dd))
        else:
            S.append(scene_value(m, it, it.get("rank", idx + 1), n / mx, dd))
    S.append(scene_table(m, items, dd))
    return S


def render(d, base, keep_frames=False):
    base = pathlib.Path(base)
    scenes = build_scenes(d)
    BOT = bottom_bar(d["meta"], d)
    tmp = pathlib.Path(tempfile.mkdtemp())
    clips, srt_rows, t_abs = [], [], 0.0

    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch(args=["--force-device-scale-factor=1"])
        pg = b.new_page(viewport={"width": W, "height": HGT})
        for si, (html, anim, hold) in enumerate(scenes):
            html = (html.replace("<!--BOT-->", BOT)
                        .replace("<!--PRG-->", prog_bar(si, len(scenes))))
            pg.set_content(html, wait_until="load")
            pg.wait_for_timeout(80)
            fdir = tmp / f"s{si:02d}"
            fdir.mkdir()
            n = max(1, int(round(anim * FPS)))
            for i in range(n):
                pg.evaluate("t=>window.draw(t)", i / FPS)
                pg.screenshot(path=str(fdir / f"f{i:04d}.png"))
            # 움직이는 구간
            ca = tmp / f"a{si:02d}.mp4"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                            "-i", str(fdir / "f%04d.png"), "-c:v", "libx264",
                            "-pix_fmt", "yuv420p", "-crf", "20", "-r", str(FPS), str(ca)], check=True)
            clips.append(ca)
            # 멈춰 있는 구간 — 마지막 프레임을 늘립니다
            if hold > 0.05:
                ch = tmp / f"h{si:02d}.mp4"
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1",
                                "-i", str(fdir / f"f{n-1:04d}.png"), "-t", f"{hold:.2f}",
                                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                                "-r", str(FPS), str(ch)], check=True)
                clips.append(ch)
            mcap = re.search(r'<div class="cap"[^>]*>(.*?)</div>', html, re.S)
            if mcap:
                srt_rows.append((t_abs, t_abs + anim + hold,
                                 re.sub(r"<[^>]+>", "", mcap.group(1)).strip()))
            t_abs += anim + hold
        b.close()

    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{c}'\n" for c in clips), encoding="utf-8")
    silent = tmp / "silent.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(lst), "-c", "copy", str(silent)], check=True)

    # 음성 — 있으면 합성, 없으면 무음
    narr = next((base / f"narration{e}" for e in (".mp3", ".m4a", ".wav")
                 if (base / f"narration{e}").exists()), None)
    out = base / "video.mp4"
    if narr:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent), "-i", str(narr),
                        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                        "-b:a", "128k", "-shortest", str(out)], check=True)
    else:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent),
                        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "64k", str(out)], check=True)
    # -shortest 는 짧은 쪽에 맞춰 자릅니다. 나레이션이 설계보다 짧으면
    # 영상이 통째로 잘린 채 조용히 넘어갑니다. 실제로 그런 적이 있습니다.
    made = float(subprocess.run(["ffmpeg" and "ffprobe", "-v", "error", "-show_entries",
                                 "format=duration", "-of", "csv=p=0", str(out)],
                                capture_output=True, text=True).stdout.strip() or 0)
    if abs(made - t_abs) > 1.0:
        raise SystemExit(f"영상 길이가 설계와 다릅니다 — 설계 {t_abs:.1f}초 / 실제 {made:.1f}초\n"
                         f"  나레이션이 짧아 -shortest 로 잘렸을 수 있습니다")

    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out), "-vframes", "1",
                    str(base / "cover.png")], check=True)

    def ts(s):
        h, r = divmod(s, 3600)
        mm, ss = divmod(r, 60)
        return f"{int(h):02d}:{int(mm):02d}:{ss:06.3f}".replace(".", ",")

    (base / "video.srt").write_text(
        "".join(f"{i+1}\n{ts(a)} --> {ts(b_)}\n{tx}\n\n"
                for i, (a, b_, tx) in enumerate(srt_rows)), encoding="utf-8")
    stamp(base, "video")
    return out, t_abs, bool(narr)


def stamp(base, kind):
    """산출물이 어느 data.json 에서 나왔는지 남깁니다.

    렌더는 사람이 손으로 돌립니다. data.json 을 고치고 렌더를 잊으면
    옛 산출물이 그대로 남고, 게이트는 그걸 최신인 줄 알고 읽습니다.
    실제로 환급금 영상이 옛 흐름 그대로 32.5초로 남아 있었고,
    게이트는 "40초 미만"이라며 엉뚱한 곳을 가리켰습니다.

    mtime 은 클론하면 전부 같아져서 못 씁니다. 내용 해시를 씁니다.
    """
    import hashlib, json, pathlib
    base = pathlib.Path(base)
    raw = (base / "data.json").read_bytes()
    f = base / ".render.json"
    cur = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    cur[kind] = hashlib.sha1(raw).hexdigest()
    f.write_text(json.dumps(cur, ensure_ascii=False, indent=1), encoding="utf-8")


def main(argv):
    base = pathlib.Path(argv[1])
    d = json.loads((base / "data.json").read_text(encoding="utf-8"))
    out, dur, has_narr = render(d, base)
    print(f"[video] {out.name} · {dur:.1f}초 · 구조 {d['meta'].get('video_structure','countdown')} "
          f"· 음성 {'있음' if has_narr else '없음(무음)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
