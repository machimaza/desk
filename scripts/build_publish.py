#!/usr/bin/env python3
"""발행 키트 생성 — 브라우저에 붙여 넣을 재료를 미리 만들어 둡니다.

왜 필요한가
  티스토리 Open API 는 2024년 2월에 종료됐고(글쓰기 포함), 네이버 블로그는
  개인 블로그용 공개 글쓰기 API 가 없습니다. 그래서 발행 경로는 브라우저뿐입니다.
  브라우저를 몰기 전에, 붙여 넣을 것들이 정리돼 있어야 작업이 짧아집니다.

만드는 것 (publish/ 폴더)
  tistory.html   티스토리 HTML 모드에 그대로 붙여 넣는 본문
  naver.html     네이버용 — 브라우저에서 열어 통째로 복사해 붙입니다 (표·굵게 유지)
  naver.txt      네이버용 평문 (표가 필요 없을 때 · 이미지 삽입 지점 표시)
  meta.json      제목 · 요약 · 태그 · 카테고리
  images.txt     업로드해야 할 이미지 순서
  instagram.txt  캐러셀 캡션 + 해시태그 5개
  threads.txt    쓰레드용 (500자 제한)

사용:  python3 scripts/build_publish.py <콘텐츠폴더>
"""
import sys, json, re, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

# 티스토리 본문에 넣을 최소 스타일. 외부 CSS 를 못 쓰므로 인라인으로 둡니다.
TBL = 'style="width:100%;border-collapse:collapse;margin:20px 0;font-size:15px"'
TD = 'style="border:1px solid #ddd;padding:10px 12px"'
TH = 'style="border:1px solid #ddd;padding:10px 12px;background:#f6f6f6;font-weight:700"'


def notice_for(category):
    """고지문구는 categories.json 이 카테고리별로 들고 있습니다.

    예전에는 이 자리에 '국민건강보험공단 1577-1000' 이 코드에 박혀 있었습니다.
    건강보험 글에서 시작한 문장이 그대로 남아, 근로장려금 글의 인스타 캡션이
    **엉뚱한 기관 번호**를 안내하고 있었습니다.
    선언만 되고 아무도 읽지 않던 필드가 또 하나 있었던 셈입니다.
    """
    try:
        cats = json.loads((ROOT / "categories.json").read_text(encoding="utf-8"))
        txt = (cats.get("카테고리", {}).get(category) or {}).get("고지문구") or ""
    except Exception:
        txt = ""
    return txt.strip()


def md_to_tistory(md):
    import markdown
    html = markdown.markdown(md, extensions=["tables", "fenced_code"])
    # 티스토리 에디터는 클래스가 없는 표를 밋밋하게 렌더합니다. 인라인 스타일을 박아 둡니다.
    html = html.replace("<table>", f"<table {TBL}>")
    html = re.sub(r"<td>", f"<td {TD}>", html)
    html = re.sub(r"<th>", f"<th {TH}>", html)
    html = html.replace("<blockquote>",
                        '<blockquote style="border-left:4px solid #2E6B5E;margin:20px 0;'
                        'padding:12px 18px;background:#f8f9f8">')
    # 이미지는 에디터에서 직접 올려야 하므로, 위치만 표시로 남깁니다.
    html = re.sub(r'<p><img alt="([^"]*)" src="images/([^"]+)"\s*/?></p>',
                  r'<p style="background:#FFF3CD;border:1px dashed #C89B3C;padding:14px;'
                  r'text-align:center;font-weight:700">▲ 여기에 \2 업로드 · alt: \1</p>', html)
    return html


def md_to_naver(md):
    """스마트에디터는 HTML 을 잘 못 받습니다. 평문으로 내리되 구조는 남깁니다."""
    t = md
    t = re.sub(r'!\[([^\]]*)\]\(images/([^)]+)\)', r'\n[[이미지 삽입: \2 · alt: \1]]\n', t)
    t = re.sub(r'^#{1,6}\s*(.+)$', r'\n■ \1', t, flags=re.M)
    t = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1 (\2)', t)     # 링크는 주소를 괄호로
    t = re.sub(r'\*\*(.+?)\*\*', r'\1', t)
    t = re.sub(r'^\s*\|', '|', t, flags=re.M)
    t = re.sub(r'\n{3,}', '\n\n', t)
    return t.strip()


