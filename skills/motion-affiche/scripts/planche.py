#!/usr/bin/env python3
"""Contrôle d'une vidéo rendue : planche d'images, fidélité de la fin, gels, trace des calques.

Usage : python3 planche.py <video.mp4> [--affiche affiche.png] [-n 12] [--mode teaser|affiche]
Écrit <video>-planche.jpg (à REGARDER) et affiche les mesures :
  SSIM dernière image / affiche (zone de l'affiche) comparé au plafond de compression,
  part du temps où l'affiche est déjà reconnaissable, avec les passages (un teaser : ≤ 35 %, à la fin),
  gels > 1,5 s, écrans noirs, plus long plan de même composition avant la tenue finale (un teaser : ≤ 3 s),
  et, si trace.json trace des calques : apparition de chaque calque, écart final à sa place.
"""
import argparse, json, re, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageStat


def sonde(v):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate,nb_frames,pix_fmt,codec_name:format=duration",
                        "-of", "json", str(v)], capture_output=True, text=True, check=True)
    j = json.loads(r.stdout)
    s = j["streams"][0]
    n, d = s["r_frame_rate"].split("/")
    return s["width"], s["height"], float(n) / float(d), float(j["format"]["duration"]), s


def image_a(v, t, f):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(v), "-frames:v", "1", str(f)], check=True)


def filtre(v, lavfi):
    return subprocess.run(["ffmpeg", "-hide_banner", "-i", str(v), "-vf", lavfi, "-f", "null", "-"],
                          capture_output=True, text=True).stderr


