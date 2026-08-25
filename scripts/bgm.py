#!/usr/bin/env python3
"""고른 배경음·알림음을 영상에 얹습니다.

소리는 만들지 않고 **고른 파일을 씁니다.**
한때 여기서 화음을 합성했지만 버렸습니다 — 귀에 맞는 소리는 사람이 고르는 게 낫고,
합성음은 "만든 티"가 납니다. 저작권이 깨끗한 무료 음원을 고르는 방법은 `BGM.md` 에 있습니다.

파일을 놓는 자리 (`build_voice.py` 가 이 순서로 찾습니다)
  배경음   글폴더/bgm.mp3   → assets/bgm/기본.mp3    → 없으면 배경음 없이
  알림음   글폴더/chime.mp3 → assets/bgm/알림음.mp3  → 없으면 알림음 없이

하는 일 셋
  prepare()      곡을 영상 길이에 맞추고 앞뒤를 눕히고 크기를 고르게 맞춥니다
  place_chimes() 시작과 끝에 알림음을 놓습니다
  mix()          대사 아래에 깝니다. 말하는 동안은 배경음이 물러납니다(더킹)

이 파일은 단독 실행하지 않습니다. `build_voice.py` 가 부릅니다.
"""
import subprocess

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

