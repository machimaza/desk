"""data.json -> video.mp4 (1080x1920, 60~90초, 카운트다운 구조)

포스터를 그대로 넣지 않습니다. 9:16 전용 씬을 data.json에서 새로 조판합니다.
"""
import sys, pathlib, subprocess, tempfile, html as H
from render import fill, shoot, autosize, load

TARGET = 72          # 목표 길이(초). 60~90 사이
HOOK, OUTRO = 4.0, 6.0
FPS = 30

def esc(s): return H.escape(str(s))

def scenes(d):
    m, items = d["meta"], d["items"]
    rev = list(reversed(items))          # 하위 → 상위 카운트다운
    n = len(rev)
    per = max(3.0, round((TARGET - HOOK - OUTRO) / n, 2))
    dday = m.get("dday", "")
    DD = f'<div class="dday">{esc(dday)}</div>' if dday else ""
    out = [("s000.png", fill("scene.html", {
        "CAT": m["category"], "PG": "", "DDAY": DD,
        "CONTENT": f'<div class="kicker">{esc(m["category"])}</div>'
                   f'<div class="head">{esc(m["title"])}</div>',
        "HF": autosize(m["title"], 120, 1.6, 74),
        "CAPTION": esc(d["hook"])}), HOOK)]
    for i, it in enumerate(rev):
        # 자막은 화면 텍스트와 달라야 정보량이 2배가 됩니다 (화면=사실, 자막=해석)
        cap = it.get("caption") or it["detail"]
        out.append((f"s{i+1:03d}.png", fill("scene.html", {
            "CAT": m["category"], "PG": f'{it.get("rank", n-i)}', "DDAY": DD,
            "CONTENT": f'<div class="head">{esc(it["label"])}</div>'
                       f'<div class="big">{esc(it["value"])}</div>',
            "HF": autosize(it["label"], 104, 2.0, 66), "DF": 40,
            "CAPTION": esc(cap[:60])}), per))
    rows = "".join(f'<tr><td>{esc(it["label"])}</td><td>{esc(it["value"])}</td></tr>'
                   for it in items)
    out.append((f"s{n+1:03d}.png", fill("scene.html", {
        "CAT": m["category"], "PG": "전체", "DDAY": DD,
        "CONTENT": f'<table class="tbl">{rows}</table>',
        "CAPTION": "지금 캡처해두세요. 신청할 때 다시 필요합니다."}), OUTRO))
    return out

def write_srt(sc, path):
    """유튜브 업로드용 자막 파일. 자동 자막보다 정확하고 검색에도 잡힙니다."""
    def ts(s):
        h, r = divmod(s, 3600); mnt, sec = divmod(r, 60)
        return f"{int(h):02d}:{int(mnt):02d}:{sec:06.3f}".replace(".", ",")
    lines, t0 = [], 0.0
    import re as _re
    for i, (_, html, dur) in enumerate(sc):
        mm = _re.search(r'<div class="cap">(.*?)</div>', html, _re.S)
        txt = _re.sub(r"<[^>]+>", "", mm.group(1)).strip() if mm else ""
        if txt:
            lines.append(f"{i+1}\n{ts(t0)} --> {ts(t0+dur)}\n{txt}\n")
        t0 += dur
    path.write_text("\n".join(lines), encoding="utf-8")

def build(base: pathlib.Path):
    d = load(base / "data.json")
    sc = scenes(d)
    tmp = pathlib.Path(tempfile.mkdtemp())
    shoot([(n, h) for n, h, _ in sc], tmp, 1080, 1920)
    clips = []
    for i, (name, _, dur) in enumerate(sc):
        clip = tmp / f"c{i:03d}.mp4"
        frames = int(dur * FPS)
        # 2배 업스케일 후 zoompan → 지터 없는 부드러운 켄번즈
        vf = (f"scale=2160:3840,zoompan=z='min(zoom+0.0007,1.12)'"
              f":d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
              f":s=1080x1920:fps={FPS},format=yuv420p")
        subprocess.run(["ffmpeg","-y","-loglevel","error","-loop","1","-i",str(tmp/name),
                        "-vf",vf,"-t",str(dur),"-c:v","libx264","-preset","medium",
                        "-crf","20","-pix_fmt","yuv420p","-r",str(FPS),str(clip)],check=True)
        clips.append(clip)
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{c}'\n" for c in clips))
    silent = base / "_novideo.mp4"
    subprocess.run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0",
                    "-i",str(lst),"-c","copy",str(silent)],check=True)
    # 오디오 스트림 없는 파일은 쇼츠·틱톡에서 불리하거나 거부됩니다.
    # BGM이 있으면 얹고, 없으면 최소한 무음 트랙이라도 넣습니다.
    out = base / "video.mp4"
    bgm = pathlib.Path(__file__).resolve().parent.parent / "assets" / "bgm.mp3"
    if bgm.exists():
        subprocess.run(["ffmpeg","-y","-loglevel","error","-i",str(silent),
                        "-stream_loop","-1","-i",str(bgm),"-shortest",
                        "-c:v","copy","-c:a","aac","-b:a","128k",
                        "-af","volume=0.18,afade=t=out:st=%.1f:d=2" % (sum(s[2] for s in sc)-2),
                        str(out)],check=True)
        audio_note = f"BGM: {bgm.name}"
    else:
        subprocess.run(["ffmpeg","-y","-loglevel","error","-i",str(silent),
                        "-f","lavfi","-i","anullsrc=r=44100:cl=stereo","-shortest",
                        "-c:v","copy","-c:a","aac","-b:a","64k",str(out)],check=True)
        audio_note = "무음 트랙 (assets/bgm.mp3 넣으면 자동 적용)"
    silent.unlink()
    # 커버(첫 프레임) — 쇼츠 썸네일·인스타 리믹스용
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i",str(out),"-vframes","1",
                    str(base/"cover.png")],check=True)
    write_srt(sc, base/"video.srt")
    dur = float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                                "-of","default=nw=1:nk=1",str(out)],
                               capture_output=True,text=True).stdout.strip())
    print(f"[video] {out}  {dur:.1f}초  씬 {len(sc)}개  |  {audio_note}")
    print(f"[video] 부산물: cover.png (썸네일), video.srt (유튜브 자막)")
    if not 60 <= dur <= 90:
        print(f"  ⚠ 길이 규격 이탈 (60~90초). TARGET 값을 조정하세요.")
    return out

if __name__ == "__main__":
    build(pathlib.Path(sys.argv[1]))
