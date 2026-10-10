"""
Traitement par lot : analyse -> choix du nom -> copie dans la destination.

Ce module ne connaît pas l'interface graphique : il communique uniquement via
une fonction `on_event(event)`. On peut donc l'utiliser aussi en ligne de
commande ou dans des tests automatiques.
"""

from __future__ import annotations

import csv
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional, Protocol

from . import config
from .classifier import ClassificationResult, ImageLoadError
from .history import NameHistory
from .names import FantasyNameGenerator


class Classifier(Protocol):
    """Tout objet possédant ces méthodes peut servir de classifieur."""

    is_loaded: bool

    def load(self, on_status: Callable[[str, str], None]) -> None: ...
    def classify(self, path: Path) -> ClassificationResult: ...


@dataclass
class Event:
    kind: str                 # "status" | "download" | "device" | "start" | "file" | "skip" | "error" | "done"
    message: str = ""
    current: int = 0
    total: int = 0
    data: dict = field(default_factory=dict)


@dataclass
class FileOutcome:
    source: Path
    status: str               # "renommé" | "ignoré" | "erreur"
    new_name: str = ""
    category: str = ""
    confidence: float = 0.0
    reason: str = ""


@dataclass
class BatchSummary:
    total: int = 0
    renamed: int = 0
    skipped: int = 0
    errors: int = 0
    cancelled: bool = False
    seconds: float = 0.0
    report_path: Optional[Path] = None
    outcomes: List[FileOutcome] = field(default_factory=list)


def list_candidate_files(source_dir: Path) -> List[Path]:
    """Tous les fichiers visibles du dossier (non récursif), triés par nom."""
    files = []
    for p in sorted(source_dir.iterdir(), key=lambda x: x.name.lower()):
        if p.name.startswith("."):          # .DS_Store, ._fichier (macOS) ...
            continue
        if p.is_file():
            files.append(p)
    return files


