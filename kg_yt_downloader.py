"""
KG-YT Downloader — self-contained GUI application.
Bundled via PyInstaller. yt-dlp and ffmpeg are included in the package.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import sys
import subprocess
import webbrowser
import json
import re
import sqlite3
from datetime import datetime

APP_NAME   = "KG-YT Downloader"
APP_VER    = "2.0.0"
GITHUB_URL = "https://github.com/ToadOak"

CONFIG_FILE  = os.path.join(os.path.expanduser("~"), ".kg_yt_downloader.json")
HISTORY_FILE = os.path.join(os.path.expanduser("~"), ".kg_yt_history.db")

# ── Resolve bundled binary / resource paths ───────────────────────────────────
def _get_base_dir():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def _bin(name):
    exe = name + ".exe" if sys.platform == "win32" else name
    return os.path.join(_get_base_dir(), exe)

def _resource(name):
    return os.path.join(_get_base_dir(), name)

def _check_bins():
    missing = [_bin(b) for b in ("yt-dlp", "ffmpeg") if not os.path.isfile(_bin(b))]
    if missing:
        return "Required binaries not found:\n" + "\n".join(missing) + \
               "\n\nPlease rebuild using build.bat."
    return None

# ── Config ────────────────────────────────────────────────────────────────────
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_folder": "", "quality": "Best", "format": "mp4",
            "embed_thumbnail": True, "embed_metadata": True, "playlist_mode": False}

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass

# ── History DB ────────────────────────────────────────────────────────────────
def init_db():
    con = sqlite3.connect(HISTORY_FILE)
    con.execute("""CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT, url TEXT, fmt TEXT,
        save_path TEXT, date TEXT, status TEXT
    )""")
    con.commit()
    return con

def add_history(title, url, fmt, save_path, status):
    try:
        con = sqlite3.connect(HISTORY_FILE)
        con.execute("INSERT INTO history (title,url,fmt,save_path,date,status) VALUES (?,?,?,?,?,?)",
                    (title, url, fmt, save_path, datetime.now().strftime("%Y-%m-%d %H:%M"), status))
        con.commit()
        con.close()
    except Exception:
        pass

def get_history(limit=200):
    try:
        con = sqlite3.connect(HISTORY_FILE)
        rows = con.execute(
            "SELECT title,url,fmt,save_path,date,status FROM history ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        con.close()
        return rows
    except Exception:
        return []

def clear_history():
    try:
        con = sqlite3.connect(HISTORY_FILE)
        con.execute("DELETE FROM history")
        con.commit()
        con.close()
    except Exception:
        pass

# ── Theme ─────────────────────────────────────────────────────────────────────
T = {
    "bg":              "#f5f5f5",
    "fg":              "#1a1a1a",
    "entry_bg":        "#ffffff",
    "entry_fg":        "#1a1a1a",
    "btn_bg":          "#e00000",
    "btn_fg":          "#ffffff",
    "btn_hover":       "#b80000",
    "muted_btn_bg":    "#dddddd",
    "muted_btn_fg":    "#444444",
    "muted_btn_hover": "#cccccc",
    "frame_bg":        "#eeeeee",
    "status_fg":       "#666666",
    "progress_trough": "#dddddd",
    "border":          "#cccccc",
    "console_bg":      "#1a1a1a",
    "console_fg":      "#e0e0e0",
    "link_fg":         "#0066cc",
    "queue_bg":        "#ffffff",
    "queue_sel":       "#ffe0e0",
    "tag_done":        "#2e7d32",
    "tag_error":       "#c62828",
    "tag_pending":     "#888888",
    "tag_active":      "#e65100",
}

QUALITY_OPTIONS = ["Best", "1080p", "720p", "480p", "360p"]

QUALITY_FORMAT_MAP = {
    "Best":  "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
    "1080p": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]",
    "720p":  "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]",
    "480p":  "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]",
    "360p":  "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360]",
}

YT_RE = re.compile(
    r"^(https?://)?(www\.)?(youtube\.com/(watch\?|shorts/|embed/)|youtu\.be/).+", re.I
)

def is_valid_yt_url(url):
    return bool(YT_RE.match(url.strip()))

def friendly_error(stderr):
    if "Private video" in stderr:
        return "This video is private and cannot be downloaded."
    if "age" in stderr.lower() and "restricted" in stderr.lower():
        return "This video is age-restricted. Sign-in is required."
    if "not available in your country" in stderr.lower():
        return "This video is not available in your region."
    if "This live event will begin" in stderr:
        return "This is a scheduled livestream that hasn't started yet."
    if "This video is available to this channel" in stderr:
        return "This video requires a channel membership."
    return stderr[-400:] if stderr else "Unknown error."

def _set_icon(window):
    icon_path = _resource("icon.ico")
    if os.path.isfile(icon_path):
        try:
            window.iconbitmap(icon_path)
        except Exception:
            pass

# ── Tooltip ───────────────────────────────────────────────────────────────────
class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tw = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _=None):
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        self.tw.geometry(f"+{x}+{y}")
        tk.Label(self.tw, text=self.text, bg="#333333", fg="#ffffff",
                 font=("Helvetica", 8), padx=6, pady=3, relief="flat").pack()

    def hide(self, _=None):
        if self.tw:
            self.tw.destroy()
            self.tw = None

# ── History window ────────────────────────────────────────────────────────────
class HistoryWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Download History")
        self.geometry("700x400")
        self.configure(bg=T["bg"])
        self.transient(parent)
        _set_icon(self)

        top = tk.Frame(self, bg=T["bg"])
        top.pack(fill="x", padx=16, pady=(14, 6))
        tk.Label(top, text="Download History", font=("Helvetica", 13, "bold"),
                 bg=T["bg"], fg=T["fg"]).pack(side="left")
        tk.Button(top, text="Clear All", font=("Helvetica", 9),
                  bg=T["muted_btn_bg"], fg=T["muted_btn_fg"], relief="flat",
                  cursor="hand2", padx=8, pady=3,
                  command=self._clear).pack(side="right")

        cols = ("Title", "Format", "Date", "Status", "Path")
        frame = tk.Frame(self, bg=T["bg"])
        frame.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        style = ttk.Style()
        style.configure("History.Treeview", rowheight=22, font=("Helvetica", 9),
                         background=T["queue_bg"], fieldbackground=T["queue_bg"],
                         foreground=T["fg"])
        style.configure("History.Treeview.Heading", font=("Helvetica", 9, "bold"))

        self.tree = ttk.Treeview(frame, columns=cols, show="headings",
                                  style="History.Treeview", selectmode="browse")
        widths = [220, 55, 120, 60, 200]
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="w")

        self.tree.tag_configure("done",    foreground=T["tag_done"])
        self.tree.tag_configure("error",   foreground=T["tag_error"])
        self.tree.tag_configure("pending", foreground=T["tag_pending"])

        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Right-click to open folder
        self.tree.bind("<Button-3>", self._on_right_click)
        self._load()

    def _load(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for title, url, fmt, path, date, status in get_history():
            tag = "done" if status == "success" else "error"
            self.tree.insert("", "end",
                values=(title or url, fmt.upper(), date, status.title(), path),
                tags=(tag,))

    def _clear(self):
        if messagebox.askyesno("Clear History", "Delete all download history?", parent=self):
            clear_history()
            self._load()

    def _on_right_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)
        vals = self.tree.item(item, "values")
        path = vals[4] if vals else ""
        folder = os.path.dirname(path) if path else ""
        menu = tk.Menu(self, tearoff=0, bg=T["bg"], fg=T["fg"],
                       activebackground=T["btn_bg"], activeforeground=T["btn_fg"])
        menu.add_command(label="Open containing folder",
                         command=lambda: self._open_folder(folder),
                         state="normal" if folder and os.path.isdir(folder) else "disabled")
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _open_folder(self, path):
        if sys.platform == "win32":
            os.startfile(path)

# ── About window ──────────────────────────────────────────────────────────────
class AboutWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title(f"About {APP_NAME}")
        self.resizable(False, False)
        self.configure(bg=T["bg"])
        self.transient(parent)
        self.grab_set()
        _set_icon(self)

        logo_frame = tk.Frame(self, bg=T["btn_bg"], height=80)
        logo_frame.pack(fill="x")
        logo_frame.pack_propagate(False)
        tk.Label(logo_frame, text=f"▶  {APP_NAME}",
                 font=("Helvetica", 18, "bold"),
                 bg=T["btn_bg"], fg="#ffffff").place(relx=0.5, rely=0.5, anchor="center")

        body = tk.Frame(self, bg=T["bg"], padx=30, pady=20)
        body.pack(fill="both", expand=True)

        for label, value in [
            ("Version",    APP_VER),
            ("Powered by", "yt-dlp + ffmpeg"),
            ("Built with", "Python + tkinter + PyInstaller"),
            ("License",    "MIT — free to use and distribute"),
        ]:
            row = tk.Frame(body, bg=T["bg"])
            row.pack(fill="x", pady=3)
            tk.Label(row, text=label + ":", font=("Helvetica", 10, "bold"),
                     bg=T["bg"], fg=T["fg"], width=12, anchor="w").pack(side="left")
            tk.Label(row, text=value, font=("Helvetica", 10),
                     bg=T["bg"], fg=T["status_fg"]).pack(side="left")

        tk.Frame(body, bg=T["border"], height=1).pack(fill="x", pady=(12, 8))
        tk.Label(body,
                 text="This app downloads YouTube videos for personal use only.\n"
                      "Please respect content creators and YouTube's Terms of Service.",
                 font=("Helvetica", 9), bg=T["bg"], fg=T["status_fg"],
                 justify="center", wraplength=340).pack()

        tk.Frame(body, bg=T["border"], height=1).pack(fill="x", pady=(12, 8))
        footer_row = tk.Frame(body, bg=T["bg"])
        footer_row.pack()
        tk.Label(footer_row, text="© ToadOak  ", font=("Helvetica", 10),
                 bg=T["bg"], fg=T["status_fg"]).pack(side="left")
        gh = tk.Label(footer_row, text="GitHub", font=("Helvetica", 10, "underline"),
                      bg=T["bg"], fg=T["link_fg"], cursor="hand2")
        gh.pack(side="left")
        gh.bind("<Button-1>", lambda e: webbrowser.open(GITHUB_URL))

        tk.Button(body, text="Close", font=("Helvetica", 10),
                  bg=T["btn_bg"], fg=T["btn_fg"],
                  activebackground=T["btn_hover"], activeforeground=T["btn_fg"],
                  relief="flat", cursor="hand2", padx=20, pady=6,
                  command=self.destroy).pack(pady=(14, 0))

        self.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{px + (pw - w)//2}+{py + (ph - h)//2}")

# ── Main app ──────────────────────────────────────────────────────────────────
class KGYTDownloader(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.resizable(False, False)
        self.configure(bg=T["bg"])
        _set_icon(self)
        self.cfg = load_config()
        init_db()

        # Queue: list of dicts {url, fmt, quality, title, status, iid}
        self.queue = []
        self.is_downloading = False

        self._build_ui()
        self._restore_settings()

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        pad = {"padx": 16, "pady": 6}

        # ── Top bar ───────────────────────────────────────────────────────────
        top = tk.Frame(self, bg=T["bg"])
        top.pack(fill="x", padx=16, pady=(14, 4))
        tk.Label(top, text=APP_NAME, font=("Helvetica", 15, "bold"),
                 bg=T["bg"], fg=T["fg"]).pack(side="left")

        btn_frame = tk.Frame(top, bg=T["bg"])
        btn_frame.pack(side="right")
        for txt, cmd, tip in [
            ("⟳ Update yt-dlp", self._update_ytdlp, "Update the bundled yt-dlp to the latest version"),
            ("🕓 History",       self._open_history,  "View download history"),
            ("ⓘ About",         lambda: AboutWindow(self), "About this app"),
        ]:
            b = tk.Button(btn_frame, text=txt, font=("Helvetica", 8), relief="flat",
                          cursor="hand2", bg=T["muted_btn_bg"], fg=T["muted_btn_fg"],
                          activebackground=T["muted_btn_hover"], activeforeground=T["fg"],
                          padx=8, pady=3, command=cmd)
            b.pack(side="left", padx=3)
            Tooltip(b, tip)

        # ── URL input row ─────────────────────────────────────────────────────
        url_outer = tk.Frame(self, bg=T["bg"])
        url_outer.pack(fill="x", **pad)
        tk.Label(url_outer, text="YouTube URL", font=("Helvetica", 9),
                 bg=T["bg"], fg=T["fg"]).pack(anchor="w")

        url_row = tk.Frame(url_outer, bg=T["bg"])
        url_row.pack(fill="x")
        self.url_entry = tk.Entry(
            url_row, font=("Helvetica", 11), relief="flat", bd=6,
            bg=T["entry_bg"], fg=T["entry_fg"],
            insertbackground=T["entry_fg"],
            highlightbackground=T["border"], highlightthickness=1,
            highlightcolor=T["btn_bg"])
        self.url_entry.pack(side="left", fill="x", expand=True, ipady=5)
        self._attach_context_menu(self.url_entry)

        self.title_var = tk.StringVar(value="")
        self.title_label = tk.Label(url_outer, textvariable=self.title_var,
                                     font=("Helvetica", 8, "italic"),
                                     bg=T["bg"], fg=T["status_fg"], anchor="w")
        self.title_label.pack(fill="x")
        self.url_entry.bind("<FocusOut>", lambda e: self._fetch_title())
        self.url_entry.bind("<Return>",   lambda e: self._add_to_queue())

        # ── Options row ───────────────────────────────────────────────────────
        opts = tk.Frame(self, bg=T["bg"])
        opts.pack(fill="x", **pad)

        # Format
        tk.Label(opts, text="Format", font=("Helvetica", 9),
                 bg=T["bg"], fg=T["fg"]).grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.format_var = tk.StringVar(value=self.cfg.get("format", "mp4"))
        fmt_box = ttk.Combobox(opts, textvariable=self.format_var,
                                values=["mp4", "mp3"], state="readonly",
                                font=("Helvetica", 10), width=6)
        fmt_box.grid(row=1, column=0, sticky="w", padx=(0, 12))
        fmt_box.bind("<<ComboboxSelected>>", lambda e: self._on_format_change())

        # Quality
        self.quality_label = tk.Label(opts, text="Quality", font=("Helvetica", 9),
                                       bg=T["bg"], fg=T["fg"])
        self.quality_label.grid(row=0, column=1, sticky="w", padx=(0, 6))
        self.quality_var = tk.StringVar(value=self.cfg.get("quality", "Best"))
        self.quality_box = ttk.Combobox(opts, textvariable=self.quality_var,
                                         values=QUALITY_OPTIONS, state="readonly",
                                         font=("Helvetica", 10), width=8)
        self.quality_box.grid(row=1, column=1, sticky="w", padx=(0, 12))

        # Save folder
        tk.Label(opts, text="Save Folder", font=("Helvetica", 9),
                 bg=T["bg"], fg=T["fg"]).grid(row=0, column=2, sticky="w", padx=(0, 6))
        folder_row = tk.Frame(opts, bg=T["bg"])
        folder_row.grid(row=1, column=2, sticky="ew", padx=(0, 12))
        opts.columnconfigure(2, weight=1)
        self.folder_var = tk.StringVar(value=self.cfg.get("last_folder", ""))
        folder_entry = tk.Entry(folder_row, textvariable=self.folder_var,
                                 font=("Helvetica", 9), relief="flat", bd=4,
                                 bg=T["entry_bg"], fg=T["entry_fg"],
                                 highlightbackground=T["border"], highlightthickness=1,
                                 state="readonly", readonlybackground=T["entry_bg"])
        folder_entry.pack(side="left", fill="x", expand=True, ipady=4)
        tk.Button(folder_row, text="Browse", font=("Helvetica", 8),
                  bg=T["muted_btn_bg"], fg=T["muted_btn_fg"], relief="flat",
                  cursor="hand2", padx=6, pady=4,
                  command=self._pick_folder).pack(side="left", padx=(4, 0))

        # ── Checkboxes ────────────────────────────────────────────────────────
        chk_frame = tk.Frame(self, bg=T["bg"])
        chk_frame.pack(fill="x", padx=16, pady=(0, 4))

        self.embed_thumb_var = tk.BooleanVar(value=self.cfg.get("embed_thumbnail", True))
        self.embed_meta_var  = tk.BooleanVar(value=self.cfg.get("embed_metadata",  True))
        self.playlist_var    = tk.BooleanVar(value=self.cfg.get("playlist_mode",   False))

        self.thumb_chk = tk.Checkbutton(
            chk_frame, text="Embed thumbnail", variable=self.embed_thumb_var,
            font=("Helvetica", 9), bg=T["bg"], fg=T["fg"],
            activebackground=T["bg"], selectcolor=T["entry_bg"],
            command=self._save_opts)
        self.meta_chk = tk.Checkbutton(
            chk_frame, text="Embed metadata", variable=self.embed_meta_var,
            font=("Helvetica", 9), bg=T["bg"], fg=T["fg"],
            activebackground=T["bg"], selectcolor=T["entry_bg"],
            command=self._save_opts)
        self.playlist_chk = tk.Checkbutton(
            chk_frame, text="Download full playlist", variable=self.playlist_var,
            font=("Helvetica", 9), bg=T["bg"], fg=T["fg"],
            activebackground=T["bg"], selectcolor=T["entry_bg"],
            command=self._save_opts)

        self.thumb_chk.pack(side="left", padx=(0, 12))
        self.meta_chk.pack(side="left", padx=(0, 12))
        self.playlist_chk.pack(side="left")
        Tooltip(self.thumb_chk,  "Embed video thumbnail as album art (MP3 only)")
        Tooltip(self.meta_chk,   "Write title, uploader and year as ID3/MP4 tags")
        Tooltip(self.playlist_chk, "Download every video in the playlist instead of just the linked video")

        self._on_format_change()

        # ── Add to queue button ───────────────────────────────────────────────
        add_btn = tk.Button(self, text="＋  Add to Queue",
                             font=("Helvetica", 10, "bold"),
                             relief="flat", cursor="hand2", pady=7,
                             bg=T["btn_bg"], fg=T["btn_fg"],
                             activebackground=T["btn_hover"], activeforeground=T["btn_fg"],
                             command=self._add_to_queue)
        add_btn.pack(fill="x", padx=16, pady=(2, 6))

        # ── Queue list ────────────────────────────────────────────────────────
        tk.Label(self, text="Queue", font=("Helvetica", 9, "bold"),
                 bg=T["bg"], fg=T["fg"]).pack(anchor="w", padx=16)

        queue_frame = tk.Frame(self, bg=T["border"], padx=1, pady=1)
        queue_frame.pack(fill="x", padx=16, pady=(2, 4))

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Queue.Treeview", rowheight=20, font=("Helvetica", 9),
                         background=T["queue_bg"], fieldbackground=T["queue_bg"],
                         foreground=T["fg"], borderwidth=0)
        style.configure("Queue.Treeview.Heading", font=("Helvetica", 9, "bold"))
        style.configure("TCombobox",
                         fieldbackground=T["entry_bg"], background=T["entry_bg"],
                         foreground=T["entry_fg"],
                         selectbackground=T["btn_bg"], selectforeground=T["btn_fg"])
        style.configure("Horizontal.TProgressbar",
                         troughcolor=T["progress_trough"], background=T["btn_bg"])

        cols = ("#", "Title", "Fmt", "Quality", "Status")
        self.queue_tree = ttk.Treeview(queue_frame, columns=cols, show="headings",
                                        style="Queue.Treeview", height=5,
                                        selectmode="browse")
        widths = [28, 310, 45, 65, 90]
        for col, w in zip(cols, widths):
            self.queue_tree.heading(col, text=col)
            self.queue_tree.column(col, width=w, anchor="w" if col == "Title" else "center")

        self.queue_tree.tag_configure("done",    foreground=T["tag_done"])
        self.queue_tree.tag_configure("error",   foreground=T["tag_error"])
        self.queue_tree.tag_configure("pending", foreground=T["tag_pending"])
        self.queue_tree.tag_configure("active",  foreground=T["tag_active"])

        qsb = ttk.Scrollbar(queue_frame, orient="vertical", command=self.queue_tree.yview)
        self.queue_tree.configure(yscrollcommand=qsb.set)
        self.queue_tree.pack(side="left", fill="both", expand=True)
        qsb.pack(side="right", fill="y")
        self.queue_tree.bind("<Button-3>", self._queue_right_click)

        # Queue action buttons
        qbtn_frame = tk.Frame(self, bg=T["bg"])
        qbtn_frame.pack(fill="x", padx=16, pady=(0, 6))
        self.dl_btn = tk.Button(
            qbtn_frame, text="▶  Start Download",
            font=("Helvetica", 10, "bold"), relief="flat", cursor="hand2",
            pady=7, bg=T["btn_bg"], fg=T["btn_fg"],
            activebackground=T["btn_hover"], activeforeground=T["btn_fg"],
            command=self._start_queue)
        self.dl_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Button(qbtn_frame, text="✕  Clear Queue",
                  font=("Helvetica", 9), relief="flat", cursor="hand2",
                  pady=7, bg=T["muted_btn_bg"], fg=T["muted_btn_fg"],
                  activebackground=T["muted_btn_hover"], activeforeground=T["fg"],
                  command=self._clear_queue).pack(side="left", padx=(4, 0))

        # ── Progress + status ─────────────────────────────────────────────────
        self.progress = ttk.Progressbar(self, mode="indeterminate")
        self.progress.pack(fill="x", padx=16, pady=(0, 2))

        self.status_var = tk.StringVar(value="Ready")
        tk.Label(self, textvariable=self.status_var, font=("Helvetica", 9),
                 anchor="w", bg=T["bg"], fg=T["status_fg"]).pack(fill="x", padx=18, pady=(0, 2))

        # ── Console ───────────────────────────────────────────────────────────
        console_frame = tk.Frame(self, bg=T["border"], padx=1, pady=1)
        console_frame.pack(fill="x", padx=16, pady=(0, 14))
        self.console = tk.Text(
            console_frame, height=6,
            bg=T["console_bg"], fg=T["console_fg"],
            font=("Courier", 8), relief="flat", state="disabled",
            wrap="word", insertbackground=T["console_fg"],
            selectbackground=T["btn_bg"], selectforeground=T["btn_fg"])
        csb = ttk.Scrollbar(console_frame, command=self.console.yview)
        self.console.configure(yscrollcommand=csb.set)
        self.console.pack(side="left", fill="both", expand=True)
        csb.pack(side="right", fill="y")

    # ── Settings helpers ──────────────────────────────────────────────────────
    def _restore_settings(self):
        self._on_format_change()

    def _save_opts(self):
        self.cfg["embed_thumbnail"] = self.embed_thumb_var.get()
        self.cfg["embed_metadata"]  = self.embed_meta_var.get()
        self.cfg["playlist_mode"]   = self.playlist_var.get()
        self.cfg["format"]          = self.format_var.get()
        self.cfg["quality"]         = self.quality_var.get()
        save_config(self.cfg)

    def _on_format_change(self):
        is_mp3 = self.format_var.get() == "mp3"
        state = "disabled" if is_mp3 else "readonly"
        self.quality_box.configure(state=state)
        self.quality_label.configure(fg=T["status_fg"] if is_mp3 else T["fg"])
        self._save_opts()

    def _pick_folder(self):
        d = filedialog.askdirectory(title="Select save folder",
                                     initialdir=self.folder_var.get() or os.path.expanduser("~"))
        if d:
            self.folder_var.set(d)
            self.cfg["last_folder"] = d
            save_config(self.cfg)

    # ── URL / title fetch ─────────────────────────────────────────────────────
    def _fetch_title(self):
        url = self.url_entry.get().strip()
        if not url or not is_valid_yt_url(url):
            self.title_var.set("" if not url else "⚠ URL doesn't look like a valid YouTube link")
            return
        self.title_var.set("Fetching title…")

        def task():
            try:
                kwargs = {}
                if sys.platform == "win32":
                    kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                r = subprocess.run(
                    [_bin("yt-dlp"), "--no-playlist", "--print", "title", "--no-download", url],
                    capture_output=True, text=True, timeout=15, **kwargs)
                title = r.stdout.strip().splitlines()[0] if r.returncode == 0 else ""
                self.after(0, lambda: self.title_var.set(f"📹 {title}" if title else ""))
            except Exception:
                self.after(0, lambda: self.title_var.set(""))

        threading.Thread(target=task, daemon=True).start()

    # ── Queue management ──────────────────────────────────────────────────────
    def _add_to_queue(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("No URL", "Please enter a YouTube URL.", parent=self)
            return
        if not is_valid_yt_url(url):
            messagebox.showwarning("Invalid URL",
                "That doesn't look like a valid YouTube URL.\n\nExpected format:\nhttps://www.youtube.com/watch?v=...",
                parent=self)
            return
        if not self.folder_var.get():
            messagebox.showwarning("No folder", "Please select a save folder first.", parent=self)
            return
        err = _check_bins()
        if err:
            messagebox.showerror("Missing files", err, parent=self)
            return

        fmt     = self.format_var.get()
        quality = self.quality_var.get()
        title   = self.title_var.get().replace("📹 ", "") or url
        n       = len(self.queue) + 1

        iid = self.queue_tree.insert("", "end",
            values=(n, title, fmt.upper(), quality if fmt == "mp4" else "—", "Pending"),
            tags=("pending",))

        self.queue.append({"url": url, "fmt": fmt, "quality": quality,
                           "title": title, "status": "pending", "iid": iid})
        self.url_entry.delete(0, tk.END)
        self.title_var.set("")

    def _clear_queue(self):
        if self.is_downloading:
            messagebox.showwarning("Downloading", "Cannot clear queue while downloading.", parent=self)
            return
        self.queue.clear()
        for row in self.queue_tree.get_children():
            self.queue_tree.delete(row)

    def _queue_right_click(self, event):
        item = self.queue_tree.identify_row(event.y)
        if not item:
            return
        self.queue_tree.selection_set(item)
        idx = self.queue_tree.index(item)
        entry = self.queue[idx] if idx < len(self.queue) else None
        menu = tk.Menu(self, tearoff=0, bg=T["bg"], fg=T["fg"],
                       activebackground=T["btn_bg"], activeforeground=T["btn_fg"])
        menu.add_command(label="Remove from queue",
                         state="normal" if entry and entry["status"] == "pending" else "disabled",
                         command=lambda: self._remove_queue_item(item, idx))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _remove_queue_item(self, iid, idx):
        self.queue_tree.delete(iid)
        if idx < len(self.queue):
            self.queue.pop(idx)
        # Renumber
        for i, item in enumerate(self.queue_tree.get_children()):
            vals = list(self.queue_tree.item(item, "values"))
            vals[0] = i + 1
            self.queue_tree.item(item, values=vals)

    # ── Download queue ────────────────────────────────────────────────────────
    def _start_queue(self):
        pending = [q for q in self.queue if q["status"] == "pending"]
        if not pending:
            messagebox.showinfo("Queue empty", "No pending items in the queue.", parent=self)
            return
        if self.is_downloading:
            return
        self.is_downloading = True
        self.dl_btn.configure(state="disabled")
        self.progress.start(12)
        self._clear_console()
        threading.Thread(target=self._process_queue, daemon=True).start()

    def _process_queue(self):
        folder = self.folder_var.get()
        for entry in self.queue:
            if entry["status"] != "pending":
                continue
            self.after(0, lambda e=entry: self._set_queue_status(e, "active", "Downloading…"))
            self.after(0, lambda t=entry["title"]: self._set_status(f"Downloading: {t}"))
            self.after(0, lambda t=entry["title"]: self._log(f"\n▶ Starting: {t}"))
            self.after(0, lambda: self._log("─" * 55))

            result, out_path = self._download_one(entry, folder)
            entry["status"] = "success" if result == "success" else "error"

            if result == "success":
                self.after(0, lambda e=entry: self._set_queue_status(e, "done", "Done ✓"))
                self.after(0, lambda: self._log("✓ Complete!"))
                add_history(entry["title"], entry["url"], entry["fmt"], out_path, "success")
            else:
                self.after(0, lambda e=entry: self._set_queue_status(e, "error", "Error ✗"))
                self.after(0, lambda r=result: self._log(f"✗ {r.replace('error:','')}"))
                add_history(entry["title"], entry["url"], entry["fmt"], "", "error")

        self.after(0, self._queue_finished)

    def _download_one(self, entry, folder):
        try:
            ytdlp      = _bin("yt-dlp")
            ffmpeg_dir = os.path.dirname(_bin("ffmpeg"))
            url        = entry["url"]
            fmt        = entry["fmt"]
            quality    = entry["quality"]
            out_tmpl   = os.path.join(folder, "%(title)s.%(ext)s")
            playlist   = self.playlist_var.get()
            embed_thumb = self.embed_thumb_var.get()
            embed_meta  = self.embed_meta_var.get()

            playlist_flag = [] if playlist else ["--no-playlist"]

            if fmt == "mp3":
                cmd = [ytdlp, "-x", "--audio-format", "mp3", "--audio-quality", "0",
                       "--ffmpeg-location", ffmpeg_dir,
                       *playlist_flag,
                       *(["--embed-thumbnail", "--convert-thumbnails", "jpg"] if embed_thumb else []),
                       *(["--add-metadata"] if embed_meta else []),
                       "-o", out_tmpl, url]
            else:
                fmt_str = QUALITY_FORMAT_MAP.get(quality, QUALITY_FORMAT_MAP["Best"])
                cmd = [ytdlp, "-f", fmt_str,
                       "--merge-output-format", "mp4",
                       "--ffmpeg-location", ffmpeg_dir,
                       *playlist_flag,
                       *(["--add-metadata"] if embed_meta else []),
                       "-o", out_tmpl, url]

            kwargs = {"stdout": subprocess.PIPE, "stderr": subprocess.STDOUT,
                      "text": True, "bufsize": 1}
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            out_path = ""
            with subprocess.Popen(cmd, **kwargs) as proc:
                for line in proc.stdout:
                    line = line.rstrip()
                    if line:
                        self.after(0, lambda l=line: self._log(l))
                        if "[download] Destination:" in line or "Merging formats into" in line:
                            out_path = line.split(":", 1)[-1].strip().strip('"')
                proc.wait()

            if proc.returncode == 0:
                return "success", out_path
            return f"error:Process exited with code {proc.returncode}", ""
        except Exception as e:
            return f"error:{e}", ""

    def _queue_finished(self):
        self.progress.stop()
        self.dl_btn.configure(state="normal")
        self.is_downloading = False
        done  = sum(1 for q in self.queue if q["status"] == "success")
        total = len(self.queue)
        self._set_status(f"Finished — {done}/{total} completed")
        self._log("─" * 55)
        self._log(f"✓ Queue finished: {done}/{total} successful")
        if done < total:
            messagebox.showwarning("Queue complete",
                f"{done}/{total} items downloaded successfully.\n"
                f"{total-done} failed — check the console for details.", parent=self)
        else:
            messagebox.showinfo("Queue complete",
                f"All {total} item(s) downloaded successfully!", parent=self)

    # ── yt-dlp self-update ────────────────────────────────────────────────────
    def _update_ytdlp(self):
        if self.is_downloading:
            messagebox.showwarning("Busy", "Cannot update while downloading.", parent=self)
            return
        self._log("Checking for yt-dlp updates…")
        self.progress.start(12)

        def task():
            try:
                kwargs = {}
                if sys.platform == "win32":
                    kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                r = subprocess.run([_bin("yt-dlp"), "-U"],
                                    capture_output=True, text=True, **kwargs)
                output = (r.stdout + r.stderr).strip()
                return output or "Update check complete."
            except Exception as e:
                return f"error:{e}"

        def done(result):
            self.progress.stop()
            self._log(result)
            self._set_status("yt-dlp update check complete")

        self._run_in_thread(task, on_done=done)

    # ── History ───────────────────────────────────────────────────────────────
    def _open_history(self):
        HistoryWindow(self)

    # ── Console / status ──────────────────────────────────────────────────────
    def _log(self, text):
        def _append():
            self.console.configure(state="normal")
            self.console.insert(tk.END, text + "\n")
            self.console.see(tk.END)
            self.console.configure(state="disabled")
        self.after(0, _append)

    def _clear_console(self):
        self.console.configure(state="normal")
        self.console.delete("1.0", tk.END)
        self.console.configure(state="disabled")

    def _set_status(self, msg):
        self.status_var.set(msg)

    def _set_queue_status(self, entry, tag, label):
        try:
            vals = list(self.queue_tree.item(entry["iid"], "values"))
            vals[4] = label
            self.queue_tree.item(entry["iid"], values=vals, tags=(tag,))
        except Exception:
            pass

    # ── Context menu ──────────────────────────────────────────────────────────
    def _attach_context_menu(self, entry):
        menu = tk.Menu(entry, tearoff=0, bg=T["bg"], fg=T["fg"],
                       activebackground=T["btn_bg"], activeforeground=T["btn_fg"],
                       relief="flat", bd=1)
        menu.add_command(label="Cut",        command=lambda: entry.selection_present() and entry.event_generate("<<Cut>>"))
        menu.add_command(label="Copy",       command=lambda: entry.selection_present() and entry.event_generate("<<Copy>>"))
        menu.add_command(label="Paste",      command=lambda: entry.event_generate("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label="Select All", command=lambda: (entry.select_range(0, tk.END), entry.icursor(tk.END)))
        menu.add_command(label="Clear",      command=lambda: entry.delete(0, tk.END))

        def show_menu(event):
            has_sel = entry.selection_present()
            menu.entryconfigure("Cut",  state="normal" if has_sel else "disabled")
            menu.entryconfigure("Copy", state="normal" if has_sel else "disabled")
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        entry.bind("<Button-3>", show_menu)
        entry.bind("<Button-2>", show_menu)

    def _run_in_thread(self, fn, on_done=None):
        def wrapper():
            r = fn()
            if on_done:
                self.after(0, on_done, r)
        threading.Thread(target=wrapper, daemon=True).start()


if __name__ == "__main__":
    app = KGYTDownloader()
    app.mainloop()