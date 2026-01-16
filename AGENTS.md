# Repository Guidelines

## Project Structure & Module Organization
This repository generates 9:16 vertical podcast videos from audio and cover art. Key paths:
- `main.py`: CLI workflow for batch or single-file processing.
- `app.py`: Flask web UI that uploads audio/cover and serves results.
- `input/audio/` and `input/cover/`: local source assets for CLI mode.
- `output/final/` and `output/temp/`: generated videos and intermediate files.
- `uploads/`: web uploads (temporary inputs).
- `static/`: web UI assets (e.g., `static/index.html`).

## Build, Test, and Development Commands
- `python3 -m venv venv && source venv/bin/activate`: create a local virtualenv.
- `pip install -r requirements.txt`: install Python dependencies.
- `python3 main.py`: process all audio under `input/audio/`.
- `python3 main.py episode01.mp3 cover.jpg`: process a single item.
- `python3 app.py`: run the web server (default: http://localhost:5001).
- `ffmpeg -version`: verify FFmpeg is installed (required for video generation).

## Coding Style & Naming Conventions
- Python uses 4-space indentation and `snake_case` for functions/variables.
- Prefer `pathlib.Path` for filesystem paths as seen in `main.py` and `app.py`.
- Keep web assets in `static/` and avoid hardcoding OS-specific paths.
- No formatter is enforced; keep diffs minimal and consistent with existing style.

## Testing Guidelines
- No automated tests are present. Validate changes by running:
  - CLI: `python3 main.py` with sample files in `input/`.
  - Web: `python3 app.py` and upload an audio + cover file.
- If adding tests, document how to run them in this file.

## Commit & Pull Request Guidelines
- Recent commits are short and descriptive; one uses Conventional Commits (`feat:`).
- Prefer concise, action-based messages (Chinese or English is fine).
- For PRs, include: a brief summary, testing performed, and screenshots for UI changes.

## Security & Configuration Notes
- FFmpeg must be installed locally (e.g., `brew install ffmpeg` on macOS).
- Generated media in `output/` and uploads in `uploads/` should stay out of git.
