#!/usr/bin/env python3
"""배경음을 직접 만듭니다 — 저작권이 없는 소리를 쓰기 위해서.

왜 만들어 쓰나
  수익화하는 영상에 남의 음원을 얹으면 나중에 되돌릴 수 없는 문제가 됩니다.
  무료 음원도 출처 표기 의무나 상업적 이용 제한이 붙는 경우가 흔합니다.
  직접 만든 소리는 그런 조건이 아예 없습니다.

무엇을 만드나
  멜로디가 아니라 '바닥'입니다. 정보를 듣는 데 방해가 되면 안 되므로
  음이 적고, 변화가 느리고, 소리가 작습니다.
  대사가 있는 구간에서는 더 작아집니다(더킹) — 그건 mix() 가 합니다.

  pad     느린 화음. 가장 얌전합니다
  pulse   pad + 2초마다 옅은 저음 맥박. 진행감이 생깁니다
  pluck   pad + 마림바풍 아르페지오. 가장 밝습니다

시작과 끝에는 "띠링" 알림음이 붙습니다. 두 가지 일을 합니다 —
시작음은 "이제 말이 시작된다"를 알리고, 끝음은 "끝났다"를 알려
다음 영상으로 넘어갈 지점을 손가락에게 알려줍니다.

사용:
  python scripts/bgm.py 42.5 out.wav --style pad
"""
import argparse
import math
import pathlib
import subprocess
import sys
import tempfile
import wave

SR = 44100

# 음이름 → 주파수. 필요한 것만 적었습니다.
N = {"A2": 110.00, "C3": 130.81, "D3": 146.83, "E3": 164.81, "F3": 174.61,
     "G3": 196.00, "A3": 220.00, "B3": 246.94, "C4": 261.63, "D4": 293.66,
     "E4": 329.63, "F4": 349.23, "G4": 392.00, "A4": 440.00, "C5": 523.25,
     "D5": 587.33, "E5": 659.25, "G5": 783.99, "A5": 880.00}

# 화음 넷이 돌아갑니다. 단조로 시작해 밝은 쪽으로 풀립니다 —
# "문제 → 해결"이라는 영상 흐름과 결이 같습니다.
CHORDS = [["A2", "C4", "E4"],   # Am  막막함
          ["F3", "A3", "C4"],   # F   누그러짐
          ["C3", "E4", "G4"],   # C   정리됨
          ["G3", "B3", "D4"]]   # G   다음으로

ARP = ["A4", "C5", "E5", "G4", "A4", "D5", "C5", "G4"]  # 5음 음계 — 어긋난 음이 없습니다

CHORD_SEC = 8.0     # 화음 하나가 머무는 시간
PULSE_SEC = 2.0


def env(i, n, attack, release):
    """소리가 갑자기 켜지고 꺼지면 '툭' 소리가 납니다. 앞뒤를 눕힙니다."""
    a, r = int(n * attack), int(n * release)
    if i < a:
        return i / a
    if i > n - r:
        return (n - i) / r
    return 1.0


def pad(total):
    """느린 화음. 살짝 어긋난 두 사인을 겹쳐 두께를 만듭니다."""
    n = int(total * SR)
    buf = [0.0] * n
    for ci in range(int(total / CHORD_SEC) + 1):
        chord = CHORDS[ci % len(CHORDS)]
        st = int(ci * CHORD_SEC * SR)
        ln = min(int(CHORD_SEC * SR), n - st)
        if ln <= 0:
            break
        for note in chord:
            f = N[note]
            for d in (0.0, 0.6):            # 0.6Hz 어긋냄 — 천천히 흔들립니다
                w = 2 * math.pi * (f + d) / SR
                for i in range(ln):
                    buf[st + i] += math.sin(w * (st + i)) * env(i, ln, 0.35, 0.35) * 0.05
    return buf


def pulse(total):
    n = int(total * SR)
    buf = [0.0] * n
    ln = int(0.35 * SR)
    for k in range(int(total / PULSE_SEC) + 1):
        st = int(k * PULSE_SEC * SR)
        if st + ln > n:
            break
        w = 2 * math.pi * 62 / SR
        for i in range(ln):
            buf[st + i] += math.sin(w * i) * math.exp(-i / (0.09 * SR)) * 0.22
    return buf


