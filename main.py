#!/usr/bin/env python3
"""
Point d'entrée de Fantasy Renamer.

    python main.py                         -> ouvre l'interface graphique
    python main.py --cli SOURCE DEST       -> mode ligne de commande (sans fenêtre)
    python main.py --device                -> affiche le moteur de calcul détecté
"""

from __future__ import annotations

import argparse
import multiprocessing
import sys
from pathlib import Path


def run_cli(source: Path, dest: Path) -> int:
    from fantasy_renamer.classifier import ImageClassifier
    from fantasy_renamer.processor import BatchProcessor

    def show(ev):
        prefix = f"[{ev.current}/{ev.total}] " if ev.total and ev.kind in ("file", "skip", "error") else ""
        print(prefix + ev.message, flush=True)

    summary = BatchProcessor(ImageClassifier()).run(source, dest, on_event=show)
    return 0 if summary.errors == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Fantasy Renamer")
    parser.add_argument("--cli", nargs=2, metavar=("SOURCE", "DEST"),
                        help="traite un dossier sans ouvrir l'interface")
    parser.add_argument("--device", action="store_true",
                        help="affiche le moteur de calcul détecté (MPS / CPU) et quitte")
    args, _unknown = parser.parse_known_args()   # tolère les arguments ajoutés par macOS

    if args.device:
        from fantasy_renamer.device import detect_device
        info = detect_device()
        print(f"Machine : {info.machine} | Processeur : {info.cpu_name}")
        print(f"Moteur PyTorch : {info.torch_device} -> {info.label_fr}")
        return 0

    if args.cli:
        return run_cli(Path(args.cli[0]).expanduser(), Path(args.cli[1]).expanduser())

    from fantasy_renamer.gui import run_gui
    run_gui()
    return 0


if __name__ == "__main__":
    multiprocessing.freeze_support()   # nécessaire pour l'app compilée (PyInstaller)
    sys.exit(main())
