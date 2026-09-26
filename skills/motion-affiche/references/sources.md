# Sources du skill motion-affiche (recherche du 25/09/2026)

Statut : **LU** = page ou résumé consulté ; « — » = date non affichée par la source ; **EXTRAIT** = extrait de recherche seulement ; **MESURÉ** = vérifié ici par un essai. Posts X lus via l'API publique fxtwitter. « → » = ce que le skill en a retenu.

## Praticiens (posts, dépôts, billets)

| Source | Date | Statut | Leçon |
|---|---|---|---|
| x.com/kenn/status/2103337314021937232 (cite @shneural) | 25/09/26 | LU | Prompt « showreel de 15 s » : Opus 5.5 xhigh jugé très supérieur à GPT 6 Astra, sur une seule comparaison. |
| x.com/leodavincs3/status/2103432795729154335 | 25/09/26 | LU | 30 min 50 s de run ; « 3 jours sous After Effects » → le gain est du temps humain, pas une qualité garantie. |
| x.com/samuel_spitz/status/2103293794594816100 | 25/09/26 | LU | Replit Animation : rendu JS → MP4 en moins de 30 min. |
| x.com/stephanlivera/status/2103315922098470926 | 25/09/26 | LU | Même prompt viral, effort max. |
| x.com/LCSlates/status/2102503027340988559 | 22/09/26 | LU (prompt : EXTRAIT) | 80 s carrées par Opus 5.5 seul. |
| x.com/abxxai/status/2102775755646337530 | 23/09/26 | LU (détail : EXTRAIT) | Opus (structure) + Seedance (image→vidéo réaliste) : autre famille, hors skill. |
| x.com/HeyGen/status/2048155061751288197 | 25/04/26 | LU | HyperFrames : HTML → vidéo pour agents. |
| github.com/heygen-com/hyperframes (guide claude-design) | — | LU | Interdiction de `Date.now()`/aléatoire ; le 1er rendu est un brouillon → **fonction pure de t** et **boucle de contrôle**. |
| remotion.dev/docs/ai/coding-agents | — | LU | Pipeline Remotion + skills d'agent ; aucun point de départ image. |
| louisedesadeleer.substack.com/p/how-i-make-custom-motion-graphics | — | LU | Donner l'image en référence, consignes courtes, puis itérer. |
| dev.to/dsplce-co (htmlrec) | — | LU | Horloge virtuelle + capture image par image ; piège des polices web → **render.py attend `document.fonts.ready`**. |
| github.com/beriki770-ship-it/code-animations | — | LU | Contrôle automatique (images noires, gels) → **planche.py : freezedetect/blackdetect**. |
| sabrina.dev/p/5-insane-claude-code-video-prompts | — | LU | Zones sûres mobiles, taille minimale de police, petites corrections après le 1er rendu. |
| pexo.ai/blog/best-image-to-video-skill-for-claude-code-9418 | — | LU | Distingue la vraie génération image→vidéo de l'effet Ken Burns. |
| github.com/klsoen/opus-js-animations | — | LU | Chaque image = fonction pure du temps (rendu parallèle, recalage sans refaire). |
| github.com/diffusionstudio/lottie | — | LU | Un ancrage visuel concret bat une description. |
| xda-developers.com (vibe-editing, PNG statiques → composants React) | — | LU | Reconstruire des visuels statiques en calques animés, c'est le principe du skill. |
| github.com/davidcervinka/vibe-editing | — | LU | Boucle inventaire → plan → rendu → auto-évaluation par images échantillonnées. |

## Recherche scientifique

