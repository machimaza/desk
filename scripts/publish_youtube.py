#!/usr/bin/env python3
"""유튜브 쇼츠로 올립니다.

미리 알아둘 것 두 가지
  1. 앱이 구글 검수를 받기 전에는 **비공개로만** 올라갑니다.
     올리는 것 자체는 되니, 검수가 끝나면 공개로 바꾸면 됩니다.
  2. OAuth 동의 화면이 '테스트' 상태면 **갱신 토큰이 7일마다 만료**됩니다.
     '프로덕션'으로 게시해야 만료되지 않습니다. YOUTUBE_SETUP.md 참고.

어떻게 올라가나
  갱신 토큰으로 접근 토큰을 받고 → 올릴 자리를 예약하고 → 파일을 밀어 넣습니다.
  큰 파일을 한 번에 보내면 중간에 끊겼을 때 처음부터 다시 해야 해서,
  구글은 '재개 가능한 업로드'를 씁니다. 우리 영상은 2MB 라 한 번에 끝납니다.

기본은 '미리보기'입니다. 실제로 올리려면 --publish 를 붙여야 합니다.

  python scripts/publish_youtube.py content/2026-08-24-건강보험-환급금
  python scripts/publish_youtube.py <폴더> --publish --privacy private
"""
import argparse
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = ("https://www.googleapis.com/upload/youtube/v3/videos"
              "?uploadType=resumable&part=snippet,status")
TITLE_MAX = 100
DESC_MAX = 5000
CATEGORY = "22"      # People & Blogs — 정보 전달 채널에 무난합니다

# 다른 채널 안내. 유튜브 설명란은 외부 링크에 불이익이 없습니다
# (쓰레드는 첫 게시물에 링크가 있으면 노출이 줄어 답글로 뺐지만, 여기는 반대입니다).
# 글을 먼저 둡니다 — 영상은 요약이고, 자세한 건 글에 있습니다.
def channels_block():
    """설명란에 붙일 다른 채널 안내.

    주소를 여기 적어두면 채널이 바뀔 때마다 세 파일을 고쳐야 합니다 —
    실제로 publish_youtube.py · docs/index.html · BRAND.md 에 흩어져 있었습니다.
    channels.json 하나만 봅니다.

    유튜브 자기 자신은 뺍니다. 보고 있는 사람에게 다시 안내할 이유가 없습니다.
    """
    d = json.loads((ROOT / "channels.json").read_text(encoding="utf-8"))
    by = {}
    for c in d["채널"]:
        if c["키"] == "youtube":
            continue
        by.setdefault(c["묶음"], []).append(c)
    L = ["━━━━━━━━━━━━━━━", "📌 자세한 내용은 블로그에", ""]
    for c in by.get("블로그", []):
        L.append(f'{c["이름"].split()[0]}  {c["주소"]}')
    L += ["", "같은 정보를 다른 곳에서도"]
    for g in ("소셜", "영상"):
        for c in by.get(g, []):
            L.append(f'{c["이름"]}  {c["주소"]}')
    L += ["", "마침 필요한 정보를, 알맞게 — 마치마자"]
    return "\n".join(L)


def _conf():
    cid = os.environ.get("YT_CLIENT_ID", "").strip()
    sec = os.environ.get("YT_CLIENT_SECRET", "").strip()
    ref = os.environ.get("YT_REFRESH_TOKEN", "").strip()
    missing = [n for n, v in (("YT_CLIENT_ID", cid), ("YT_CLIENT_SECRET", sec),
                              ("YT_REFRESH_TOKEN", ref)) if not v]
    if missing:
        raise SystemExit(
            "유튜브 열쇠가 없습니다: " + ", ".join(missing) + "\n"
            "  저장소 Settings → Secrets 에 넣으세요.\n"
            "  만드는 법은 YOUTUBE_SETUP.md 를 보세요.")
    return cid, sec, ref


def access_token():
    """갱신 토큰으로 한 시간짜리 접근 토큰을 받습니다."""
    cid, sec, ref = _conf()
    data = urllib.parse.urlencode({
        "client_id": cid, "client_secret": sec,
        "refresh_token": ref, "grant_type": "refresh_token"}).encode()
    try:
        r = json.loads(urllib.request.urlopen(
            urllib.request.Request(TOKEN_URL, data=data), timeout=60).read())
    except urllib.error.HTTPError as ex:
        body = ex.read().decode("utf-8", "replace")[:300]
        hint = ""
        if "invalid_grant" in body:
            hint = ("\n  갱신 토큰이 만료됐거나 취소됐습니다.\n"
                    "  OAuth 동의 화면이 '테스트' 상태면 7일마다 이렇게 됩니다.\n"
                    "  '프로덕션'으로 게시하고 토큰을 다시 받으세요.")
        raise SystemExit(f"구글 응답 {ex.code} — {body}{hint}")
    return r["access_token"]


