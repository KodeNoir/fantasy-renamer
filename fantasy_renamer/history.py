"""
Mémoire des noms attribués (fichier history.json).

Règle : un nom donné ne peut pas être réattribué pendant 30 jours.
Les entrées plus anciennes sont automatiquement purgées.

Le fichier est réécrit de manière "atomique" (fichier temporaire puis
remplacement) après CHAQUE nom attribué : même en cas de coupure de courant
au milieu d'un lot, aucun nom déjà donné n'est oublié.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set

from . import config


def _normalize(name: str) -> str:
    return name.strip().casefold()


class NameHistory:
    def __init__(self, path: Optional[Path] = None, memory_days: int = config.NAME_MEMORY_DAYS):
        self.path = Path(path) if path else config.history_file()
        self.memory_days = memory_days
        self._lock = threading.Lock()
        self._entries: List[Dict[str, str]] = []
        self.load()

    # ------------------------------------------------------------------ I/O
    def load(self) -> None:
        with self._lock:
            self._entries = []
            if not self.path.exists():
                return
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                entries = data.get("entries", []) if isinstance(data, dict) else data
                self._entries = [e for e in entries if isinstance(e, dict) and "name" in e and "date" in e]
            except (json.JSONDecodeError, OSError):
                # Fichier abîmé : on le met de côté au lieu de planter.
                backup = self.path.with_suffix(f".corrompu-{datetime.now():%Y%m%d-%H%M%S}.json")
                try:
                    self.path.rename(backup)
                except OSError:
                    pass
                self._entries = []
            self._purge_locked()

    def _save_locked(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "app": config.APP_NAME,
            "memory_days": self.memory_days,
            "entries": self._entries,
        }
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".history-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    # ---------------------------------------------------------------- logique
    def _cutoff(self, now: Optional[datetime] = None) -> datetime:
        return (now or datetime.now()) - timedelta(days=self.memory_days)

    def _purge_locked(self, now: Optional[datetime] = None) -> int:
        cutoff = self._cutoff(now)
        kept = []
        for e in self._entries:
            try:
                if datetime.fromisoformat(e["date"]) >= cutoff:
                    kept.append(e)
            except (ValueError, TypeError):
                continue
        removed = len(self._entries) - len(kept)
        self._entries = kept
        return removed

    def recent_names(self, now: Optional[datetime] = None) -> Set[str]:
        """Noms (normalisés) attribués pendant la période de mémoire."""
        cutoff = self._cutoff(now)
        with self._lock:
            out = set()
            for e in self._entries:
                try:
                    if datetime.fromisoformat(e["date"]) >= cutoff:
                        out.add(_normalize(e["name"]))
                except (ValueError, TypeError):
                    continue
            return out

    def is_recent(self, name: str, now: Optional[datetime] = None) -> bool:
        return _normalize(name) in self.recent_names(now)

    def add(self, name: str, category: str, source_file: str = "", now: Optional[datetime] = None) -> None:
        """Enregistre un nom et sauvegarde immédiatement."""
        with self._lock:
            self._entries.append({
                "name": name,
                "category": category,
                "date": (now or datetime.now()).isoformat(timespec="seconds"),
                "source_file": source_file,
            })
            self._purge_locked(now)
            self._save_locked()

    def entries(self) -> List[Dict[str, str]]:
        with self._lock:
            return list(self._entries)

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)