# ── 네이버용 HTML ──────────────────────────────────────────────────
# 스마트에디터에는 HTML 소스 모드가 없습니다. 그래서 파일을 '붙여넣는' 게 아니라,
# **브라우저에 띄운 화면을 통째로 복사해서** 에디터에 붙입니다(서식 있는 붙여넣기).
# 이 경로로는 제목·굵게·목록·**표**가 살아남습니다 — 손이 제일 많이 가던 부분입니다.
#
# 정직하게 적어 둘 것: 네이버는 붙여넣은 것을 자기 서식으로 정규화합니다.
# 글꼴과 색은 네이버 기본값으로 바뀔 수 있습니다. 그래서 여기서는 색을 쓰지 않고
# 검정·회색만 씁니다 — 어차피 바뀔 것을 넣으면 결과가 들쭉날쭉해집니다.
# 이미지는 클립보드로 넘어가지 않습니다. 자리표시가 남고 거기에 직접 올리면 됩니다.

NAVER_CSS = """
:root{color-scheme:light}
*{box-sizing:border-box}
body{margin:0;background:#eef0f3;
  font-family:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Malgun Gothic",
  "Noto Sans KR",sans-serif;color:#111;line-height:1.8}
.guide{max-width:860px;margin:24px auto 0;background:#fff8e1;border:1px solid #e8c874;
  border-radius:10px;padding:18px 22px;font-size:14px;line-height:1.7;color:#5a4a1f}
.guide b{color:#3b3110}
.guide ol{margin:10px 0 0;padding-left:20px}
.guide li{margin:4px 0}
button{margin-top:14px;font:inherit;font-weight:700;padding:10px 18px;border-radius:8px;
  border:1px solid #3b7a57;background:#3b7a57;color:#fff;cursor:pointer}
#msg{margin-left:12px;font-weight:700;color:#3b7a57}
.sheet{max-width:860px;margin:18px auto 60px;background:#fff;border-radius:10px;
  padding:44px 48px;box-shadow:0 1px 3px rgba(0,0,0,.12)}
/* 아래부터가 실제로 복사되는 부분입니다. 색을 쓰지 않습니다. */
/* 네이버 본문에 가깝게 — 15px · 줄간격 1.8. 보이는 것과 붙은 것이 다르면
   여기서 아무리 예뻐도 소용이 없습니다. */
#body{font-size:15px;line-height:1.8}
#body h2{font-size:19px;font-weight:800;margin:0}
#body h3{font-size:17px;font-weight:800;margin:0}
#body p{margin:0}
#body p:empty,#body p br:only-child{line-height:1.2}
#body hr{border:0;border-top:1px solid #ccc;margin:0}
/* 상세페이지에서 가져온 것 — 리드는 가운데, 소제목엔 번호, 인용은 가운데.
   본문은 왼쪽 정렬 그대로 둡니다. 정보 글에서 가운데 정렬은 눈이 줄 시작을
   매번 찾아야 해서 오히려 느려집니다. */
#body .lead{text-align:center;font-size:17px;line-height:1.9;font-weight:700}
#body .no{display:inline-block;margin-right:8px;font-weight:900}
#body .pull{text-align:center;border:0;background:none;
  font-size:17px;font-weight:700;line-height:1.9;padding:0}
#body .pull p{margin:0}
#body ul,#body ol{margin:0 0 16px;padding-left:22px}
#body li{margin:6px 0}
#body strong{font-weight:800}
#body table{width:100%;border-collapse:collapse;margin:18px 0;font-size:15px}
#body th{border:1px solid #999;padding:9px 11px;background:#f2f2f2;font-weight:800;
  text-align:left}
#body td{border:1px solid #999;padding:9px 11px}
#body blockquote{margin:18px 0;padding:12px 16px;border-left:4px solid #666;
  background:#f7f7f7}
#body .ph{border:2px dashed #999;background:#fafafa;padding:16px;text-align:center;
  font-weight:800;margin:18px 0}
"""

NAVER_JS = """
function pick(){
  const el = document.getElementById('body');
  const r = document.createRange(); r.selectNodeContents(el);
  const s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
  let ok = false;
  try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
  document.getElementById('msg').textContent =
    ok ? '복사했습니다. 스마트에디터에 붙여넣으세요.'
       : '본문이 선택됐습니다. Ctrl+C (맥은 Cmd+C) 를 누르세요.';
}
"""


