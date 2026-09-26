#!/usr/bin/env python3
"""Découpe l'affiche analysée en calques animables, fond reconstruit dessous.

Usage : python3 calques.py <projet> [--retire T1,T2,S1] [--objet nom:x,y,w,h ...] [--lettres T3] [--marge 6]
  --retire  éléments de analyse/calques.json à sortir du fond, plages permises (T9-T18) ; défaut : tous,
            sauf les textes dont l'encre est à ≥ 60 % dans un objet (sigle d'un logo, texte d'une carte) : ils y restent
  --objet   zone à détourer en plus (Vision relancé sur ce recadrage) : carte, logo… Un objet déclaré
            plus tard est posé DESSUS les précédents : ce qu'il cache chez eux est bouché.
  --lettres textes à découper aussi en lettres (T3-0.png, T3-1.png…) pour une typo cinétique
Produit <projet>/calques/ : fond.png, <id>.png, scene.json (positions en px de l'affiche),
recompose.png (tous les calques remis en place) et affiche le SSIM recompose/affiche.
"""
import argparse, json, re, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image, ImageChops, ImageFilter, ImageMath, ImageStat

ICI = Path(__file__).resolve().parent


def remplir(rgba):
    """Bouche les pixels transparents par tirer-pousser (moyennes pyramidales, alpha prémultiplié)."""
    niveaux = [rgba]
    while min(niveaux[-1].size) > 2:
        w, h = niveaux[-1].size
        niveaux.append(niveaux[-1].resize((max(1, w // 2), max(1, h // 2)), Image.BOX))
    plein = niveaux[-1].copy()
    plein.putalpha(255)
    for n in reversed(niveaux[:-1]):
        plein = Image.alpha_composite(plein.resize(n.size, Image.BILINEAR), n)
    return plein


def dilate(masque, px):
    return masque.filter(ImageFilter.MaxFilter(px * 2 + 1)) if px > 0 else masque


def detoure(affiche, boite):
    x, y, w, h = boite
    with tempfile.TemporaryDirectory() as d:
        affiche.crop((x, y, x + w, y + h)).save(f"{d}/zone.png")
        subprocess.run(["swift", str(ICI / "vision.swift"), f"{d}/zone.png", d], check=True, capture_output=True)
        v = json.loads(Path(f"{d}/vision.json").read_text())
        if not v["sujets"]:
            return None
        masque = Image.new("L", (w, h), 0)
        for s in v["sujets"]:
            masque = ImageChops.lighter(masque, Image.open(f"{d}/{s['fichier']}").getchannel("A"))
    plein = Image.new("L", affiche.size, 0)
    plein.paste(masque, (x, y))
    return plein


def encre(p):
    """Masque des pixels loin de la couleur du BORD de la zone p (son support) : l'encre d'un texte."""
    anneau = Image.new("L", p.size, 255)
    anneau.paste(0, (3, 3, max(4, p.width - 3), max(4, p.height - 3)))
    bord = tuple(int(c) for c in ImageStat.Stat(p, anneau).median)
    ecart = ImageChops.difference(p, Image.new("RGB", p.size, bord)).split()
    return ImageChops.lighter(ImageChops.lighter(ecart[0], ecart[1]), ecart[2]).point(lambda v: 255 if v > 60 else 0)


def cle_texte(P, B, boite, exclure=None):
    """Alpha du texte par différence de couleur avec le fond reconstruit B (fonds dégradés compris)."""
    x, y, w, h = boite
    p, b = P.crop((x, y, x + w, y + h)), B.crop((x, y, x + w, y + h))
    diff = ImageChops.difference(p, b).convert("L")
    seuil = int(ImageStat.Stat(diff).extrema[0][1] * 0.3)
    fort = diff.point(lambda v: 255 if v >= max(seuil, 24) else 0)
    # …et loin de la couleur du BORD de la zone (le support : cartouche, aplat, ciel) — sinon un
    # cartouche clair mal reconstruit passe pour du texte.
    loin = encre(p)
    if ImageChops.multiply(fort, loin).getbbox():
        fort = ImageChops.multiply(fort, loin)
    # Couleur du texte = teinte la PLUS FRÉQUENTE parmi les pixels qui diffèrent du fond
    # (pas la plus extrême : un reflet blanc battrait un grand titre gris).
    px = [c for c, f in zip(zip(*[iter(p.tobytes())] * 3), fort.tobytes()) if f]
    if not px:
        px = list(zip(*[iter(p.tobytes())] * 3))
    casiers = {}
    for c in px:
        casiers.setdefault((c[0] >> 5, c[1] >> 5, c[2] >> 5), []).append(c)
    dominant = max(casiers.values(), key=len)
    T = [round(sum(c[i] for c in dominant) / len(dominant)) for i in range(3)]
    proches = [c for c in px if sum((c[i] - T[i]) ** 2 for i in range(3)) < 90 ** 2]
    moy = [sum(c[i] for c in proches) / len(proches) for i in range(3)]
    uni = max((sum((c[i] - moy[i]) ** 2 for c in proches) / len(proches)) ** .5 for i in range(3)) < 22
    pb, bb = [c.convert("F") for c in p.split()], [c.convert("F") for c in b.split()]
    v = dict(pr=pb[0], pg=pb[1], pb=pb[2], br=bb[0], bg=bb[1], bb=bb[2])

    def alpha(m):
        dr, dg, db = T[0] - m["br"], T[1] - m["bg"], T[2] - m["bb"]
        num = (m["pr"] - m["br"]) * dr + (m["pg"] - m["bg"]) * dg + (m["pb"] - m["bb"]) * db
        return m["convert"](m["min"](m["max"](num / (dr * dr + dg * dg + db * db + 1) * 255, 0), 255), "L")

    # Voile faible (texture du fond prise pour du texte) supprimé ; les bords utiles sont au-dessus.
    a = ImageMath.lambda_eval(alpha, **v).point(lambda x: 0 if x < 24 else min(255, round((x - 24) * 255 / 231)))
    if exclure is not None:
        a = ImageChops.subtract(a, exclure.crop((x, y, x + w, y + h)))
    if uni:
        couleur = Image.new("RGB", p.size, tuple(T))
    else:  # décontamination : C = B + (P - B) / a
        af = a.convert("F")
        couleur = Image.merge("RGB", [
            ImageMath.lambda_eval(lambda m: m["convert"](m["min"](m["max"](m["b"] + (m["p"] - m["b"]) * 255 / m["max"](m["a"], 12), 0), 255), "L"),
                                  p=pb[i], b=bb[i], a=af) for i in range(3)])
    calque = couleur.convert("RGBA")
    calque.putalpha(a)
    return calque, "#%02x%02x%02x" % tuple(T), uni


def lettres(calque, ident, dossier, x0, y0):
    """Découpe un calque de texte en glyphes selon les colonnes vides de son alpha.

    Une coupure exige ≥ 2 colonnes vides (l'anticrénelage crée de faux creux) ; un morceau plus
    étroit que 15 % de la hauteur rejoint son voisin (sinon « MOSELLE » donne 10 fragments).
    Deux lettres qui se touchent (« LL ») restent ensemble : c'est voulu.
    """
    a = calque.getchannel("A")
    col = list(a.resize((a.width, 1), Image.BOX).tobytes())
    seuil = max(6, 0.1 * max(col))  # relatif : la texture d'une photo laisse un voile entre les lettres
    morceaux, debut, vides = [], None, 0
    for i, v in enumerate(col + [0, 0]):
        if v > seuil:
            if debut is None:
                debut = i
            vides = 0
        elif debut is not None:
            vides += 1
            if vides >= 2:
                morceaux.append([debut, i - vides + 1])
                debut, vides = None, 0
    mini = max(3, round(0.15 * a.height))
    fusion = []
    for m in morceaux:
        if fusion and (m[1] - m[0] < mini or fusion[-1][1] - fusion[-1][0] < mini):
            fusion[-1][1] = m[1]
        else:
            fusion.append(m)
    sortie = []
    for k, (g, d) in enumerate(fusion):
        f = dossier / f"{ident}-{k}.png"
        bb = a.crop((g, 0, d, a.height)).getbbox() or (0, 0, d - g, a.height)
        calque.crop((g, 0, d, a.height)).crop(bb).save(f)
        sortie.append({"fichier": f"calques/{f.name}", "x": x0 + g + bb[0], "y": y0 + bb[1], "w": bb[2] - bb[0], "h": bb[3] - bb[1]})
    return sortie


def _place(petit, boite, taille):
    plein = Image.new("L", taille, 0)
    plein.paste(petit, tuple(boite[:2]))
    return plein


def ssim(a, b):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(a), "-i", str(b), "-lavfi", "ssim", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.search(r"All:([0-9.]+)", r.stderr)
    return float(m.group(1)) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("projet")
    ap.add_argument("--retire", default="")
    ap.add_argument("--objet", action="append", default=[])
    ap.add_argument("--lettres", default="")
    ap.add_argument("--marge", type=int, default=6)
    o = ap.parse_args()
    projet = Path(o.projet)
    ana = json.loads((projet / "analyse" / "calques.json").read_text())
    P = Image.open(projet / "affiche.png").convert("RGB")
    out = projet / "calques"
    out.mkdir(exist_ok=True)
    garder = set()
    for jeton in filter(None, o.retire.split(",")):  # « T9-T18 » ou « T9-18 » = plage
        m = re.fullmatch(r"([A-Z]+)(\d+)-\1?(\d+)", jeton)
        garder |= {f"{m[1]}{i}" for i in range(int(m[2]), int(m[3]) + 1)} if m else {jeton}
    garder = garder or {e["id"] for e in ana["textes"] + ana["sujets"]}

    objets = []  # (id, masque plein format)
    for s in ana["sujets"]:
        if s["id"] in garder:
            m = Image.new("L", P.size, 0)
            m.paste(Image.open(projet / s["fichier"]).getchannel("A"), tuple(s["boite"][:2]))
            objets.append((s["id"], m))
    for spec in o.objet:
        nom, b = spec.split(":")
        m = detoure(P, [int(v) for v in b.split(",")])
        if m is None:
            print(f"⚠️ {nom} : Vision ne trouve aucun sujet dans cette zone", file=sys.stderr)
        else:
            objets.append((nom, m))
    # Un texte dont l'encre est dans un objet (sigle d'un logo lu comme texte, texte d'une carte) fait partie de
    # ses pixels : retiré, il serait bouché dans l'objet (RTT : sigle lu « Ptt », logo sans son orange, alors que la
    # SSIM du recomposé restait à 0,98). L'encre, pas la boîte : un sigle ne couvre que 40 % de sa boîte.
    # Par défaut on l'y laisse ; nommé dans --retire, on prévient.
    textes = []
    for t in ana["textes"]:
        if t["id"] not in garder:
            continue
        x, y, w, h = t["boite"]
        ink = encre(P.crop((x, y, x + w, y + h)))
        n = max(1, ink.histogram()[255])
        dedans = [(ident, ImageChops.multiply(ink, m.crop((x, y, x + w, y + h)).point(lambda v: 255 if v > 8 else 0)).histogram()[255] / n)
                  for ident, m in objets]
        ident, part = max(dedans, key=lambda d: d[1], default=("", 0))
        if part >= 0.6 and not o.retire:
            print(f"ℹ️ {t['id']} « {t['texte']} » reste dans l'objet {ident} ({part:.0%} dedans) ; le nommer dans --retire pour l'en sortir")
            continue
        if part >= 0.6:
            print(f"⚠️ {t['id']} « {t['texte']} » est à {part:.0%} dans l'objet {ident} : retiré, il y sera bouché", file=sys.stderr)
        textes.append(t)

    def zone(t, marge):
        x, y, w, h = t["boite"]
        m = max(marge, h // 6)
        return [max(0, x - m), max(0, y - m), min(P.width, x + w + m) - max(0, x - m), min(P.height, y + h + m) - max(0, y - m)]

    def construire(trous_textes):
        """Fond bouché + objets (textes intérieurs bouchés) + « dessous » = ce que chaque texte recouvre."""
        trous = trous_textes.copy()
        for _, m in objets:
            trous = ImageChops.lighter(trous, dilate(m.point(lambda v: 255 if v > 8 else 0), o.marge))
        base = P.convert("RGBA")
        base.putalpha(ImageChops.invert(trous))
        fond = remplir(base).convert("RGB")
        dessous, faits = fond.copy(), []
        for i, (ident, m) in enumerate(objets):
            rgba = P.convert("RGBA")
            rgba.putalpha(m)
            dessus = trous_textes  # textes retirés + objets déclarés APRÈS celui-ci (posés dessus)
            for _, m2 in objets[i + 1:]:
                dessus = ImageChops.lighter(dessus, dilate(m2.point(lambda v: 255 if v > 8 else 0), o.marge))
            interieur = ImageChops.multiply(dessus, m.point(lambda v: 255 if v > 8 else 0))
            if interieur.getbbox():
                trou = rgba.copy()
                trou.putalpha(ImageChops.subtract(m, interieur))
                rgba = remplir(trou).convert("RGB").convert("RGBA")
                rgba.putalpha(m)
            dessous.paste(rgba.convert("RGB"), (0, 0), m)
            faits.append((ident, m, rgba))
        return fond, faits, dessous

    def propre(t):
        """Boîte Vision à peine élargie (accents) + masque des AUTRES textes, à exclure de celui-ci."""
        x, y, w, h = t["boite"]
        e = max(2, h // 10)
        b = [max(0, x - e), max(0, y - e), min(P.width, x + w + e) - max(0, x - e), min(P.height, y + h + e) - max(0, y - e)]
        autres = Image.new("L", P.size, 0)
        for u in textes:
            if u is not t:
                ux, uy, uw, uh = u["boite"]
                autres.paste(255, (ux, uy, ux + uw, uy + uh))
        return b, autres

    # Passe 1 : trous = boîtes des textes (grossier) → forme des glyphes.
    boites = Image.new("L", P.size, 0)
    for t in textes:
        x, y, w, h = zone(t, o.marge)
        boites.paste(255, (x, y, x + w, y + h))
    _, _, dessous = construire(boites)
    glyphes = Image.new("L", P.size, 0)
    for t in textes:
        b, autres = propre(t)
        calque, _, _ = cle_texte(P, dessous, b, autres)
        g = dilate(calque.getchannel("A").point(lambda v: 255 if v > 40 else 0), max(o.marge, t["boite"][3] // 12))
        glyphes = ImageChops.lighter(glyphes, _place(g, b, P.size))
    # Passe 2 : trous = glyphes dilatés seulement → le fond garde sa texture entre les lettres.
    fond, faits, dessous = construire(glyphes)
    fond.save(out / "fond.png")

    scene = {"largeur": P.width, "hauteur": P.height, "fond": "calques/fond.png", "calques": []}
    for ident, m, rgba in faits:
        bb = m.point(lambda v: 255 if v > 8 else 0).getbbox()
        rgba.crop(bb).save(out / f"{ident}.png")
        scene["calques"].append({"id": ident, "type": "objet", "fichier": f"calques/{ident}.png",
                                 "x": bb[0], "y": bb[1], "w": bb[2] - bb[0], "h": bb[3] - bb[1]})
    for t in textes:
        b, autres = propre(t)
        calque, couleur, uni = cle_texte(P, dessous, b, autres)
        bb = calque.getchannel("A").point(lambda v: 255 if v > 10 else 0).getbbox() or (0, 0, b[2], b[3])
        calque = calque.crop(bb)
        calque.save(out / f"{t['id']}.png")
        e = {"id": t["id"], "type": "texte", "texte": t["texte"], "couleur": couleur, "uni": uni,
             "fichier": f"calques/{t['id']}.png", "x": b[0] + bb[0], "y": b[1] + bb[1], "w": calque.width, "h": calque.height}
        if t["id"] in o.lettres.split(","):
            e["lettres"] = lettres(calque, t["id"], out, e["x"], e["y"])
        scene["calques"].append(e)
    (out / "scene.json").write_text(json.dumps(scene, ensure_ascii=False, indent=2))

    rec = fond.convert("RGBA")
    for c in scene["calques"]:
        rec.alpha_composite(Image.open(projet / c["fichier"]).convert("RGBA"), (c["x"], c["y"]))
    rec.convert("RGB").save(out / "recompose.png")
    for c in scene["calques"]:
        print(f'{c["id"]:>8} {c["type"]:<6} x={c["x"]} y={c["y"]} {c["w"]}x{c["h"]}' + (f' {c["couleur"]} « {c["texte"]} »' if c["type"] == "texte" else "") + (f' {len(c.get("lettres", []))} lettres' if "lettres" in c else ""))
    print(f"SSIM recompose/affiche : {ssim(out / 'recompose.png', projet / 'affiche.png')}  (≥ 0,95 bon ; 0,92-0,95 : accepter seulement si recompose.png ne montre que des ombres/bords ; sinon retirer moins)")


if __name__ == "__main__":
    main()
