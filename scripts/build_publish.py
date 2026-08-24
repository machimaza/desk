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
    (out / "images.txt").write_text(
        "본문에 나오는 순서입니다. 에디터에서 이 순서대로 올리세요.\n\n"
        + "\n".join(f"{i+1}. {n}" for i, n in enumerate(imgs)) + "\n", encoding="utf-8")

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
    print(f"[publish] {out}/ — tistory.html · naver.txt · meta.json · images.txt")
    print(f"  제목 {meta['제목']}")
    print(f"  태그 {', '.join(meta['태그'])}")
    print(f"  이미지 {len(imgs)}장 · 본문 {meta['본문자수']}자")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
