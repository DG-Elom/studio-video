# python3 assemble.py <démo> <nom> : images du screencast (frames/ + marks.json) + voix off (voix/<séq>.wav)
# -> une séquence par passage, calée sur la voix, bandeau de titre, sous-titres incrustés + piste mov_text + .srt.
# Sans voix/<séq>.wav (répétition à blanc) : piste muette, sous-titres répartis sur la séquence.
import json, re, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tuto import config, SEQ_RE

ROOT = Path(sys.argv[1]).resolve()
NOM = sys.argv[2]  # nom du fichier final, sans extension
OUT = ROOT / "montage"; OUT.mkdir(exist_ok=True)
DEST = Path(config(ROOT.parent).get("dest", "~/Movies/tutoriels")).expanduser(); DEST.mkdir(parents=True, exist_ok=True)
FPS = 30
FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_ST = "/System/Library/Fonts/Supplemental/Arial.ttf"


def sh(*a):
    subprocess.run(a, check=True)


def dur(f):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)]))


def banner(text, path):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    if text:
        d = ImageDraw.Draw(im); f = ImageFont.truetype(FONT, 40)
        w = d.textlength(text, font=f)
        d.rounded_rectangle((48, 44, 48 + w + 44, 44 + 72), radius=16, fill=(29, 78, 216, 235))
        d.text((70, 58), text, font=f, fill="white")
    im.save(path); return path


def soustitre(text, path, width=1500, haut=False):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT_ST, 36)
    lines, cur = [], ""
    for w in text.split():
        nxt = (cur + " " + w).strip()
        if d.textlength(nxt, font=f) > width and cur:
            lines.append(cur); cur = w
        else:
            cur = nxt
    lines.append(cur)
    lh = 48; h = lh * len(lines) + 24; y0 = 40 if haut else 1080 - 60 - h
    wmax = max(d.textlength(l, font=f) for l in lines)
    d.rounded_rectangle(((1920 - wmax) / 2 - 24, y0, (1920 + wmax) / 2 + 24, y0 + h), radius=12, fill=(0, 0, 0, 175))
    for i, l in enumerate(lines):
        d.text(((1920 - d.textlength(l, font=f)) / 2, y0 + 12 + i * lh), l, font=f, fill="white")
    im.save(path); return path


def srt_time(t):
    h, t = divmod(t, 3600); m, s = divmod(t, 60)
    return f"{int(h):02}:{int(m):02}:{int(s):02},{int((s % 1) * 1000):03}"


def main():
    marks = json.loads((ROOT / "marks.json").read_text())
    frames = sorted((ROOT / "frames").glob("*.jpg"), key=lambda f: float(f.stem))
    stamps = [float(f.stem) for f in frames]
    txt = re.sub(r"\{\d+\}", "", (ROOT / "narration.txt").read_text())
    narr = dict(re.findall(SEQ_RE, txt, re.S))
    TITRES = {k: v.strip() for k, v in re.findall(r"## (\S+) \| ([^\n]*)", txt)}
    HAUT = set(re.findall(r"## (\S+) \^", txt))  # « ## id ^ » : sous-titres en haut (résultat affiché en bas)
    parts, subs, clock = [], [], 0.0
    for a, b in zip(marks, marks[1:]):
        sid = a["id"]
        sel = [(f, t) for f, t in zip(frames, stamps) if a["t"] <= t < b["t"]] or \
              [max(zip(frames, stamps), key=lambda x: x[1] if x[1] < a["t"] else -1)]
        lst = OUT / f"{sid}.txt"
        with lst.open("w") as fh:
            for (f, t), nxt in zip(sel, [t for _, t in sel[1:]] + [b["t"]]):
                fh.write(f"file '{f}'\nduration {max(nxt - t, 1 / FPS):.4f}\n")
            fh.write(f"file '{sel[-1][0]}'\n")
        vdur = b["t"] - a["t"]
        wav = ROOT / "voix" / f"{sid}.wav"
        muet = not wav.exists()
        adur = max(vdur - 0.8, 1.0) if muet else dur(wav)
        total = max(vdur, adur + 0.8)
        audio = ["-f", "lavfi", "-t", f"{total:.2f}", "-i", "anullsrc=r=48000:cl=mono"] if muet else ["-i", str(wav)]
        phrases = [p.strip() for p in re.split(r"(?<=[.!?:])\s+", narr[sid].strip()) if p.strip()]
        n = sum(len(p) for p in phrases); t0 = 0.4
        ovl = [(banner(TITRES.get(sid, ""), OUT / f"{sid}_titre.png"), 0.0, 4.0)]
        for i, ph in enumerate(phrases):
            d = adur * len(ph) / n
            ovl.append((soustitre(ph, OUT / f"{sid}_st{i}.png", haut=sid in HAUT), t0, t0 + d))
            subs.append((clock + t0, clock + t0 + d, ph)); t0 += d
        base = (f"[0:v]fps={FPS},scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x0b1640,"
                f"tpad=stop_mode=clone:stop_duration={total - vdur + 0.1:.2f},trim=duration={total:.2f},setpts=PTS-STARTPTS[v0]")
        chain, ins = [base], []
        for k, (png, s, e) in enumerate(ovl):
            ins += ["-i", str(png)]
            chain.append(f"[v{k}][{k + 2}:v]overlay=0:0:enable='between(t,{s:.2f},{e:.2f})'[v{k + 1}]")
        chain.append(f"[1:a]adelay=400|400,apad,atrim=duration={total:.2f}[a]")
        out = OUT / f"{sid}.mp4"
        sh("ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), *audio, *ins,
           "-filter_complex", ";".join(chain), "-map", f"[v{len(ovl)}]", "-map", "[a]",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", str(out))
        parts.append(out); clock += dur(out)
    (OUT / "liste.txt").write_text("".join(f"file '{p}'\n" for p in parts))
    with (OUT / "tuto.srt").open("w") as fh:
        for i, (s, e, p) in enumerate(subs, 1):
            fh.write(f"{i}\n{srt_time(s)} --> {srt_time(e)}\n{p}\n\n")
    final = DEST / f"{NOM}.mp4"
    sh("ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(OUT / "liste.txt"), "-i", str(OUT / "tuto.srt"),
       "-map", "0", "-map", "1", "-c", "copy", "-c:s", "mov_text", "-metadata:s:s:0", "language=fre", "-movflags", "+faststart", str(final))
    (DEST / f"{NOM}.srt").write_text((OUT / "tuto.srt").read_text())
    print("OK", final, round(dur(final), 1), "s")


if __name__ == "__main__":
    main()
