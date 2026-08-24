#!/usr/bin/env python3
"""발행 키트 생성 — 브라우저에 붙여 넣을 재료를 미리 만들어 둡니다.

왜 필요한가
  티스토리 Open API 는 2024년 2월에 종료됐고(글쓰기 포함), 네이버 블로그는
  개인 블로그용 공개 글쓰기 API 가 없습니다. 그래서 발행 경로는 브라우저뿐입니다.
  브라우저를 몰기 전에, 붙여 넣을 것들이 정리돼 있어야 작업이 짧아집니다.

만드는 것 (publish/ 폴더)
  tistory.html   티스토리 HTML 모드에 그대로 붙여 넣는 본문
  naver.txt      네이버 스마트에디터용 평문 (이미지 삽입 지점 표시)
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
          "정확한 금액과 자격은 국민건강보험공단 1577-1000 에서 확인하세요.",
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
    print(f"[publish] {out}/ — tistory.html · naver.txt · instagram.txt · threads.txt · meta.json · images.txt")
    print(f"  제목 {meta['제목']}")
    print(f"  태그 {', '.join(meta['태그'])}")
    print(f"  이미지 {len(imgs)}장 · 본문 {meta['본문자수']}자")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
