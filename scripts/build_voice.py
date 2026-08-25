#!/usr/bin/env python3
"""나레이션 음성 생성 — 장면 시작 시각에 맞춰 배치합니다.

왜 장면별로 나누나
  한 덩어리로 읽어서 얹으면 화면과 말이 어긋납니다.
  장면마다 따로 만들어 그 장면이 시작하는 시각에 놓아야 맞습니다.
  장면 길이는 motion.py 가 이미 알고 있으므로 그대로 가져옵니다.

왜 이 컨테이너에서 안 도나
  edge-tts 는 speech.platform.bing.com 을 사용하는데 프록시가 막습니다.
  GitHub Actions 러너에서는 정상 동작합니다. 그래서 CI 로 돌립니다.

사용:
  python3 scripts/build_voice.py <콘텐츠폴더> --voice ko-KR-InJoonNeural
  python3 scripts/build_voice.py <콘텐츠폴더> --list         음성 목록만
  python3 scripts/build_voice.py <콘텐츠폴더> --dry          TTS 없이 배치만 검증
"""
import sys, json, asyncio, pathlib, subprocess, tempfile, argparse

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def scene_plan(base):
    """[(장면번호, 시작초, 길이초, 대사)] — motion.py 와 같은 계산을 씁니다."""
    import motion
    d = json.loads((base / "data.json").read_text(encoding="utf-8"))
    scenes = motion.build_scenes(d)
    flow = d.get("flow", {}).get("scenes", [])
    out, t = [], 0.0
    for i, (_html, anim, hold) in enumerate(scenes):
        voice = flow[i].get("voice", "") if i < len(flow) else ""
        out.append((i, t, anim + hold, voice.strip()))
        t += anim + hold
    return out, t


async def list_voices():
    import edge_tts
    vs = await edge_tts.list_voices()
    ko = [v for v in vs if v["Locale"].startswith("ko")]
    for v in sorted(ko, key=lambda x: x["ShortName"]):
        print(f"  {v['ShortName']:34} {v.get('Gender',''):7} {v.get('FriendlyName','')}")
    return [v["ShortName"] for v in ko]


async def say(text, voice, out, rate="+0%"):
    import edge_tts
    await edge_tts.Communicate(text, voice, rate=rate).save(str(out))


def assemble(parts, total, out):
    """무음 바닥 위에 각 대사를 시작 시각에 배치합니다."""
    if not parts:
        return False
    ins = ["-f", "lavfi", "-t", f"{total:.2f}", "-i", "anullsrc=r=24000:cl=mono"]
    for _, _, p in parts:
        ins += ["-i", str(p)]
    mix = "".join(f"[{i+1}:a]adelay={int(st*1000)}|{int(st*1000)}[d{i}];"
                  for i, (_, st, _) in enumerate(parts))
    mix += "".join(f"[d{i}]" for i in range(len(parts)))
    mix += f"[0:a]amix=inputs={len(parts)+1}:duration=first:normalize=0[a]"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *ins,
                    "-filter_complex", mix, "-map", "[a]",
                    "-c:a", "libmp3lame", "-q:a", "4", str(out)], check=True)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("--voice", default="ko-KR-InJoonNeural")
    ap.add_argument("--rate", default="+0%")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--dry", action="store_true", help="TTS 없이 무음으로 배치만 검증")
    a = ap.parse_args()
    base = pathlib.Path(a.base)

    if a.list:
        asyncio.run(list_voices())
        return 0

    plan, total = scene_plan(base)
    print(f"[voice] 장면 {len(plan)}개 · 총 {total:.1f}초 · 음성 {a.voice}")
    tmp = pathlib.Path(tempfile.mkdtemp())
    parts = []
    for i, st, dur, txt in plan:
        if not txt:
            continue
        p = tmp / f"s{i:02d}.mp3"
        if a.dry:
            # 대사 길이에 비례한 무음으로 배치만 확인합니다.
            # 글자 수가 아니라 **읽었을 때의 음절 수**로 셉니다
            # (공백·문장부호·숫자 표기를 그대로 세면 과대 추정됩니다).
            import build_narration
            est = max(0.8, build_narration.syllables(txt) / 5.5)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                            "-t", f"{est:.2f}", "-i", "anullsrc=r=24000:cl=mono",
                            "-c:a", "libmp3lame", str(p)], check=True)
        else:
            asyncio.run(say(txt, a.voice, p, a.rate))
        d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                  "format=duration", "-of", "csv=p=0", str(p)],
                                 capture_output=True, text=True).stdout.strip() or 0)
        flag = "  ⚠ 장면보다 길" if d > dur else ""
        print(f"  {i+1:>2}. {st:>5.1f}초  대사 {d:4.1f}초 / 장면 {dur:4.1f}초{flag}")
        parts.append((i, st, p))

    out = base / "narration.mp3"
    if not assemble(parts, total, out):
        print("  대사가 없습니다")
        return 1
    print(f"[voice] {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
