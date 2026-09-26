# python3 login.py <projet> : ouvre un Chrome visible sur le profil du tournage ; l'UTILISATEUR s'y connecte
# lui-même (l'agent ne saisit jamais d'identifiants). Attend auth_check (3 h max), puis ferme.
import sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tuto import config

projet = Path(sys.argv[1]).resolve(); cfg = config(projet)
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(str(projet / "profile"), channel="chrome", headless=False,
                                               viewport=dict(zip(("width", "height"), cfg.get("viewport", [1600, 900]))))
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(cfg["base_url"])
    for _ in range(10800):
        try:
            if page.evaluate(cfg["auth_check"]):
                print("CONNECTÉ", page.url); break
        except Exception:
            pass  # navigation en cours
        time.sleep(1)
    else:
        print("PAS CONNECTÉ")
    time.sleep(2)
    ctx.close()