def naver_rhythm(html):
    """네이버에 붙였을 때 **숨 쉴 자리**를 만듭니다.

    실제로 붙여넣어 보니 표·굵게·목록은 살아남는데 **여백이 전부 죽었습니다.**
    네이버가 붙여넣은 것을 자기 본문 스타일로 정규화하면서 line-height 와
    margin 을 자기 값으로 덮기 때문입니다. 그래서 글이 빽빽하게 붙어 나옵니다.

    CSS 로는 못 이깁니다. 대신 **빈 문단을 실제로 끼워 넣습니다** —
    빈 문단은 스타일이 아니라 내용이라서 정규화를 통과합니다.
    소제목 앞은 두 줄, 문단 사이는 한 줄입니다.
    """
    EMPTY = "<p><br></p>"
    # 소제목에 번호를 붙입니다 — 상세페이지에서 가져온 것 중 가장 값싼 장치입니다.
    # '1. · 2. · 3.' 이 붙으면 글이 몇 덩어리인지 눈으로 세집니다.
    n = [0]

    def _num(mo):
        n[0] += 1
        return f'<h2><span class="no">{n[0]}.</span>{mo.group(1)}</h2>'

    html = re.sub(r"<h2>(.*?)</h2>", _num, html, flags=re.S)
    # 블록이 끝날 때마다 한 줄 비웁니다.
    html = re.sub(r"(</(?:p|table|ul|ol|blockquote)>)", r"\1" + EMPTY, html)
    # 소제목 앞은 세 줄. 상세페이지의 '섹션이 바뀐다' 는 느낌은 대부분 여백이 만듭니다.
    # 앞에 구분선도 둡니다 — 네이버가 글자 크기를 덮어도 선은 남습니다.
    html = re.sub(r"<h2>", EMPTY * 2 + "<hr>" + EMPTY + "<h2>", html)
    html = re.sub(r"<h3>", EMPTY + "<h3>", html)
    html = re.sub(r"(</h[23]>)", r"\1" + EMPTY, html)
    # 인용은 가운데로. 한 편에 두세 번만 나오므로 여기서 호흡이 끊깁니다.
    html = html.replace("<blockquote>", '<blockquote class="pull">')
    html = html.replace(EMPTY + EMPTY + EMPTY + EMPTY, EMPTY + EMPTY + EMPTY)
    return html


def md_to_naver_html(md, title, imgs):
    import markdown
    html = markdown.markdown(md, extensions=["tables", "fenced_code"])
    html = re.sub(r'<p><img alt="([^"]*)" src="images/([^"]+)"\s*/?></p>',
                  r'<p class="ph">▲ 여기에 \2 를 올리세요 · 대체텍스트: \1</p>', html)
    # 첫 문단의 **첫 문장만** 리드로 세웁니다.
    # 문단 전체를 가운데 정렬해 봤더니 네 줄이 폭을 꽉 채워서 가운데인지 티가
    # 안 났습니다. 상세페이지의 리드가 눈에 들어오는 이유는 정렬이 아니라
    # **짧아서**입니다. 첫 문장만 떼고 나머지는 보통 문단으로 둡니다.
    mo = re.match(r"<p>(.+?[.!?])\s+(.*?)</p>", html, flags=re.S)
    if mo:
        html = (f'<p class="lead">{mo.group(1)}</p><p>{mo.group(2)}</p>'
                + html[mo.end():])
    html = naver_rhythm(html)
    # 이미지 목록은 <li> 로 넣으면 안내 번호(1·2·3)에 이어 붙어 4·5·6 이 됩니다.
    # 안내 단계가 여덟 개인 것처럼 보였습니다. 한 줄 안에 나열합니다.
    steps = " → ".join(imgs)
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{title} — 네이버 붙여넣기용</title><style>{NAVER_CSS}</style></head><body>'
            f'<div class="guide"><b>네이버 블로그에 붙여넣는 법</b>'
            f'<ol><li>아래 <b>본문 복사</b> 를 누릅니다 (안 되면 본문만 드래그해서 Ctrl+C).</li>'
            f'<li>스마트에디터 본문에 <b>그대로 붙여넣습니다.</b> 제목·굵게·목록·표가 따라옵니다.</li>'
            f'<li>점선 상자 자리에 이미지를 올리고 상자는 지웁니다 — 순서: {steps or "없음"}</li>'
            f'<li>글꼴과 색은 네이버가 자기 기본값으로 바꿉니다. 그대로 두시면 됩니다.</li></ol>'
            f'<button onclick="pick()">본문 복사</button><span id="msg"></span></div>'
            f'<div class="sheet"><div id="body">{html}</div></div>'
            f'<script>{NAVER_JS}</script></body></html>')


