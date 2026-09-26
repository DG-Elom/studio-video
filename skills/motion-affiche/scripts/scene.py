#!/usr/bin/env python3
"""Génère <projet>/scene.html : les calques placés au pixel près + une chorégraphie GSAP par rôle.

Usage : python3 scene.py <projet> [--format 1080x1080|1080x1350|1080x1920|1920x1080] [--duree 8]
La chorégraphie produite est un POINT DE DÉPART : on la réécrit ensuite selon la fiche de mouvement.
"""
import argparse, json
from pathlib import Path

GSAP = "https://cdn.jsdelivr.net/npm/gsap@3.13.0/dist/gsap.min.js"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("projet")
    ap.add_argument("--format", default="1080x1080")
    ap.add_argument("--duree", type=float, default=8)
    o = ap.parse_args()
    projet = Path(o.projet)
    sc = json.loads((projet / "calques" / "scene.json").read_text())
    W, H = (int(v) for v in o.format.split("x"))
    w, h = sc["largeur"], sc["hauteur"]
    k = min(W / w, H / h)
    ox, oy = (W - w * k) / 2, (H - h * k) / 2

    def attendu(c):
        return f'{ox + c["x"] * k:.0f},{oy + c["y"] * k:.0f},{c["w"] * k:.0f},{c["h"] * k:.0f}'

    objets = [c for c in sc["calques"] if c["type"] == "objet"]

    def support(c):  # objet qui contient ce texte (cartouche, carte…) : ils entrent ensemble
        for ob in objets:
            if ob["x"] <= c["x"] and ob["y"] <= c["y"] and c["x"] + c["w"] <= ob["x"] + ob["w"] and c["y"] + c["h"] <= ob["y"] + ob["h"]:
                return ob["id"]
        return ""

    lignes = [f'<img class="calque" id="fond" src="{sc["fond"]}" style="left:0;top:0;width:{w}px;height:{h}px" data-attendu="{attendu({"x": 0, "y": 0, "w": w, "h": h})}">']
    for c in sc["calques"]:
        pos = f'left:{c["x"]}px;top:{c["y"]}px;width:{c["w"]}px;height:{c["h"]}px'
        role = "objet" if c["type"] == "objet" else ("titre" if c["h"] >= 0.08 * h else "texte")
        sur = f' data-sur="{support(c)}"' if c["type"] == "texte" and support(c) else ""
        if c.get("lettres"):
            enfants = "".join(
                f'<img class="lettre" src="{l["fichier"]}" style="left:{l["x"] - c["x"]}px;top:{l["y"] - c["y"]}px;width:{l["w"]}px;height:{l["h"]}px">'
                for l in c["lettres"])
            lignes.append(f'<div class="calque" id="{c["id"]}" data-role="{role}"{sur} style="{pos}" data-attendu="{attendu(c)}">{enfants}</div>')
        else:
            lignes.append(f'<img class="calque" id="{c["id"]}" data-role="{role}"{sur} src="{c["fichier"]}" style="{pos}" data-attendu="{attendu(c)}"'
                          + (f' alt="{c["texte"]}"' if c["type"] == "texte" else "") + ">")
    part_objets = {c["id"]: round(c["w"] * c["h"] / (w * h), 3) for c in sc["calques"] if c["type"] == "objet"}

    html = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<script src="{GSAP}"></script>
<style>
  html, body {{ margin: 0; background: #000; }}
  #scene {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; background: #000; }}
  #debord {{ position: absolute; inset: -60px; background: url(affiche.png) center / cover; filter: blur(40px) brightness(.6); }}
  #affiche {{ position: absolute; left: {ox:.1f}px; top: {oy:.1f}px; width: {w}px; height: {h}px;
             transform: scale({k:.5f}); transform-origin: 0 0; overflow: hidden; }}
  .calque, .lettre, #finale {{ position: absolute; display: block; will-change: transform, opacity; }}
  #finale {{ left: 0; top: 0; width: {w}px; height: {h}px; opacity: 0; }}
