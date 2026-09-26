#!/usr/bin/env python3
"""Rend une scène HTML en MP4, image par image, sur une horloge virtuelle (aucune image sautée).

Contrat de la page : window.DUREE (s), window.rendu(t) qui fixe l'état à l'instant t,
window.pret (Promise, facultatif). Les éléments .calque[data-attendu="x,y,w,h"] sont tracés.

Usage :
  python3 render.py <scene.html> --instants 0,1.5,3,7.9 [--flou 5]   # PNG + planche.jpg dans controle/
  python3 render.py <scene.html> -o video.mp4 [--fps 30] [--flou 5] [--travailleurs 4] [--son musique.mp3]
--flou N : flou de mouvement, moyenne de N sous-images sur un obturateur à 180° (N=1 : aucun) ;
           la page peut en exiger davantage sur un passage rapide avec window.echantillons(t).
--travailleurs K : K navigateurs rendent chacun une tranche d'images (segments sans perte), puis assemblage.
Écrit à côté de la vidéo : trace.json (position/opacité de chaque calque à chaque image).
"""
import argparse, io, json, os, shutil, subprocess, sys, time
from multiprocessing import get_context
from pathlib import Path
from urllib.parse import quote, unquote, urlparse
from PIL import Image, ImageChops, ImageDraw, ImageMath
from playwright.sync_api import sync_playwright

ORIGINE = "http://scene.local/"

ALEA = """(() => { let s = 20260925; Math.random = () => { s |= 0; s = s + 0x6D2B79F5 | 0;
  let t = Math.imul(s ^ s >>> 15, 1 | s); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
  return ((t ^ t >>> 14) >>> 0) / 4294967296; }; })();"""

# Attente bornée : sans délai, une police ou un script du CDN qui ne répond pas figerait le rendu sans erreur.
PRET = """async () => {
  const delai = new Promise((_, non) => setTimeout(() => non(new Error(
    'page pas prête en 60 s : police, GSAP ou image injoignable (réseau, CDN ?) ; relancer')), 60000));
  await Promise.race([delai, (async () => {
    await (window.pret || Promise.resolve());
    await document.fonts.ready;
    await Promise.all([...document.images].map(i => i.decode().catch(() => { throw new Error('image illisible : ' + i.src); })));
  })()]);
  const s = document.querySelector('#scene') || document.body;
  const r = s.getBoundingClientRect();
  return { w: Math.round(r.width), h: Math.round(r.height), duree: window.DUREE, rendu: typeof window.rendu };
}"""

TRACE = """() => {
  const s = (document.querySelector('#scene') || document.body).getBoundingClientRect();
  return [...document.querySelectorAll('.calque[id]')].map(e => {
    let o = 1; for (let n = e; n && n.nodeType === 1; n = n.parentElement) o *= +getComputedStyle(n).opacity;
    const r = e.getBoundingClientRect();
    return [e.id, Math.round(r.x - s.x), Math.round(r.y - s.y), Math.round(r.width), Math.round(r.height), +o.toFixed(3), e.dataset.attendu || ''];
  });
}"""


def ouvrir(p, html):
    nav = p.chromium.launch(executable_path=str(Path(__file__).resolve().parent / "chrome-muet.sh"),
                            args=["--force-color-profile=srgb", "--hide-scrollbars"])
    page = nav.new_page(viewport={"width": 1920, "height": 1920}, device_scale_factor=1)
    page.add_init_script(ALEA)
    # Scène servie sous une origine http virtuelle : Playwright répond depuis son dossier, sans port ouvert. En file://,
    # Chrome bloque mask-image d'un fichier local (logo masqué : élément invisible), fetch() et la lecture de pixels.
    racine = Path(html).resolve().parent

    def servir(route):
        f = (racine / unquote(urlparse(route.request.url).path).lstrip("/")).resolve()
        route.fulfill(path=str(f)) if f.is_file() and racine in f.parents else route.fulfill(status=404)
    page.route(ORIGINE + "**", servir)
    erreurs = []
    page.on("pageerror", lambda e: erreurs.append(str(e)))
    page.on("console", lambda m: m.type == "error" and erreurs.append(m.text))
    page.set_default_timeout(60000)
    page.goto(ORIGINE + quote(Path(html).name))
    info = page.evaluate(PRET)
    if info["rendu"] != "function" or not info["duree"]:
        sys.exit(f"❌ la page doit définir window.DUREE et window.rendu(t) : {info}")
    # Sur une page neuve, un tout premier seek(0) de GSAP n'applique pas les réglages posés à t = 0 (le temps ne
    # change pas) : l'image 0 de la vidéo sortait sans eux (RTT : image 0 vide), alors que --instants la montrait juste.
    page.evaluate("d => { window.rendu(d); window.rendu(0); }", info["duree"])
    page.set_viewport_size({"width": info["w"], "height": info["h"]})
    return nav, page, info, erreurs


