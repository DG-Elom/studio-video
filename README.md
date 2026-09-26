# Studio vidéo

Two video workflows for Claude Code, each ending with a measured check of the final file.

| Skill | Ask Claude for… | Output |
|---|---|---|
| `motion-affiche` | "turn this poster into an animated teaser", « fais bouger cette affiche » | MP4 motion-design teaser (e.g. 1080x1350, 15 s): each element of the poster gets its own scene, the poster itself lands only at the end |
| `tutoriel-video` | "make a narrated video tutorial of our web app", « un tuto vidéo de notre appli » | 1920x1080 MP4 with voice-over, title bars, burned-in and `.srt` subtitles |

Skill instructions are written in French; Claude answers in your language.

## Requirements

Claude Code on **macOS 14 or later** (the scripts rely on macOS-only tools):

- Python 3 with `Pillow` and `playwright`
- Google Chrome in `/Applications`
- `ffmpeg` and `ffprobe`
- Xcode Command Line Tools (`swift`, used for Apple Vision in `motion-affiche`)
- `tutoriel-video` only: an ElevenLabs API key stored in the macOS Keychain by you, never in a file:
  `security add-generic-password -s elevenlabs-api-key -a "$USER" -w` (you type the key at the prompt).

## What runs, what leaves your machine

- Rendering is local: headless Chrome driven by Playwright, encoding by ffmpeg, in a project folder the skill creates for the task.
- `motion-affiche` loads GSAP 3.13 from `cdn.jsdelivr.net` and fonts from `fonts.googleapis.com` while rendering. Your poster is not uploaded.
- `tutoriel-video` sends the narration text to `api.elevenlabs.io` (text-to-speech, billed to your ElevenLabs account) and opens the web app you name in a Chrome profile stored in the project folder. **You log in yourself**; Claude never types credentials. Film a demo environment with fictitious data.
- No telemetry, no other network calls.

## Evals

```bash
claude plugin eval . --no-publish
```

Five cases under `evals/` check that each skill triggers on a natural request in French or English, that it does not trigger on AI-generated video requests, and that the key rules hold (storyboard before code, voice before filming, the user logs in themselves).

## License

MIT, see [LICENSE](LICENSE).
