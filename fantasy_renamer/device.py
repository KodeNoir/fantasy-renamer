"""
Détection dynamique du matériel.

- Mac Apple Silicon (M1/M2/M3/M4...) : accélération GPU via MPS (Metal).
- Mac Intel : bascule automatiquement sur le CPU, sans erreur.
- Linux/Windows avec carte NVIDIA : CUDA (bonus pour les contributeurs GitHub).

Important : ce module n'importe PyTorch qu'à l'intérieur des fonctions, pour
que l'interface s'ouvre instantanément (l'import de torch prend plusieurs
secondes sur un iMac Intel).
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from dataclasses import dataclass

# Si une opération n'existe pas encore en version Metal, PyTorch la calcule
# sur le CPU au lieu de planter. Doit être défini AVANT l'import de torch.
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")


@dataclass
class DeviceInfo:
    torch_device: str          # "mps", "cuda" ou "cpu"
    label_fr: str              # Texte affiché dans l'interface
    cpu_name: str              # Ex. "Apple M4" ou "Intel(R) Core(TM) i5-8500"
    machine: str               # "arm64" ou "x86_64"
    rosetta: bool              # True si un Python Intel tourne sur puce Apple

    @property
    def is_accelerated(self) -> bool:
        return self.torch_device in ("mps", "cuda")


def _sysctl(key: str) -> str:
    """Lit une valeur système macOS (silencieusement vide en cas d'échec)."""
    try:
        out = subprocess.run(
            ["sysctl", "-n", key], capture_output=True, text=True, timeout=3
        )
        return out.stdout.strip()
    except Exception:
        return ""


def cpu_name() -> str:
    if sys.platform == "darwin":
        name = _sysctl("machdep.cpu.brand_string")
        if name:
            return name
    return platform.processor() or platform.machine() or "Processeur inconnu"


def running_under_rosetta() -> bool:
    """
    Vrai si l'on exécute un Python x86_64 (Intel) sur une puce Apple via
    Rosetta 2. Dans ce cas MPS n'est PAS disponible : on prévient l'utilisateur.
    """
    if sys.platform != "darwin":
        return False
    return _sysctl("sysctl.proc_translated") == "1"


def _mps_really_works(torch) -> bool:
    """
    `is_available()` peut répondre oui alors qu'un vieux macOS bloque ensuite.
    On fait donc un vrai petit calcul de test sur le GPU.
    """
    try:
        if not (torch.backends.mps.is_built() and torch.backends.mps.is_available()):
            return False
        x = torch.ones(4, device="mps")
        _ = (x * 2).sum().item()
        return True
    except Exception:
        return False


def detect_device() -> DeviceInfo:
    """Choisit le meilleur moteur de calcul disponible, sans jamais planter."""
    import torch  # import tardif volontaire

    machine = platform.machine()
    rosetta = running_under_rosetta()
    name = cpu_name()

    # 1) Apple Silicon -> Metal (MPS)
    if sys.platform == "darwin" and machine == "arm64" and _mps_really_works(torch):
        return DeviceInfo("mps", f"Puce Apple ({name}) – accélération Metal activée ⚡",
                          name, machine, rosetta)

    # 2) NVIDIA (Linux / Windows)
    try:
        if torch.cuda.is_available():
            gpu = torch.cuda.get_device_name(0)
            return DeviceInfo("cuda", f"Carte graphique NVIDIA ({gpu})",
                              name, machine, rosetta)
    except Exception:
        pass

    # 3) CPU (iMac Intel, ou tout autre cas)
    # Sur Intel, utiliser tous les cœurs physiques donne le meilleur débit.
    try:
        physical = int(_sysctl("hw.physicalcpu") or 0)
        if physical > 0:
            torch.set_num_threads(physical)
    except Exception:
        pass

    label = f"Processeur ({name}) – mode classique CPU"
    if rosetta:
        label += " [Rosetta : installez la version Apple Silicon pour aller plus vite]"
    return DeviceInfo("cpu", label, name, machine, rosetta)


def empty_device_cache(torch_device: str) -> None:
    """Libère la mémoire GPU réservée par PyTorch (appelé entre les images)."""
    try:
        import torch

        if torch_device == "mps" and hasattr(torch, "mps"):
            torch.mps.empty_cache()
        elif torch_device == "cuda":
            torch.cuda.empty_cache()
    except Exception:
        pass