def pluck(total):
    n = int(total * SR)
    buf = [0.0] * n
    step = 0.5
    ln = int(0.45 * SR)
    for k in range(int(total / step) + 1):
        st = int(k * step * SR)
        if st + ln > n:
            break
        f = N[ARP[k % len(ARP)]]
        w = 2 * math.pi * f / SR
        for i in range(ln):
            # 배음을 살짝 섞으면 사인보다 나무 두드리는 소리에 가까워집니다
            s = math.sin(w * i) + 0.3 * math.sin(2 * w * i) + 0.1 * math.sin(3 * w * i)
            buf[st + i] += s * math.exp(-i / (0.08 * SR)) * 0.06
    return buf


def bell(buf, at, freq, dur, vol):
    """종소리 한 번. 배음을 살짝 얹고 빠르게 사그라들게 합니다."""
    st = int(at * SR)
    ln = int(dur * SR)
    if st + ln > len(buf):
        ln = len(buf) - st
    if ln <= 0:
        return
    w = 2 * math.pi * freq / SR
    for i in range(ln):
        s = (math.sin(w * i)
             + 0.35 * math.sin(2 * w * i)      # 옥타브 — 맑아집니다
             + 0.12 * math.sin(3.01 * w * i))  # 살짝 어긋난 배음 — 금속 느낌
        # 앞 2ms 를 눕혀 "툭" 소리를 막습니다
        a = min(1.0, i / (0.002 * SR))
        buf[st + i] += s * a * math.exp(-i / (dur * 0.28 * SR)) * vol


def chime(buf, at, kind="start", vol=0.30):
    """띠-링. 두 음이 이어집니다.

    시작은 올라가고(주의를 끕니다), 끝은 내려갑니다(닫힙니다).
    두 번째 음을 더 길게 울려야 "링~" 하고 남습니다.
    """
    lo, hi = N["E5"], N["A5"]
    if kind == "start":
        bell(buf, at, lo, 0.5, vol)
        bell(buf, at + 0.16, hi, 1.5, vol)
    else:
        bell(buf, at, hi, 0.5, vol * 0.85)
        bell(buf, at + 0.16, lo, 1.8, vol * 0.85)


def write_wav(buf, path):
    peak = max(1e-9, max(abs(x) for x in buf))
    scale = min(1.0, 0.9 / peak)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(b"".join(
            int(max(-1.0, min(1.0, x * scale)) * 32767).to_bytes(2, "little", signed=True)
            for x in buf))


def make_chimes(total, out):
    """알림음만 따로 만듭니다.

    배경음에 섞어버리면 더킹에 같이 눌립니다. 시작음은 첫 대사와 겹치는데,
    눌리면 들리지 않습니다. 알림음은 눌리면 안 되므로 별도 트랙으로 둡니다.
    """
    buf = [0.0] * int(total * SR)
    chime(buf, 0.05, "start")
    chime(buf, max(0.0, total - 2.2), "end")
    tmp = pathlib.Path(tempfile.mkdtemp()) / "chime.wav"
    write_wav(buf, tmp)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp),
                    "-af", "highpass=f=200,volume=0.45", str(out)], check=True)
    return out


def make(total, out, style="pad", chimes=True):
    buf = pad(total)
    if style == "pulse":
        for i, v in enumerate(pulse(total)):
            buf[i] += v
    elif style == "pluck":
        for i, v in enumerate(pluck(total)):
            buf[i] += v
    elif style != "pad":
        raise ValueError(f"모르는 스타일: {style}")

    tmp = pathlib.Path(tempfile.mkdtemp()) / "raw.wav"
    write_wav(buf, tmp)
    # 저음의 웅웅거림과 고음의 쨍함을 깎습니다. 말소리 대역을 비워둡니다.
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp),
                    "-af", "highpass=f=70,lowpass=f=4500,volume=0.5",
                    str(out)], check=True)
    return out


