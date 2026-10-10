"""
Génération de noms de Fantasy.

1. On pioche d'abord au hasard dans les listes du dossier `data/`
   (names_homme.txt, names_femme.txt, names_lieu.txt) — modifiables à volonté.
2. Si tous les noms d'une liste ont déjà servi dans les 30 derniers jours,
   un générateur procédural de syllabes prend le relais (réserve quasi infinie).

Règle stricte : un seul mot, uniquement des lettres (pas d'espace, pas de
tiret, pas d'apostrophe) → jamais de nom composé.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Set

from . import config

MIN_LEN = 3
MAX_LEN = 14


def is_valid_name(name: str) -> bool:
    """Un seul mot, uniquement des lettres, longueur raisonnable."""
    return MIN_LEN <= len(name) <= MAX_LEN and name.isalpha()


def load_name_list(path: Path) -> List[str]:
    """Lit un fichier texte (un nom par ligne, # = commentaire), sans doublons."""
    names: List[str] = []
    seen: Set[str] = set()
    if not path.exists():
        return names
    for raw in path.read_text(encoding="utf-8").splitlines():
        name = raw.split("#", 1)[0].strip()
        if not name or not is_valid_name(name):
            continue
        name = name[0].upper() + name[1:].lower()
        key = name.casefold()
        if key not in seen:
            seen.add(key)
            names.append(name)
    return names


# --------------------------------------------------------------------------- #
# Générateur procédural de syllabes
# --------------------------------------------------------------------------- #
SYLLABLES = {
    config.CATEGORY_MALE: {
        "start": ["Al", "Bal", "Bran", "Cael", "Cor", "Dar", "Dor", "Eld", "Fal", "Fen",
                  "Gal", "Gar", "Hal", "Is", "Jor", "Kael", "Kor", "Lor", "Mal", "Mor",
                  "Nor", "Or", "Ras", "Ruv", "Sar", "Tal", "Tor", "Ul", "Var", "Vor",
                  "Wul", "Zan", "Thar", "Grim", "Bel", "Ash"],
        "mid": ["", "", "a", "e", "i", "o", "an", "ar", "en", "or", "ri", "va", "dra", "go"],
        "end": ["ric", "dor", "mir", "ion", "ath", "gar", "wyn", "las", "rin", "thas",
                "mund", "vard", "ius", "orn", "ek", "an", "us", "ald", "is", "ok"],
    },
    config.CATEGORY_FEMALE: {
        "start": ["Ae", "Al", "Bri", "Cae", "Cy", "Del", "El", "Fae", "Gwen", "Ys",
                  "Il", "Is", "Ka", "Lae", "Li", "Lu", "Mae", "Mi", "Ny", "Ori",
                  "Rhi", "Sa", "Sel", "Syl", "Ta", "Thi", "Vae", "Vi", "Wy", "Ze",
                  "Ara", "Eli", "Ilv", "Nim", "Ser"],
        "mid": ["", "", "a", "e", "i", "la", "li", "ra", "re", "na", "ne", "th", "lys", "ri"],
        "end": ["ia", "wen", "ra", "elle", "ith", "yra", "ana", "iel", "ssa", "nae",
                "lys", "ora", "ys", "ine", "is", "eth", "a", "ielle", "wyn", "ara"],
    },
    config.CATEGORY_PLACE: {
        "start": ["Ael", "Bar", "Cal", "Dun", "Eber", "Fal", "Glen", "Hael", "Ir", "Kar",
                  "Lor", "Mor", "Nar", "Ost", "Rav", "Sil", "Tir", "Ul", "Val", "Wyn",
                  "Zar", "Ash", "Brim", "Crag", "Drak", "Frost", "Gold", "Iron", "Mist", "Storm"],
        "mid": ["", "", "", "a", "e", "o", "en", "er", "il", "an", "um", "ar"],
        "end": ["heim", "dor", "mar", "grad", "fell", "garde", "holm", "mere", "ia", "vale",
                "wood", "reach", "spire", "haven", "moor", "crest", "ford", "keep", "thal", "ion"],
    },
}


def _has_ugly_cluster(name: str) -> bool:
    low = name.lower()
    # Trois lettres identiques d'affilée, ou trois voyelles d'affilée
    for i in range(len(low) - 2):
        a, b, c = low[i], low[i + 1], low[i + 2]
        if a == b == c:
            return True
        if all(ch in "aeiouy" for ch in (a, b, c)):
            return True
    return False


def generate_procedural(category: str, rng: random.Random) -> str:
    parts = SYLLABLES.get(category, SYLLABLES[config.CATEGORY_PLACE])
    for _ in range(50):
        name = rng.choice(parts["start"]) + rng.choice(parts["mid"]) + rng.choice(parts["end"])
        name = name[0].upper() + name[1:].lower()
        if is_valid_name(name) and not _has_ugly_cluster(name):
            return name
    return name  # en pratique jamais atteint


# --------------------------------------------------------------------------- #
# Générateur principal
# --------------------------------------------------------------------------- #
class FantasyNameGenerator:
    def __init__(self, data_dir: Optional[Path] = None, seed: Optional[int] = None):
        self.data_dir = Path(data_dir) if data_dir else config.resource_dir()
        self.rng = random.Random(seed)
        self.lists: Dict[str, List[str]] = {
            cat: load_name_list(self.data_dir / f"names_{cat}.txt") for cat in config.CATEGORIES
        }

    def list_size(self, category: str) -> int:
        return len(self.lists.get(category, []))

    def pick(
        self,
        category: str,
        forbidden: Iterable[str],
        extra_check: Optional[Callable[[str], bool]] = None,
        max_procedural_tries: int = 5000,
    ) -> str:
        """
        Choisit un nom pour `category`.

        forbidden   : noms interdits (déjà donnés < 30 jours), comparés sans
                      tenir compte des majuscules.
        extra_check : fonction optionnelle renvoyant False si le nom est
                      inutilisable (ex. fichier déjà présent dans la destination).
        """
        banned = {n.casefold() for n in forbidden}

        def ok(name: str) -> bool:
            return name.casefold() not in banned and (extra_check is None or extra_check(name))

        candidates = [n for n in self.lists.get(category, []) if ok(n)]
        if candidates:
            return self.rng.choice(candidates)

        for _ in range(max_procedural_tries):
            name = generate_procedural(category, self.rng)
            if ok(name):
                return name

        raise RuntimeError(
            f"Impossible de trouver un nom libre pour la catégorie « {category} ». "
            "Ajoutez des noms dans le dossier data/."
        )
