# Screen2Social

> **Record in OBS. Turn the recording into a ready-to-review social package — locally.**

Screen2Social connects local OBS capture with a deterministic FFmpeg pipeline that prepares a screen recording for manual social publishing.

It can control recording and configured OBS scenes, render a LinkedIn-ready video, create a thumbnail and metadata, generate an editable `post.md`, and optionally add local TXT/SRT transcription through `whisper.cpp`.

No source recording is uploaded by Screen2Social, and nothing is published automatically.

> **Automate the boring media plumbing. Keep the publishing decision human.**

---

## Typical workflow

```text
OBS
 ↓
recording.mkv
 ↓
screen2social process
 ↓
ready/demo/
├── linkedin.mp4
├── thumbnail.png
├── metadata.json
├── post.md
└── transcript.*   optional
 ↓
human review
 ↓
manual publish
```

The capture and processing steps stay explicit. Stopping an OBS recording does not silently trigger transcoding or publication.

---

## What it does

### Local OBS control

```powershell
screen2social status
screen2social record
screen2social scene capture
screen2social scene studio
screen2social scene toggle
screen2social stop
```

OBS control targets the local OBS WebSocket interface. Recording status, start/stop and configured scene switching remain separate commands so the operator can see exactly what action is being requested.

### Deterministic media package

Process an existing recording:

```powershell
screen2social process "C:\path\to\demo.mkv"
```

A successful run creates:

```text
ready/demo/
├── linkedin.mp4
├── thumbnail.png
├── metadata.json
└── post.md
```

`linkedin.mp4` uses a 1920×1080 H.264/AAC-friendly social preset while preserving the source aspect ratio with padding where necessary.

`thumbnail.png` is generated from a deterministic frame.

`metadata.json` records source/output media properties, pipeline steps, warnings and pipeline version.

`post.md` is deterministic UTF-8 Markdown with the asset names, a human-editable post body placeholder and a manual publishing checklist.

### Optional local transcription

If `whisper.cpp` and a multilingual GGML model are already installed locally:

```powershell
screen2social process "C:\path\to\demo.mkv" --transcribe
```

The package additionally contains:

```text
transcript.txt
transcript.srt
```

Screen2Social does not download or manage Whisper models. Transcription is opt-in, uses the local executable/model paths supplied by the operator, and does not burn subtitles into the video.

---

## Safety by design

The pipeline is intentionally conservative:

```text
source recording != disposable input
processing success != publishing approval
local transcription != cloud upload
generated post template != finished copy
```

Important behavior:

- source recordings are never overwritten, edited or deleted;
- an existing `ready/<slug>/` package is never silently replaced;
- partial packages are cleaned up when processing fails;
- requested transcription fails closed if the required transcript artifacts are not produced;
- OBS authentication is configured outside the CLI;
- the OBS endpoint defaults to local use rather than public exposure;
- Screen2Social does not store social-network credentials;
- Screen2Social does not auto-publish, schedule or browser-automate posts.

---

## Requirements

Base workflow:

- Python 3.11+
- FFmpeg with `ffmpeg` and `ffprobe` available on `PATH`
- OBS Studio 28+ for OBS control

Windows is the primary local environment used by the project.

Optional transcription additionally requires:

- a local `whisper.cpp` `whisper-cli` executable;
- a local multilingual GGML Whisper model.

No paid API, hosted transcription service, database or backend is required.

---

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
screen2social doctor
```

`doctor` checks the mandatory FFmpeg/ffprobe toolchain. Optional Whisper resources are only relevant when `--transcribe` is requested.

---

## OBS setup

Screen2Social uses OBS WebSocket 5.x / OBS Studio 28+.

1. Open **OBS Studio → Tools → WebSocket Server Settings**.
2. Enable the WebSocket server.
3. Keep the endpoint local unless you have a separate reason not to.
4. Enable authentication.
5. Provide the OBS password through the environment used to launch Screen2Social.

Example PowerShell session:

```powershell
$env:SCREEN2SOCIAL_OBS_PASSWORD = "<your OBS WebSocket password>"
$env:SCREEN2SOCIAL_OBS_HOST = "localhost"
$env:SCREEN2SOCIAL_OBS_PORT = "4455"
$env:SCREEN2SOCIAL_OBS_TIMEOUT_SECONDS = "5.0"
```

The password is not accepted as a CLI argument.

A minimal recording flow is:

```powershell
screen2social status
screen2social record
screen2social scene capture
# record...
screen2social scene studio
screen2social stop
```

Then process the returned file explicitly:

```powershell
screen2social process "C:\path\to\recording.mkv"
```

---

## Optional transcription setup

Install `whisper.cpp` and a multilingual GGML model independently, then point Screen2Social at those local resources:

```powershell
$env:SCREEN2SOCIAL_WHISPER_CLI = "C:\tools\whisper.cpp\whisper-cli.exe"
$env:SCREEN2SOCIAL_WHISPER_MODEL = "C:\tools\whisper.cpp\models\ggml-base.bin"

screen2social process "C:\videos\demo.mkv" --transcribe
```

During transcription FFmpeg prepares a temporary mono 16 kHz PCM WAV. That temporary artifact is removed before successful package completion.

---

## Architecture

```text
OBS WebSocket
     ↓
local recording
     ↓
FFmpeg / ffprobe
     ↓
package builder
 ┌───────────────┬──────────────┬───────────────┐
 ↓               ↓              ↓               ↓
video         thumbnail      metadata        post.md
                                    \
                                     └─ whisper.cpp (optional)
                                            ↓
                                      TXT + SRT
```

The boundaries are deliberately small: OBS controls capture, FFmpeg handles media transformation, `whisper.cpp` is an optional external transcription tool, and Screen2Social coordinates the local package without owning publication.

---

## Development

Run the test suite with:

```powershell
python -m pytest -v
```

The repository includes tests for media processing, output-package contracts, OBS command boundaries and optional transcription behavior. Synthetic media fixtures are generated with FFmpeg; external OBS and Whisper behavior is isolated behind testable boundaries rather than requiring real services for every automated test.

---

## Scope

Screen2Social is intentionally a small local utility, not a social-media management platform.

Currently outside the core workflow:

- automatic `stop → process` chaining;
- automatic publishing or scheduling;
- social-network APIs;
- browser automation;
- AI-generated post copy;
- automatic model downloads;
- silence cutting or aggressive automatic editing;
- burned-in subtitles;
- translation or diarization;
- GUI, backend or database;
- multi-user account management.

Future additions should earn their place through real workflow friction rather than turning the project into a generic content platform.

## License

MIT.
