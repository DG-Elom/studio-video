# Privacy policy

Studio vidéo is a Claude Code plugin: two skills and scripts that run on your Mac. Its publisher (DG-Elom) runs no server and receives nothing from it: no account, no telemetry, no analytics.

Last updated: 27 September 2026.

## What stays on your Mac

- `motion-affiche` reads the poster you point it to, analyses it locally with Apple Vision (text and subject masks), renders the animation in headless Chrome and writes the frames, contact sheets and final MP4 in the task's project folder. Posters often carry names and addresses; they stay in that folder.
- `tutoriel-video` opens the web app you name in a Chrome profile kept in `<project>/profile/` and writes in the project folder the narration, voice files, subtitles, MP4 and every recorded frame (`<demo>/frames/*.jpg`, full-size screenshots of the app). You log in yourself; Claude never types credentials. The profile keeps your app session until you delete it. Film a demo environment with fictitious data.
- The animation scene is served to Chrome from the project folder under `http://scene.local/`, an address the render script answers itself: it never reaches the network.

Apart from its own working files, which it replaces on each run (render segments, recorded frames, control stills), the plugin deletes nothing: delete the project folder to erase all of it (`motion-affiche` works in a temporary folder that macOS may also clear).

## What leaves your Mac

| Destination | What is sent | When |
|---|---|---|
| `api.elevenlabs.io` | the narration text and your ElevenLabs API key | `tutoriel-video`, voice-over generation |
| `cdn.jsdelivr.net` | a request for the GSAP library | `motion-affiche`, rendering |
| Google Fonts (`fonts.googleapis.com`, font files from `fonts.gstatic.com`) | requests for web fonts | `motion-affiche`, rendering |
| the web app you film | what your browser normally sends it | `tutoriel-video`, filming |

Your poster is not uploaded. Each service applies its own privacy policy; the ElevenLabs request runs under your own ElevenLabs account.

As in any Claude Code session, what Claude reads to do the work (the poster, the narration, the contact sheets it checks) is processed by Anthropic under your Claude account's terms.

## Your ElevenLabs key

You store the key yourself in the macOS Keychain (see the README). `skills/tutoriel-video/scripts/tts.py` reads it when it runs and sends it only to `api.elevenlabs.io`, the service that issued it. The key is never written to a file or printed, and the skills never have Claude read it.

## Contact

Open an issue: https://github.com/DG-Elom/studio-video/issues