def capture(page, t):
    page.evaluate("t => { window.rendu(t); }", t)  # jamais la valeur de retour (sérialisation infinie)
    return page.screenshot(type="png", clip={"x": 0, "y": 0, **page.viewport_size})


def moyenne(ims):
    """Moyenne exacte (arrondie) de N images RGB."""
    n = len(ims)
    bandes = []
    for b in range(3):
        canaux = {f"c{k}": im.getchannel(b) for k, im in enumerate(ims)}

        def somme(a):
            s = a["c0"]
            for k in range(1, n):
                s = s + a[f"c{k}"]
            return a["convert"]((s + n // 2) / n, "L")
        bandes.append(ImageMath.lambda_eval(somme, **canaux))
    return Image.merge("RGB", bandes)


def image(page, t, fps, flou, duree):
    """PNG de l'instant t ; avec flou > 1, moyenne de sous-images réparties sur la moitié de l'intervalle (180°).
    La page peut en demander plus sur les passages rapides : window.echantillons(t) → nombre (0 = défaut)."""
    if flou <= 1:
        return capture(page, t)
    flou = max(flou, int(page.evaluate("t => window.echantillons ? +window.echantillons(t) || 0 : 0", t)))
    ims = [Image.open(io.BytesIO(capture(page, min(duree, max(0.0, t + ((k + .5) / flou - .5) * .5 / fps))))).convert("RGB")
           for k in range(flou)]
    tampon = io.BytesIO()
    moyenne(ims).save(tampon, "PNG", compress_level=1)
    return tampon.getvalue()


def ecart(a, b):
    """Plus grand écart entre deux PNG, en niveaux (0-255)."""
    d = ImageChops.difference(Image.open(io.BytesIO(a)).convert("RGB"), Image.open(io.BytesIO(b)).convert("RGB"))
    return max(hi for _, hi in d.getextrema())


def planche(vues, sortie):
    """Planche des instants de contrôle, instant écrit au-dessus de chaque vignette : une seule image à regarder."""
    ims = [(t, Image.open(f).convert("RGB")) for t, f in vues]
    w, h = ims[0][1].size
    cols = 5 if w >= h else 7
    tw = 1600 // cols
    th = round(tw * h / w)
    pl = Image.new("RGB", (cols * tw, -(-len(ims) // cols) * (th + 22)), "#111")
    d = ImageDraw.Draw(pl)
    for i, (t, im) in enumerate(ims):
        x, y = (i % cols) * tw, (i // cols) * (th + 22)
        pl.paste(im.resize((tw - 4, th)), (x + 2, y + 20))
        d.text((x + 6, y + 4), f"{t:.2f} s", fill="#ffea00")
    pl.save(sortie, quality=85)
    print(f"🖼️  {sortie} ({len(ims)} instants, PNG en pleine taille à côté)")


def tranche(args):
    """Rend les images [i0, i1) dans un segment sans perte (FFV1). Exécuté dans un processus à part."""
    html, i0, i1, fps, flou, segment, rang = args
    trace = []
    with sync_playwright() as p:
        nav, page, info, erreurs = ouvrir(p, html)
        duree = float(info["duree"])
        enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(fps),
                                "-c:v", "png", "-i", "-", "-c:v", "ffv1", segment], stdin=subprocess.PIPE)
        for i in range(i0, i1):
            t = i / fps
            enc.stdin.write(image(page, t, fps, flou, duree))
            trace.append({"t": round(t, 4), "calques": page.evaluate(TRACE)})
            if (i - i0) % (fps * 3) == 0:
                print(f"  [{rang}] {i - i0}/{i1 - i0} images", flush=True)
        enc.stdin.close()
        ok = enc.wait() == 0
        nav.close()
    return ok, trace, erreurs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("-o", "--sortie")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--instants")
    ap.add_argument("--son")
    ap.add_argument("--flou", type=int, default=1, help="sous-images par image (flou de mouvement), 1 = aucun")
    ap.add_argument("--travailleurs", type=int, default=max(1, min(4, (os.cpu_count() or 2) // 2)))
    o = ap.parse_args()
    if not o.sortie and not o.instants:
        sys.exit("indiquer -o video.mp4 ou --instants")
    with sync_playwright() as p:
        nav, page, info, erreurs = ouvrir(p, o.html)
        W, H, D = info["w"], info["h"], float(info["duree"])
        # Déterminisme : l'état doit ne dépendre que de t (ni horloge réelle ni ordre de visite).
        # Tolérance de 2 niveaux : la composition GPU (fusions, grain) arrondit selon les zones repeintes.
        a, _, b = capture(page, D * 0.6), capture(page, D * 0.2), capture(page, D * 0.6)
        e = ecart(a, b)
        if e > 2:
            print(f"⚠️ NON DÉTERMINISTE : rendu(t) donne deux images différentes pour le même t (écart {e} niveaux) "
                  "(Date.now, animation CSS non pilotée, état cumulé, tween 'to' enchaîné sur la même propriété…)", file=sys.stderr)
        if o.instants:
            dossier = Path(o.html).resolve().parent / "controle"
            dossier.mkdir(exist_ok=True)
            vues = []
            for t in [float(x) for x in o.instants.split(",")]:
                f = dossier / f"t{t:06.2f}.png"
                f.write_bytes(image(page, min(t, D), o.fps, o.flou, D))
                vues.append((t, f))
            planche(vues, dossier / "planche.jpg")
        nav.close()
    if o.sortie:
        n = round(D * o.fps)
        k = max(1, min(o.travailleurs, n // 30))
        parts = Path(o.sortie).resolve().with_suffix(".parts")
        parts.mkdir(exist_ok=True)
        bornes = [round(n * j / k) for j in range(k + 1)]
        taches = [(o.html, bornes[j], bornes[j + 1], o.fps, o.flou, str(parts / f"{j:02d}.mkv"), j) for j in range(k)]
        debut = time.time()
        print(f"  {n} images, {k} travailleur(s), flou {o.flou}")
        if k == 1:
            resultats = [tranche(taches[0])]
        else:
            with get_context("spawn").Pool(k) as pool:
                resultats = pool.map(tranche, taches)
        if not all(r[0] for r in resultats):
            sys.exit("❌ ffmpeg a échoué sur un segment")
        liste = parts / "liste.txt"
        liste.write_text("".join(f"file '{t[5]}'\n" for t in taches))
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(liste)]
        if o.son:
            cmd += ["-i", o.son, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k", "-shortest"]
        cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(o.fps),
                "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-movflags", "+faststart", o.sortie]
        if subprocess.run(cmd).returncode != 0:
            sys.exit("❌ ffmpeg a échoué à l'assemblage")
        shutil.rmtree(parts)
        trace = [im for r in resultats for im in r[1]]
        erreurs += [e for r in resultats for e in r[2]]
        Path(o.sortie).with_name("trace.json").write_text(json.dumps({"fps": o.fps, "duree": D, "largeur": W, "hauteur": H, "images": trace}))
        print(f"✅ {o.sortie} : {n} images {W}x{H} à {o.fps} i/s, flou {o.flou}, en {time.time() - debut:.0f} s")
    if erreurs:
        print("⚠️ erreurs JS : " + " | ".join(dict.fromkeys(erreurs[:5])), file=sys.stderr)


if __name__ == "__main__":
    main()