def build_meta(base, privacy):
    """발행 키트가 만들어 둔 값에서 제목·설명을 짭니다."""
    pub = base / "publish"
    meta = json.loads((pub / "meta.json").read_text(encoding="utf-8"))

    # 쇼츠는 제목이 화면에 조금만 보입니다. 짧은 제목을 씁니다.
    # #Shorts 는 유튜브가 쇼츠로 알아보게 하는 신호입니다.
    title = f"{meta['짧은제목']} #Shorts"
    if len(title) > TITLE_MAX:
        title = title[:TITLE_MAX - 8].rstrip() + " #Shorts"

    body = "\n".join(l for l in (pub / "threads.txt").read_text(encoding="utf-8")
                     .splitlines() if not l.startswith("#")).strip()
    parts = [body, "",
             "정확한 금액과 자격은 소관 기관에서 확인하세요.",
             "출처는 영상 안에 표기했습니다.", "",
             channels_block(), "",
             " ".join("#" + t.replace(" ", "") for t in meta.get("태그", [])[:4]),
             "#마치마자"]
    desc = "\n".join(parts)[:DESC_MAX]

    return {"snippet": {"title": title, "description": desc,
                        "tags": meta.get("태그", [])[:10], "categoryId": CATEGORY,
                        "defaultLanguage": "ko", "defaultAudioLanguage": "ko"},
            "status": {"privacyStatus": privacy,
                       "selfDeclaredMadeForKids": False}}


def upload(base, privacy="private", do_publish=False):
    base = pathlib.Path(base)
    vid = base / "video.mp4"
    if not vid.exists():
        raise SystemExit(f"{vid} 가 없습니다. 먼저 영상을 만드세요.")
    body = build_meta(base, privacy)

    print(f"[유튜브] 제목  {body['snippet']['title']}")
    print(f"[유튜브] 공개  {privacy}")
    print(f"[유튜브] 파일  {vid} ({vid.stat().st_size:,} bytes)")
    print("─" * 46)
    print(body["snippet"]["description"])
    print("─" * 46)

    if not do_publish:
        # 미리보기에서도 열쇠는 확인합니다. 문구만 보여주고 끝내면
        # 정작 올릴 때 토큰이 틀린 걸 알게 됩니다 — 그때는 이미 늦습니다.
        try:
            access_token()
            print("\n[유튜브] 열쇠 확인됨 — 접근 토큰을 정상적으로 받았습니다.")
        except SystemExit as ex:
            print(f"\n[유튜브] 열쇠 확인 실패\n{ex}")
            raise
        print("미리보기입니다. 실제로 올리려면 --publish 를 붙이세요.")
        return None

    tok = access_token()
    size = vid.stat().st_size
    req = urllib.request.Request(
        UPLOAD_URL, data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {tok}",
                 "Content-Type": "application/json; charset=UTF-8",
                 "X-Upload-Content-Length": str(size),
                 "X-Upload-Content-Type": "video/mp4"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            session = r.headers["Location"]
    except urllib.error.HTTPError as ex:
        raise SystemExit(f"자리 예약 실패 {ex.code} — "
                         f"{ex.read().decode('utf-8','replace')[:400]}")

    put = urllib.request.Request(
        session, data=vid.read_bytes(), method="PUT",
        headers={"Authorization": f"Bearer {tok}",
                 "Content-Type": "video/mp4", "Content-Length": str(size)})
    try:
        res = json.loads(urllib.request.urlopen(put, timeout=600).read())
    except urllib.error.HTTPError as ex:
        raise SystemExit(f"업로드 실패 {ex.code} — "
                         f"{ex.read().decode('utf-8','replace')[:400]}")

    vid_id = res["id"]
    print(f"[유튜브] 올렸습니다 — https://youtube.com/watch?v={vid_id}")
    if privacy == "private":
        print("        비공개입니다. 스튜디오에서 공개로 바꾸거나,")
        print("        앱 검수가 끝나면 privacy 를 public 으로 두세요.")
    return vid_id


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("--privacy", default="private",
                    choices=["private", "unlisted", "public"])
    ap.add_argument("--publish", action="store_true", help="실제로 올립니다")
    a = ap.parse_args(argv[1:])
    upload(a.base, a.privacy, a.publish)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
