# Tournage « voix d'abord » : navigateur au profil connecté, curseur visible, screencast CDP horodaté,
# gestes déclenchés aux instants où la voix prononce les repères {n} (cues.json, produit par tts.py).
# Arborescence : <projet>/tuto.json, <projet>/profile/ (profil navigateur), <projet>/<démo>/{narration.txt,scene.py}.
import json, re, sys, time, base64, shutil
from contextlib import contextmanager
from pathlib import Path
from playwright.sync_api import sync_playwright

CURSOR_JS = r"""(() => {
  if (window.__tutoCursor) return; window.__tutoCursor = true;
  const add = () => {
    const c = document.createElement('div');
    c.style.cssText = 'position:fixed;z-index:2147483647;pointer-events:none;width:22px;height:22px;left:-50px;top:-50px;'
      + 'background:url("data:image/svg+xml;utf8,<svg xmlns=%27http://www.w3.org/2000/svg%27 width=%2722%27 height=%2722%27><path d=%27M2 2 L2 18 L7 13 L10 20 L13 19 L10 12 L17 12 Z%27 fill=%27white%27 stroke=%27black%27 stroke-width=%271.5%27/></svg>") no-repeat;';
    document.documentElement.appendChild(c);
    document.addEventListener('mousemove', e => { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; }, true);
    document.addEventListener('mousedown', e => {
      const r = document.createElement('div');
      r.style.cssText = `position:fixed;z-index:2147483646;pointer-events:none;left:${e.clientX-18}px;top:${e.clientY-18}px;width:36px;height:36px;border-radius:50%;border:3px solid #ffb020;opacity:1;transition:all .45s ease-out;`;
      document.documentElement.appendChild(r);
      requestAnimationFrame(() => { r.style.transform = 'scale(1.8)'; r.style.opacity = '0'; });
      setTimeout(() => r.remove(), 600);
    }, true);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', add); else add();
})();"""

SEQ_RE = r"## (\S+)[^\n]*\n(.*?)(?=\n## |\Z)"


def config(projet):
    return json.loads((Path(projet) / "tuto.json").read_text())


def fake_cues(demo):
    # répétition à blanc, sans voix : un repère par seconde
    out = {}
    for sid, body in re.findall(SEQ_RE, (demo / "narration.txt").read_text(), re.S):
        ks = re.findall(r"\{(\d+)\}", body)
        out[sid] = {k: float(i + 1) for i, k in enumerate(ks)} | {"_fin": float(len(ks) + 1)}
    return out


class Rec:
    # Les pauses passent par page.wait_for_timeout : un time.sleep bloque la réception
    # des images du screencast (API synchrone) et fige la vidéo pendant l'attente.
    def __init__(self, page, demo):
        self.page, self.demo, self.marks, self.n = page, Path(demo), [], 0
        self.frames = self.demo / "frames"
        cues = self.demo / "cues.json"
        self.cues = json.loads(cues.read_text()) if cues.exists() else fake_cues(self.demo)
        if not cues.exists(): print("RÉPÉTITION À BLANC (pas de cues.json)")
        self.cdp = page.context.new_cdp_session(page)
        self.cdp.on("Page.screencastFrame", self.on_frame)
        self.mouse = (800, 450)

    def on_frame(self, ev):
        self.n += 1
        (self.frames / f"{ev['metadata']['timestamp']:.4f}.jpg").write_bytes(base64.b64decode(ev["data"]))
        self.cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]})

    def start(self):
        shutil.rmtree(self.frames, ignore_errors=True); self.frames.mkdir()
        self.cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 92, "maxWidth": 1920, "maxHeight": 1080, "everyNthFrame": 1})

    def finish(self):
        self.mark("fin")
        self.cdp.send("Page.stopScreencast"); self.sleep(0.5)
        (self.demo / "marks.json").write_text(json.dumps(self.marks, indent=1))
        print("images", self.n)

    def mark(self, sid):
        # ouvre la séquence sid, après la fin de la phrase précédente
        if self.marks and self.marks[-1]["id"] in self.cues:
            self.until(self.cues[self.marks[-1]["id"]]["_fin"] + 0.9)
        self.marks.append({"id": sid, "t": time.time()})
        print("SEQ", sid, flush=True)

    def until(self, sec):
        # sec = instant dans la voix de la séquence courante ; la voix démarre 0,4 s après la marque
        dt = self.marks[-1]["t"] + 0.4 + sec - time.time()
        if dt > 0: self.sleep(dt)
        elif dt < -0.6: print(f"  retard {-dt:.1f}s ({self.marks[-1]['id']})", flush=True)

    def at(self, k, lead=0.35):
        # attend que la voix prononce le repère {k}
        self.until(self.cues[self.marks[-1]["id"]][str(k)] - lead)

    def glide(self, x, y, steps=18):
        x0, y0 = self.mouse
        for i in range(1, steps + 1):
            k = i / steps; k = k * k * (3 - 2 * k)
            self.page.mouse.move(x0 + (x - x0) * k, y0 + (y - y0) * k)
            self.sleep(0.012)
        self.mouse = (x, y)

    def center(self, loc):
        loc.scroll_into_view_if_needed()
        b = loc.bounding_box()
        return b["x"] + b["width"] / 2, b["y"] + b["height"] / 2

    def point(self, loc, pause=0.35):
        self.glide(*self.center(loc)); self.sleep(pause)

    def click(self, loc, pause=0.6):
        self.point(loc, 0.25)
        self.page.mouse.down(); self.sleep(0.06); self.page.mouse.up()
        self.sleep(pause)

    def drag(self, src, dst, pause=0.6):
        self.point(src, 0.2); self.page.mouse.down(); self.sleep(0.1)
        self.glide(*self.center(dst), steps=40); self.sleep(0.1)
        self.page.mouse.up(); self.sleep(pause)

    def type(self, loc, text, clear=True, delay=28):
        # delay=0 : texte inséré d'un bloc (longues saisies sans intérêt à l'écran)
        self.click(loc, 0.2)
        if clear:
            self.page.keyboard.press("Meta+A"); self.page.keyboard.press("Backspace")
        if delay: self.page.keyboard.type(text, delay=delay)
        else: self.page.keyboard.insert_text(text)
        self.sleep(0.4)

    def sleep(self, s):
        self.page.wait_for_timeout(s * 1000)


@contextmanager
def browser(projet, headless=True):
    # contexte persistant <projet>/profile ; vérifie la connexion si tuto.json déclare auth_check
    cfg = config(projet)
    w, h = cfg.get("viewport", [1600, 900])
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(str(Path(projet) / "profile"), channel="chrome", headless=headless,
                                                   viewport={"width": w, "height": h}, device_scale_factor=cfg.get("dpr", 1.2),
                                                   locale=cfg.get("locale", "en-US"))
        ctx.add_init_script(CURSOR_JS)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.on("pageerror", lambda e: print("pageerror", e))
        page.goto(cfg["base_url"]); page.wait_for_load_state("networkidle")
        if cfg.get("auth_check") and not page.evaluate(cfg["auth_check"]):
            sys.exit("PAS CONNECTÉ : lancer login.py <projet> et laisser l'utilisateur se connecter")
        try:
            yield page
        finally:
            ctx.close()
