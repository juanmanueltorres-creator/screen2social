# screen2social

Local-first automation pipeline that turns screen recordings into social-ready media packages using Python, FFmpeg, and local OBS WebSocket control — no paid APIs required.

## Current capabilities

### V0.1 — media package

```text
recording
  -> linkedin.mp4
  -> thumbnail.png
  -> metadata.json
```

### V0.2 — local OBS control

```text
screen2social status
screen2social record
screen2social stop
```

V0.2 controls recording only. `stop` returns the OBS file path; processing remains a separate explicit command. Real Windows/OBS validation is required before V0.2 is merged.

## Requirements

- Python 3.11+
- FFmpeg, with both `ffmpeg` and `ffprobe` available on `PATH`
- OBS Studio 28+ for V0.2 OBS control
- Windows is the primary local environment

No social-network API keys, cloud services, paid APIs, database, or publishing credentials are required.

## Setup on Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
screen2social doctor
```

A healthy media setup reports the local paths for `ffmpeg` and `ffprobe`.

## OBS WebSocket setup on Windows

Screen2Social V0.2 targets OBS Studio 28+ / obs-websocket 5.x.

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

`.env.example` is documentation only. Screen2Social does not automatically load `.env` files in V0.2, and the OBS password is never accepted as a CLI argument.

### Capture smoke flow

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

Automatic stop-and-process chaining is intentionally deferred until this real OBS path flow is validated.

## Process a recording

```powershell
screen2social process "C:\path\to\demo.mkv"
```

By default the package is created under `ready/`:

```text
ready/demo/
├── linkedin.mp4
├── thumbnail.png
└── metadata.json
```

You can choose another output root:

```powershell
screen2social process "C:\path\to\demo.mkv" --ready-dir "C:\content\ready"
```

### Safety behavior

- The source recording is never overwritten or edited.
- An existing `ready/<slug>/` package is never overwritten; the command fails with `OUTPUT_EXISTS`.
- Partial output created by a failed processing run is removed.
- Local recordings under `inbox/` and generated assets under `ready/` are ignored by Git.
- OBS WebSocket defaults to `localhost:4455`; Screen2Social does not configure public exposure, tunnels, or port forwarding.
- OBS authentication is required by the V0.2 configuration contract.

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

`metadata.json` records source/output duration, dimensions, codecs, processing timestamp, pipeline steps, warnings, and pipeline version.

## Development

```powershell
python -m pytest -v
```

The media integration suite generates temporary synthetic media with FFmpeg. OBS integration tests use fake clients; GitHub Actions does not require a real OBS instance.

## Roadmap

- **V0.1** — media vertical slice: process, LinkedIn preset, thumbnail, metadata, doctor, CI ✅
- **V0.2** — OBS WebSocket status / record / stop: implemented on feature branch; real Windows smoke pending
- **V0.3** — `post.md`, templates, social package naming
- **V0.4** — optional local transcription and silence editing
- **V1** — validated GeoPlatform → Screen2Social → manual LinkedIn workflow
- **V1.1+** — vertical presets only after real usage proves the need
- **V2** — evaluate Postiz before building direct social-network integrations

## Explicitly deferred from V0.2

Automatic `stop -> process`, scene switching, pause/resume, streaming control, Whisper/subtitles, Auto-Editor, `post.md`, vertical presets, social APIs, browser automation, Postiz, schedulers, GUI, backend, and database remain outside V0.2.

## License

MIT.