</style></head>
<body><div id="scene"><div id="debord"></div><div id="affiche">
{chr(10).join(lignes)}
<img id="finale" src="affiche.png">
</div></div>
<script>
// Toute image doit être une fonction pure de t : pas de Date.now(), pas de setTimeout, pas d'animation CSS libre.
window.DUREE = {o.duree};
const PART_OBJETS = {json.dumps(part_objets)};  // fraction de l'affiche couverte par chaque objet
const tl = gsap.timeline({{ paused: true, defaults: {{ ease: "power3.out" }} }});
const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];

// >>> CHORÉGRAPHIE (à réécrire selon la fiche de mouvement ; le reste du fichier ne bouge pas)
// 1. Fond : sort de l'ombre (jamais transparent : ses trous restent sombres tant qu'ils sont à nu)
//    + lente poussée (vie pendant toute la durée).
tl.fromTo("#fond", {{ filter: "brightness(.3)", scale: 1.12 }}, {{ filter: "brightness(1)", duration: 1.2, ease: "power1.out" }}, 0)
  .fromTo("#debord", {{ opacity: .3 }}, {{ opacity: 1, duration: 1.2, ease: "power1.out" }}, 0)  // les débords suivent le fond
  .to("#fond", {{ scale: 1, duration: DUREE, ease: "none" }}, 0);

// 2. Objets : un GRAND objet (> 10 %) ne quitte jamais sa place (le fond dessous est flou) ;
//    un petit objet peut entrer franchement.
$$('[data-role="objet"]').forEach((e, i) => {{
  if (PART_OBJETS[e.id] > .10) tl.fromTo(e, {{ scale: 1.08, transformOrigin: "50% 100%", filter: "brightness(.6)" }},
                                         {{ scale: 1, filter: "brightness(1)", duration: 1.6 }}, .2);
  else tl.from(e, {{ scale: 0, rotation: -12, opacity: 0, duration: .7, ease: "back.out(1.8)" }}, .6 + i * .15);
}});

// 3. Textes posés sur un objet (cartouche, carte) : entrent AVEC lui, sinon son trou flou reste visible.
$$('[data-sur]').forEach((e, i) => tl.from(e, {{ opacity: 0, y: 10, duration: .5 }}, .5 + i * .08));
// 4. Autres textes dans l'ordre de lecture (haut → bas) : titres lettre à lettre si découpés, sinon rideau.
const textes = $$('[data-role="titre"]:not([data-sur]), [data-role="texte"]:not([data-sur])').sort((a, b) => a.offsetTop - b.offsetTop || a.offsetLeft - b.offsetLeft);
let t0 = .9;
textes.forEach(e => {{
  const lettres = e.querySelectorAll(".lettre");
  if (lettres.length) tl.from(lettres, {{ yPercent: 60, opacity: 0, rotationX: -70, duration: .6, stagger: .05, ease: "back.out(1.6)" }}, t0);
  else if (e.dataset.role === "titre") tl.fromTo(e, {{ clipPath: "inset(0 100% 0 0)", x: -30 }}, {{ clipPath: "inset(0 0% 0 0)", x: 0, duration: .8, ease: "power4.out" }}, t0);
  else tl.from(e, {{ y: 24, opacity: 0, duration: .55 }}, t0);
  t0 += e.dataset.role === "titre" ? .45 : .25;
}});

// <<< CHORÉGRAPHIE

// Atterrissage : fondu vers l'affiche d'origine → la dernière image EST l'affiche.
tl.to("#finale", {{ opacity: 1, duration: .5, ease: "power1.inOut" }}, DUREE - .9);
tl.set({{}}, {{}}, DUREE);

window.rendu = t => {{ tl.seek(t, false); }};  // ne rien renvoyer : Playwright sérialiserait la timeline
</script></body></html>
"""
    (projet / "scene.html").write_text(html)
    print(f"✅ {projet / 'scene.html'} · {W}x{H} · échelle {k:.3f} · {len(sc['calques'])} calques · {o.duree} s")


if __name__ == "__main__":
    main()
