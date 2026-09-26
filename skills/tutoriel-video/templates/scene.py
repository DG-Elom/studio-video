# Démo <n> : <ce que montre la démo>. Lancer : python3 scene.py (sans cues.json = répétition à blanc).
import sys
from pathlib import Path
sys.path.insert(0, "__SCRIPTS__")  # remplacé à la copie par le dossier scripts/ du skill (SKILL.md, étape 5)
from tuto import Rec, browser, config

DEMO = Path(__file__).resolve().parent
PROJET = DEMO.parent
BASE = config(PROJET)["base_url"].rstrip("/")


def reset(page):
    # remettre l'application dans l'état de départ (supprimer les restes des prises précédentes)
    pass


with browser(PROJET) as page:
    reset(page)
    page.goto(BASE + "/"); page.wait_for_load_state("networkidle")
    page.get_by_text("Texte présent seulement une fois la page chargée").first.wait_for(timeout=30000)
    page.wait_for_timeout(1500)
    r = Rec(page, DEMO); r.start()

    r.mark("01-intro")
    r.point(page.get_by_role("link", name="Menu").first, 1)

    r.mark("02-etape")
    r.at(1); r.click(page.get_by_role("link", name="Menu").first, 1)
    r.at(2); r.click(page.get_by_role("button", name="Bouton"), 0.6)

    r.mark("03-attente")
    r.at(1); r.click(page.get_by_role("button", name="Run"), 0.5)
    # attente d'un résultat de durée variable : HORS voix, sur un sélecteur VISIBLE
    page.locator("text=Résultat >> visible=true").first.wait_for(timeout=120000)

    r.mark("04-resultat")
    r.at(1); r.point(page.locator("text=Résultat >> visible=true").first, 0.5)

    r.mark("05-outro")
    r.glide(800, 300)
    r.finish()
