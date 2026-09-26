// >>> CHORÉGRAPHIE — exemple adapté d'une affiche réelle (textes fictifs) : « FLAMENCO INHOUSE » (4:5, groupe + titre + carte de date)
// Calques : calques.py --retire S1,T1-T4,T6,T9-T18 --objet carte:250,880,580,340 --lettres T6
// Concept « FLAMENCO INHOUSE » : énergie, feu, impact.
// Fiche : noir, INHOUSE tombe lettre à lettre (0,25-1,05 s) → IMPACT 1,05 s : éclair, secousse, le fond
// s'embrase → papier de la date plaqué, groupe encore dans l'ombre (1,35 s) → le groupe s'éclaire (1,75-2,95 s)
// → infos pratiques par colonnes (3,0-3,9 s) + logo (3,3 s) → tenue lisible, lueur vivante → atterrissage (7,1 s).
const aff = $("#affiche");
const lueur = document.createElement("div");  // halo de feu, piloté par la timeline (pas d'animation CSS libre)
lueur.style.cssText = "position:absolute;inset:0;pointer-events:none;mix-blend-mode:screen;opacity:0;" +
  "background:radial-gradient(60% 45% at 85% 35%, rgba(255,120,30,.55), transparent 70%)," +
  "radial-gradient(50% 40% at 10% 80%, rgba(255,90,20,.35), transparent 70%)";
const flash = document.createElement("div");  // éclair d'impact d'INHOUSE
flash.style.cssText = "position:absolute;inset:0;pointer-events:none;opacity:0;mix-blend-mode:screen;" +
  "background:radial-gradient(55% 30% at 50% 40%, rgba(255,170,90,.9), transparent 75%)";
aff.insertBefore(lueur, $("#finale"));
aff.insertBefore(flash, $("#finale"));

// Règle des trous : tout ce qui couvre un trou (INHOUSE, papier) arrive AVANT que la zone dessous s'éclaire.
// Fond : presque noir pendant l'arrivée d'INHOUSE, puis s'embrase à l'impact ; légère poussée continue.
tl.fromTo("#fond", { scale: 1.1, filter: "brightness(.12)" }, { filter: "brightness(.12)", duration: .01 }, 0)
  .to("#fond", { filter: "brightness(1)", duration: .7, ease: "power2.out" }, 1.05)
  .to("#fond", { scale: 1, duration: DUREE, ease: "none" }, 0);
tl.set("#S1", { filter: "brightness(.12)", scale: 1.07, transformOrigin: "50% 100%" }, 0);
// Ombre portée d'INHOUSE perdue au détourage : recréée en CSS.
tl.set("#T6", { filter: "drop-shadow(0 10px 22px rgba(0,0,0,.65))" }, 0);

// INHOUSE : chaque lettre tombe de très grand dans le noir.
tl.from("#T6 .lettre", { scale: 2.6, opacity: 0, transformOrigin: "50% 60%", duration: .4,
                         ease: "expo.in", stagger: .05 }, .25);
// Impact : éclair + secousse + embrasement.
tl.fromTo(flash, { opacity: 0 }, { opacity: 1, duration: .08, ease: "none" }, 1.05)
  .to(flash, { opacity: 0, duration: .5, ease: "power2.out" }, 1.13);
tl.fromTo(aff, { x: 0, y: 0 }, { keyframes: [{ x: -14, y: 6 }, { x: 11, y: -8 }, { x: -6, y: 4 }, { x: 3, y: -2 }, { x: 0, y: 0 }],
                                 duration: .35, ease: "none" }, 1.05);
// Lueur de feu : pulsations irrégulières mais déterministes.
tl.to(lueur, { opacity: .9, duration: .5 }, 1.1);
[[1.7, .55], [2.4, .95], [3.2, .6], [4.0, 1], [4.8, .65], [5.6, .95], [6.4, .7]]
  .forEach(([t, o]) => tl.to(lueur, { opacity: o, duration: .7, ease: "sine.inOut" }, t));

// Papier de la date : plaqué pendant que le groupe est encore dans l'ombre.
tl.fromTo("#carte", { scale: 1.45, rotation: -9, opacity: 0 },
                    { scale: 1, rotation: 0, opacity: 1, duration: .5, ease: "back.out(2.2)" }, 1.35)
  .fromTo(aff, { x: 0 }, { keyframes: [{ x: 7 }, { x: -5 }, { x: 0 }], duration: .2, ease: "none" }, 1.55);
// Groupe : grand objet (> 10 %) → ne quitte pas sa place ; il sort de l'ombre et monte d'un cran.
tl.to("#S1", { filter: "brightness(1)", scale: 1, duration: 1.2, ease: "power2.out" }, 1.75);

// Infos pratiques : par paires (colonnes), de gauche à droite.
[["#T9", "#T10"], ["#T11", "#T12"], ["#T13", "#T14"], ["#T15", "#T16"], ["#T17", "#T18"]]
  .forEach((paire, i) => tl.from(paire, { y: 18, opacity: 0, duration: .45, stagger: .06 }, 3.0 + i * .12));
// Logo de l'église.
tl.from(["#T1", "#T2", "#T3", "#T4"], { x: 30, opacity: 0, duration: .5, stagger: .05 }, 3.3);
// <<< CHORÉGRAPHIE