def place_chimes(src, total, out, end_db=-5.0, tail=2.4, chime_db=-2.0):
    """고른 알림음을 시작과 끝에 놓습니다.

    직접 합성하지 않고 파일을 그대로 씁니다 — 귀에 맞는 소리는 사람이 고르는 게 낫습니다.
    끝음은 조금 작게 둡니다. 시작은 부르는 소리, 끝은 닫는 소리라 무게가 다릅니다.
    """
    end_at = max(0.0, total - tail)
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-i", str(src),
        "-filter_complex",
        f"[0:a]volume={chime_db}dB,adelay=0|0[a0];"
        f"[1:a]volume={chime_db + end_db}dB,"
        f"adelay={int(end_at*1000)}|{int(end_at*1000)}[a1];"
        f"[a0][a1]amix=inputs=2:duration=longest:normalize=0,"
        f"apad,atrim=0:{total:.2f}[a]",
        "-map", "[a]", "-c:a", "libmp3lame", "-q:a", "4", str(out)], check=True)
    return out


# 어떤 곡을 골라오든 같은 크기로 맞춥니다.
# 받아온 파일마다 녹음 크기가 제각각이라(-12dB 짜리도 있고 -30dB 짜리도 있습니다)
# 그대로 쓰면 곡을 바꿀 때마다 다시 귀로 맞춰야 합니다.
BED_LUFS = -31


def prepare(src, total, out, fade_in=0.6, fade_out=1.8):
    """골라온 음원을 영상 길이에 맞춥니다.

    짧으면 이어붙이고, 길면 자릅니다. 앞뒤는 눕힙니다 —
    갑자기 시작하거나 뚝 끊기면 그것만 귀에 걸립니다.
    크기도 여기서 한 번 고르게 맞춥니다.
    """
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-stream_loop", "-1", "-i", str(src), "-t", f"{total:.2f}",
        "-af", f"loudnorm=I={BED_LUFS}:TP=-3:LRA=11,"
               f"afade=t=in:st=0:d={fade_in},"
               f"afade=t=out:st={max(0.0, total - fade_out):.2f}:d={fade_out}",
        "-ac", "1", "-c:a", "libmp3lame", "-q:a", "4", str(out)], check=True)
    return out


def mix(voice, bed, out, chimes=None, bed_db=3):
    """대사 아래에 배경음을 깝니다. 말할 때는 배경음이 알아서 물러납니다.

    sidechaincompress 가 그 일을 합니다 — 대사를 감지해서 배경음을 눌러줍니다.
    그냥 겹치면 대사가 묻히고, 배경음만 낮추면 빈 구간이 다시 조용해집니다.

    알림음은 더킹을 거치지 않고 그대로 얹습니다. 눌리면 들리지 않으니까요.
    """
    ins = ["-i", str(voice), "-i", str(bed)]
    f = (f"[1:a]volume={bed_db}dB[b];"
         "[b][0:a]sidechaincompress=threshold=0.02:ratio=6:attack=8:release=400[duck];")
    if chimes:
        ins += ["-i", str(chimes)]
        f += "[0:a][duck][2:a]amix=inputs=3:duration=first:normalize=0[a]"
    else:
        f += "[0:a][duck]amix=inputs=2:duration=first:normalize=0[a]"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *ins,
                    "-filter_complex", f, "-map", "[a]",
                    "-c:a", "libmp3lame", "-q:a", "4", str(out)], check=True)
    return out


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("seconds", type=float)
    ap.add_argument("out")
    ap.add_argument("--style", default="pad", choices=["pad", "pulse", "pluck"])
    ap.add_argument("--no-chime", action="store_true", help="시작·끝 알림음 빼기")
    a = ap.parse_args(argv[1:])
    make(a.seconds, a.out, a.style)
    if not a.no_chime:
        make_chimes(a.seconds, str(pathlib.Path(a.out).with_suffix("")) + "-chime.mp3")
    print(f"[bgm] {a.out} · {a.seconds:.1f}초 · {a.style}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
