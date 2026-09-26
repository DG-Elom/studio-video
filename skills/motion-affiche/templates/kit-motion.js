/* kit-motion.js — briques de motion design pour le mode teaser de motion-affiche.
   Copier ce fichier à côté de la scène (<script src="kit-motion.js">), après GSAP.
   Règle : tout est une fonction pure de t. Les fonctions qui dessinent (grain, braises, lueurs,
   déchirure) s'appellent depuis window.rendu(t), APRÈS tl.seek(t) ; jamais depuis une horloge. */
(function () {
  const K = {};

  // Aléa à graine (mulberry32) : mêmes valeurs à chaque rendu et dans chaque processus.
  K.alea = seed => {
    let s = seed | 0;
    return () => {
      s = s + 0x6D2B79F5 | 0;
      let t = Math.imul(s ^ s >>> 15, 1 | s);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  };

  // Progression 0→1 entre t0 et t1 avec une courbe GSAP ("expo.out", "power2.inOut"…).
  K.prog = (t, t0, t1, ease = "none") => gsap.parseEase(ease)(Math.min(1, Math.max(0, (t - t0) / (t1 - t0))));

  // Charge les polices puis vérifie qu'elles sont là : sinon la vidéo part en police de secours sans erreur.
  K.polices = async specs => {
    await Promise.all(specs.map(s => document.fonts.load(s)));
    await document.fonts.ready;
    const manquantes = specs.filter(s => !document.fonts.check(s));
    if (manquantes.length) throw new Error("police absente : " + manquantes.join(", "));
  };

  // Découpe le texte d'un élément en <span class="car"> inline-block (espaces insécables conservées).
  K.lettres = (el, cls = "car") => {
    const txt = el.textContent;
    el.textContent = "";
    return [...txt].map(c => {
      const s = document.createElement("span");
      s.className = cls;
      s.textContent = c === " " ? "\u00a0" : c;
      s.style.display = "inline-block";
      el.appendChild(s);
      return s;
    });
  };

  // Fixe la taille de police pour que l'élément (inline-block, nowrap) mesure `largeur` px.
  K.ajuste = (el, largeur) => {
    el.style.fontSize = "100px";
    const f = 100 * largeur / el.getBoundingClientRect().width;
    el.style.fontSize = f + "px";
    return f;
  };

  // Boîte d'ENCRE d'un texte (pas sa boîte typographique), en px relatifs à `repere`, mesurée
  // avant toute transformation. Sert à centrer un mot sur ses capitales ou à viser le creux d'un O.
  K.encre = (el, repere) => {
    const cs = getComputedStyle(el);
    const g = document.createElement("canvas").getContext("2d");
    g.font = `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
    g.letterSpacing = cs.letterSpacing === "normal" ? "0px" : cs.letterSpacing;  // même espacement que le DOM
    g.wordSpacing = cs.wordSpacing === "normal" ? "0px" : cs.wordSpacing;
    g.fontKerning = cs.fontKerning === "none" ? "none" : "normal";
    // Blancs de mise en forme du HTML (retour \u00e0 la ligne, indentation) r\u00e9duits comme le fait le DOM : mesur\u00e9s tels
    // quels, ils d\u00e9calaient la bo\u00eete de 117 \u00e0 129 px (titres RTT \u00e9crits sur plusieurs lignes).
    const texte = /^pre(-wrap)?$|^break-spaces$/.test(cs.whiteSpace) ? el.textContent
      : el.textContent.replace(/[ \t\n\r\f]+/g, " ").replace(/^ | $/g, "");
    const m = g.measureText(texte.replace(/\u00a0/g, " "));
    const sonde = document.createElement("span");
    sonde.style.cssText = "display:inline-block;width:0;height:0;vertical-align:baseline";
    el.insertBefore(sonde, el.firstChild);
    const base = sonde.getBoundingClientRect().top, r = el.getBoundingClientRect(), o = repere.getBoundingClientRect();
    sonde.remove();
    return {
      x: r.left - o.left - m.actualBoundingBoxLeft, y: base - o.top - m.actualBoundingBoxAscent,
      w: m.actualBoundingBoxLeft + m.actualBoundingBoxRight, h: m.actualBoundingBoxAscent + m.actualBoundingBoxDescent,
    };
  };

  // Compteur à rouleaux : chaque chiffre défile `tours` fois avant de s'arrêter sur sa valeur.
  // Renvoie [{pile, n}] : animer pile de yPercent 0 à -100*n/(n+1).
  K.odometre = (el, texte, tours = 1) => {
    el.textContent = "";
    return [...texte].map((ch, i) => {
      const col = document.createElement("span");
      col.style.cssText = "display:inline-block;overflow:hidden;height:1em;line-height:1em;vertical-align:top;text-align:center";
      const pile = document.createElement("span");
      pile.style.display = "block";
      const n = 10 * (tours + i) + +ch;  // le 2e chiffre tourne plus longtemps : les rouleaux ne s'arrêtent pas ensemble
      for (let k = 0; k <= n; k++) {
        const d = document.createElement("span");
        d.style.display = "block";
        d.textContent = k % 10;
        pile.appendChild(d);
      }
      col.appendChild(pile);
      el.appendChild(col);
      const mesure = document.createElement("span");
      mesure.textContent = ch;
      el.appendChild(mesure);
      col.style.width = mesure.getBoundingClientRect().width + "px";
      mesure.remove();
      return { pile, n };
    });
  };

  // Secousse de caméra : somme d'impulsions amorties (6 à 10 Hz, en dessous de la fréquence d'image).
  K.secousse = (impacts, t) => {
    let x = 0, y = 0, r = 0;
    for (const { t: ti, force = 1, duree = .45 } of impacts) {
      const d = t - ti;
      if (d < 0 || d > duree) continue;
      const env = force * (1 - d / duree) ** 2;
      x += 20 * env * Math.sin(d * 60 + ti * 7);
      y += 15 * env * Math.sin(d * 47 + ti * 3 + 1.7);
      r += .6 * env * Math.sin(d * 38 + ti * 5 + .6);
    }
    return { x, y, r };
  };

  // Grain de film : tuiles de bruit tirées une fois, choisies et décalées selon le numéro d'image.
  // Canvas en mix-blend-mode: overlay ; régler l'opacité du canvas pour la force.
  K.grain = (canvas, { seed = 3, tuiles = 6, taille = 256, fps = 30 } = {}) => {
    const R = K.alea(seed), ctx = canvas.getContext("2d"), motifs = [];
    for (let k = 0; k < tuiles; k++) {
      const c = document.createElement("canvas");
      c.width = c.height = taille;
      const g = c.getContext("2d"), d = g.createImageData(taille, taille);
      for (let i = 0; i < d.data.length; i += 4) {
        d.data[i] = d.data[i + 1] = d.data[i + 2] = R() * 255 | 0;
        d.data[i + 3] = 255;
      }
      g.putImageData(d, 0, 0);
      motifs.push(ctx.createPattern(c, "repeat"));
    }
    return t => {
      const f = Math.round(t * fps), r = K.alea(f * 7919 + seed);
      ctx.save();
      ctx.fillStyle = motifs[f % tuiles];
      ctx.translate(-(r() * taille | 0), -(r() * taille | 0));
      ctx.fillRect(0, 0, canvas.width + taille, canvas.height + taille);
      ctx.restore();
    };
  };

  // Braises qui montent (particules). densite 0→1 = part des particules visibles.
  K.braises = (canvas, { n = 120, seed = 11, couleur = "255,122,32", vmin = 45, vmax = 170, tmin = 1.4, tmax = 4, vent = 18 } = {}) => {
    const R = K.alea(seed), W = canvas.width, H = canvas.height, ctx = canvas.getContext("2d");
    const P = Array.from({ length: n }, () => ({
      x: R() * W, y: R() * (H + 200), v: vmin + R() * (vmax - vmin), s: tmin + R() * (tmax - tmin),
      a: 8 + R() * 36, f: .5 + R() * 2, ph: R() * 6.283, o: R(),
    }));
    const spr = document.createElement("canvas");
    spr.width = spr.height = 64;
    const g = spr.getContext("2d"), rg = g.createRadialGradient(32, 32, 0, 32, 32, 32);
    rg.addColorStop(0, "rgba(255,244,214,1)");
    rg.addColorStop(.16, `rgba(${couleur},.95)`);
    rg.addColorStop(.42, `rgba(${couleur},.22)`);
    rg.addColorStop(1, `rgba(${couleur},0)`);
    g.fillStyle = rg;
    g.fillRect(0, 0, 64, 64);
    return (t, densite = 1) => {
      ctx.clearRect(0, 0, W, H);
      if (densite <= 0) return;
      ctx.globalCompositeOperation = "lighter";
      for (const q of P) {
        if (q.o > densite) continue;
        const y = ((q.y - q.v * t) % (H + 200) + H + 200) % (H + 200) - 100;
        const x = ((q.x + q.a * Math.sin(q.f * t + q.ph) + vent * t) % W + W) % W;
        ctx.globalAlpha = Math.max(0, .55 + .45 * Math.sin(t * q.f * 7 + q.ph));
        const sz = q.s * 9;
        ctx.drawImage(spr, x - sz / 2, y - sz / 2, sz, sz);
      }
      ctx.globalAlpha = 1;
    };
  };

  // Lueurs de feu : dégradés radiaux qui dérivent (élément en mix-blend-mode: screen).
  // sources = [{x, y, r, c:"255,110,20", a, vx, vy, f, ph}]
  K.lueurs = (el, sources) => (t, force = 1) => {
    el.style.background = sources.map(({ x, y, r, c, a, vx = 0, vy = 0, f = .5, ph = 0 }) => {
      const px = x + vx * Math.sin(t * f + ph), py = y + vy * Math.cos(t * f * .8 + ph);
      const al = Math.max(0, a * force * (.82 + .18 * Math.sin(t * f * 3.1 + ph)));
      return `radial-gradient(circle ${r}px at ${px.toFixed(1)}px ${py.toFixed(1)}px, rgba(${c},${al.toFixed(3)}), rgba(${c},0))`;
    }).join(",") || "none";
  };

  // Déchirure qui balaie l'écran (transition « papier arraché »).
  // Renvoie p => {reste, bord} : deux polygon() CSS. `reste` = ce qui n'est pas encore arraché
  // (clip-path du plan qui part), `bord` = la frange de papier blanc le long de la déchirure.
  K.dechirure = ({ W, H, angle = -15, seed = 5, pas = 18, ampl = 18, bordMin = 5, bordMax = 22 }) => {
    const R = K.alea(seed), a = angle * Math.PI / 180, d = [Math.cos(a), Math.sin(a)], e = [-d[1], d[0]];
    const L = Math.hypot(W, H), n = Math.ceil(2 * L / pas);
    const f1 = R() * 6, f2 = R() * 6;
    const jit = Array.from({ length: n + 1 }, (_, i) => {
      const s = i * pas;
      return ampl * (.6 * Math.sin(s * .006 + f1) + .3 * Math.sin(s * .019 + f2) + .5 * (R() - .5));
    });
    const larg = Array.from({ length: n + 1 }, () => bordMin + R() * (bordMax - bordMin));
    const poly = pts => `polygon(${pts.map(([x, y]) => `${x.toFixed(1)}px ${y.toFixed(1)}px`).join(",")})`;
    return p => {
      const c = -L / 2 - 2 * (ampl + bordMax) + p * (L + 4 * (ampl + bordMax));
      const cx = W / 2 + d[0] * c, cy = H / 2 + d[1] * c;
      const bordure = jit.map((j, i) => { const s = -L + i * pas; return [cx + e[0] * s + d[0] * j, cy + e[1] * s + d[1] * j]; });
      const loin = [bordure[n][0] + d[0] * 2 * L, bordure[n][1] + d[1] * 2 * L, bordure[0][0] + d[0] * 2 * L, bordure[0][1] + d[1] * 2 * L];
      const reste = poly([...bordure, [loin[0], loin[1]], [loin[2], loin[3]]]);
      const bord = poly([...bordure, ...bordure.map(([x, y], i) => [x + d[0] * larg[i], y + d[1] * larg[i]]).reverse()]);
      return { reste, bord };
    };
  };

  window.KIT = K;
})();
