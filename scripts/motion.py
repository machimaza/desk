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
.cat-건강{--cat:var(--cat-health)}
.cat-재테크{--cat:var(--cat-money)}
.cat-생활꿀팁{--cat:var(--cat-life)}
body{font-family:var(--font);background:var(--paper);color:var(--ink);
  width:1080px;height:1920px;overflow:hidden}
.wrap{width:1080px;height:1920px;padding:210px 190px 430px 100px;
  display:flex;flex-direction:column}
.top{display:flex;align-items:center;gap:16px;margin-bottom:50px}
.badge{background:var(--cat);color:#fff;font-size:34px;font-weight:900;
  padding:14px 30px;border-radius:999px}
.pg{margin-left:auto;font-size:34px;font-weight:800;color:var(--ink-soft)}
.body{flex:1;display:flex;flex-direction:column;justify-content:center}
.kicker{font-size:52px;font-weight:800;color:var(--cat);margin-bottom:30px}
.head{font-weight:900;line-height:1.18;letter-spacing:-.035em;word-break:keep-all}
/* 자릿수가 길어져도 단위가 줄바꿈되지 않도록 — 프로토타입에서 발견한 버그 */
.big{font-size:132px;font-weight:900;color:var(--cat);letter-spacing:-.05em;
  margin:30px 0 18px;white-space:nowrap;font-variant-numeric:tabular-nums}
.unit{font-size:64px;font-weight:800;margin-left:6px}
.bar{height:26px;background:var(--line);overflow:hidden;border-radius:999px}
.fill{height:100%;background:var(--cat);border-radius:999px}
.cmp{display:flex;flex-direction:column;gap:44px;margin-top:20px}
.cmp .lab2{font-size:40px;font-weight:800;color:var(--ink-soft);margin-bottom:14px}
.cmp .v2{font-size:84px;font-weight:900;letter-spacing:-.04em;white-space:nowrap;
  font-variant-numeric:tabular-nums;margin-bottom:16px}
.stepno{width:104px;height:104px;border-radius:999px;background:var(--cat);color:#fff;
  font-size:56px;font-weight:900;display:flex;align-items:center;justify-content:center;
  margin-bottom:34px}
.steptx{font-size:62px;font-weight:800;line-height:1.35;letter-spacing:-.03em;word-break:keep-all}
.tbl{width:100%;border-collapse:collapse;font-size:36px}
.tbl td{padding:16px 12px;border-bottom:2px solid var(--line);font-weight:700}
.tbl td:last-child{text-align:right;color:var(--cat);font-weight:900}
.dd{position:absolute;top:210px;right:100px;background:var(--ink);color:var(--paper);
  font-size:30px;font-weight:900;padding:12px 22px;border-radius:12px}
.cap{position:absolute;left:100px;right:190px;bottom:460px;font-size:46px;font-weight:800;
  line-height:1.35;border-left:8px solid var(--cat);padding-left:26px;word-break:keep-all}
.brand{position:absolute;left:100px;bottom:625px;font-size:26px;font-weight:800;
  color:var(--ink-soft)}
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
            f'<style>{CSS}</style></head><body class="cat-{esc(cat)}">{inner}'
            f'<script>{JS}\n{script}</script></body></html>')


# ── 장면 정의 ──────────────────────────────────────────────────────────
# 각 장면은 (html, 움직이는 시간, 멈춰 있는 시간, 자막) 입니다.

def scene_title(m, hook, dd):
    inner = f'''<div class="wrap">
<div class="top"><div class="badge">{esc(m["category"])}</div></div>
<div class="body">
  <div class="kicker" id="k">{esc(m["category"])}</div>
  <div class="head" id="h" style="font-size:{max(52, 108 - len(m["title"]))}px">{esc(m["title"])}</div>
</div></div>{dd}<div class="cap" id="c">{esc(hook)}</div>
<div class="brand">@machimaza</div>'''
    js = '''window.draw=(t)=>{
  enter(document.getElementById('k'), easeOut(seg(t,0.0,0.5)));
  enter(document.getElementById('h'), easeOut(seg(t,0.25,0.7)));
  enter(document.getElementById('c'), easeOut(seg(t,0.8,0.6)));
};'''
    return page(m["category"], inner, js), 1.6, 3.0