def build(base):
    base = pathlib.Path(base)
    d = json.loads((base / "data.json").read_text(encoding="utf-8"))
    md = (base / "blog.md").read_text(encoding="utf-8")
    m = d["meta"]
    out = base / "publish"
    out.mkdir(exist_ok=True)

    body = md.split("\n", 1)[1] if md.startswith("# ") else md   # H1 은 제목 칸으로 감
    (out / "tistory.html").write_text(md_to_tistory(body), encoding="utf-8")
    (out / "naver.txt").write_text(md_to_naver(body), encoding="utf-8")

    imgs = re.findall(r'!\[[^\]]*\]\(images/([^)]+)\)', md)
    (out / "naver.html").write_text(
        md_to_naver_html(body, m["title"], imgs), encoding="utf-8")
    cards = sorted(x.name for x in (base / "images").glob("card_*.png"))
    (out / "images.txt").write_text(
        "[블로그] 본문에 나오는 순서입니다. 에디터에서 이 순서대로 올리세요.\n"
        + "\n".join(f"  {i+1}. {n}" for i, n in enumerate(imgs))
        + "\n\n[인스타 캐러셀] flow 순서 그대로 올리세요.\n"
        + "\n".join(f"  {i+1}. {n}" for i, n in enumerate(cards))
        + "\n\n[포스터] poster.png — 단독 공유용\n", encoding="utf-8")

    # ── 인스타 · 쓰레드 ────────────────────────────────────────────
    # 캐러셀이 기본입니다(단일 이미지 대비 저장 9배). 카드는 flow 순서 그대로.
    # 첫 두 줄이 '더 보기' 앞에 보이는 전부이므로 거기서 승부가 납니다.
    scenes = d.get("flow", {}).get("scenes", [])
    hook = d.get("hook", "")
    beats = [sc.get("screen", "") for sc in scenes[1:] if sc.get("screen")]
    # 해시태그는 5개까지 (2025.12.18 인스타 공식 상한)
    tags = ["#" + k.replace(" ", "") for k in m.get("keywords", [])][:4] + ["#마치마자"]
    ig = [hook, "",
          "\n".join(f"· {b}" for b in beats[:5]), "",
          d.get("cta", "저장해두세요"), "",
          (notice_for(m.get("category", "")) or "정확한 내용은 담당 기관에 확인하세요") + ".",
          "출처는 카드 안에 표기했습니다.", "",
          " ".join(tags)]
    (out / "instagram.txt").write_text(
        "# 캐러셀 캡션 — 첫 두 줄이 '더 보기' 앞에 보이는 전부입니다\n"
        f"# 카드 {len(scenes)}장을 flow 순서대로 올리세요 (images.txt 참고)\n\n"
        + "\n".join(ig) + "\n", encoding="utf-8")

    th = [hook, ""] + [f"· {b}" for b in beats[:3]] + ["", d.get("cta", "")]
    body_th = "\n".join(th)
    (out / "threads.txt").write_text(
        f"# 쓰레드 — 500자 제한. 현재 {len(body_th)}자\n"
        "# 링크는 첫 게시물에 넣지 말고 답글에 다세요\n\n" + body_th + "\n", encoding="utf-8")

    # 요약은 도입부 첫 문단에서 뽑습니다 (검색결과 설명문으로 쓰임)
    first = next((p.strip() for p in body.split("\n\n")
                  if p.strip() and not p.startswith(("!", "#", ">", "|"))), "")
    summary = re.sub(r"\*\*|\[|\]\([^)]*\)", "", first)[:155]
    # 제목은 data.json 의 짧은 제목이 아니라 blog.md 의 H1 을 씁니다.
    # H1 쪽에 검색용 수식어(｜2026년 기준 …)가 붙어 있고, 그게 발행 제목이어야 합니다.
    h1 = md.split("\n", 1)[0].lstrip("# ").strip() if md.startswith("# ") else m["title"]
    meta = {"제목": h1,
            "짧은제목": m["title"],
            "요약": summary,
            "카테고리": m["category"],
            "태그": m.get("keywords", []),
            "발행일": m["publish_date"],
            "이미지수": len(imgs),
            "본문자수": len(md)}
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                                   encoding="utf-8")
    return out, meta, imgs


def main(argv):
    out, meta, imgs = build(argv[1])
    print(f"[publish] {out}/ — tistory.html · naver.html · naver.txt · instagram.txt · threads.txt · meta.json · images.txt")
    print(f"  제목 {meta['제목']}")
    print(f"  태그 {', '.join(meta['태그'])}")
    print(f"  이미지 {len(imgs)}장 · 본문 {meta['본문자수']}자")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
