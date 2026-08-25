#!/usr/bin/env python3
"""쓰레드에 올립니다 — 영상 한 편 + 본문, 링크는 답글로.

왜 쓰레드부터인가
  본인 계정에 올리는 것은 Meta 앱 검수 없이 됩니다.
  인스타는 페이스북 페이지 연결과 검수(2~4주)가 필요하고,
  티스토리는 API 가 2024년 2월에 닫혔으며, 네이버 블로그는 쓰기 API 가 없습니다.

어떻게 올라가나
  1. 영상을 릴리스에 올려 공개 주소를 만듭니다 (Meta 가 그 주소로 가져갑니다)
  2. 담을 그릇(container)을 만들고
  3. 영상 처리가 끝날 때까지 기다렸다가
  4. 발행합니다
  5. 링크는 답글에 답니다 — 첫 게시물에 링크가 있으면 노출이 줄어듭니다

기본은 '미리보기'입니다. 실제로 올리려면 --publish 를 붙여야 합니다.
사람이 확인하지 않은 글이 공개되는 일이 없도록 일부러 이렇게 두었습니다.

  python scripts/publish_threads.py content/2026-08-24-건강보험-환급금
  python scripts/publish_threads.py <폴더> --publish
"""
import argparse
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://graph.threads.net/v1.0"
LIMIT = 500          # 쓰레드 본문 글자 수 상한
WAIT_MAX = 300       # 영상 처리 대기 상한(초)


def _conf():
    uid = os.environ.get("THREADS_USER_ID", "").strip()
    tok = os.environ.get("THREADS_ACCESS_TOKEN", "").strip()
    if not uid or not tok:
        raise SystemExit(
            "쓰레드 열쇠가 없습니다. 저장소 Settings → Secrets 에 넣으세요.\n"
            "  THREADS_USER_ID        쓰레드 사용자 번호\n"
            "  THREADS_ACCESS_TOKEN   장기 토큰 (60일마다 갱신)\n"
            "  만드는 법은 PUBLISH_AUTO.md 를 보세요.")
    return uid, tok


def _call(method, path, params):
    url = f"{BASE}/{path}"
    data = urllib.parse.urlencode(params).encode()
    if method == "GET":
        url += "?" + data.decode()
        data = None
    req = urllib.request.Request(url, data=data, method=method)
    try:
        return json.loads(urllib.request.urlopen(req, timeout=120).read())
    except urllib.error.HTTPError as ex:
        body = ex.read().decode("utf-8", "replace")[:400]
        # 190 은 토큰 만료, 4 는 호출 한도, 100 은 값이 잘못된 경우입니다.
        raise SystemExit(f"쓰레드 응답 {ex.code} — {body}")


def read_text(base):
    """발행 키트가 만들어 둔 본문을 읽습니다. # 로 시작하는 안내줄은 뺍니다."""
    f = base / "publish" / "threads.txt"
    if not f.exists():
        raise SystemExit(f"{f} 가 없습니다. 먼저 build_publish.py 를 돌리세요.")
    body = "\n".join(l for l in f.read_text(encoding="utf-8").splitlines()
                     if not l.startswith("#")).strip()
    if not body:
        raise SystemExit("본문이 비어 있습니다.")
    if len(body) > LIMIT:
        raise SystemExit(f"본문이 {len(body)}자입니다. 쓰레드 상한은 {LIMIT}자입니다.")
    return body


def wait_ready(cid, tok):
    """영상은 바로 못 올립니다. Meta 가 받아서 변환할 때까지 기다립니다."""
    waited = 0
    while waited < WAIT_MAX:
        r = _call("GET", cid, {"fields": "status,error_message", "access_token": tok})
        st = r.get("status")
        if st == "FINISHED":
            return
        if st == "ERROR":
            raise SystemExit(f"영상 처리 실패 — {r.get('error_message')}")
        time.sleep(5)
        waited += 5
        print(f"  … 영상 처리 대기 {waited}초 ({st})")
    raise SystemExit(f"{WAIT_MAX}초를 기다렸는데 처리가 안 끝났습니다.")


def publish(base, media_url, reply_link="", do_publish=False):
    base = pathlib.Path(base)
    text = read_text(base)
    print(f"[쓰레드] 본문 {len(text)}자 / {LIMIT}자")
    print("─" * 46)
    print(text)
    print("─" * 46)
    print(f"[쓰레드] 영상 {media_url or '(없음 — 글만)'}")
    if reply_link:
        print(f"[쓰레드] 답글 링크 {reply_link}")

    if not do_publish:
        print("\n미리보기입니다. 실제로 올리려면 --publish 를 붙이세요.")
        return None

    uid, tok = _conf()
    p = {"text": text, "access_token": tok}
    if media_url:
        p |= {"media_type": "VIDEO", "video_url": media_url}
    else:
        p["media_type"] = "TEXT"
    cid = _call("POST", f"{uid}/threads", p)["id"]
    print(f"[쓰레드] 그릇 {cid}")

    if media_url:
        wait_ready(cid, tok)

    post = _call("POST", f"{uid}/threads_publish",
                 {"creation_id": cid, "access_token": tok})["id"]
    print(f"[쓰레드] 올렸습니다 — {post}")

    # 링크는 답글로. 첫 게시물에 링크가 있으면 노출이 줄어듭니다.
    if reply_link:
        rid = _call("POST", f"{uid}/threads",
                    {"media_type": "TEXT", "text": f"전체 내용은 여기에 정리했습니다\n{reply_link}",
                     "reply_to_id": post, "access_token": tok})["id"]
        _call("POST", f"{uid}/threads_publish",
              {"creation_id": rid, "access_token": tok})
        print("[쓰레드] 답글에 링크를 달았습니다")
    return post


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("--media-url", default="", help="영상 공개 주소")
    ap.add_argument("--upload", action="store_true", help="영상을 릴리스에 올려 주소를 만듭니다")
    ap.add_argument("--link", default="", help="답글에 달 블로그 주소")
    ap.add_argument("--publish", action="store_true", help="실제로 올립니다")
    a = ap.parse_args(argv[1:])

    url = a.media_url
    if a.upload and not url:
        sys.path.insert(0, str(pathlib.Path(__file__).parent))
        import release_asset
        vid = pathlib.Path(a.base) / "video.mp4"
        if vid.exists():
            url = release_asset.upload(vid, f"media-{pathlib.Path(a.base).name}")
            print(f"[릴리스] {url}")
    publish(a.base, url, a.link, a.publish)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