def scene_value(m, it, pg, ratio, dd):
    num, unit = parse_amount(it["value"])
    inner = f'''<div class="wrap">
<div class="top"><div class="badge">{esc(m["category"])}</div><div class="pg">{esc(pg)}</div></div>
<div class="body">
  <div class="head" id="l" style="font-size:{max(58, 100 - len(it["label"]) * 2)}px">{esc(it["label"])}</div>
  <div class="big" id="n">0</div>
  <div class="bar"><div class="fill" id="b" style="width:0%"></div></div>
</div></div>{dd}<div class="cap" id="c">{esc(it.get("caption") or it["detail"])[:60]}</div>
<div class="brand">@machimaza</div>'''
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
<div class="top"><div class="badge">{esc(m["category"])}</div><div class="pg">{esc(pg)}</div></div>
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
<div class="brand">@machimaza</div>'''
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
<div class="top"><div class="badge">{esc(m["category"])}</div><div class="pg">{esc(pg)}</div></div>
<div class="body">
  <div class="stepno" id="s">{no}</div>
  <div class="steptx" id="l">{esc(it["label"])}</div>
  <div class="big" id="n" style="font-size:96px">0</div>
</div></div>{dd}<div class="cap" id="c">{esc(tx)}</div>
<div class="brand">@machimaza</div>'''
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


def scene_table(m, items, dd):
    rows = "".join(
        f'<tr class="r" style="opacity:0"><td>{esc(i["label"])}</td>'
        f'<td>{esc(i["value"])}</td></tr>' for i in items)
    inner = f'''<div class="wrap">
<div class="top"><div class="badge">{esc(m["category"])}</div><div class="pg">전체</div></div>
<div class="body"><table class="tbl">{rows}</table></div>
</div>{dd}<div class="cap" id="c">지금 캡처해두세요. 신청할 때 다시 필요합니다.</div>
<div class="brand">@machimaza</div>'''
    js = '''window.draw=(t)=>{
  const rs = document.querySelectorAll('.r');
  rs.forEach((r,i)=>{ enter(r, easeOut(seg(t, 0.12*i, 0.45))); });
  enter(document.getElementById('c'), easeOut(seg(t, 0.12*rs.length+0.2, 0.5)));
};'''
    return page(m["category"], inner, js), 1.8, 4.4


# ── 렌더 ───────────────────────────────────────────────────────────────

def build_scenes(d):
    m, items = d["meta"], d["items"]
    dd = f'<div class="dd">{esc(m["dday"])}</div>' if m.get("dday") else ""
    struct = m.get("video_structure", "countdown")
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
    tmp = pathlib.Path(tempfile.mkdtemp())
    clips, srt_rows, t_abs = [], [], 0.0

    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch(args=["--force-device-scale-factor=1"])
        pg = b.new_page(viewport={"width": W, "height": HGT})
        for si, (html, anim, hold) in enumerate(scenes):
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
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out), "-vframes", "1",
                    str(base / "cover.png")], check=True)

    def ts(s):
        h, r = divmod(s, 3600)
        mm, ss = divmod(r, 60)
        return f"{int(h):02d}:{int(mm):02d}:{ss:06.3f}".replace(".", ",")

    (base / "video.srt").write_text(
        "".join(f"{i+1}\n{ts(a)} --> {ts(b_)}\n{tx}\n\n"
                for i, (a, b_, tx) in enumerate(srt_rows)), encoding="utf-8")
    return out, t_abs, bool(narr)


def main(argv):
    base = pathlib.Path(argv[1])
    d = json.loads((base / "data.json").read_text(encoding="utf-8"))
    out, dur, has_narr = render(d, base)
    print(f"[video] {out.name} · {dur:.1f}초 · 구조 {d['meta'].get('video_structure','countdown')} "
          f"· 음성 {'있음' if has_narr else '없음(무음)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
