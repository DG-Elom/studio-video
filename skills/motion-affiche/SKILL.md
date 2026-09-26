---
name: motion-affiche
description: >-
  Turn an EXISTING poster, flyer or banner (PNG/JPG) into a motion-design video (event teaser,
  Instagram story or reel, WhatsApp status), coded frame by frame and checked by measurement; macOS.
  Animer une affiche, un flyer, une bannière ou un visuel EXISTANT : motion design, teaser
  d'événement, vidéo story/réel/statut à partir d'une image, « fais bouger ce visuel », même sans
  dire « skill ». Pas pour un tutoriel d'application (tutoriel-video) ni pour une vidéo générée par
  IA (Veo, Kling…).
---

# Affiche → motion design

**Un motion design ne remonte pas l'affiche : il la raconte.** Chaque élément (logo, titre, mots-clés, visages, date, infos) a sa scène, en typographie recréée en vectoriel, avec formes, chocs et transitions. L'affiche n'apparaît qu'à la fin, quand tout atterrit à sa place, et **la dernière image EST l'affiche**. Chaque image est une fonction pure de `t`, rendue image par image avec flou de mouvement.

Mesuré : la version « remontage » (les calques de l'affiche entrent à leur place en 3 s, puis tenue) a été jugée **« trop sage »** à l'usage ; l'affiche y était reconnaissable 69 % du temps (teaser refait : 25 %). `planche.py` mesure cette part et la refuse au-delà de 35 %.

Mode par défaut : **teaser**. Mode **affiche** (animation discrète de l'affiche elle-même, en bas de page) seulement si l'utilisateur le demande (« juste faire bouger un peu », statut sobre).

Fichiers : `S=${CLAUDE_SKILL_DIR}/scripts` · `${CLAUDE_SKILL_DIR}/templates/exemple-teaser.html` (exemple complet, adapté d'un teaser réel aux textes remplacés, 15 s : **le lire avant d'écrire**) · `templates/kit-motion.js` (briques) · `references/sources.md`.
Dépendances : macOS 14+ (Vision via `swift`), Python 3 + Pillow + `playwright`, Google Chrome dans /Applications (lancé par `scripts/chrome-muet.sh`), `ffmpeg`. GSAP 3.13 et Google Fonts chargés par CDN au rendu.

## Déroulé (teaser)

Projet dans un dossier temporaire propre à la tâche (scratchpad), jamais dans le dossier du skill.

1. **Analyse** : `python3 $S/analyse.py affiche.jpg <projet>`, puis **regarder `analyse/reperes.png`** (textes T…, sujets S…, grille en px). Couleurs : les `accents` (saturées) sont celles de la marque, les dominantes comptent le fond. Choisir la Google Font la plus proche de chaque police (condensée grasse → Anton ; condensée fine → Bebas Neue ; géométrique → Montserrat…).
2. **Storyboard (fiche de mouvement) AVANT le code**, en commentaire en tête de la scène (modèle : la fiche de l'exemple) :
   - un concept en une phrase tiré du sujet (feu, lumière, papier, néon, douceur…) : il décide des textures, des couleurs et des transitions. Ne pas recopier le feu de l'exemple sur une affiche claire : là, lueurs, vignette et grain passent en `multiply` (en `screen`/`overlay`, ils disparaissent sur le blanc), la frange de déchirure est sombre et le fantôme de l'atterrissage délavé vers le blanc (assombri, le blanc vire au gris) ;
   - 5 à 7 scènes de 1,3 à 2,6 s, 12 à 16 s au total, calées sur une grille de 0,5 s ;
   - une idée par scène, chacune avec un motif du catalogue ; entre deux scènes, une transition qui porte le mouvement (zoom à travers, déchirure, objet lancé), pas un fondu ;
   - pendant les scènes, **aucun élément à sa place et à sa taille finales** : centré, agrandi, recadré ou en mouvement, il ne rejoint sa place qu'à l'atterrissage (RTT : sigle posé à sa place de 5,8 à 11,6 s → affiche reconnaissable 57 % du temps, refusé) ;
   - 2 à 4 chocs (impact + secousse + flash) espacés d'au moins 1,5 s, en plus des micro-chocs du claquement lettre à lettre ; une secousse sans impact ne sert jamais à faire vivre un plan figé ;
   - fin : atterrissage (≈ 1,5 s) puis tenue lisible de 2,5 à 3 s.
3. **Éléments** : tout texte = typographie vectorielle, jamais un texte de l'affiche agrandi en pixels. Pixels seulement pour les photos, les logos, les objets et l'atterrissage : `python3 $S/calques.py …` (voir « Calques »).
4. **Scène** : copier `templates/exemple-teaser.html` et `templates/kit-motion.js` dans `<projet>/`. Garder le cadre (caméra, grain, braises, lueurs, flash, vignette, `rendu`, `echantillons`, atterrissage) et réécrire les scènes. Positions calculées après chargement des polices (`K.ajuste`, `K.encre`), jamais à l'œil.
5. **Boucle de contrôle** : `python3 $S/render.py <projet>/teaser.html --instants …` sur 15 à 20 instants (sans flou ; mesuré : 11 s pour 18 instants), puis **regarder `controle/planche.jpg`** (PNG en pleine taille à côté). Chercher un titre décentré, un texte coupé, une scène vide, une transition sans mouvement, un élément sans sa scène (slogan ou infos ajoutés en petit sous le logo : RTT). Puis `--flou 5` sur les passages rapides. Corriger, recommencer : le premier jet est un brouillon. Avant le rendu final, un **aperçu** : `render.py <projet>/teaser.html -o <projet>/apercu.mp4 --fps 10`, puis `planche.py <projet>/apercu.mp4 --affiche <projet>/affiche.png` (mesuré : 1 min en tout, contre 17 min pour le rendu final, et les mêmes mesures sur l'exemple) ; corriger tant qu'une des mesures de l'étape 7 est ❌.
6. **Rendu** : `python3 $S/render.py <projet>/teaser.html -o <projet>/<nom>.mp4 --flou 5` (4 navigateurs en parallèle ; mesuré : 17 min pour 15 s sur MacBook Air, donc en arrière-plan, l'outil Bash coupant à 10 min). Lire un éventuel « NON DÉTERMINISTE ».
7. **Contrôle** : `python3 $S/planche.py <projet>/<nom>.mp4 --affiche <projet>/affiche.png` → **regarder `<nom>-planche.jpg`**. Toutes les mesures ✅ : SSIM de fin, affiche reconnaissable au plus 35 % du temps et seulement à la fin, aucun plan de même composition de plus de 3 s avant la tenue finale, aucun gel, aucun écran noir. Une mesure ❌ se corrige par la mise en scène, jamais en réglant un effet contre planche.py (RTT : secousses calées pour passer une ancienne mesure, plan inchangé).
8. **Livrer** le MP4 (SendUserFile si l'outil existe), puis faire le ménage.

## Catalogue de motifs (tous dans l'exemple, sauf la poussée caméra et le reflet sur logo pixel)

| Motif | Recette |
|---|---|
| Fente de lumière (logo) | deux traits lumineux qui s'écartent ; `clip-path: inset(50% …)` → `inset(0)` |
| Claquement lettre à lettre | `K.lettres` ; `scale 2.6→1`, opacité 0→1, `expo.out` 0,32 s, 75 ms entre lettres ; micro-choc par lettre, choc à la dernière |
| Mot en texture | rangs du mot en contour (`-webkit-text-stroke`) qui défilent en sens alternés |
| Reflet | copie du mot en `background-clip: text`, dégradé qui balaie ; sur un logo pixel, le dégradé masqué par `mask-image: url(calques/logo.png)` |
| Zoom à travers une lettre | `K.encre` sur le O → `transformOrigin` au creux, `scale 1→70` en `expo.in` ; le creux prend la couleur de la scène suivante |
| Montée derrière un masque | lettres `yPercent 118→0` dans une boîte `overflow: hidden` |
| Mot coupé + inversion | moitiés haut/bas (`clip-path`) qui s'écartent puis claquent → choc, passage positif → négatif par `attr: {class}` |
| Déchirure de papier | `K.dechirure(p)` → `clip-path` du plan qui part + frange de papier |
| Mots au temps | un mot par demi-temps, `scale 1.7→1` ; mot-clé plus gros et en couleur ; personnes détourées DEVANT le texte |
| Carte + compteur | carte lancée (rotation, `expo.out`), `K.odometre`, balayage `clip-path`, texte tapé lettre à lettre |
| Bandeau d'infos | adresse, heure, réseaux qui défilent en bas |
| Poussée caméra | découpe un plan tenu : le groupe en place passe de `scale 1` à `1.5` (`expo.out`, 0,5 s), tenue serrée ≈ 1 s, retour `expo.in` tuilé avec l'entrée suivante (RTT : plan de 6 s ramené à 2,8 s) |
| Atterrissage | l'affiche elle-même, floue et assourdie (sombre, ou délavée si l'affiche est claire), se précise ; les calques pixel tombent à leur place ; fondu vers `#finale` |

## Règles de mouvement

| Règle | Pourquoi |
|---|---|
| Image 0 jamais vide : trait, lueur ou braises dès t = 0 | Le fil défile ; il faut accrocher en 0,3 s. |
| Affiche reconnaissable ≤ 35 % du temps, seulement à la fin | Sinon c'est un remontage, même partiel (« trop sage »). |
| Aucun plan de plus de 3 s avant la tenue finale (même composition à 1,5 s d'écart) : un plan qui dure se **découpe** en scènes (nouveau cadrage, élément suivant en grand, transition), il ne s'agite pas | RTT : sigle au centre 6 s pendant que de petits textes apparaissent, refusé malgré 18 % d'affiche reconnaissable ; avec 4 secousses, un reflet et un souffle en plus, toujours 6 s. |
| Entrées `expo.out`/`power3.out`, sorties `expo.in`, chocs sur un temps | L'accélération donne le poids ; la grille donne le rythme. |
| Texte posé immobile ≥ 0,6 s ; le mot-clé plus gros que le reste | Lisible même en passant vite. |
| Passage vectoriel → pixel caché par un mouvement ou un flash ; texte vectoriel calé sur le vrai (angle, taille et centre mesurés au pixel, cf. `cale` dans l'exemple) | Sinon on voit le texte se dédoubler. |
| Effets (grain ≈ 0,07, braises, lueurs, vignette) à 0 dans les 0,3 dernières s | La dernière image doit être l'affiche exacte. |
| `--flou 5`, et `window.echantillons(t)` = 16 sur les passages très rapides (zoom, déchirure, chute) | Sans flou, ça saccade ; à 5 sous-images, un mouvement très rapide se dédouble en escalier. |

## Calques (pixels de l'affiche)

`python3 $S/calques.py <projet> --retire S1,T6,T9-T18 --objet carte:x,y,w,h`
- `--retire` : éléments qui bougeront seuls. **Extraire moins** : un texte multicolore, translucide ou posé sur une texture reste dans son support (fond ou objet) ; un texte posé sur un objet reste dans ses pixels. Sans `--retire`, un texte dont l'encre est dans un objet (sigle d'un logo lu comme texte, texte d'une carte) y reste (ℹ️) ; nommé dans `--retire`, il y est bouché (⚠️).
- `--objet nom:x,y,w,h` : relance Vision sur une zone lue sur la grille (carte posée sur un groupe, logo…) ; un objet déclaré plus tard est au-dessus.
- En teaser, les trous flous de `calques/fond.png` gênent peu : l'atterrissage montre l'affiche elle-même, floue puis nette, sous les calques qui tombent.

## Pièges (payés en vrai)

- `window.rendu` ne doit **rien renvoyer** (`tl.seek()` renvoie la timeline → Playwright se fige sans erreur).
- Tout passe par la timeline ou par une fonction de `t` appelée dans `rendu` : pas de `Date.now()`, de `setTimeout`, ni d'animation CSS libre.
- Copie périmée du kit dans le projet : un correctif du kit n'agit qu'après recopie (titres décentrés de 300 px).
- Mesurer avant de déplacer : un décalage calculé après `gsap.set` sur le même élément vaut zéro (trait d'INHOUSE en haut de l'écran).
- `transform` sans effet sur un `<span>` en ligne : le passer en `inline-block`.
- GSAP 3 ne sait pas animer `className` : changer d'état par `tl.set(el, {attr: {class: "…"}}, t)`, qui s'annule quand on revient en arrière.
- `measureText` ignore `letter-spacing` et `word-spacing` s'ils ne sont pas repris dans le canvas (`K.encre` le fait).
- Un logo blanc sur fond sombre sort de Vision en rectangle opaque : clé de luminance sur l'affiche.
- La composition GPU varie de 1 à 2 niveaux selon les zones repeintes : render.py le tolère.
- render.py sert la scène sous `http://scene.local/` (réponses lues dans son dossier) : `mask-image`, `fetch()` et la lecture des pixels d'une image y marchent. Ouverte en `file://` dans un navigateur, ils échouent (un élément masqué disparaît).
- render.py figé après la dernière image : le `chrome_crashpad_handler` de Chrome, détaché, gardait la sortie d'erreur reliée au pilote Playwright. `chrome-muet.sh` l'envoie vers /dev/null : ne pas lancer Chrome autrement.
- Une SSIM de recomposé élevée ne prouve pas des calques justes : un texte recollé par-dessus cache un objet bouché (RTT : logo sans son orange, recomposé à 0,98). Regarder chaque calque objet.
- Vision fusionne le bas d'une affiche en un seul sujet (séparer avec `--objet`), classe parfois des lettres en sujets et lit mal les titres stylisés : regarder `reperes.png`.
- Une affiche granuleuse plafonne vers 0,94 de SSIM après H.264, même avec une dernière image parfaite : planche.py compare donc au plafond.
- zsh ne découpe pas `$VAR` en mots : dans les boucles, passer par Python ou par des tableaux.

## Mode affiche (animation discrète, sur demande)

`python3 $S/scene.py <projet> --format 1080x1350 --duree 8` génère le remontage des calques et l'atterrissage (exemple : `templates/exemple-choregraphie.js`). Ses règles : **règle des trous** (ce qui couvre un trou du fond arrive avant que la zone s'éclaire, ou pendant qu'elle est sombre) ; un grand objet (> 10 %) ne quitte pas sa place ; un texte posé sur un objet (`data-sur`) entre avec lui ; une ombre perdue au détourage se rend par `filter: drop-shadow(...)`. Contrôle : `planche.py --mode affiche`.

## Contrôles de fin

Vidéo lue par `ffprobe` (via planche.py) et planche regardée APRÈS le dernier rendu. Mesures toutes ✅, ou écart expliqué. Durée et format annoncés = mesurés. Ménage fait ou conservation motivée. Une vidéo dont personne n'a regardé la planche n'est pas livrable.