class BatchProcessor:
    def __init__(
        self,
        classifier: Classifier,
        history: Optional[NameHistory] = None,
        name_generator: Optional[FantasyNameGenerator] = None,
    ):
        self.classifier = classifier
        self.history = history or NameHistory()
        self.names = name_generator or FantasyNameGenerator()

    # ------------------------------------------------------------------ utils
    @staticmethod
    def _validate_dirs(source: Path, dest: Path) -> None:
        if not source.is_dir():
            raise ValueError(f"Le dossier source n'existe pas : {source}")
        if source.resolve() == dest.resolve():
            raise ValueError("Le dossier destination doit être différent du dossier source.")
        dest.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _existing_stems(dest: Path) -> set:
        """Noms déjà présents dans la destination (sans extension, sans casse)."""
        return {p.stem.casefold() for p in dest.iterdir() if p.is_file()}

    # -------------------------------------------------------------- principal
    def run(
        self,
        source_dir: Path,
        dest_dir: Path,
        on_event: Callable[[Event], None] = lambda e: None,
        should_stop: Callable[[], bool] = lambda: False,
    ) -> BatchSummary:
        t0 = time.time()
        source_dir, dest_dir = Path(source_dir), Path(dest_dir)
        self._validate_dirs(source_dir, dest_dir)

        files = list_candidate_files(source_dir)
        summary = BatchSummary(total=len(files))
        if not files:
            on_event(Event("done", "Aucun fichier trouvé dans le dossier source."))
            return summary

        # 1) Modèle IA (téléchargé au premier lancement)
        if not self.classifier.is_loaded:
            def relay(kind: str, msg: str) -> None:
                on_event(Event(kind if kind in ("download", "device") else "status", msg))
            self.classifier.load(on_status=relay)

        on_event(Event("start", f"{len(files)} fichier(s) à traiter.", 0, len(files)))
        existing = self._existing_stems(dest_dir)

        # 2) Boucle sur les fichiers
        for index, src in enumerate(files, start=1):
            if should_stop():
                summary.cancelled = True
                break

            outcome = self._process_one(src, dest_dir, existing)
            summary.outcomes.append(outcome)

            if outcome.status == "renommé":
                summary.renamed += 1
                label = config.CATEGORY_LABELS_FR.get(outcome.category, outcome.category)
                doubt = "   ⚠️ à vérifier" if outcome.confidence < config.LOW_CONFIDENCE else ""
                on_event(Event(
                    "file",
                    f"{src.name}  →  {outcome.new_name}   ({label}, {outcome.confidence:.0%}){doubt}",
                    index, len(files), {"category": outcome.category},
                ))
            elif outcome.status == "ignoré":
                summary.skipped += 1
                on_event(Event("skip", f"{src.name} ignoré : {outcome.reason}", index, len(files)))
            else:
                summary.errors += 1
                on_event(Event("error", f"{src.name} : {outcome.reason}", index, len(files)))

        # 3) Rapport CSV dans la destination
        summary.seconds = time.time() - t0
        summary.report_path = self._write_report(dest_dir, summary)

        msg = (f"Terminé : {summary.renamed} image(s) renommée(s), "
               f"{summary.skipped} ignorée(s), {summary.errors} erreur(s) "
               f"en {summary.seconds:.0f} s.")
        if summary.cancelled:
            msg = "Traitement arrêté. " + msg
        on_event(Event("done", msg, len(summary.outcomes), len(files), {"summary": summary}))
        return summary

    def _process_one(self, src: Path, dest_dir: Path, existing: set) -> FileOutcome:
        ext = src.suffix.lower()
        if ext not in config.SUPPORTED_EXTENSIONS:
            return FileOutcome(src, "ignoré", reason=f"format non pris en charge ({ext or 'sans extension'})")

        # Analyse IA
        try:
            result = self.classifier.classify(src)
        except ImageLoadError:
            return FileOutcome(src, "ignoré", reason="image corrompue ou illisible")
        except Exception as exc:
            return FileOutcome(src, "erreur", reason=f"échec de l'analyse ({exc})")

        # Choix d'un nom libre (30 jours + pas de fichier existant)
        try:
            name = self.names.pick(
                result.category,
                forbidden=self.history.recent_names(),
                extra_check=lambda n: n.casefold() not in existing,
            )
        except RuntimeError as exc:
            return FileOutcome(src, "erreur", reason=str(exc))

        # Copie (l'original n'est jamais modifié)
        target = dest_dir / f"{name}{'.jpg' if ext == '.jpeg' else ext}"
        try:
            shutil.copy2(src, target)
        except Exception as exc:
            return FileOutcome(src, "erreur", reason=f"copie impossible ({exc})")

        existing.add(name.casefold())
        self.history.add(name, result.category, source_file=src.name)
        reason = "confiance faible : à vérifier" if result.confidence < config.LOW_CONFIDENCE else ""
        return FileOutcome(src, "renommé", target.name, result.category, result.confidence, reason)

    @staticmethod
    def _write_report(dest_dir: Path, summary: BatchSummary) -> Optional[Path]:
        if not summary.outcomes:
            return None
        path = dest_dir / f"rapport_fantasy_renamer_{datetime.now():%Y-%m-%d_%Hh%M%S}.csv"
        try:
            with path.open("w", newline="", encoding="utf-8-sig") as f:   # utf-8-sig : lisible dans Excel/Numbers
                w = csv.writer(f, delimiter=";")
                w.writerow(["Fichier original", "Statut", "Nouveau nom", "Catégorie", "Confiance", "Détail"])
                for o in summary.outcomes:
                    w.writerow([
                        o.source.name, o.status, o.new_name,
                        config.CATEGORY_LABELS_FR.get(o.category, o.category),
                        f"{o.confidence:.0%}" if o.status == "renommé" else "",
                        o.reason,
                    ])
            return path
        except OSError:
            return None
