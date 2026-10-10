"""
Interface graphique (customtkinter), entièrement en français.

Architecture :
- Le traitement (IA + copies) tourne dans un thread séparé pour que la
  fenêtre reste réactive.
- Le thread n'a PAS le droit de toucher aux widgets (règle de Tkinter) :
  il dépose des messages dans une file (queue), que la fenêtre lit toutes
  les 100 ms.
"""

from __future__ import annotations

import json
import queue
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from . import config
from .classifier import ImageClassifier
from .history import NameHistory
from .processor import BatchProcessor, Event

ACCENT = "#7B5CD6"        # violet "magique"
ACCENT_HOVER = "#6545C0"
STOP = "#C0485A"
STOP_HOVER = "#A23748"


class FantasyRenamerApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("system")      # suit le mode clair/sombre du Mac
        ctk.set_default_color_theme("blue")

        self.title(config.APP_NAME)
        self.geometry("720x640")
        self.minsize(620, 560)

        self.source_dir: Path | None = None
        self.dest_dir: Path | None = None
        self.events: "queue.Queue[Event]" = queue.Queue()
        self.stop_flag = threading.Event()
        self.worker: threading.Thread | None = None
        self.classifier = ImageClassifier()     # gardé en mémoire entre deux lots

        self._build_ui()
        self._load_settings()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._poll_events)

    # ================================================================== UI
    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        # --- En-tête
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(22, 8))
        ctk.CTkLabel(header, text="✨ Fantasy Renamer",
                     font=ctk.CTkFont(size=26, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(header, text="Renomme tes images avec des noms de Fantasy uniques, "
                                  "grâce à une IA qui tourne sur ton Mac.",
                     font=ctk.CTkFont(size=13), text_color=("gray35", "gray70")).pack(anchor="w")

        # --- Choix des dossiers
        folders = ctk.CTkFrame(self, corner_radius=12)
        folders.grid(row=1, column=0, sticky="ew", padx=24, pady=8)
        folders.grid_columnconfigure(1, weight=1)

        self.btn_source = ctk.CTkButton(folders, text="📂  Dossier source", width=190,
                                        command=self._choose_source)
        self.btn_source.grid(row=0, column=0, padx=14, pady=(14, 6), sticky="w")
        self.lbl_source = ctk.CTkLabel(folders, text="Aucun dossier choisi", anchor="w",
                                       text_color=("gray40", "gray65"))
        self.lbl_source.grid(row=0, column=1, padx=(0, 14), pady=(14, 6), sticky="ew")

        self.btn_dest = ctk.CTkButton(folders, text="📁  Dossier destination", width=190,
                                      command=self._choose_dest)
        self.btn_dest.grid(row=1, column=0, padx=14, pady=(6, 14), sticky="w")
        self.lbl_dest = ctk.CTkLabel(folders, text="Aucun dossier choisi", anchor="w",
                                     text_color=("gray40", "gray65"))
        self.lbl_dest.grid(row=1, column=1, padx=(0, 14), pady=(6, 14), sticky="ew")

        # --- Démarrer + progression
        action = ctk.CTkFrame(self, fg_color="transparent")
        action.grid(row=2, column=0, sticky="ew", padx=24, pady=(8, 4))
        action.grid_columnconfigure(0, weight=1)

        self.btn_start = ctk.CTkButton(action, text="Démarrer", height=46,
                                       font=ctk.CTkFont(size=17, weight="bold"),
                                       fg_color=ACCENT, hover_color=ACCENT_HOVER,
                                       command=self._on_start_stop)
        self.btn_start.grid(row=0, column=0, sticky="ew")

        self.progress = ctk.CTkProgressBar(action, height=14, progress_color=ACCENT)
        self.progress.grid(row=1, column=0, sticky="ew", pady=(14, 6))
        self.progress.set(0)

        status_row = ctk.CTkFrame(action, fg_color="transparent")
        status_row.grid(row=2, column=0, sticky="ew")
        status_row.grid_columnconfigure(0, weight=1)
        self.lbl_status = ctk.CTkLabel(status_row, text="Prêt. Choisis tes dossiers puis clique sur Démarrer.",
                                       anchor="w", justify="left", wraplength=560)
        self.lbl_status.grid(row=0, column=0, sticky="ew")
        self.lbl_counter = ctk.CTkLabel(status_row, text="", anchor="e",
                                        font=ctk.CTkFont(weight="bold"))
        self.lbl_counter.grid(row=0, column=1, sticky="e")

        # --- Journal
        ctk.CTkLabel(self, text="Journal", anchor="w",
                     font=ctk.CTkFont(size=13, weight="bold")).grid(row=3, column=0, sticky="ew",
                                                                    padx=24, pady=(10, 0))
        self.log = ctk.CTkTextbox(self, corner_radius=10, font=ctk.CTkFont(family="Menlo", size=12))
        self.log.grid(row=4, column=0, sticky="nsew", padx=24, pady=(4, 8))
        self.log.configure(state="disabled")

        # --- Pied de page
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=5, column=0, sticky="ew", padx=24, pady=(0, 16))
        footer.grid_columnconfigure(0, weight=1)
        self.lbl_device = ctk.CTkLabel(footer, text="Moteur IA : détecté au démarrage du traitement",
                                       anchor="w", font=ctk.CTkFont(size=11),
                                       text_color=("gray45", "gray60"))
        self.lbl_device.grid(row=0, column=0, sticky="ew")
        self.btn_open = ctk.CTkButton(footer, text="Ouvrir la destination", width=170,
                                      fg_color="transparent", border_width=1,
                                      text_color=("gray20", "gray85"),
                                      command=self._open_dest, state="disabled")
        self.btn_open.grid(row=0, column=1, sticky="e")

    # ============================================================ réglages
    def _load_settings(self) -> None:
        try:
            data = json.loads(config.settings_file().read_text(encoding="utf-8"))
        except Exception:
            return
        for key, setter in (("source", self._set_source), ("dest", self._set_dest)):
            p = data.get(key)
            if p and Path(p).is_dir():
                setter(Path(p))

    def _save_settings(self) -> None:
        try:
            config.settings_file().write_text(json.dumps({
                "source": str(self.source_dir) if self.source_dir else "",
                "dest": str(self.dest_dir) if self.dest_dir else "",
            }, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    # ============================================================= actions
    @staticmethod
    def _short(path: Path, maxlen: int = 60) -> str:
        s = str(path).replace(str(Path.home()), "~", 1)
        return s if len(s) <= maxlen else "…" + s[-(maxlen - 1):]

    def _set_source(self, p: Path) -> None:
        self.source_dir = p
        self.lbl_source.configure(text=self._short(p), text_color=("gray10", "gray90"))

    def _set_dest(self, p: Path) -> None:
        self.dest_dir = p
        self.lbl_dest.configure(text=self._short(p), text_color=("gray10", "gray90"))
        self.btn_open.configure(state="normal")

    def _choose_source(self) -> None:
        d = filedialog.askdirectory(title="Choisis le dossier contenant les images",
                                    initialdir=str(self.source_dir or Path.home()))
        if d:
            self._set_source(Path(d))
            self._save_settings()

    def _choose_dest(self) -> None:
        d = filedialog.askdirectory(title="Choisis le dossier où copier les images renommées",
                                    initialdir=str(self.dest_dir or self.source_dir or Path.home()))
        if d:
            self._set_dest(Path(d))
            self._save_settings()

    def _open_dest(self) -> None:
        if self.dest_dir and self.dest_dir.exists():
            opener = "open" if sys.platform == "darwin" else "xdg-open"
            subprocess.Popen([opener, str(self.dest_dir)])

    def _on_start_stop(self) -> None:
        if self.worker and self.worker.is_alive():
            self.stop_flag.set()
            self.btn_start.configure(state="disabled", text="Arrêt après l'image en cours…")
            return

        if not self.source_dir:
            messagebox.showwarning(config.APP_NAME, "Choisis d'abord le dossier source.")
            return
        if not self.dest_dir:
            messagebox.showwarning(config.APP_NAME, "Choisis d'abord le dossier destination.")
            return
        if self.source_dir.resolve() == self.dest_dir.resolve():
            messagebox.showwarning(config.APP_NAME,
                                   "Le dossier destination doit être différent du dossier source.")
            return

        self._clear_log()
        self.progress.set(0)
        self.lbl_counter.configure(text="")
        self.stop_flag.clear()
        self._set_busy(True)
        self.worker = threading.Thread(target=self._worker, daemon=True)
        self.worker.start()

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.btn_source.configure(state=state)
        self.btn_dest.configure(state=state)
        if busy:
            self.btn_start.configure(text="Arrêter", fg_color=STOP, hover_color=STOP_HOVER, state="normal")
        else:
            self.btn_start.configure(text="Démarrer", fg_color=ACCENT, hover_color=ACCENT_HOVER, state="normal")

    # ============================================================== thread
    def _worker(self) -> None:
        """Exécuté hors du thread graphique : ne touche à aucun widget !"""
        try:
            processor = BatchProcessor(self.classifier, history=NameHistory())
            processor.run(self.source_dir, self.dest_dir,
                          on_event=self.events.put,
                          should_stop=self.stop_flag.is_set)
        except Exception as exc:
            self.events.put(Event("fatal", str(exc)))

    def _poll_events(self) -> None:
        try:
            while True:
                self._handle_event(self.events.get_nowait())
        except queue.Empty:
            pass
        self.after(100, self._poll_events)

    def _handle_event(self, ev: Event) -> None:
        if ev.kind == "download":
            # Durée inconnue : barre animée "en attente" + message rassurant
            self.lbl_status.configure(text=ev.message)
            self.progress.configure(mode="indeterminate")
            self.progress.start()
            self._log("⏬ " + ev.message)
        elif ev.kind == "status":
            self.lbl_status.configure(text=ev.message)
            self._log("• " + ev.message)
        elif ev.kind == "device":
            self.lbl_device.configure(text="Moteur IA : " + ev.message)
            self._log("🖥  " + ev.message)
        elif ev.kind == "start":
            self._stop_indeterminate()
            self.lbl_status.configure(text="Analyse des images…")
            self.lbl_counter.configure(text=f"0 / {ev.total}")
            self._log("▶ " + ev.message)
        elif ev.kind in ("file", "skip", "error"):
            icon = {"file": "✅", "skip": "⏭ ", "error": "⚠️"}[ev.kind]
            self._log(f"{icon} {ev.message}")
            if ev.total:
                self.progress.set(ev.current / ev.total)
                self.lbl_counter.configure(text=f"{ev.current} / {ev.total}")
                self.lbl_status.configure(text=f"Image {ev.current} sur {ev.total}…")
        elif ev.kind == "done":
            self._stop_indeterminate()
            if ev.total:
                self.progress.set(ev.current / ev.total)
            self.lbl_status.configure(text=ev.message)
            self._log("🏁 " + ev.message)
            summary = ev.data.get("summary")
            if summary and summary.report_path:
                self._log(f"📄 Rapport : {summary.report_path.name}")
            self._set_busy(False)
        elif ev.kind == "fatal":
            self._stop_indeterminate()
            self.progress.set(0)
            self.lbl_status.configure(text="Une erreur a interrompu le traitement.")
            self._log("❌ " + ev.message)
            self._set_busy(False)
            messagebox.showerror(config.APP_NAME, ev.message)

    def _stop_indeterminate(self) -> None:
        self.progress.stop()
        self.progress.configure(mode="determinate")
        self.progress.set(0)

    # ============================================================== journal
    def _log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def _on_close(self) -> None:
        if self.worker and self.worker.is_alive():
            if not messagebox.askyesno(config.APP_NAME,
                                       "Un traitement est en cours. Quitter quand même ?\n"
                                       "(Les images déjà copiées sont conservées.)"):
                return
            self.stop_flag.set()
        self.destroy()


def run_gui() -> None:
    app = FantasyRenamerApp()
    app.mainloop()
