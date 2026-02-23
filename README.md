# KG-YT Downloader

![Version](https://img.shields.io/badge/version-1.0.0-red?style=flat-square)
![Platform](https://img.shields.io/badge/platform-Windows-blue?style=flat-square&logo=windows)
![Python](https://img.shields.io/badge/Python-3.8%2B-yellow?style=flat-square&logo=python)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
![Powered by yt-dlp](https://img.shields.io/badge/powered%20by-yt--dlp-ff0000?style=flat-square)
![Built with tkinter](https://img.shields.io/badge/GUI-tkinter-lightgrey?style=flat-square)

A clean, self-contained Windows desktop app for downloading YouTube videos as **MP4** or **MP3**. No installation required — just download and run the `.exe`.

---

## Features

- Download any YouTube video as **MP4** (video) or **MP3** (audio)
- Choose your save location with a folder picker
- Live console output showing real-time download progress
- Right-click context menu on the URL field (cut, copy, paste, select all, clear)
- About page with version info and GitHub link
- Custom app icon
- Zero dependencies for end users — everything bundled into one `.exe`

---

## Download

Head to the [Releases](https://github.com/ToadOak/kg-yt-downloader/releases) page and grab the latest `KG-YT-Downloader.exe`.

No Python, no installs, no setup. Just run it.

---

## Usage

1. Paste a YouTube URL into the input box
2. Select **MP4** or **MP3** from the dropdown
3. Click **Download**
4. Choose where to save the file
5. Watch the console for live progress

---

## Building from Source

If you'd like to build the `.exe` yourself:

**Requirements:** Python 3.8+ and pip installed on Windows.

1. Clone this repo
```
git clone https://github.com/ToadOak/kg-yt-downloader.git
cd kg-yt-downloader
```

2. Place your `icon.ico` in the same folder as `build.bat`

3. Run the build script
```
build.bat
```

The script will automatically download `yt-dlp.exe` and `ffmpeg.exe`, then use PyInstaller to bundle everything into `dist\KG-YT-Downloader.exe`.

---

## Tech Stack

| Component | Purpose |
|-----------|---------|
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | YouTube downloading engine |
| [ffmpeg](https://ffmpeg.org) | Audio/video processing & merging |
| Python + tkinter | GUI framework |
| [PyInstaller](https://pyinstaller.org) | Bundling into standalone `.exe` |

---

## Disclaimer

This tool is intended for **personal use only**. Please respect content creators and YouTube's [Terms of Service](https://www.youtube.com/t/terms). Do not use this app to download copyrighted content without permission.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  Made by <a href="https://github.com/ToadOak">ToadOak</a>
</p>
