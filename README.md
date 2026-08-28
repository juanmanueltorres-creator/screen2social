# screen2social

Local-first automation pipeline that turns screen recordings into social-ready media packages using Python and FFmpeg — no paid APIs required.

## V0.1

Current workflow:

```text
recording
  -> linkedin.mp4
  -> thumbnail.png
  -> metadata.json
```

The V0.1 pipeline is deliberately small: it processes an existing local recording. OBS control, subtitles, post copy, vertical presets, scheduling, and auto-publishing are later gates.

## Requirements

- Python 3.11+
- FFmpeg, with both `ffmpeg` and `ffprobe` available on `PATH`
- Windows is the primary local environment for V0.1

No API keys, cloud services, paid APIs, database, or social-media credentials are required.

## Setup on Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
screen2social doctor
```

A healthy setup reports the local paths for `ffmpeg` and `ffprobe`.

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

The integration suite generates temporary synthetic media with FFmpeg. Real recordings are not needed for tests and are not committed.

## Roadmap

- **V0.1** — media vertical slice: process, LinkedIn preset, thumbnail, metadata, doctor, CI
- **V0.2** — OBS WebSocket status / record / stop
- **V0.3** — `post.md`, templates, social package naming
- **V0.4** — optional local transcription and silence editing
- **V1** — validated GeoPlatform → Screen2Social → manual LinkedIn workflow
- **V1.1+** — vertical presets only after real usage proves the need
- **V2** — evaluate Postiz before building direct social-network integrations

## License

MIT.
