# python3 tts.py <démo> [séquences] : voix off ElevenLabs horodatée de narration.txt.
# Clé lue dans le trousseau macOS (jamais affichée). cues.json = instant (s) où chaque repère {n} est prononcé.
# Sans séquence : tout est régénéré ; avec séquences : seules celles-ci, cues.json complété.
import base64, json, re, subprocess, sys, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tuto import config, SEQ_RE

root = Path(sys.argv[1]).resolve(); cfg = config(root.parent)
KEY = subprocess.check_output(["security", "find-generic-password", "-s", cfg.get("keychain_service", "elevenlabs-api-key"), "-w"]).decode().strip()
VOICE = cfg.get("voice_id", "JBFqnCBsd6RMkjVDRZzb")  # George, multilingue
out = root / "voix"; out.mkdir(exist_ok=True)
ONLY = sys.argv[2:]
cues = json.loads((root / "cues.json").read_text()) if ONLY else {}
for sid, body in re.findall(SEQ_RE, (root / "narration.txt").read_text(), re.S):
    if ONLY and sid not in ONLY: continue
    text, marks = "", {}
    for part in re.split(r"(\{\d+\})", body.strip()):
        if re.fullmatch(r"\{\d+\}", part): marks[part[1:-1]] = len(text)
        else: text += part
    r = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}/with-timestamps?output_format=mp3_44100_128",
        data=json.dumps({"text": text, "model_id": cfg.get("tts_model", "eleven_multilingual_v2"),
                         "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "style": 0.2, "use_speaker_boost": True}}).encode(),
        headers={"xi-api-key": KEY, "Content-Type": "application/json"})
    d = json.loads(urllib.request.urlopen(r, timeout=180).read())
    (out / f"{sid}.mp3").write_bytes(base64.b64decode(d["audio_base64"]))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(out / f"{sid}.mp3"), "-ar", "48000", "-ac", "1", str(out / f"{sid}.wav")], check=True)
    starts = d["alignment"]["character_start_times_seconds"]
    cues[sid] = {k: round(starts[min(i, len(starts) - 1)], 3) for k, i in marks.items()}
    cues[sid]["_fin"] = round(d["alignment"]["character_end_times_seconds"][-1], 3)
    print(sid, cues[sid], flush=True)
(root / "cues.json").write_text(json.dumps(cues, indent=1))
