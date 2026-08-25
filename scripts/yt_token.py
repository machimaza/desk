#!/usr/bin/env python3
"""유튜브 갱신 토큰을 받습니다 — 마치마자님 컴퓨터에서 한 번만.

이 파일은 러너에서 돌지 않습니다. **본인 컴퓨터에서** 돌리세요.
클라이언트 시크릿을 물어보는데, 그 값은 이 컴퓨터 밖으로 나가지 않습니다
(구글에게만 보냅니다). 저에게 보내지 마세요.

  python scripts/yt_token.py

브라우저가 열리면 마치마자님 유튜브 계정으로 동의하고,
주소창에 뜬 code= 뒤의 값을 여기 붙여넣으면 됩니다.
"""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/youtube.upload"
REDIRECT = "http://localhost"


def main():
    print(__doc__)
    cid = input("클라이언트 ID: ").strip()
    sec = input("클라이언트 시크릿: ").strip()
    if not cid or not sec:
        raise SystemExit("두 값이 다 있어야 합니다.")

    # access_type=offline 이어야 갱신 토큰이 나옵니다.
    # prompt=consent 를 빼면 두 번째부터는 갱신 토큰이 안 옵니다 — 자주 겪는 함정입니다.
    url = AUTH + "?" + urllib.parse.urlencode({
        "client_id": cid, "redirect_uri": REDIRECT, "response_type": "code",
        "scope": SCOPE, "access_type": "offline", "prompt": "consent"})
    print("\n브라우저에서 아래 주소를 여세요:\n")
    print(url)
    try:
        webbrowser.open(url)
    except Exception:
        pass

    print("\n동의하면 연결할 수 없는 페이지로 넘어갑니다. 정상입니다.")
    print("그 페이지 주소창에서 code= 뒤부터 & 앞까지를 복사해 붙여넣으세요.\n")
    code = input("code: ").strip()
    if "code=" in code:                       # 주소를 통째로 붙여도 받아줍니다
        code = code.split("code=", 1)[1].split("&", 1)[0]
    code = urllib.parse.unquote(code)

    data = urllib.parse.urlencode({
        "code": code, "client_id": cid, "client_secret": sec,
        "redirect_uri": REDIRECT, "grant_type": "authorization_code"}).encode()
    try:
        r = json.loads(urllib.request.urlopen(
            urllib.request.Request(TOKEN, data=data), timeout=60).read())
    except urllib.error.HTTPError as ex:
        raise SystemExit("교환 실패 — " + ex.read().decode("utf-8", "replace")[:400])

    ref = r.get("refresh_token")
    if not ref:
        raise SystemExit(
            "갱신 토큰이 안 왔습니다.\n"
            "  이미 동의한 적이 있으면 안 옵니다. 아래에서 접근 권한을 지우고 다시 하세요.\n"
            "  https://myaccount.google.com/permissions")

    print("\n" + "─" * 46)
    print("YT_REFRESH_TOKEN 에 넣을 값:")
    print(ref)
    print("─" * 46)
    print("\n이 값과 클라이언트 ID·시크릿을 저장소 Secrets 에 넣으세요.")
    print("https://github.com/machimaza/desk/settings/secrets/actions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
