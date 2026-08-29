# screen2social

Local-first automation pipeline that turns screen recordings into social-ready media packages using Python, FFmpeg, local OBS WebSocket control, and optional local transcription — no paid APIs required.

## Current capabilities

### V0.1 — media package ✅

```text
recording
  -> linkedin.mp4
  -> thumbnail.png
  -> metadata.json
```

### V0.2 — local OBS control ✅

```text
screen2social status
screen2social record
screen2social stop
```

V0.2 controls recording only. `stop` returns the OBS file path; processing remains a separate explicit command. The OBS WebSocket flow was validated on real Windows + OBS, including authentication, recording, status, stop, the returned MKV path, and end-to-end processing.

### V0.3 — deterministic social package ✅

`screen2social process` adds deterministic, editable `post.md` to the media package:

```text
ready/demo/
├── linkedin.mp4
├── thumbnail.png
├── metadata.json
└── post.md
```

`post.md` contains:

- the human-readable source filename as the title;
- a manual post-body placeholder;
- the canonical `linkedin.mp4` and `thumbnail.png` asset names;
- a manual LinkedIn publishing checklist.

V0.3 does not generate copy with AI and does not publish anything automatically.

### V0.4 — optional local transcription

V0.4 adds an opt-in transcription path while preserving the normal V0.3 package when the flag is omitted:

```powershell
screen2social process "C:\path\to\demo.mkv" --transcribe
```

A successful transcription-enabled package contains:

```text
ready/demo/
├── linkedin.mp4
├── thumbnail.png
├── metadata.json
├── post.md
├── transcript.txt
└── transcript.srt
```

Transcription uses an externally installed local `whisper.cpp` `whisper-cli` executable and a local multilingual GGML model. Screen2Social does not download, install, update, or manage either resource.

## Requirements

Base pipeline:

- Python 3.11+
- FFmpeg, with both `ffmpeg` and `ffprobe` available on `PATH`
- OBS Studio 28+ for OBS control
- Windows is the primary local environment

Optional V0.4 transcription additionally requires:

- a local `whisper.cpp` `whisper-cli` executable;
- a local multilingual GGML Whisper model such as `ggml-base.bin`.

No social-network API keys, cloud services, paid APIs, database, publishing credentials, or hosted transcription API are required.

