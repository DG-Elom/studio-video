# python3 controle.py <démo> <vidéo.mp4> : planche d'une image de la vidéo finale à chaque repère vocal (+0,6 s),
# à relire AVANT de livrer (l'action nommée par la voix doit être visible). Sortie : <démo>/planche.jpg.
import json, subprocess, sys, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tuto import fake_cues
d, f = Path(sys.argv[1]).resolve(), sys.argv[2]
cues = json.loads((d / "cues.json").read_text()) if (d / "cues.json").exists() else fake_cues(d)
marks = json.loads((d / "marks.json").read_text())
dur = lambda p: float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]))
clock, shots = 0.0, []
for m in marks[:-1]:
    ks = [k for k in cues[m["id"]] if k != "_fin"] or ["_fin"]
    shots += [(f"{m['id']}-{k}", clock + 0.4 + (cues[m['id']][k] if k != "_fin" else 1) + 0.6) for k in ks]
    clock += dur(d / "montage" / f"{m['id']}.mp4")
out = d / "controle"; shutil.rmtree(out, ignore_errors=True); out.mkdir()
for i, (name, t) in enumerate(shots):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", f, "-frames:v", "1", "-vf", "scale=640:-1", str(out / f"{i:02}-{name}.jpg")], check=True)
cols = 5; rows = -(-len(shots) // cols)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-pattern_type", "glob", "-i", str(out / "*.jpg"), "-vf", f"tile={cols}x{rows}", "-frames:v", "1", str(d / "planche.jpg")], check=True)
print(len(shots), "images ->", d / "planche.jpg")
