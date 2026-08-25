#!/usr/bin/env python3
"""음성 합성 창구 — 어느 엔진을 쓰든 부르는 쪽은 같게.

두 갈래가 있습니다.

  edge   무료. 키가 필요 없습니다. 다만 한국어 음성이 세 개뿐입니다.
  azure  Microsoft Azure Speech. 한국어 열 개가 전부 열립니다.
         월 50만 자까지 무료(F0)이고, 우리 분량이면 1%도 안 씁니다.
         키가 필요합니다 — 환경변수로 받습니다.

키를 코드나 워크플로 파일에 적지 않습니다. GitHub Secrets 에 넣고
러너가 환경변수로 넘겨줍니다. 저장소가 공개라 더더욱 그렇습니다.

  AZURE_SPEECH_KEY     구독 키
  AZURE_SPEECH_REGION  지역 (예: koreacentral)
"""
import asyncio
import os
import pathlib
import sys
import urllib.error
import urllib.request
import xml.sax.saxutils as SU

FORMAT = "audio-24khz-48kbitrate-mono-mp3"


def _azure_conf():
    # 러너는 없는 시크릿도 "빈 문자열"로 넘겨줍니다. 키가 아예 없는 것과
    # 빈 값인 것이 파이썬에서는 다르게 동작합니다 —
    #   os.environ.get("X", "기본값")  →  X 가 빈 문자열이면 기본값이 안 나옵니다
    # 그래서 지역이 ""가 된 채로 주소를 만들었고,
    # "https://.tts.speech.microsoft.com" 이 되어 idna 오류로 죽었습니다.
    # get 의 기본값이 아니라 or 로 받아야 합니다.
    key = os.environ.get("AZURE_SPEECH_KEY", "").strip()
    region = os.environ.get("AZURE_SPEECH_REGION", "").strip() or "koreacentral"
    if not key:
        raise SystemExit(
            "AZURE_SPEECH_KEY 가 비어 있습니다.\n"
            "  · 러너에서 도는 중이라면 저장소 Settings → Secrets 에 키를 넣으세요\n"
            "  · 손으로 돌리는 중이라면 AZURE_SPEECH_KEY=... 를 앞에 붙이세요")
    return key, region


def azure_voices(locale="ko-"):
    """그 지역에서 실제로 쓸 수 있는 음성 목록. 문서보다 이게 정확합니다."""
    import json
    key, region = _azure_conf()
    req = urllib.request.Request(
        f"https://{region}.tts.speech.microsoft.com/cognitiveservices/voices/list",
        headers={"Ocp-Apim-Subscription-Key": key})
    vs = json.load(urllib.request.urlopen(req, timeout=60))
    return [v for v in vs if v["Locale"].startswith(locale)]


def _ssml(text, voice, rate, pitch):
    lang = "-".join(voice.split("-")[:2]) or "ko-KR"
    return (f"<speak version='1.0' xml:lang='{lang}'>"
            f"<voice name='{voice}'>"
            f"<prosody rate='{rate}' pitch='{pitch}'>{SU.escape(text)}</prosody>"
            f"</voice></speak>")


def azure_say(text, voice, out, rate="+0%", pitch="+0Hz"):
    key, region = _azure_conf()
    req = urllib.request.Request(
        f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1",
        data=_ssml(text, voice, rate, pitch).encode("utf-8"),
        headers={"Ocp-Apim-Subscription-Key": key,
                 "Content-Type": "application/ssml+xml",
                 "X-Microsoft-OutputFormat": FORMAT,
                 "User-Agent": "machimaza"})
    try:
        audio = urllib.request.urlopen(req, timeout=120).read()
    except urllib.error.HTTPError as ex:
        body = ex.read().decode("utf-8", "replace")[:300]
        # 401 은 키, 403 은 지역이나 한도, 400 은 음성 이름이 대개 원인입니다.
        raise SystemExit(f"Azure 응답 {ex.code} — {body}")
    pathlib.Path(out).write_bytes(audio)


async def edge_say(text, voice, out, rate="+0%", pitch="+0Hz"):
    import edge_tts
    await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(str(out))


def say(text, voice, out, rate="+0%", pitch="+0Hz", engine="edge"):
    """부르는 쪽은 이것만 씁니다. 동기 함수입니다."""
    if engine == "azure":
        azure_say(text, voice, out, rate, pitch)
    elif engine == "edge":
        asyncio.run(edge_say(text, voice, out, rate, pitch))
    else:
        raise ValueError(f"모르는 엔진: {engine}")


def detail(engine="edge", locale="ko-"):
    """이름만이 아니라 딸린 것까지 — 말투(style)와 세대(VoiceType).

    같은 목소리라도 말투가 여러 개면 고를 거리가 그만큼 늘어납니다.
    Azure 는 <mstts:express-as> 로 말투를 바꿉니다. edge 는 이 정보를 안 줍니다.
    """
    if engine != "azure":
        return [{"ShortName": n, "Gender": g, "LocalName": l, "StyleList": []}
                for n, g, l in voices(engine, locale)]
    return azure_voices(locale)


def voices(engine="edge", locale="ko-"):
    if engine == "azure":
        return [(v["ShortName"], v.get("Gender", ""), v.get("LocalName", ""))
                for v in azure_voices(locale)]
    import edge_tts
    vs = asyncio.run(edge_tts.list_voices())
    return [(v["ShortName"], v.get("Gender", ""), v.get("FriendlyName", ""))
            for v in vs if v["Locale"].startswith(locale)]


if __name__ == "__main__":
    eng = sys.argv[1] if len(sys.argv) > 1 else "edge"
    loc = sys.argv[2] if len(sys.argv) > 2 else "ko-"
    for v in sorted(detail(eng, loc), key=lambda x: x["ShortName"]):
        st = ", ".join(v.get("StyleList") or []) or "-"
        print(f"  {v['ShortName']:<38} {v.get('Gender',''):<7} "
              f"{v.get('VoiceType',''):<14} 말투: {st}")
