@echo off
REM ============================================================
REM  KG-YT Downloader — one-click .exe builder
REM  Run this script once on your Windows machine.
REM  Output: dist\KG-YT-Downloader.exe
REM ============================================================

echo [1/5] Installing Python dependencies...
pip install pyinstaller yt-dlp
if errorlevel 1 (echo ERROR: pip failed & pause & exit /b 1)

echo.
echo [2/5] Downloading yt-dlp standalone binary...
curl -L "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe" -o yt-dlp.exe
if errorlevel 1 (echo ERROR: yt-dlp download failed & pause & exit /b 1)

echo.
echo [3/5] Downloading ffmpeg...
curl -L "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip" -o ffmpeg.zip
if errorlevel 1 (echo ERROR: ffmpeg download failed & pause & exit /b 1)

echo Extracting ffmpeg...
powershell -Command "Expand-Archive -Force ffmpeg.zip ."
for /r %%f in (ffmpeg.exe) do (
    if not "%%~dpf"=="%CD%\" copy "%%f" ffmpeg.exe >nul 2>&1
)
del ffmpeg.zip

echo.
echo [4/5] Building .exe with PyInstaller...
python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "KG-YT-Downloader" ^
    --add-binary "yt-dlp.exe;." ^
    --add-binary "ffmpeg.exe;." ^
    --add-data "icon.ico;." ^
    --icon "icon.ico" ^
    kg_yt_downloader.py

if errorlevel 1 (echo ERROR: PyInstaller build failed & pause & exit /b 1)

echo.
echo [5/5] Cleaning up...
del yt-dlp.exe
del ffmpeg.exe
rmdir /s /q build
del KG-YT-Downloader.spec

echo.
echo ============================================================
echo  SUCCESS! Your app is ready:
echo  dist\KG-YT-Downloader.exe
echo
echo  You can share this single .exe — no installation needed.
echo ============================================================
pause
