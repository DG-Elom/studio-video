#!/usr/bin/env python3
"""Analyse une affiche : textes (OCR Vision), sujets détourés, couleurs dominantes.

Usage : python3 analyse.py <affiche.png|jpg> <dossier-projet>
Produit dans <projet>/analyse/ : vision.json, calques.json, sujet-N.png (recadrés),
reperes.png (boîtes numérotées T1…/S1… sur l'affiche, à REGARDER avant de planifier).
"""
import json, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw

ICI = Path(__file__).resolve().parent


def palette(im, n, total):
    q = im.quantize(colors=n, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()
    return [{"hex": "#%02x%02x%02x" % tuple(pal[i * 3:i * 3 + 3]), "part": round(c / total, 3)}
            for c, i in sorted(q.getcolors(), reverse=True)]


def couleurs(im, n=6):
    """Couleurs dominantes (fond compris) et couleurs d'accent, tirées des seuls pixels saturés : sur une affiche
    claire, les dominantes ne sont que des blancs (RTT : 6 quasi-blancs, ni l'orange ni le bleu de la marque)."""
    petit = im.convert("RGB").resize((96, 96))
    sat = bytes(v for c in zip(*[iter(petit.tobytes())] * 3) if max(c) >= 60 and max(c) - min(c) >= .35 * max(c) for v in c)
    accents = palette(Image.frombytes("RGB", (len(sat) // 3, 1), sat), 4, 96 * 96) if sat else []
    return palette(petit, n, 96 * 96), [a for a in accents if a["part"] >= .002]


def main(affiche, projet):
    projet = Path(projet)
    out = projet / "analyse"
    out.mkdir(parents=True, exist_ok=True)
    src = Image.open(affiche)
    src.convert("RGB").save(projet / "affiche.png")
    subprocess.run(["swift", str(ICI / "vision.swift"), str(projet / "affiche.png"), str(out)], check=True)
    v = json.loads((out / "vision.json").read_text())

    dominantes, accents = couleurs(src)
    calques = {"largeur": v["largeur"], "hauteur": v["hauteur"], "couleurs": dominantes, "accents": accents,
               "textes": [], "sujets": []}
    for i, t in enumerate(v["textes"], 1):
        calques["textes"].append({"id": f"T{i}", **t})
    for i, s in enumerate(v["sujets"], 1):
        im = Image.open(out / s["fichier"]).convert("RGBA")
        x0, y0, x1, y1 = im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox() or (0, 0, *im.size)
        f = out / f"sujet-S{i}.png"
        im.crop((x0, y0, x1, y1)).save(f)
        (out / s["fichier"]).unlink()
        calques["sujets"].append({"id": f"S{i}", "fichier": f"analyse/{f.name}", "boite": [x0, y0, x1 - x0, y1 - y0]})
    (out / "calques.json").write_text(json.dumps(calques, ensure_ascii=False, indent=2))

    rep = src.convert("RGB")
    d = ImageDraw.Draw(rep)
    pas = 100 if max(rep.size) <= 2000 else 200  # grille pour lire des coordonnées (--objet de calques.py)
    for x in range(pas, rep.width, pas):
        d.line((x, 0, x, rep.height), fill="#ffffff", width=1)
        d.text((x + 2, 2), str(x), fill="#ffffff", stroke_width=2, stroke_fill="black")
    for y in range(pas, rep.height, pas):
        d.line((0, y, rep.width, y), fill="#ffffff", width=1)
        d.text((2, y + 2), str(y), fill="#ffffff", stroke_width=2, stroke_fill="black")
    for c, coul in (("textes", "#00e5ff"), ("sujets", "#ffea00")):
        for e in calques[c]:
            x, y, w, h = e["boite"]
            d.rectangle((x, y, x + w, y + h), outline=coul, width=3)
            d.rectangle((x, y, x + 34, y + 18), fill=coul)
            d.text((x + 3, y + 3), e["id"], fill="black")
    rep.save(out / "reperes.png")
    for e in calques["textes"]:
        print(f'{e["id"]} {e["boite"]} conf={e["confiance"]:.2f} « {e["texte"]} »')
    for e in calques["sujets"]:
        print(f'{e["id"]} {e["boite"]} {e["fichier"]}')
    print("couleurs :", " ".join(c["hex"] for c in dominantes), "| accents :", " ".join(c["hex"] for c in accents) or "aucun")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