| Référence | Statut | Technique retenue |
|---|---|---|
| Liu et al., *LogoMotion*, arXiv:2405.07065 (2024-25) | LU | Hiérarchie d'éléments + rôle sémantique → patron d'animation par rôle, puis réparation guidée par le rendu → **fiche de mouvement par rôles** et `data-role` dans scene.py. |
| Ma & Agrawala, *MoVer*, ACM TOG / SIGGRAPH 2025, arXiv:2502.13372 | LU | Prédicats spatio-temporels vérifiés sur une trace ; de 58,8 % à 93,6 % de réussite avec les itérations → **trace.json + tableau apparition/écart final** de planche.py. |
| Tseng et al., *Keyframer* (Apple), arXiv:2402.06071 | LU | Instructions décomposées et raffinées par petites touches → **boucle `--instants`**. |
| Suzuki et al., *LayerD*, ICCV 2025, arXiv:2509.25134 | LU | Retrait itératif des calques du dessus, apparence uniforme par calque → même logique dans calques.py (objets empilés, « dessous » reconstruit), sans le modèle entraîné. |
| Qwen Team, *Qwen-Image-Layered*, arXiv:2512.15603 | EXTRAIT | Décomposition RGBA par diffusion : trop lourde ; on garde l'idée « du fond vers l'avant ». |
| *Don't Forget Me* (arXiv:2207.10273), *DeepEraser* (2402.19108), *TextDestroyer* (2411.00355) | EXTRAIT | Retrait du texte par réseaux dédiés → remplacé par un tirer-pousser pyramidal (Pillow) + la **règle des trous**. |
| Xiao et al., *TypeDance*, CHI 2024, arXiv:2401.11094 | LU | Décomposer le texte à plusieurs granularités (mot, lettre) → `--lettres`. |
| Liu et al., *Dynamic Typography*, ICCV 2025, arXiv:2404.11614 | LU | La lisibilité reste une contrainte → texte immobile pendant sa lecture. |
| *AniClipart*, arXiv:2404.12347 (IJCV 2024) | LU | Trajectoires en Bézier, déformation rigide : inspiration seulement. |
| StarVector (arXiv:2312.11556), OmniSVG (arXiv:2504.06263) | LU / EXTRAIT | Vectorisation dédiée : inutile ici, on anime les pixels. |
| Si et al., *Design2Code*, NAACL 2025, arXiv:2403.03163 | LU | Les modèles ratent surtout la mise en page fine → **fidélité mesurée** (SSIM recomposition, SSIM de fin, écart en px). |
| *Vision-Guided Iterative Refinement* arXiv:2604.05839 ; *UI2Code^N* arXiv:2511.08195 | EXTRAIT | Rendre → critiquer → corriger comme paradigme. |
| Lasseter 1987, SIGGRAPH 21(4) DOI 10.1145/37402.37407 ; Thesen 2020, *Animation* 15(3) | EXTRAIT | Timing, anticipation, mise en scène, accélérations → **table « Règles de mouvement »**. |

## Outils

| Source | Statut | Décision |
|---|---|---|
| webflow.com/blog/gsap-becomes-free ; gsap.com/docs/v3/GSAP/Timeline | LU / EXTRAIT | GSAP gratuit, y compris en usage commercial ; `seek(t)` déterministe → moteur retenu. |
| github.com/remotion-dev/remotion LICENSE ; remotion.dev/docs/license/faq | LU | Licence BUSL, payante à partir de 4 personnes → écarté par défaut. |
| github.com/tungs/timecut | LU | Horloge virtuelle par réécriture de `Date`/rAF → inutile avec `window.rendu(t)` explicite. |
| github.com/motion-canvas/motion-canvas ; Revideo | LU / EXTRAIT | Peu présents dans les données d'entraînement des LLM → écartés. |
| developer.apple.com … VNGenerateForegroundInstanceMaskRequest | LU | Détourage natif macOS 14+ → vision.swift (**MESURÉ** : 20 s, sujets propres sur 3 affiches). |
| github.com/danielgatis/rembg · github.com/ZhengPeng7/BiRefNet · github.com/advimman/lama · github.com/visioncortex/vtracer · potrace (brew) | LU / EXTRAIT | Non nécessaires ; lourds ou soumis à des licences. |
| github.com/microsoft/playwright/issues/35200 ; CDP `beginFrame` | EXTRAIT | `beginFrame` n'est fiable que sous Linux → `page.screenshot` + polices attendues. |
| trac.ffmpeg.org/wiki/Encode/H.264 | EXTRAIT | libx264, CRF 18, preset slow, yuv420p, +faststart. |

## Mesures faites en construisant le skill

- Essai de référence **sans skill** (affiche d'événement) : l'agent a animé l'image plate (Ken Burns et incrustations), sans découpage en calques et sans mesure de fidélité, en 13 min.
- Découpage : SSIM de recomposition 0,925 → 0,957 grâce au 2e passage (trous en forme de glyphes au lieu de boîtes) ; 0,938 sur l'affiche de l'exemple en extrayant moins.
- Rendu : 240 images en 1080x1350 en 44 s ; dernière image rendue = affiche (SSIM 1,000 avant encodage ; 0,952 après, pour un plafond de compression de 0,943).
