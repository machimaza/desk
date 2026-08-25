#!/usr/bin/env python3
"""후보 목소리로 같은 대사를 읽어 샘플을 만듭니다.

이 컨테이너에서는 TTS 가 프록시에 막혀 있어 GitHub Actions 러너에서 돌립니다.
narrate.yml 은 이 파일을 한 줄로 부르기만 합니다 — 반복문을 YAML 안에 두면
따옴표와 줄바꿈 때문에 CI 가 두 번이나 깨졌습니다. 로직은 여기 둡니다.

한국어 전용 음성은 세 개뿐입니다. 그래서 두 갈래를 더 봅니다.
  · 변형  — 같은 목소리의 빠르기·높낮이를 바꾼 것. 실제로 쓰는 손잡이입니다.
  · 다국어 — 다른 나라 음성 중 한국어를 읽을 수 있는 것. 억양이 살짝 다릅니다.

낱개 파일을 스무 개 넘게 듣는 건 고역이라, 번호를 말해주는 합본도 함께 만듭니다.

  python scripts/voice_samples.py --mode all
"""
import argparse
import pathlib
import subprocess
import sys

LINE = "퇴직하면 건강보험료 얼마 나오는지, 기한 안에 알려드립니다. 마치마자입니다."

# 한국어 전용 음성 — 목록 조회가 실패해도 이건 있습니다.
KO = ["ko-KR-SunHiNeural", "ko-KR-InJoonNeural", "ko-KR-HyunsuMultilingualNeural",
      "ko-KR-SeoHyeonNeural", "ko-KR-YuJinNeural", "ko-KR-JiMinNeural",
      "ko-KR-SoonBokNeural", "ko-KR-BongJinNeural", "ko-KR-GookMinNeural",
      "ko-KR-HyunsuNeural"]
# 뒤의 일곱은 azure 에서만 나옵니다. edge 로 돌리면 목록에 없어서 저절로 빠집니다.

# 변형 — 빠르기와 높낮이. 원본(+0%/+0Hz)은 기본 묶음에 이미 있으니 뺍니다.
VARIANTS = [("+12%", "+0Hz", "조금 빠르게"),
            ("+0%", "-15Hz", "조금 낮게")]

MULTI_CAP = 12  # 합본이 너무 길어지지 않게. 잘린 개수는 아래에서 알립니다.


ENGINE = "edge"  # main() 에서 정해집니다


def all_voices():
    import tts
    return {n for n, _, _ in tts.voices(ENGINE, "")} if ENGINE == "edge" else \
           {n for n, _, _ in tts.voices(ENGINE, "ko-")}


def say(text, voice, out, rate="+0%", pitch="+0Hz"):
    import tts
    tts.say(text, voice, out, rate, pitch, ENGINE)


def silence(path, seconds=0.7):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                    "-i", "anullsrc=r=24000:cl=mono", "-t", f"{seconds}",
                    "-c:a", "libmp3lame", "-q:a", "5", str(path)], check=True)


def concat(parts, out):
    # 목록 파일은 조각들과 같은 폴더에 둡니다.
    # ffmpeg 은 목록 안의 상대 경로를 "목록 파일이 있는 곳" 기준으로 찾습니다.
    # 다른 폴더에 두면 조각을 못 찾고 "No such file or directory" 로 죽습니다.
    lst = parts[0].parent / (out.stem + ".txt")
    lst.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat",
                    "-safe", "0", "-i", str(lst), "-c", "copy", str(out)], check=True)
    lst.unlink()


def build(out, want):
    out.mkdir(parents=True, exist_ok=True)
    tmp = out / "_tmp"
    tmp.mkdir(exist_ok=True)

    try:
        avail = all_voices()
    except Exception as ex:
        print(f"[경고] 음성 목록 조회 실패 ({ex}) — 한국어 전용만 만듭니다")
        avail = set(KO)

    # 후보 모으기 ------------------------------------------------------
    korean, multi = [], []
    for v in KO:
        if v in avail:
            korean.append((v, "+0%", "+0Hz", "원본"))
    for v, _, _, _ in list(korean):
        for rate, pitch, label in VARIANTS:
            korean.append((v, rate, pitch, label))

    found = sorted(n for n in avail
                   if n.endswith("MultilingualNeural") and not n.startswith("ko-"))
    if len(found) > MULTI_CAP:
        print(f"[알림] 다국어 음성 {len(found)}개 중 {MULTI_CAP}개만 만듭니다 "
              f"— 뺀 것: {', '.join(found[MULTI_CAP:])}")
        found = found[:MULTI_CAP]
    multi = [(v, "+0%", "+0Hz", "다국어") for v in found]

    groups = []
    if want in ("all", "korean"):
        groups.append(("A-한국어", korean))
    if want in ("all", "multilingual"):
        groups.append(("B-다국어", multi))

    # 만들기 -----------------------------------------------------------
    index = []
    for gname, items in groups:
        if not items:
            continue
        parts = []
        for i, (v, rate, pitch, label) in enumerate(items, 1):
            short = v.replace("Neural", "").replace("Multilingual", "")
            tag = f"{short}_{rate}_{pitch}".replace("%", "").replace("+", "")
            f = out / f"{gname}_{i:02d}_{tag}.mp3"
            print(f"  {gname} {i:>2}. {v} {rate} {pitch} — {label}")
            say(LINE, v, f, rate, pitch)

            # 번호를 말해주는 안내 — 합본을 눈 감고 들을 수 있게
            num = tmp / f"n_{gname}_{i:02d}.mp3"
            say(f"{i}번.", "ko-KR-SunHiNeural", num)
            gap = tmp / f"g_{gname}_{i:02d}.mp3"
            silence(gap)
            for p in (num, f, gap):
                q = tmp / f"{len(parts):03d}_{p.name}"
                q.write_bytes(p.read_bytes())
                parts.append(q)
            index.append(f"{gname} {i:>2}번  {v}  빠르기 {rate}  높낮이 {pitch}  ({label})")

        merged = out / f"{gname}-합본.mp3"
        concat(parts, merged)
        print(f"[합본] {merged.name}")

    (out / "목록.txt").write_text("\n".join(index) + "\n", encoding="utf-8")
    for p in tmp.iterdir():
        p.unlink()
    tmp.rmdir()
    print(f"[완료] {len(index)}종")


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="all",
                    choices=["all", "korean", "multilingual"])
    ap.add_argument("--out", default="samples")
    ap.add_argument("--engine", default="edge", choices=["edge", "azure"])
    a = ap.parse_args(argv[1:])
    global ENGINE
    ENGINE = a.engine
    build(pathlib.Path(a.out), a.mode)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
