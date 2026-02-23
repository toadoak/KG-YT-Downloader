# Changelog

All notable changes to **KG-YT Downloader** will be documented here.

This project follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) formatting and [Semantic Versioning](https://semver.org/).

---

## [2.0.0] — 2026-02-23

![Status](https://img.shields.io/badge/status-stable-brightgreen?style=flat-square)
![Type](https://img.shields.io/badge/release-major-red?style=flat-square)

### Added
- **Download queue** — add multiple URLs and process them sequentially, with per-item status (Pending / Downloading / Done / Error)
- **Video quality selector** — choose Best, 1080p, 720p, 480p, or 360p for MP4 downloads
- **Filename/title preview** — fetches video title in the background after pasting a URL and displays it before adding to queue
- **Open output folder** — right-click a history entry to open its containing folder in Explorer
- **URL validation** — inline warning if the URL doesn't match a recognised YouTube format
- **Auto-update yt-dlp** — toolbar button runs `yt-dlp -U` and streams output to the console
- **Friendly error messages** — private, age-restricted, region-blocked and membership videos show plain-English errors
- **Persistent save folder** — last used folder saved to config and pre-filled on next launch
- **Embed thumbnail** — checkbox to embed video thumbnail as album art in MP3 files
- **Embed metadata** — checkbox to write title, uploader and year as ID3/MP4 tags
- **Playlist mode toggle** — checkbox to intentionally download a full playlist (default off)
- **Download history** — logs every attempt with title, format, date, status and file path
- **Tooltips** — hover hints on toolbar buttons and checkboxes
- **Queue right-click menu** — remove individual pending items from the queue

### Changed
- Save location is now a persistent folder field always visible in the UI
- Progress bar and console reflect per-item and overall queue state
- App version bumped to 2.0.0

---

## [1.0.0] — 2026-02-22

![Status](https://img.shields.io/badge/status-stable-brightgreen?style=flat-square)
![Type](https://img.shields.io/badge/release-initial-blue?style=flat-square)

### Added
- Initial release of KG-YT Downloader
- YouTube URL input field with right-click context menu (cut, copy, paste, select all, clear)
- Format selector dropdown — MP4 (video) or MP3 (audio)
- Folder picker dialog to choose save location before download
- Live console output panel streaming real-time yt-dlp progress
- Progress bar (indeterminate) active during download
- Status label showing current state (Ready / Downloading / Complete / Error)
- About window with version info, tech stack, ToS disclaimer, and GitHub link
- Custom `.ico` icon applied to main window and About window
- Fully self-contained `.exe` — yt-dlp and ffmpeg bundled via PyInstaller
- `build.bat` one-click build script for Windows

---

<!-- 
Template for future releases:

## [X.Y.Z] — YYYY-MM-DD

![Status](https://img.shields.io/badge/status-stable-brightgreen?style=flat-square)
![Type](https://img.shields.io/badge/release-feature-orange?style=flat-square)

### Added
- 

### Changed
- 

### Fixed
- 

### Removed
- 
-->