#!/usr/bin/env python3
"""tts.py 회귀 테스트 — 빈 시크릿이 조용히 통과하지 못하게.

러너는 없는 시크릿을 빈 문자열로 넘깁니다. 그걸 그대로 주소에 끼우면
"https://.tts.speech.microsoft.com" 이 되고, 오류 메시지가 idna 어쩌고로
나와서 원인이 시크릿이라는 걸 알아채기 어렵습니다. 실제로 한 번 겪었습니다.
"""
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import tts

FAIL = []


def check(name, cond):
    print(f"  {'✓' if cond else '✗'} {name}")
    if not cond:
        FAIL.append(name)


def with_env(**kw):
    old = {k: os.environ.get(k) for k in kw}
    for k, v in kw.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    return old


print("지역 기본값")
with_env(AZURE_SPEECH_KEY="k", AZURE_SPEECH_REGION="")
check("빈 문자열이면 koreacentral", tts._azure_conf()[1] == "koreacentral")
with_env(AZURE_SPEECH_REGION=None)
check("아예 없어도 koreacentral", tts._azure_conf()[1] == "koreacentral")
with_env(AZURE_SPEECH_REGION="  eastus  ")
check("앞뒤 공백은 잘라냄", tts._azure_conf()[1] == "eastus")

print("\n키 없음")
with_env(AZURE_SPEECH_KEY="")
try:
    tts._azure_conf()
    check("키가 비면 멈춤", False)
except SystemExit as ex:
    check("키가 비면 멈춤", "AZURE_SPEECH_KEY" in str(ex))

print("\nSSML")
with_env(AZURE_SPEECH_KEY="k", AZURE_SPEECH_REGION="koreacentral")
s = tts._ssml("가 & 나 <다>", "ko-KR-SeoHyeonNeural", "+0%", "-15Hz")
check("특수문자 이스케이프", "&amp;" in s and "&lt;다&gt;" in s)
check("언어 태그", "xml:lang='ko-KR'" in s)
check("음성 이름", "ko-KR-SeoHyeonNeural" in s)
check("빠르기·높낮이", "rate='+0%'" in s and "pitch='-15Hz'" in s)

print("\n엔진 이름")
try:
    tts.say("가", "v", "/tmp/x.mp3", engine="없는엔진")
    check("모르는 엔진은 거부", False)
except ValueError:
    check("모르는 엔진은 거부", True)

print()
if FAIL:
    print(f"🔴 {len(FAIL)}건 실패: {', '.join(FAIL)}")
    sys.exit(1)
print("🟢 tts 회귀 테스트 전부 통과")
