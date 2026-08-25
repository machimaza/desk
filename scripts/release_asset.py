#!/usr/bin/env python3
"""영상에 공개 주소를 붙입니다 — 릴리스 첨부파일로 올려서.

왜 필요한가
  쓰레드·인스타는 파일을 직접 받지 않습니다. "이 주소에서 가져가라"고 알려주면
  Meta 서버가 그 주소로 받아갑니다. 그래서 먼저 공개된 자리에 둬야 합니다.

왜 저장소가 아니라 릴리스인가
  영상은 편당 2MB 안팎이고 고칠 때마다 새로 만듭니다. 저장소에 넣으면
  기록이 계속 쌓여 무거워집니다. 릴리스는 덮어쓸 수 있고 기록에 안 남습니다.

  python scripts/release_asset.py <파일> --tag media-2026-08-24-환급금
"""
import argparse
import json
import mimetypes
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"
UPLOAD = "https://uploads.github.com"


def _repo():
    r = os.environ.get("GITHUB_REPOSITORY", "machimaza/desk")
    return r.split("/", 1)


def _token():
    t = os.environ.get("GITHUB_TOKEN", "").strip()
    if not t:
        raise SystemExit(
            "GITHUB_TOKEN 이 없습니다.\n"
            "  러너에서는 워크플로가 자동으로 넘겨줍니다.\n"
            "  손으로 돌린다면 GITHUB_TOKEN=... 을 앞에 붙이세요.")
    return t


def _req(method, url, body=None, token=None, ctype="application/json"):
    data = None
    if body is not None:
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
    r = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {token or _token()}",
        "Accept": "application/vnd.github+json",
        "Content-Type": ctype})
    try:
        return json.loads(urllib.request.urlopen(r, timeout=300).read() or b"{}")
    except urllib.error.HTTPError as ex:
        raise SystemExit(f"GitHub 응답 {ex.code} — {ex.read().decode('utf-8','replace')[:300]}")


def upload(path, tag, clobber=True):
    """파일을 릴리스에 올리고 공개 주소를 돌려줍니다."""
    path = pathlib.Path(path)
    owner, repo = _repo()
    tok = _token()

    # 릴리스가 없으면 만듭니다. 사람이 보는 목록을 어지럽히지 않게 draft 는 아니되
    # prerelease 로 둡니다 — 이건 배포물이 아니라 전달용 자리입니다.
    try:
        rel = _req("GET", f"{API}/repos/{owner}/{repo}/releases/tags/"
                          f"{urllib.parse.quote(tag)}", token=tok)
    except SystemExit:
        rel = _req("POST", f"{API}/repos/{owner}/{repo}/releases",
                   {"tag_name": tag, "name": tag, "prerelease": True,
                    "body": "영상·이미지 전달용. 쓰레드·인스타가 이 주소로 가져갑니다."},
                   token=tok)

    # 같은 이름이 이미 있으면 지웁니다. 안 지우면 GitHub 이 이름 뒤에 숫자를 붙입니다.
    if clobber:
        for a in rel.get("assets", []):
            if a["name"] == path.name:
                _req("DELETE", f"{API}/repos/{owner}/{repo}/releases/assets/{a['id']}",
                     token=tok)

    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    url = (f"{UPLOAD}/repos/{owner}/{repo}/releases/{rel['id']}/assets"
           f"?name={urllib.parse.quote(path.name)}")
    asset = _req("POST", url, path.read_bytes(), token=tok, ctype=ctype)
    return asset["browser_download_url"]


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--tag", required=True)
    a = ap.parse_args(argv[1:])
    print(upload(a.path, a.tag))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
