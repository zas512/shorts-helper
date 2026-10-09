# Shorts Helper

This workspace generates voiceover audio with the existing ElevenLabs Node.js tool and assembles five numbered video/audio pairs into a captioned vertical video.

## Requirements

- Python 3.10 or newer
- The project-local FFmpeg bundle (installed by `setup_ffmpeg.ps1`)
- Node.js and an ElevenLabs API key to generate audio with `generate.js`

The Python assembler uses only the standard library. `requirements.txt` stays empty; FFmpeg is downloaded into the project-local `.tools/` folder, not installed system-wide.

## Python Setup

Create the local environment from PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If the `py` launcher is unavailable, use the path to your installed Python executable in the first command. VS Code is configured to use `.venv` automatically.

Install the video tools into this project:

```powershell
.\setup_ffmpeg.ps1
```

The setup script verifies the downloaded archive checksum. The bundled FFmpeg build includes subtitle support required for captions.

## Prepare Media

Place the five source clips in `videos/`, named `1.mp4` through `5.mp4` (MOV, MKV, and WebM are also supported). Keep five non-empty transcript lines in `script.txt`; line 1 captions scene 1, and so on. Each caption displays one word at a time.

Generate the matching numbered MP3 voiceovers using the existing Node tool:

```powershell
npm start
```

It saves MP3 files under `output/<script-name>/`. The Python tool can find them automatically if there is only one matching set under `output/`. If multiple generated sets exist, select the correct folder explicitly.

## Assemble

With the virtual environment active:

```powershell
python assemble.py --audio-dir output/<script-name>
```

Or specify all paths:

```powershell
python assemble.py --video-dir videos --audio-dir output/<script-name> --transcript script.txt --output final_video.mp4
```

The output is 1080x1920 MP4. Each scene runs for the duration of its audio track; word caption timing is estimated from word length and punctuation, not aligned by speech recognition. Source video audio is replaced by the matching audio track.

## Test

```powershell
python -m unittest discover -s tests -v
```