def ssim(a, b):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(a), "-i", str(b), "-lavfi", "ssim", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    m = re.search(r"All:([0-9.]+)", r)
    return float(m.group(1)) if m else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--affiche")
    ap.add_argument("-n", type=int, default=12)
    ap.add_argument("--mode", choices=["teaser", "affiche"], default="teaser",
                    help="teaser : l'affiche reconnaissable au plus 35 %% du temps, à la fin")
    o = ap.parse_args()
    v = Path(o.video)
    W, H, fps, D, s = sonde(v)
    print(f"📼 {v.name} : {W}x{H} {fps:.0f} i/s {D:.2f} s {s['codec_name']} {s['pix_fmt']} ({s.get('nb_frames')} images)")
    with tempfile.TemporaryDirectory() as tmp:
        instants = [round(i * D / o.n, 2) for i in range(o.n)] + [round(D - 1.5 / fps, 3)]
        vignettes = []
        for i, t in enumerate(instants):
            f = Path(tmp) / f"{i:03d}.png"
            image_a(v, t, f)
            vignettes.append((t, Image.open(f).convert("RGB")))
        derniere = vignettes[-1][1]
        cols = 5 if W >= H else 7
        tw = 1600 // cols
        th = round(tw * H / W)
        rangs = -(-len(vignettes) // cols)
        pl = Image.new("RGB", (cols * tw, rangs * (th + 22)), "#111")
        d = ImageDraw.Draw(pl)
        for i, (t, im) in enumerate(vignettes):
            x, y = (i % cols) * tw, (i // cols) * (th + 22)
            pl.paste(im.resize((tw - 4, th)), (x + 2, y + 20))
            d.text((x + 6, y + 4), f"{t:.2f} s" + (" (fin)" if i == len(vignettes) - 1 else ""), fill="#ffea00")
        sortie = v.with_name(v.stem + "-planche.jpg")
        pl.save(sortie, quality=85)
        print(f"🖼️  {sortie}")

        if o.affiche:
            a = Image.open(o.affiche).convert("RGB")
            k = min(W / a.width, H / a.height)
            zw, zh = round(a.width * k), round(a.height * k)
            zx, zy = (W - zw) // 2, (H - zh) // 2
            fa, fb = Path(tmp) / "a.png", Path(tmp) / "b.png"
            a.resize((zw, zh), Image.LANCZOS).save(fa)
            derniere.crop((zx, zy, zx + zw, zy + zh)).save(fb)
            ss = ssim(fb, fa)
            # Référence : l'affiche elle-même passée par le même encodage (une affiche granuleuse
            # perd déjà plusieurs points en H.264 4:2:0 ; c'est le plafond atteignable).
            fv, fr = Path(tmp) / "ref.mp4", Path(tmp) / "ref.png"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(fa), "-c:v", "libx264", "-preset", "slow", "-crf", "18",
                            "-pix_fmt", "yuv420p", "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", str(fv)], check=True)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(fv), "-frames:v", "1", "-vf", f"crop={zw}:{zh}:0:0", str(fr)], check=True)
            ref = ssim(fr, fa)
            ok = ss >= ref - 0.01
            print(f"{'✅' if ok else '❌'} SSIM dernière image / affiche : {ss:.4f} (plafond de compression {ref:.4f} ; attendu ≥ plafond − 0,01)")

            # Pendant quelle part de la vidéo l'affiche est-elle reconnaissable ? SSIM de chaque image contre l'affiche,
            # en gris et en basse définition (insensible au grain), rapportée à la SSIM de l'affiche floutée (sa mise en
            # page sans ses détails) : 0 = pas mieux que l'affiche floutée, 1 = l'affiche exacte. Sans cette base, le
            # fond blanc d'une affiche claire dépasse déjà 0,5 de SSIM brute. On compte toutes les images, pas la
            # dernière suite : un flash ou un fantôme en fin de vidéo ne doit pas effacer un remontage au milieu.
            # Mesuré : exemple v1 (remontage) 69 % du temps ; v2 (teaser) 25 % ; RTT dont le sigle reste à sa place
            # finale de 5,8 à 10,5 s : score 0,40 à 0,43 pendant ce passage, que l'ancienne mesure laissait passer.
            stats = Path(tmp) / "ssim.txt"
            subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-i", str(v), "-loop", "1", "-i", str(fa), "-lavfi",
                            f"[0]crop={zw}:{zh}:{zx}:{zy},scale=270:-2,format=gray[v];[1]scale=270:-2,format=gray[a];"
                            f"[v][a]ssim=stats_file={stats}", "-frames:v", str(round(D * fps)), "-f", "null", "-"], check=True)
            # ffmpeg écrit une ligne de plus que -frames:v (la dernière image répétée) : on la retire.
            sims = [float(m) for m in re.findall(r"All:([0-9.]+)", stats.read_text())][:round(D * fps)]
            r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(fa), "-lavfi",
                                "[0]scale=270:-2,format=gray,split[p][q];[p]gblur=sigma=8[f];[f][q]ssim", "-f", "null", "-"],
                               capture_output=True, text=True)
            base = float(re.findall(r"All:([0-9.]+)", r.stderr)[-1])
            vues = [i for i, s in enumerate(sims) if (s - base) / (1 - base) >= 0.35]
            part = len(vues) / max(1, len(sims))
            plages = []  # passages où l'affiche est reconnaissable (trous de moins de 0,2 s ignorés)
            for i in vues:
                if plages and i - plages[-1][1] <= round(0.2 * fps):
                    plages[-1][1] = i
                else:
                    plages.append([i, i])
            quand = ", ".join(f"{a / fps:.1f}-{(b + 1) / fps:.1f} s" for a, b in plages) or "jamais"
            if o.mode == "teaser":
                print(f"{'✅' if part <= 0.35 else '❌'} affiche reconnaissable {part:.0%} du temps ({quand}) "
                      "(teaser : ≤ 35 % ; au-delà, c'est l'affiche qui se remonte, pas un motion design)")
            else:
                print(f"ℹ️ affiche reconnaissable {part:.0%} du temps ({quand})")

    gels = re.findall(r"freeze_start: ([0-9.]+).*?freeze_duration: ([0-9.]+)", filtre(v, "freezedetect=n=0.0005:d=1.5"), re.S)
    gels = [(float(a), float(b)) for a, b in gels if float(a) + float(b) < D - 0.05]
    print(("⚠️ gels (début, durée) hors tenue finale : " + str(gels)) if gels else "✅ aucun gel > 1,5 s avant la fin")
    noirs = re.findall(r"black_start:([0-9.]+) black_end:([0-9.]+)", filtre(v, "blackdetect=d=0.2:pix_th=0.05"))
    print(("⚠️ écrans noirs : " + str(noirs)) if noirs else "✅ aucun écran noir ≥ 0,2 s")

    # Plans qui durent : chaque image comparée à celle d'1,5 s plus tard, en gris et réduites à 32 px (seule la
    # composition compte : grain, secousses, reflets et souffles s'y effacent) ; écart moyen < 12 niveaux : même plan.
    # Hors tenue finale (3,5 dernières s), un plan de plus de 3 s est une scène qui dure : la vidéo reste « sage » même
    # quand l'affiche n'y est pas reconnaissable. Mesuré : exemple v2 2,3 s au plus ; teaser RTT (sigle au centre
    # pendant que de petits textes apparaissent) 6,0 s, et toujours 6,0 s après 4 secousses, un reflet et un souffle
    # réglés pour passer une mesure image à image (écart à 0,5 s), que ces effets trompaient (2,2 s).
    pw, ph = 32, max(2, round(32 * H / W))
    brut = subprocess.run(["ffmpeg", "-v", "error", "-i", str(v), "-vf", f"scale={pw}:{ph}:flags=area,format=gray",
                           "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    ims = [Image.frombytes("L", (pw, ph), brut[i:i + pw * ph]) for i in range(0, len(brut) - pw * ph + 1, pw * ph)]
    lag, fin = max(1, round(1.5 * fps)), len(ims) - round(3.5 * fps)
    plans = []  # suites d'images i dont l'image i + lag est du même plan
    for i in range(0, fin - lag):
        if ImageStat.Stat(ImageChops.difference(ims[i], ims[i + lag])).mean[0] < 12:
            if plans and plans[-1][1] == i - 1:
                plans[-1][1] = i
            else:
                plans.append([i, i])
    a, b = max(plans, key=lambda r: r[1] - r[0], default=(0, 0))
    plan = (b - a + 1 + lag) / fps if plans else 0.0
    ou = f"{a / fps:.1f}-{(b + 1 + lag) / fps:.1f} s" if plans else "aucun"
    if o.mode == "teaser":
        print(f"{'✅' if plan <= 3 else '❌'} plus long plan de même composition avant la tenue finale : {plan:.1f} s ({ou}) "
              "(teaser : ≤ 3 s ; au-delà, une scène qui dure : la découper, pas l'agiter)")
    else:
        print(f"ℹ️ plus long plan de même composition avant la tenue finale : {plan:.1f} s ({ou})")

    tr = v.with_name("trace.json")
    j = json.loads(tr.read_text()) if tr.exists() else {"images": []}
    if j["images"] and j["images"][-1]["calques"]:  # scènes à calques tracés (.calque[data-attendu]) seulement
        imgs = j["images"]
        fin = [im for im in imgs if im["t"] <= j["duree"] - 1.0] or imgs  # avant l'atterrissage
        print("calque    apparaît  écart final (px)   hors cadre à la fin")
        for c in imgs[-1]["calques"]:
            ident = c[0]
            app = next((im["t"] for im in imgs for e in im["calques"] if e[0] == ident and e[5] >= 0.5), None)
            e = next(e for e in fin[-1]["calques"] if e[0] == ident)
            ecart = "—"
            if e[6]:
                ax, ay, aw, ah = (float(x) for x in e[6].split(","))
                ecart = f"{max(abs(e[1] - ax), abs(e[2] - ay), abs(e[3] - aw), abs(e[4] - ah)):.0f}"
            hors = e[1] + e[3] < 0 or e[2] + e[4] < 0 or e[1] > j["largeur"] or e[2] > j["hauteur"]
            print(f"{ident:<9} {('%.2f s' % app) if app is not None else 'JAMAIS':>8}  {ecart:>8}           {'⚠️ oui' if hors else 'non'}")


if __name__ == "__main__":
    main()
