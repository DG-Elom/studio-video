---
name: tutoriel-video
description: >-
  Produce a narrated video tutorial of a web app (product demo, user guide, screencast): ElevenLabs
  voice-over first, Playwright gestures synced to the voice, title bars, burned-in and .srt
  subtitles, ffmpeg edit, contact-sheet check. Produire un tutoriel vidéo d'une application web
  (démo produit, guide utilisateur, screencast commenté) : voix off ElevenLabs, gestes calés sur la
  voix, sous-titres, montage ffmpeg. Utiliser dès qu'on demande un tuto, une vidéo de
  démonstration, un screencast ou une « démo filmée », même sans dire « skill ».
---

# Tutoriel vidéo « voix d'abord »

Principe : on écrit et on synthétise la **voix d'abord**, puis le tournage déclenche chaque geste à l'instant où la voix le nomme. L'inverse (filmer puis commenter) donne toujours des décalages.

Scripts : `T=${CLAUDE_SKILL_DIR}/scripts` · modèles : `${CLAUDE_SKILL_DIR}/templates/` · spécificités d'une app : `<projet>/app.md` (dans le projet, jamais dans le skill : il est remplacé à chaque mise à jour).

Dépendances : Python 3 + `playwright` (canal Chrome), `ffmpeg`/`ffprobe`, `Pillow`, clé ElevenLabs dans le trousseau macOS (service `elevenlabs-api-key`), rangée par l'utilisateur lui-même : `security add-generic-password -s elevenlabs-api-key -a "$USER" -w` (clé demandée au clavier, jamais passée en argument).

## Arborescence d'un projet

Dans un dossier temporaire propre à la tâche (scratchpad) :

```
<projet>/tuto.json          # base_url, auth_check, dest, voix… (templates/tuto.json)
<projet>/profile/           # profil navigateur CONNECTÉ : sensible, jamais copié ni livré
<projet>/<démo>/narration.txt, scene.py   (templates/)
          → cues.json, voix/, frames/, marks.json, montage/, planche.jpg  (générés)
```

## Déroulé

1. **Cadrer** : public, parcours exact, environnement. Toujours un environnement de **dev/démo**, jamais la prod sans accord explicite. Données fictives mais crédibles (aucun client réel).
2. **Repérer** l'UI en navigateur (sans filmer) : sélecteurs, textes de chargement, durées des traitements, fonctions qui échouent (à ne pas filmer). Consigner dans `<projet>/app.md`.
3. **Connexion** : `python3 $T/login.py <projet>` ouvre un Chrome visible ; **l'utilisateur se connecte lui-même**. L'agent ne saisit jamais d'identifiant ni de mot de passe.
4. **Narration** (`narration.txt`) :
   - `## <id> | <Titre>` ouvre une séquence avec bandeau ; `## <id>` sans titre ; `## <id> ^` = sous-titres en haut (résultat affiché en bas d'écran).
   - `{n}` juste **avant** le mot qui nomme ce qu'on montre ; le geste `r.at(n)` part 0,35 s avant.
   - Phrases courtes, vocabulaire d'utilisateur. Les noms de l'UI anglaise restent en anglais.
5. **Scène** (`scene.py`, copié de `templates/` en remplaçant `__SCRIPTS__` par le chemin de `$T`) : `reset()` remet l'état de départ (restes des prises précédentes), attendre un texte qui prouve la page chargée, puis `r.start()` et, par séquence, `r.mark(id)` + `r.at(k)` + gestes (`point`, `click`, `drag`, `type`, `glide`), enfin `r.finish()`.
6. **Répétition à blanc** (sans `cues.json`, gratuite) : `python3 <démo>/scene.py`, puis `python3 $T/assemble.py <démo> <nom>-essai` (piste muette) et `$T/controle.py`. Corriger les sélecteurs avant de payer la voix.
7. **Voix** : `python3 $T/tts.py <démo>` (toutes) ou `$T/tts.py <démo> 05-x 06-y` (seulement celles-ci). Coût : ~1 crédit par caractère.
8. **Tournage** : `python3 <démo>/scene.py`. Lire les lignes `retard X s` : au-delà de ~1 s, allonger la phrase, accélérer le geste (`insert_text` via `type(..., delay=0)`) ou scinder la séquence.
9. **Montage** : `python3 $T/assemble.py <démo> <nom>` → `<dest>/<nom>.mp4` + `.srt`.
10. **Contrôle** : `python3 $T/controle.py <démo> <dest>/<nom>.mp4`, puis **lire** `planche.jpg` : à chaque repère, l'action nommée doit être visible. `ffprobe` : 1920x1080, audio, piste de sous-titres. Refaire les séquences fautives (voix ciblée + nouveau tournage).
11. **Livrer** vidéo + `.srt`, envoyer à l'utilisateur (SendUserFile si l'outil existe), puis **ménage** après validation (voir plus bas).

## Pièges (payés en vrai)

- `time.sleep` pendant le screencast **fige la vidéo** (l'API sync ne reçoit plus les images) : toujours `r.sleep()` / `page.wait_for_timeout`.
- Traitement de durée variable (IA, run) : **séquence de voix séparée**, marquée seulement quand le résultat est visible. Sélecteur `text=… >> visible=true` : un `get_by_text` seul peut trouver un texte caché.
- Filmer une page encore en chargement : attendre un texte qui n'apparaît qu'une fois chargée, + 1,5 s.
- Sous-titres qui cachent le résultat : `## id ^`.
- Montrer un terminal : `templates/terminal.html` (fenêtre factice) ; la commande est **réellement exécutée** par `subprocess` et sa vraie sortie injectée par `page.evaluate("s => sortie(s)", texte)`. `curl -sS` pour masquer la barre de progression.
- Secret visible à l'écran (URL de webhook, jeton) : le régénérer après le tournage et vérifier que l'ancien est refusé.
- Un appel de test sur l'environnement filmé laisse des traces (runs, conversations) : les signaler et les nettoyer.

## Ménage (après validation de l'utilisateur)

- Application : supprimer ce que les prises ont créé (par API ou UI), sans toucher aux ressources d'autres sessions ; relire la liste restante.
- Local : supprimer le dossier du projet (profil connecté compris).
- Si les scripts d'une démo doivent être gardés : les copier **sans** `profile/`, `frames/`, `voix/`, `montage/`, vérifier l'absence de secret, et documenter comment relancer.

## Contrôles de fin

Vidéo lue par `ffprobe` + planche relue après le dernier tournage, durées annoncées mesurées, ménage fait ou conservation motivée. Une vidéo non regardée (au moins par sa planche) n'est pas livrable.