## Setup on Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
screen2social doctor
```

A healthy base media setup reports the local paths for `ffmpeg` and `ffprobe`.

`screen2social doctor` intentionally validates only mandatory FFmpeg/ffprobe dependencies. Optional Whisper configuration is checked only when `--transcribe` is requested.

## OBS WebSocket setup on Windows

Screen2Social targets OBS Studio 28+ / obs-websocket 5.x.

1. Open OBS Studio.
2. Open **Tools -> WebSocket Server Settings**.
3. Enable the WebSocket server.
4. Keep the server local; the default Screen2Social endpoint is `localhost:4455`.
5. Enable authentication and set a password.
6. In the same PowerShell session where you run Screen2Social, set:

```powershell
$env:SCREEN2SOCIAL_OBS_PASSWORD = "<your OBS WebSocket password>"
$env:SCREEN2SOCIAL_OBS_HOST = "localhost"
$env:SCREEN2SOCIAL_OBS_PORT = "4455"
$env:SCREEN2SOCIAL_OBS_TIMEOUT_SECONDS = "5.0"
```

`.env.example` is documentation only. Screen2Social does not automatically load `.env` files, and the OBS password is never accepted as a CLI argument.

### Capture flow

```powershell
screen2social status
screen2social record
# record a few seconds in OBS
screen2social status
screen2social stop
```

`stop` prints:

```text
RECORDING: stopped
FILE: C:\path\to\recording.mkv
```

Confirm that file exists, then process it separately:

```powershell
Test-Path "C:\path\to\recording.mkv"
screen2social process "C:\path\to\recording.mkv"
```

Automatic stop-and-process chaining remains intentionally deferred.

## Process a recording

```powershell
screen2social process "C:\path\to\demo.mkv"
```

By default the package is created under `ready/`:

```text
ready/demo/
├── linkedin.mp4
├── thumbnail.png
├── metadata.json
└── post.md
```

You can choose another output root:

```powershell
screen2social process "C:\path\to\demo.mkv" --ready-dir "C:\content\ready"
```

### Optional local transcription

First install `whisper.cpp` and a multilingual GGML model independently of Screen2Social. Then point the current PowerShell session at those already-existing local resources:

```powershell
$env:SCREEN2SOCIAL_WHISPER_CLI = "C:\tools\whisper.cpp\whisper-cli.exe"
$env:SCREEN2SOCIAL_WHISPER_MODEL = "C:\tools\whisper.cpp\models\ggml-base.bin"
screen2social process "C:\videos\demo.mkv" --transcribe
```

V0.4 transcription behavior is deliberately narrow:

- transcription is opt-in; a normal `process` command never requires or inspects Whisper configuration;
- language is fixed to `auto`;
- `whisper-cli` generates both `transcript.txt` and `transcript.srt`;
- FFmpeg creates a temporary mono 16 kHz PCM WAV for transcription and Screen2Social removes it before successful completion;
- the original recording is never overwritten, edited, or deleted;
- if transcription was explicitly requested and fails, the partial package is removed and no `READY:` result is delivered;
- no model or executable is downloaded automatically;
- no subtitles are burned into the video.

### Safety behavior

- The source recording is never overwritten or edited.
- An existing `ready/<slug>/` package is never overwritten; the command fails with `OUTPUT_EXISTS`.
- Partial output created by a failed processing run is removed.
- Requested transcription is fail-closed: both transcript files must exist before the package is considered ready.
- Local recordings under `inbox/` and generated assets under `ready/` are ignored by Git.
- OBS WebSocket defaults to `localhost:4455`; Screen2Social does not configure public exposure, tunnels, or port forwarding.
- OBS authentication is required by the configuration contract.

## Output preset

`linkedin.mp4` is rendered as:

- MP4 container
- H.264 video
- AAC audio when the source contains audio
- `yuv420p`
- 1920×1080 16:9 canvas
- original aspect ratio preserved with padding where needed
- fast-start metadata for web playback

`thumbnail.png` uses a deterministic frame: the middle of short clips, capped at five seconds for longer clips.

`metadata.json` records source/output duration, dimensions, codecs, processing timestamp, pipeline steps, warnings, and pipeline version. When transcription succeeds, metadata additionally records the `transcription` step and the portable TXT/SRT artifact names, not machine-specific Whisper/model paths.

`post.md` is deterministic UTF-8 Markdown intended to be edited by a human before manual publication.

`transcript.txt` and `transcript.srt` are emitted by `whisper-cli` only when `--transcribe` is requested. The SRT preserves timed segments for future subtitle workflows without modifying `linkedin.mp4`.

## Development

```powershell
python -m pytest -v
```

The media integration suite generates temporary synthetic media with FFmpeg. OBS integration tests use fake clients. Transcription tests fake the Whisper subprocess boundary and do not download or execute a real model in GitHub Actions.

## Roadmap

- **V0.1** — media vertical slice: process, LinkedIn preset, thumbnail, metadata, doctor, CI ✅
- **V0.2** — OBS WebSocket status / record / stop ✅
- **V0.3** — `post.md` + deterministic social package ✅
- **V0.4** — optional local TXT + SRT transcription with `whisper.cpp`
- **V0.5+** — evaluate silence editing only after real transcription usage proves the need
- **V1** — validated GeoPlatform → Screen2Social → manual LinkedIn workflow
- **V1.1+** — vertical presets only after real usage proves the need
- **V2** — evaluate Postiz before building direct social-network integrations

## Explicitly deferred

Automatic `stop -> process`, scene switching, pause/resume, streaming control, silence cutting, burned-in subtitles, translation, configurable template files, vertical presets, AI summarization/post generation, model downloading, GPU/CUDA tuning, diarization, standalone transcription commands, social APIs, browser automation, Postiz, schedulers, GUI, backend, and database remain outside V0.4.

## License

MIT.
